import sys
import os

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QFileDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QMessageBox
)

from core.data_loader import  DataLoader
from core.data_loader import DataLoader
from core.cpk import CpkAnalyzer
from core.grr import GrrAnalyzer
from core.minitab import MinitabRunner
from report.excel import ExcelReport
from config import CONFIG


class FAToolApp(QWidget):

    def __init__(self):
        super().__init__()
        self.file_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("FA 自动分析工具（企业版）")
        self.setGeometry(300, 200, 420, 260)

        layout = QVBoxLayout()

        # ===== 文件选择 =====
        file_layout = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        btn_file = QPushButton("浏览")

        btn_file.clicked.connect(self.select_file)

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(btn_file)

        # ===== 参数输入 =====
        spec_layout = QHBoxLayout()

        self.usl_input = QLineEdit(str(CONFIG["spec"]["USL"]))
        self.lsl_input = QLineEdit(str(CONFIG["spec"]["LSL"]))

        spec_layout.addWidget(QLabel("USL"))
        spec_layout.addWidget(self.usl_input)
        spec_layout.addWidget(QLabel("LSL"))
        spec_layout.addWidget(self.lsl_input)

        # ===== 按钮 =====
        self.run_btn = QPushButton("生成 FA 报告")
        self.run_btn.clicked.connect(self.run_analysis)

        # ===== 状态 =====
        self.status_label = QLabel("状态：待机")

        layout.addLayout(file_layout)
        layout.addLayout(spec_layout)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择CSV", "", "CSV Files (*.csv)")
        if file:
            self.file_path = file
            self.file_label.setText(os.path.basename(file))

    def run_analysis(self):

        if not self.file_path:
            QMessageBox.warning(self, "错误", "请先选择CSV文件")
            return

        try:
            self.status_label.setText("状态：分析中...")
            # ✅ 1. 数据加载
            loader = DataLoader(self.file_path)
            df = loader.load()

            # ✅ 2. 初始化分析器（你问的就在这里 ✅）
            cpk_analyzer = CpkAnalyzer(CONFIG)
            grr_analyzer = GrrAnalyzer(CONFIG)

            # ✅ 3. CPK（多列分析 + 出图）
            print(self.file_path, cpk_analyzer)
            cpk_results = cpk_analyzer.run_minitab_multi(self.file_path)

            # ✅ 4. GRR（分析 + 出图）
            grr_result = grr_analyzer.run_minitab(self.file_path)

            # ✅ 5. Python计算（用于Summary）
            cpk_calc = cpk_analyzer.calculate_multi(df)

            output_path = os.path.join(
                CONFIG["paths"]["reports"],
                os.path.basename(self.file_path).replace(".csv", "_FA.xlsx")
            )

            # ✅ 7. 生成Excel
            report = ExcelReport(CONFIG)
            report.generate(
                output_path,
                df,
                # cpk_calc,  # 用计算结果写数值
                cpk_results,
                grr_result  # 结果 + 图路径
            )

            self.status_label.setText("✅ 完成")

            QMessageBox.information(self, "完成", f"报告已生成:\n{output_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))


def run_app():
    app = QApplication(sys.argv)
    window = FAToolApp()
    window.show()
    sys.exit(app.exec_())