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
    
    print(f"✅ 已创建跨平台spec文件: {output_spec}")
    print(f"📱 使用图标: {icon_file}")

def check_icon_files():
    """检查图标文件是否存在"""
    current_dir = Path('.')
    
    # 检查各种格式的图标文件
    icon_files = {
        'icon.ico': '适用于Windows和Linux',
        'icon.icns': '适用于macOS',
        'icon.png': '通用格式（可转换）'
    }
    
    print("🔍 检查图标文件:")
    found_icons = []
    
    for icon_file, description in icon_files.items():
        if (current_dir / icon_file).exists():
            size = (current_dir / icon_file).stat().st_size
            print(f"  ✅ {icon_file} ({size} bytes) - {description}")
            found_icons.append(icon_file)
        else:
            print(f"  ❌ {icon_file} - {description}")
    
    return found_icons

def create_icon_recommendations():
    """提供图标创建建议"""
    print("\n💡 图标文件建议:")
    print("  📏 推荐尺寸: 256x256 像素")
    print("  🎨 格式支持:")
    print("     • Windows: .ico (多尺寸图标)")
    print("     • macOS: .icns (Apple图标格式)")
    print("     • Linux: .ico 或 .png")
    print("\n🛠️  在线转换工具:")
    print("     • https://convertio.co/png-ico/")
    print("     • https://iconverticons.com/online/")
    print("\n📦 如果你有PNG图标，可以使用以下命令转换:")
    print("     # 安装Pillow")
    print("     pip install Pillow")
    print("     # 转换为ico")
    print("     python -c \"from PIL import Image; Image.open('icon.png').save('icon.ico')\"")

def main():
    print("🎯 Docker Pull 图标配置工具")
    print("=" * 40)
    
    # 检查图标文件
    found_icons = check_icon_files()
    
    if not found_icons:
        print("\n⚠️  未找到任何图标文件！")
        create_icon_recommendations()
        return
    
    # 获取当前平台信息
    current_platform = platform.system()
    recommended_icon = get_platform_icon()
    
    print(f"\n🖥️  当前平台: {current_platform}")
    print(f"📱 推荐图标: {recommended_icon}")
    
    # 检查推荐图标是否存在
    if recommended_icon in found_icons:
        print(f"✅ 推荐图标文件存在: {recommended_icon}")
    else:
        print(f"⚠️  推荐图标文件不存在: {recommended_icon}")
        if 'icon.ico' in found_icons:
            print("💡 将使用 icon.ico 作为备选")
    
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
                print(f"❌ 处理 {spec_file} 时出错: {e}")
    
    print("\n🎉 图标配置完成！")
    print("\n📝 使用方法:")
    print("   pyinstaller docker_pull_platform.spec")
    print("   pyinstaller docker_pull_ultra_optimized_platform.spec")

if __name__ == '__main__':
    main()