from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar
from PySide6.QtGui import QAction

class ToolbarExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Toolbar Example")

        self.toolbar = QToolBar("Main Toolbar")

        action_open = QAction("Open",self)
        action_save = QAction("Save", self)
        action_cut = QAction("Cut", self)
        action_paste = QAction("Paste", self)
        action_copy = QAction("Copy", self)


        self.toolbar.addAction(action_open)
        self.toolbar.addAction(action_save)
        self.toolbar.addSeparator()
        self.toolbar.addAction(action_cut)
        self.toolbar.addAction(action_copy)
        self.toolbar.addAction(action_paste)

        self.addToolBar(self.toolbar)

if __name__ == "__main__":
    app = QApplication([])
    example = ToolbarExample()
    example.show()
    app.exec()
