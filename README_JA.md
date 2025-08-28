<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README_CN.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./README_TW.md"><img alt="繁體中文文件" src="https://img.shields.io/badge/繁體中文-d9d9d9"></a>
  <a href="./README_JA.md"><img alt="日本語のREADME" src="https://img.shields.io/badge/日本語-d9d9d9"></a>
  <a href="./README_ES.md"><img alt="README en Español" src="https://img.shields.io/badge/Español-d9d9d9"></a>
  <a href="./README_KR.md"><img alt="README in Korean" src="https://img.shields.io/badge/한국어-d9d9d9"></a>
</p>

# Docker Pull Script

Docker環境を必要としないイメージダウンロードツール。マルチプラットフォーム、並行ダウンロード、インテリジェントキャッシュ（レイヤー増分更新）、認証ログインをサポート。

> 注意：このツールはイメージのダウンロードのみを目的としており、コンテナのビルドや実行はサポートしていません。
> releaseページから事前コンパイル済みのバイナリファイルを直接ダウンロードでき、Python環境のインストールは不要です。
> Windows、macOS、Linuxシステムをサポート。

## 🚀 機能特性

### コア機能
- **マルチプラットフォームサポート**: 指定されたプラットフォームイメージを自動識別・ダウンロード（linux/amd64, linux/arm64, linux/arm/v7など）
- **並行ダウンロード**: マルチスレッドによるイメージレイヤーの同時ダウンロード、30-50%の速度向上
- **インテリジェントキャッシュ**: SHA256ベースのレイヤーキャッシュシステム、増分更新で帯域幅を節約
- **メモリ最適化**: ストリーミングダウンロード、メモリ使用量90%削減
- **ネットワーク再試行**: インテリジェント再試行メカニズム、ネットワーク中断時の自動復旧
- **進捗表示**: ダウンロード速度、進捗率、残り時間のリアルタイム表示
- **認証サポート**: Dockerログイン認証、プライベートイメージソースをサポート

### サポートされているイメージソース
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** プライベートレジストリ
- ✅ **Quay.io**
- ✅ **Alibaba Cloud ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **OCI互換レジストリ** (OCIイメージインデックス形式をサポート)

## 📦 インストールと使用

### システム要件
- Python 3.6+
- requestsライブラリ

### 依存関係のインストール
```bash
pip install requests
```

### 基本コマンド
```bash
python docker_pull.py [イメージ名] [オプション]
```

### キャッシュ機能
- **自動キャッシュ**: ダウンロードされたレイヤーは自動的に `./docker_images_cache/` にキャッシュ
- **増分更新**: 再ダウンロード時にキャッシュされたレイヤーを自動再利用
- **クロスイメージ共有**: 異なるイメージの同じレイヤーでキャッシュを共有可能
- **キャッシュ統計**: キャッシュヒット率と節約されたデータ量を表示

## 🔧 使用例

### 1. 基本的な使用

#### パブリックイメージのダウンロード
```bash
# 最新版nginxをダウンロード
python docker_pull.py nginx:latest

# 指定プラットフォームイメージをダウンロード
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# カスタム並行数
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# キャッシュを無効化
python docker_pull.py nginx:latest --no-cache

# カスタムキャッシュディレクトリ
python docker_pull.py nginx:latest --cache-dir /path/to/cache
```

#### プライベートイメージのダウンロード（ログイン認証）
```bash
# Docker Hubログイン
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# プライベートHarborレジストリ
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# 環境変数を使用（より安全）
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. プラットフォームサポート

サポートされているプラットフォーム形式：
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32ビット)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. 完全なコマンドライン引数

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      image

引数説明：
- image: Dockerイメージ名 [registry/][repository/]image[:tag|@digest]
- --platform: ターゲットプラットフォーム (linux/amd64, linux/arm64, linux/arm/v7など)
- --max-concurrent-downloads: 最大並行ダウンロードレイヤー数 (デフォルト: 3)
- --username: ユーザー名（プライベートイメージソース認証用）
- --password: パスワード（プライベートイメージソース認証用）
- --cache-dir: レイヤーキャッシュディレクトリ (デフォルト: ./docker_images_cache)
- --no-cache: レイヤーキャッシュ機能を無効化
```

## 📊 パフォーマンス比較

### 並行ダウンロードパフォーマンス
| ダウンロード方式 | 時間 | パフォーマンス向上 |
|------------------|------|--------------------|
| 順次ダウンロード（1スレッド） | 43.97秒 | ベースライン |
| **並行ダウンロード（3スレッド）** | **28.08秒** | **36.1%** |
| 並行ダウンロード（5スレッド） | 18.91秒 | 57.0% |

### キャッシュ機能効果
| シナリオ | 初回ダウンロード | 再ダウンロード | キャッシュヒット率 | データ節約 |
|----------|------------------|----------------|-------------------|------------|
| nginx:1.21.0 (6レイヤー) | 通常速度 | 瞬時完了 | 100% | 131MB |
| 類似バージョンイメージ | 部分キャッシュ | 大幅加速 | 60-80% | 50-100MB |

## 🎯 実際の使用シナリオ

### シナリオ1: クロスプラットフォームダウンロード
```bash
# x86サーバーでARMデバイス用イメージを準備
python docker_pull.py --platform linux/arm64 nginx:latest
# nginx_arm64.tarを生成、ARMデバイスに転送してインポート可能
```

### シナリオ2: CI/CD統合
```bash
# GitHub Actions例
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### シナリオ3: プライベートレジストリ管理
```bash
# 異なるプラットフォームイメージの一括ダウンロード
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### シナリオ4: 開発環境最適化
```bash
# 初回ベースイメージダウンロード
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# 関連イメージダウンロード、ベースレイヤーを自動再利用
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# 再ダウンロード、100%キャッシュヒット
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

## 🔐 認証設定

### サポートされている認証方式
| イメージソース | 認証方式 | 例 |
|----------------|----------|----|
| Docker Hub | ユーザー名/パスワード | `--username dockerhubuser --password dockerhubpass` |
| Harbor | ユーザー名/パスワード | `--username harboruser --password harborpass` |
| ECR | ユーザー名/パスワード | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | ユーザー名/パスワード | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### セキュリティ推奨事項
```bash
# 推奨：環境変数を使用
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# 非推奨：コマンドラインに直接パスワードを記述
python docker_pull.py image --username user --password pass  # 安全でない
```

## 🛠️ トラブルシューティング

### よくある問題と解決策

#### 認証失敗
```bash
# エラー：401 Unauthorized
# 解決：ユーザー名とパスワードが正しいか確認
python docker_pull.py private-image --username user --password pass

# エラー：403 Forbidden  
# 解決：ユーザー権限を確認
```

#### プラットフォーム不一致
```bash
# エラー：Platform mismatch
# 解決：利用可能なプラットフォームリストを確認
python docker_pull.py image --platform invalid
# スクリプトが利用可能なすべてのプラットフォームを表示
```

#### ネットワーク問題
```bash
# プロキシ設定
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### エラーコード説明
- **401**: 認証が必要または認証失敗
- **403**: 権限不足
- **404**: イメージが存在しない
- **429**: レート制限

## 📋 出力ファイル

ダウンロード完了後、標準Docker tarファイルを生成：
- **ファイル名**: `{registry}_{repository}_{image}_{tag}.tar`
- **形式**: `docker load`コマンドと100%互換
- **サイズ**: 公式イメージと一致
- **例**: `docker load < library_nginx.tar`

## 更新履歴

### v3.0 (現在のバージョン) - インテリジェントキャッシュバージョン
- 🆕 **インテリジェントレイヤーキャッシュシステム**: SHA256ベースのグローバルレイヤー管理
- 🆕 **増分更新**: ダウンロード済みレイヤーの自動再利用、帯域幅節約
- 🆕 **キャッシュ統計**: キャッシュヒット率と節約データ量の表示
- 🆕 **OCI形式サポート**: OCIイメージインデックス形式の完全サポート
- 🆕 **Alibaba Cloud ACRサポート**: Alibaba Cloudコンテナイメージサービスをサポート
- ✅ ハードリンクによるストレージ空間最適化
- ✅ クロスイメージレイヤー共有

### v2.0
- ✅ Dockerログイン認証サポートを追加
- ✅ すべての主要イメージソースをサポート
- ✅ メモリ使用量90%最適化
- ✅ エラーハンドリング強化
- ✅ 進捗表示改善

### v1.5
- ✅ 並行ダウンロード機能を追加
- ✅ マルチプラットフォームイメージサポート
- ✅ パフォーマンス最適化

### v1.0
- ✅ 基本イメージダウンロード機能

## ライセンス
MIT License - 自由に使用、修正、配布可能

---

**クイックスタート：**
```bash
# ヘルプを表示
python docker_pull.py --help

# イメージをダウンロード（自動キャッシュ）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# 再ダウンロード（キャッシュヒット）
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# キャッシュディレクトリを確認
ls -la docker_images_cache/layers/
```