<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README_CN.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
</p>

# Docker Pull Script

A Docker image download tool that doesn't require Docker environment, supporting multi-platform, concurrent downloads, intelligent caching (layer incremental updates), and authentication login.

> Note: This tool is only for downloading images, does not support building or running containers.
> You can directly download pre-compiled binary files from the release page without installing Python environment.
> Supports Windows, macOS, Linux systems.

## 🚀 Features

### Core Features
- **Multi-platform Support**: Automatically identifies and downloads specified platform images (linux/amd64, linux/arm64, linux/arm/v7, etc.)
- **Concurrent Downloads**: Multi-threaded simultaneous download of image layers, 30-50% speed improvement
- **Intelligent Caching**: SHA256-based layer caching system, incremental updates save bandwidth
- **Memory Optimization**: Streaming downloads, 90% reduction in memory usage
- **Network Retry**: Intelligent retry mechanism, automatic recovery from network interruptions
- **Progress Display**: Real-time display of download speed, progress percentage, and remaining time
- **Authentication Support**: Docker login authentication, supports private image sources
- **Import Feature**: Support importing layers from existing Docker tar files to cache, improving cache hit rates

### Supported Image Sources
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** Private Registry
- ✅ **Quay.io**
- ✅ **Alibaba Cloud ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **OCI Compatible Registries** (supports OCI image index format)

## 📦 Installation and Usage

### System Requirements
- Python 3.6+
- requests library

### Install Dependencies
```bash
pip install requests
```

### Basic Commands
```bash
python docker_pull.py [image_name] [options]
```

### Caching Features
- **Auto Caching**: Downloaded layers are automatically cached to `./docker_images_cache/`
- **Incremental Updates**: Automatically reuse cached layers on repeat downloads
- **Cross-image Sharing**: Same layers from different images can share cache
- **Cache Statistics**: Display cache hit rate and data saved
- **Tar File Import**: Support importing layers from existing Docker tar files to cache, preheating cache system

## 🔧 Usage Examples

### 1. Basic Usage

#### Download Public Images
```bash
# Download latest nginx
python docker_pull.py nginx:latest

# Download specific platform image
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# Custom concurrency
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# Disable caching
python docker_pull.py nginx:latest --no-cache

# Custom cache directory
python docker_pull.py nginx:latest --cache-dir /path/to/cache

# Import layers from existing Docker tar file to cache
python docker_pull.py --import-tar existing_image.tar

# Use standalone import tool
python import_tar.py existing_image.tar --cache-dir /path/to/cache
```

#### Download Private Images (Login Authentication)
```bash
# Docker Hub login
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# Private Harbor registry
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# Use environment variables (more secure)
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. Platform Support

Supported platform formats:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32-bit)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. Complete Command Line Arguments

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      [--import-tar IMPORT_TAR]
                      image

Arguments:
- image: Docker image name [registry/][repository/]image[:tag|@digest]
- --platform: Target platform (linux/amd64, linux/arm64, linux/arm/v7, etc.)
- --max-concurrent-downloads: Maximum concurrent download layers (default: 3)
- --username: Username (for private image source authentication)
- --password: Password (for private image source authentication)
- --cache-dir: Layer cache directory (default: ./docker_images_cache)
- --no-cache: Disable layer caching feature
- --import-tar: Import layers from existing Docker tar file to cache
```

## 📊 Performance Comparison

### Concurrent Download Performance
| Download Method | Time | Performance Improvement |
|-----------------|------|------------------------|
| Sequential Download (1 thread) | 43.97s | Baseline |
| **Concurrent Download (3 threads)** | **28.08s** | **36.1%** |
| Concurrent Download (5 threads) | 18.91s | 57.0% |

### Cache Feature Effects
| Scenario | First Download | Repeat Download | Cache Hit Rate | Data Saved |
|----------|----------------|-----------------|----------------|------------|
| nginx:1.21.0 (6 layers) | Normal speed | Instant completion | 100% | 131MB |
| Similar version images | Partial cache | Significant acceleration | 60-80% | 50-100MB |

## 🎯 Real-world Use Cases

### Scenario 1: Cross-platform Downloads
```bash
# Prepare images for ARM devices on x86 server
python docker_pull.py --platform linux/arm64 nginx:latest
# Generates nginx_arm64.tar, can be transferred to ARM device for import
```

### Scenario 2: CI/CD Integration
```bash
# GitHub Actions example
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### Scenario 3: Private Registry Management
```bash
# Batch download different platform images
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### Scenario 4: Development Environment Optimization
```bash
# First download base image
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# Download related image, automatically reuse base layers
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# Repeat download, 100% cache hit
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

### Scenario 5: Cache Preheating
```bash
# Import layers from existing Docker tar file to cache
python docker_pull.py --import-tar nginx_latest.tar
# 🔄 Starting import of Docker tar file to cache: nginx_latest.tar
# ✅ Successfully imported: 6 layers, 💾 Import data: 131.0 MB

# Or use standalone import tool
python import_tar.py existing_image.tar
# Support batch import of multiple tar files to preheat cache
```

## 🔐 Authentication Configuration

### Supported Authentication Methods
| Image Source | Authentication Method | Example |
|--------------|----------------------|----------|
| Docker Hub | Username/Password | `--username dockerhubuser --password dockerhubpass` |
| Harbor | Username/Password | `--username harboruser --password harborpass` |
| ECR | Username/Password | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | Username/Password | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### Security Recommendations
```bash
# Recommended: Use environment variables
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# Not recommended: Direct password in command line
python docker_pull.py image --username user --password pass  # Insecure
```

## 🛠️ Troubleshooting

### Common Issues and Solutions

#### Authentication Failure
```bash
# Error: 401 Unauthorized
# Solution: Check if username and password are correct
python docker_pull.py private-image --username user --password pass

# Error: 403 Forbidden
# Solution: Check user permissions
```

#### Platform Mismatch
```bash
# Error: Platform mismatch
# Solution: View available platform list
python docker_pull.py image --platform invalid
# Script will display all available platforms
```

#### Network Issues
```bash
# Set proxy
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### Error Code Descriptions
- **401**: Authentication required or authentication failed
- **403**: Insufficient permissions
- **404**: Image does not exist
- **429**: Rate limit exceeded

## 📋 Output Files

After download completion, generates standard Docker tar files:
- **Filename**: `{registry}_{repository}_{image}_{tag}.tar`
- **Format**: 100% compatible with `docker load` command
- **Size**: Consistent with official images
- **Example**: `docker load < library_nginx.tar`

## Changelog

### v3.0 (Current Version) - Intelligent Caching Version
- 🆕 **Intelligent Layer Caching System**: Global layer management based on SHA256
- 🆕 **Incremental Updates**: Automatically reuse downloaded layers, save bandwidth
- 🆕 **Cache Statistics**: Display cache hit rate and data saved
- 🆕 **OCI Format Support**: Full support for OCI image index format
- 🆕 **Alibaba Cloud ACR Support**: Support for Alibaba Cloud Container Registry
- ✅ Hard link optimization for storage space
- ✅ Cross-image layer sharing

### v2.0
- ✅ Added Docker login authentication support
- ✅ Support for all mainstream image sources
- ✅ 90% memory usage optimization
- ✅ Enhanced error handling
- ✅ Improved progress display

### v1.5
- ✅ Added concurrent download feature
- ✅ Multi-platform image support
- ✅ Performance optimization

### v1.0
- ✅ Basic image download functionality

## License
MIT License - Free to use, modify and distribute

---

**Quick Start:**
```bash
# View help
python docker_pull.py --help

# Download image (auto cache)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# Repeat download (cache hit)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# Import existing tar file to cache
python docker_pull.py --import-tar existing_image.tar
# 🔄 Starting import of Docker tar file to cache...

# View cache directory
ls -la docker_images_cache/layers/
```