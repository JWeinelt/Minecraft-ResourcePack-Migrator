import os
import glob
import shutil
import subprocess

def create_exe():
    """創建需要管理員權限的exe檔案"""
    # 創建 manifest 檔案
    manifest_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="1.0.0.0"
    processorArchitecture="X86"
    name="MCPackConverter"
    type="win32"/>
  <description>MCPack Converter</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>'''
    
    with open('uac_manifest.xml', 'w', encoding='utf-8') as f:
        f.write(manifest_content)

    # 創建 spec 檔案
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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
)'''
    
    # 寫入 spec 檔案
    with open('MCPackConverter.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    # 使用 spec 檔案進行打包
    subprocess.run([
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'MCPackConverter.spec'
    ])
    
    # 清理臨時檔案
    if os.path.exists('uac_manifest.xml'):
        os.remove('uac_manifest.xml')
    
    print("建構完成！exe檔案位於 dist 目錄中")

if __name__ == "__main__":
    create_exe()