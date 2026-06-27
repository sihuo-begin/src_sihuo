#!/usr/bin/env python3
"""
PyInstaller 打包脚本 —— 把 utils/config.py 暴露给用户修改。

生成的 exe 首次启动时：
  1. 把 utils/config.py + __init__.py 从 bundle 复制到 <exe 旁边>/utils/
  2. 把 <exe 旁边> 注入 sys.path → 用户编辑 config.py 立即生效

打包产物（onedir 模式）：
  dist/M600099_GRR_CPK_Analyzer/
    ├── M600099_GRR_CPK_Analyzer.exe        ← 主程序
    ├── utils/                                ← 用户可改的 config 目录（首次启动自动生成）
    ├── _internal/                            ← PyInstaller 解压的依赖
    ├── templates/                            ← 用户可改的 report 模板目录（可选）
    └── report/                               ← Excel 模板（只读）

用法：
  python build_exe.py                # 默认 onedir 模式（推荐）
  python build_exe.py --onefile      # 单文件模式（启动慢）
  python build_exe.py --clean        # 清理 build/dist 再打包

要求：
  - Python 3.9+
  - pip install -r requirements.txt
  - Windows（也可在 Linux/macOS 上 cross-build，但需注意 win32com 等 Windows-only 依赖）
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()


# ── Hidden imports ────────────────────────────────────────────
# These are dynamic imports that PyInstaller can't see in static
# analysis. Without these, the bundled exe will fail with
# "ModuleNotFoundError" at runtime.
HIDDEN_IMPORTS = [
    # PyQt5 submodules (especially for QSS, QML, etc.)
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.sip",
    # easyocr (lazy-loaded)
    "easyocr",
    "easyocr.easyocr",
    "easyocr.config",
    "easyocr.detection",
    "easyocr.recognition",
    "easyocr.utils",
    # scipy/sklearn
    "scipy",
    "scipy.stats",
    "sklearn",
    # openpyxl (for Excel read/write)
    "openpyxl",
    "openpyxl.cell",
    "openpyxl.styles",
    "openpyxl.utils",
    # python-pptx (for AR&R chart extraction)
    "pptx",
    "pptx.util",
    "pptx.enum",
    "PIL",
    "PIL.Image",
    # pandas / numpy
    "pandas",
    "numpy",
    # xlrd (for reading legacy .xls if needed)
    "xlrd",
]

# ── Data files bundled into the exe ──────────────────────────
# Format: (source_path_relative_to_BASE_DIR, target_subdir_in_bundle)
DATA_FILES = [
    # utils package — config + package marker
    ("utils/__init__.py",    "utils"),
    ("utils/config.py",      "utils"),
    # Excel templates (read-only)
    ("report/GR_R_Template.xlsx", "report"),
    ("report/AR_R_Template.xlsx", "report"),
]

# ── Modules to exclude (shrink exe, avoid license issues) ─────
EXCLUDES = [
    "tkinter",      # we use PyQt5; tkinter is the fallback but excluded for size
    "matplotlib.tests",
    "numpy.tests",
    "pandas.tests",
    "scipy.tests",
    "PIL.tests",
]


def run(cmd, check=True):
    print(f"\n{'='*70}")
    print(f"  Running: {' '.join(str(c) for c in cmd)}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    if check and result.returncode != 0:
        print(f"\n[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result.returncode == 0


def clean():
    for d in [BASE_DIR / "build", BASE_DIR / "dist", BASE_DIR / "__pycache__"]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print(f"  Removed: {d}")
    for f in BASE_DIR.glob("*.spec.bak"):
        f.unlink()
    for d in BASE_DIR.rglob("__pycache__"):
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    for f in BASE_DIR.rglob("*.pyc"):
        f.unlink()


def build(onefile: bool = False):
    print("=" * 70)
    print(f"  Building M600099_GRR_CPK_Analyzer (mode={'onefile' if onefile else 'onedir'})")
    print("=" * 70)

    # ── PyInstaller base command ──
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "main.py",
        "--name=M600099_GRR_CPK_Analyzer",
        "--noconfirm",
        "--clean",
    ]

    # Windowed (no console)
    if sys.platform.startswith("win"):
        cmd.append("--windowed")
    else:
        cmd.append("--noconsole")

    # Mode
    if onefile:
        cmd.append("--onefile")
    else:
        # onedir (default) — easier to debug, faster startup
        pass

    # Paths
    cmd += [
        f"--distpath={BASE_DIR / 'dist'}",
        f"--workpath={BASE_DIR / 'build'}",
        f"--specpath={BASE_DIR}",
    ]

    # Data files
    sep = ";" if sys.platform.startswith("win") else ":"
    for src, dest in DATA_FILES:
        src_path = BASE_DIR / src
        if not src_path.exists():
            print(f"  [WARN] Skipping missing data file: {src}")
            continue
        # On Windows, paths with backslashes confuse PyInstaller; use forward slashes
        cmd.append(f"--add-data={src_path.as_posix()}{sep}{dest}")
        print(f"  add-data: {src} → {dest}/")

    # Hidden imports
    for mod in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={mod}")

    # Excludes
    for mod in EXCLUDES:
        cmd.append(f"--exclude-module={mod}")

    # Collect subpackages
    cmd += [
        "--collect-submodules=easyocr",
        "--collect-submodules=PIL",
    ]

    run(cmd)

    # ── Post-build summary ──
    dist_dir = BASE_DIR / "dist" / "M600099_GRR_CPK_Analyzer"
    exe_name = "M600099_GRR_CPK_Analyzer.exe" if sys.platform.startswith("win") else "M600099_GRR_CPK_Analyzer"
    exe_path = dist_dir / exe_name

    if onefile:
        exe_path = BASE_DIR / "dist" / exe_name

    print("\n" + "=" * 70)
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"  ✅ Build successful!")
        print(f"     Executable: {exe_path}")
        print(f"     Size:       {size_mb:.1f} MB")
        if not onefile:
            print(f"     Bundle dir: {dist_dir}")
            print()
            print(f"  📝 Next steps:")
            print(f"     1. cd {dist_dir}")
            print(f"     2. Run {exe_name} once to auto-create utils/config.py")
            print(f"     3. Edit utils/config.py to change:")
            print(f"        - inspector_numbers: ['2572744', '693109', '2566142']")
            print(f"        - reported_by: 'Simon Huo'")
            print(f"        - part_number, instrument, LED specs, etc.")
            print(f"     4. Re-run the exe — your changes are picked up live")
    else:
        print(f"  ⚠️  Exe not found at {exe_path}")
        print(f"     Check the build output above for errors.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onefile", action="store_true",
                        help="Build a single-file exe (slower startup, easier to share)")
    parser.add_argument("--clean", action="store_true",
                        help="Remove build/ and dist/ first")
    args = parser.parse_args()

    if args.clean:
        print("Cleaning build artifacts...")
        clean()

    build(onefile=args.onefile)
