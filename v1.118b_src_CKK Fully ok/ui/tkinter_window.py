# ──────────────────────────────────────────────
#  Main Window  (tkinter backend)
#  Used when PyQt5 is not available (e.g. Linux servers)
# ──────────────────────────────────────────────
import logging
import os
import traceback
import threading
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
from report.report_generator import ReportGenerator
from utils.config import (
    APP_NAME, APP_VERSION, AUTHOR,
    LED_INTENSITY_COLS, OUTPUT_DIR, CPK_SPECS
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  Analysis Runner (runs in thread)
# ══════════════════════════════════════════════
def _run_analysis(df, selected_items, run_grr, run_cpk, minitab_path, result_holder, error_holder):
    results = {}
    try:
        for item in selected_items:
            res = {}
            if run_grr:
                grr = GRRAnalyzer(df, item)
                res["grr"] = grr.compute(minitab_path)
            if run_cpk:
                cpk = CPKAnalyzer(df, item)
                res["cpk"] = cpk.compute(minitab_path)
            results[item] = res
        result_holder["results"] = results
    except Exception as e:
        error_holder["error"] = traceback.format_exc()


# ══════════════════════════════════════════════
#  Main Window
# ══════════════════════════════════════════════
class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)

        self.df: Optional[object] = None
        self.df_raw: Optional[dict] = None
        self.sheet_names: List[str] = []
        self.available_items: List[str] = []
        self.minitab_path: Optional[str] = None

        self._build_ui()
        self._log("Welcome! Load a GRR/CPK Excel file to begin.", "info")

    # ── UI construction ────────────────────────

    def _build_ui(self):
        # ── Top header ──
        hdr = tk.Frame(self.root, bg="#1a2a6c", height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"🦞 {APP_NAME}", font=("Segoe UI", 16, "bold"),
                 fg="white", bg="#1a2a6c").pack(pady=(8, 2))
        tk.Label(hdr, text=f"GRR & CPK Analysis Tool  ·  {AUTHOR}  ·  {APP_VERSION}",
                 font=("Segoe UI", 9), fg="#aab4d4", bg="#1a2a6c").pack()

        # ── Main body ──
        body = tk.PanedWindow(self.root, orient="horizontal", sashrelief="raised", sashwidth=4)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # ── Left panel ──
        left = tk.Frame(body, width=300)
        body.add(left, stretch="never")

        # File loader
        frm_file = tk.LabelFrame(left, text="📂  Data File", font=("Segoe UI", 9, "bold"),
                                  padx=8, pady=6)
        frm_file.pack(fill="x", pady=(0, 8))

        btn_load = ttk.Button(frm_file, text="Load Excel File (.xlsx)", command=self._on_load_file)
        btn_load.pack(fill="x", pady=(0, 4))
        self.lbl_file = tk.Label(frm_file, text="No file loaded", fg="#546e7a", font=("Segoe UI", 8))
        self.lbl_file.pack()

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
                                    font=("Segoe UI", 9), height=15,
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
        ttk.Checkbutton(row1, text="Run GRR Analysis", variable=self.chk_grr,
                        command=self._check_at_least_one).pack(side="left", padx=(20, 10))
        ttk.Checkbutton(row1, text="Run CPK Analysis", variable=self.chk_cpk,
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
        self.log_text.tag_add(level, END)
        self.log_text.insert(END, f"[{ts}] {msg}\n")
        self.log_text.tag_config(level, foreground=color)
        self.log_text.see(END)
        logger.info(msg)

    # ── File loading ────────────────────────────

    def _on_load_file(self):
        path = filedialog.askopenfilename(
            title="Open GRR/CPK Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*")]
        )
        if not path:
            return
        try:
            self._log(f"Loading: {os.path.basename(path)}")
            self.loader     = DataLoader(path)
            self.df_raw    = self.loader.df_raw
            self.sheet_names = loader.sheet_names

            self.sheet_combo["values"] = self.sheet_names
            if len(self.sheet_names) == 1:
                self.sheet_combo.current(0)
                self._on_sheet_selected()
            else:
                self.sheet_combo.current(0)

            self.lbl_file.config(text=os.path.basename(path))
            self._log(f"Loaded {len(self.df_raw)} rows, {len(self.sheet_names)} sheet(s).", "ok")

        except Exception as e:
            self._log(f"Load error: {e}", "error")
            messagebox.showerror("Load Error", str(e))

    def _on_sheet_selected(self):
        sheet = self.sheet_combo.get()
        if not sheet or not self.df_raw:
            return
        try:
            # Use normalized df from loader (has LED_RED_D303_INTENSITY column names,
            # not raw PNUM-XXXX names from GRR template)
            df = self.loader.df
            cols = [c for c in df.columns if c in LED_INTENSITY_COLS]
            self.available_items = cols

            self.item_listbox.delete(0, END)
            for col in cols:
                self.item_listbox.insert(END, f"  {col}")
                # Alternate row color via tags
                idx = self.item_listbox.size() - 1
                tag = "even" if idx % 2 == 0 else "odd"
                self.item_listbox.itemconfig(idx, bg="#f5f5f5" if tag == "even" else "white")

            self.lbl_item_count.config(text=f"{len(cols)} LED items loaded")
            self._log(f"Sheet '{sheet}': {len(cols)} LED items available.", "ok")
        except Exception as e:
            self._log(f"Sheet error: {e}", "error")

    # ── Item selection ──────────────────────────

    def _select_all(self):
        self.item_listbox.select_set(0, END)

    def _select_none(self):
        self.item_listbox.select_clear(0, END)

    def _check_at_least_one(self):
        if not (self.chk_grr.get() or self.chk_cpk.get()):
            messagebox.showwarning("Selection", "Select at least one analysis type (GRR or CPK).")
            # Re-check both
            self.chk_grr.set(True)
            self.chk_cpk.set(True)

    # ── Minitab path ────────────────────────────

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

    # ── Run analysis ────────────────────────────

    def _on_run(self):
        if self.df is None:
            messagebox.showwarning("No Data", "Please load an Excel file first.")
            return

        selections = self.item_listbox.curselection()
        if not selections:
            messagebox.showwarning("No Items", "Select at least one test item.")
            return

        selected = [self.available_items[i] for i in selections]
        if not selected:
            return

        run_grr = self.chk_grr.get()
        run_cpk = self.chk_cpk.get()
        mt_path = self.minitab_path if self.chk_inline.get() else None

        self._log("=" * 50)
        self._log(f"Starting: {len(selected)} items  [GRR={run_grr}, CPK={run_cpk}]")

        self.btn_run.config(state="disabled")
        self.progress["value"] = 0

        # Run in background thread
        self._analysis_thread = threading.Thread(
            target=self._analysis_bg,
            args=(self.df, selected, run_grr, run_cpk, mt_path),
            daemon=True
        )
        self._analysis_thread.start()

        # Poll progress
        self.root.after(200, self._poll_progress)

    def _analysis_bg(self, df, selected, run_grr, run_cpk, mt_path):
        results = {}
        try:
            total = len(selected)
            for i, item in enumerate(selected):
                self.root.after(0, lambda pct=100*(i+1)/total, msg=f"Analyzing {item}…":
                    [self.progress.config(value=pct), self.status_label.config(text=msg)])
                self._log(f"Analyzing {item}…")
                res = {}
                if run_grr:
                    grr = GRRAnalyzer(df, item)
                    res["grr"] = grr.compute(mt_path)
                if run_cpk:
                    cpk = CPKAnalyzer(df, item)
                    res["cpk"] = cpk.compute(mt_path)
                results[item] = res
            self._analysis_results = results
            self._analysis_error   = None
        except Exception as e:
            self._analysis_error = traceback.format_exc()
            self._analysis_results = {}

    def _poll_progress(self):
        if hasattr(self, "_analysis_thread") and self._analysis_thread.is_alive():
            self.root.after(200, self._poll_progress)
        else:
            self._on_analysis_done()

    def _on_analysis_done(self):
        self.btn_run.config(state="normal")
        if self._analysis_error:
            self._log(f"ERROR: {self._analysis_error}", "error")
            messagebox.showerror("Analysis Error", self._analysis_error)
            return

        results = self._analysis_results
        self.progress["value"] = 100
        self._log("Analysis complete!", "ok")

        # Generate report
        try:
            self._log("Generating Word report…")
            mt_path = self.minitab_path if self.chk_inline.get() else None
            gen = ReportGenerator(OUTPUT_DIR)
            report_path = gen.generate(
                results, self.df,
                minitab_path=mt_path,
                inline_charts=self.chk_inline.get(),
            )
            self._log(f"Report saved: {report_path}", "ok")
            self.status_label.config(text=f"Done — {Path(report_path).name}")
            messagebox.showinfo(
                "Done",
                f"Report generated successfully!\n\n{report_path}"
            )
        except Exception as e:
            self._log(f"Report error: {e}", "error")
            messagebox.showerror("Report Error", str(e))

    # ── Drag & Drop ────────────────────────────

    def _on_drop(self, event):
        # Tkinter doesn't support drag-drop natively; use file dialog instead.
        pass


def launch():
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
