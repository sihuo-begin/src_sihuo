# ──────────────────────────────────────────────
#  AR&R Sample Mapping Configuration Dialog  (tkinter version)
# ──────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox


# Default sample mapping
DEFAULT_SAMPLE_MAP = {
    1:  {"item_name": "Known bad DUT 1",  "error_code": "CONTROL_MT_MODE_STATE",        "expected": 0},
    2:  {"item_name": "Known bad DUT 2",  "error_code": "CONTROL_VBATT_VOLTAGE",         "expected": 0},
    3:  {"item_name": "Known bad DUT 3",  "error_code": "MEAS_HOT_GS_VLOAD",              "expected": 0},
    4:  {"item_name": "Known bad DUT 4",  "error_code": "HOT_GS_ENGINE_THERMISTER_TEMPERATURE_BEFORE_HEAT", "expected": 0},
    5:  {"item_name": "Known Good DUT 5", "error_code": "PASS",                          "expected": 1},
    6:  {"item_name": "Known Good DUT 6", "error_code": "PASS",                          "expected": 1},
    7:  {"item_name": "Known Good DUT 7", "error_code": "PASS",                          "expected": 1},
    8:  {"item_name": "Known Good DUT 8", "error_code": "PASS",                          "expected": 1},
    9:  {"item_name": "Known Good DUT 9", "error_code": "PASS",                          "expected": 1},
    10: {"item_name": "Known Good DUT 10","error_code": "PASS",                          "expected": 1},
}


def show_arr_config_dialog(parent, folder: str):
    """
    Show AR&R configuration dialog (tkinter version).
    Returns (True, config_dict) on OK, (False, None) on Cancel.
    """
    try:
        dlg = ARRConfigDialog(parent, folder)
        parent.wait_window(dlg.top)
        if dlg.result == "ok":
            return True, dlg.get_config()
        return False, None
    except Exception as e:
        import traceback, tkinter.messagebox as mb
        err_msg = "Failed to show config dialog:\n" + str(e)
        mb.showerror("Dialog Error", err_msg)
        return False, None


class ARRConfigDialog:
    def __init__(self, parent, folder: str):
        self.result = None
        self._cfg = {}

        self.top = tk.Toplevel(parent)
        self.top.title("AR&R Sample Mapping Configuration")
        self.top.geometry("720x560")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()

        # Center on screen
        self.top.update_idletasks()
        sw = self.top.winfo_screenwidth()
        sh = self.top.winfo_screenheight()
        w, h = 720, 560
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        # Bring to front
        self.top.lift()
        self.top.focus_force()

        # Make rows/columns expand properly
        self.top.columnconfigure(0, weight=1)

        row = 0

        # ── Report metadata ──────────────────────
        tk.Label(self.top, text="Report Metadata",
                 font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        meta = tk.Frame(self.top)
        meta.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        meta.columnconfigure(1, weight=1)
        meta.columnconfigure(3, weight=1)

        fields = [
            ("Part Number:", "PMMEH-ASM5286"),
            ("Instrument:", "Alpha MT7H"),
            ("Instrument No:", "HVTE-M600271"),
            ("Department:", "TE"),
            ("Reported by:", ""),
            ("Project Name:", "Alpha"),
            ("Fixture No:", "HVTE-M600271"),
        ]
        self._meta_entries = {}
        for i, (label, default) in enumerate(fields):
            r, c = i // 2, (i % 2) * 2
            tk.Label(meta, text=label, font=("Segoe UI", 8)).grid(row=r, column=c, sticky="w", padx=4, pady=2)
            e = ttk.Entry(meta, font=("Segoe UI", 9), width=28)
            e.insert(0, default)
            e.grid(row=r, column=c+1, sticky="ew", padx=4, pady=2)
            self._meta_entries[label.rstrip(":")] = e

        # Inspector rows
        tk.Label(meta, text="Inspector 1:", font=("Segoe UI", 8)).grid(row=4, column=0, sticky="w", padx=4, pady=2)
        self._insp1 = ttk.Entry(meta, font=("Segoe UI", 9), width=28)
        self._insp1.grid(row=4, column=1, sticky="ew", padx=4, pady=2)
        tk.Label(meta, text="Inspector 2:", font=("Segoe UI", 8)).grid(row=4, column=2, sticky="w", padx=4, pady=2)
        self._insp2 = ttk.Entry(meta, font=("Segoe UI", 9), width=28)
        self._insp2.grid(row=4, column=3, sticky="ew", padx=4, pady=2)
        tk.Label(meta, text="Inspector 3:", font=("Segoe UI", 8)).grid(row=5, column=0, sticky="w", padx=4, pady=2)
        self._insp3 = ttk.Entry(meta, font=("Segoe UI", 9), width=28)
        self._insp3.grid(row=5, column=1, sticky="ew", padx=4, pady=2)
        tk.Label(meta, text="Date:", font=("Segoe UI", 8)).grid(row=5, column=2, sticky="w", padx=4, pady=2)
        self._date = ttk.Entry(meta, font=("Segoe UI", 9), width=28)
        self._date.insert(0, "Apr 08, 2026")
        self._date.grid(row=5, column=3, sticky="ew", padx=4, pady=2)

        row += 1

        # ── Sample mapping ───────────────────────
        tk.Label(self.top, text="Sample Mapping  (map each sample → expected result)",
                 font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=(0, 4))
        row += 1

        tbl_frame = tk.Frame(self.top)
        tbl_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        cols = ["#", "Item Name", "Error Code (test item)", "Expected\n(0=FAIL/1=PASS)"]
        widths = [30, 180, 280, 130]
        self._tbl_cols = []
        for j, (col_name, w) in enumerate(zip(cols, widths)):
            lbl = tk.Label(tbl_frame, text=col_name, font=("Segoe UI", 8, "bold"),
                           bg="#e0e0e0", relief="raised", padx=4, pady=2)
            lbl.grid(row=0, column=j, sticky="ew")
            lbl.columnconfigure(0, weight=1)
        tbl_frame.columnconfigure(j, weight=1)

        self._tbl_rows = []  # (item_name_var, err_code_var, expected_var)
        for s in range(1, 11):
            dfl = DEFAULT_SAMPLE_MAP.get(s, {"item_name": f"Sample {s}", "error_code": "PASS", "expected": 1})
            bg = "#f5f5f5" if s % 2 == 0 else "white"

            row_f = tk.Frame(tbl_frame, bg=bg)
            row_f.grid(row=s, column=0, columnspan=4, sticky="ew")

            tk.Label(row_f, text=str(s), font=("Segoe UI", 8), bg=bg, width=3).grid(row=0, column=0, padx=2, pady=1)

            e_name = ttk.Entry(row_f, font=("Segoe UI", 8), width=22)
            e_name.insert(0, dfl["item_name"])
            e_name.grid(row=0, column=1, padx=2, pady=1)

            e_code = ttk.Entry(row_f, font=("Segoe UI", 8), width=30)
            e_code.insert(0, dfl["error_code"])
            e_code.grid(row=0, column=2, padx=2, pady=1)

            exp_var = tk.IntVar(value=dfl["expected"])
            om = ttk.OptionMenu(row_f, exp_var, dfl["expected"], 0, 1)
            om.config(width=12)
            om.grid(row=0, column=3, padx=2, pady=1)

            self._tbl_rows.append((e_name, e_code, exp_var))

        row += 1

        # Quick fill buttons
        quick_frm = tk.Frame(self.top)
        quick_frm.grid(row=row, column=0, sticky="w", pady=(0, 8))
        ttk.Button(quick_frm, text="Samples 1–4 = Known Bad",
                   command=self._quick_bad).pack(side="left", padx=(0, 4))
        ttk.Button(quick_frm, text="Samples 5–10 = Known Good",
                   command=self._quick_good).pack(side="left")

        row += 1

        # Buttons
        btn_frm = tk.Frame(self.top)
        btn_frm.grid(row=row, column=0, sticky="e", pady=(4, 0))
        ttk.Button(btn_frm, text="Cancel", command=self._on_cancel, width=12).pack(side="right", padx=(4, 0))
        ttk.Button(btn_frm, text="OK", command=self._on_ok, width=12).pack(side="right")

    def _quick_bad(self):
        bad_samples = {
            1: ("Known bad DUT 1",  "CONTROL_MT_MODE_STATE"),
            2: ("Known bad DUT 2",  "CONTROL_VBATT_VOLTAGE"),
            3: ("Known bad DUT 3",  "MEAS_HOT_GS_VLOAD"),
            4: ("Known bad DUT 4",  "HOT_GS_ENGINE_THERMISTER_TEMPERATURE_BEFORE_HEAT"),
        }
        for i, s in enumerate(range(1, 11)):
            name, code = bad_samples.get(s, (f"Known Good DUT {s}", "PASS"))
            exp = 0 if s <= 4 else 1
            self._tbl_rows[i][0].delete(0, tk.END)
            self._tbl_rows[i][0].insert(0, name)
            self._tbl_rows[i][1].delete(0, tk.END)
            self._tbl_rows[i][1].insert(0, code)
            self._tbl_rows[i][2].set(exp)

    def _quick_good(self):
        for i, s in enumerate(range(5, 11)):
            self._tbl_rows[i][0].delete(0, tk.END)
            self._tbl_rows[i][0].insert(0, f"Known Good DUT {s}")
            self._tbl_rows[i][1].delete(0, tk.END)
            self._tbl_rows[i][1].insert(0, "PASS")
            self._tbl_rows[i][2].set(1)

    def _on_ok(self):
        self._cfg = self.get_config()
        self.result = "ok"
        self.top.destroy()

    def _on_cancel(self):
        self.result = "cancel"
        self.top.destroy()

    def get_config(self) -> dict:
        sample_map = {}
        for s, (e_name, e_code, exp_var) in enumerate(self._tbl_rows, start=1):
            sample_map[s] = {
                "item_name":  e_name.get().strip() or f"Sample {s}",
                "error_code": e_code.get().strip() or "PASS",
                "expected":    exp_var.get(),
            }

        inspectors = [e.get().strip() for e in [self._insp1, self._insp2, self._insp3] if e.get().strip()]

        faults_map = {}
        for s in range(1, 11):
            code = sample_map[s]["error_code"]
            name = sample_map[s]["item_name"]
            if code != "PASS":
                faults_map[s] = (code, name)

        return {
            "sample_map":     sample_map,
            "faults_map":     faults_map,
            "n_samples":      10,
            "n_appraisers":    3,
            "n_trials":        3,
            "part_number":    self._meta_entries["Part Number"].get().strip() or "PMMEH-ASM5286",
            "instrument":      self._meta_entries["Instrument"].get().strip() or "Alpha MT7H",
            "instrument_no":   self._meta_entries["Instrument No"].get().strip(),
            "department":      self._meta_entries["Department"].get().strip() or "TE",
            "reported_by":     self._meta_entries["Reported by"].get().strip(),
            "project_name":   self._meta_entries["Project Name"].get().strip(),
            "fixture_no":     self._meta_entries["Fixture No"].get().strip(),
            "date":           self._date.get().strip(),
            "inspector_numbers": inspectors,
        }
