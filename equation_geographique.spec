# -*- mode: python ; coding: utf-8 -*-
# Construction : uv run pyinstaller --clean --noconfirm mireille_tuto.spec
# Résultat : dist/Mireille-Tuto/ (Windows, Linux) et dist/Mireille-Tuto.app (macOS).
import sys
from pathlib import Path

data_src = Path.cwd() / "src" / "mireille_tuto" / "data"
icon_png = str(data_src / "icon.png")  # converti en .ico / .icns par PyInstaller (requiert Pillow)

a = Analysis(
    ["src/mireille_tuto/__main__.py"],
    pathex=["src"],
    datas=[
        (str(data_src / "ne_50m_admin_0_countries.geojson"), "data"),
        (str(data_src / "ne_110m_admin_0_countries.geojson"), "data"),
        (str(data_src / "SOURCE.json"), "data"),
        (str(data_src / "icon.png"), "data"),
    ],
    hiddenimports=["matplotlib.backends.backend_qtagg"],
    excludes=["tkinter", "matplotlib.backends.backend_tkagg", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore"],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Mireille-Tuto",
    console=False,
    icon=icon_png,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Mireille-Tuto")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Mireille-Tuto.app",
        icon=icon_png,
        bundle_identifier="com.mireille.tuto",
        info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "1.0.0"},
    )
