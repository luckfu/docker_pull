# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['docker_pull.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['requests', 'json', 'threading', 'argparse'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 添加图标
    version='version_info.txt'  # 添加版本信息
)