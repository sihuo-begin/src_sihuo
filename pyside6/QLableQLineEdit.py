from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QLineEdit, QLabel, QGridLayout

from pyside6.QFormLayout import line_edit1

app = QApplication([])
widget = QWidget()
widget.setGeometry(100, 100, 300, 200)
layout = QGridLayout(widget)
label1 = QLabel("Name:")
label2 = QLabel("Password:")
line_edit1 = QLineEdit()
line_edit2 = QLineEdit()
layout.addWidget(label1, 0, 0)
layout.addWidget(label2, 1, 0)
# layout.addWidget(line_edit2, 0, 1)
layout.addWidget(line_edit1, 0, 1)
layout.addWidget(line_edit2, 1, 1)
widget.show()
app.exec()

