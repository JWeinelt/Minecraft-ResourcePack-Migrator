# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('converter.py', '.'),
        ('run.py', '.')
    ],
    hiddenimports=[
        'tkinter',
        'rich',
        'rich.console',
        'rich.table',
        'rich.panel',
        'rich.progress',
        'rich.style',
        'threading',
        'json',
        'datetime',
        'pathlib',
        'shutil',
        'zipfile',
        'tempfile',
        'errno',
        'stat'
    ],
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
    name='MCPackConverter',
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
    manifest='uac_manifest.xml',
)