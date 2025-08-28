<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README_CN.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./README_TW.md"><img alt="繁體中文文件" src="https://img.shields.io/badge/繁體中文-d9d9d9"></a>
  <a href="./README_JA.md"><img alt="日本語のREADME" src="https://img.shields.io/badge/日本語-d9d9d9"></a>
  <a href="./README_ES.md"><img alt="README en Español" src="https://img.shields.io/badge/Español-d9d9d9"></a>
  <a href="./README_KR.md"><img alt="README in Korean" src="https://img.shields.io/badge/한국어-d9d9d9"></a>
</p>

# Docker Pull Script

Docker 환경이 필요하지 않은 이미지 다운로드 도구로, 멀티플랫폼, 동시 다운로드, 지능형 캐시(레이어 증분 업데이트), 인증 로그인을 지원합니다.

> 참고: 이 도구는 이미지 다운로드만을 위한 것이며, 컨테이너 빌드나 실행은 지원하지 않습니다.
> release 페이지에서 사전 컴파일된 바이너리 파일을 직접 다운로드할 수 있으며, Python 환경 설치가 필요하지 않습니다.
> Windows, macOS, Linux 시스템을 지원합니다.

## 🚀 기능 특성

### 핵심 기능
- **멀티플랫폼 지원**: 지정된 플랫폼 이미지를 자동으로 식별하고 다운로드 (linux/amd64, linux/arm64, linux/arm/v7 등)
- **동시 다운로드**: 멀티스레드로 이미지 레이어를 동시에 다운로드하여 30-50% 속도 향상
- **지능형 캐시**: SHA256 기반 레이어 캐시 시스템으로 증분 업데이트를 통해 대역폭 절약
- **메모리 최적화**: 스트리밍 다운로드로 메모리 사용량 90% 감소
- **네트워크 재시도**: 지능형 재시도 메커니즘으로 네트워크 중단 시 자동 복구
- **진행률 표시**: 다운로드 속도, 진행률 백분율, 남은 시간을 실시간으로 표시
- **인증 지원**: Docker 로그인 인증, 프라이빗 이미지 소스 지원

### 지원되는 이미지 소스
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** 프라이빗 레지스트리
- ✅ **Quay.io**
- ✅ **Alibaba Cloud ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **OCI 호환 레지스트리** (OCI 이미지 인덱스 형식 지원)

## 📦 설치 및 사용

### 시스템 요구사항
- Python 3.6+
- requests 라이브러리

### 종속성 설치
```bash
pip install requests
```

### 기본 명령
```bash
python docker_pull.py [이미지명] [옵션]
```

### 캐시 기능
- **자동 캐시**: 다운로드된 레이어가 자동으로 `./docker_images_cache/`에 캐시됨
- **증분 업데이트**: 재다운로드 시 캐시된 레이어를 자동으로 재사용
- **크로스 이미지 공유**: 서로 다른 이미지의 동일한 레이어가 캐시를 공유할 수 있음
- **캐시 통계**: 캐시 적중률과 절약된 데이터량을 표시

## 🔧 사용 예제

### 1. 기본 사용법

#### 공개 이미지 다운로드
```bash
# 최신 nginx 다운로드
python docker_pull.py nginx:latest

# 특정 플랫폼 이미지 다운로드
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# 사용자 정의 동시 실행 수
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# 캐시 비활성화
python docker_pull.py nginx:latest --no-cache

# 사용자 정의 캐시 디렉토리
python docker_pull.py nginx:latest --cache-dir /path/to/cache
```

#### 프라이빗 이미지 다운로드 (로그인 인증)
```bash
# Docker Hub 로그인
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# 프라이빗 Harbor 레지스트리
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# 환경 변수 사용 (더 안전함)
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. 플랫폼 지원

지원되는 플랫폼 형식:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32비트)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. 전체 명령줄 인수

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      image

인수 설명:
- image: Docker 이미지 이름 [registry/][repository/]image[:tag|@digest]
- --platform: 대상 플랫폼 (linux/amd64, linux/arm64, linux/arm/v7 등)
- --max-concurrent-downloads: 최대 동시 다운로드 레이어 수 (기본값: 3)
- --username: 사용자명 (프라이빗 이미지 소스 인증용)
- --password: 비밀번호 (프라이빗 이미지 소스 인증용)
- --cache-dir: 레이어 캐시 디렉토리 (기본값: ./docker_images_cache)
- --no-cache: 레이어 캐시 기능 비활성화
```

## 📊 성능 비교

### 동시 다운로드 성능
| 다운로드 방식 | 시간 | 성능 향상 |
|---------------|------|----------|
| 순차 다운로드 (1스레드) | 43.97초 | 기준선 |
| **동시 다운로드 (3스레드)** | **28.08초** | **36.1%** |
| 동시 다운로드 (5스레드) | 18.91초 | 57.0% |

### 캐시 기능 효과
| 시나리오 | 첫 번째 다운로드 | 재다운로드 | 캐시 적중률 | 데이터 절약 |
|----------|------------------|------------|-------------|-------------|
| nginx:1.21.0 (6레이어) | 정상 속도 | 즉시 완료 | 100% | 131MB |
| 유사한 버전 이미지 | 부분 캐시 | 상당한 가속 | 60-80% | 50-100MB |

## 🎯 실제 사용 시나리오

### 시나리오 1: 크로스 플랫폼 다운로드
```bash
# x86 서버에서 ARM 장치용 이미지 준비
python docker_pull.py --platform linux/arm64 nginx:latest
# nginx_arm64.tar 생성, ARM 장치로 전송하여 가져오기 가능
```

### 시나리오 2: CI/CD 통합
```bash
# GitHub Actions 예제
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### 시나리오 3: 프라이빗 레지스트리 관리
```bash
# 다양한 플랫폼 이미지 일괄 다운로드
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### 시나리오 4: 개발 환경 최적화
```bash
# 첫 번째 기본 이미지 다운로드
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# 관련 이미지 다운로드, 기본 레이어 자동 재사용
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# 재다운로드, 100% 캐시 적중
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

## 🔐 인증 구성

### 지원되는 인증 방법
| 이미지 소스 | 인증 방법 | 예제 |
|-------------|-----------|------|
| Docker Hub | 사용자명/비밀번호 | `--username dockerhubuser --password dockerhubpass` |
| Harbor | 사용자명/비밀번호 | `--username harboruser --password harborpass` |
| ECR | 사용자명/비밀번호 | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | 사용자명/비밀번호 | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### 보안 권장사항
```bash
# 권장: 환경 변수 사용
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# 권장하지 않음: 명령줄에 직접 비밀번호 입력
python docker_pull.py image --username user --password pass  # 안전하지 않음
```

## 🛠️ 문제 해결

### 일반적인 문제 및 해결책

#### 인증 실패
```bash
# 오류: 401 Unauthorized
# 해결: 사용자명과 비밀번호가 올바른지 확인
python docker_pull.py private-image --username user --password pass

# 오류: 403 Forbidden  
# 해결: 사용자 권한 확인
```

#### 플랫폼 불일치
```bash
# 오류: Platform mismatch
# 해결: 사용 가능한 플랫폼 목록 확인
python docker_pull.py image --platform invalid
# 스크립트가 사용 가능한 모든 플랫폼을 표시함
```

#### 네트워크 문제
```bash
# 프록시 설정
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### 오류 코드 설명
- **401**: 인증 필요 또는 인증 실패
- **403**: 권한 부족
- **404**: 이미지가 존재하지 않음
- **429**: 속도 제한

## 📋 출력 파일

다운로드 완료 후 표준 Docker tar 파일 생성:
- **파일명**: `{registry}_{repository}_{image}_{tag}.tar`
- **형식**: `docker load` 명령과 100% 호환
- **크기**: 공식 이미지와 일치
- **예제**: `docker load < library_nginx.tar`

## 변경 로그

### v3.0 (현재 버전) - 지능형 캐시 버전
- 🆕 **지능형 레이어 캐시 시스템**: SHA256 기반 글로벌 레이어 관리
- 🆕 **증분 업데이트**: 다운로드된 레이어 자동 재사용으로 대역폭 절약
- 🆕 **캐시 통계**: 캐시 적중률과 절약된 데이터량 표시
- 🆕 **OCI 형식 지원**: OCI 이미지 인덱스 형식 완전 지원
- 🆕 **Alibaba Cloud ACR 지원**: Alibaba Cloud 컨테이너 이미지 서비스 지원
- ✅ 하드 링크로 저장 공간 최적화
- ✅ 크로스 이미지 레이어 공유

### v2.0
- ✅ Docker 로그인 인증 지원 추가
- ✅ 모든 주요 이미지 소스 지원
- ✅ 메모리 사용량 90% 최적화
- ✅ 오류 처리 강화
- ✅ 진행률 표시 개선

### v1.5
- ✅ 동시 다운로드 기능 추가
- ✅ 멀티플랫폼 이미지 지원
- ✅ 성능 최적화

### v1.0
- ✅ 기본 이미지 다운로드 기능

## 라이선스
MIT License - 자유롭게 사용, 수정, 배포 가능

---

**빠른 시작:**
```bash
# 도움말 보기
python docker_pull.py --help

# 이미지 다운로드 (자동 캐시)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# 재다운로드 (캐시 적중)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# 캐시 디렉토리 확인
ls -la docker_images_cache/layers/
```