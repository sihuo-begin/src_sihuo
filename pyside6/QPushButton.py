from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QLineEdit, QLabel, QLineEdit, QVBoxLayout
from PySide6.QtGui import  QPixmap
from PySide6.QtCore import Qt
def on_button_click(self):
    print("button is clicked")
app = QApplication([])
widget = QWidget()
widget.setGeometry(100, 100, 200, 200)
layout = QVBoxLayout(widget)

button = QPushButton("按钮")
layout.addWidget(button)
# button.setEnabled(False)
button.setShortcut("Ctrl+C")
# button.hitButton(True)
button.setStyleSheet("QPushButton {background-color: red;}")
button.setAutoRepeat(True)
button.setAutoRepeatInterval(500)
button.clicked.connect(on_button_click)
widget.show()
app.exec()

