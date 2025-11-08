from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QLineEdit, QLabel, QGridLayout, QVBoxLayout
from PySide6.QtGui import  QPixmap
from PySide6.QtCore import Qt

app = QApplication([])
widget = QWidget()
widget.setGeometry(100, 100, 200, 200)
layout = QVBoxLayout(widget)


label = QLabel()
layout.addWidget(label)
label.setText("这是一个演示这是一个演示这是一个演示这是一个演示")
label.setAlignment(Qt.AlignCenter)
# label.setAlignment(Qt.AlignLeft)
label.setIndent(20)
label.setMargin(10)
# pixmap = QPixmap("123.png")
# label.setPixmap(pixmap)
label.setTextFormat(Qt.RichText)
label.setWordWrap(True)
widget.show()
app.exec()

