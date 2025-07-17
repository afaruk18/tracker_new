# -*- mode: python; coding: utf-8 -*-
import sys, os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# -----------------------------------------------------------------------------
# 1) Stub out missing PG_* env vars so Pydantic models import cleanly
# -----------------------------------------------------------------------------
for k in ("PG_USER","PG_PASS","PG_DATABASE","PG_HOST","PG_PORT"):
    os.environ.setdefault(k, "")

# -----------------------------------------------------------------------------
# 2) Compute project_root & src_path (use cwd so __file__ isn’t needed)
# -----------------------------------------------------------------------------
project_root = Path(os.getcwd()).resolve()
src_path     = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Automatically include all submodules under tracker/
hidden_tracker = collect_submodules("tracker")

# -----------------------------------------------------------------------------
# 3) Analysis – no datas/assets
# -----------------------------------------------------------------------------
a = Analysis(
    ["run_tracker.py"],                                # your entry‑point
    pathex=[str(project_root), str(src_path)] 
           if src_path.exists() else [str(project_root)],
    binaries=[],
    datas=[],                                          # <-- no assets
    hiddenimports=[*hidden_tracker, "PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# -----------------------------------------------------------------------------
# 4) Build the .pyz
# -----------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# -----------------------------------------------------------------------------
# 5) Build the executable
# -----------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="tracker",            # name of exe/folder
    debug=False,
    strip=False,
    upx=True,
    console=True,             # set True if you need a console
)

# -----------------------------------------------------------------------------
# 6) Collect into one‑folder bundle
# -----------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="tracker",
)
