# ──────────────────────────────────────────────
#  UI Package
#  (PyQt5 is used when available; falls back to tkinter)
# ──────────────────────────────────────────────

try:
    from PyQt5.QtWidgets import QApplication
    UI_BACKEND = "PyQt5"
except ImportError:
    UI_BACKEND = "tkinter"

__all__ = ["UI_BACKEND"]
