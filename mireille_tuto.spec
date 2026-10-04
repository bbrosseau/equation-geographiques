# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

repo_root = Path.cwd()
data_src = repo_root / "src" / "mireille_tuto" / "data"

datas = [
    (str(data_src / "ne_50m_admin_0_countries.geojson"), "data"),
    (str(data_src / "ne_110m_admin_0_countries.geojson"), "data"),
    (str(data_src / "SOURCE.json"), "data"),
    (str(data_src / "icon.png"), "data"),
]

icon_ico = data_src / "icon.ico"
icon_file = str(icon_ico) if icon_ico.exists() else None

a = Analysis(
    ["src/mireille_tuto/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pyside6",
        "matplotlib",
        "matplotlib.backends.backend_qtagg",
        "shapely",
        "shapely.geometry",
        "numpy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="Mireille-Tuto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

app = BUNDLE(
    exe,
    name="Mireille-Tuto.app",
    icon=str(data_src / "icon.png") if (data_src / "icon.png").exists() else None,
    bundle_identifier="com.mireille.tuto",
)

