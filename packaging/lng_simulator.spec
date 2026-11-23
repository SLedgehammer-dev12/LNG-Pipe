# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for LNG Pipeline Flow Simulator (macOS arm64 & Windows x64)."""

from pathlib import Path
import sys
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    copy_metadata,
)

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "core"), "core"),
    (str(ROOT / "components"), "components"),
    (str(ROOT / "reports"), "reports"),
    (str(ROOT / "assets"), "assets"),
]
datas += collect_data_files("streamlit")
datas += collect_data_files("plotly")

for pkg in ("streamlit", "CoolProp", "plotly", "reportlab", "altair", "packaging"):
    datas += copy_metadata(pkg)

binaries = []
binaries += collect_dynamic_libs("CoolProp")

hiddenimports = [
    "CoolProp",
    "CoolProp.CoolProp",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "plotly",
    "reportlab",
    "reportlab.graphics.barcode",
    "reportlab.graphics.barcode.code128",
    "reportlab.graphics.barcode.code39",
    "reportlab.graphics.barcode.qr",
]

icon_path = str(
    ROOT / "packaging" / "icons" / ("icon.icns" if sys.platform == "darwin" else "icon.ico")
)

a = Analysis(
    [str(ROOT / "launcher_desktop.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy.tests"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LNG Simulator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="LNG Simulator",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="LNG Simulator.app",
        icon=icon_path,
        bundle_identifier="com.lng.pipeline.simulator",
        info_plist={
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "CFBundleDisplayName": "LNG Pipeline Flow Simulator",
        },
    )
