from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSpinBox


app = QApplication([])

widget = QWidget()
layout = QVBoxLayout(widget)

spinbox = QSpinBox()
spinbox.setRange(0, 10000)
spinbox.setSingleStep(1)
spinbox.setValue(10000)
layout.addWidget(spinbox)
widget.show()
app.exec()
