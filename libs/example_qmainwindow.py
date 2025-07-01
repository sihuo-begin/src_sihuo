import sys
from random import choice

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton

window_titles = [
    "My App",
    "My App",
    "Still My App",
    "Still My App",
    "What on earth",
    "What on earth",
    "This is surprising",
    "This is surprising",
    "Something went wrong",
]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.n_times_clicked = 0
        self.setWindowTitle('my application')
        self.button = QPushButton('Click me')
        self.button.clicked.connect(self.the_button_was_clicked)

        self.windowTitleChanged.connect(self.the_window_title_changed)
        # self.setFixedSize(QSize(800, 600))
        self.setCentralWidget(self.button)

    def the_window_title_changed(self, window_title):
        print("windwon title changed %s" % window_title)
        if window_title == "Something went wrong":
            self.button.setDisabled(True)

    def the_button_was_clicked(self):
        print('Clicked')
        new_window_title = choice(window_titles)
        print("seting title to %s"% new_window_title)
        self.setWindowTitle(new_window_title)

app = QApplication(sys.argv)
window = QMainWindow()
window.show()
app.exec()