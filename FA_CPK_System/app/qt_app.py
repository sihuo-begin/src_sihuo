import sys
from PyQt5.QtWidgets import QApplication
from app.ui_main import MainUI
from app.controller import Controller

def run_app():
    app = QApplication(sys.argv)
    ui = MainUI()
    controller = Controller(ui)   # ✅ 确保实例存在
    ui.show()
    sys.exit(app.exec_())
