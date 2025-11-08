from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QPushButton, QVBoxLayout
app = QApplication([])
widget = QWidget()
# widget.saveGeometry(300,300,400,200)
widget.setGeometry(300,300,400,200)
layout = QVBoxLayout(widget)
button1 = QPushButton("Button 1")
button2 = QPushButton("Button 2")
layout.addWidget(button1)
layout.addWidget(button2)
widget.show()
app.exec()

