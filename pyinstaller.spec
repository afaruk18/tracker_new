# -*- mode: python; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# -----------------------------------------------------------------------------
# Project paths (use cwd instead of __file__)
# -----------------------------------------------------------------------------
project_root = Path('.').resolve()
src_path     = project_root / "src"
sys.path.insert(0, str(src_path))

# Automatically include all submodules under your package
hidden_tracker = collect_submodules("tracker")

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    ['run_tracker.py'],
    pathex=[
        str(project_root),
        str(src_path)
    ],
    binaries=[],
    datas=[
        (str(project_root / 'assets'), 'assets'),
    ],
    hiddenimports=[
        *hidden_tracker,
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0
)

# -----------------------------------------------------------------------------
# Build the Python byte‑code archive
# -----------------------------------------------------------------------------
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

# -----------------------------------------------------------------------------
# Build the executable
# -----------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='tracker',
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
    icon=str(project_root / 'assets' / 'icon.ico')
)

# -----------------------------------------------------------------------------
# Collect into one‑folder bundle
# -----------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tracker'
)
