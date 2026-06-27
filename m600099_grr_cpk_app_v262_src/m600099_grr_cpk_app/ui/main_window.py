# ──────────────────────────────────────────────
#  Main Window
# ──────────────────────────────────────────────
import logging
import os
import traceback
from pathlib import Path
import pandas as pd
from datetime import datetime
import time as _time
import json

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QProgressBar, QTextEdit, QFileDialog, QMessageBox,
    QSpacerItem, QSizePolicy, QTreeWidget, QTreeWidgetItem, QSplitter,
    QFrame, QStatusBar, QProgressDialog, QComboBox, QLineEdit, QSpinBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

from ui.styles import MAIN_STYLE
from core.data_loader import DataLoader
from core.grr_analyzer import GRRAnalyzer
from core.cpk_analyzer import CPKAnalyzer
from core.json_parser  import JsonParser
from core.arr_parser import parse_json_folder as arr_parse_json_folder
from report.arr_excel_report_generator import ARRReportGenerator
from report.excel_report_generator    import ExcelReportGenerator
from report.cpk_excel_report_generator import CPKExcelReportGenerator
from utils.config import APP_NAME, APP_VERSION, AUTHOR, LED_INTENSITY_COLS, OUTPUT_DIR, _norm_led


logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  Worker Thread – runs analysis without freezing UI
# ══════════════════════════════════════════════
class AnalysisWorker(QThread):
    """Runs GRR/CPK analysis in a background thread."""
    progress = pyqtSignal(str, int)   # message, percentage
    finished = pyqtSignal(dict)       # results dict
    error    = pyqtSignal(str)

    def __init__(self, df, selected_items, run_grr, run_cpk, minitab_path, file_path=None, parent=None):
        super().__init__(parent)
        self.df            = df
        self.selected_items = selected_items
        self.run_grr       = run_grr
        self.run_cpk       = run_cpk
        self.minitab_path  = minitab_path
        self._file_path    = file_path
        self._results      = {}
        self.minitab_path_set = False

    def run(self):
        if self.run_grr:
            pnum_item_map = {}
            LED_SPECS = {}
            with open(r"{}\\test_data.json".format(OUTPUT_DIR), "r", encoding="utf-8") as f:
                test_data = json.load(f)
            for item in self.selected_items:
                for data in test_data:
                    if item.lower() == data["reference"].lower():
                        pnum = data["pnum"]
                        pnum_item_map.update({pnum: item})
                        LED_SPECS.update(
                            {
                                item: {
                                    "lsl": data["min"],
                                    "usl": data["max"],
                                    "pnum": pnum,
                                    "unit": data["unit"],
                                    "nominal": (float(data["min"]) + float(data["max"])) / 2,
                                    "tol": round((float(data["max"]) - float(data["min"])), 3),
                                }
                            }
                        )

            pnum_list = sorted(pnum_item_map)
            for pnum in pnum_list:
                for data in test_data:
                    if pnum == data["pnum"]:
                        item = data["reference"]
                        LED_SPECS.update(
                            {
                                item: {
                                    "lsl": data["min"],
                                    "usl": data["max"],
                                    "pnum": pnum,
                                    "unit": data["unit"],
                                    "nominal": (float(data["min"]) + float(data["max"])) / 2,
                                    "tol": round((float(data["max"]) - float(data["min"])), 3),
                                }
                            }
                        )
            logger.info("simon select pnum_item_map \n {}".format(pnum_item_map))
            logger.info("simon select pnum_list \n {}".format(pnum_list))
            logger.info("simon select self LED_SPECS \n {}".format(LED_SPECS))
        try:
            P = self.progress.emit
            total = len(self.selected_items)
            # Load LSL/USL specs from .specs.json sidecar before CPK computation
            if self._file_path:
                sidecar = Path(self._file_path).parent / (Path(self._file_path).name + ".specs.json")
                if sidecar.exists():
                    try:
                        import json as _json
                        specs_map = _json.load(open(sidecar))
                        for col, val in specs_map.items():
                            if col not in self.df.columns:
                                self.df[col] = val
                        logger.info(f"Loaded {len(specs_map)} specs from sidecar")
                    except Exception as ex:
                        logger.warning(f"Could not load specs sidecar: {ex}")

            # ── V256: pre-warm easyocr.Reader() so the user sees a
            # progress message during the 5–10s model load instead
            # of a silent wait when the first chart is OCR'd. The
            # reader is cached on the function as
            # `_ocr_extract_grr_metrics._easyocr_reader` so all
            # subsequent OCR calls reuse it without re-loading.
            if self.run_grr:
                try:
                    P("Pre-loading easyocr model (one-time, 5–10s)…", 3)
                    logger.info("V256: pre-loading easyocr.Reader() …")
                    from core.grr_analyzer import (
                        _ocr_extract_grr_metrics as _prewarm_ocr)
                    if not hasattr(_prewarm_ocr, "_easyocr_reader"):
                        import easyocr as _eo
                        _prewarm_ocr._easyocr_reader = _eo.Reader(
                            ["en"], gpu=False, verbose=False)
                    logger.info("V256: easyocr.Reader() pre-warmed")
                except Exception as pre:
                    logger.warning("V256: easyocr pre-warm failed: %s", pre)

            # ── Batch CPK: all items in ONE Minitab session ──
            import time as _t0
            t0 = _t0.time()
            logger.info(f"[Step 3/3] Starting CPK batch ({len(self.selected_items)} items)…")
            if self.run_cpk and self.minitab_path and os.path.isfile(self.minitab_path):
                P("Running CPK (batch mode)…", 10)
                self.minitab_path_set=True
                cpk_chart_paths = CPKAnalyzer.run_all_minitab(
                    self.df, self.selected_items, self.minitab_path
                )
                logger.info(f"  CPK batch done in {_t0.time()-t0:.1f}s")
                P("CPK batch done.", 40)
            else:
                cpk_chart_paths = {}
                logger.info(f"  CPK batch skipped (no minitab path)")

            # ── Batch GRR: all items in ONE Minitab session ──
            t1 = _t0.time()
            grr_chart_paths = {}
            if self.run_grr and self.minitab_path and os.path.isfile(self.minitab_path):
                logger.info(f"Starting GRR batch ({len(self.selected_items)} items)…")
                P("Running GRR (batch mode)…", 5)
                grr_chart_paths = GRRAnalyzer.run_all_minitab(
                    self.df, self.selected_items, self.minitab_path, LED_SPECS = LED_SPECS
                )
                logger.info(f"  GRR batch done in {_t0.time()-t1:.1f}s ({_t0.time()-t0:.1f}s total)")
                P("GRR batch done.", 20)
            else:
                logger.info(f"  GRR batch skipped (no minitab path)")

            # ── Per-item: CPK metrics + GRR ──
            for i, item in enumerate(self.selected_items):
                pct = int((i / total) * 100)
                result = {}

                if self.run_cpk:
                    # CPK metrics (Minitab already opened in batch above)
                    P(f"  CPK: {item}", pct)
                    cpk_analyzer = CPKAnalyzer(self.df, item)
                    minitab_chart_path ={'capability': cpk_chart_paths[item]} if item in cpk_chart_paths else {}
                    cpk_result = cpk_analyzer.compute(minitab_path=None, minitab_path_set=self.minitab_path_set, chart_path = minitab_chart_path)
                    cpk_result.chart_paths = minitab_chart_path
                    result['cpk'] = cpk_result

                if self.run_grr:
                    P(f"  GRR: {item}", pct)
                    grr_analyzer = GRRAnalyzer(self.df, item, LED_SPECS = LED_SPECS)
                    grr_result = grr_analyzer.compute(minitab_path=None)
                    safe = item.replace("/", "_")
                    # Filter only this item's charts from the batch result.
                    # run_all_minitab prefixes every chart key with
                    # "<safe>__<slide>_<shape>" so we strip that prefix
                    # and pass a stem-only dict (plus _img_dir) to the
                    # Excel generator.
                    prefix = f"{safe}__"
                    item_paths = {
                        k[len(prefix):]: v
                        for k, v in grr_chart_paths.items()
                        if k.startswith(prefix)
                    }
                    if grr_chart_paths.get("_img_dir"):
                        item_paths["_img_dir"] = grr_chart_paths["_img_dir"]
                    worksheet_key = "{}__grr_worksheet".format(safe)
                    if worksheet_key in grr_chart_paths:
                        item_paths["_grr_worksheet"] = grr_chart_paths[worksheet_key]
                    grr_result.chart_paths = item_paths
                    # Now that in-memory chart paths are available
                    # (compute() skipped the JOURNAL read in batch
                    # mode), parse the JOURNAL session text to
                    # overwrite %GR&R / %P/T / NDC with Minitab's
                    # official values.
                    try:
                        from core.grr_analyzer import (
                            _parse_minitab_session_for_grr_str,
                            augment_grr_with_ocr)
                        metrics = _parse_minitab_session_for_grr_str(
                            item_paths.get("_grr_worksheet"))
                        if metrics is not None and (metrics[0] is not None
                                                    or metrics[1] is not None
                                                    or metrics[2] is not None):
                            pct_m, pt_m, ndc_m = metrics
                            if pct_m is not None:
                                grr_result.grr_pct = float(pct_m)
                            if pt_m is not None:
                                grr_result.pt_ratio = float(pt_m)
                            if ndc_m is not None:
                                grr_result.ndc = float(ndc_m)
                        else:
                            # JOURNAL text not parseable — fall
                            # back to OCR.
                            augment_grr_with_ocr(grr_result, item_paths)
                    except Exception as ce:
                        logger.warning(
                            "main_window JOURNAL/OCR augment failed: "
                            "%s; keeping Python fallback", ce)
                    result['grr'] = grr_result

                norm = _norm_led(item)
                self._results[norm] = result
                P(f"Done: {item}", int(((i + 1) / total) * 100))

            self.finished.emit(self._results)

        except Exception as e:
            logger.exception("AnalysisWorker error")
            self.error.emit(traceback.format_exc())




# ══════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.df             = None
        self.df_raw         = None          # raw GRR sheet data
        self.cpk_df         = None           # raw CPK sheet data
        self.analysis_worker = None
        self._intermediate_excel = None
        self._mode              = "excel"
        self._arr_folder = None
        self._arr_config = None
        self.chk_arr          = None   # initialized in _build_left_panel
        self._build_ui()
        self.setStyleSheet(MAIN_STYLE)
        self._log("Select a data source and click Run Analysis.")

    # ── UI construction ────────────────────────

    def _build_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(12, 10, 12, 8)
        lay.setSpacing(8)

        # ── Header (fixed height so it never grows) ──
        header = self._build_header()
        header.setFixedHeight(28)
        lay.addWidget(header)

        # ── Three-panel layout (fills all remaining vertical space) ──
        #  [Left]    Data source + GRR structure + sheet selector
        #  [Middle]  Available items (checkbox list)
        #  [Right]   Selected items confirm + analysis options + log
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())     # data source + structure + sheet
        splitter.addWidget(self._build_middle_panel())   # available items
        splitter.addWidget(self._build_right_panel())    # selected confirm + options + log
        splitter.setStretchFactor(0, 1)   # left: data source - can stretch
        splitter.setStretchFactor(1, 1)   # middle: available items - can stretch
        splitter.setStretchFactor(2, 2)   # right: options + log - stretches more
        splitter.setSizes([280, 340, 480])
        lay.addWidget(splitter, stretch=1)   # stretch vertically to fill window

        # ── Status bar ──
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("header-widget")
        lo = QHBoxLayout(frame)
        lo.setContentsMargins(14, 4, 14, 4)
        lo.setSpacing(10)
        title = QLabel(f"🦞 {APP_NAME}  ·  GRR & CPK Analysis Tool")
        title.setObjectName("header-title")
        sub   = QLabel(f"version {APP_VERSION}  ·  {AUTHOR}")
        sub.setObjectName("header-sub")
        lo.addWidget(title)
        lo.addStretch()
        lo.addWidget(sub)
        return frame

    # ── Unified left panel ────────────────────────

    def _build_left_panel(self):
        widget = QWidget()
        lo = QVBoxLayout(widget)
        lo.setContentsMargins(4, 4, 8, 4)
        lo.setSpacing(8)

        # ── 1. Data source selector ──
        gb_src = QGroupBox("📂 Data Source")
        gl = QGridLayout(gb_src)

        self._cmb_source = QComboBox()
        self._cmb_source.addItems([
            "📁 Jason Logs Folder  (解析→分析→报告)",
            "📄 Intermediate Excel  (已有数据，直接分析)",
        ])
        self._cmb_source.setFixedHeight(28)
        self._cmb_source.currentIndexChanged.connect(self._on_source_changed)
        gl.addWidget(self._cmb_source, 0, 0, 1, 2)

        self._lbl_mode = QLabel("")
        self._lbl_mode.setStyleSheet("font-size:8pt;")
        gl.addWidget(self._lbl_mode, 1, 0, 1, 2)

        # Folder path row (JSON mode)
        self._edt_folder = QLineEdit()
        self._edt_folder.setPlaceholderText("Select Jason logs folder…")
        self._edt_folder.setReadOnly(True)
        self._btn_folder = QPushButton("Browse…")
        self._btn_folder.setFixedWidth(80)
        self._btn_folder.clicked.connect(self._on_browse_folder)
        gl.addWidget(self._edt_folder, 2, 0)
        gl.addWidget(self._btn_folder, 2, 1)

        # File path row (Excel mode)
        self._edt_file = QLineEdit()
        self._edt_file.setPlaceholderText("Load intermediate Excel…")
        self._edt_file.setReadOnly(True)
        self._btn_file = QPushButton("Load…")
        self._btn_file.setFixedWidth(80)
        self._btn_file.clicked.connect(self._on_load_file)
        gl.addWidget(self._edt_file, 3, 0)
        gl.addWidget(self._btn_file, 3, 1)

        # AR&R folder row (AR&R mode only)
        self._edt_arr_folder = QLineEdit()
        self._edt_arr_folder.setPlaceholderText("Select AR&R Jason logs folder…")
        self._edt_arr_folder.setReadOnly(True)
        self._btn_arr_folder = QPushButton("Browse…")
        self._btn_arr_folder.setFixedWidth(80)
        self._btn_arr_folder.clicked.connect(self._on_browse_arr_folder)
        gl.addWidget(self._edt_arr_folder, 4, 0)
        gl.addWidget(self._btn_arr_folder, 4, 1)
        self._edt_arr_folder.setVisible(False)
        self._btn_arr_folder.setVisible(False)

        lo.addWidget(gb_src)

        # ── 2. GRR structure (JSON mode only) ──
        self._gb_struct = QGroupBox("📐 GRR Structure  (仅 Jason Logs 模式)")
        gl2 = QGridLayout(self._gb_struct)
        gl2.addWidget(QLabel("Parts (DUTs):"), 0, 0)
        self._spn_parts  = QSpinBox(); self._spn_parts.setRange(2, 50)
        self._spn_parts.setValue(10); self._spn_parts.setFixedWidth(70)
        gl2.addWidget(self._spn_parts, 0, 1)
        gl2.addWidget(QLabel("Operators:"), 0, 2)
        self._spn_ops = QSpinBox(); self._spn_ops.setRange(2, 10)
        self._spn_ops.setValue(3); self._spn_ops.setFixedWidth(70)
        gl2.addWidget(self._spn_ops, 0, 3)
        gl2.addWidget(QLabel("Trials:"), 1, 0)
        self._spn_trials = QSpinBox(); self._spn_trials.setRange(2, 10)
        self._spn_trials.setValue(3); self._spn_trials.setFixedWidth(70)
        gl2.addWidget(self._spn_trials, 1, 1)
        lo.addWidget(self._gb_struct)

        # ── 3. Sheet selector ──
        gb_sheet = QGroupBox("📋 Select Sheet")
        gl3 = QGridLayout(gb_sheet)
        self.sheet_list = QListWidget()
        self.sheet_list.setMaximumHeight(80)
        self.sheet_list.itemClicked.connect(self._on_sheet_selected)
        gl3.addWidget(self.sheet_list)
        lo.addWidget(gb_sheet)

        # Init source visibility
        self._on_source_changed(0)
        lo.addStretch()
        return widget

    def _build_middle_panel(self):
        widget = QWidget()
        lo = QVBoxLayout(widget)
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(6)

        # Available items
        gb_avail = QGroupBox("OK Available Test Items")
        gl = QVBoxLayout(gb_avail)
        tb = QHBoxLayout()
        self.btn_sel_all = QPushButton("Select All")
        self.btn_sel_none = QPushButton("Select None")
        self.btn_sel_all.clicked.connect(self._select_all)
        self.btn_sel_none.clicked.connect(self._select_none)
        self.btn_sel_all.setFixedHeight(24)
        self.btn_sel_none.setFixedHeight(24)
        self.btn_sel_all.setStyleSheet("min-width:80px; padding:2px 8px;")
        self.btn_sel_none.setStyleSheet("min-width:80px; padding:2px 8px;")
        tb.addWidget(self.btn_sel_all)
        tb.addWidget(self.btn_sel_none)
        tb.addStretch()
        gl.addLayout(tb)
        self.item_list = QListWidget()
        self.item_list.setSelectionMode(QListWidget.MultiSelection)
        self.item_list.itemChanged.connect(self._on_item_checked)
        self.item_list.itemChanged.connect(self._refresh_selected_panel)
        gl.addWidget(self.item_list)
        lo.addWidget(gb_avail)

        # Selected items confirmation panel
        gb_sel = QGroupBox("Checked Selected Items (Confirm)")
        gl_sel = QVBoxLayout(gb_sel)
        self._sel_list = QListWidget()
        self._sel_list.setStyleSheet("background:#1a2e1a; color:#aaffaa; font-size:9pt;")
        gl_sel.addWidget(self._sel_list)
        lo.addWidget(gb_sel)

        return widget

    def _refresh_selected_panel(self):
        self._sel_list.clear()
        for i in range(self.item_list.count()):
            item = self.item_list.item(i)
            if item.checkState() == Qt.Checked:
                self._sel_list.addItem(item.text())

    def _on_source_changed(self, idx: int):
        """Toggle visibility between JSON folder and Excel file controls."""
        is_json = (idx == 0)
        self._edt_folder.setVisible(is_json)
        self._btn_folder.setVisible(is_json)
        self._edt_file.setVisible(not is_json)
        self._btn_file.setVisible(not is_json)
        self._gb_struct.setVisible(is_json)
        # Show AR&R Browse button only in JSON source mode
        if hasattr(self, "_edt_arr_folder"): self._edt_arr_folder.setVisible(is_json)
        if hasattr(self, "_btn_arr_folder"): self._btn_arr_folder.setVisible(is_json)
        if is_json:
            self._lbl_mode.setText("流程: Jason Logs → 解析 → GRR/CPK / AR&R 报告")
        else:
            self._lbl_mode.setText("流程: Intermediate Excel → GRR/CPK / AR&R 报告")
        self._lbl_mode.setStyleSheet("color:#66bb6a; font-weight:bold; font-size:8pt;")
        # In Excel mode: if AR&R already checked, open config dialog
        if not is_json:
            if self.chk_arr is not None and self.chk_arr.isChecked():
                self._log("Source switched to Excel — opening Sample Mapping Configuration…")
                self._on_browse_arr_folder()

    def _on_browse_arr_folder(self):
        # JSON source mode: Browse button selects Jason folder AND shows Sample Mapping config
        # Excel source mode: Browse button shows Sample Mapping config directly
        is_json = (self._cmb_source.currentIndex() == 0) if hasattr(self, "_cmb_source") else False
        folder = None

        if is_json:
            folder = QFileDialog.getExistingDirectory(
                self, "Select AR&R Jason Logs Folder", "C:/output"
            )
            if not folder:
                return
            self._edt_arr_folder.setText(folder)
            self._arr_folder = folder
            self._log(f"AR&R folder set: {folder}")

        from ui.arr_config_dialog import show_arr_config_dialog
        try:
            ok, config = show_arr_config_dialog(self, folder)
        except Exception as e:
            err_msg = "Failed to open Sample Mapping Configuration dialog:\n" + str(e)
            QMessageBox.critical(self, "Config Dialog Error", err_msg)
            return
        if not ok:
            self._log("AR&R sample mapping cancelled.", "ERROR")
            return
        self._arr_config = config
        self._log("AR&R config ready — click Run when ready.", "OK")

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select GRR Jason Logs Folder", "C:/output"
        )
        if not folder:
            return

        self._edt_folder.setText(folder)
        self._json_folder = folder
        self._log(f"Folder set: {folder}")

        # ── Immediately parse JSON and populate item list ──
        parts     = self._spn_parts.value()
        operators = self._spn_ops.value()
        trials    = self._spn_trials.value()
        os.makedirs("C:/output", exist_ok=True)
        excel_path = str(Path("C:/output") / (
            f"raw_data---{datetime.now():%Y%m%d%H%M%S}.xlsx"
        ))

        self.btn_run.setEnabled(False)
        self._log("=" * 50)
        self._log(f"[Step 1/2] Parsing Jason logs: {folder}")
        self._log(f"  Structure: {parts} parts x {operators} ops x {trials} trials")
        self.progress_bar.setValue(10)

        try:
            import traceback as _tb
            parser = JsonParser(folder)
            parser.parse()
            parser.assign_trials(parts=parts, operators=operators, trials=trials)
            excel_path = parser.export(excel_path)
            self._log(f"[Step 1/2] Intermediate Excel: {excel_path}", "OK")
            self._log("[Step 2/2] Loading parsed Excel to detect items...")
            self.progress_bar.setValue(50)

            # Load the parsed Excel and populate item list
            self._path = excel_path
            loader = DataLoader(excel_path)
            self._loader = loader
            self.df_raw    = loader.df_raw
            # Normalize: to_grr_format() converts PNUM cols -> LED_INTENSITY names
            self.df        = loader.to_grr_format()
            self.df_sheets = loader.sheet_names
            self._edt_file.setText(os.path.basename(excel_path))

            # Populate sheet list
            self.sheet_list.clear()
            for name in self.df_sheets:
                self.sheet_list.addItem(name)
            self.sheet_list.setCurrentRow(0)
            self._on_sheet_selected(self.sheet_list.item(0))

            self.progress_bar.setValue(80)
            self._log(f"[Step 2/2] Done. Found {self.item_list.count()} items.", "OK")
            self.btn_run.setEnabled(True)
            self.progress_bar.setValue(100)

        except Exception as e:
            self.btn_run.setEnabled(True)
            self.progress_bar.setValue(0)
            self._log(f"Browse/parse error: {e}", "ERROR")
            QMessageBox.critical(self, "Parse Error",
                f"Failed to parse Jason logs:\n{e}")

    def _build_right_panel(self):
        widget = QWidget()
        lo = QVBoxLayout(widget)
        lo.setContentsMargins(8, 4, 4, 4)
        lo.setSpacing(8)

        # ── Analysis options ──
        gb_opt = QGroupBox("⚙ Analysis Options")
        gl = QGridLayout(gb_opt)

        gl.addWidget(QLabel("Analysis Type:"), 0, 0, 1, 2)

        self.chk_grr = QCheckBox("GRR Analysis")
        self.chk_cpk = QCheckBox("CPK Analysis")
        self.chk_arr = QCheckBox("AR&R Report")
        self.chk_grr.setChecked(True)
        self.chk_cpk.setChecked(True)
        if self.chk_arr is not None: self.chk_arr.setChecked(False)
        gl.addWidget(self.chk_grr, 1, 0)
        gl.addWidget(self.chk_cpk, 1, 1)
        gl.addWidget(self.chk_arr, 2, 0)

        self.chk_grr.stateChanged.connect(self._check_at_least_one)
        self.chk_cpk.stateChanged.connect(self._check_at_least_one)
        self.chk_arr.stateChanged.connect(self._check_at_least_one)

        gl.addWidget(QLabel("Minitab Path:"), 3, 0)
        self.edt_minitab = QPushButton("Browse…")
        self.edt_minitab.setFixedWidth(90)
        self.edt_minitab.clicked.connect(self._browse_minitab)
        gl.addWidget(self.edt_minitab, 3, 1, 1, 1, Qt.AlignLeft)

        self._lbl_mtpath = QLabel("Not set – charts disabled")
        self._lbl_mtpath.setStyleSheet("color: #ef5350; font-size: 8pt;")
        gl.addWidget(self._lbl_mtpath, 4, 0, 1, 2)

        self.chk_inline_charts = QCheckBox("Insert Minitab charts into report")
        self.chk_inline_charts.setChecked(True)
        gl.addWidget(self.chk_inline_charts, 5, 0, 1, 2)

        lo.addWidget(gb_opt)

        # ── Action buttons ──
        gb_act = QGroupBox("🚀 Run Analysis")
        gl2 = QGridLayout(gb_act)

        self.btn_run = QPushButton("▶  Run Selected")
        self.btn_run.setObjectName("btn-success")
        self.btn_run.setFixedHeight(36)
        self.btn_run.clicked.connect(self._on_run)
        gl2.addWidget(self.btn_run, 0, 0, 1, 2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        gl2.addWidget(self.progress_bar, 1, 0, 1, 2)

        lo.addWidget(gb_act)

        # ── Log ──
        gb_log = QGroupBox("📝 Log")
        gl3 = QVBoxLayout(gb_log)
        self._log_widget = QTextEdit()
        self._log_widget.setObjectName("logWidget")
        self._log_widget.setReadOnly(True)
        gl3.addWidget(self._log_widget)
        lo.addWidget(gb_log)

        return widget

    def _log(self, msg, level="INFO"):
        color = {"INFO": "#d4d4d4", "WARN": "#ffca28", "ERROR": "#ef5350", "OK": "#66bb6a"}.get(level, "#d4d4d4")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_widget.append(f'<span style="color:#6a6a6a">[{ts}]</span> <span style="color:{color}">{msg}</span>')
        logger.info(msg)


    # ── File loading ────────────────────────────

    def _on_load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Excel File", "C:/output",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return
        try:
            self._log(f"Loading: {os.path.basename(path)}")
            self._log("Parsing sheets…")
            loader = DataLoader(path)
            self._loader = loader
            self._path   = path
            self.df_raw = loader.df_raw
            self.df_sheets = loader.sheet_names

            self.sheet_list.clear()
            for name in self.df_sheets:
                self.sheet_list.addItem(name)

            if len(self.df_sheets) == 1:
                self.sheet_list.setCurrentRow(0)
                self._on_sheet_selected(self.sheet_list.item(0))


            # sheet list updated below
            self._log(f"Loaded {len(self.df_raw)} rows, {len(self.df_sheets)} sheet(s).", "OK")
            if self.chk_arr is not None: self.chk_arr.setChecked(False)

        except Exception as e:
            self._log(str(e), "ERROR")
            QMessageBox.critical(self, "Load Error", str(e))

    def _on_sheet_selected(self, item):
        sheet = item.text()
        try:
            # Rebuild loader for the selected sheet so that format detection and
            # normalization use the correct sheet's columns and data.
            self._loader._current_sheet = sheet
            self.df = self._loader.to_grr_format()

            # Auto-detect: show ALL columns that have numeric data (or can be
            # converted to numbers). User picks whatever they need.
            cols = []
            for col in self.df.columns:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    if self.df[col].notna().sum() > 0:
                        cols.append(col)
                    continue
                try:
                    converted = pd.to_numeric(self.df[col], errors="coerce")
                    if converted.notna().sum() > 0:
                        cols.append(col)
                except Exception:
                    pass
            cols.sort()
            self.item_list.clear()
            for col in cols:
                it = QListWidgetItem(col)
                it.setCheckState(Qt.Unchecked)
                it.setData(Qt.UserRole, col)
                self.item_list.addItem(it)
            self._log(f"Sheet '{sheet}': {len(cols)} test items detected.", "OK")
        except Exception as e:
            self._log(f"Sheet load error: {e}", "ERROR")

    # ── Item selection helpers ───────────────────

    def _select_all(self):
        for i in range(self.item_list.count()):
            self.item_list.item(i).setCheckState(Qt.Checked)
        self._refresh_selected_panel()

    def _select_none(self):
        for i in range(self.item_list.count()):
            self.item_list.item(i).setCheckState(Qt.Unchecked)
        self._refresh_selected_panel()

    def _on_item_checked(self, item):
        pass

    def _check_at_least_one(self):
        if not (self.chk_grr.isChecked() or self.chk_cpk.isChecked() or self.chk_arr.isChecked()):
            QMessageBox.warning(self, "Selection", "Select at least one analysis type.")
            return
        # In Excel source mode: checking AR&R immediately opens Sample Mapping config
        if self.chk_arr.isChecked():
            src = self._cmb_source.currentIndex()
            if src != 0:  # not Jason Logs mode
                self._log("AR&R checked — opening Sample Mapping Configuration…")
                self._on_browse_arr_folder()

    # ── Minitab path ────────────────────────────

    def _browse_minitab(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Minitab Mtb.exe",
            r"C:\Program Files\Minitab",
            "Mtb.exe (Mtb.exe);;All Files (*)"
        )
        if path:
            self._minitab_path = path
            self._lbl_mtpath.setText(path)
            self._lbl_mtpath.setStyleSheet("color: #66bb6a; font-size: 8pt;")
            self._log(f"Minitab set: {path}", "OK")

    @property
    def _minitab_path(self):
        return getattr(self, "__minitab_path", None)

    @_minitab_path.setter
    def _minitab_path(self, v):
        setattr(self, "__minitab_path", v)

    def _on_run(self):
        run_grr = self.chk_grr.isChecked()
        run_cpk = self.chk_cpk.isChecked()
        run_arr = self.chk_arr.isChecked()

        # ── AR&R branch ─────────────────────────────
        if run_arr:
            config = self._arr_config
            folder = self._arr_folder
            if not config:
                QMessageBox.information(self, "AR&R Configuration",
                    "Please click the 'Browse…' button to fill in the\n"
                    "Sample Mapping Configuration dialog first.")
                return
            self._run_arr_analysis(folder, config)
            return

        # ── GRR/CPK branch ─────────────────────────
        selected = [self.item_list.item(i).text()
                    for i in range(self.item_list.count())
                    if self.item_list.item(i).checkState() == Qt.Checked]
        if not selected:
            QMessageBox.warning(self, "No Items", "Select at least one test item first.")
            return

        if self.df is None:
            QMessageBox.warning(self, "No Data", "Load data first (Jason logs or Excel).")
            return

        minitab = self._minitab_path if self.chk_inline_charts.isChecked() else None
        self._log(f"Running analysis for {len(selected)} item(s)  [GRR={run_grr}, CPK={run_cpk}]")
        self.progress_bar.setValue(40)

        self.analysis_worker = AnalysisWorker(
            self.df, selected, run_grr, run_cpk, minitab, self._path, self
        )
        self.analysis_worker.progress.connect(self._on_progress)
        self.analysis_worker.finished.connect(self._on_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        self.analysis_worker.start()

    def _run_arr_analysis(self, folder, config):
        """Generate Form-004091 AR&R report.

        Two data sources:
          folder != None : parse Jason logs from folder first, then generate report
          folder == None : use already-loaded Excel data (self.df)
        """
        try:
            self.btn_run.setEnabled(False)
            df_jason = None

            if folder:
                # Path 1: Parse Jason logs from folder
                self._log(f"Parsing AR&R Jason logs: {folder}")
                self.progress_bar.setValue(20)

                # Export full GRR intermediate template (90-row raw format)
                from core.arr_parser import parse_json_folder_raw
                df_raw = parse_json_folder_raw(folder)
                template_dir = Path("C:/output/ARR_template")
                template_dir.mkdir(parents=True, exist_ok=True)
                import datetime as _dt
                ts = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
                template_path = template_dir / f"ARR_template_{ts}.xlsx"
                df_raw.to_excel(template_path, index=False, sheet_name="GRR_intermediate")
                self._log(f"GRR intermediate template exported ({len(df_raw)} rows): {template_path}")
                self.progress_bar.setValue(40)

                # AR&R analysis uses the consolidated 30-row format
                df_jason = arr_parse_json_folder(
                    folder,
                    appraiser_names=None,
                )
                self._log(f"Parsed {len(df_jason)} records (AR&R format)")
                self.progress_bar.setValue(60)
            else:
                # Path 2: Use the GRR intermediate Excel directly.
                # The Excel already has parsed Jason data with one row per measurement.
                # Consolidate to one row per trial: any FAIL in the trial → FAIL.
                if self.df is None:
                    QMessageBox.warning(self, "No Data",
                        "Load an Excel file first via the Load button.")
                    self.btn_run.setEnabled(True)
                    return
                self._log(f"Building AR&R table from loaded Excel ({len(self.df)} rows)…")
                self.progress_bar.setValue(30)

                df_src = self.df.copy()

                # Normalize column names
                col_map = {}
                for col in df_src.columns:
                    cl = col.lower().strip()
                    if cl in ('part_num', 'partnum', 'sample', 'sample_id', 'sampleid'):
                        col_map[col] = 'sample_num'
                    elif cl in ('sn', 'serial', 'serial_number', 'device_sn', 'devicesn'):
                        col_map[col] = 'device_sn'
                df_src = df_src.rename(columns=col_map)

                for col in ["device_sn", "trial"]:
                    if col not in df_src.columns:
                        QMessageBox.warning(self, "Missing Column",
                            f"Required column '{col}' not found in the loaded Excel.")
                        self.btn_run.setEnabled(True)
                        return

                # Derive PASS/FAIL from OVERALL_TEST_RESULT column if present,
                # otherwise fall back to 'status' column
                result_col = None
                for candidate in ["OVERALL_TEST_RESULT", "overall_test_result", "status"]:
                    if candidate in df_src.columns:
                        result_col = candidate
                        break
                if result_col is None:
                    QMessageBox.warning(self, "Missing Column",
                        "No result column (OVERALL_TEST_RESULT / status) found.")
                    self.btn_run.setEnabled(True)
                    return

                def to_pass_fail(v):
                    sv = str(v).strip()
                    if sv in ("0", "pass", "PASS", "Pass", ""):
                        return "PASS"
                    return "FAIL"

                df_src["_pf"] = df_src[result_col].apply(to_pass_fail)

                # Consolidate: group by device_sn + trial → one row per trial
                agg = df_src.groupby(["device_sn", "trial"], as_index=False).agg(
                    status=("_pf", lambda x: "FAIL" if "FAIL" in set(x) else "PASS"),
                    starttime=("starttime", "first"),
                )

                # Strip leading quote from SN and assign appraiser A/B/C
                agg["device_sn"] = agg["device_sn"].astype(str).str.strip().str.lstrip("'")
                uniq_sn = sorted(agg["device_sn"].unique())
                sn_to_app  = {sn: ["A","B","C"][i % 3] for i, sn in enumerate(uniq_sn)}
                sn_to_samp = {sn: i+1 for i, sn in enumerate(uniq_sn)}
                agg["appraiser"]  = agg["device_sn"].map(sn_to_app)
                agg["sample_num"] = agg["device_sn"].map(sn_to_samp)

                df_jason = agg.sort_values(["appraiser","trial","sample_num"]).reset_index(drop=True)
                n_sn   = agg["device_sn"].nunique()
                n_tr   = int(agg["trial"].max())
                n_pass = (agg["status"] == "PASS").sum()
                n_fail = (agg["status"] == "FAIL").sum()
                self._log(f"AR&R table built: {len(df_jason)} rows "
                          f"({n_sn} samples × {n_tr} trials, "
                          f"PASS={n_pass} FAIL={n_fail})")
                self.progress_bar.setValue(60)

            # ── Save ARR data Excel for Minitab to COPY from ──────────
            arr_data_excel = str(Path("C:/output") / f"arr_data_{int(_time.time()*1000)}.xlsx")
            df_jason.to_excel(arr_data_excel, index=False, sheet_name="Sheet1")
            self._log(f"ARR data saved: {arr_data_excel}")

            # ── Run Minitab AR&R if path configured ────────────────────
            chart_paths = {}
            minitab = self._minitab_path if hasattr(self, "_minitab_path") else None
            if minitab and Path(minitab).exists():
                self._log("Generating AR&R charts via Minitab…")
                self.progress_bar.setValue(70)
                try:
                    from core.arr_parser import _run_arr_minitab
                    chart_paths = _run_arr_minitab(
                        mtb_path=minitab,
                        df_jason=df_jason,
                        minitab_opts={
                            "date":    config.get("date", ""),
                            "user":            config.get("reported_by") or "Simon Huo",
                            "product":         config.get("project_name", "Alpha"),
                            "inspector_numbers": config.get("inspector_numbers", []),
                        },
                        excel_path=arr_data_excel,
                        sample_map=config.get("sample_map"),
                    )
                    self._log(f"AR&R charts: {list(chart_paths.values())}")
                except Exception as e:
                    self._log(f"Minitab AR&R skipped: {e}", "ERROR")
                self.progress_bar.setValue(80)
            else:
                if not minitab:
                    self._log("No Minitab path — set in Settings to enable AR&R charts.")
                else:
                    self._log(f"Minitab not found at: {minitab}", "ERROR")

            gen = ARRReportGenerator(output_dir="C:/output")
            out_path = gen.generate(
                df_jason=df_jason,
                sample_map=config["sample_map"],
                part_number=config.get("part_number", "PMMEH-ASM5286"),
                instrument=config.get("instrument", "Alpha MT7H"),
                instrument_no=config.get("instrument_no", ""),
                department=config.get("department", "TE"),
                reported_by=config.get("reported_by", ""),
                project_name=config.get("project_name", ""),
                inspector_numbers=config.get("inspector_numbers", []),
                fixture_no=config.get("fixture_no", ""),
                faults_map=config.get("faults_map"),
                n_trials=config.get("n_trials", 3),
                chart_paths=chart_paths,
            )
            self.progress_bar.setValue(100)
            self.btn_run.setEnabled(True)
            self._log(f"AR&R Report saved: {out_path}", "OK")
            QMessageBox.information(self, "Done",
                "AR&R Report generated successfully!\n\n" + out_path)
        except Exception as e:
            self.btn_run.setEnabled(True)
            import traceback
            self._log(str(e), "ERROR")
            QMessageBox.critical(self, "AR&R Error", str(e) + "\n\n" + traceback.format_exc())

    def _on_progress(self, msg, pct):
        self.progress_bar.setValue(pct)
        self._log(msg)
        self.status_bar.showMessage(msg)

    def _get_cpk_raw_df(self):
        """Return the raw DataFrame to feed the CPK report's raw data sheet.

        The CPK report now does a 1:1 copy of whatever the JsonParser
        produced, so we just return the raw sheet data as-is — no column
        aliasing, no numeric coercion, no missing-Config injection. The
        sheet is selected the same way as before.
        """
        if not self.df_raw:
            return self.df
        sheet_name = None
        if self.sheet_list and self.sheet_list.currentItem() is not None:
            sheet_name = self.sheet_list.currentItem().text()
        if not sheet_name:
            sheet_name = self.df_sheets[0] if self.df_sheets else None
        df = self.df_raw.get(sheet_name) if sheet_name else None
        return df if df is not None else self.df

    def _on_finished(self, results):
        self.progress_bar.setValue(100)
        self.btn_run.setEnabled(True)
        self._log("Analysis complete!", "OK")

        # Check which analyses were run
        grr_results = {k: v for k, v in results.items() if "grr" in v and v["grr"]}
        cpk_results = {k: v for k, v in results.items() if "cpk" in v and v["cpk"]}

        generated = []
        try:
            # Generate GRR Excel report (Form-004090)
            if grr_results and self.chk_grr.isChecked():
                import time as _t2
                _t2_start = _t2.time()
                logger.info(f"Generating GRR Excel report ({len(grr_results)} items)…")
                gen = ExcelReportGenerator(OUTPUT_DIR)
                grr_path = gen.generate(
                    grr_results,
                    self.df,
                    minitab_path=self._minitab_path if self.chk_inline_charts.isChecked() else None,
                    inline_charts=self.chk_inline_charts.isChecked(),
                )
                generated.append(f"GRR: {grr_path}")
                logger.info(f"GRR Report saved: {grr_path} ({_t2.time()-_t2_start:.1f}s)")

            # Generate CPK Excel report
            if cpk_results and self.chk_cpk.isChecked():
                self._log(f"Generating CPK Excel report ({len(cpk_results)} items)…")
                cpk_gen = CPKExcelReportGenerator(OUTPUT_DIR)
                cpk_path = cpk_gen.generate(
                    cpk_results,
                    self._get_cpk_raw_df(),
                    minitab_path=self._minitab_path if self.chk_inline_charts.isChecked() else None,
                    inline_charts=self.chk_inline_charts.isChecked(),
                )
                generated.append(f"CPK: {cpk_path}")
                self._log(f"CPK Report saved: {cpk_path}", "OK")

            if generated:
                msg = "Report(s) generated successfully!\n\n" + "\n".join(generated)
                QMessageBox.information(self, "Done", msg)
            else:
                QMessageBox.information(self, "Done", "Analysis complete, no reports selected.")

        except Exception as e:
            self._log(f"Report error: {e}", "ERROR")
            QMessageBox.critical(self, "Report Error", str(e))

    def _on_analysis_error(self, err):
        self.progress_bar.setValue(0)
        self.btn_run.setEnabled(True)
        self._log(f"ERROR: {err}", "ERROR")
        QMessageBox.critical(self, "Analysis Error", err)

    # ── Drag & drop on main window ─────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith((".xlsx", ".xls")):
                self._btn_file.setText("Loading…")
                self._on_load_file_drop(path)
                self._btn_file.setText("Load…")
            else:
                QMessageBox.warning(self, "Unsupported", "Please drop an Excel file (.xlsx / .xls)")

    def _on_load_file_drop(self, path):
        try:
            self._log(f"Loading dropped file: {os.path.basename(path)}")
            loader = DataLoader(path)
            self._loader = loader
            self._path   = path
            self.df_raw   = loader.df_raw
            self.df_sheets = loader.sheet_names
            self.sheet_list.clear()
            for name in self.df_sheets:
                self.sheet_list.addItem(name)
            if len(self.df_sheets) == 1:
                self.sheet_list.setCurrentRow(0)
                self._on_sheet_selected(self.sheet_list.item(0))

            # sheet list updated below
            self._log(f"Loaded {len(self.df_raw[list(self.df_raw.keys())[0]])} rows.", "OK")
            if self.chk_arr is not None: self.chk_arr.setChecked(False)
        except Exception as e:
            self._log(f"Drop load error: {e}", "ERROR")
