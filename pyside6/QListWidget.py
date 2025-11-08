from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QSlider, QListWidget, QPushButton, QLineEdit, QListWidgetItem

class ListWidgetExample(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.add_button = QPushButton("ADD Item")
        self.remove_button = QPushButton("Remove Selected Item")
        self.clear_button = QPushButton("Clear All")
        self.input_text = QLineEdit()

        self.input_text.setPlaceholderText("Enter Text to add")

        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.remove_button)
        self.layout.addWidget(self.input_text)

        self.add_button.clicked.connect(self.add_item)
        self.remove_button.clicked.connect(self.remove_selected_item)
        self.clear_button.clicked.connect(self.clear_all)

        self.list_widget.itemClicked.connect(self.item_clicked)


    def add_item(self):
        text = self.input_text.text()
        if text:
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
            self.input_text.clear()


    def remove_selected_item(self):
        selected_item = self.list_widget.currentItem()
        if selected_item:
            self.list_widget.takeItem(self.list_widget.row(selected_item))


    def clear_all(self):
        self.list_widget.clear()


    def item_clicked(self, item):
        print(f"Clicked on item: {item.test()}")

if __name__ == "__main__":
    app = QApplication([])
    example = ListWidgetExample()
    example.show()
    app.exec_()
