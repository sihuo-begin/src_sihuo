#!/usr/bin/python3
# -*- coding:utf-8 -*-

import sys
import locale
import os

print("stdout encoding =", sys.stdout.encoding)
print("stderr encoding =", sys.stderr.encoding)
print("preferred encoding =", locale.getpreferredencoding(False))
print("PYTHONUTF8 =", os.environ.get("PYTHONUTF8"))

__marjor_version__ = "R1"

# from src.libs.version import *

import os
import yaml
import math
import sys
import time
import threading
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QTabWidget,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QToolButton,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QDialog,
    QInputDialog,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap, QIcon, QMovie
from PyQt5.QtCore import Qt, QSize, QTimer, QDateTime
from src.ui.cell_widget import CellWidget
from src.ui.detail_tab import DetailPanel
from src.ui.debug import DebugControlWidget
from src.libs.logger import setup_main_logger
from src.ui.group_container import GroupContainer
from src.libs import global_var as gl
from src.definition.product_mapping import stations_mapping
from src.libs.common import read_version


class MainWindow(QWidget):
    SIMPLE_CELL_THRESHOLD = 2

    def __init__(self, layout_config, operator="default"):
        super().__init__()
        self.setStyleSheet(
            """
            QWidget {
                background: #f5f7fa;
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', sans-serif;
                color: #212b36;
                font-size: 16px;
            }
            QTabWidget::pane {
                border-top: 2px solid #e0e3e7;
                background: #f5f7fa;
            }
            QTabBar::tab {
                background: #fff;
                border: 1px solid #e0e3e7;
                border-bottom: none;
                border-radius: 8px 8px 0 0;
                padding: 4px 20px;
                font-weight: 450;
            }
            QTabBar::tab:selected {
                background: #1976d2;
                color: #fff;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QInputDialog {
                background: #f5f7fa;
                border-radius: 12px;
            }
            QLineEdit {
                font-size: 16px;
            }
        """
        )
        self.total_test_qty = 0
        self.total_pass_qty = 0
        self.total_fail_qty = 0
        self.operator = operator
        self.setMinimumHeight(900)
        self.setMinimumWidth(1100)
        self.main_logger = setup_main_logger()
        self.base = os.path.dirname(__file__)
        if hasattr(sys, "_MEIPASS"):
            self.base_file_path = sys._MEIPASS
            self.base = os.path.join(self.base_file_path, "src", "ui")
            config_path = os.path.join(self.base, "config.yaml")
        else:
            self.base = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(self.base, "config.yaml")

        self.setWindowTitle("J-UTP")
        icon_path = os.path.join(self.base, "static", "utp_icon.ico")
        print(icon_path)
        self.setWindowIcon(QIcon(icon_path))

        self.all_steps = []
        self.current_step_index = None
        self.layout_config = layout_config
        self.cell_config = self.load_config(config_path)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        path = os.path.join(self.base, "static", "utp2.gif")
        self.banner = QLabel()
        self.banner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.banner.setFixedHeight(30)
        self.banner.setAlignment(Qt.AlignCenter)
        self.movie = QMovie(path)
        # 初始设定
        self.movie.setScaledSize(QSize(self.width(), 120))
        self.banner.setMovie(self.movie)
        self.movie.start()
        self.layout.addWidget(self.banner)
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(10, 5, 10, 5)

        self.topbar = QWidget()
        self.topbar.setStyleSheet(
            """
            background: #f0f5fb;
            border-bottom: 1.5px solid #e0e3e7;
            min-height: 60px;
        """
        )
        topbar_layout = QVBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(10, 4, 10, 4)
        topbar_layout.setSpacing(0)

        # 第一排：Online按钮、SW Version、Operator
        row1 = QHBoxLayout()
        row1.setSpacing(5)

        self.btn_mode = QToolButton()
        self.btn_mode.setText("Online")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setChecked(False)
        self.btn_mode.toggled.connect(self._on_mode_toggled)
        self.test_mode = self.btn_mode.text()
        self.btn_mode.setFixedSize(80, 80)
        self.btn_mode.setStyleSheet(
            """
            QToolButton {
                background-color: #1976d2;
                color: #fff;
                font-size: 18px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }
            QToolButton:checked {
                background-color: #ff1744;
                color: #fff;
            }
        """
        )
        version = read_version()
        build_time = version["build_time"]
        commit = version["commit"]
        row1.addWidget(self.btn_mode)
        product = self.layout_config.get("station").split("_")[0]
        self.software_main_version = stations_mapping.get(product, {}).get(self.layout_config.get("station"), None)
        pdims_rev = self.layout_config.get("pdims_rev", __marjor_version__)
        self.lbl_sw = QLabel(
            f"SW: {self.layout_config.get('station')}_{self.software_main_version}_{pdims_rev}\n\nSub: {build_time}_{commit}"
        )
        self.lbl_sw.setStyleSheet("font-size: 16px; color: #1976d2; font-weight: 600;")
        self.lbl_sw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_sw.setMinimumWidth(300)
        self.lbl_sw.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row1.addWidget(self.lbl_sw)
        # 头像
        self.lbl_operator_photo = QLabel()
        self.lbl_operator_photo.setFixedSize(90, 90)
        self.lbl_operator_photo.setStyleSheet("border-radius: 16px; background: #e0e3e7;")
        default_photo_path = os.path.join(self.base, "static", "default_user.png")
        if os.path.exists(default_photo_path):
            pix = QPixmap(default_photo_path)
            self.lbl_operator_photo.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            pass
        row1.addWidget(self.lbl_operator_photo, alignment=Qt.AlignRight)
        self.lbl_operator = QLabel(f"Operator: {self.operator}")
        self.lbl_operator.setStyleSheet("font-size: 16px; color: #ff9800; font-weight: 600; margin-left: 26px;")
        self.lbl_operator.setMinimumWidth(120)
        row1.addWidget(self.lbl_operator, alignment=Qt.AlignRight)

        self.lbl_engineer_photo = QLabel()
        self.lbl_engineer_photo.setFixedSize(90, 90)
        self.lbl_engineer_photo.setStyleSheet("border-radius: 16px; background: #e0e3e7;")
        default_photo_path = os.path.join(self.base, "static", "engineer.png")
        if os.path.exists(default_photo_path):
            pix = QPixmap(default_photo_path)
            self.lbl_engineer_photo.setPixmap(pix.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            pass

        row1.addWidget(self.lbl_engineer_photo, alignment=Qt.AlignRight)
        row1.setSpacing(50)
        self.btn_mode_switch = QPushButton("Product Mode")
        self.btn_mode_switch.setCheckable(True)
        self.btn_mode_switch.setChecked(False)
        self.is_engineer = self.btn_mode_switch.isChecked()
        self.btn_mode_switch.setMinimumHeight(38)
        self.btn_mode_switch.setFixedWidth(176)
        self.btn_mode_switch.setStyleSheet(self._get_mode_btn_style(False))
        self.btn_mode_switch.clicked.connect(self._toggle_mode)
        row1.addStretch(1)
        row1.addWidget(self.btn_mode_switch, alignment=Qt.AlignRight)
        topbar_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(50)

        self.lbl_station = QLabel(f"Station: {self.layout_config.get('station', '--')}")
        self.lbl_station.setStyleSheet("font-size: 16px; color: #1565c0; font-weight: bold; padding-right: 32px;")
        row2.addWidget(self.lbl_station)

        self.lbl_testqty = QLabel("TestQty: --")
        self.lbl_passqty = QLabel("PassQty: --")
        self.lbl_failqty = QLabel("FailQty: --")
        self.lbl_yield = QLabel("Yield: --")
        for lbl in (
            self.lbl_testqty,
            self.lbl_passqty,
            self.lbl_failqty,
            self.lbl_yield,
        ):
            lbl.setStyleSheet("font-size: 14px; color: #607d8b; font-weight: 500;")
            row2.addWidget(lbl)

        # spacer = QWidget()
        # spacer.setFixedWidth(60)  # 26为sw的margin-left
        # row2.addWidget(spacer)

        self.lbl_clock = QLabel()
        self.lbl_clock.setFixedSize(300, 25)
        self.lbl_clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_clock.setStyleSheet(
            """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #222c36, stop:1 #314158);
                color: #c6e2ff;
                border-radius: 14px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 16px;
                font-weight: 60;
                letter-spacing: 3px;
                padding: 2px 18px;
                border: 2px solid #1565c0;
            }
        """
        )
        self._start_clock_timer()
        row2.addStretch(1)
        row2.addWidget(self.lbl_clock)
        # spacer = QWidget()
        # spacer.setFixedWidth(80)
        # row2.addWidget(spacer)
        # row2.addStretch(1)
        topbar_layout.addLayout(row2)

        self.layout.addWidget(self.topbar)
        mode_layout.addStretch()
        self.layout.addLayout(mode_layout, stretch=0)
        self.cell_count = self.layout_config["layout"][0] * self.layout_config["layout"][1]
        self.sample_mode = self.cell_count > 2

        main_content = QWidget()
        if self.cell_count > 2:
            main_hbox = QVBoxLayout(main_content)  # 纵向布局
        else:
            main_hbox = QHBoxLayout(main_content)  # 横向布局
        # main_hbox = QHBoxLayout(main_content)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        self.main_tab = QWidget()
        # self.main_tab.setMinimumWidth(36)
        col_count = math.ceil(self.cell_count / 10)
        self.main_tab.setMinimumWidth(col_count * 320 + 40)
        self.detail_panel = DetailPanel()
        self.detail_panel.setMinimumWidth(450)

        main_hbox.addWidget(self.main_tab)
        main_hbox.addWidget(self.detail_panel, stretch=1)

        self.layout.addWidget(main_content, stretch=1)
        self.init_main_tab(self.layout_config)
        self._connect_cell_signals()
        self.apply_main_background(self.is_engineer)
        if not self.is_engineer:
            QTimer.singleShot(500, self.start_all_cells_auto)

    def _connect_cell_signals(self):
        from functools import partial

        for idx, cell in enumerate(getattr(self, "cell_widgets", [])):
            cell.counters_updated.connect(partial(self._on_counters_updated, idx))

    def _on_counters_updated(self, cell_index: int, tested: int, passed: int, failed: int):
        """
        slot 接受从 CellWidget 发来的增量（如果使用 partial，第一个参数是 cell_index）。
        把增量累加到 MainWindow 的全局总计，并更新 UI。
        """
        # 累加
        self.total_test_qty += tested
        self.total_pass_qty += passed
        self.total_fail_qty += failed

        # 更新 labels
        self.lbl_testqty.setText(f"TestQty: {self.total_test_qty}")
        self.lbl_passqty.setText(f"PassQty: {self.total_pass_qty}")
        self.lbl_failqty.setText(f"FailQty: {self.total_fail_qty}")

        # 计算 yield
        if self.total_test_qty > 0:
            yield_pct = (self.total_pass_qty / self.total_test_qty) * 100
            self.lbl_yield.setText(f"Yield: {yield_pct:.2f}%")
        else:
            self.lbl_yield.setText("Yield: --")

    def resizeEvent(self, event):
        new_size = QSize(self.width(), 120)
        self.movie.setScaledSize(new_size)
        self.banner.repaint()
        super().resizeEvent(event)

    def apply_main_background(self, is_engineer):
        if is_engineer:
            bg_color = "#fff3cd"
        else:
            bg_color = "#fff"
        self.topbar.setStyleSheet(
            f"""
                    background: {bg_color};
                    border-bottom: 1.5px solid #e0e3e7;
                    min-height: 60px;
                """
        )
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {bg_color};
                font-family: 'Segoe UI', 'Microsoft YaHei', 'Arial', sans-serif;
                color: #212b36;
                font-size: 16px;
            }}
        """
        )

    def _toggle_mode(self):
        self.is_engineer = self.btn_mode_switch.isChecked()
        if self.is_engineer:
            if not self.sample_mode:
                self.debug_control.set_buttons_enabled(True)
            password, ok = QInputDialog.getText(self, "Engineer Mode", "Enter passwrod：", echo=QLineEdit.Password)
            if ok:
                if password == "pmi_123":
                    self.is_engineer = True
                    self.btn_mode_switch.setText("Engineer Mode")
                else:
                    QMessageBox.warning(self, "wrong", "password is wrong")
                    self.btn_mode_switch.setChecked(False)
                    self.is_engineer = False
            else:
                self.btn_mode_switch.setChecked(False)
                self.is_engineer = False
        else:
            if not self.sample_mode:
                self.debug_control.set_buttons_enabled(False)
            self.btn_mode_switch.setText("Product Mode")
            self.start_all_cells_auto()
        self.btn_mode_switch.setStyleSheet(self._get_mode_btn_style(self.is_engineer))
        for cell in self.cell_widgets:
            cell.engineer_mode = self.is_engineer
            cell.set_simple_mode(self.sample_mode)
            cell.setMaximumWidth(320)
            cell.setMinimumWidth(180)
            cell.setMaximumHeight(320)
            cell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.apply_main_background(self.is_engineer)

    def _start_clock_timer(self):
        timer = QTimer(self)
        timer.timeout.connect(self._update_time)
        timer.start(1000)
        self._update_time()

    def _update_time(self):
        now = QDateTime.currentDateTime()
        self.lbl_clock.setText(now.toString("yyyy-MM-dd HH:mm:ss"))

    def _get_mode_btn_style(self, is_engineer):
        if is_engineer:
            # 蓝色高亮
            return """
            QPushButton {
                background-color: #1976d2;
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 16px;
                border: 2px solid #1976d2;
                padding: 6px 24px;
                box-shadow: 0 2px 8px #1976d222;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            """
        else:
            return """
            QPushButton {
                background-color: #ff9800;
                color: #fff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 16px;
                border: 2px solid #43a047;
                padding: 6px 24px;
                box-shadow: 0 2px 8px #43a04722;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            """

    def load_steps_from_yaml(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        steps = []
        for t in data.get("tests", []):
            steps.append(
                {
                    "name": t.get("test_name", ""),
                    "value": "",
                    "limit": t.get("limit", ""),
                    "status": "",
                    "runtime": "",
                }
            )
        return steps

    def load_config(self, path):
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        self.sequence_map = config.get("sequence_map", {})
        self.cell_configs = config.get("cells")
        self.limits = config.get("limits", {})
        self.pre_sequence_file = self.layout_config.get("pre_sequence")
        self.finalization_file = self.layout_config.get("finalize_sequence")
        self.max_concurrent = config.get("max_concurrent", 2)
        self.groups = self.layout_config.get("groups", None)
        self.auto_restart = True if int(config.get("auto_restart", 0)) == 1 else False
        print(f"auto_restart: {self.auto_restart}")
        return config

    def _on_mode_toggled(self, is_offline: bool):
        self._apply_mode_style()

    def _apply_mode_style(self):
        if self.btn_mode.isChecked():
            self.btn_mode.setText("Offline")
            self.btn_mode.setStyleSheet(
                """
                    QToolButton {
                        background-color: #ff1744;
                        color: #fff;
                        font-size: 18px;
                        font-weight: bold;
                        border-radius: 16px;
                        border: none;
                        box-shadow: 0 2px 8px #ff174422;
                    }
                """
            )
            self.test_mode = self.btn_mode.text()
        else:
            self.btn_mode.setText("Online")
            self.btn_mode.setStyleSheet(
                """
                    QToolButton {
                        background-color: #43a047;
                        color: #fff;
                        font-size: 18px;
                        font-weight: bold;
                        border-radius: 16px;
                        border: none;
                        box-shadow: 0 2px 8px #43a04722;
                    }
                """
            )
            self.test_mode = self.btn_mode.text()

    def init_main_tab(self, layout_config):
        cells = layout_config["cells"]
        laylout_list = layout_config["layout"]
        rows = laylout_list[0]
        cols = laylout_list[1]
        total_cell = rows * cols
        groups = layout_config.get("groups")
        self.cell_widgets = []

        container_widget = QWidget()
        if total_cell > 2:
            vbox = QHBoxLayout(container_widget)
        else:
            vbox = QVBoxLayout(container_widget)
        # vbox = QVBoxLayout(container_widget)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(8)

        max_rows = 3
        max_per_row = 8
        cell_w = 80
        margin = 20

        col_count = min(max_per_row, total_cell)
        row_count = (total_cell + max_per_row - 1) // max_per_row
        container_widget.setMinimumWidth(col_count * cell_w + margin)

        if groups:
            for idx in range(total_cell):
                cell_data = cells[idx]
                cell = CellWidget(
                    cell_data,
                    idx,
                    self.cell_config,
                    self.sequence_map,
                    layout_config,
                    self.limits,
                    self.pre_sequence_file,
                    self.finalization_file,
                    self.auto_restart,
                    self.is_engineer,
                    total_cell,
                )
                self.cell_widgets.append(cell)
            for group_name, indices in groups.items():
                group_box = GroupContainer(group_name, indices, self, self.cell_widgets)
                group_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
                group_grid = QGridLayout(group_box)
                group_grid.setContentsMargins(6, 6, 6, 6)
                group_grid.setSpacing(12)
                for n, idx in enumerate(indices):
                    if idx < total_cell:
                        cell_data = cells[idx]
                        cell = CellWidget(
                            cell_data,
                            idx,
                            self.cell_config,
                            self.sequence_map,
                            layout_config,
                            self.limits,
                            self.pre_sequence_file,
                            self.finalization_file,
                            self.auto_restart,
                            self.is_engineer,
                            total_cell,
                        )
                        if self.sample_mode:
                            cell.set_simple_mode(True)
                            cell.detail_requested.connect(self.show_detail_dialog)
                        else:
                            cell.set_simple_mode(False)
                            cell.detail_requested.connect(self.show_detail_dialog)
                        cell.setMaximumWidth(320)
                        cell.setMinimumWidth(100)
                        cell.setMaximumHeight(100)
                        cell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                        cell.start_clicked.connect(self.on_cell_start)
                        cell.stop_clicked.connect(self.on_cell_stop)
                        cell.view_clicked.connect(self.on_view_clicked)
                        cell.steps_updated.connect(lambda idx, step: self.detail_panel.update_step(idx, step))
                        cell.steps_updated_all.connect(
                            lambda idx, steps: self.detail_panel.update_content({"steps": steps})
                        )
                        self.cell_widgets.append(cell)
                        row = idx // max_per_row
                        col = idx % max_per_row
                        group_grid.addWidget(cell, row, col)
                vbox.addWidget(group_box)
        else:
            grid = QGridLayout()
            grid.setSpacing(12)
            for idx in range(total_cell):
                cell_data = cells[idx]
                cell = CellWidget(
                    cell_data,
                    idx,
                    self.cell_config,
                    self.sequence_map,
                    layout_config,
                    self.limits,
                    self.pre_sequence_file,
                    self.finalization_file,
                    self.auto_restart,
                )
                if self.sample_mode:
                    cell.set_simple_mode(True)
                    cell.detail_requested.connect(self.show_detail_dialog)
                else:
                    cell.set_simple_mode(False)
                    cell.detail_requested.connect(self.show_detail_dialog)
                cell.setMaximumWidth(320)
                cell.setMinimumWidth(100)
                cell.setMaximumHeight(320)
                cell.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                cell.start_clicked.connect(self.on_cell_start)
                cell.stop_clicked.connect(self.on_cell_stop)
                cell.view_clicked.connect(self.on_view_clicked)
                cell.steps_updated.connect(lambda idx, step: self.detail_panel.update_step(idx, step))
                cell.steps_updated_all.connect(lambda idx, steps: self.detail_panel.update_content({"steps": steps}))
                self.cell_widgets.append(cell)
                row = idx // max_per_row
                col = idx % max_per_row
                grid.addWidget(cell, row, col)
                # 单cell时加debug
            vbox.addLayout(grid)
            if total_cell == 1:
                # grid.addWidget(cell, 0, 0)
                vbox.addSpacing(16)
                self.debug_control = DebugControlWidget()
                self.debug_control.fixture_open.connect(self.on_fixture_open)
                self.debug_control.fixture_close.connect(self.on_fixture_close)
                self.debug_control.mode_setting.connect(self.on_mode_setting)
                self.debug_control.send_cmd.connect(self.on_send_cmd)
                if not self.is_engineer:
                    self.debug_control.set_buttons_enabled(False)
                vbox.addWidget(self.debug_control)
        vbox.addStretch(1)

        scroll = QScrollArea(self.main_tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(container_widget)
        main_tab_layout = QVBoxLayout(self.main_tab)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        main_tab_layout.setSpacing(0)
        main_tab_layout.addWidget(scroll)

    def on_cell_start(self, index):
        print("stdout encoding 中文 =", sys.stdout.encoding)
        print(f"▶ Start Cell {index + 1}")
        self.cell_widgets[index].set_status("running")
        cell = self.cell_widgets[index]
        if self.is_engineer:
            cell.btn_start.setEnabled(False)
        self.main_logger.debug("Threading..")
        threading.Thread(target=self._run_full_sequence, args=(cell,), daemon=True).start()

    def _run_full_sequence(self, cell):
        self.main_logger.debug(f"{cell.cell_id}: running!")
        cell.run_all_sequences()

    def start_all_cells_auto(self):
        for idx, cell in enumerate(self.cell_widgets):
            if self.is_engineer:
                if cell.btn_start.isEnabled():
                    self.on_cell_start(idx)
            self.on_cell_start(idx)

    def on_cell_stop(self, index):
        print(f"■ Stop Cell {index + 1}")
        self.cell_widgets[index].set_status("idle")
        cell = self.cell_widgets[index]
        cell.btn_start.setEnabled(True)
        if hasattr(cell, "_stop_event"):
            cell._stop_event.set()
        if hasattr(cell, "step_results"):
            print("clear")
            cell._stop_event.clear()

    def on_fixture_open(self):
        print("Debug: Fixture Open")

    def on_fixture_close(self):
        print("Debug: Fixture Close")

    def on_mode_setting(self):
        print("Debug: DUT Mode Setting")

    def on_send_cmd(self):
        print("Debug: DUT Send Cmd")

    def on_view_clicked(self):
        current_cell = self.sender()
        connection_names = list(current_cell.connections.keys())
        self.detail_panel.init_connections_tabs(connection_names)
        if isinstance(current_cell, CellWidget):
            log_content = current_cell._read_log()
            steps = getattr(current_cell, "all_step_results", [])
            output_logs = {}
            if hasattr(current_cell, "connections"):
                for conn_name, conn in current_cell.connections.items():
                    if hasattr(conn, "get_output_log"):
                        output_logs[conn_name] = conn.get_output_log()
            cell_name = getattr(current_cell, "cell_name", f"Cell {current_cell} Detail")
            self.detail_panel.set_title(f"{cell_name} Detail")
            self.detail_panel.update_content(
                {
                    "steps": steps,
                    "log": log_content,
                    "output_logs": output_logs,
                }
            )
        if hasattr(self, "detail_panel_timer") and self.detail_panel_timer is not None:
            self.detail_panel_timer.stop()
            self.detail_panel_timer.deleteLater()
            self.detail_panel_timer = None
        self.detail_panel_timer = QTimer(self)

        def refresh_detail_panel():
            log_content = current_cell._read_log()
            steps = getattr(current_cell, "all_step_results", [])
            output_logs = {}
            if hasattr(current_cell, "connections"):
                for conn_name, conn in current_cell.connections.items():
                    if hasattr(conn, "get_output_log"):
                        output_logs[conn_name] = conn.get_output_log()
            self.detail_panel.update_content(
                {
                    "steps": steps,
                    "log": log_content,
                    "output_logs": output_logs,
                }
            )

        self.detail_panel_timer.timeout.connect(refresh_detail_panel)
        self.detail_panel_timer.start(500)

    def show_detail_dialog(self, cell_index):
        current_cell = self.cell_widgets[cell_index]
        connection_names = list(current_cell.connections.keys())
        self.detail_panel.init_connections_tabs(connection_names)
        if isinstance(current_cell, CellWidget):
            log_content = current_cell._read_log()
            steps = getattr(current_cell, "all_step_results", [])
            output_logs = {}
            if hasattr(current_cell, "connections"):
                for conn_name, conn in current_cell.connections.items():
                    if hasattr(conn, "get_output_log"):
                        output_logs[conn_name] = conn.get_output_log()
            cell_name = getattr(current_cell, "cell_name", f"Cell {cell_index + 1} Detail")
            self.detail_panel.set_title(f"{cell_name} Detail")
            self.detail_panel.update_content(
                {
                    "steps": steps,
                    "log": log_content,
                    "output_logs": output_logs,  # {conn_name: log_str}
                }
            )
        if hasattr(self, "detail_panel_timer") and self.detail_panel_timer is not None:
            self.detail_panel_timer.stop()
            self.detail_panel_timer.deleteLater()
            self.detail_panel_timer = None
        self.detail_panel_timer = QTimer(self)

        def refresh_detail_panel():
            log_content = current_cell._read_log()
            steps = getattr(current_cell, "all_step_results", [])
            output_logs = {}
            if hasattr(current_cell, "connections"):
                for conn_name, conn in current_cell.connections.items():
                    if hasattr(conn, "get_output_log"):
                        output_logs[conn_name] = conn.get_output_log()
            self.detail_panel.update_content(
                {
                    "steps": steps,
                    "log": log_content,
                    "output_logs": output_logs,
                }
            )

        self.detail_panel_timer.timeout.connect(refresh_detail_panel)
        self.detail_panel_timer.start(500)
