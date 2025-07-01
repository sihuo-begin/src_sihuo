import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QToolBar
from PySide6.QtCore import Qt, QSize

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('my application')
        # self.setWindowIcon(QIcon('QIcon.png'))
        self.button = QPushButton('Push button')
        self.setCentralWidget(self.button)
        self.setFixedSize(QSize(200,300))
        self.button.clicked.connect(self.the_button_was_clicked())
        # self.button.setCheckable(True)
        # self.button.released.connect(self.the_button_was_released)
        # self.button.setCheckable(self.button.isChecked())
        # self.button.clicked.connect(self.the_button_was_clicked)
        # self.button.clicked.connect(self.the_button_was_togglde)
        # self.setMaximumSize(QSize(20000, 10000))
        # self.setMinimumSize(QSize(20000, 10000))

    def the_button_was_clicked(self,):
        self.button.setText('You already clicked me')
        self.button.setEnabled(False)
        self.setWindowTitle('my oneshot application')
        print(self.button.isChecked())

    # def the_button_was_togglde(self, checked):
    #     self.button_is_checked = checked
    #
    #     print(self.button_is_checked)
    #
    # def the_button_was_released(self):
    #     self.button_is_checked = self.button.isChecked()
    #     print(self.button_is_checked)
app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
