from PySide6.QtWidgets import QApplication, QWidget,  QPushButton, QFormLayout, QLineEdit, QLabel
from PySide6.QtCore import Qt
app = QApplication([])
widget = QWidget()
layout = QFormLayout(widget)
label1 = QLabel("Name:")
line_edit1 = QLineEdit()
label2 = QLabel("Age:")
line_edit2 = QLineEdit()
layout.addRow(label1, line_edit1)
layout.addRow(label2, line_edit2)
layout.setHorizontalSpacing(15)
layout.setVerticalSpacing(10)
widget.show()
app.exec()

