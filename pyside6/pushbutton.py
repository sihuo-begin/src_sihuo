import sys

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

app = QApplication(sys.argv)
window = QPushButton('Push button')
window.windowTitle()
window.show()
app.exec()