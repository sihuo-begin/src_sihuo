import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QComboBox

app = QApplication(sys.argv)

window = QWidget()
window.setWindowTitle("QCombox Example")
layout = QVBoxLayout()
combo_box = QComboBox()
combo_box.addItem("one")
combo_box.addItem("two")
combo_box.addItem("three")

lable = QLabel('Please select on option!')

layout.addWidget(lable)
layout.addWidget(combo_box)

window.setLayout(layout)

def on_combox_changed(index):
    selected_text = combo_box.currentText()
    lable.setText(f"selected item is: {selected_text}")

combo_box.currentIndexChanged.connect(on_combox_changed)
window.show()
sys.exit(app.exec_())
