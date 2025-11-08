from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QFileDialog

class FileDialogExample(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.open_button = QPushButton("Open File Dialog")

        self.layout.addWidget(self.open_button)

        self.open_button.clicked.connect(self.show_file_dialog)


    def show_file_dialog(self):
        file_dialog = QFileDialog(self)

        file_dialog.setWindowTitle("Choose a file")

        file_dialog.setFileMode(QFileDialog.ExistingFile)

        selected_file, _ = file_dialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt)")

        if selected_file:
            print(f"Selected file: {selected_file}")

if __name__ == "__main__":
    app = QApplication([])
    example = FileDialogExample()
    example.show()
    app.exec()
