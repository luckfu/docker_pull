# -*- mode: python ; coding: utf-8 -*-
# 专门为Windows图标优化的PyInstaller配置文件

import os

# 获取绝对路径
base_dir = os.path.abspath('.')
icon_path = os.path.join(base_dir, 'icon_new.ico')
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

# Windows专用EXE配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='docker_pull',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 确保图标配置正确
    icon=icon_path if os.path.exists(icon_path) else None,
    # 确保版本信息配置正确
    version=version_path if os.path.exists(version_path) else None,
)