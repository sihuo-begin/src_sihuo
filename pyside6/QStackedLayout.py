from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QLineEdit, QLabel, QStackedLayout
from PySide6.QtCore import Qt

app = QApplication([])
widget = QWidget()
layout = QStackedLayout(widget)
button1 = QPushButton("Page 1")
label1 = QLabel("Page 2")
layout.addWidget(button1)
layout.addWidget(label1)
layout.setCurrentIndex(0)
button1.clicked.connect(lambda: layout.setCurrentIndex(1))
widget.show()
app.exec()

