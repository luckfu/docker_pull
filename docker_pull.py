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
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Optional, Dict, Any
import urllib.parse
from pathlib import Path
urllib3.disable_warnings()

# 全局变量用于优雅退出
shutdown_event = threading.Event()
executor = None

def signal_handler(signum, frame):
    """处理Ctrl+C信号"""
    print("\n\n⚠️  接收到中断信号，正在优雅退出...")
    print("📋 清理下载任务和临时文件...")
    
    # 设置关闭事件
    shutdown_event.set()
    
    # 关闭线程池
    if executor:
        print("🔄 等待下载任务完成...")
        executor.shutdown(wait=False)
    
    print("✅ 清理完成，程序退出")
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

# 版本和版权信息
__version__ = "1.24"
__author__ = "luckfu"
__copyright__ = "Copyright © 2024 luckfu"
__license__ = "MIT"
__url__ = "https://github.com/luckfu/docker_pull"

def show_version():
    """显示版本和版权信息"""
    print(f"Docker Pull v{__version__}")
    print(f"Docker镜像下载工具，支持多平台、并发下载、智能缓存")
    print(f"{__copyright__}")
    print(f"开源项目: {__url__}")
    print(f"许可证: {__license__}")
    print()

def show_banner():
    """显示启动横幅"""
    print("="*60)
    print(f"🐳 Docker Pull v{__version__} - Docke容器镜像下载工具")
    print(f"📦 来自开源项目: {__url__}")
    print(f"⚡ 支持多平台、并发下载、智能缓存")
    print("="*60)
    print()

# Parse command line arguments
parser = argparse.ArgumentParser(
    description='不需要Docker环境的镜像下载工具，支持多平台、并发下载、智能缓存',
    epilog=f'开源项目: {__url__}',
    formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument('image', nargs='?', help='[registry/][repository/]image[:tag|@digest]')
parser.add_argument('--platform', help='Target platform (e.g., linux/amd64, linux/arm64, linux/arm/v7)')
parser.add_argument('--max-concurrent-downloads', type=int, default=3, help='Maximum number of concurrent layer downloads (default: 3)')
parser.add_argument('--username', help='Username for registry authentication (supports Docker Hub, GCR, ECR, Harbor, etc.)')
parser.add_argument('--password', help='Password for registry authentication')
parser.add_argument('--cache-dir', help='Layer cache directory (default: ./docker_images_cache)', default=None)
parser.add_argument('--no-cache', action='store_true', help='Disable layer caching')
parser.add_argument('--import-tar', help='Import layers from existing Docker tar file to cache')
parser.add_argument('--version', action='store_true', help='Show version information and exit')
args = parser.parse_args()

# 处理版本信息显示
if args.version:
    show_version()
    sys.exit(0)

# 检查是否提供了镜像参数或导入tar文件
if not args.image and not args.import_tar:
    show_banner()
    parser.print_help()
    print(f"\n💡 示例用法:")
    print(f"   python docker_pull.py nginx:latest")
    print(f"   python docker_pull.py --platform linux/arm64 ubuntu:20.04")
    print(f"   python docker_pull.py --import-tar xxx.tar")
    print(f"   python docker_pull.py --version")
    sys.exit(1)

# 处理导入tar文件功能（提前处理以避免执行镜像下载逻辑）
if args.import_tar:
    # 设置缓存相关变量
    if args.cache_dir:
        cache_dir = Path(args.cache_dir).expanduser().resolve()
    else:
        cache_dir = Path.cwd() / 'docker_images_cache'
    
    layers_cache_dir = cache_dir / 'layers'
    use_cache = True  # 导入功能需要启用缓存
    
    print(f"\n🔄 Docker tar文件导入模式")
    # 跳转到函数定义后的导入处理
    import_tar_file = args.import_tar
else:
    import_tar_file = None

# 显示启动横幅（仅在非导入模式下）
if not args.import_tar:
    show_banner()

# 导入tar文件功能将在缓存函数定义后处理

# 只有在非导入模式下才执行镜像下载逻辑
if not args.import_tar:
    image_arg = args.image
    target_platform = args.platform
    max_concurrent_downloads = args.max_concurrent_downloads

    # Layer cache configuration
    use_cache = not args.no_cache
    if args.cache_dir:
        cache_dir = Path(args.cache_dir).expanduser().resolve()
    else:
        cache_dir = Path.cwd() / 'docker_images_cache'

    layers_cache_dir = cache_dir / 'layers'
    manifests_cache_dir = cache_dir / 'manifests'

    # Initialize cache directories
    if use_cache:
        layers_cache_dir.mkdir(parents=True, exist_ok=True)
        manifests_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Using layer cache: {cache_dir}")
    else:
        print("Layer caching disabled")

    # Thread-safe progress tracking
    progress_lock = threading.Lock()
    download_progress = {}
    cache_stats = {'hits': 0, 'misses': 0, 'bytes_saved': 0}

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

def get_auth_head(type_var, registry=None, repository=None, username=None, password=None, auth_url=None, reg_service=None):
    """Get authentication header for Docker registry requests"""
    header = {'Accept': type_var}
    
    # If username and password are provided, use basic auth first
    if username and password:
        # Use basic authentication for private registries
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        header['Authorization'] = f'Basic {credentials}'
        return header
    
    # Try token auth if we have auth_url and reg_service (from registry probing or known endpoints)
    if registry and auth_url and reg_service:
        try:
            token_url = f"{auth_url}?service={reg_service}&scope=repository:{repository}:pull"
            
            resp = requests.get(token_url, verify=False, timeout=10)
            
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
    
    # For registries without token auth configuration, just return basic header
    return header

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

# Initialize variables for image download mode
if not args.import_tar:
    image_arg = args.image
    target_platform = args.platform
    max_concurrent_downloads = args.max_concurrent_downloads

    # Cache configuration
    use_cache = not args.no_cache
    if args.cache_dir:
        cache_dir = Path(args.cache_dir).expanduser().resolve()
    else:
        cache_dir = Path.cwd() / 'docker_images_cache'

    layers_cache_dir = cache_dir / 'layers'
    manifests_cache_dir = cache_dir / 'manifests'

    # Create cache directories if caching is enabled
    if use_cache:
        layers_cache_dir.mkdir(parents=True, exist_ok=True)
        manifests_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Using layer cache: {cache_dir}")
    else:
        print("Layer caching disabled")

    # Initialize progress tracking
    progress_lock = threading.Lock()
    download_progress = {}
    cache_stats = {'hits': 0, 'misses': 0, 'bytes_saved': 0}

    # Initialize HTTP session
    session = requests.Session()
    session.headers.update({'User-Agent': 'Docker-Pull-Script/1.0'})

    # Authentication configuration
    username = args.username
    password = args.password

    # Print authentication status
    if username and password:
        print(f"Using authentication for user: {username}")
    elif username or password:
        print("Warning: Both username and password are required for authentication")
    else:
        print("Using anonymous access (no credentials provided)")

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
        },
        'registry.cn-shanghai.aliyuncs.com': {
            'auth_url': 'https://dockerauth.cn-hangzhou.aliyuncs.com/auth',
            'service': 'registry.aliyuncs.com:cn-shanghai:26842'
        },
        'registry.cn-beijing.aliyuncs.com': {
            'auth_url': 'https://registry.cn-beijing.aliyuncs.com/v2/token',
            'service': 'registry.cn-beijing.aliyuncs.com'
        },
        'registry.cn-hangzhou.aliyuncs.com': {
            'auth_url': 'https://dockerauth.cn-hangzhou.aliyuncs.com/auth',
            'service': 'registry.aliyuncs.com:cn-hangzhou:26842'
        }
    }

    # Check if we have a known registry
    if registry in registry_auth_endpoints:
        auth_url = registry_auth_endpoints[registry]['auth_url']
        reg_service = registry_auth_endpoints[registry]['service']
    else:
        # For private registries, don't probe for authentication unless necessary
        # Only probe if we don't have credentials
        if not (username and password):
            try:
                # Probe for authentication endpoint
                resp = requests.get(f'https://{registry}/v2/', verify=False, timeout=10)
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
                elif resp.status_code == 200:
                    # Registry allows anonymous access
                    print(f"Registry {registry} allows anonymous access")
            except Exception as e:
                print(f"Warning: Could not probe registry {registry}: {e}")
                # Continue with basic authentication if credentials are provided

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

# Layer cache management functions
def get_layer_cache_path(layer_digest: str) -> Path:
    """Get the cache path for a layer based on its digest"""
    return layers_cache_dir / layer_digest.replace(':', '_')

def check_layer_cache(layer_digest: str) -> Optional[Path]:
    """Check if a layer exists in cache and is valid"""
    if not use_cache:
        return None
    
    cache_path = get_layer_cache_path(layer_digest)
    layer_file = cache_path / 'layer.tar'
    
    if layer_file.exists():
        # Update access time for LRU
        cache_path.touch()
        return cache_path
    return None

def save_layer_to_cache(layer_digest: str, layer_tar_path: str) -> bool:
    """Save a downloaded layer to cache"""
    if not use_cache:
        return False
    
    try:
        cache_path = get_layer_cache_path(layer_digest)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Create hard link to save space
        cache_layer_file = cache_path / 'layer.tar'
        if not cache_layer_file.exists():
            os.link(layer_tar_path, cache_layer_file)
        
        # Save metadata
        metadata = {
            'digest': layer_digest,
            'size': os.path.getsize(layer_tar_path),
            'cached_at': time.time()
        }
        with open(cache_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
        
        return True
    except Exception as e:
        print(f"Warning: Failed to cache layer {layer_digest[7:19]}: {e}")
        return False

def use_cached_layer(cache_path: Path, target_dir: str, layer_digest: str) -> bool:
    """Use a cached layer by creating hard link"""
    try:
        cached_layer = cache_path / 'layer.tar'
        target_layer = target_dir + '/layer.tar'
        
        # Create hard link to reuse cached layer
        os.link(cached_layer, target_layer)
        
        # Update cache stats
        with progress_lock:
            cache_stats['hits'] += 1
            if (cache_path / 'metadata.json').exists():
                with open(cache_path / 'metadata.json', 'r') as f:
                    metadata = json.load(f)
                    cache_stats['bytes_saved'] += metadata.get('size', 0)
        
        return True
    except Exception as e:
        print(f"Warning: Failed to use cached layer {layer_digest[7:19]}: {e}")
        return False

def calculate_layer_digest(layer_tar_path: str) -> str:
    """Calculate SHA256 digest of a layer tar file"""
    sha256_hash = hashlib.sha256()
    with open(layer_tar_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return f"sha256:{sha256_hash.hexdigest()}"

def import_docker_tar_to_cache(tar_file_path: str):
    """Import layers from a Docker tar file to cache"""
    print(f"🔄 开始导入Docker tar文件到缓存: {tar_file_path}")
    
    if not os.path.exists(tar_file_path):
        print(f"❌ 错误: 文件不存在 {tar_file_path}")
        return
    
    # 确保缓存目录存在
    layers_cache_dir.mkdir(parents=True, exist_ok=True)
    
    imported_count = 0
    skipped_count = 0
    total_size = 0
    temp_dir = Path('temp_docker_import')
    
    try:
        with tarfile.open(tar_file_path, 'r') as tar:
            # 提取到临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir()
            
            print("📦 解压Docker tar文件...")
            tar.extractall(temp_dir)
            
            # 查找manifest.json文件
            manifest_files = list(temp_dir.glob('**/manifest.json'))
            if not manifest_files:
                print("❌ 错误: 在Docker tar文件中未找到manifest.json")
                return
            
            manifest_file = manifest_files[0]
            with open(manifest_file, 'r') as f:
                manifest_data = json.load(f)
            
            print(f"📋 找到 {len(manifest_data)} 个镜像清单")
            
            # 处理每个镜像的layers
            for image_manifest in manifest_data:
                if 'Layers' not in image_manifest:
                    continue
                    
                repo_tags = image_manifest.get('RepoTags', ['unknown:latest'])
                print(f"\n🏷️  处理镜像: {', '.join(repo_tags)}")
                
                layers = image_manifest['Layers']
                print(f"📦 发现 {len(layers)} 个层")
                
                for layer_path in layers:
                    full_layer_path = temp_dir / layer_path
                    if not full_layer_path.exists():
                        print(f"⚠️  警告: 层文件不存在 {layer_path}")
                        continue
                    
                    # 计算层的digest
                    print(f"🔍 计算层digest: {layer_path}")
                    layer_digest = calculate_layer_digest(str(full_layer_path))
                    
                    # 检查是否已经在缓存中
                    if check_layer_cache(layer_digest):
                        print(f"⏭️  跳过已缓存的层: {layer_digest[7:19]}")
                        skipped_count += 1
                        continue
                    
                    # 导入到缓存
                    layer_size = full_layer_path.stat().st_size
                    if save_layer_to_cache(layer_digest, str(full_layer_path)):
                        print(f"✅ 成功导入层: {layer_digest[7:19]} ({format_speed(layer_size)})")
                        imported_count += 1
                        total_size += layer_size
                    else:
                        print(f"❌ 导入层失败: {layer_digest[7:19]}")
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
    except Exception as e:
        print(f"❌ 导入过程中发生错误: {e}")
        # 清理临时目录
        if 'temp_dir' in locals() and temp_dir.exists():
            shutil.rmtree(temp_dir)
        return
    
    # 显示导入统计
    print(f"\n📊 导入完成统计:")
    print(f"   ✅ 成功导入: {imported_count} 个层")
    print(f"   ⏭️  跳过已存在: {skipped_count} 个层")
    if total_size > 0:
        if total_size >= 1024 * 1024 * 1024:
            print(f"   💾 导入数据量: {total_size/(1024*1024*1024):.1f} GB")
        else:
            print(f"   💾 导入数据量: {total_size/(1024*1024):.1f} MB")
    print(f"   📁 缓存位置: {layers_cache_dir}")
    print(f"\n🎉 Docker tar文件导入完成！")

# 处理导入tar文件功能（在函数定义后立即处理）
if args.import_tar:
    import_docker_tar_to_cache(args.import_tar)
    sys.exit(0)
else:
    # 只有在非导入模式下才定义和执行镜像下载相关的函数和逻辑
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
        # 检查是否收到中断信号
        if shutdown_event.is_set():
            raise KeyboardInterrupt("Download interrupted by user")
        
        ublob = layer['digest']
        fake_layerid = hashlib.sha256((parentid+'\n'+ublob+'\n').encode('utf-8')).hexdigest()
        layerdir = imgdir + '/' + fake_layerid
        os.makedirs(layerdir, exist_ok=True)

        # Create VERSION file
        with open(layerdir + '/VERSION', 'w') as f:
            f.write('1.0')

        # Check cache first
        cache_path = check_layer_cache(ublob)
        if cache_path:
            with progress_lock:
                # 显示缓存使用的进度条
                sys.stdout.write(f'\r{ublob[7:19]}: |{"█" * 30}| 100.0% (cached)')
                sys.stdout.flush()
                print(f'\n{ublob[7:19]}: Using cached layer')
            if use_cached_layer(cache_path, layerdir, ublob):
                return {'fake_layerid': fake_layerid, 'layer': layer, 'layerdir': layerdir}
            else:
                with progress_lock:
                    print(f'{ublob[7:19]}: Cache failed, downloading...')
        
        # Update cache miss stats
        with progress_lock:
            cache_stats['misses'] += 1
            # 显示开始下载的进度条
            sys.stdout.write(f'\r{ublob[7:19]}: |{" " * 30}|   0.0% (starting...)')
            sys.stdout.flush()

        start_time = time.time()

        auth_head = get_auth_head('application/vnd.docker.distribution.manifest.v2+json', registry, repository, username, password, auth_url, reg_service)

        # Try primary URL first, then fallback URLs
        urls = [f'https://{registry}/v2/{repository}/blobs/{ublob}']
        if 'urls' in layer and layer['urls']:
            urls.extend(layer['urls'])

        bresp = None
        for url in urls:
            try:
                # 检查中断信号
                if shutdown_event.is_set():
                    raise KeyboardInterrupt("Download interrupted by user")
                    
                bresp = session.get(url, headers=auth_head, stream=True, verify=False, timeout=30)
                if bresp.status_code == 200:
                    break
            except KeyboardInterrupt:
                raise
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

        try:
            # Stream directly to file without loading entire content in memory
            with open(layerdir + '/layer_gzip.tar', 'wb') as file:
                for chunk in bresp.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    # 检查中断信号
                    if shutdown_event.is_set():
                        bresp.close()
                        raise KeyboardInterrupt("Download interrupted by user")
                        
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
                # 显示最终完成的进度条
                if content_length:
                    sys.stdout.write(f'\r{ublob[7:19]}: |{"█" * 30}| 100.0% ({format_speed(downloaded)})')
                else:
                    sys.stdout.write(f'\r{ublob[7:19]}: |{"█" * 30}| 100.0% ({format_speed(downloaded)})')
                sys.stdout.flush()
                print(f'\n{ublob[7:19]}: Download complete')
                print(f'{ublob[7:19]}: Extracting...')

            # Stream decompress to avoid memory issues
            with open(layerdir + '/layer.tar', 'wb') as out_file:
                with gzip.open(layerdir + '/layer_gzip.tar', 'rb') as gz_file:
                    shutil.copyfileobj(gz_file, out_file)  # type: ignore

            os.remove(layerdir + '/layer_gzip.tar')
            
            # Save to cache after successful download and extraction
            layer_tar_path = layerdir + '/layer.tar'
            if save_layer_to_cache(ublob, layer_tar_path):
                with progress_lock:
                    print(f'{ublob[7:19]}: Cached for future use')
            
            return {'fake_layerid': fake_layerid, 'layer': layer, 'layerdir': layerdir}
            
        except KeyboardInterrupt:
            # 清理部分下载的文件
            if os.path.exists(layerdir + '/layer_gzip.tar'):
                os.remove(layerdir + '/layer_gzip.tar')
            if os.path.exists(layerdir + '/layer.tar'):
                os.remove(layerdir + '/layer.tar')
            raise
        except Exception as e:
            # 清理部分下载的文件
            if os.path.exists(layerdir + '/layer_gzip.tar'):
                os.remove(layerdir + '/layer_gzip.tar')
            if os.path.exists(layerdir + '/layer.tar'):
                os.remove(layerdir + '/layer.tar')
            raise RetryError(f'Error downloading layer {ublob[7:19]}: {str(e)}')

    # Main execution continues...
    # Get Docker authentication
    # Support multiple manifest formats including OCI index
    accept_types = [
        'application/vnd.oci.image.index.v1+json',
        'application/vnd.oci.image.manifest.v1+json',
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.docker.distribution.manifest.v2+json',
        'application/vnd.docker.distribution.manifest.v1+json'
    ]
    auth_head = get_auth_head(', '.join(accept_types), registry, repository, username, password, auth_url, reg_service)

    # Get manifest
    try:
        resp = requests.get('https://{}/v2/{}/manifests/{}'.format(registry, repository, tag), headers=auth_head, verify=False, timeout=30)
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
    except KeyboardInterrupt:
        print('\n⚠️  获取镜像清单时被用户中断')
        sys.exit(0)
    except requests.exceptions.RequestException as e:
        print(f'Network error fetching manifest: {e}')
        exit(1)

    manifest = resp.json()

    # Debug: Print manifest structure to understand the format
    print(f"Manifest keys: {list(manifest.keys())}")
    if 'mediaType' in manifest:
        print(f"Media type: {manifest['mediaType']}")

    # Handle multi-platform manifests (both Docker and OCI formats)
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
                print(f"Platform manifest digest: {digest}")
                
                # Fetch the actual manifest for this platform
                manifest_url = 'https://{}/v2/{}/manifests/{}'.format(registry, repository, digest)
                print(f"Fetching platform manifest from: {manifest_url}")
                auth_head = get_auth_head(', '.join(accept_types), registry, repository, username, password, auth_url, reg_service)
                resp = requests.get(manifest_url, headers=auth_head, verify=False)
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

    # Handle case where no platform is specified but manifest is multi-platform
    if not target_platform and 'manifests' in manifest:
        print('Multi-platform image detected. Available platforms:')
        image_manifests = []
        last_platform_str = ""
        for m in manifest['manifests']:
            # Skip attestation manifests and other non-image manifests
            annotations = m.get('annotations', {})
            if annotations.get('vnd.docker.reference.type') == 'attestation-manifest':
                continue
            
            platform = m.get('platform', {})
            platform_str = f"{platform.get('os', 'linux')}/{platform.get('architecture', 'amd64')}"
            if platform.get('variant'):
                platform_str += f"/{platform.get('variant')}"
            print(f"  - {platform_str}")
            image_manifests.append(m)
            last_platform_str = platform_str
        
        if len(image_manifests) == 1:
            # Only one actual image manifest, use it directly
            print(f"Using the only available platform: {last_platform_str}")
            selected_manifest = image_manifests[0]
            # We need to fetch the actual manifest content
            digest = selected_manifest['digest']
            manifest_url = 'https://{}/v2/{}/manifests/{}'.format(registry, repository, digest)
            print(f"Fetching manifest from: {manifest_url}")
            auth_head = get_auth_head(', '.join(accept_types), registry, repository, username, password, auth_url, reg_service)
            resp = requests.get(manifest_url, headers=auth_head, verify=False)
            if resp.status_code != 200:
                print('Cannot fetch manifest [HTTP {}]'.format(resp.status_code))
                print(f'Response: {resp.content}')
                exit(1)
            manifest = resp.json()
        else:
            print('Please specify a platform using --platform argument')
            exit(1)

    # Create image directory
    imgdir = 'docker_{}_{}'.format(img, tag.replace(':', '_').replace('@', '_'))
    if os.path.exists(imgdir):
        shutil.rmtree(imgdir)
    os.makedirs(imgdir)

    # Extract layers from manifest
    if 'layers' in manifest:
        layers = manifest['layers']
    else:
        print('Error: No layers found in manifest')
        print(f'Manifest content: {manifest}')
        exit(1)

    # Create repositories file
    repositories = '{{"{}":{{"{}":"{}"}}}}'.format(repo, img, tag)
    with open(imgdir + '/repositories', 'w') as f:
        f.write(repositories)

    # Download layers concurrently
    print('Downloading {} layers...'.format(len(layers)))
    print('💡 提示: 按 Ctrl+C 可以随时中断下载\n')

    try:
        with ThreadPoolExecutor(max_workers=max_concurrent_downloads) as thread_executor:
            executor = thread_executor
            
            future_to_layer = {thread_executor.submit(download_layer, layer, imgdir, 'sha256:' + hashlib.sha256(''.encode()).hexdigest()): layer for layer in layers}

            for future in as_completed(future_to_layer):
                # 检查中断信号
                if shutdown_event.is_set():
                    print('\n⚠️  下载已被用户中断')
                    break
                    
                layer = future_to_layer[future]
                try:
                    result = future.result()
                    if result:
                        print('{}: Layer {} completed'.format(result['fake_layerid'][:12], result['layer']['digest'][7:19]))
                    else:
                        print('ERROR: Failed to download layer {}'.format(layer['digest'][7:19]))
                except KeyboardInterrupt:
                    print('\n⚠️  下载被用户中断')
                    break
                except Exception as e:
                    print('ERROR: Exception downloading layer {}: {}'.format(layer['digest'][7:19], str(e)))
            
            # 清除全局executor引用
            executor = None
            
    except KeyboardInterrupt:
        print('\n\n⚠️  下载被用户中断，正在清理...')
        # 清理临时目录
        if os.path.exists(imgdir):
            shutil.rmtree(imgdir)
            print(f'🗑️  已清理临时目录: {imgdir}')
        print('✅ 清理完成，程序退出')
        sys.exit(0)

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
    auth_head = get_auth_head('application/vnd.docker.container.image.v1+json', registry, repository, username, password, auth_url, reg_service)
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
    print(f'\n🎉 下载完成！感谢使用 Docker Pull v{__version__}')
    print(f'📦 开源项目: {__url__}')

    # Display cache statistics
    if use_cache and (cache_stats['hits'] > 0 or cache_stats['misses'] > 0):
        total_layers = cache_stats['hits'] + cache_stats['misses']
        hit_rate = (cache_stats['hits'] / total_layers * 100) if total_layers > 0 else 0
        saved_mb = cache_stats['bytes_saved'] / (1024 * 1024)
        print(f"\n💾 Cache Statistics:")
        print(f"   Cache hits: {cache_stats['hits']}/{total_layers} layers ({hit_rate:.1f}%)")
        if cache_stats['bytes_saved'] > 0:
            if saved_mb >= 1024:
                print(f"   Data saved: {saved_mb/1024:.1f} GB")
            else:
                print(f"   Data saved: {saved_mb:.1f} MB")
        print(f"   Cache location: {cache_dir}")