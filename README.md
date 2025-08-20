# Docker Pull Script

高性能Docker镜像下载工具，支持多平台、并发下载、智能缓存、认证登录。

## 🚀 功能特性

### 核心功能
- **多平台支持**: 自动识别并下载指定平台镜像（linux/amd64, linux/arm64, linux/arm/v7等）
- **并发下载**: 多线程同时下载镜像层，速度提升30-50%
- **智能缓存**: 基于SHA256的层缓存系统，增量更新节省带宽
- **内存优化**: 流式下载，内存占用减少90%
- **网络重试**: 智能重试机制，网络中断自动恢复
- **进度显示**: 实时显示下载速度、进度百分比和剩余时间
- **认证支持**: Docker登录认证，支持私有镜像源

### 支持的镜像源
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** 私有仓库
- ✅ **Quay.io**
- ✅ **阿里云ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **OCI兼容注册表** (支持OCI镜像索引格式)

## 📦 安装使用

### 系统要求
- Python 3.6+
- requests库

### 安装依赖
```bash
pip install requests
```

### 基本命令
```bash
python docker_pull.py [镜像名] [选项]
```

### 缓存功能
- **自动缓存**: 下载的层自动缓存到 `./docker_images_cache/`
- **增量更新**: 重复下载时自动复用已缓存的层
- **跨镜像共享**: 不同镜像的相同层可以共享缓存
- **缓存统计**: 显示缓存命中率和节省的数据量

## 🔧 使用示例

### 1. 基础使用

#### 下载公共镜像
```bash
# 下载最新版nginx
python docker_pull.py nginx:latest

# 下载指定平台镜像
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# 自定义并发数
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# 禁用缓存
python docker_pull.py nginx:latest --no-cache

# 自定义缓存目录
python docker_pull.py nginx:latest --cache-dir /path/to/cache
```

#### 下载私有镜像（登录认证）
```bash
# Docker Hub登录
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# 私有Harbor仓库
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# 使用环境变量（更安全）
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. 平台支持

支持的平台格式：
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32位)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. 完整命令行参数

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      image

参数说明：
- image: Docker镜像名称 [registry/][repository/]image[:tag|@digest]
- --platform: 目标平台 (linux/amd64, linux/arm64, linux/arm/v7等)
- --max-concurrent-downloads: 最大并发下载层数 (默认: 3)
- --username: 用户名（私有镜像源认证）
- --password: 密码（私有镜像源认证）
- --cache-dir: 层缓存目录 (默认: ./docker_images_cache)
- --no-cache: 禁用层缓存功能
```

## 📊 性能对比

### 并发下载性能
| 下载方式 | 耗时 | 性能提升 |
|----------|------|----------|
| 顺序下载（1线程） | 43.97秒 | 基准 |
| **并发下载（3线程）** | **28.08秒** | **36.1%** |
| 并发下载（5线程） | 18.91秒 | 57.0% |

### 缓存功能效果
| 场景 | 首次下载 | 重复下载 | 缓存命中率 | 节省数据 |
|------|----------|----------|------------|----------|
| nginx:1.21.0 (6层) | 正常速度 | 瞬间完成 | 100% | 131MB |
| 相似版本镜像 | 部分缓存 | 显著加速 | 60-80% | 50-100MB |

## 🎯 实际使用场景

### 场景1：跨平台下载
```bash
# 在x86服务器上为ARM设备准备镜像
python docker_pull.py --platform linux/arm64 nginx:latest
# 生成 nginx_arm64.tar，可传输到ARM设备导入
```

### 场景2：CI/CD集成
```bash
# GitHub Actions示例
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### 场景3：私有仓库管理
```bash
# 批量下载不同平台镜像
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### 场景4：开发环境优化
```bash
# 首次下载基础镜像
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# 下载相关镜像，自动复用基础层
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# 重复下载，100%缓存命中
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

## 🔐 认证配置

### 支持的认证方式
| 镜像源 | 认证方式 | 示例 |
|--------|----------|------|
| Docker Hub | 用户名密码 | `--username dockerhubuser --password dockerhubpass` |
| Harbor | 用户名密码 | `--username harboruser --password harborpass` |
| ECR | 用户名密码 | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | 用户名密码 | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### 安全建议
```bash
# 推荐：使用环境变量
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# 不推荐：命令行直接写密码
python docker_pull.py image --username user --password pass  # 不安全
```

## 🛠️ 故障排除

### 常见问题及解决方案

#### 认证失败
```bash
# 错误：401 Unauthorized
# 解决：检查用户名密码是否正确
python docker_pull.py private-image --username user --password pass

# 错误：403 Forbidden  
# 解决：检查用户权限
```

#### 平台不匹配
```bash
# 错误：Platform mismatch
# 解决：查看可用平台列表
python docker_pull.py image --platform invalid
# 脚本会显示所有可用平台
```

#### 网络问题
```bash
# 设置代理
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### 错误代码说明
- **401**: 需要认证或认证失败
- **403**: 权限不足
- **404**: 镜像不存在
- **429**: 速率限制

## 📋 输出文件

下载完成后生成标准Docker tar文件：
- **文件名**: `{registry}_{repository}_{image}_{tag}.tar`
- **格式**: 100%兼容`docker load`命令
- **大小**: 与官方镜像一致
- **示例**: `docker load < library_nginx.tar`

## 更新日志

### v3.0 (当前版本) - 智能缓存版本
- 🆕 **智能层缓存系统**: 基于SHA256的全局层管理
- 🆕 **增量更新**: 自动复用已下载的层，节省带宽
- 🆕 **缓存统计**: 显示缓存命中率和节省的数据量
- 🆕 **OCI格式支持**: 完整支持OCI镜像索引格式
- 🆕 **阿里云ACR支持**: 支持阿里云容器镜像服务
- ✅ 硬链接优化存储空间
- ✅ 跨镜像层共享

### v2.0
- ✅ 添加Docker登录认证支持
- ✅ 支持所有主流镜像源
- ✅ 优化内存使用90%
- ✅ 增强错误处理
- ✅ 改进进度显示

### v1.5
- ✅ 添加并发下载功能
- ✅ 支持多平台镜像
- ✅ 性能优化

### v1.0
- ✅ 基础镜像下载功能

## 许可证
MIT License - 可自由使用、修改和分发

---

**快速开始：**
```bash
# 查看帮助
python docker_pull.py --help

# 下载镜像（自动缓存）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# 重复下载（缓存命中）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# 查看缓存目录
ls -la docker_images_cache/layers/
```