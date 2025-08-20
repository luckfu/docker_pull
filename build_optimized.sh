#!/bin/bash
# 本地构建优化版本的脚本

set -e

echo "🚀 开始构建优化版本的docker_pull..."

# 检查是否安装了必要的工具
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller未安装，正在安装..."
    pip install pyinstaller
fi

# 检查UPX是否可用
if command -v upx &> /dev/null; then
    echo "✅ UPX压缩工具已安装"
else
    echo "⚠️  UPX未安装，建议安装以获得更好的压缩效果"
    echo "   macOS: brew install upx"
    echo "   Ubuntu: sudo apt-get install upx-ucl"
fi

# 创建虚拟环境进行干净构建
echo "📦 创建临时虚拟环境..."
if [ -d "build_env" ]; then
    rm -rf build_env
fi
python -m venv build_env
source build_env/bin/activate

# 安装最小依赖
echo "📥 安装最小依赖..."
pip install --upgrade pip
pip install -r requirements_minimal.txt
pip install pyinstaller

# 清理之前的构建
echo "🧹 清理之前的构建文件..."
if [ -d "dist" ]; then
    rm -rf dist
fi
if [ -d "build" ]; then
    rm -rf build
fi

# 构建标准版本
echo "🔨 构建标准版本..."
pyinstaller --onefile --name docker_pull_standard docker_pull.py
standard_size=$(stat -f%z dist/docker_pull_standard 2>/dev/null || stat -c%s dist/docker_pull_standard 2>/dev/null)

# 构建优化版本
echo "⚡ 构建超级优化版本..."
pyinstaller docker_pull_ultra_optimized.spec
optimized_size=$(stat -f%z dist/docker_pull_mini 2>/dev/null || stat -c%s dist/docker_pull_mini 2>/dev/null)

# 显示结果
echo ""
echo "📊 构建完成！文件大小对比："
echo "   标准版本: $(echo "scale=1; $standard_size/1024/1024" | bc -l 2>/dev/null || python3 -c "print(f'{$standard_size/1024/1024:.1f}')" 2>/dev/null || echo "$((standard_size/1024/1024))") MB"
echo "   优化版本: $(echo "scale=1; $optimized_size/1024/1024" | bc -l 2>/dev/null || python3 -c "print(f'{$optimized_size/1024/1024:.1f}')" 2>/dev/null || echo "$((optimized_size/1024/1024))") MB"

if [ $optimized_size -lt $standard_size ]; then
    reduction=$((100 - optimized_size * 100 / standard_size))
    echo "   🎉 优化版本减少了 ${reduction}% 的大小！"
fi

# 测试功能
echo ""
echo "🧪 测试优化版本功能..."
if ./dist/docker_pull_mini --help > /dev/null 2>&1; then
    echo "✅ 优化版本功能正常"
else
    echo "❌ 优化版本可能有问题，请检查"
fi

# 清理虚拟环境
deactivate
rm -rf build_env

echo ""
echo "✨ 构建完成！文件位置："
echo "   标准版本: dist/docker_pull_standard"
echo "   优化版本: dist/docker_pull_mini"
echo ""
echo "💡 提示：你可以运行以下命令测试："
echo "   ./dist/docker_pull_mini nginx:latest --help"