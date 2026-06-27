# ──────────────────────────────────────────────
#  Main Window  (tkinter backend)
#  Used when PyQt5 is not available (e.g. Linux servers)
# ──────────────────────────────────────────────
import logging
import os
import traceback
import threading
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import tkinter as tk
from tkinter import (
    ttk, filedialog, messagebox, scrolledtext,
    Listbox, END, SINGLE, MULTIPLE, ANCHOR
)

from core.data_loader import DataLoader
from core.grr_analyzer import GRRAnalyzer
from core.cpk_analyzer import CPKAnalyzer
from core.json_parser  import JsonParser
from core.arr_parser   import parse_json_folder as arr_parse_json_folder
from report.excel_report_generator    import ExcelReportGenerator
from report.cpk_excel_report_generator import CPKExcelReportGenerator
from report.arr_excel_report_generator import ARRReportGenerator
from utils.config import (
    APP_NAME, APP_VERSION, AUTHOR,
    LED_INTENSITY_COLS, OUTPUT_DIR
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════
class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.df: Optional[object]       = None
        self.df_raw: Optional[dict]     = None
        self.sheet_names: List[str]    = []
        self.available_items: List[str]  = []
        self.minitab_path: Optional[str] = None
        self._data_mode: str = "excel"  # "json" or "excel"

        self._build_ui()
        self._log("Welcome! Select a data source and click Run.", "info")

    # ── UI construction ────────────────────────

    def _build_ui(self):
        # ── Top header ──
        hdr = tk.Frame(self.root, bg="#1a2a6c", height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"🦞 {APP_NAME}", font=("Segoe UI", 14, "bold"),
                 fg="white", bg="#1a2a6c").pack(pady=(6, 2))
        tk.Label(hdr, text=f"GRR & CPK Analysis Tool  ·  {AUTHOR}  ·  {APP_VERSION}",
                 font=("Segoe UI", 9), fg="#aab4d4", bg="#1a2a6c").pack()

        # ── Main body ──
        body = tk.PanedWindow(self.root, orient="horizontal", sashrelief="raised", sashwidth=4)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # ── Left panel ──
        left = tk.Frame(body, width=300)
        body.add(left, stretch="never")

        # ── Data Source ──
        frm_src = tk.LabelFrame(left, text="📂  Data Source", font=("Segoe UI", 9, "bold"),
                                padx=8, pady=6)
        frm_src.pack(fill="x", pady=(0, 8))

        self.src_var = tk.StringVar(value="excel")
        rb_json = ttk.Radiobutton(frm_src, text="📁 Jason Logs Folder",
                                  variable=self.src_var, value="json",
                                  command=self._on_src_changed)
        rb_json.pack(anchor="w")
        self._frm_json = tk.Frame(frm_src)
        self._frm_json.pack(fill="x", pady=(0, 6))
        self.lbl_json_folder = tk.Label(self._frm_json, text="(select folder first)",
                                        fg="#90a4ae", font=("Segoe UI", 8))
        self.lbl_json_folder.pack(side="left", fill="x", expand=True)
        ttk.Button(self._frm_json, text="Browse…", width=8,
                   command=self._on_browse_json_folder).pack(side="right")

        rb_xlsx = ttk.Radiobutton(frm_src, text="📄 Intermediate Excel",
                                  variable=self.src_var, value="excel",
                                  command=self._on_src_changed)
        rb_xlsx.pack(anchor="w")
        self._frm_xlsx = tk.Frame(frm_src)
        self._frm_xlsx.pack(fill="x")
        self.lbl_xlsx_file = tk.Label(self._frm_xlsx, text="No file loaded",
                                       fg="#90a4ae", font=("Segoe UI", 8))
        self.lbl_xlsx_file.pack(side="left", fill="x", expand=True)
        ttk.Button(self._frm_xlsx, text="Load…", width=8,
                   command=self._on_load_file).pack(side="right")

        # GRR Structure (JSON mode only)
        self._frm_struct = tk.LabelFrame(left, text="📐  GRR Structure  (Jason Logs mode)",
                                         font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        self._frm_struct.pack(fill="x", pady=(0, 8))
        self._frm_struct.pack_forget()  # hidden by default

        struct_row1 = tk.Frame(self._frm_struct)
        struct_row1.pack(fill="x", pady=2)
        tk.Label(struct_row1, text="Parts:", font=("Segoe UI", 8)).pack(side="left")
        self.spn_parts = ttk.Spinbox(struct_row1, from_=2, to=100, width=5)
        self.spn_parts.set(10); self.spn_parts.pack(side="left", padx=(4, 12))
        tk.Label(struct_row1, text="Operators:", font=("Segoe UI", 8)).pack(side="left")
        self.spn_ops = ttk.Spinbox(struct_row1, from_=2, to=20, width=5)
        self.spn_ops.set(3); self.spn_ops.pack(side="left", padx=(4, 0))

        struct_row2 = tk.Frame(self._frm_struct)
        struct_row2.pack(fill="x", pady=2)
        tk.Label(struct_row2, text="Trials:", font=("Segoe UI", 8)).pack(side="left")
        self.spn_trials = ttk.Spinbox(struct_row2, from_=2, to=20, width=5)
        self.spn_trials.set(3); self.spn_trials.pack(side="left", padx=(4, 0))

        # Sheet selector
        frm_sheet = tk.LabelFrame(left, text="📋  Select Sheet", font=("Segoe UI", 9, "bold"),
                                  padx=8, pady=6)
        frm_sheet.pack(fill="x", pady=(0, 8))
        self.sheet_combo = ttk.Combobox(frm_sheet, state="readonly", font=("Segoe UI", 9))
        self.sheet_combo.pack(fill="x")
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda e: self._on_sheet_selected())

        # Item selector
        frm_items = tk.LabelFrame(left, text="☑  Select Test Items", font=("Segoe UI", 9, "bold"),
                                  padx=8, pady=6)
        frm_items.pack(fill="both", expand=True, pady=(0, 8))

        btn_frame = tk.Frame(frm_items)
        btn_frame.pack(fill="x", pady=(0, 4))
        ttk.Button(btn_frame, text="Select All",   command=self._select_all).pack(side="left", padx=(0, 4))
        ttk.Button(btn_frame, text="Select None", command=self._select_none).pack(side="left")

        self.item_listbox = Listbox(frm_items, selectmode=MULTIPLE,
                                    font=("Segoe UI", 9), height=12,
                                    activestyle="dotbox", selectbackground="#c5cae9",
                                    selectforeground="#1a2a6c")
        self.item_listbox.pack(fill="both", expand=True)

        self.lbl_item_count = tk.Label(frm_items, text="0 items loaded",
                                        fg="#78909c", font=("Segoe UI", 8))
        self.lbl_item_count.pack()

        # ── Right panel ──
        right = tk.Frame(body)
        body.add(right, stretch="always")

        # Options
        frm_opt = tk.LabelFrame(right, text="⚙  Analysis Options", font=("Segoe UI", 9, "bold"),
                                padx=10, pady=8)
        frm_opt.pack(fill="x", pady=(0, 8))

        row1 = tk.Frame(frm_opt)
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Analysis Type:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.chk_grr = tk.BooleanVar(value=True)
        self.chk_cpk = tk.BooleanVar(value=True)
        self.chk_arr = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="GRR Analysis", variable=self.chk_grr,
                        command=self._check_at_least_one).pack(side="left", padx=(12, 6))
        ttk.Checkbutton(row1, text="CPK Analysis", variable=self.chk_cpk,
                        command=self._check_at_least_one).pack(side="left", padx=(0, 6))
        ttk.Checkbutton(row1, text="AR&R Report", variable=self.chk_arr,
                        command=self._check_at_least_one).pack(side="left")

        row2 = tk.Frame(frm_opt)
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Minitab Path:", font=("Segoe UI", 9)).pack(side="left")
        ttk.Button(row2, text="Browse…", command=self._browse_minitab,
                  width=12).pack(side="left", padx=(8, 4))
        self.lbl_mtpath = tk.Label(row2, text="Not set — charts disabled",
                                    fg="#ef5350", font=("Segoe UI", 8))
        self.lbl_mtpath.pack(side="left")

        self.chk_inline = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm_opt, text="Insert Minitab charts into report",
                        variable=self.chk_inline).pack(anchor="w")

        # Action buttons
        frm_act = tk.LabelFrame(right, text="🚀  Run Analysis", font=("Segoe UI", 9, "bold"),
                                padx=10, pady=8)
        frm_act.pack(fill="x", pady=(0, 8))

        self.btn_run = ttk.Button(frm_act, text="▶  Run Selected", command=self._on_run)
        self.btn_run.pack(fill="x", pady=(0, 4))

        self.progress = ttk.Progressbar(frm_act, mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        self.status_label = tk.Label(frm_act, text="Ready", fg="#3949ab", font=("Segoe UI", 8))
        self.status_label.pack()

        # Log
        frm_log = tk.LabelFrame(right, text="📝  Log", font=("Segoe UI", 9, "bold"),
                                padx=8, pady=4)
        frm_log.pack(fill="both", expand=True)
        self.log_text = scrolledtext.ScrolledText(
            frm_log, font=("Consolas", 8), bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white", relief="flat", wrap="none"
        )
        self.log_text.pack(fill="both", expand=True)

    # ── Logging ────────────────────────────────

    def _log(self, msg: str, level: str = "info"):
        color = {
            "info":  "#d4d4d4",
            "warn":  "#ffca28",
            "error": "#ef5350",
            "ok":    "#66bb6a",
        }.get(level, "#d4d4d4")
        ts = datetime.now().strftime("%H:%M:%S")
        tag = f"lvl_{id(msg)}"
        self.log_text.insert(END, f"[{ts}] {msg}\n")
        self.log_text.tag_add(tag, f"{END} linestart", END)
        self.log_text.tag_config(tag, foreground=color)
        self.log_text.see(END)

    # ── Source switching ──────────────────────

    def _on_src_changed(self):
        self._data_mode = self.src_var.get()
        if self._data_mode == "json":
            self._frm_struct.pack(fill="x", pady=(0, 8))
            self._frm_xlsx.pack_forget()
            self._log("Mode: Jason Logs — set folder above then click Run", "info")
        else:
            self._frm_struct.pack_forget()
            self._frm_xlsx.pack(fill="x")
            self._log("Mode: Intermediate Excel — load file above then click Run", "info")

    # ── File / Folder loading ─────────────────

    def _on_browse_json_folder(self):
        folder = filedialog.askdirectory(title="Select GRR Jason Logs Folder")
        if not folder:
            return
        self._json_folder = folder
        self.lbl_json_folder.config(text=os.path.basename(folder), fg="#37474f")
        self._log(f"Jason log folder: {folder}")

        # Parse JSON immediately
        parts     = int(self.spn_parts.get())
        operators = int(self.spn_ops.get())
        trials    = int(self.spn_trials.get())

        self._log(f"Structure: {parts} parts × {operators} ops × {trials} trials")
        self.btn_run.config(state="disabled")
        self._log("Parsing Jason logs…")

        def bg():
            try:
                parser = JsonParser(folder)
                parser.parse()
                parser.assign_trials(parts=parts, operators=operators, trials=trials)
                excel_path = os.path.join("C:/output", f"raw_data---{datetime.now():%Y%m%d%H%M%S}.xlsx")
                os.makedirs("C:/output", exist_ok=True)
                parser.export(excel_path)
                self._on_json_parsed(excel_path)
            except Exception as e:
                self._on_parse_error(str(e))

        threading.Thread(target=bg, daemon=True).start()

    def _on_json_parsed(self, excel_path: str):
        self.root.after(0, lambda: self._log(f"Intermediate Excel: {excel_path}", "ok"))
        self._path = excel_path
        try:
            self.loader = DataLoader(excel_path)
            self.df_raw    = self.loader.df_raw
            self.df        = self.loader.df
            self.sheet_names = self.loader.sheet_names

            def ui():
                self.sheet_combo["values"] = self.sheet_names
                self.sheet_combo.current(0)
                self.lbl_xlsx_file.config(text=os.path.basename(excel_path), fg="#37474f")
                self._on_sheet_selected()
                self.btn_run.config(state="normal")
                self._log(f"Done — {len(self.df)} records, {self.sheet_names} sheet(s)", "ok")

            self.root.after(0, ui)
        except Exception as e:
            self.root.after(0, lambda: self._on_parse_error(str(e)))

    def _on_parse_error(self, err: str):
        self.root.after(0, lambda: [
            self._log(f"Parse error: {err}", "error"),
            self.btn_run.config(state="normal"),
            messagebox.showerror("Parse Error", err)
        ])

    def _on_load_file(self):
        path = filedialog.askopenfilename(
            title="Open GRR/CPK Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*")]
        )
        if not path:
            return
        try:
            self._log(f"Loading: {os.path.basename(path)}")
            self._path = path
            self.loader     = DataLoader(path)
            self.df_raw    = self.loader.df_raw
            self.df        = self.loader.df
            self.sheet_names = self.loader.sheet_names

            self.sheet_combo["values"] = self.sheet_names
            self.sheet_combo.current(0)
            self.lbl_xlsx_file.config(text=os.path.basename(path), fg="#37474f")
            self._on_sheet_selected()
            self._log(f"Loaded {len(self.df_raw)} rows, {len(self.sheet_names)} sheet(s).", "ok")
        except Exception as e:
            self._log(f"Load error: {e}", "error")
            messagebox.showerror("Load Error", str(e))

    def _on_sheet_selected(self):
        sheet = self.sheet_combo.get()
        if not sheet or not self.df_raw:
            return
        try:
            df = self.df
            cols = [c for c in df.columns
                    if c in LED_INTENSITY_COLS
                    or c in self.loader.PNUM_TO_LED.values()]
            self.available_items = cols
            self.item_listbox.delete(0, END)
            for i, col in enumerate(cols):
                self.item_listbox.insert(END, f"  {col}")
                tag = "even" if i % 2 == 0 else "odd"
                self.item_listbox.itemconfig(i, bg="#f5f5f5" if tag == "even" else "white")
            self.lbl_item_count.config(text=f"{len(cols)} LED items loaded")
            self._log(f"Sheet '{sheet}': {len(cols)} LED items available.", "ok")
        except Exception as e:
            self._log(f"Sheet error: {e}", "error")

    # ── Item selection ────────────────────────

    def _select_all(self):
        self.item_listbox.select_set(0, END)

    def _select_none(self):
        self.item_listbox.select_clear(0, END)

    def _check_at_least_one(self):
        if not (self.chk_grr.get() or self.chk_cpk.get() or self.chk_arr.get()):
            messagebox.showwarning("Selection", "Select at least one analysis type.")
            self.chk_grr.set(True)
            self.chk_cpk.set(True)

    # ── Minitab path ───────────────────────────

    def _browse_minitab(self):
        path = filedialog.askopenfilename(
            title="Select Minitab Mtb.exe",
            initialdir=r"C:\Program Files\Minitab",
            filetypes=[("Mtb.exe", "Mtb.exe"), ("All Files", "*")]
        )
        if path:
            self.minitab_path = path
            self.lbl_mtpath.config(text=path, fg="#66bb6a")
            self._log(f"Minitab set: {path}", "ok")

    # ── Run ───────────────────────────────────

    def _on_run(self):
        run_arr = self.chk_arr.get()
        run_grr = self.chk_grr.get()
        run_cpk = self.chk_cpk.get()

        # ── AR&R branch ───────────────────────
        if run_arr:
            self._run_arr()
            return

        # ── GRR/CPK branch ───────────────────
        if self.df is None:
            messagebox.showwarning("No Data", "Load a file or Jason log folder first.")
            return
        selections = self.item_listbox.curselection()
        if not selections:
            messagebox.showwarning("No Items", "Select at least one test item.")
            return

        selected = [self.available_items[i] for i in selections]
        mt_path  = self.minitab_path if self.chk_inline.get() else None

        self._log(f"Running: {len(selected)} items  [GRR={run_grr}, CPK={run_cpk}]")
        self.btn_run.config(state="disabled")
        self.progress["value"] = 0

        def bg():
            results = {}
            total = len(selected)
            try:
                for i, item in enumerate(selected):
                    pct = 100 * (i + 1) / total
                    self.root.after(0, lambda p=pct, m=f"Analyzing {item}…": [
                        self.progress.config(value=p),
                        self.status_label.config(text=m)
                    ])
                    self.root.after(0, lambda m=f"Analyzing {item}…": self._log(m))
                    res = {}
                    if run_grr:
                        grr = GRRAnalyzer(self.df, item)
                        res["grr"] = grr.compute(mt_path)
                    if run_cpk:
                        cpk = CPKAnalyzer(self.df, item)
                        res["cpk"] = cpk.compute(mt_path)
                    results[item] = res
                self._results   = results
                self._run_error = None
            except Exception as e:
                self._run_error = traceback.format_exc()
                self._results   = {}

            self.root.after(0, self._on_grr_cpk_done)

        threading.Thread(target=bg, daemon=True).start()

    def _on_grr_cpk_done(self):
        self.btn_run.config(state="normal")
        self.progress["value"] = 100
        if self._run_error:
            self._log(f"ERROR: {self._run_error}", "error")
            messagebox.showerror("Analysis Error", self._run_error)
            return

        results = self._results
        self._log("Analysis complete!", "ok")

        # ── Generate GRR Excel report ──
        grr_results = {k: v for k, v in results.items() if v.get("grr")}
        if grr_results and self.chk_grr.get():
            try:
                self._log(f"Generating GRR Excel report ({len(grr_results)} items)…")
                gen = ExcelReportGenerator(OUTPUT_DIR)
                grr_path = gen.generate(
                    grr_results, self.df,
                    minitab_path=self.minitab_path if self.chk_inline.get() else None,
                    inline_charts=self.chk_inline.get(),
                )
                self._log(f"GRR Report: {grr_path}", "ok")
            except Exception as e:
                self._log(f"GRR report error: {e}", "error")

        # ── Generate CPK Excel report ──
        cpk_results = {k: v for k, v in results.items() if v.get("cpk")}
        if cpk_results and self.chk_cpk.get():
            try:
                self._log(f"Generating CPK Excel report ({len(cpk_results)} items)…")
                gen = CPKExcelReportGenerator(OUTPUT_DIR)
                cpk_path = gen.generate(
                    cpk_results, self._get_cpk_raw_df(),
                    minitab_path=self.minitab_path if self.chk_inline.get() else None,
                    inline_charts=self.chk_inline.get(),
                )
                self._log(f"CPK Report: {cpk_path}", "ok")
                self.status_label.config(text=f"Done — {Path(cpk_path).name}")
            except Exception as e:
                self._log(f"CPK report error: {e}", "error")

        if grr_results or cpk_results:
            messagebox.showinfo("Done", "Report(s) generated successfully!")
        else:
            messagebox.showinfo("Done", "No reports to generate.")

    # ── AR&R ──────────────────────────────────

    def _run_arr(self):
        folder = filedialog.askdirectory(
            title="Select AR&R Jason Logs Folder", initialdir="C:/output"
        )
        if not folder:
            return

        # Show config dialog (simple input dialog)
        from ui.tkinter_arr_dialog import show_arr_config_dialog
        ok, config = show_arr_config_dialog(self.root, folder)
        if not ok:
            return

        self.btn_run.config(state="disabled")
        self._log(f"Parsing AR&R Jason logs: {folder}")
        self.progress["value"] = 20

        def bg():
            try:
                df_jason = arr_parse_json_folder(
                    folder,
                    appraiser_labels=config.get("inspector_numbers", []),
                )
                self.root.after(0, lambda: [
                    self._log(f"Parsed {len(df_jason)} records"),
                    self.progress.config(value=60)
                ])
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
                )
                self._arr_result = out_path
                self._arr_error  = None
            except Exception as e:
                self._arr_error  = traceback.format_exc()
                self._arr_result = None

            self.root.after(0, self._on_arr_done)

        threading.Thread(target=bg, daemon=True).start()

    def _get_cpk_raw_df(self):
        """Return the raw DataFrame to feed the CPK report's raw data sheet.

        1:1 copy of the Jason-log-derived raw data — no column aliasing,
        no numeric coercion, no Config injection.
        """
        if not getattr(self, "df_raw", None):
            return self.df
        sheet_name = self.sheet_combo.get() if hasattr(self, "sheet_combo") else None
        if not sheet_name and getattr(self, "sheet_names", None):
            sheet_name = self.sheet_names[0]
        df = self.df_raw.get(sheet_name) if sheet_name else None
        return df if df is not None else self.df

    def _on_arr_done(self):
        self.btn_run.config(state="normal")
        self.progress["value"] = 100
        if self._arr_error:
            self._log(f"AR&R ERROR: {self._arr_error}", "error")
            messagebox.showerror("AR&R Error", self._arr_error)
        else:
            self._log(f"AR&R Report: {self._arr_result}", "ok")
            self.status_label.config(text=f"Done — {Path(self._arr_result).name}")
            messagebox.showinfo("Done", "AR&R Report generated!\n\n" + self._arr_result)


def launch():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
