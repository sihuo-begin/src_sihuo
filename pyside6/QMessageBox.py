from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget,QVBoxLayout, QMessageBox



class MessageBoxExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MessageBox Example")

        self.show_info_button = QPushButton("Show Info Message")
        self.show_warning_button = QPushButton("Show Warning Message")
        self.ask_question_button = QPushButton("Ask Question")

        layout = QVBoxLayout()

        layout.addWidget(self.show_info_button)
        layout.addWidget(self.show_warning_button)
        layout.addWidget(self.ask_question_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.show_info_button.clicked.connect(self.show_info_message)
        self.show_warning_button.clicked.connect(self.show_warning_message)
        self.ask_question_button.clicked.connect(self.ask_question)


    def show_info_message(self):
        QMessageBox.information(self, "Info", "This is an informattion message")


    def show_warning_message(self):
        QMessageBox.information(self, "Info", "This is a warning message")


    def ask_question(self):
        result = QMessageBox.question(self, "Question", "Do you want proceed?")

        if result == QMessageBox.Yes:
            print("user clicked yes.")
        else:
            print("user clicked No.")


if __name__ == "__main__":
    app = QApplication([])
    example = MessageBoxExample()
    example.show()
    app.exec()
