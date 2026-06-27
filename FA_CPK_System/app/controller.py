# import os
# from PyQt5.QtWidgets import QFileDialog
# from PyQt5.QtCore import Qt
# from PyQt5.QtWidgets import QListWidgetItem
#
#
# from core.item_detector import ItemDetector
# from core.data_builder import DataBuilder
# from core.analysis_runner import AnalysisRunner
# # from core.minitab_runner import MinitabRunner
# from core.report_builder import ReportBuilder
#
#
# class Controller:
#
#     def __init__(self, ui):
#         self.ui = ui
#         self.folder = None
#         self.detector = ItemDetector()
#
#         print("✅ Controller 初始化")   # ✅ debug
#
#         self.ui.btn_select.clicked.connect(self.load_folder)
#         self.ui.btn_run.clicked.connect(self.run)
#
#     def log(self, txt):
#         self.ui.log.append(txt)
#
#     from PyQt5.QtCore import Qt
#     from PyQt5.QtWidgets import QListWidgetItem
#
#     def load_folder(self):
#
#         folder = QFileDialog.getExistingDirectory(
#             self.ui, "选择JSON文件夹", "", QFileDialog.ShowDirsOnly
#         )
#
#         if not folder:
#             return
#
#         self.folder = folder
#         self.ui.folder_label.setText(folder)
#
#         items = self.detector.detect_items(folder)
#
#         self.ui.item_list.clear()
#
#         for item in items:
#             list_item = QListWidgetItem(item)
#
#             # ✅ 关键：加checkbox
#             list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
#             list_item.setCheckState(Qt.Unchecked)
#
#             self.ui.item_list.addItem(list_item)
#
#         # ✅ 监听变化（核心）
#         self.ui.item_list.itemChanged.connect(self.sync_selected_items)
#
#     def run(self):
#
#         items = [
#             self.ui.selected_list.item(i).text()
#             for i in range(self.ui.selected_list.count())
#         ]
#         self.ui.selected_list.itemDoubleClicked.connect(self.remove_selected)
#         if not items:
#             self.log("⚠️ 未选择Item")
#             return
#         print(items)
#         config = {
#             "items": items,
#             "minitab": {"output_dir": "./output/charts"}
#         }
#
#         builder = DataBuilder(config)
#         data = builder.build_from_folder(self.folder)
#         print(data)
#
#         runner = AnalysisRunner(config)
#
#         self.log("📊 执行Python分析...")
#         print(runner)
#         if self.ui.chk_cpk.isChecked():
#             results = runner.run_cpk(data)
#             print(results)
#         if self.ui.chk_grr.isChecked():
#             runner.run_grr(data)
#
#         report = ReportBuilder(
#             'C:\Production_Related\B15\src_sihuo\FA_CPK_System\output\\template\cpk_template.xlsx',
#             'C:\Production_Related\B15\src_sihuo\FA_CPK_System\output\cpk_report.xlsx'
#         )
#
#         report.insert_images(data, 'C:\Production_Related\B15\src_sihuo\FA_CPK_System\output\charts')
#
#         self.log("✅ 完成")
#
#     def sync_selected_items(self):
#
#         self.ui.selected_list.clear()
#
#         for i in range(self.ui.item_list.count()):
#             item = self.ui.item_list.item(i)
#
#             if item.checkState() == Qt.Checked:
#                 self.ui.selected_list.addItem(item.text())
#
#     def remove_selected(self, item):
#
#         text = item.text()
#
#         # 左侧取消勾选
#         for i in range(self.ui.item_list.count()):
#             it = self.ui.item_list.item(i)
#             if it.text() == text:
#                 it.setCheckState(Qt.Unchecked)
#                 break
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt

from core.item_detector import ItemDetector
from core.data_builder import DataBuilder
from core.analysis_runner_mtb import AnalysisRunnerMtb
from core.runner_worker import RunnerWorker
from PyQt5.QtWidgets import QListWidgetItem


class Controller:

    def __init__(self, ui):

        self.ui = ui
        self.folder = None

        self.detector = ItemDetector()

        self.ui.btn_select.clicked.connect(self.load_folder)
        self.ui.btn_run.clicked.connect(self.run)

        self.ui.item_list.itemChanged.connect(self.sync_selected)

    def log(self, txt):
        self.ui.log.append(txt)

    def load_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self.ui, "选择JSON目录"
        )

        if not folder:
            return

        self.folder = folder
        self.ui.folder_label.setText(folder)

        items = self.detector.detect_items(folder)

        self.ui.item_list.clear()

        for item in items:
            it = QListWidgetItem(item)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            self.ui.item_list.addItem(it)

        self.log(f"✅ 识别 {len(items)} 个Item")

    def sync_selected(self):

        self.ui.selected_list.clear()

        for i in range(self.ui.item_list.count()):
            it = self.ui.item_list.item(i)
            if it.checkState() == Qt.Checked:
                self.ui.selected_list.addItem(it.text())

    def run(self):

        items = [
            self.ui.selected_list.item(i).text()
            for i in range(self.ui.selected_list.count())
        ]

        if not items:
            self.log("⚠️ 未选择Item")
            return

        config = {
            "items": items,
            "minitab": {
                "exe_path": r"C:\Program Files\Minitab\Minitab 22\Mtb.exe",
                "output_dir": "C:\Production_Related\B15\src_sihuo\FA_CPK_System\output\charts"
            }
        }

        builder = DataBuilder(config)
        data = builder.build_from_folder(self.folder)

        runner = AnalysisRunnerMtb(config)

        self.worker = RunnerWorker(runner, data)

        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.ui.progress.setValue)
        self.worker.done_signal.connect(
            lambda: self.log("🎉 完成")
        )

        self.worker.start()
