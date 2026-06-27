"""
PyInstaller 启动钩子：把 utils/config.py 暴露到 exe 旁边让用户可改。

行为：
  - frozen mode (PyInstaller 打包)：
      1. 首次启动时，从 _MEIPASS (bundle 内部) 把 utils/config.py + __init__.py
         复制到 <exe 旁边>/utils/
      2. 把 <exe 旁边> 注入到 sys.path[0]，用户编辑生效
  - dev 模式（python main.py）：什么都不做，import 系统按源码加载

main.py 必须 import 这个文件 **作为第一行**（在所有 from utils... 之前）。
"""
import sys
import shutil
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _setup_user_config() -> None:
    """frozen mode 下首次启动复制 config.py 到 exe 旁边。"""
    meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    exe_dir = Path(sys.executable).parent.resolve()

    user_utils = exe_dir / "utils"
    user_config = user_utils / "config.py"
    user_init = user_utils / "__init__.py"

    bundle_config = meipass / "utils" / "config.py"
    bundle_init = meipass / "utils" / "__init__.py"

    user_utils.mkdir(parents=True, exist_ok=True)

    # First-run: copy config + __init__ to user-editable location
    if not user_config.exists() and bundle_config.exists():
        shutil.copy2(bundle_config, user_config)
    if not user_init.exists() and bundle_init.exists():
        shutil.copy2(bundle_init, user_init)

    # Inject user-editable dir to sys.path so `from utils.config import ...`
    # finds the user's config (not the frozen one).
    exe_dir_str = str(exe_dir)
    if exe_dir_str not in sys.path:
        sys.path.insert(0, exe_dir_str)


# Auto-run on import
if _is_frozen():
    try:
        _setup_user_config()
    except Exception as e:  # pragma: no cover
        # Don't kill the app — fall back to frozen config.
        sys.stderr.write(f"[bootstrap] WARN: could not set up user config: {e}\n")
