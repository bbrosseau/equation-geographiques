# -*- mode: python ; coding: utf-8 -*-
# Construction : uv run pyinstaller --clean --noconfirm equation_geographique.spec
# Résultat : dist/Equation-Geographique/ (Windows, Linux) et dist/Equation-Geographique.app (macOS).
import sys
from pathlib import Path

data_src = Path.cwd() / "src" / "equation_geographique" / "data"
icon_png = str(data_src / "icon.png")  # converti en .ico / .icns par PyInstaller (requiert Pillow)

a = Analysis(
    ["src/equation_geographique/__main__.py"],
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
    name="Equation-Geographique",
    console=False,
    icon=icon_png,
)

coll = COLLECT(exe, a.binaries, a.datas, name="Equation-Geographique")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Equation-Geographique.app",
        icon=icon_png,
        bundle_identifier="com.bbrosseau.equation-geographique",
        info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "1.0.0"},
    )
