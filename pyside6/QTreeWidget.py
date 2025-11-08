from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTreeWidget, QPushButton, QLineEdit, QTreeWidgetItem

class TreeWidgetExample(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.add_button = QPushButton("ADD Item")

        self.layout.addWidget(self.tree_widget)
        self.layout.addWidget(self.add_button)

        self.tree_widget.setColumnCount(2)
        self.tree_widget.setHeaderLabels(["Name", "Value"])

        self.add_button.clicked.connect(self.add_item)


    def add_item(self):
        top_item = QTreeWidgetItem(self.tree_widget)
        top_item.setText(0, "Top Item")
        top_item.setText(1, "Value 1")

        child_item = QTreeWidgetItem(top_item)
        child_item.setText(0, "Child Item")
        child_item.setText(1, "Value 2")

        top_item.setExpanded(True)


if __name__ == "__main__":
    app = QApplication([])
    example = TreeWidgetExample()
    example.show()
    app.exec_()
