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
from concurrent.futures import ThreadPoolExecutor, as_completed
urllib3.disable_warnings()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Pull Docker images with platform specification')
parser.add_argument('image', help='[registry/][repository/]image[:tag|@digest]')
parser.add_argument('--platform', help='Target platform (e.g., linux/amd64, linux/arm64, linux/arm/v7)')
parser.add_argument('--max-concurrent-downloads', type=int, default=3, help='Maximum number of concurrent layer downloads (default: 3)')
args = parser.parse_args()

image_arg = args.image
target_platform = args.platform
max_concurrent_downloads = args.max_concurrent_downloads

# Thread-safe progress tracking
progress_lock = threading.Lock()
download_progress = {}

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
resp = requests.get('https://{}/v2/'.format(registry), verify=False)
if resp.status_code == 401:
	auth_url = resp.headers['WWW-Authenticate'].split('"')[1]
	try:
		reg_service = resp.headers['WWW-Authenticate'].split('"')[3]
	except IndexError:
		reg_service = ""

# Get Docker token (this function is useless for unauthenticated registries like Microsoft)
def get_auth_head(type):
	resp = requests.get('{}?service={}&scope=repository:{}:pull'.format(auth_url, reg_service, repository), verify=False)
	access_token = resp.json()['token']
	auth_head = {'Authorization':'Bearer '+ access_token, 'Accept': type}
	return auth_head

# Docker style progress bar
def progress_bar(ublob, nb_traits):
	sys.stdout.write('\r' + ublob[7:19] + ': Downloading [')
	for i in range(0, nb_traits):
		if i == nb_traits - 1:
			sys.stdout.write('>')
		else:
			sys.stdout.write('=')
	for i in range(0, 49 - nb_traits):
		sys.stdout.write(' ')
	sys.stdout.write(']')
	sys.stdout.flush()

def download_layer(layer, imgdir, parentid):
	"""Download a single layer in a separate thread"""
	ublob = layer['digest']
	# FIXME: Creating fake layer ID. Don't know how Docker generates it
	fake_layerid = hashlib.sha256((parentid+'\n'+ublob+'\n').encode('utf-8')).hexdigest()
	layerdir = imgdir + '/' + fake_layerid
	os.mkdir(layerdir)

	# Creating VERSION file
	file = open(layerdir + '/VERSION', 'w')
	file.write('1.0')
	file.close()

	# Creating layer.tar file
	with progress_lock:
		sys.stdout.write(ublob[7:19] + ': Downloading...\n')
		sys.stdout.flush()
	
	auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json') # refreshing token to avoid its expiration
	bresp = requests.get('https://{}/v2/{}/blobs/{}'.format(registry, repository, ublob), headers=auth_head, stream=True, verify=False)
	if (bresp.status_code != 200): # When the layer is located at a custom URL
		if 'urls' in layer and len(layer['urls']) > 0:
			bresp = requests.get(layer['urls'][0], headers=auth_head, stream=True, verify=False)
		if (bresp.status_code != 200):
			content_length = bresp.headers.get('Content-Length', 'unknown')
			with progress_lock:
				print('\rERROR: Cannot download layer {} [HTTP {}] Content-Length: {}'.format(ublob[7:19], bresp.status_code, content_length))
				print(bresp.content)
			return None
	
	# Stream download
	bresp.raise_for_status()
	content_length = bresp.headers.get('Content-Length')
	if content_length:
		unit = int(content_length) / 50
	else:
		unit = 8192  # fallback unit size
	
	acc = 0
	nb_traits = 0
	with open(layerdir + '/layer_gzip.tar', "wb") as file:
		for chunk in bresp.iter_content(chunk_size=8192): 
			if chunk:
				file.write(chunk)
				acc = acc + 8192
				if acc > unit:
					nb_traits = nb_traits + 1
					acc = 0
	
	with progress_lock:
		sys.stdout.write("{}:  Extracting...\n".format(ublob[7:19]))
		sys.stdout.flush()
	
	with open(layerdir + '/layer.tar', "wb") as file: # Decompress gzip response
		with gzip.open(layerdir + '/layer_gzip.tar','rb') as unzLayer:
			# Type cast to ensure compatibility with copyfileobj
			shutil.copyfileobj(unzLayer, file)  # type: ignore
	os.remove(layerdir + '/layer_gzip.tar')
	content_length = bresp.headers.get('Content-Length', 'unknown')
	with progress_lock:
		print("{}: Pull complete [{}]".format(ublob[7:19], content_length))
	
	return {'fake_layerid': fake_layerid, 'layer': layer, 'layerdir': layerdir}

# First try to fetch manifest list to check for multi-platform support
auth_head = get_auth_head('application/vnd.docker.distribution.manifest.list.v2+json')
resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, tag), headers=auth_head, verify=False)

# Initialize manifest variables
manifests = None
manifest_data = None

# Check if we got a manifest list (multi-platform)
if resp.status_code == 200 and 'manifests' in resp.json():
	print('[+] Multi-platform manifest detected')
	manifests = resp.json()['manifests']
	# Continue with existing multi-platform logic
elif resp.status_code == 200:
	# Single platform manifest, but got it with list accept header
	print('[+] Single platform manifest detected')
	manifest_data = resp.json()
	# Handle single manifest case
else:
	# Fallback to v2 manifest
	print('[-] Cannot fetch manifest list, trying v2 manifest for {} [HTTP {}]'.format(repository, resp.status_code))
	auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json')
	resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, tag), headers=auth_head, verify=False)
	if resp.status_code != 200:
		print('[-] Cannot fetch any manifest for {} [HTTP {}]'.format(repository, resp.status_code))
		print(resp.content)
		exit(1)
	manifest_data = resp.json()

# Initialize variables
layers = None
config = None
confresp = None

# Handle multi-platform manifest
if manifests is not None:
	# Handle platform selection
	if target_platform:
		print('[+] Searching for platform-specific manifest...')
		selected_manifest = None

		for manifest in manifests:
			platform_info = manifest.get('platform', {})
			platform_string = f"{platform_info.get('os', 'linux')}/{platform_info.get('architecture', 'amd64')}"
			
			# Handle variant (e.g., arm/v7)
			if 'variant' in platform_info:
				platform_string += f"/{platform_info['variant']}"
			
			if platform_string == target_platform:
				selected_manifest = manifest
				break

		if selected_manifest:
			print(f'[+] Found manifest for platform: {target_platform}')
			manifest_digest = selected_manifest['digest']
			
			# Fetch the platform-specific manifest
			auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json')
			resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, manifest_digest), headers=auth_head, verify=False)
			if resp.status_code != 200:
				print('[-] Cannot fetch platform-specific manifest [HTTP {}]'.format(resp.status_code))
				exit(1)
			
			layers = resp.json()['layers']
			config = resp.json()['config']['digest']
			confresp = requests.get('https://{}/v2/{}/blobs/{}'.format(registry, repository, config), headers=auth_head, verify=False)
		else:
			print('[-] No manifest found for platform: {}'.format(target_platform))
			print('[+] Available platforms:')
			for manifest in manifests:
				platform_info = manifest.get('platform', {})
				platform_str = f"{platform_info.get('os', 'linux')}/{platform_info.get('architecture', 'amd64')}"
				if 'variant' in platform_info:
					platform_str += f"/{platform_info['variant']}"
				print(f'    - {platform_str}')
			exit(1)
	else:
		# No platform specified, show available platforms
		print('[+] Manifests found for this tag (use --platform to specify platform):')
		for manifest in manifests:
			platform_info = manifest.get('platform', {})
			platform_str = f"{platform_info.get('os', 'linux')}/{platform_info.get('architecture', 'amd64')}"
			if 'variant' in platform_info:
				platform_str += f"/{platform_info['variant']}"
			print(f'    Platform: {platform_str}, digest: {manifest["digest"]}')
		exit(1)

# Process single manifest case
if layers is None and manifest_data is not None:
	
	# Check platform compatibility for single manifest
	if target_platform:
		# For schema v2, get platform info from config
		if 'layers' in manifest_data:
			# Get config to check architecture
			temp_config = manifest_data['config']['digest']
			temp_confresp = requests.get('https://{}/v2/{}/blobs/{}'.format(registry, repository, temp_config), headers=auth_head, verify=False)
			if temp_confresp.status_code == 200:
				config_json = temp_confresp.json()
				image_arch = config_json.get('architecture', 'amd64')
				image_os = config_json.get('os', 'linux')
				image_variant = config_json.get('variant', '')
				image_platform = f"{image_os}/{image_arch}"
				if image_variant:
					image_platform += f"/{image_variant}"
				
				if image_platform != target_platform:
					print(f'[-] Platform mismatch: requested {target_platform}, but image only supports {image_platform}')
					print('[-] This image does not support multi-platform manifests')
					exit(1)
				else:
					print(f'[+] Platform verified: {target_platform}')
		elif 'fsLayers' in manifest_data:
			# For schema v1, check architecture field
			image_arch = manifest_data.get('architecture', 'amd64')
			image_platform = f"linux/{image_arch}"
			
			if image_platform != target_platform:
				print(f'[-] Platform mismatch: requested {target_platform}, but image only supports {image_platform}')
				print('[-] Schema v1 manifests do not support multi-platform')
				exit(1)
			else:
				print(f'[+] Platform verified: {target_platform}')
	
	# Handle different manifest schema versions
	if 'layers' in manifest_data:
		# Schema version 2
		layers = manifest_data['layers']
		config = manifest_data['config']['digest']
		confresp = requests.get('https://{}/v2/{}/blobs/{}'.format(registry, repository, config), headers=auth_head, verify=False)
	elif 'fsLayers' in manifest_data:
		# Schema version 1 - convert to version 2 format
		print('[+] Converting schema v1 manifest to v2 format')
		layers = []
		for fs_layer in manifest_data['fsLayers']:
			layers.append({'digest': fs_layer['blobSum']})
		# For schema v1, we need to create a fake config
		config_data = {
			'architecture': manifest_data.get('architecture', 'amd64'),
			'config': {},
			'created': '1970-01-01T00:00:00Z',
			'history': [],
			'os': 'linux',
			'rootfs': {
				'type': 'layers',
				'diff_ids': []
			}
		}
		# Create a fake config blob
		config_json = json.dumps(config_data).encode('utf-8')
		config_digest = 'sha256:' + hashlib.sha256(config_json).hexdigest()
		config = config_digest
		# Create a mock response for config
		class MockResponse:
			def __init__(self, content):
				self.content = content
				self.status_code = 200
		confresp = MockResponse(config_json)
	else:
		print('[-] Invalid manifest format: missing layers or fsLayers field')
		print('Manifest content:', manifest_data)
		exit(1)

# Create tmp folder that will hold the image
imgdir = 'tmp_{}_{}'.format(img, tag.replace(':', '@'))
os.mkdir(imgdir)
print('Creating image structure in: ' + imgdir)
if config is not None and confresp is not None:
	file = open('{}/{}.json'.format(imgdir, config[7:]), 'wb')
	if hasattr(confresp, 'content'):
		# For both Response and MockResponse objects
		content_data = getattr(confresp, 'content')
		if isinstance(content_data, bytes):
			file.write(content_data)
		elif isinstance(content_data, str):
			file.write(content_data.encode('utf-8'))
	file.close()

if config is not None:
	manifest_content = [{
		'Config': config[7:] + '.json',
		'RepoTags': [ ],
		'Layers': [ ]
		}]
else:
	print('[-] Error: config is None')
	exit(1)
if len(imgparts[:-1]) != 0:
	manifest_content[0]['RepoTags'].append('/'.join(imgparts[:-1]) + '/' + img + ':' + tag)
else:
	manifest_content[0]['RepoTags'].append(img + ':' + tag)

empty_json = '{"created":"1970-01-01T00:00:00Z","container_config":{"Hostname":"","Domainname":"","User":"","AttachStdin":false, \
	"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false, "StdinOnce":false,"Env":null,"Cmd":null,"Image":"", \
	"Volumes":null,"WorkingDir":"","Entrypoint":null,"OnBuild":null,"Labels":null}}'

# Ensure all variables are properly initialized before use
if layers is None or config is None or confresp is None:
	print('[-] Error: Required manifest data not properly initialized')
	exit(1)

# Build layer folders with concurrent downloads
print(f'[+] Starting concurrent download of {len(layers)} layers (max concurrent: {max_concurrent_downloads})')

# Download layers concurrently
download_results = []
with ThreadPoolExecutor(max_workers=max_concurrent_downloads) as executor:
	# Submit all download tasks
	future_to_layer = {}
	parentid = ''
	for i, layer in enumerate(layers):
		# Calculate parentid for this layer (based on previous layers)
		temp_parentid = ''
		for j in range(i):
			temp_ublob = layers[j]['digest']
			temp_fake_layerid = hashlib.sha256((temp_parentid+'\n'+temp_ublob+'\n').encode('utf-8')).hexdigest()
			temp_parentid = temp_fake_layerid
		
		future = executor.submit(download_layer, layer, imgdir, temp_parentid)
		future_to_layer[future] = (i, layer)
	
	# Collect results as they complete
	for future in as_completed(future_to_layer):
		layer_index, layer = future_to_layer[future]
		try:
			result = future.result()
			if result is None:
				print('[-] Failed to download layer')
				exit(1)
			download_results.append((layer_index, result))
		except Exception as exc:
			print(f'[-] Layer download generated an exception: {exc}')
			exit(1)

# Sort results by layer index to maintain order
download_results.sort(key=lambda x: x[0])

# Add layers to content in correct order and create JSON files
parentid = ''
for layer_index, result in download_results:
	manifest_content[0]['Layers'].append(result['fake_layerid'] + '/layer.tar')
	
	# Creating json file for each layer
	layerdir = result['layerdir']
	layer = result['layer']
	fake_layerid = result['fake_layerid']
	
	file = open(layerdir + '/json', 'w')
	# last layer = config manifest - history - rootfs
	if layers[-1]['digest'] == layer['digest']:
		# FIXME: json.loads() automatically converts to unicode, thus decoding values whereas Docker doesn't
		if hasattr(confresp, 'content'):
			json_obj = json.loads(confresp.content)
		else:
			json_obj = json.loads(empty_json)
		if 'history' in json_obj:
			del json_obj['history']
		if 'rootfs' in json_obj:
			del json_obj['rootfs']
		elif 'rootfS' in json_obj: # Because Microsoft loves case insensitiveness
			del json_obj['rootfS']
	else: # other layers json are empty
		json_obj = json.loads(empty_json)
	json_obj['id'] = fake_layerid
	if parentid:
		json_obj['parent'] = parentid
	parentid = json_obj['id']
	file.write(json.dumps(json_obj))
	file.close()

file = open(imgdir + '/manifest.json', 'w')
file.write(json.dumps(manifest_content))
file.close()

if len(imgparts[:-1]) != 0:
    repo_content = { '/'.join(imgparts[:-1]) + '/' + img : { tag : parentid } }
else: # when pulling only an img (without repo and registry)
    repo_content = { img : { tag : parentid } }
file = open(imgdir + '/repositories', 'w')
file.write(json.dumps(repo_content))
file.close()

# Create image tar and clean tmp folder
docker_tar = repo.replace('/', '_') + '_' + img + '.tar'
sys.stdout.write("Creating archive...")
sys.stdout.flush()
tar = tarfile.open(docker_tar, "w")
tar.add(imgdir, arcname=os.path.sep)
tar.close()
shutil.rmtree(imgdir)
print('\rDocker image pulled: ' + docker_tar)
