import os
import sys
import gzip
from io import BytesIO
import json
import hashlib
import shutil
import requests
import tarfile
import urllib3
import argparse
import threading
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Optional, Dict, Any
import urllib.parse
urllib3.disable_warnings()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Pull Docker images with platform specification and authentication support')
parser.add_argument('image', help='[registry/][repository/]image[:tag|@digest]')
parser.add_argument('--platform', help='Target platform (e.g., linux/amd64, linux/arm64, linux/arm/v7)')
parser.add_argument('--max-concurrent-downloads', type=int, default=3, help='Maximum number of concurrent layer downloads (default: 3)')
parser.add_argument('--username', help='Username for registry authentication (supports Docker Hub, GCR, ECR, Harbor, etc.)')
parser.add_argument('--password', help='Password for registry authentication')
args = parser.parse_args()

image_arg = args.image
target_platform = args.platform
max_concurrent_downloads = args.max_concurrent_downloads

# Thread-safe progress tracking
progress_lock = threading.Lock()
download_progress = {}

# Global session for connection pooling
session = requests.Session()
session.headers.update({'User-Agent': 'Docker-Pull-Script/1.0'})

# Authentication support
username = args.username
password = args.password

# Display authentication info
if username and password:
    print(f"Using authentication for user: {username}")
elif username or password:
    print("Warning: Both username and password are required for authentication")
else:
    print("Using anonymous access (no credentials provided)")

# Retry decorator
class RetryError(Exception):
    pass

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, RetryError) as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

# Look for the Docker image to download
repo = 'library'
tag = 'latest'
imgparts = image_arg.split('/')
try:
    img,tag = imgparts[-1].split('@')
except ValueError:
    try:
        img,tag = imgparts[-1].split(':')
    except ValueError:
        img = imgparts[-1]
# Docker client doesn't seem to consider the first element as a potential registry unless there is a '.' or ':'
if len(imgparts) > 1 and ('.' in imgparts[0] or ':' in imgparts[0]):
    registry = imgparts[0]
    repo = '/'.join(imgparts[1:-1])
else:
    registry = 'registry-1.docker.io'
    if len(imgparts[:-1]) != 0:
        repo = '/'.join(imgparts[:-1])
    else:
        repo = 'library'
repository = '{}/{}'.format(repo, img)

# Get Docker authentication endpoint when it is required
auth_url='https://auth.docker.io/token'
reg_service='registry.docker.io'

# Handle authentication for different registry types
registry_auth_endpoints = {
    'registry-1.docker.io': {
        'auth_url': 'https://auth.docker.io/token',
        'service': 'registry.docker.io'
    },
    'gcr.io': {
        'auth_url': 'https://gcr.io/v2/token',
        'service': 'gcr.io'
    },
    'us.gcr.io': {
        'auth_url': 'https://us.gcr.io/v2/token',
        'service': 'us.gcr.io'
    },
    'eu.gcr.io': {
        'auth_url': 'https://eu.gcr.io/v2/token',
        'service': 'eu.gcr.io'
    },
    'asia.gcr.io': {
        'auth_url': 'https://asia.gcr.io/v2/token',
        'service': 'asia.gcr.io'
    },
    'quay.io': {
        'auth_url': 'https://quay.io/v2/auth',
        'service': 'quay.io'
    }
}

# Check if we have a known registry
if registry in registry_auth_endpoints:
    auth_url = registry_auth_endpoints[registry]['auth_url']
    reg_service = registry_auth_endpoints[registry]['service']

# Probe for authentication endpoint
resp = requests.get(f'https://{registry}/v2/', verify=False)
if resp.status_code == 401:
    www_auth = resp.headers.get('WWW-Authenticate', '')
    if 'Bearer' in www_auth:
        # Parse WWW-Authenticate header for token endpoint
        try:
            # Handle different formats of WWW-Authenticate header
            if 'realm=' in www_auth:
                realm_start = www_auth.find('realm="') + 7
                realm_end = www_auth.find('"', realm_start)
                auth_url = www_auth[realm_start:realm_end]
                
            if 'service=' in www_auth:
                service_start = www_auth.find('service="') + 9
                service_end = www_auth.find('"', service_start)
                if service_start > 8:  # Check if service= was found
                    reg_service = www_auth[service_start:service_end]
        except (IndexError, ValueError):
            # Fallback to registry-specific defaults
            pass
    elif 'Basic' in www_auth:
        # Registry uses basic authentication
        print(f"Registry {registry} uses basic authentication")


def get_auth_head(type_var):
    header = {'Accept': type_var}
    
    # If username and password are provided, use basic auth
    if username and password:
        # Use basic authentication for private registries
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header['Authorization'] = f'Basic {credentials}'
        return header
    
    # For public registries or when no credentials provided, use token auth
    try:
        token_url = f"{auth_url}?service={reg_service}&scope=repository:{repository}:pull"
        
        # Add credentials to token request if available
        auth = None
        if username and password:
            auth = (username, password)
            
        resp = requests.get(token_url, auth=auth, verify=False)
        
        if resp.status_code == 200:
            token_data = resp.json()
            token = token_data.get('token') or token_data.get('access_token')
            if token:
                header['Authorization'] = f'Bearer {token}'
        else:
            # If token auth fails, try anonymous access
            print(f"Warning: Token authentication failed with status {resp.status_code}")
            
    except Exception as e:
        print(f"Warning: Could not obtain authentication token: {e}")
    
    return header

def format_speed(bytes_downloaded):
    """Format download speed in human-readable format"""
    if bytes_downloaded < 1024:
        return f"{bytes_downloaded:.0f} B"
    elif bytes_downloaded < 1024 * 1024:
        return f"{bytes_downloaded/1024:.1f} KB"
    elif bytes_downloaded < 1024 * 1024 * 1024:
        return f"{bytes_downloaded/(1024*1024):.1f} MB"
    else:
        return f"{bytes_downloaded/(1024*1024*1024):.1f} GB"

def format_time(seconds):
    """Format time in human-readable format"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.0f}m{seconds%60:.0f}s"
    else:
        return f"{seconds/3600:.0f}h{(seconds%3600)/60:.0f}m"

def progress_bar(ublob, downloaded, total, start_time):
    """Enhanced progress bar with speed and ETA"""
    if total and total > 0:
        percentage = (downloaded / total) * 100
        bar_length = 30
        filled_length = int(bar_length * downloaded // total)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        elapsed = time.time() - start_time
        speed = downloaded / elapsed if elapsed > 0 else 0
        
        if total > downloaded:
            eta = (total - downloaded) / speed if speed > 0 else 0
            eta_str = format_time(eta)
        else:
            eta_str = "0s"
        
        speed_str = format_speed(speed)
        
        sys.stdout.write(f'\r{ublob[7:19]}: |{bar}| {percentage:.1f}% ({speed_str}/s, ETA: {eta_str})')
        sys.stdout.flush()
    else:
        # Unknown total size
        speed = format_speed(downloaded / (time.time() - start_time))
        sys.stdout.write(f'\r{ublob[7:19]}: Downloaded {format_speed(downloaded)} ({speed}/s)')
        sys.stdout.flush()

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def download_layer(layer, imgdir, parentid):
    """Download a single layer in a separate thread with streaming and progress"""
    ublob = layer['digest']
    fake_layerid = hashlib.sha256((parentid+'\n'+ublob+'\n').encode('utf-8')).hexdigest()
    layerdir = imgdir + '/' + fake_layerid
    os.makedirs(layerdir, exist_ok=True)

    # Create VERSION file
    with open(layerdir + '/VERSION', 'w') as f:
        f.write('1.0')

    start_time = time.time()

    auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json')

    # Try primary URL first, then fallback URLs
    urls = [f'https://{registry}/v2/{repository}/blobs/{ublob}']
    if 'urls' in layer and layer['urls']:
        urls.extend(layer['urls'])

    for url in urls:
        try:
            with session.get(url, headers=auth_head, stream=True, verify=False, timeout=30) as bresp:
                if bresp.status_code == 200:
                    break
        except requests.RequestException:
            continue
    else:
        with progress_lock:
            print(f'ERROR: Cannot download layer {ublob[7:19]} from any source')
        return None

    # Stream download with progress
    content_length = int(bresp.headers.get('Content-Length', 0)) if bresp.headers.get('Content-Length') else None
    downloaded = 0
    last_update = 0

    # Stream directly to file without loading entire content in memory
    with open(layerdir + '/layer_gzip.tar', 'wb') as file:
        for chunk in bresp.iter_content(chunk_size=1024*1024):  # 1MB chunks
            if chunk:
                file.write(chunk)
                downloaded += len(chunk)

                # Update progress every 100ms
                current_time = time.time()
                if current_time - last_update > 0.1:
                    with progress_lock:
                        progress_bar(ublob, downloaded, content_length, start_time)
                    last_update = current_time

    with progress_lock:
        print(f'{ublob[7:19]}: Download complete ({format_speed(downloaded)})')
        print(f'{ublob[7:19]}: Extracting...')

    # Stream decompress to avoid memory issues
    with open(layerdir + '/layer.tar', 'wb') as out_file:
        with gzip.open(layerdir + '/layer_gzip.tar', 'rb') as gz_file:
            shutil.copyfileobj(gz_file, out_file)

    os.remove(layerdir + '/layer_gzip.tar')
    return {'fake_layerid': fake_layerid, 'layer': layer, 'layerdir': layerdir}

# Main execution continues...
# Get Docker authentication
auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json')

# Get manifest
resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, tag), headers=auth_head, verify=False)
if resp.status_code != 200:
    print('Cannot fetch manifest for {} [HTTP {}]'.format(repository, resp.status_code))
    if resp.status_code == 401:
        print('Authentication failed. Please check your credentials.')
        if not username or not password:
            print('Private registry requires authentication. Use --username and --password arguments.')
    elif resp.status_code == 403:
        print('Access forbidden. You may not have permission to access this image.')
    print(resp.content)
    exit(1)

manifest = resp.json()

# Handle multi-platform images
if target_platform and 'manifests' in manifest:
    # This is a manifest list, find the right platform
    found = False
    for m in manifest['manifests']:
        platform = m.get('platform', {})
        platform_str = f"{platform.get('os', 'linux')}/{platform.get('architecture', 'amd64')}"
        if platform.get('variant'):
            platform_str += f"/{platform.get('variant')}"
        
        if platform_str == target_platform:
            print(f"Found manifest for platform: {platform_str}")
            digest = m['digest']
            
            # Fetch the actual manifest for this platform
            auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json')
            resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, digest), headers=auth_head, verify=False)
            if resp.status_code != 200:
                print('Cannot fetch manifest for platform {} [HTTP {}]'.format(target_platform, resp.status_code))
                if resp.status_code == 401:
                    print('Authentication failed. Please check your credentials.')
                    if not username or not password:
                        print('Private registry requires authentication. Use --username and --password arguments.')
                elif resp.status_code == 403:
                    print('Access forbidden. You may not have permission to access this image.')
                exit(1)
            
            manifest = resp.json()
            found = True
            break
    
    if not found:
        print('No manifest found for platform: {}'.format(target_platform))
        print('Available platforms:')
        for m in manifest['manifests']:
            platform = m.get('platform', {})
            platform_str = f"{platform.get('os', 'linux')}/{platform.get('architecture', 'amd64')}"
            if platform.get('variant'):
                platform_str += f"/{platform.get('variant')}"
            print(f"  - {platform_str}")
        exit(1)

# Create image directory
imgdir = 'docker_{}_{}'.format(img, tag.replace(':', '_').replace('@', '_'))
if os.path.exists(imgdir):
    shutil.rmtree(imgdir)
os.makedirs(imgdir)

# Get layers
layers = manifest['layers']

# Create repositories file
repositories = '{{"{}":{{"{}":"{}"}}}}'.format(repo, img, tag)
with open(imgdir + '/repositories', 'w') as f:
    f.write(repositories)

# Download layers concurrently
print('Downloading {} layers...'.format(len(layers)))
with ThreadPoolExecutor(max_workers=max_concurrent_downloads) as executor:
    future_to_layer = {executor.submit(download_layer, layer, imgdir, 'sha256:' + hashlib.sha256(''.encode()).hexdigest()): layer for layer in layers}
    
    for future in as_completed(future_to_layer):
        layer = future_to_layer[future]
        try:
            result = future.result()
            if result:
                print('{}: Layer {} completed'.format(result['fake_layerid'][:12], result['layer']['digest'][7:19]))
            else:
                print('ERROR: Failed to download layer {}'.format(layer['digest'][7:19]))
        except Exception as e:
            print('ERROR: Exception downloading layer {}: {}'.format(layer['digest'][7:19], str(e)))

# Create manifest.json
manifest_json = [{
    'Config': 'config.json',
    'RepoTags': ['{}:{}'.format(repository, tag)],
    'Layers': ['{}/layer.tar'.format(hashlib.sha256(('sha256:' + hashlib.sha256(''.encode()).hexdigest() + '\n' + layer['digest'] + '\n').encode()).hexdigest()) for layer in layers]
}]

with open(imgdir + '/manifest.json', 'w') as f:
    json.dump(manifest_json, f)

# Save config blob
config_digest = manifest['config']['digest']
auth_head = get_auth_head('application/vnd.docker.container.image.v1+json')
resp = requests.get('https://{}/v2/{}/blobs/{}'.format(registry, repository, config_digest), headers=auth_head, verify=False)
if resp.status_code != 200:
    print('Cannot fetch config blob [HTTP {}]'.format(resp.status_code))
    if resp.status_code == 401:
        print('Authentication failed. Please check your credentials.')
        if not username or not password:
            print('Private registry requires authentication. Use --username and --password arguments.')
    elif resp.status_code == 403:
        print('Access forbidden. You may not have permission to access this image.')
    exit(1)

with open(imgdir + '/config.json', 'wb') as f:
    f.write(resp.content)

# Create final tar file
docker_tar = repo.replace('/', '_') + '_' + img + '.tar'
sys.stdout.write("Creating archive...")
sys.stdout.flush()

tar = tarfile.open(docker_tar, "w")
tar.add(imgdir, arcname=os.path.sep)
tar.close()

# Clean up temporary directory
shutil.rmtree(imgdir)

print('\rDocker image pulled: ' + docker_tar)
print('You can load it with: docker load < ' + docker_tar)