# -*- mode: python; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# -----------------------------------------------------------------------------
# Project paths
# -----------------------------------------------------------------------------
project_root = Path(__file__).parent.resolve()
src_path     = project_root / "src"
sys.path.insert(0, str(src_path))  # so imports like "tracker.core" work

# Automatically include all submodules under tracker/
hidden_tracker = collect_submodules("tracker")

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    ['run_tracker.py'],                                 # your launcher script
    pathex=[                                           # where to look for imports
        str(project_root),
        str(src_path)
    ],
    binaries=[],                                       # no extra binary dependencies
    datas=[
        (str(project_root / 'assets'), 'assets'),      # bundle the entire assets/ folder
    ],
    hiddenimports=[                                    # force these into the build
        *hidden_tracker,
        'PIL._tkinter_finder',                        # for any Pillow‑Tk integration
    ],
    hookspath=[],                                      # add paths to any custom PyInstaller hooks
    hooksconfig={},
    runtime_hooks=[],                                  # e.g. for codec or logging tweaks
    excludes=[],                                       # modules to explicitly drop
    noarchive=False,                                   # keep the archive separate (faster startup)
    optimize=0                                         # leave bytecode at default optimization
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
    name='tracker',                                    # base name of created exe/folder
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                                          # compress with UPX if installed
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                                     # set True if you need a console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'icon.ico')    # your application icon
)

# -----------------------------------------------------------------------------
# Collect into a one‑folder bundle (dist/tracker/)
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
