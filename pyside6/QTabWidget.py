from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTabWidget, QLabel, QTextEdit

class TabWidgetExample(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()


        tab1 = QWidget()
        tab2 = QWidget()

        label_tab1 = QLabel("This is Tab 1")
        text_edit_tab2 = QTextEdit()

        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.addWidget(label_tab1)

        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.addWidget(text_edit_tab2)

        self.tab_widget.addTab(tab1, "Tabel 1")
        self.tab_widget.addTab(tab2, "Tabel 1")

        self.layout.addWidget(self.tab_widget)


if __name__ == "__main__":
    app = QApplication([])
    example = TabWidgetExample()
    example.show()
    app.exec_()
