# ──────────────────────────────────────────────
#  AR&R Sample Mapping Configuration Dialog
# ──────────────────────────────────────────────
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox,
    QDialogButtonBox, QGroupBox, QMessageBox, QScrollArea,
    QWidget, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import json
from pathlib import Path

from utils.config import (
    ARR_FORM_DEFAULTS,
    DEFAULT_SAMPLE_MAP,
    DEFAULT_FAULTS,
    ARR_TEST_STRUCTURE,
    QUICK_FILL_BAD_SAMPLES,
)

# Persist user choice to skip the dialog when config is complete.
# Stored next to this file (writable) so user can delete it to re-enable the dialog.
_SKIP_FLAG_FILE = Path(__file__).parent / ".arr_dialog_skipped.flag"


def show_arr_config_dialog(parent, folder: str = None, force: bool = False):
    """
    Show AR&R configuration dialog, pre-filled from utils.config.

    If the user previously checked "Use defaults from config.py, don't ask again"
    and all required values are present in ARR_FORM_DEFAULTS, this returns
    the config dict directly without showing the dialog. Pass `force=True` to
    always show the dialog.

    Returns (True, config_dict) on OK, (False, None) on Cancel.
    """
    if not force and _SKIP_FLAG_FILE.exists():
        try:
            defaults = _build_config_from_defaults()
            if defaults is not None:
                return True, defaults
        except Exception:
            pass  # fall through to dialog if anything goes wrong

    dlg = ARRConfigDialog(parent, folder)
    dlg.setWindowModality(Qt.ApplicationModal)
    # Ensure dialog appears in front after file picker closes
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowStaysOnTopHint)
    dlg.raise_()
    dlg.activateWindow()
    ret = dlg.exec_()
    if ret == QDialog.Accepted:
        cfg = dlg.get_config()
        if dlg._skip_next_time.isChecked():
            try:
                _SKIP_FLAG_FILE.write_text("skipped\n", encoding="utf-8")
            except Exception:
                pass
        return True, cfg
    return False, None


def _build_config_from_defaults() -> dict:
    """Build a config dict purely from ARR_FORM_DEFAULTS + DEFAULT_SAMPLE_MAP
    + DEFAULT_FAULTS + ARR_TEST_STRUCTURE. Returns None if required values
    are missing."""
    _d = ARR_FORM_DEFAULTS
    # Required for the report to be valid
    if not _d.get("part_number"):
        return None
    if not _d.get("instrument"):
        return None

    sample_map = {int(k): dict(v) for k, v in DEFAULT_SAMPLE_MAP.items()}

    inspectors = list(_d.get("inspector_numbers") or [])

    import string
    app_names = {}
    for i, insp in enumerate(inspectors):
        app_names[insp] = string.ascii_uppercase[i]

    faults_map = {}
    for s in range(1, len(sample_map) + 1):
        code = sample_map.get(s, {}).get("error_code", "")
        name = sample_map.get(s, {}).get("item_name", "")
        if code and code != "PASS":
            faults_map[s] = (code, name)

    from datetime import datetime
    date_txt = datetime.now().strftime(_d.get("date_format", "%b %d, %Y"))

    return {
        "sample_map":        sample_map,
        "appraiser_names":   app_names,
        "faults_map":        faults_map,
        "n_samples":         ARR_TEST_STRUCTURE["n_samples"],
        "n_appraisers":      ARR_TEST_STRUCTURE["n_appraisers"],
        "n_trials":          ARR_TEST_STRUCTURE["n_trials"],
        "part_number":       _d["part_number"],
        "instrument":        _d["instrument"],
        "instrument_no":     _d.get("instrument_no", ""),
        "department":        _d.get("department", ""),
        "reported_by":       _d.get("reported_by", ""),
        "project_name":      _d.get("project_name", ""),
        "fixture_no":        _d.get("fixture_no", ""),
        "date":              date_txt,
        "inspector_numbers": inspectors,
    }


class ARRConfigDialog(QDialog):
    def __init__(self, parent, folder: str):
        super().__init__(parent)
        self.setWindowTitle("AR&R Sample Mapping Configuration")
        self.setMinimumSize(700, 520)
        self._folder = folder

        self._setup_ui()

    def _setup_ui(self):
        # Set WindowFlags before showing to ensure correct modality
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout(self)

        # ── 0. Source banner (proves values came from config.py) ──
        _d = ARR_FORM_DEFAULTS
        _insp = _d.get("inspector_numbers") or []
        _insp_summary = ", ".join(_insp) if _insp else "(empty — edit utils/config.py)"
        banner = QLabel(
            f"✔ Values pre-filled from <b>utils/config.py</b>  ·  "
            f"Inspectors: {_insp_summary}  ·  "
            f"Part Number: {_d.get('part_number', '')}"
        )
        banner.setStyleSheet("background:#E8F5E9; padding:6px; border-radius:4px; color:#1B5E20;")
        banner.setWordWrap(True)
        layout.addWidget(banner)

        # ── 1. Report metadata ─────────────────────
        meta_gb = QGroupBox("Report Metadata")
        meta_gl = QGridLayout(meta_gb)

        self._edt_part    = self._mk_line(ARR_FORM_DEFAULTS["part_number"])
        self._edt_instr   = self._mk_line(ARR_FORM_DEFAULTS["instrument"])
        self._edt_instr_no= self._mk_line(ARR_FORM_DEFAULTS["instrument_no"])
        self._edt_dept    = self._mk_line(ARR_FORM_DEFAULTS["department"])
        self._edt_reported= self._mk_line(ARR_FORM_DEFAULTS["reported_by"])
        self._edt_project = self._mk_line(ARR_FORM_DEFAULTS["project_name"])
        self._edt_fixture = self._mk_line(ARR_FORM_DEFAULTS["fixture_no"])
        self._edt_date    = self._mk_line("")
        self._edt_date.setPlaceholderText(ARR_FORM_DEFAULTS["date_placeholder"])

        _insp_defaults = (ARR_FORM_DEFAULTS.get("inspector_numbers") or ["", "", ""])
        self._edt_insp1 = self._mk_line(_insp_defaults[0] if len(_insp_defaults) > 0 else "")
        self._edt_insp1.setPlaceholderText(ARR_FORM_DEFAULTS["inspector_placeholders"][0])
        self._edt_insp2 = self._mk_line(_insp_defaults[1] if len(_insp_defaults) > 1 else "")
        self._edt_insp2.setPlaceholderText(ARR_FORM_DEFAULTS["inspector_placeholders"][1])
        self._edt_insp3 = self._mk_line(_insp_defaults[2] if len(_insp_defaults) > 2 else "")
        self._edt_insp3.setPlaceholderText(ARR_FORM_DEFAULTS["inspector_placeholders"][2])

        row = 0
        meta_gl.addWidget(QLabel("Part Number:"),       row, 0); meta_gl.addWidget(self._edt_part,     row, 1)
        meta_gl.addWidget(QLabel("Instrument:"),         row, 2); meta_gl.addWidget(self._edt_instr,    row, 3)
        row += 1
        meta_gl.addWidget(QLabel("Instrument No:"),      row, 0); meta_gl.addWidget(self._edt_instr_no,row, 1)
        meta_gl.addWidget(QLabel("Department:"),         row, 2); meta_gl.addWidget(self._edt_dept,     row, 3)
        row += 1
        meta_gl.addWidget(QLabel("Reported by:"),        row, 0); meta_gl.addWidget(self._edt_reported,row, 1)
        meta_gl.addWidget(QLabel("Project Name:"),       row, 2); meta_gl.addWidget(self._edt_project,  row, 3)
        row += 1
        meta_gl.addWidget(QLabel("Inspector 1:"),        row, 0); meta_gl.addWidget(self._edt_insp1,    row, 1)
        meta_gl.addWidget(QLabel("Inspector 2:"),       row, 2); meta_gl.addWidget(self._edt_insp2,    row, 3)
        row += 1
        meta_gl.addWidget(QLabel("Inspector 3:"),        row, 0); meta_gl.addWidget(self._edt_insp3,    row, 1)
        meta_gl.addWidget(QLabel("Fixture No:"),         row, 2); meta_gl.addWidget(self._edt_fixture,  row, 3)
        row += 1
        meta_gl.addWidget(QLabel("Date:"),               row, 0); meta_gl.addWidget(self._edt_date,    row, 1)
        row += 1

        layout.addWidget(meta_gb)

        # ── 2. Sample mapping table ───────────────
        map_gb = QGroupBox("Sample Mapping  (map each sample to its expected result)")
        map_lo = QVBoxLayout(map_gb)

        self._tbl = QTableWidget(10, 4)
        self._tbl.setHorizontalHeaderLabels(["Sample #", "Item Name", "Error Code (test item)", "Expected\n(0=FAIL/1=PASS)"])
        self._tbl.setColumnWidth(0, 70)
        self._tbl.setColumnWidth(1, 160)
        self._tbl.setColumnWidth(2, 300)
        self._tbl.setColumnWidth(3, 80)
        self._tbl.verticalHeader().setVisible(False)

        self._sample_rows = []  # list of (item_name_edt, error_code_edt, expected_cmb)
        for s in range(1, 11):
            dfl = DEFAULT_SAMPLE_MAP.get(s, {"item_name": f"Sample {s}", "error_code": "PASS", "expected": 1})
            row_data = [
                str(s),
                dfl["item_name"],
                dfl["error_code"],
            ]
            items = [QTableWidgetItem(rd) for rd in row_data]
            for it in items[:3]:
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)  # read-only for sample#
            self._tbl.setItem(s - 1, 0, items[0])
            self._tbl.setItem(s - 1, 1, items[1])
            self._tbl.setItem(s - 1, 2, items[2])
            # Combo for expected
            cmb = QComboBox()
            cmb.addItems(["0 — FAIL (Known Bad)", "1 — PASS (Known Good)"])
            cmb.setCurrentIndex(0 if dfl["expected"] == 0 else 1)
            self._tbl.setCellWidget(s - 1, 3, cmb)
            self._sample_rows.append((items[1], items[2], cmb))
            for c in range(3):
                items[c].setBackground
        map_lo.addWidget(self._tbl)

        # Quick-fill buttons
        quick_lo = QHBoxLayout()
        quick_lo.addWidget(QLabel("Quick fill:"))
        btn_4bad = QPushButton("Set samples 1–4 as Known Bad")
        btn_4bad.clicked.connect(lambda: self._quick_fill_bad())
        btn_6good = QPushButton("Set samples 5–10 as Known Good")
        btn_6good.clicked.connect(lambda: self._quick_fill_good())
        quick_lo.addWidget(btn_4bad)
        quick_lo.addWidget(btn_6good)
        quick_lo.addStretch()
        map_lo.addLayout(quick_lo)
        layout.addWidget(map_gb)

        # ── 3. GRR Structure ───────────────────────
        struct_gb = QGroupBox("Test Structure")
        struct_gl = QGridLayout(struct_gb)
        self._spn_n_samples   = self._mk_spin(ARR_TEST_STRUCTURE["n_samples"],
                                                  *ARR_TEST_STRUCTURE["n_samples_range"])
        self._spn_n_appraisers= self._mk_spin(ARR_TEST_STRUCTURE["n_appraisers"],
                                                  *ARR_TEST_STRUCTURE["n_appraisers_range"])
        self._spn_n_trials    = self._mk_spin(ARR_TEST_STRUCTURE["n_trials"],
                                                  *ARR_TEST_STRUCTURE["n_trials_range"])
        struct_gl.addWidget(QLabel("Number of samples (DUTs):"),   0, 0)
        struct_gl.addWidget(self._spn_n_samples,                  0, 1)
        struct_gl.addWidget(QLabel("Number of appraisers (inspectors):"), 1, 0)
        struct_gl.addWidget(self._spn_n_appraisers,               1, 1)
        struct_gl.addWidget(QLabel("Number of trials per appraiser:"),   2, 0)
        struct_gl.addWidget(self._spn_n_trials,                   2, 1)
        layout.addWidget(struct_gb)

        # ── Buttons ────────────────────────────────
        btn_lo = QHBoxLayout()
        self._skip_next_time = QCheckBox("Use defaults from config.py, don't ask again")
        self._skip_next_time.setToolTip(
            "If checked, this dialog will be skipped on future runs.\n"
            "All values will be read directly from utils/config.py.\n"
            "Delete ui/.arr_dialog_skipped.flag to re-enable the dialog."
        )
        btn_lo.addWidget(self._skip_next_time)
        btn_lo.addStretch()
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        btn_lo.addWidget(btns)
        layout.addLayout(btn_lo)

    @staticmethod
    def _mk_line(text=""):
        ed = QLineEdit(text)
        ed.setMinimumWidth(140)
        return ed

    @staticmethod
    def _mk_spin(val, lo, hi):
        sp = QSpinBox()
        sp.setRange(lo, hi)
        sp.setValue(val)
        return sp

    def _quick_fill_bad(self):
        bad_samples = QUICK_FILL_BAD_SAMPLES
        for s in range(1, 11):
            if s in bad_samples:
                name, code = bad_samples[s]
                self._tbl.item(s - 1, 1).setText(name)
                self._tbl.item(s - 1, 2).setText(code)
                self._tbl.cellWidget(s - 1, 3).setCurrentIndex(0)
            else:
                self._tbl.item(s - 1, 1).setText(f"Known Good DUT {s}")
                self._tbl.item(s - 1, 2).setText("PASS")
                self._tbl.cellWidget(s - 1, 3).setCurrentIndex(1)

    def _quick_fill_good(self):
        for s in range(5, 11):
            self._tbl.item(s - 1, 1).setText(f"Known Good DUT {s}")
            self._tbl.item(s - 1, 2).setText("PASS")
            self._tbl.cellWidget(s - 1, 3).setCurrentIndex(1)

    def _on_ok(self):
        # Validate at least one inspector number is filled
        inspectors = [ed.text().strip() for ed in
                      (self._edt_insp1, self._edt_insp2, self._edt_insp3) if ed.text().strip()]
        # Allow empty — just accept
        self.accept()

    def get_config(self) -> dict:
        sample_map = {}
        for s in range(1, 11):
            item_name  = self._tbl.item(s - 1, 1).text()
            err_code   = self._tbl.item(s - 1, 2).text()
            expected   = 0 if self._tbl.cellWidget(s - 1, 3).currentIndex() == 0 else 1
            sample_map[s] = {
                "item_name":  item_name,
                "error_code": err_code,
                "expected":   expected,
            }

        inspectors = []
        for ed in (self._edt_insp1, self._edt_insp2, self._edt_insp3):
            v = ed.text().strip()
            if v:
                inspectors.append(v)

        # Build appraiser_names: LOG_USER_NAME raw value -> display letter (A, B, C)
        import string
        app_names = {}
        for i, insp in enumerate(inspectors):
            app_names[insp] = string.ascii_uppercase[i]

        faults_map = {}
        for s in range(1, 11):
            code = self._tbl.item(s - 1, 2).text()
            name = self._tbl.item(s - 1, 1).text()
            if code != "PASS":
                faults_map[s] = (code, name)

        date_txt = self._edt_date.text().strip()
        if not date_txt:
            from datetime import datetime
            date_txt = datetime.now().strftime(ARR_FORM_DEFAULTS["date_format"])

        return {
            "sample_map":      sample_map,
            "appraiser_names": app_names,
            "faults_map":     faults_map,
            "n_samples":      self._spn_n_samples.value(),
            "n_appraisers":   self._spn_n_appraisers.value(),
            "n_trials":       self._spn_n_trials.value(),
            "part_number":    self._edt_part.text().strip() or ARR_FORM_DEFAULTS["part_number"],
            "instrument":     self._edt_instr.text().strip() or ARR_FORM_DEFAULTS["instrument"],
            "instrument_no":  self._edt_instr_no.text().strip() or "",
            "department":     self._edt_dept.text().strip() or ARR_FORM_DEFAULTS["department"],
            "reported_by":    self._edt_reported.text().strip() or "",
            "project_name":   self._edt_project.text().strip() or "",
            "fixture_no":     self._edt_fixture.text().strip() or "",
            "date":           date_txt,
            "inspector_numbers": inspectors,
        }
