# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Specification for CoreSync Multicore Workstation Simulator.

Supports cross-platform single-folder and single-binary packaging across:
- Linux (x86_64, aarch64)
- Microsoft Windows (x86_64)
- Apple macOS (Intel, Apple Silicon)
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

SPEC_ROOT = Path(SPECPATH).resolve()

# Collect all package submodules
hidden_imports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "psutil",
    "numpy",
    "matplotlib",
    "engine.data_parallel",
    "engine.task_parallel",
    "engine.process_manager",
    "engine.process_scheduler",
    "engine.virtual_lab",
    "engine.analytics",
    "engine.comparison",
    "gui",
    "gui.components",
    "gui.real_system",
    "gui.virtual_lab",
    "utils",
    "utils.hardware",
    "monitoring",
]

# Assets and styling data
datas = [
    (str(SPEC_ROOT / "gui" / "styles.py"), "gui"),
]
if (SPEC_ROOT / "assets").exists():
    datas.append((str(SPEC_ROOT / "assets"), "assets"))

# Platform specific icon
icon_file = None
if sys.platform == "win32":
    win_icon = SPEC_ROOT / "assets" / "icons" / "coresync.ico"
    if win_icon.exists():
        icon_file = str(win_icon)
elif sys.platform == "darwin":
    mac_icon = SPEC_ROOT / "assets" / "icons" / "coresync.icns"
    if mac_icon.exists():
        icon_file = str(mac_icon)

a = Analysis(
    [str(SPEC_ROOT / "main.py")],
    pathex=[str(SPEC_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "IPython",
        "jupyter",
        "scipy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="coresync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="coresync",
)

# macOS App Bundle configuration
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CoreSync.app",
        icon=icon_file,
        bundle_identifier="org.academicos.coresync",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": "True",
            "NSRequiresAquaSystemAppearance": "False",
        },
    )

