# -*- mode: python; coding: utf-8 -*-
import sys, os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# -----------------------------------------------------------------------------
# 1) Make sure Pydantic settings don’t fail on missing DB env vars
# -----------------------------------------------------------------------------
for k in ("PG_USER","PG_PASS","PG_DATABASE","PG_HOST","PG_PORT"):
    os.environ.setdefault(k, "")

# -----------------------------------------------------------------------------
# 2) Compute project_root & assets path
# -----------------------------------------------------------------------------
# PyInstaller doesn’t define __file__, so use cwd
project_root = Path(os.getcwd()).resolve()

# Try both project_root/assets and one level up
assets_src = project_root / "assets"
if not assets_src.exists():
    assets_src = project_root.parent / "assets"

assert assets_src.exists(), f"Assets directory not found at {assets_src}"

# If your code is in src/, insert it
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Automatically include all submodules under tracker/
hidden_tracker = collect_submodules("tracker")

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    ['run_tracker.py'],                # or 'main.py' if that’s your entry
    pathex=[str(project_root), str(src_path)] if src_path.exists() else [str(project_root)],
    binaries=[],
    datas=[(str(assets_src), 'assets')],  # bundle the real assets folder
    hiddenimports=[
        *hidden_tracker,
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# -----------------------------------------------------------------------------
# Build byte‑code archive
# -----------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    icon=str(assets_src / 'icon.ico')  # assuming icon.ico lives in assets/
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
