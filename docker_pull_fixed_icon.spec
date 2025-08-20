# -*- mode: python ; coding: utf-8 -*-
# 修复图标问题的PyInstaller配置文件

import os

# 获取绝对路径
base_dir = os.path.abspath('.')
icon_path = os.path.join(base_dir, 'icon_new.ico')  # 使用多尺寸图标
version_path = os.path.join(base_dir, 'version_info.txt')

a = Analysis(
    ['docker_pull.py'],
    pathex=[base_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        'requests.packages.urllib3',
        'requests.adapters',
        'urllib3.util.retry',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 只排除最明显的大型模块
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'PIL', 'Pillow', 'scipy', 'sklearn',
        'jupyter', 'IPython', 'pytest', 'unittest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='docker_pull',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,        # 禁用符号剥离避免问题
    upx=False,          # 禁用UPX压缩避免问题
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,     # 使用绝对路径的多尺寸图标
    version=version_path,  # 使用绝对路径的版本信息
)