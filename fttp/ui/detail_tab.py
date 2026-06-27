import re
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QHeaderView,
    QLabel,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class DetailPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.title_label = QLabel("Cell Detail", self)
        self.title_label.setStyleSheet("font-size:18px;font-weight:bold;margin-bottom:8px;")
        self.layout.addWidget(self.title_label)
        self.tabs = QTabWidget()

        self.info_tab = QTableWidget()
        self.info_tab.setColumnCount(10)
        self.info_tab.setHorizontalHeaderLabels(
            [
                "pnum",
                "reference",
                "actual",
                "unit",
                "min",
                "max",
                "equal",
                "status",
                "runtime",
                "starttime",
            ]
        )
        header = self.info_tab.horizontalHeader()
        for col in range(10):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.info_tab.setColumnWidth(0, 80)
        self.info_tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.info_tab.horizontalHeader().resizeSection(1, 110)
        self.info_tab.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.info_tab.horizontalHeader().resizeSection(2, 100)
        self.info_tab.setColumnWidth(3, 60)
        self.info_tab.setColumnWidth(4, 60)
        self.info_tab.setColumnWidth(5, 60)
        self.info_tab.horizontalHeader().setSectionResizeMode(6, QHeaderView.Interactive)
        self.info_tab.horizontalHeader().resizeSection(6, 60)
        # self.info_tab.setColumnWidth(6, 120)
        self.info_tab.horizontalHeader().setMinimumSectionSize(60)
        self.info_tab.setEditTriggers(QTableWidget.NoEditTriggers)
        self.info_tab.setStyleSheet("QTableWidget { font-size:12px; }")

        self.log_tab = QTextEdit()
        self.log_tab.setReadOnly(True)
        self.log_tab.setStyleSheet("QTextEdit { font-size:14px; }")
        # self.control_tab = QTextEdit()
        # self.control_tab.setReadOnly(True)
        # self.control_tab.setStyleSheet("QTextEdit { font-size:12px; }")

        self.tabs.addTab(self.info_tab, "TestSequence")
        self.tabs.addTab(self.log_tab, "RunningLog")
        # self.tabs.addTab(self.control_tab, "Connection")

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.connection_tabs = {}

        self._log_lines = []
        self._output_lines = []

    def _get_val(self, step, key):
        val = step.get(key, None)
        if val is not None:
            return str(val)
        limit = step.get("limit", None)
        if isinstance(limit, dict):
            v = limit.get(key, None)
            if v is not None:
                return str(v)
        return ""

    def set_title(self, cell_name):
        self.title_label.setText(cell_name)

    def init_connections_tabs(self, connection_names):
        while self.tabs.count() > 2:
            self.tabs.removeTab(2)
        for conn_name in connection_names:
            conn_widget = QTextEdit()
            conn_widget.setReadOnly(True)
            tab_title = f"Conn: {conn_name}"
            self.tabs.addTab(conn_widget, tab_title)
            self.connection_tabs[conn_name] = conn_widget

    def update_step(self, row, step):
        if self.info_tab.rowCount() <= row:
            self.info_tab.setRowCount(row + 1)
        self._set_cell(self.info_tab, row, 0, str(step.get("pnum", "")))
        self._set_cell(
            self.info_tab,
            row,
            1,
            step.get("reference", "").upper() or step.get("name", "").upper(),
        )
        self._set_cell(self.info_tab, row, 2, str(step.get("actual", "") or step.get("value", "")))
        self._set_cell(self.info_tab, row, 3, str(step.get("unit", "")))
        self._set_cell(self.info_tab, row, 4, self._get_val(step, "min"))
        self._set_cell(self.info_tab, row, 5, self._get_val(step, "max"))
        self._set_cell(self.info_tab, row, 6, self._get_val(step, "equal"))
        status_text = step.get("status", "").upper()
        self._set_cell(self.info_tab, row, 7, status_text)
        self._set_cell(self.info_tab, row, 8, str(step.get("runtime", "")))
        self._set_cell(self.info_tab, row, 9, str(step.get("starttime", "")))
        color = QColor(249, 249, 249)
        if status_text == "PASS":
            color = QColor(249, 249, 249)
        elif status_text == "FAIL":
            color = QColor(255, 200, 200)
        elif status_text == "RUNNING":
            color = QColor(255, 255, 150)
            self.info_tab.setCurrentCell(row, 0)
            self.info_tab.scrollToItem(self.info_tab.item(row, 0))
        elif status_text == "JUMPED":
            color = QColor(230, 230, 230)
        elif re.findall(r"(STOPPED|ERROR|NOTFOUND).*", status_text):
            color = QColor(255, 180, 160)
        for col in range(self.info_tab.columnCount()):
            item = self.info_tab.item(row, col)
            if item:
                item.setBackground(color)
            self.info_tab.scrollToBottom()

    def update_content(self, data):
        steps = data.get("steps", None) if isinstance(data, dict) else None
        log = data.get("log", None)
        output_logs = data.get("output_logs", None)

        if steps is not None:
            self.info_tab.setRowCount(len(steps))
            for row, step in enumerate(steps):
                self._set_cell(self.info_tab, row, 0, str(step.get("pnum", "")))
                self._set_cell(
                    self.info_tab,
                    row,
                    1,
                    step.get("reference", "").upper() or step.get("name", "").upper(),
                )
                self._set_cell(
                    self.info_tab,
                    row,
                    2,
                    str(step.get("actual", "") or step.get("value", "")),
                )
                self._set_cell(self.info_tab, row, 3, str(step.get("unit", "")))
                self._set_cell(self.info_tab, row, 4, self._get_val(step, "min"))
                self._set_cell(self.info_tab, row, 5, self._get_val(step, "max"))
                self._set_cell(self.info_tab, row, 6, self._get_val(step, "equal"))
                status_text = step.get("status", "").upper()
                self._set_cell(self.info_tab, row, 7, status_text)
                self._set_cell(self.info_tab, row, 8, str(step.get("runtime", "")))
                self._set_cell(self.info_tab, row, 9, str(step.get("starttime", "")))
                color = QColor(249, 249, 249)
                if status_text == "PASS":
                    color = QColor(249, 249, 249)
                elif status_text == "FAIL":
                    color = QColor(255, 200, 200)
                elif status_text == "RUNNING":
                    color = QColor(255, 255, 150)
                    self.info_tab.setCurrentCell(row, 0)
                    self.info_tab.scrollToItem(self.info_tab.item(row, 0))
                elif status_text == "JUMPED":
                    color = QColor(230, 230, 230)
                elif re.findall(r"(STOPPED|ERROR|NOTFOUND).*", status_text):
                    color = QColor(255, 180, 160)
                for col in range(self.info_tab.columnCount()):
                    item = self.info_tab.item(row, col)
                    if item:
                        item.setBackground(color)
            # self.info_tab.resizeColumnsToContents()
        elif self.info_tab.rowCount() > 0:
            self.info_tab.setRowCount(0)
        if log is not None:
            self.set_log(str(log))
        if output_logs and isinstance(output_logs, dict):
            for conn_name, log_text in output_logs.items():
                if hasattr(self, "connection_tabs") and conn_name in self.connection_tabs:
                    self.connection_tabs[conn_name].setPlainText(log_text)
                    self.connection_tabs[conn_name].verticalScrollBar().setValue(
                        self.connection_tabs[conn_name].verticalScrollBar().maximum()
                    )
        self.info_tab.scrollToBottom()

    def _set_cell(self, table: QTableWidget, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.setItem(row, col, item)

    def set_log(self, msg: str):
        self._log_lines = [msg]
        self.log_tab.setPlainText(msg)
        self.log_tab.verticalScrollBar().setValue(self.log_tab.verticalScrollBar().maximum())

    def set_output_log(self, msg: str):
        self._output_lines = [msg]
        self.control_tab.setPlainText(msg)
        self.control_tab.verticalScrollBar().setValue(self.control_tab.verticalScrollBar().maximum())

    def append_log(self, msg: str):
        self._log_lines.append(msg)
        self.log_tab.setPlainText("\n".join(self._log_lines))
        self.log_tab.verticalScrollBar().setValue(self.log_tab.verticalScrollBar().maximum())

    # def append_output_log(self, msg: str):
    #     self._output_lines.append(msg)
    #     self.control_tab.setPlainText('\n'.join(self._output_lines))
    #     self.control_tab.verticalScrollBar().setValue(self.control_tab.verticalScrollBar().maximum())

    def clear_logs(self):
        self._log_lines = []
        self.log_tab.clear()

    def clear_output_logs(self):
        self._output_lines = []
        self.control_tab.clear()
