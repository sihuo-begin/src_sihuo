from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget,QVBoxLayout, QCalendarWidget


class CalendarWidgetExample(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calendar Widget Example")
        layout = QVBoxLayout(self)

        calendar_widget = QCalendarWidget()

        layout.addWidget(calendar_widget)


if __name__ == "__main__":
    app = QApplication([])
    example = CalendarWidgetExample()
    example.show()
    app.exec()

# import sys
# from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget, QCalendarWidget, QLabel
#
#
# class CalendarApp(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.setWindowTitle("日期选择器")
#
#         # 设置主布局
#         self.layout = QVBoxLayout()
#
#         # 创建日历组件
#         self.calendar = QCalendarWidget(self)
#         self.layout.addWidget(self.calendar)
#
#         # 创建标签用于显示选择的日期
#         self.label = QLabel("选择的日期: ", self)
#         self.layout.addWidget(self.label)
#
#         # 创建按钮以获取选择的日期
#         self.button = QPushButton("获取选择的日期", self)
#         self.button.clicked.connect(self.show_selected_date)
#         self.layout.addWidget(self.button)
#
#         # 设置中心小部件
#         container = QWidget()
#         container.setLayout(self.layout)
#         self.setCentralWidget(container)
#
#     def show_selected_date(self):
#         selected_date = self.calendar.selectedDate().toString()
#         self.label.setText(f"选择的日期: {selected_date}")
#
#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = CalendarApp()
#     window.resize(400, 300)
#     window.show()
#     sys.exit(app.exec())