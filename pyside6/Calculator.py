import sys
from cgitb import enable

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QTabWidget,QGridLayout,
                               QLabel, QComboBox)



class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计算器")

        self.tabs = QTabWidget()
        # self.setGeometry(100, 100, 600, 600)
        self.setCentralWidget(self.tabs)

        self.standard_calculator()
        self.programmer_calculator()
        self.scientific_calculator()

        self.show()

    def standard_calculator(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.display = QLineEdit()
        layout.addWidget(self.display)

        buttons = {
            0: ['7', '8', '9', '/'],
            1: ['4', '5', '6', '*'],
            2: ['1', '2', '3', '-'],
            3: ['0', 'C', '=', '+']
        }

        # grid_layout = QVBoxLayout()
        grid_layout = QGridLayout()
        for key in buttons:
            for i in range(len(buttons[key])):
                btn = QPushButton(buttons[key][i])
                # if btn.isChecked:
                #     btn.setStyleSheet("QPushButton {background-color: green;}")
                btn.clicked.connect(self.on_button_click)
                btn.setStyleSheet("QPushButton {background-color: white;}")
                grid_layout.addWidget(btn, key, i)

        layout.addLayout(grid_layout)
        tab.setLayout(layout)
        self.tabs.addTab(tab, "标准计算器")

    def programmer_calculator(self):
        tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("程序员计算器 (功能实现中)"))
        self.tabs.addTab(tab, "程序员计算器")

    def scientific_calculator(self):
        tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("科学计算器 (功能实现中)"))
        self.tabs.addTab(tab, "科学计算器")

    def on_button_click(self):
        button_text = self.sender().text()
        if button_text == "C":
            self.display.clear()
        elif button_text == "=":
            try:
                result = eval(self.display.text())
                self.display.setText(str(result))
            except Exception:
                self.display.setText("错误")
        else:
            current_text = self.display.text()
            new_text = current_text + button_text
            self.display.setText(new_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    calculator = Calculator()
    sys.exit(app.exec())