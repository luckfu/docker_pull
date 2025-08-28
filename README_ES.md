<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-d9d9d9"></a>
  <a href="./README_CN.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9"></a>
  <a href="./README_TW.md"><img alt="繁體中文文件" src="https://img.shields.io/badge/繁體中文-d9d9d9"></a>
  <a href="./README_JA.md"><img alt="日本語のREADME" src="https://img.shields.io/badge/日本語-d9d9d9"></a>
  <a href="./README_ES.md"><img alt="README en Español" src="https://img.shields.io/badge/Español-d9d9d9"></a>
  <a href="./README_KR.md"><img alt="README in Korean" src="https://img.shields.io/badge/한국어-d9d9d9"></a>
</p>

# Docker Pull Script

Herramienta de descarga de imágenes que no requiere entorno Docker, compatible con multiplataforma, descargas concurrentes, caché inteligente (actualizaciones incrementales de capas) y autenticación de inicio de sesión.

> Nota: Esta herramienta es solo para descargar imágenes, no admite construcción ni ejecución de contenedores.
> Puedes descargar directamente archivos binarios precompilados desde la página de releases, sin necesidad de instalar el entorno Python.
> Compatible con sistemas Windows, macOS y Linux.

## 🚀 Características

### Funciones Principales
- **Soporte Multiplataforma**: Identifica y descarga automáticamente imágenes de plataforma específica (linux/amd64, linux/arm64, linux/arm/v7, etc.)
- **Descargas Concurrentes**: Descarga simultánea de capas de imagen con múltiples hilos, mejora de velocidad del 30-50%
- **Caché Inteligente**: Sistema de caché de capas basado en SHA256, actualizaciones incrementales ahorran ancho de banda
- **Optimización de Memoria**: Descargas por streaming, reducción del 90% en uso de memoria
- **Reintento de Red**: Mecanismo de reintento inteligente, recuperación automática de interrupciones de red
- **Visualización de Progreso**: Muestra en tiempo real velocidad de descarga, porcentaje de progreso y tiempo restante
- **Soporte de Autenticación**: Autenticación de inicio de sesión Docker, compatible con fuentes de imágenes privadas

### Fuentes de Imágenes Compatibles
- ✅ **Docker Hub** (registry-1.docker.io)
- ✅ **Google Container Registry** (gcr.io, us.gcr.io, eu.gcr.io, asia.gcr.io)
- ✅ **AWS ECR** (amazonaws.com)
- ✅ **Harbor** Registro Privado
- ✅ **Quay.io**
- ✅ **Alibaba Cloud ACR** (registry.cn-shanghai.aliyuncs.com, registry.cn-beijing.aliyuncs.com)
- ✅ **Registros Compatibles con OCI** (soporte para formato de índice de imagen OCI)

## 📦 Instalación y Uso

### Requisitos del Sistema
- Python 3.6+
- Biblioteca requests

### Instalar Dependencias
```bash
pip install requests
```

### Comandos Básicos
```bash
python docker_pull.py [nombre_imagen] [opciones]
```

### Funciones de Caché
- **Caché Automático**: Las capas descargadas se almacenan automáticamente en caché en `./docker_images_cache/`
- **Actualizaciones Incrementales**: Reutiliza automáticamente las capas en caché en descargas repetidas
- **Compartición Entre Imágenes**: Las mismas capas de diferentes imágenes pueden compartir caché
- **Estadísticas de Caché**: Muestra la tasa de aciertos de caché y la cantidad de datos ahorrados

## 🔧 Ejemplos de Uso

### 1. Uso Básico

#### Descargar Imágenes Públicas
```bash
# Descargar la última versión de nginx
python docker_pull.py nginx:latest

# Descargar imagen de plataforma específica
python docker_pull.py --platform linux/arm64 ubuntu:20.04

# Concurrencia personalizada
python docker_pull.py --max-concurrent-downloads 5 alpine:latest

# Deshabilitar caché
python docker_pull.py nginx:latest --no-cache

# Directorio de caché personalizado
python docker_pull.py nginx:latest --cache-dir /path/to/cache
```

#### Descargar Imágenes Privadas (Autenticación de Inicio de Sesión)
```bash
# Inicio de sesión en Docker Hub
python docker_pull.py library/ubuntu:latest \
  --username myuser --password mypass

# Registro Harbor privado
python docker_pull.py harbor.company.com/dev/app:v1.2.0 \
  --username devuser --password devpass

# Usar variables de entorno (más seguro)
export USER=myuser
export PASS=mypass
python docker_pull.py private-image:latest \
  --username $USER --password $PASS
```

### 2. Soporte de Plataformas

Formatos de plataforma compatibles:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64)
- `linux/arm/v7` (ARM 32-bit)
- `linux/386` (x86)
- `linux/ppc64le` (PowerPC)
- `linux/s390x` (IBM Z)

### 3. Argumentos Completos de Línea de Comandos

```bash
python docker_pull.py [-h] [--platform PLATFORM]
                      [--max-concurrent-downloads MAX_CONCURRENT_DOWNLOADS]
                      [--username USERNAME] [--password PASSWORD]
                      [--cache-dir CACHE_DIR] [--no-cache]
                      image

Descripción de argumentos:
- image: Nombre de imagen Docker [registry/][repository/]image[:tag|@digest]
- --platform: Plataforma objetivo (linux/amd64, linux/arm64, linux/arm/v7, etc.)
- --max-concurrent-downloads: Número máximo de capas de descarga concurrente (predeterminado: 3)
- --username: Nombre de usuario (para autenticación de fuente de imagen privada)
- --password: Contraseña (para autenticación de fuente de imagen privada)
- --cache-dir: Directorio de caché de capas (predeterminado: ./docker_images_cache)
- --no-cache: Deshabilitar función de caché de capas
```

## 📊 Comparación de Rendimiento

### Rendimiento de Descarga Concurrente
| Método de Descarga | Tiempo | Mejora de Rendimiento |
|--------------------|--------|-----------------------|
| Descarga Secuencial (1 hilo) | 43.97s | Línea base |
| **Descarga Concurrente (3 hilos)** | **28.08s** | **36.1%** |
| Descarga Concurrente (5 hilos) | 18.91s | 57.0% |

### Efectos de la Función de Caché
| Escenario | Primera Descarga | Descarga Repetida | Tasa de Aciertos de Caché | Datos Ahorrados |
|-----------|------------------|-------------------|---------------------------|------------------|
| nginx:1.21.0 (6 capas) | Velocidad normal | Finalización instantánea | 100% | 131MB |
| Imágenes de versión similar | Caché parcial | Aceleración significativa | 60-80% | 50-100MB |

## 🎯 Escenarios de Uso Real

### Escenario 1: Descarga Multiplataforma
```bash
# Preparar imágenes para dispositivos ARM en servidor x86
python docker_pull.py --platform linux/arm64 nginx:latest
# Genera nginx_arm64.tar, se puede transferir al dispositivo ARM para importar
```

### Escenario 2: Integración CI/CD
```bash
# Ejemplo de GitHub Actions
- name: Pull Docker image
  run: |
    python docker_pull.py ${{ secrets.REGISTRY }}/${{ secrets.IMAGE }}:${{ env.TAG }} \
      --username ${{ secrets.USERNAME }} \
      --password ${{ secrets.PASSWORD }}
```

### Escenario 3: Gestión de Registro Privado
```bash
# Descarga por lotes de imágenes de diferentes plataformas
python docker_pull.py myregistry.com/app:v1.0 --platform linux/amd64 --username user --password pass
python docker_pull.py myregistry.com/app:v1.0 --platform linux/arm64 --username user --password pass
```

### Escenario 4: Optimización del Entorno de Desarrollo
```bash
# Primera descarga de imagen base
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 0/5 layers (0.0%)

# Descargar imagen relacionada, reutilizar automáticamente capas base
python docker_pull.py ubuntu:20.04-slim
# 💾 Cache Statistics: Cache hits: 3/4 layers (75.0%), Data saved: 45.2 MB

# Descarga repetida, 100% aciertos de caché
python docker_pull.py ubuntu:20.04
# 💾 Cache Statistics: Cache hits: 5/5 layers (100.0%), Data saved: 72.8 MB
```

## 🔐 Configuración de Autenticación

### Métodos de Autenticación Compatibles
| Fuente de Imagen | Método de Autenticación | Ejemplo |
|------------------|-------------------------|----------|
| Docker Hub | Usuario/Contraseña | `--username dockerhubuser --password dockerhubpass` |
| Harbor | Usuario/Contraseña | `--username harboruser --password harborpass` |
| ECR | Usuario/Contraseña | `--username AWS --password $(aws ecr get-login-password)` |
| GCR | Usuario/Contraseña | `--username oauth2accesstoken --password $(gcloud auth print-access-token)` |

### Recomendaciones de Seguridad
```bash
# Recomendado: Usar variables de entorno
export DOCKER_USERNAME=myuser
export DOCKER_PASSWORD=mypass
python docker_pull.py image --username $DOCKER_USERNAME --password $DOCKER_PASSWORD

# No recomendado: Escribir contraseña directamente en línea de comandos
python docker_pull.py image --username user --password pass  # Inseguro
```

## 🛠️ Solución de Problemas

### Problemas Comunes y Soluciones

#### Fallo de Autenticación
```bash
# Error: 401 Unauthorized
# Solución: Verificar si el nombre de usuario y contraseña son correctos
python docker_pull.py private-image --username user --password pass

# Error: 403 Forbidden  
# Solución: Verificar permisos de usuario
```

#### Desajuste de Plataforma
```bash
# Error: Platform mismatch
# Solución: Ver lista de plataformas disponibles
python docker_pull.py image --platform invalid
# El script mostrará todas las plataformas disponibles
```

#### Problemas de Red
```bash
# Configurar proxy
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
python docker_pull.py image
```

### Descripción de Códigos de Error
- **401**: Autenticación requerida o fallo de autenticación
- **403**: Permisos insuficientes
- **404**: La imagen no existe
- **429**: Límite de velocidad

## 📋 Archivos de Salida

Después de completar la descarga, genera archivos tar estándar de Docker:
- **Nombre de archivo**: `{registry}_{repository}_{image}_{tag}.tar`
- **Formato**: 100% compatible con el comando `docker load`
- **Tamaño**: Consistente con imágenes oficiales
- **Ejemplo**: `docker load < library_nginx.tar`

## Registro de Cambios

### v3.0 (Versión Actual) - Versión de Caché Inteligente
- 🆕 **Sistema de Caché de Capas Inteligente**: Gestión global de capas basada en SHA256
- 🆕 **Actualizaciones Incrementales**: Reutilización automática de capas descargadas, ahorro de ancho de banda
- 🆕 **Estadísticas de Caché**: Muestra tasa de aciertos de caché y datos ahorrados
- 🆕 **Soporte de Formato OCI**: Soporte completo para formato de índice de imagen OCI
- 🆕 **Soporte de Alibaba Cloud ACR**: Soporte para Servicio de Registro de Contenedores de Alibaba Cloud
- ✅ Optimización de espacio de almacenamiento con enlaces duros
- ✅ Compartición de capas entre imágenes

### v2.0
- ✅ Agregado soporte de autenticación de inicio de sesión Docker
- ✅ Soporte para todas las fuentes de imágenes principales
- ✅ Optimización del 90% en uso de memoria
- ✅ Manejo de errores mejorado
- ✅ Visualización de progreso mejorada

### v1.5
- ✅ Agregada función de descarga concurrente
- ✅ Soporte de imágenes multiplataforma
- ✅ Optimización de rendimiento

### v1.0
- ✅ Funcionalidad básica de descarga de imágenes

## Licencia
Licencia MIT - Libre para usar, modificar y distribuir

---

**Inicio Rápido:**
```bash
# Ver ayuda
python docker_pull.py --help

# Descargar imagen (caché automático)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 0/6 layers (0.0%)

# Descarga repetida (acierto de caché)
python docker_pull.py nginx:latest --platform linux/amd64
# 💾 Cache Statistics: Cache hits: 6/6 layers (100.0%), Data saved: 131.0 MB

# Ver directorio de caché
ls -la docker_images_cache/layers/
```