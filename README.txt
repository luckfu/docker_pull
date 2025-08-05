# Docker Pull Cross-Platform Workflow

## 功能特性

- **跨平台支持**: 支持多种CPU架构（amd64, arm64, arm/v7, 386, ppc64le, s390x等）
- **多注册表兼容**: 支持Docker Hub、Quay.io等主流容器注册表
- **智能平台检测**: 自动检测并验证镜像平台兼容性
- **Schema兼容**: 同时支持Docker Registry API v1和v2清单格式
- **并发下载**: 支持多线程并发下载镜像层，显著提升大型镜像的下载速度
- **错误处理**: 完善的错误提示和平台不匹配检测

## 并发下载功能

### 性能优势

- **显著提升下载速度**: 通过并发下载多个镜像层，可以充分利用网络带宽
- **智能线程管理**: 使用ThreadPoolExecutor确保线程安全和资源管理
- **保持层顺序**: 虽然并发下载，但确保最终镜像结构的正确性

### 使用建议

- **小型镜像**: 对于只有1-2个层的镜像，建议使用默认值（3个并发）
- **中型镜像**: 对于5-10个层的镜像，建议使用5-8个并发
- **大型镜像**: 对于超过10个层的镜像，可以使用8-12个并发
- **网络限制**: 如果网络带宽有限，适当降低并发数以避免连接超时

### 性能测试结果

基于nginx镜像（7个层）的实际测试结果：

| 下载方式 | 耗时 | 性能提升 |
|---------|------|----------|
| 顺序下载（1线程） | 43.97秒 | 基准 |
| 并发下载（3线程） | 28.08秒 | **36.1%** |
| 并发下载（5线程） | 18.91秒 | **57.0%** |

### 示例对比

```bash
# 传统顺序下载（较慢）
python docker_pull.py nginx --platform linux/amd64 --max-concurrent-downloads 1

# 并发下载（推荐，默认）
python docker_pull.py nginx --platform linux/amd64 --max-concurrent-downloads 3

# 高并发下载（适用于大型镜像）
python docker_pull.py ubuntu:20.04 --platform linux/amd64 --max-concurrent-downloads 8
```

### 性能测试工具

项目包含了性能测试脚本 `performance_test.py`，可以用来测试不同并发设置的性能差异：

```bash
python3 performance_test.py
```

## 重要说明

⚠️ **不同标签可能支持不同的平台架构**

同一个镜像仓库的不同标签可能有不同的平台支持：
- 某些标签可能只支持单一架构（如 `linux/amd64`）
- 某些标签可能支持多平台（如 `linux/amd64`, `linux/arm64`）
- 容器注册表界面显示的平台支持是整个仓库的汇总信息，不代表每个标签都支持所有平台

**示例：**
```bash
# 这个标签可能只支持 amd64
python docker_pull.py quay.io/ascend/vllm-ascend:v0.9.2rc1-openeuler --platform linux/arm64
# 输出：[-] Platform mismatch: requested linux/arm64, but image only supports linux/amd64

# 而这个标签支持多平台
python docker_pull.py quay.io/ascend/vllm-ascend:latest --platform linux/arm64
# 输出：[+] Found manifest for platform: linux/arm64
```

## 使用方法

```bash
python docker_pull.py [registry/][repository/]image[:tag|@digest] [--platform PLATFORM] [--max-concurrent-downloads N]
```

### 参数说明

- `image`: Docker镜像名称，支持完整的镜像引用格式
- `--platform`: 可选，指定目标平台（如 linux/amd64, linux/arm64, linux/arm/v7）
- `--max-concurrent-downloads`: 可选，最大并发下载层数（默认值：3）

### 使用示例

```bash
# 拉取默认平台的镜像
python docker_pull.py hello-world

# 拉取指定平台的镜像
python docker_pull.py hello-world --platform linux/amd64
python docker_pull.py nginx --platform linux/arm64
python docker_pull.py alpine --platform linux/arm/v7

# 使用并发下载加速（推荐用于大型镜像）
python docker_pull.py nginx --platform linux/amd64 --max-concurrent-downloads 5
python docker_pull.py ubuntu:20.04 --platform linux/amd64 --max-concurrent-downloads 8

# 拉取私有仓库镜像
python docker_pull.py quay.io/ascend/vllm-ascend:v0.9.2rc1-openeuler --platform linux/amd64
```

## Usage Examples

```bash
# Pull linux/amd64 image (default)
python docker_pull.py nginx:latest

# Pull linux/arm64 image
python docker_pull.py --platform linux/arm64 nginx:latest

# Pull linux/arm/v7 image
python docker_pull.py --platform linux/arm/v7 alpine:latest

# Pull with custom registry
python docker_pull.py --platform linux/arm64 myregistry.com/myrepo/myimage:tag

# Pull with concurrent downloads for faster performance
python docker_pull.py --platform linux/amd64 --max-concurrent-downloads 5 nginx:latest
python docker_pull.py --platform linux/arm64 --max-concurrent-downloads 8 ubuntu:20.04
```

## Workflow Diagram

```mermaid
flowchart TD
    Start([Start]) --> Parse[Parse Arguments]
    Parse --> CheckPlatform{Platform Specified?}
    
    CheckPlatform -->|No| FetchV2[Fetch Manifest V2]
    CheckPlatform -->|Yes| FetchV2
    
    FetchV2 --> CheckV2{Manifest V2 Success?}
    
    CheckV2 -->|Yes| SingleManifest[Single Manifest Found]
    CheckV2 -->|No| FetchList[Fetch Manifest List]
    
    FetchList --> CheckList{Manifest List Success?}
    
    CheckList -->|No| ExitError[Exit with Error]
    CheckList -->|Yes| CheckPlatformList{Platform Specified?}
    
    CheckPlatformList -->|No| ShowPlatforms[Show Available Platforms]
    CheckPlatformList -->|Yes| FindPlatform[Find Platform Manifest]
    
    ShowPlatforms --> ExitInfo[Exit with Platform Info]
    
    FindPlatform --> PlatformFound{Platform Found?}
    
    PlatformFound -->|No| ShowAvailable[Show Available Platforms]
    PlatformFound -->|Yes| FetchPlatform[Fetch Platform Manifest]
    
    ShowAvailable --> ExitError
    
    FetchPlatform --> CheckPlatformSuccess{Fetch Success?}
    CheckPlatformSuccess -->|No| ExitError
    CheckPlatformSuccess -->|Yes| PlatformManifest[Platform Manifest Found]
    
    SingleManifest --> DownloadLayers[Download Layers]
    PlatformManifest --> DownloadLayers
    
    DownloadLayers --> ExtractLayers[Extract Layers]
    ExtractLayers --> CreateTar[Create Tar Archive]
    CreateTar --> CleanUp[Clean Up Temp Files]
    CleanUp --> Done([Complete])

    style Start fill:#90EE90
    style Done fill:#90EE90
    style ExitError fill:#FFB6C1
    style ExitInfo fill:#87CEEB
```

## 清单类型处理

脚本支持两种 Docker 清单格式：

### Schema V2 清单（推荐）
- 支持多平台清单列表
- 包含详细的平台信息（OS、架构、变体）
- 现代容器注册表的标准格式

### Schema V1 清单（传统）
- 单一平台支持
- 架构信息有限
- 主要用于向后兼容
- 当指定 `--platform` 参数时，脚本会验证请求的平台是否与清单中的架构匹配

## Platform Detection Logic

```mermaid
flowchart TD
    Start([Platform Requested]) --> ParsePlatform[Parse Platform String]
    
    ParsePlatform --> FormatCheck{Format Valid?}
    FormatCheck -->|No| ErrorInvalid[Error: Invalid Format]
    FormatCheck -->|Yes| SplitPlatform[Split into OS/Arch/Variant]
    
    SplitPlatform --> MatchManifests[Iterate through Manifests]
    
    MatchManifests --> CheckOS{OS Match?}
    CheckOS -->|No| NextManifest[Next Manifest]
    CheckOS -->|Yes| CheckArch{Architecture Match?}
    
    CheckArch -->|No| NextManifest
    CheckArch -->|Yes| CheckVariant{Variant Required?}
    
    CheckVariant -->|No| MatchFound[Platform Match Found]
    CheckVariant -->|Yes| CheckVariantMatch{Variant Match?}
    
    CheckVariantMatch -->|No| NextManifest
    CheckVariantMatch -->|Yes| MatchFound
    
    NextManifest --> ManifestsLeft{More Manifests?}
    ManifestsLeft -->|Yes| CheckOS
    ManifestsLeft -->|No| NoMatch[No Platform Match]
    
    ErrorInvalid --> ExitError[Exit with Error]
    MatchFound --> ReturnManifest[Return Platform Manifest]
    NoMatch --> ShowAvailable[Show Available Platforms]
    
    style ReturnManifest fill:#90EE90
    style ExitError fill:#FFB6C1
    style ShowAvailable fill:#87CEEB
```

## Platform Format Support

| Platform Format | Example | Description |
|----------------|---------|-------------|
| `os/arch` | `linux/amd64` | Basic platform specification |
| `os/arch/variant` | `linux/arm/v7` | Platform with variant |
| `os/arch` | `linux/arm64` | ARM 64-bit |
| `os/arch/variant` | `linux/arm64/v8` | ARM 64-bit with variant |
| `os/arch` | `linux/386` | 32-bit x86 |
| `os/arch` | `linux/s390x` | IBM System z |
| `os/arch` | `linux/ppc64le` | PowerPC 64-bit Little Endian |

## 错误处理

### 平台不匹配错误
当请求的平台不被支持时，脚本会：
1. 显示清晰的错误信息
2. 列出所有可用的平台
3. 以退出码 1 退出

### Schema V1 清单的平台检查
对于传统的 Schema V1 清单：
- 脚本会检查清单中的 `architecture` 字段
- 如果与请求的平台不匹配，会显示错误并退出
- 提示用户该清单不支持多平台

## Example Output

### When platform is available:
```
[+] Searching for platform-specific manifest...
[+] Found manifest for platform: linux/arm64
Creating image structure in: tmp_nginx_latest
...
Docker image pulled: library_nginx.tar
```

### When platform is not available:
```
[-] No manifest found for platform: linux/ppc64le
[+] Available platforms:
    - linux/amd64
    - linux/arm/v5
    - linux/arm/v7
    - linux/arm64/v8
    - linux/386
    - linux/mips64le
    - linux/ppc64le
    - linux/s390x
```

### Schema V1 平台不匹配:
```
[+] Single platform manifest detected
[-] Platform mismatch: requested linux/arm64, but image only supports linux/amd64
[-] Schema v1 manifests do not support multi-platform
```

### Schema V2 平台验证成功:
```
[+] Single platform manifest detected
[+] Platform verified: linux/amd64
Creating image structure in: tmp_image_tag
...
```

### When no platform specified and multiple available:
```
[+] Manifests found for this tag (use --platform to specify platform):
    Platform: linux/amd64, digest: sha256:123abc...
    Platform: linux/arm64, digest: sha256:456def...
    Platform: linux/arm/v7, digest: sha256:789ghi...
```