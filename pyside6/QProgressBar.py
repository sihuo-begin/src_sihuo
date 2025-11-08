
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSlider, QProgressBar, QPushButton
from PySide6.QtCore import Qt, QTimer

app = QApplication([])

widget = QWidget()
# widget.setGeometry(100, 100, 600, 600)
layout = QVBoxLayout(widget)

progress_bar = QProgressBar()
progress_bar.setRange(0,100)
progress_bar.setValue(0)
progress_bar.setFormat()

start_button = QPushButton("Start")
reset_button = QPushButton("Reset")

layout.addWidget(progress_bar)
layout.addWidget(start_button)
layout.addWidget(reset_button)

def simulate_task():
    current_value = progress_bar.value()
    new_value = current_value + 10
    if new_value > 100:
        new_value = 0
    progress_bar.setValue(new_value)

timer = QTimer()
timer.timeout.connect(simulate_task)

def start_task():
    timer.start(1000)

def reset_task():
    timer.stop()
    progress_bar.setValue(0)
start_button.clicked.connect(start_task)
reset_button.clicked.connect(reset_task)

widget.show()
app.exec()