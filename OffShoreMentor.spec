# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('streamlit_app.py', '.'), ('modules', 'modules'), ('planner', 'planner'), ('viz', 'viz'), ('requirements.txt', '.'), ('LICENSE.txt', '.'), ('THIRD_PARTY_LICENSES.md', '.')],
    hiddenimports=['PIL', 'pydeck', 'streamlit.web.server'],
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
    [],
    exclude_binaries=True,
    name='OffShoreMentor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # Release build: no console window (errors go to logs/launcher.log and
    # logs/animation.log, plus a message box on fatal startup failures - see
    # launcher.py). For a debug build with a visible console, change this to
    # True or build via packaging\build_exe.ps1 -Console.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version='packaging/version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OffShoreMentor',
)
