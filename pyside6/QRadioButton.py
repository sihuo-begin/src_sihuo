
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QRadioButton



def my_print():
    print("Radio Button 1 Toggled")
app = QApplication([])

window = QWidget()
window.setWindowTitle("QRadioButton Example")
window.setGeometry(100,100, 300, 200)
radio_button1 = QRadioButton("Option 1", window)
radio_button2 = QRadioButton("Option 2", window)
radio_button1.setChecked(True)

print("Radio Button 1 Text:", radio_button1.text())
print("Is Radio Button 1 Checked:", radio_button1.isChecked())

radio_button1.toggled.connect(my_print)
layout = QVBoxLayout(window)
layout.addWidget(radio_button1)
layout.addWidget(radio_button2)
window.setLayout(layout)

window.show()
app.exec()
