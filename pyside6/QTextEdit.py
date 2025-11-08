import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QSize

app = QApplication()

window = QWidget()
window.setWindowTitle("QTextEdit")

text_edit = QTextEdit()
layout = QVBoxLayout()
layout.addWidget(text_edit)
window.setLayout(layout)
window.setGeometry(100,100,400,300)
text_edit.cut()
text_edit.copy()
text_edit.paste()
window.show()
app.exec()
