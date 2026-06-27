# ──────────────────────────────────────────────
#  M600099 GRR & CPK Analyzer  –  Main Entry Point
# ──────────────────────────────────────────────
import sys
import logging
from pathlib import Path

# ── Detect UI backend ──
try:
    from PyQt5.QtWidgets import QApplication, QMainWindow
    UI_BACKEND = "PyQt5"
    from ui.main_window import MainWindow as _MainWindow
except ImportError:
    UI_BACKEND = "tkinter"
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
