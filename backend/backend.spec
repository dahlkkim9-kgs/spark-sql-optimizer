# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件
用于打包 Spark SQL 优化工具的 Python 后端
"""

block_cipher = None

a = Analysis(
    ['api/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('core', 'core'),  # 包含 core 目录
        ('../frontend/build', 'frontend/build'),  # 前端静态文件
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'fastapi.app',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'pydantic',
        'pydantic_core',
        'pydantic.core',
        'sqlglot',
        'sqlglot.dialects',
        'sqlglot.dialects.spark',
        'starlette',
        'starlette.applications',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.routing',
        'typing_extensions',
        'email_validator',
        'anyio',
        'anyio.backends',
        'anyio.backends.asyncio',
        'webbrowser',
        'socket',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pandas', 'numpy', 'scipy', 'openpyxl'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='spark-sql-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台以便调试
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
