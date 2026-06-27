from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal


class DebugControlWidget(QWidget):
    fixture_open = pyqtSignal()
    fixture_close = pyqtSignal()
    mode_setting = pyqtSignal()
    send_cmd = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        btn1 = QPushButton("Fixture Open")
        btn1.clicked.connect(self.fixture_open)
        btn2 = QPushButton("Fixture Close")
        btn2.clicked.connect(self.fixture_close)
        btn3 = QPushButton("Mode Setting")
        btn3.clicked.connect(self.mode_setting)
        btn4 = QPushButton("Send Cmd")
        btn4.clicked.connect(self.send_cmd)
        frame = QFrame()
        frame.setMaximumWidth(340)
        frame.setObjectName("debugFrame")
        frame.setStyleSheet(
            """
            QFrame#debugFrame {
                background: #f6fafd;
                border: 1.5px solid #e0e3e7;
                border-radius: 10px;
                padding: 10px 6px 14px 6px;
            }
        """
        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.addWidget(frame)

        inner_layout = QVBoxLayout(frame)
        inner_layout.setSpacing(4)
        inner_layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        title = QLabel("Debug Control")
        title.setStyleSheet("font-size:14px; font-weight:600; color:#1976d2; margin-bottom:4px;")
        inner_layout.addWidget(title, alignment=Qt.AlignLeft)

        # 按钮区，2列紧凑排布
        btn_grid = QGridLayout()
        btn_grid.setHorizontalSpacing(6)
        btn_grid.setVerticalSpacing(8)

        btn_style = """
            QPushButton {
                background: #fff;
                color: #1976d2;
                font-size:13px;
                font-weight: 600;
                border: 1.4px solid #1976d2;
                border-radius: 7px;
                padding: 3px 0px;
                min-width: 80px;
                min-height: 26px;
                max-width: 140px;
            }
            QPushButton:hover {
                background: #e3eafc;
                color: #1976d2;
                border: 2px solid #1976d2;
            }
            QPushButton:pressed {
                background: #1976d2;
                color: #fff;
            }
        """
        self.control_buttons = []
        btn_names = [
            ("Fixture Open", self.on_fixture_open),
            ("Fixture Close", self.on_fixture_close),
            ("Mode Setting", self.on_mode_setting),
            ("Send Cmd", self.on_send_cmd),
            ("reserve1", self.on_send_cmd),
            ("reserve2", self.on_send_cmd),
            ("reserve3", self.on_send_cmd),
            ("reserve4", self.on_send_cmd),
        ]
        # 2列布局
        for i, (name, slot) in enumerate(btn_names):
            btn = QPushButton(name)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(slot)
            btn_grid.addWidget(btn, i // 2, i % 2)
            self.control_buttons.append(btn)

        inner_layout.addLayout(btn_grid)
        inner_layout.addStretch(1)

    def set_buttons_enabled(self, enabled: bool):
        for btn in self.control_buttons:
            btn.setEnabled(enabled)

    # 示例按钮槽函数
    def on_fixture_open(self):
        print("Fixture Open")

    def on_fixture_close(self):
        print("Fixture Close")

    def on_mode_setting(self):
        print("Mode Setting")

    def on_send_cmd(self):
        print("Send Cmd")
