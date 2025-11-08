import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QComboBox, QCheckBox

app = QApplication([])

window = QWidget()
window.setWindowTitle("Qcheckbox Example")
check_box = QCheckBox('Enable Feafure', window)
checked = check_box.isChecked()
check_box.setChecked(True)
# check_box.setEnabled(False)
# check_box.stateChanged.connect(my_function)
label_text = check_box.text()
checked_state = check_box.isChecked()
print(f"check_state is :{checked_state}")
layout = QVBoxLayout()
layout.addWidget(check_box)
window.setLayout(layout)
window.setGeometry(100,100,1200,700)
window.show()
sys.exit(app.exec_())
