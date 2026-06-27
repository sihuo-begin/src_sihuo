# from PyQt5.QtWidgets import *
# from PyQt5.QtCore import Qt
#
# class MainUI(QWidget):
#
#     def __init__(self):
#         super().__init__()
#
#         self.setWindowTitle("CPK + GRR System")
#         self.resize(900, 600)
#
#         main_layout = QVBoxLayout()
#
#         # 顶部
#         self.btn_select = QPushButton("选择JSON文件夹")
#         self.folder_label = QLabel("未选择")
#
#         # 中间双窗口
#         mid_layout = QHBoxLayout()
#
#         # 左：全部items
#         left_layout = QVBoxLayout()
#         left_layout.addWidget(QLabel("全部Items"))
#
#         self.item_list = QListWidget()
#         left_layout.addWidget(self.item_list)
#
#         # 右：已选items
#         right_layout = QVBoxLayout()
#         right_layout.addWidget(QLabel("已选Items"))
#
#         self.selected_list = QListWidget()
#         right_layout.addWidget(self.selected_list)
#
#         mid_layout.addLayout(left_layout)
#         mid_layout.addLayout(right_layout)
#
#         # 控制
#         self.chk_cpk = QCheckBox("CPK")
#         self.chk_cpk.setChecked(True)
#         self.chk_grr = QCheckBox("GRR")
#
#         self.btn_run = QPushButton("开始")
#
#         self.log = QTextEdit()
#
#         main_layout.addWidget(self.btn_select)
#         main_layout.addWidget(self.folder_label)
#         main_layout.addLayout(mid_layout)
#         main_layout.addWidget(self.chk_cpk)
#         main_layout.addWidget(self.chk_grr)
#         main_layout.addWidget(self.btn_run)
#         main_layout.addWidget(self.log)
#
#         self.setLayout(main_layout)
from PyQt5.QtWidgets import *

class MainUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("FA CPK System")
        self.resize(900, 600)

        layout = QVBoxLayout()

        self.btn_select = QPushButton("选择JSON目录")
        self.folder_label = QLabel("未选择")

        # ===== 中间双窗口 =====
        mid = QHBoxLayout()

        self.item_list = QListWidget()
        self.selected_list = QListWidget()

        mid.addWidget(self.item_list)
        mid.addWidget(self.selected_list)

        # ===== 控制 =====
        self.btn_run = QPushButton("开始分析")
        self.progress = QProgressBar()

        self.log = QTextEdit()

        layout.addWidget(self.btn_select)
        layout.addWidget(self.folder_label)
        layout.addLayout(mid)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

        self.setLayout(layout)