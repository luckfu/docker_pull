# -*- mode: python ; coding: utf-8 -*-
# Ultra-optimized PyInstaller spec for minimal file size

a = Analysis(
    ['docker_pull.py'],
    pathex=[],
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
    # 排除所有不必要的大型模块
    excludes=[
        # GUI相关
        'tkinter', 'tk', 'tcl', '_tkinter',
        'tkinter.constants', 'tkinter.filedialog',
        
        # 数据科学和科学计算
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'sklearn', 'seaborn', 'plotly',
        
        # 图像处理
        'PIL', 'Pillow', 'cv2', 'skimage',
        
        # 开发和测试工具
        'pytest', 'unittest', 'doctest', 'pdb',
        'IPython', 'jupyter', 'notebook',
        'setuptools', 'distutils', 'pip',
        
        # 数据库
        'sqlite3', 'pymongo', 'psycopg2',
        
        # Web框架
        'flask', 'django', 'tornado', 'fastapi',
        
        # XML/HTML处理
        'xml.etree', 'xml.dom', 'xml.sax',
        'html', 'html.parser', 'lxml',
        'bs4', 'beautifulsoup4',
        
        # 网络服务器
        'http.server', 'wsgiref', 'socketserver',
        
        # 邮件处理
        'email', 'smtplib', 'imaplib', 'poplib',
        
        # 加密（如果不需要高级加密）
        'cryptography', 'Crypto',
        
        # 多媒体
        'pygame', 'pyaudio',
        
        # 其他大型库
        'pytz', 'dateutil', 'babel',
        'jinja2', 'markupsafe',
        'click', 'colorama',
        
        # 调试和分析工具
        'pstats', 'cProfile', 'profile',
        'trace', 'tracemalloc',
        
        # 文档生成
        'sphinx', 'docutils',
        
        # 并发相关（保留基本的threading）
        'multiprocessing.spawn',
        'multiprocessing.forkserver',
        
        # 平台特定模块
        'winreg', 'winsound',  # Windows
        'termios', 'tty',      # Unix
    ],
    noarchive=False,
)

# 进一步过滤，只保留核心模块
filtered_pure = []
for name, code, is_pkg in a.pure:
    # 排除不必要的标准库模块
    exclude_patterns = [
        'test.', 'tests.',
        'unittest.',
        'distutils.',
        'setuptools.',
        'pkg_resources.',
        'wheel.',
        'pip.',
        'email.',
        'html.',
        'xml.',
        'sqlite3.',
        'tkinter.',
        'turtle.',
        'pydoc.',
        'doctest.',
        'pdb.',
        'profile.',
        'cProfile.',
        'trace.',
        'calendar.',
        'mailbox.',
        'mimetypes.',
        'uu.',
        'base64.',  # 如果不需要base64编码
        'binhex.',
        'binascii.',
        'quopri.',
    ]
    
    should_exclude = False
    for pattern in exclude_patterns:
        if name.startswith(pattern):
            should_exclude = True
            break
    
    if not should_exclude:
        filtered_pure.append((name, code, is_pkg))

a.pure = filtered_pure

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='docker_pull_mini',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,           # 剥离调试符号
    upx=True,            # 启用UPX压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',     # 添加图标支持
    optimize=2,          # 最高级别的Python字节码优化
)