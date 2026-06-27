from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QDesktopWidget,
    QWidget,
    QComboBox,
)
from src.definition.product_mapping import stations_mapping
import os
import sys


class LoginForm(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = None
        self.setObjectName("loginWindow")
        self.setStyleSheet("#loginWindow{background-color:white}")
        self.setFixedSize(650, 410)
        self.setWindowTitle("Login")
        if hasattr(sys, "_MEIPASS"):
            self.base_file_path = sys._MEIPASS
            self.seq_dir = os.path.join(self.base_file_path, "src", "ui", "static")
        else:
            self.seq_dir = os.path.abspath("src/ui/static")
        logo_path = os.path.join(self.seq_dir, "utp_icon.png")
        self.setWindowIcon(QIcon(logo_path))
        self._initUI()

    def _initUI(self):
        head_image_path = os.path.join(self.seq_dir, "energy.jpeg")
        pixmap = QPixmap(head_image_path).scaled(650, 100)
        logo_label = QLabel()
        logo_label.setPixmap(pixmap)

        lbl_logo = QLabel("J-Universal AutoTest Platform Login")
        lbl_logo.setStyleSheet(
            """
            QLabel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4e54c8,  /* 深蓝色 */
                    stop: 0.5 #8f94fb, /* 柔和亮蓝过渡色 */
                    stop: 1 #32e3b2   /* 青绿色 */
                );
                font-weight: bold;
                color: white;
                font-size: 32px;
                letter-spacing: 1px;
                padding: 6px;
            }
        
            QLabel:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1px-(Transparency alpha-value   
                     drop-inside npm commands
        """
        )
        lbl_logo.setFont(QFont("Microsoft YaHei", 30, QFont.Bold))
        lbl_logo.setAlignment(Qt.AlignCenter)

        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(0)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(lbl_logo)

        # 登录表单部分
        login_widget = QWidget(self)
        login_widget.setFixedHeight(200)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(30, 20, 30, 20)
        hbox.setSpacing(0)

        # 左侧logo
        logolb = QLabel()
        login_path = os.path.join(self.seq_dir, "login3.png")
        logopix = QPixmap(login_path).scaled(180, 120)
        logolb.setPixmap(logopix)
        logolb.setAlignment(Qt.AlignCenter)
        hbox.addWidget(logolb, 1)

        # 右侧表单
        fmlayout = QFormLayout()
        fmlayout.setLabelAlignment(Qt.AlignRight)
        fmlayout.setFormAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        fmlayout.setHorizontalSpacing(20)
        fmlayout.setVerticalSpacing(16)

        self.cmb_product = QComboBox()
        self.cmb_product.setFixedWidth(260)
        self.cmb_product.setFixedHeight(38)
        # 添加产品选项
        self.cmb_product.addItems(stations_mapping.keys())
        self.cmb_product.setCurrentIndex(0)
        self.cmb_product.setStyleSheet(
            """
        QComboBox {
            border: 1px solid #2c7adf;
            border-radius: 4px;
            padding: 6px 20px 6px 8px;
            min-width: 6em;
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            color: #222;
            background: #f6faff;
        }
        QComboBox:focus {
            border: 2px solid #2c7adf;
            outline: none;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #2c7adf;
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            selection-background-color: #2c7adf;
            selection-color: white;
        }
        QComboBox QAbstractItemView::item {
            height: 34px;
            padding-left: 8px;
            color: #222;
        }
        QComboBox QAbstractItemView::item:selected {
            background: #2c7adf;
            color: white;
        }
        """
        )
        self.cmb_product.currentIndexChanged.connect(self.update_stations)  # 更新站点

        self.cmb_station = QComboBox()
        self.cmb_station.setFixedWidth(260)
        self.cmb_station.setFixedHeight(38)
        self.cmb_station.setStyleSheet(
            """
        QComboBox {
            border: 1px solid #2c7adf;
            border-radius: 4px;
            padding: 6px 20px 6px 8px;
            min-width: 6em;
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            color: #222;
            background: #f6faff;
        }
        QComboBox:focus {
            border: 2px solid #2c7adf;
            outline: none;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #2c7adf;
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            font-size: 14px;
            selection-background-color: #2c7adf;
            selection-color: white;
        }
        QComboBox QAbstractItemView::item {
            height: 34px;
            padding-left: 8px;
            color: #222;
        }
        QComboBox QAbstractItemView::item:selected {
            background: #2c7adf;
            color: white;
        }
        """
        )
        self.update_stations()  # 初始化station选项

        self.led_workerid = QLineEdit()
        self.led_workerid.setFixedWidth(260)
        self.led_workerid.setFixedHeight(38)

        self.led_pwd = QLineEdit()
        self.led_pwd.setEchoMode(QLineEdit.Password)
        self.led_pwd.setFixedWidth(260)
        self.led_pwd.setFixedHeight(38)

        self.btn_login = QPushButton("Login:")
        self.btn_login.setFixedWidth(260)
        self.btn_login.setFixedHeight(40)
        self.btn_login.setFont(QFont("Microsoft YaHei"))
        self.btn_login.setObjectName("login_btn")
        self.btn_login.setStyleSheet(
            "#login_btn{background-color:#2c7adf; color:#fff; border:none; border-radius:4px; font-size: 18px;}"
        )
        self.btn_login.clicked.connect(self._login)

        font_label = QFont("Microsoft YaHei", 10)
        font_edit = QFont("Microsoft YaHei", 10)
        font_button = QFont("Microsoft YaHei", 10, QFont.Bold)

        Product = QLabel("Product:")
        Product.setFont(font_label)
        label_station = QLabel("Station:")
        label_station.setFont(font_label)
        label_user = QLabel("User:")
        label_user.setFont(font_label)
        label_pwd = QLabel("Password:")
        label_pwd.setFont(font_label)

        self.cmb_station.setFont(font_edit)
        self.led_workerid.setFont(font_edit)
        self.led_pwd.setFont(font_edit)
        self.btn_login.setFont(font_button)

        fmlayout.addRow(Product, self.cmb_product)
        fmlayout.addRow(label_station, self.cmb_station)
        fmlayout.addRow(label_user, self.led_workerid)
        fmlayout.addRow(label_pwd, self.led_pwd)
        fmlayout.addWidget(self.btn_login)
        self.led_workerid.returnPressed.connect(self.btn_login.click)
        self.led_pwd.returnPressed.connect(self.btn_login.click)

        hbox.addLayout(fmlayout, 2)
        login_widget.setLayout(hbox)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(logo_layout)
        main_layout.addWidget(login_widget)

        copyright_label = QLabel("Copyright © 2025 Ja All rights reserved.")
        copyright_label.setAlignment(Qt.AlignRight)
        copyright_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        main_layout.addWidget(copyright_label)
        self.setLayout(main_layout)
        self.center()
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def update_stations(self):
        product = self.cmb_product.currentText()
        self.cmb_station.clear()
        if product in stations_mapping:
            self.cmb_station.addItems(stations_mapping[product].keys())

    def _login(self):
        product = self.cmb_product.currentText().strip()
        station = self.cmb_station.currentText().strip()
        user = self.led_workerid.text().strip()
        pwd = self.led_pwd.text().strip()
        if not product:
            QMessageBox.warning(self, "Warning", "Input product name")
            return
        if not station:
            QMessageBox.warning(self, "Warning", "Input station name")
            return
        if not user:
            QMessageBox.warning(self, "Warning", "Input user")
            return
        if not pwd:
            QMessageBox.warning(self, "Warning", "Input password")
            return
        if user != "10001" or pwd != "123":
            QMessageBox.warning(self, "Warning", "User/Password error")
            return
        self.username = user
        self.product = product
        self.station = station
        self.accept()
