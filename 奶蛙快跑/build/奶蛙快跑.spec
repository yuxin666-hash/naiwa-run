# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/Codex/奶蛙桌宠/奶蛙快跑/pc/app.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/Codex/奶蛙桌宠/奶蛙快跑/index.html', '.'), ('D:/Codex/奶蛙桌宠/奶蛙快跑/assets', 'assets'), ('D:/Codex/奶蛙桌宠/奶蛙快跑/vendor', 'vendor')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='奶蛙快跑',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/Codex/奶蛙桌宠/奶蛙快跑/../assets/tray.ico'],
)
