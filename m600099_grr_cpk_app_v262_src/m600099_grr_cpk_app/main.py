# ──────────────────────────────────────────────
#  M600099 GRR & CPK Analyzer  –  Main Entry Point
# ──────────────────────────────────────────────
#  bootstrap MUST be the first import — it sets up the
#  user-editable utils/config.py when running as a frozen
#  PyInstaller exe (so end users can edit inspector numbers,
#  reported_by, LED specs, etc. without re-packaging).
import bootstrap  # noqa: F401
import sys
import logging
from pathlib import Path

# ── Detect UI backend ──
UI_BACKEND = None
_import_err = None
try:
    from PyQt5.QtWidgets import QApplication, QMainWindow
    UI_BACKEND = "PyQt5"
    from ui.main_window import MainWindow as _MainWindow
except ImportError as e:
    UI_BACKEND = "tkinter"
    _import_err = f"ImportError: {e}"
    from ui.tkinter_window import launch as _launch
except Exception as e:
    # Other errors (e.g. Qt platform plugin missing) → try tkinter but log details
    import traceback as _tb
    UI_BACKEND = "tkinter"
    _import_err = f"{type(e).__name__}: {e}\n{_tb.format_exc()}"
    from ui.tkinter_window import launch as _launch

# ── Logging ──
BASE_DIR = Path(__file__).parent.resolve()
LOG_FILE = BASE_DIR / "app.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def excepthook(type_, value, tb):
    import traceback
    msg = "".join(traceback.format_exception(type_, value, tb))
    logging.critical(f"Unhandled exception:\n{msg}")
    if UI_BACKEND == "tkinter":
        import tkinter as tk
        from tkinter import messagebox
        try:
            messagebox.showerror("Unexpected Error", msg)
        except Exception:
            pass
    else:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Unexpected Error", msg)


sys.excepthook = excepthook


if __name__ == "__main__":
    from utils.config import APP_NAME, APP_VERSION, AUTHOR

    logging.info(f"{APP_NAME} v{APP_VERSION} ({UI_BACKEND} backend) starting…")
    if _import_err:
        logging.warning(f"PyQt5 not available ({_import_err.strip()}), using tkinter.")

    if UI_BACKEND == "tkinter":
        _launch()
    else:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt

        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        win = _MainWindow()
        win.show()

        sys.exit(app.exec_())
