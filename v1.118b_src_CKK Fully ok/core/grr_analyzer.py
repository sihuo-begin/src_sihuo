# ──────────────────────────────────────────────
#  GRR Analyzer  –  AIAG (Average & Range) method
#
#  Model:
#    Total TV   = √(EV² + PV²)          (Total Variation)
#    EV         = Repeatability  = d₂·R̄ᵢ  (Equipment Variation)
#    PV         = Reproducibility= d₂·XP̄   (Part Variation)
#    GRR%       = 100 × TV / (TV + PV)   [%GRR of tolerance – NIST style]
#    P/T Ratio  = 6·TV / tolerance
#    NDC        = √(PV/EV) ≈ 1.41·(PV/R) – Number of Distinct Categories
#
#  GRR < 10%  → Excellent
#  10–30%    → Acceptable
#  > 30%     → Marginal / Unacceptable
# ──────────────────────────────────────────────
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from itertools import islice, cycle

from utils.config import grr_tolerance, CPK_SPECS, LED_MAPPING, _norm_led, GRR_OPS

logger = logging.getLogger(__name__)

# ── d₂ table (partial – most common values) ──
_D2 = {
    (2, 2): 1.128, (2, 3): 1.693, (2, 4): 2.059, (2, 5): 2.326,
    (2, 6): 2.534, (2, 7): 2.704, (2, 8): 2.847, (2, 9): 2.970,
    (2,10): 3.078,
    (3, 2): 1.693, (3, 3): 2.394, (3, 4): 2.772, (3, 5): 3.078,
    (3, 6): 3.258, (3, 7): 3.407, (3, 8): 3.532, (3, 9): 3.640,
    (3,10): 3.735,
}

def _d2(n, k):
    """d₂ for k repetitions, n operators / part groups."""
    return _D2.get((n, k), 1.0)   # fallback


class GRRResult:
    """Holds GRR computation results for one LED item."""
    def __init__(self, item: str):
        self.item = item
        self.ev    = None   # Equipment Variation
        self.pv    = None   # Part Variation
        self.tv    = None   # Total Variation
        self.grr_pct = None # %GRR
        self.pt_ratio = None # P/T ratio
        self.ndc  = None   # Number of Distinct Categories
        self.tolerance = None
        self.summary = ""   # Text summary
        self.chart_paths = {}  # {chart_type: file_path}

    def grade(self) -> str:
        if self.grr_pct is None:
            return "N/A"
        g = self.grr_pct
        if g < 10:
            return "Excellent ✅"
        if g < 30:
            return "Acceptable ⚠️"
        return "Marginal ❌"

    def to_dict(self) -> dict:
        return {
            "item": self.item,
            "EV": round(self.ev, 4) if self.ev else None,
            "PV": round(self.pv, 4) if self.pv else None,
            "TV": round(self.tv, 4) if self.tv else None,
            "GRR%": round(self.grr_pct, 2) if self.grr_pct else None,
            "P/T": round(self.pt_ratio, 4) if self.pt_ratio else None,
            "NDC": round(self.ndc, 1) if self.ndc else None,
            "tolerance": round(self.tolerance, 2) if self.tolerance else None,
            "grade": self.grade(),
            "summary": self.summary,
            "chart_paths": self.chart_paths,
        }


class GRRAnalyzer:
    """
    AIAG Average-and-Range GRR for one LED intensity column.

    Expects df to have:
      - 'sn'      : device serial number (part identifier)
      - 'QR_SCAN' : operator / appraiser identifier (optional)
      - <item>    : measurement value
    """

    # Factor d₂ for n=2 operators, k repetitions
    D2_2_2 = 1.128

    def __init__(self, df: pd.DataFrame, item: str):
        self.df    = df
        self.item  = item
        self.result = GRRResult(item)

    def _detect_cols(self, df: pd.DataFrame, col: str):
        """Detect sn/appraiser column names regardless of format."""
        # sn: prefer "part_num" (GRR part number, set by assign_trials) > "sn" > "Sample"
        # In intermediate Excel: sn=UNKNOWN (not useful), part_num=1..10 (correct for GRR)
        sn_candidates = [c for c in df.columns if c.lower() in ("sn", "sample", "part_num")]
        # Prefer part_num > sn > Sample (part_num is set by assign_trials for GRR)
        sn_col = None
        for candidate in ["part_num", "sn", "sample"]:
            for c in sn_candidates:
                if c.lower() == candidate:
                    sn_col = c
                    break
            if sn_col:
                break
        # Operator column: appraiser > inspector > qr_scan
        # appraiser = operator ID from MT7 QR_SCAN result (intermediate Excel)
        # inspector = GRR template format
        # qr_scan = raw MT7 QR_SCAN field (not ideal for GRR)
        op_candidates = [c for c in df.columns if c.lower() in ("appraiser", "inspector", "qr_scan", "operator")]
        op_col = op_candidates[0] if op_candidates else None
        return sn_col, op_col

    def compute(self, minitab_path: str = None) -> GRRResult:
        # Resolve actual column name in df (item may be bare LED name or PNUM)
        item = self.item
        if item in self.df.columns:
            col = item
        elif _norm_led(item) in self.df.columns:
            col = _norm_led(item)
        else:
            # Try PNUM reverse lookup
            col = None
            for pnum, led in LED_MAPPING.items():
                if led == item and pnum in self.df.columns:
                    col = pnum
                    break
            if col is None:
                logger.warning("Column for item '%s' not found in df. Available: %s", item, list(self.df.columns))
                return self.result

        sn_col, op_col = self._detect_cols(self.df, col)
        if sn_col is None:
            logger.warning("No sn/Part column found for col=%s. Available cols: %s", col, list(self.df.columns))
            return self.result

        # Build keep_cols — always include sn_col, op_col, and the LED measurement col
        if op_col:
            keep_cols = [sn_col, op_col, col]
        else:
            keep_cols = [sn_col, col]

        logger.info("compute: item=%s col=%s sn_col=%s op_col=%s keep_cols=%s df_rows=%d",
                     item, col, sn_col, op_col, keep_cols, len(self.df))

        df = self.df[keep_cols].copy()
        df["part"]       = df[sn_col].astype(str).str.strip()
        df["appraiser"]  = df[op_col].astype(str).str.strip() if op_col else "A"
        df[col]           = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=[col], inplace=True)

        logger.info("compute: after dropna rows=%d unique_parts=%s",
                     len(df), df["part"].unique().tolist() if len(df) > 0 else "N/A")

        n_parts     = df["part"].nunique()
        n_appraisers = df["appraiser"].nunique()
        n_reps      = max(df.groupby(["part", "appraiser"]).size().max(), 2)

        logger.info(f"GRR {col}: {n_parts} parts × {n_appraisers} appraisers × {n_reps} reps")

        # ── Average & Range per appraiser ──
        X_bar = df.groupby("appraiser")[col].mean()          # X̄ per appraiser
        R_i   = df.groupby("appraiser")[col].apply(
            lambda x: x.max() - x.min()
        )                                                       # Range per appraiser
        X_bar_bar = X_bar.mean()                               # grand mean

        # ── Equipment Variation (EV) ──
        R_bar_i = R_i.mean()                                   # average range
        EV = _d2(2, n_reps) * R_bar_i / 1.128 * self.D2_2_2
        EV = _d2(2, 2) * R_i.mean()                           # simplified: d₂(2,2)=1.128

        # ── Part Variation (PV) ──
        X_p_bar = df.groupby("part")[col].mean()
        R_p     = X_p_bar.max() - X_p_bar.min()
        PV = _d2(2, 2) * R_p

        # ── Total Variation ──
        TV = np.sqrt(EV**2 + PV**2) if (EV and PV) else (EV or PV or 0)

        # ── Tolerance (USL – LSL) ──
        lo, hi = CPK_SPECS.get(col, (None, None))
        if lo is None or hi is None:
            # Fall back to 20% of mean
            tol = X_bar_bar * 0.20
        else:
            tol = hi - lo
        tolerance = tol

        # ── GRR metrics ──
        grr_pct   = 100 * TV / tolerance if tolerance else None
        pt_ratio  = 6  * TV / tolerance if tolerance else None
        ndc       = 1.41 * PV / EV if (PV and EV) else None

        self.result.ev          = float(EV)  if EV  else None
        self.result.pv          = float(PV)  if PV  else None
        self.result.tv          = float(TV)  if TV  else None
        self.result.grr_pct     = float(grr_pct) if grr_pct else None
        self.result.pt_ratio    = float(pt_ratio) if pt_ratio else None
        self.result.ndc         = float(ndc)  if ndc else None
        self.result.tolerance   = float(tolerance)
        self.result.summary = (
            f"GRR% = {round(grr_pct,2) if grr_pct else 'N/A'}%  |  "
            f"P/T = {round(pt_ratio,4) if pt_ratio else 'N/A'}  |  "
            f"NDC = {round(ndc,1) if ndc else 'N/A'}  |  "
            f"Grade: {self.result.grade()}"
        )

        logger.info(f"GRR {col}: {self.result.summary}")

        # ── Minitab charts ──
        if minitab_path and os.path.isfile(minitab_path):
            self.result.chart_paths = self._run_minitab(minitab_path, df, col)

        return self.result

    def _run_minitab(self, mtb_path: str, df: pd.DataFrame, col: str) -> dict:
        """
        Generate GRR chart via Minitab using SET (no CSV files).
        Uses GageRR command with numeric Part/Operator columns.
        """
        import subprocess as _sub
        import time as _time
        out_dir = Path.home() / "grr_charts"
        out_dir.mkdir(exist_ok=True)
        ts = int(_time.time() * 1000)
        mtb_file = out_dir / "grr_{}_{}.mtb".format(col.replace("/", "_"), ts)

        # Kill existing Minitab
        for attempt in range(4):
            try:
                _sub.run(["taskkill", "/F", "/IM", "Mtb.exe"],
                         capture_output=True, timeout=5)
            except Exception:
                pass
            try:
                mtb_file.write_text("", encoding="utf-8")
                break
            except (PermissionError, OSError):
                if attempt < 3: _time.sleep(0.5)
                else: raise

        # ── Build GRR data from dataframe ──────────────────────────────────
        # Part column: encode as 1, 2, 3, ... (deduplicate)
        sn_col, op_col = self._detect_cols(df, col)
        df_work = df.copy()
        if sn_col:
            df_work["part_str"] = df_work[sn_col].astype(str).str.strip()
        else:
            df_work["part_str"] = df_work.index.astype(str)
        if op_col:
            df_work["op_str"] = df_work[op_col].astype(str).str.strip()
        else:
            df_work["op_str"] = "1"
        # Filter invalid rows BEFORE computing unique_ops/unique_parts
        # (removes "Parameter" / nan / empty rows from GRR From sheet)
        df_work = df_work.dropna(subset=["part_str", "op_str"])
        df_work = df_work[df_work["op_str"].str.lower().isin(["nan", "none", "parameter", ""]) == False]
        df_work = df_work[df_work["part_str"].str.lower().isin(["nan", "none", ""]) == False]
        unique_ops  = df_work["op_str"].unique().tolist()
        unique_parts = df_work["part_str"].unique().tolist()
        if len(unique_ops) == 0:
            logger.warning("_run_minitab: no operators in data, skipping")
            return {}
        logger.info("_run_minitab: unique_ops=%s n_parts=%d n_rows=%d",
                     unique_ops, len(unique_parts), len(df_work))

        # LED col
        led_col = col if col in df_work.columns else col.replace("_INTENSITY", "")
        if led_col not in df_work.columns:
            logger.warning("_run_minitab: LED col '%s' not found, skipping", led_col)
            return {}
        df_work = df_work.dropna(subset=[led_col])

        # Build SET C1/C2 via direct cycling (uses FILTERED unique_ops)
        n_parts = len(unique_parts)
        n_ops   = len(unique_ops)
        n_reps  = max(len(df_work) // (n_parts * n_ops), 1) if n_parts and n_ops else 1
        n_rows  = n_parts * n_ops * n_reps
        # C1: each part 1..n_parts repeated n_reps times, for n_ops blocks
        # Pattern per trial: 1..n_parts, repeated n_reps times, for n_ops operators
        # e.g. 1..10 ×3trials ×3ops = 90 rows (10 values per row × 9 rows)
        part_pattern = list(range(1, n_parts + 1)) * n_reps  # [1..10] × 3 = 30 vals
        c1_vals = list(islice(cycle(part_pattern), n_rows))
        op_pattern = [GRR_OPS[i % len(GRR_OPS)] for i in range(n_ops) for _ in range(n_parts * n_reps)]
        c2_vals = list(islice(cycle(op_pattern), n_rows))
        df_sorted = df_work.sort_values(by=["op_str", "part_str"])
        c3_vals = [int(v) for v in df_sorted[led_col].tolist()[:n_rows]]

        # Build SET blocks with ~10 values per line
        def fmt_row(vals, width=10, quote=False):
            rows = []
            for i in range(0, len(vals), width):
                row_vals = vals[i:i+width]
                if quote:
                    # Quote values containing spaces (operator IDs like "TN5S 6C0 NYT E21Q")
                    row_vals = [repr(str(v)) if " " in str(v) else str(v) for v in row_vals]
                rows.append(" ".join(str(v) for v in row_vals))
            return rows

        c1_rows = fmt_row(c1_vals)
        c2_rows = fmt_row(c2_vals, quote=True)   # quote operator IDs with spaces
        c3_rows = fmt_row(c3_vals)

        # Save chart paths
        grr_img = str(out_dir / "grr_{}.png".format(col.replace("/", "_")))
        xbc_img = str(out_dir / "grr_{}_xbar.png".format(col.replace("/", "_")))
        r_img   = str(out_dir / "grr_{}_r.png".format(col.replace("/", "_")))

        lines = (
            [
                "NAME C1 'Part'",
                "NAME C2 'Operator'",
                "NAME C3 'Measurement'",
            ]
            + ["SET C1"]
            + c1_rows + ["END.", ""]
            + ["SET C2"]
            + c2_rows + ["END.", ""]
            + ["SET C3"]
            + c3_rows + ["END.", ""]
            + [
                "",
                # GageRR main chart → save
                "LAYOUT",
                "GageRR;",
                "  Parts {};".format(len(unique_parts)),
                "  Opers {};".format(len(unique_ops)),
                "  Response C3;",
                "  Studyvar 6;",
                "  LSL 0;",
                "  USL 65555;",
                "  Risk;",
                "ENDLAYOUT",
                'GSAVE \'{}\' ;'.format(grr_img),
                "PNG;",
                "",
                # Xbar chart → save
                "LAYOUT",
                "XBARCHART C3 C1 C2",
                "ENDLAYOUT",
                'GSAVE \'{}\' ;'.format(xbc_img),
                "PNG;",
                "",
                "",
                # R chart → save
                "LAYOUT",
                "RCHART C3 C1 C2",
                "ENDLAYOUT",
                'GSAVE \'{}\' ;'.format(r_img),
                "PNG;",
            ]
        )

        mtb_file.write_text(chr(10).join(lines), encoding="latin1")
        logger.info("GRR MTB written: %s", mtb_file)
        logger.info("GRR MTB preview:\n%s", "\n".join(lines)[:400])

        chart_files = [grr_img, xbc_img, r_img]
        import time as _mt
        _t0 = _mt.time()
        try:
            r = _sub.run(
                [mtb_path, str(mtb_file)],
                timeout=30
            )
            _elapsed = _mt.time() - _t0
            logger.info("Minitab started (%.1fs), polling for %d GRR chart files…", _elapsed, len(chart_files))
            for _polling in range(60):   # up to 5 min
                if all(Path(f).exists() for f in chart_files):
                    break
                _time.sleep(5.0)
            _elapsed2 = _mt.time() - _t0
            for img_path in chart_files:
                if Path(img_path).exists():
                    paths[Path(img_path).stem] = img_path
            logger.info("GRR charts ready: %d/%d in %.1fs", len(paths), len(chart_files), _elapsed2)
            if r.returncode != 0:
                logger.warning("Minitab exit code %s: %s", r.returncode, (r.stderr or b"")[:200])
        except Exception as e:
            logger.warning("Minitab GRR chart failed: %s", e)

        return paths



    @staticmethod
    def _detect_cols_static(df: pd.DataFrame, col: str):
        """
        Detect part-number and operator column names from the GRR DataFrame.

        Priority (first match wins, scanning in priority order):
          Part column:
            'part_num'  → numeric 1-11 from assign_trials (intermediate Excel)
            'sample'    → GRR template (1-10)
            'sn'        → device serial (MT7 raw log, fallback only)
          Operator column:
            'appraiser' → intermediate Excel / MT7 QR_SCAN result
            'inspector' → GRR template
            'qr_scan'   → MT7 raw QR_SCAN field
        """
        # Part column: part_num > sample > sn
        sn_col = None
        for candidate in ["part_num", "sample", "sn"]:
            for c in df.columns:
                if c.lower() == candidate:
                    sn_col = c
                    break
            if sn_col:
                break

        # Operator column: appraiser > inspector > qr_scan
        op_col = None
        for candidate in ["appraiser", "inspector", "qr_scan"]:
            for c in df.columns:
                if c.lower() == candidate:
                    op_col = c
                    break
            if op_col:
                break

        return sn_col, op_col

    @staticmethod
    def run_all_minitab(df: pd.DataFrame, items: list, minitab_path: str) -> dict:
        """
        Run GRR GageRR for all items in ONE Minitab session.
        Each item uses its own column group (C1-C3, C4-C6, C7-C9, ...).
        GageRR uses column numbers, not names.
        """
        import subprocess as _sub
        import time as _time
        out_dir = Path.home() / "grr_charts"
        out_dir.mkdir(exist_ok=True)
        ts = int(_time.time() * 1000)
        mtb_file = out_dir / "grr_batch_{}.mtb".format(ts)

        # Kill existing Minitab
        try:
            _sub.run(["taskkill", "/F", "/IM", "Mtb.exe"],
                     capture_output=True, timeout=5)
        except Exception:
            pass
        _time.sleep(0.3)

        all_lines = []

        for idx, item in enumerate(items):
            norm = _norm_led(item)
            if norm not in df.columns:
                continue

            # Column numbers for this item (1-based)
            c_part  = idx * 3 + 1   # C1, C4, C7, C10...
            c_op    = idx * 3 + 2   # C2, C5, C8, C11...
            c_meas  = idx * 3 + 3   # C3, C6, C9, C12...

            # Build data
            sn_col, op_col = GRRAnalyzer._detect_cols_static(df, norm)
            logger.info("run_all_minitab[%s]: df=%s, norm=%s, sn_col=%s, op_col=%s",
                        item, df.shape, norm, sn_col, op_col)
            logger.info("  df cols: %s", list(df.columns))
            logger.info("  df sn sample: %s", df[sn_col].head(3).tolist() if sn_col else "N/A")
            logger.info("  df op sample: %s", df[op_col].head(3).tolist() if op_col else "N/A")
            logger.info("  df LED sample: %s",
                        df[norm].head(3).tolist() if norm in df.columns
                        else df.get(norm.replace("_INTENSITY",""), pd.Series()).head(3).tolist())
            df_w = df.copy()
            df_w["part_str"] = (df_w[sn_col].astype(str).str.strip()
                               if sn_col else df_w.index.astype(str))
            df_w["op_str"]  = (df_w[op_col].astype(str).str.strip()
                               if op_col else "1")
            # Filter invalid rows BEFORE computing unique lists (removes "Parameter" etc.)
            df_w = df_w.dropna(subset=["part_str", "op_str"])
            df_w = df_w[df_w["op_str"].str.lower().isin(["nan", "none", "parameter", ""]) == False]
            df_w = df_w[df_w["part_str"].str.lower().isin(["nan", "none", ""]) == False]
            unique_ops  = df_w["op_str"].unique().tolist()
            unique_parts = df_w["part_str"].unique().tolist()
            if len(unique_ops) == 0:
                logger.warning("run_all_minitab: no operators in data, skipping '%s'", item)
                continue
            logger.info("run_all_minitab: unique_ops=%s n_parts=%d n_rows=%d",
                         unique_ops, len(unique_parts), len(df_w))

            # LED col
            led_col = norm if norm in df_w.columns else norm.replace("_INTENSITY", "")
            if led_col not in df_w.columns:
                bare = item.replace("_INTENSITY", "")
                led_col = bare if bare in df_w.columns else norm
            if led_col not in df_w.columns:
                continue
            df_w = df_w.dropna(subset=[led_col])
            if len(df_w) == 0:
                continue

            # Build SET C1/C2 via direct cycling (uses FILTERED unique_ops)
            n_parts = len(unique_parts)
            n_ops   = len(unique_ops)
            n_reps  = max(len(df_w) // (n_parts * n_ops), 1) if n_parts and n_ops else 1
            n_rows  = n_parts * n_ops * n_reps
            # C1: each part 1..n_parts repeated n_reps times, for n_ops blocks
            part_pattern = list(range(1, n_parts + 1)) * n_reps
            c1 = list(islice(cycle(part_pattern), n_rows))
            op_pattern = [GRR_OPS[i % len(GRR_OPS)] for i in range(n_ops) for _ in range(n_parts * n_reps)]
            c2 = list(islice(cycle(op_pattern), n_rows))
            df_sorted = df_w.sort_values(by=["op_str", "part_str"])
            c3 = [int(v) for v in df_sorted[led_col].tolist()[:n_rows]]
            logger.info("run_all_minitab[%s]: c1=%s, c2=%s, c3=%s (len=%d)",
                        item,
                        c1[:5] if c1 else [],
                        c2[:5] if c2 else [],
                        c3[:5] if c3 else [],
                        len(c3) if c3 else 0)

            def fmt(vals, w=10, quote=False):
                rows = []
                for i in range(0, len(vals), w):
                    row_vals = vals[i:i+w]
                    if quote:
                        row_vals = [repr(str(v)) if " " in str(v) else str(v) for v in row_vals]
                    rows.append(" ".join(str(v) for v in row_vals))
                return rows

            safe = item.replace("/", "_")
            grr_png = str(out_dir / "grr_{}.png".format(safe)).replace('\\', '/')

            # Column names for NAME statements (short names, like _run_minitab)
            block = (
                ["NAME C{} 'Part'".format(c_part),
                 "NAME C{} 'Operator'".format(c_op),
                 "NAME C{} 'Measurement'".format(c_meas),
                 ""]
                + ["SET C{}".format(c_part)] + fmt(c1) + ["END.", ""]
                + ["SET C{}".format(c_op)]   + fmt(c2, quote=True) + ["END.", ""]
                + ["SET C{}".format(c_meas)] + fmt(c3) + ["END.", ""]
                + [
                    "",
                    "LAYOUT",
                    "GageRR;",
                    "  Parts {};".format(len(unique_parts)),
                    "  Opers {};".format(len(unique_ops)),
                    "  Response C{};".format(c_meas),
                    "  Studyvar 6;",
                    "  LSL 0;",
                    "  USL 65555;",
                    "  Risk;",
                    "ENDLAYOUT",
                    'GSAVE \'{}\' ;'.format(grr_png),
                    "PNG;",
                ]
            )
            all_lines.extend(block)
            all_lines.append("")

        mtb_content = chr(10).join(all_lines)
        mtb_file.write_text(mtb_content, encoding="latin1")
        logger.info("GRR batch MTB written: %s", mtb_file)
        logger.info("GRR MTB preview:\n%s", mtb_content[:600])

        paths = {}
        import time as _mt
        _t0 = _mt.time()
        chart_files = [str(out_dir / "grr_{}.png".format(item.replace("/", "_"))) for item in items]
        try:
            r = _sub.run(
                [minitab_path, str(mtb_file)],
                timeout=30
            )
            _elapsed = _mt.time() - _t0
            logger.info("Minitab started (%.1fs), polling for %d GRR chart files…", _elapsed, len(chart_files))
            for _polling in range(120):   # up to 10 min total
                if all(Path(f).exists() for f in chart_files):
                    break
                _time.sleep(5.0)
            _elapsed2 = _mt.time() - _t0
            for item in items:
                safe = item.replace("/", "_")
                p = str(out_dir / "grr_{}.png".format(safe))
                if Path(p).exists():
                    paths[safe] = p
            logger.info("GRR charts ready: %d/%d in %.1fs", len(paths), len(chart_files), _elapsed2)
            if r.returncode != 0:
                logger.warning("Minitab stderr: %s", (r.stderr or b"")[:300])
        except Exception as e:
            logger.warning("Minitab GRR batch failed: %s", e)

        return paths

