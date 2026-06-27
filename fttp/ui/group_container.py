from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt


class GroupContainer(QWidget):
    def __init__(
        self,
        group_name,
        cell_indices,
        main_window,
        cell_widgets,
        cols=4,
        max_concurrent=2,
        cell_width=180,
        cell_height=160,
        cell_spacing=12,
        margin=20,
    ):
        super().__init__()
        self.group_name = group_name
        self.cell_indices = cell_indices
        self.main_window = main_window
        self.cell_widgets = [cell_widgets[i] for i in cell_indices]
        self.max_concurrent = max_concurrent

        layout = QVBoxLayout(self)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(f"<b>{group_name}</b>"))
        self.btn_start = QPushButton(f"Start {group_name}")
        self.btn_start.clicked.connect(self.on_group_start)
        hlayout.addWidget(self.btn_start)
        hlayout.addStretch()
        layout.addLayout(hlayout)

        grid = QGridLayout()
        grid.setSpacing(cell_spacing)
        grid.setContentsMargins(margin, 0, margin, 0)
        for idx, cell in enumerate(self.cell_widgets):
            r, c = divmod(idx, cols)
            cell.setFixedSize(cell_width, cell_height)
            grid.addWidget(cell, r, c)
        layout.addLayout(grid)

    def on_group_start(self):
        from concurrent.futures import ThreadPoolExecutor

        to_run = [i for i in self.cell_indices if not getattr(self.main_window.cell_widgets[i], "is_running", False)]

        def run_cell(idx):
            self.main_window.on_cell_start(idx)

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            for idx in to_run:
                executor.submit(run_cell, idx)
