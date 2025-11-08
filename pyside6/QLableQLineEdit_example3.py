from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QLineEdit, QLabel, QLineEdit, QVBoxLayout
from PySide6.QtGui import  QPixmap
from PySide6.QtCore import Qt

app = QApplication([])
widget = QWidget()
widget.setGeometry(100, 100, 200, 200)
layout = QVBoxLayout(widget)

line_edit = QLineEdit()
layout.addWidget(line_edit)
line_edit.setPlaceholderText("Enter text Here")

widget.show()
app.exec()

