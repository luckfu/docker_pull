<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README_CN.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./README_TW.md"><img alt="繁體中文文件" src="https://img.shields.io/badge/繁體中文-d9d9d9"></a>
  <a href="./README_JA.md"><img alt="日本語のREADME" src="https://img.shields.io/badge/日本語-d9d9d9"></a>
  <a href="./README_ES.md"><img alt="README en Español" src="https://img.shields.io/badge/Español-d9d9d9"></a>
  <a href="./README_KR.md"><img alt="README in Korean" src="https://img.shields.io/badge/한국어-d9d9d9"></a>
</p>

# Docker Pull Script

不需要Docker環境的映像下載工具，支援多平台、並發下載、智慧快取（layer增量更新）、認證登入。

> 注意：本工具僅用於下載映像，不支援建構、執行容器。
> 可以直接在 release 頁面下載預編譯的二進位檔案，無需安裝Python環境。
> 支援Windows、macOS、Linux系統。

## 🚀 功能特性

### 核心功能
- **多平台支援**: 自動識別並下載指定平台映像（linux/amd64, linux/arm64, linux/arm/v7等）
- **並發下載**: 多執行緒同時下載映像層，速度提升30-50%
- **智慧快取**: 基於SHA256的層快取系統，增量更新節省頻寬
- **記憶體最佳化**: 串流下載，記憶體佔用減少90%
- **網路重試**: 智慧重試機制，網路中斷自動恢復
- **進度顯示**: 即時顯示下載速度、進度百分比和剩餘時間
- **認證支援**: Docker登入認證，支援私有映像源

### 支援的映像源
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** 私有倉庫
- ✅ **Quay.io**
- ✅ **阿里雲ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **OCI相容註冊表** (支援OCI映像索引格式)

## 📦 安裝使用

### 系統要求
- Python 3.6+
- requests函式庫

### 安裝相依性
```bash
pip install requests
```

### 基本命令
```bash
python docker_pull.py [映像名] [選項]
```

### 快取功能
- **自動快取**: 下載的層自動快取到 `./docker_images_cache/`
- **增量更新**: 重複下載時自動複用已快取的層
- **跨映像共享**: 不同映像的相同層可以共享快取
- **快取統計**: 顯示快取命中率和節省的資料量

## 🔧 使用範例

### 1. 基礎使用

#### 下載公共映像
```bash
# 下載最新版nginx
python docker_pull.py nginx:latest

# 下載指定平台映像
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# 自訂並發數
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# 停用快取
python docker_pull.py nginx:latest --no-cache

# 自訂快取目錄
python docker_pull.py nginx:latest --cache-dir /path/to/cache
```

#### 下載私有映像（登入認證）
```bash
# Docker Hub登入
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# 私有Harbor倉庫
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# 使用環境變數（更安全）
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. 平台支援

支援的平台格式：
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32位元)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. 完整命令列參數

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      image

參數說明：
- image: Docker映像名稱 [registry/][repository/]image[:tag|@digest]
- --platform: 目標平台 (linux/amd64, linux/arm64, linux/arm/v7等)
- --max-concurrent-downloads: 最大並發下載層數 (預設: 3)
- --username: 使用者名稱（私有映像源認證）
- --password: 密碼（私有映像源認證）
- --cache-dir: 層快取目錄 (預設: ./docker_images_cache)
- --no-cache: 停用層快取功能
```

## 📊 效能比較

### 並發下載效能
| 下載方式 | 耗時 | 效能提升 |
|----------|------|----------|
| 順序下載（1執行緒） | 43.97秒 | 基準 |
| **並發下載（3執行緒）** | **28.08秒** | **36.1%** |
| 並發下載（5執行緒） | 18.91秒 | 57.0% |

### 快取功能效果
| 場景 | 首次下載 | 重複下載 | 快取命中率 | 節省資料 |
|------|----------|----------|------------|----------|
| nginx:1.21.0 (6層) | 正常速度 | 瞬間完成 | 100% | 131MB |
| 相似版本映像 | 部分快取 | 顯著加速 | 60-80% | 50-100MB |

## 🎯 實際使用場景

### 場景1：跨平台下載
```bash
# 在x86伺服器上為ARM裝置準備映像
python docker_pull.py --platform linux/arm64 nginx:latest
# 產生 nginx_arm64.tar，可傳輸到ARM裝置匯入
```

### 場景2：CI/CD整合
```bash
# GitHub Actions範例
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### 場景3：私有倉庫管理
```bash
# 批次下載不同平台映像
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### 場景4：開發環境最佳化
```bash
# 首次下載基礎映像
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# 下載相關映像，自動複用基礎層
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# 重複下載，100%快取命中
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

## 🔐 認證設定

### 支援的認證方式
| 映像源 | 認證方式 | 範例 |
|--------|----------|------|
| Docker Hub | 使用者名稱密碼 | `--username dockerhubuser --password dockerhubpass` |
| Harbor | 使用者名稱密碼 | `--username harboruser --password harborpass` |
| ECR | 使用者名稱密碼 | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | 使用者名稱密碼 | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### 安全建議
```bash
# 推薦：使用環境變數
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# 不推薦：命令列直接寫密碼
python docker_pull.py image --username user --password pass  # 不安全
```

## 🛠️ 故障排除

### 常見問題及解決方案

#### 認證失敗
```bash
# 錯誤：401 Unauthorized
# 解決：檢查使用者名稱密碼是否正確
python docker_pull.py private-image --username user --password pass

# 錯誤：403 Forbidden  
# 解決：檢查使用者權限
```

#### 平台不匹配
```bash
# 錯誤：Platform mismatch
# 解決：檢視可用平台清單
python docker_pull.py image --platform invalid
# 指令碼會顯示所有可用平台
```

#### 網路問題
```bash
# 設定代理
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### 錯誤代碼說明
- **401**: 需要認證或認證失敗
- **403**: 權限不足
- **404**: 映像不存在
- **429**: 速率限制

## 📋 輸出檔案

下載完成後產生標準Docker tar檔案：
- **檔案名**: `{registry}_{repository}_{image}_{tag}.tar`
- **格式**: 100%相容`docker load`命令
- **大小**: 與官方映像一致
- **範例**: `docker load < library_nginx.tar`

## 更新日誌

### v3.0 (目前版本) - 智慧快取版本
- 🆕 **智慧層快取系統**: 基於SHA256的全域層管理
- 🆕 **增量更新**: 自動複用已下載的層，節省頻寬
- 🆕 **快取統計**: 顯示快取命中率和節省的資料量
- 🆕 **OCI格式支援**: 完整支援OCI映像索引格式
- 🆕 **阿里雲ACR支援**: 支援阿里雲容器映像服務
- ✅ 硬連結最佳化儲存空間
- ✅ 跨映像層共享

### v2.0
- ✅ 新增Docker登入認證支援
- ✅ 支援所有主流映像源
- ✅ 最佳化記憶體使用90%
- ✅ 增強錯誤處理
- ✅ 改進進度顯示

### v1.5
- ✅ 新增並發下載功能
- ✅ 支援多平台映像
- ✅ 效能最佳化

### v1.0
- ✅ 基礎映像下載功能

## 授權條款
MIT License - 可自由使用、修改和分發

---

**快速開始：**
```bash
# 檢視說明
python docker_pull.py --help

# 下載映像（自動快取）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# 重複下載（快取命中）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# 檢視快取目錄
ls -la docker_images_cache/layers/
```