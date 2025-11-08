
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSlider, QLabel
from PySide6.QtCore import Qt

app = QApplication([])

widget = QWidget()
widget.setGeometry(100, 100, 600, 600)
layout = QVBoxLayout(widget)


slider_horizontal = QSlider(Qt.Horizontal)
slider_horizontal.setRange(0,10000)
slider_horizontal.setSingleStep(1)
slider_horizontal.setValue(50)

slider_vertical = QSlider(Qt.Vertical)
slider_vertical.setRange(0,10000)
slider_vertical.setValue(50)
slider_vertical.setSingleStep(1)

label_horizontal = QLabel("Horizontal Slider Value: ")
label_vertical = QLabel("Vertical Slider Value: ")

slider_horizontal.valueChanged.connect(lambda value: label_horizontal.setText(f"Horizontal Slider Value: {value}"))
slider_vertical.valueChanged.connect(lambda  value: label_vertical.setText(f"Vertical Slider Value: {value}"))

layout.addWidget(label_horizontal)
layout.addWidget(slider_horizontal)
layout.addWidget(slider_vertical)
layout.addWidget(label_vertical)

widget.show()
app.exec()