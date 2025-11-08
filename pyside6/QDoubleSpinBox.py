
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSpinBox, QDoubleSpinBox


app = QApplication([])

widget = QWidget()
layout = QVBoxLayout(widget)

spinbox = QDoubleSpinBox()
spinbox.setRange(0.0, 10000.0)
spinbox.setSingleStep(0.1)
spinbox.setValue(10000)
layout.addWidget(spinbox)
widget.show()
app.exec()