#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台图标设置脚本
自动为不同平台准备合适的图标格式
"""

import os
import sys
import platform
from pathlib import Path

# 设置输出编码，避免Windows上的编码问题
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def get_platform_icon():
    """根据当前平台返回合适的图标文件名"""
    system = platform.system().lower()
    
    if system == 'windows':
        return 'icon.ico'
    elif system == 'darwin':  # macOS
        return 'icon.icns'
    else:  # Linux and others
        return 'icon.ico'  # Linux也可以使用ico格式

def create_cross_platform_spec(template_spec, output_spec):
    """创建跨平台的spec文件"""
    icon_file = get_platform_icon()
    
    # 读取模板spec文件
    with open(template_spec, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换图标配置
    if "icon='icon.ico'" in content:
        content = content.replace("icon='icon.ico'", f"icon='{icon_file}'")
    elif "icon=" not in content and "entitlements_file=None," in content:
        # 如果没有图标配置，添加一个
        content = content.replace(
            "entitlements_file=None,",
            f"entitlements_file=None,\n    icon='{icon_file}',"
        )
    
    # 写入新的spec文件
    with open(output_spec, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Created cross-platform spec file: {output_spec}")
    print(f"Using icon: {icon_file}")

def check_icon_files():
    """检查图标文件是否存在"""
    current_dir = Path('.')
    
    # 检查各种格式的图标文件
    icon_files = {
        'icon.ico': '适用于Windows和Linux',
        'icon.icns': '适用于macOS',
        'icon.png': '通用格式（可转换）'
    }
    
    print("Checking icon files:")
    found_icons = []
    
    for icon_file, description in icon_files.items():
        if (current_dir / icon_file).exists():
            size = (current_dir / icon_file).stat().st_size
            print(f"  OK: {icon_file} ({size} bytes) - {description}")
            found_icons.append(icon_file)
        else:
            print(f"  Missing: {icon_file} - {description}")
    
    return found_icons

def create_icon_recommendations():
    """提供图标创建建议"""
    print("\nIcon file recommendations:")
    print("  Recommended size: 256x256 pixels")
    print("  Format support:")
    print("     - Windows: .ico (multi-size icon)")
    print("     - macOS: .icns (Apple icon format)")
    print("     - Linux: .ico or .png")
    print("\nOnline conversion tools:")
    print("     - https://convertio.co/png-ico/")
    print("     - https://iconverticons.com/online/")
    print("\nIf you have a PNG icon, convert it with:")
    print("     # Install Pillow")
    print("     pip install Pillow")
    print("     # Convert to ico")
    print("     python -c \"from PIL import Image; Image.open('icon.png').save('icon.ico')\"")

def main():
    print("Docker Pull Icon Configuration Tool")
    print("=" * 40)
    
    # 检查图标文件
    found_icons = check_icon_files()
    
    if not found_icons:
        print("\nWarning: No icon files found!")
        create_icon_recommendations()
        return
    
    # 获取当前平台信息
    current_platform = platform.system()
    recommended_icon = get_platform_icon()
    
    print(f"\nCurrent platform: {current_platform}")
    print(f"Recommended icon: {recommended_icon}")
    
    # 检查推荐图标是否存在
    if recommended_icon in found_icons:
        print(f"OK: Recommended icon file exists: {recommended_icon}")
    else:
        print(f"Warning: Recommended icon file not found: {recommended_icon}")
        if 'icon.ico' in found_icons:
            print("Info: Will use icon.ico as fallback")
    
    # 创建跨平台spec文件
    spec_files = [
        'docker_pull.spec',
        'docker_pull_ultra_optimized.spec'
    ]
    
    for spec_file in spec_files:
        if Path(spec_file).exists():
            output_file = f"{spec_file.replace('.spec', '')}_platform.spec"
            try:
                create_cross_platform_spec(spec_file, output_file)
            except Exception as e:
                print(f"Error processing {spec_file}: {e}")
    
    print("\nIcon configuration completed!")
    print("\nUsage:")
    print("   pyinstaller docker_pull_platform.spec")
    print("   pyinstaller docker_pull_ultra_optimized_platform.spec")

if __name__ == '__main__':
    main()