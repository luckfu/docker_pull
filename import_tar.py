#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker tar文件导入工具
从现有的Docker tar文件中提取layers并添加到缓存目录
"""

import os
import sys
import json
import hashlib
import shutil
import tarfile
import argparse
from pathlib import Path

def calculate_layer_digest(layer_tar_path: str) -> str:
    """Calculate SHA256 digest of a layer tar file"""
    sha256_hash = hashlib.sha256()
    with open(layer_tar_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return f"sha256:{sha256_hash.hexdigest()}"

def format_speed(bytes_size):
    """Format file size in human-readable format"""
    if bytes_size < 1024:
        return f"{bytes_size:.0f} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size/1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size/(1024*1024):.1f} MB"
    else:
        return f"{bytes_size/(1024*1024*1024):.1f} GB"

def get_layer_cache_path(layer_digest: str, layers_cache_dir: Path) -> Path:
    """Get the cache path for a layer based on its digest"""
    return layers_cache_dir / layer_digest.replace(':', '_')

def check_layer_cache(layer_digest: str, layers_cache_dir: Path) -> bool:
    """Check if a layer exists in cache"""
    cache_path = get_layer_cache_path(layer_digest, layers_cache_dir)
    layer_file = cache_path / 'layer.tar'
    return layer_file.exists()

def save_layer_to_cache(layer_digest: str, layer_tar_path: str, layers_cache_dir: Path) -> bool:
    """Save a layer to cache"""
    try:
        cache_path = get_layer_cache_path(layer_digest, layers_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Create hard link to save space
        cache_layer_file = cache_path / 'layer.tar'
        if not cache_layer_file.exists():
            os.link(layer_tar_path, cache_layer_file)
        
        # Save metadata
        metadata = {
            'digest': layer_digest,
            'size': os.path.getsize(layer_tar_path),
            'cached_at': __import__('time').time()
        }
        with open(cache_path / 'metadata.json', 'w') as f:
            json.dump(metadata, f)
        
        return True
    except Exception as e:
        print(f"Warning: Failed to cache layer {layer_digest[7:19]}: {e}")
        return False

def import_docker_tar_to_cache(tar_file_path: str, cache_dir: Path):
    """Import layers from a Docker tar file to cache"""
    print(f"🔄 开始导入Docker tar文件到缓存: {tar_file_path}")
    
    if not os.path.exists(tar_file_path):
        print(f"❌ 错误: 文件不存在 {tar_file_path}")
        return
    
    layers_cache_dir = cache_dir / 'layers'
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
                    if check_layer_cache(layer_digest, layers_cache_dir):
                        print(f"⏭️  跳过已缓存的层: {layer_digest[7:19]}")
                        skipped_count += 1
                        continue
                    
                    # 导入到缓存
                    layer_size = full_layer_path.stat().st_size
                    if save_layer_to_cache(layer_digest, str(full_layer_path), layers_cache_dir):
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
        if temp_dir.exists():
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

def main():
    parser = argparse.ArgumentParser(
        description='从Docker tar文件导入layers到缓存目录',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('tar_file', help='Docker tar文件路径')
    parser.add_argument('--cache-dir', help='缓存目录 (默认: ./docker_images_cache)', default='./docker_images_cache')
    
    args = parser.parse_args()
    
    cache_dir = Path(args.cache_dir).expanduser().resolve()
    
    print("="*60)
    print("🐳 Docker Tar导入工具")
    print("📦 将Docker tar文件的layers导入到缓存目录")
    print("="*60)
    print()
    
    import_docker_tar_to_cache(args.tar_file, cache_dir)

if __name__ == '__main__':
    main()