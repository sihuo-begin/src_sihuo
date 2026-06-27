# ──────────────────────────────────────────────
#  CPK Analyzer  –  Process Capability
#
#  USL / LSL  → from CPK_SPECS in config
#  Cp   = (USL – LSL) / (6·σ_within)
#  Cpl  = (Mean – LSL) / (3·σ_within)
#  Cpu  = (USL – Mean) / (3·σ_within)
#  Cpk  = min(Cpl, Cpu)
#  Pp / Ppk  → using overall σ (within + between)
#
#  CPK ≥ 2.0  → World-class
#  CPK ≥ 1.67 → Excellent
#  CPK ≥ 1.33 → Minimum acceptable
#  CPK < 1.00 → Poor
# ──────────────────────────────────────────────
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from utils.config import CPK_SPECS
import easyocr
import cv2
import re
reader = easyocr.Reader(['en'], gpu=False)

logger = logging.getLogger(__name__)


class CPKResult:
    """Holds CPK computation results for one measurement item."""
    def __init__(self, item: str):
        self.item  = item
        self.mean  = None
        self.std   = None
        self.std_w = None
        self.lsl   = None
        self.usl   = None
        self.cp    = None
        self.cpl   = None
        self.cpu   = None
        self.cpk   = None
        self.pp    = None
        self.ppk   = None
        self.pct_outside_lsl = None
        self.pct_outside_usl = None
        self.pct_total       = None
        self.summary  = ""
        self.chart_paths = {}

    def grade(self) -> str:
        v = self.cpk or self.ppk
        if v is None:
            return "N/A"
        if v >= 2.0: return "World-class 🌟"
        if v >= 1.67: return "Excellent ✅"
        if v >= 1.33: return "Good ✅"
        if v >= 1.00: return "Acceptable ⚠️"
        return "Poor ❌"

    def to_dict(self) -> dict:
        return {
            "item":     self.item,
            "Mean":     round(self.mean, 2) if self.mean else None,
            "Std(w)":   round(self.std_w, 2) if self.std_w else None,
            "Std(o)":   round(self.std, 2) if self.std else None,
            "LSL":      round(self.lsl, 2) if self.lsl else None,
            "USL":      round(self.usl, 2) if self.usl else None,
            "Cp":       round(self.cp, 3) if self.cp else None,
            "Cpk":      round(self.cpk, 3) if self.cpk else None,
            "Pp":       round(self.pp, 3) if self.pp else None,
            "Ppk":      round(self.ppk, 3) if self.ppk else None,
            "Out%":     round(self.pct_total, 4) if self.pct_total else None,
            "Grade":    self.grade(),
            "summary":  self.summary,
            "chart_paths": self.chart_paths,
        }


class CPKAnalyzer:
    def __init__(self, df: pd.DataFrame, item: str):
        self.df     = df
        self.item   = item
        self.result = CPKResult(item)

    def compute(self, minitab_path: str = None, minitab_path_set=False, chart_path = {}) -> CPKResult:
        col = self.item
        data = pd.to_numeric(self.df[col], errors="coerce").dropna()
        if len(data) < 2:
            logger.warning(f"Insufficient data for {col}: {len(data)} points")
            return self.result

        specs = CPK_SPECS.get(col, None)
        if specs:
            lsl, usl = specs
        else:
            # Try reading LSL/USL from dataframe columns (populated by json_parser from JSON)
            import math as _math
            _lsl = self.df[f"{col}_lsl"].dropna().iloc[0] if f"{col}_lsl" in self.df.columns and len(self.df[f"{col}_lsl"].dropna()) > 0 else None
            _usl = self.df[f"{col}_usl"].dropna().iloc[0] if f"{col}_usl" in self.df.columns and len(self.df[f"{col}_usl"].dropna()) > 0 else None
            try:
                lsl = float(_lsl) if _lsl is not None else None
                if _math.isnan(lsl): lsl = None
            except (ValueError, TypeError):
                lsl = None
            try:
                usl = float(_usl) if _usl is not None else None
                if _math.isnan(usl): usl = None
            except (ValueError, TypeError):
                usl = None

        mean = float(data.mean())
        std_overall = float(data.std(ddof=1))
        std_within  = float(self._within_std(data))
        # logger.info("simon std_overall is {} std_within is {}".format(std_overall, std_within))

        self.result.mean  = mean
        self.result.std   = std_overall
        self.result.std_w = std_within
        self.result.usl   = usl
        self.result.lsl   = lsl
        # Only compute CPK if both lsl and usl are valid
        has_specs = (lsl is not None) and (usl is not None) and std_within
        cp   = (usl - lsl) / (6 * std_within) if has_specs else None
        cpl  = (mean - lsl) / (3 * std_within) if has_specs else None
        cpu  = (usl - mean) / (3 * std_within) if has_specs else None
        cpk  = min(cpl, cpu) if (cpl and cpu) else None
        # logger.info("simon CPK data \n {} {} {} {} {} {} ".format(cp, cpl, cpu, cpk, std_within, std_overall))

        has_pp = (lsl is not None) and (usl is not None) and std_overall
        pp    = (usl - lsl) / (6 * std_overall) if has_pp else None
        ppk_l = (mean - lsl) / (3 * std_overall) if has_pp else None
        ppk_u = (usl - mean) / (3 * std_overall) if has_pp else None
        ppk   = min(ppk_l, ppk_u) if (ppk_l and ppk_u) else None
        # logger.info("simon CPK data \n {} {} {} {} {} {} ".format(pp, ppk_l, ppk_u, ppk, std_within, std_overall))
        self.result.cp   = cp
        self.result.cpl  = cpl
        self.result.cpu  = cpu
        self.result.cpk  = cpk
        self.result.pp   = pp
        self.result.ppk  = ppk
            # if minitab_path and os.path.isfile(minitab_path):
            #     self.result.chart_paths = self._run_minitab(minitab_path, data, lsl, usl, col)
        if minitab_path_set:
            try:
                self.result.cpk  = float(self.fast_extract_cpk(path=chart_path['capability']))
            except Exception as e:
                error_cpk = self.fast_extract_cpk(path=chart_path['capability'])
                cpk_str=''
                for i in error_cpk:
                    if i != ",":
                        cpk_str= cpk_str + i
                self.result.cpk = float(cpk_str)
            cpk = self.result.cpk
        n = len(data)
        n_lo = float((data < lsl).sum())
        n_hi = float((data > usl).sum())
        self.result.pct_outside_lsl = 100 * n_lo / n
        self.result.pct_outside_usl = 100 * n_hi / n
        self.result.pct_total        = 100 * (n_lo + n_hi) / n

        self.result.summary = (
            f"Cpk={round(cpk,2) if cpk else 'N/A'}  |  "
            # f"Cpk_minitab={round(self.result.cpk,2) if self.result.cpk else 'N/A'}  |  "
            f"Ppk={round(ppk,2) if ppk else 'N/A'}  |  "
            f"Mean={round(mean,1)}  |  "
            f"σ(within)={round(std_within,1)}  |  "
            f"Out_of_spec={round(self.result.pct_total,3)}%  |  "
            f"Grade: {self.result.grade()}"
        )
        logger.info(f"CPK {col}: {self.result.summary}")


        logger.info("results is {}".format(self.result))
        return self.result

    def fast_extract_cpk(self, path):
        img = cv2.imread(path)

        h, w = img.shape[:2]
        print(h, w)
        # ✅ 裁剪右上角
        roi = img[0:int(h * 0.7), int(w * 0.6):w]

        # ✅ 降采样
        # roi = cv2.resize(roi, None, fx=0.6, fy=0.6)

        # ✅ 灰度
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # ✅ OCR
        results = reader.readtext(
            gray,
            # detail=0,
            # allowlist='Cpk0123456789.'
        )
        print(results)
        len_item = len(results)
        for key in range(len_item):
            # print(key)
            # print(result[key])
            # print(len(result[key]))
            if "Cpk" in results[key]:
                cpk = results[key + 1][1]
                print("cpk is {}".format(cpk))
                break
        return cpk

    def _within_std(self, data):
        import numpy as np

        data = np.asarray(data)

        if len(data) < 2:
            return 0.0

        # 🚨 关键1：必须保持原始顺序（不要排序）
        # data = np.sort(data) ❌ 禁止！

        # ✅ Moving Range
        mr = np.abs(np.diff(data))

        # 🚨 关键2：去掉 NaN
        mr = mr[~np.isnan(mr)]

        if len(mr) == 0:
            return 0.0

        mr_bar = np.mean(mr)

        # ✅ d2 常数（n=2）
        d2 = 1.128

        return mr_bar / d2
    # def _within_std(self, data: pd.Series) -> float:
    #
    #     return data.std(ddof=1)

    # ── Single-item Minitab ─────────────────────────────────────────────────

    def _run_minitab(self, mtb_path: str, data: pd.Series,
                     lsl: float, usl: float, col: str) -> dict:
        import time as _time
        out_dir = Path.home() / "cpk_charts"
        out_dir.mkdir(exist_ok=True)
        ts = int(_time.time() * 1000)
        mtb_file = out_dir / "cpk_{}_{}.mtb".format(col.replace('_', ''), ts)

        # Kill existing Minitab
        for attempt in range(4):
            try:
                subprocess.run(["taskkill", "/F", "/IM", "Mtb.exe"],
                               capture_output=True, timeout=5)
            except Exception:
                pass
            try:
                mtb_file.write_bytes(b"")
                break
            except (PermissionError, OSError):
                if attempt < 3: _time.sleep(0.5)
                else: raise

        # Build SET block, ~12 per line
        vals = [str(int(v)) for v in data.values]
        rows = [" ".join(vals[i:i+12]) for i in range(0, len(vals), 12)]
        set_block = ["SET C1"] + rows + ["END."]

        # Build full MTB (no CSV, no READ - pure inline data)
        gsave = str(out_dir / "cpk_{}.jpg".format(col.replace('_', '')))
        capa_lines = [
            "CAPA C1 5;",
            "  LSPEC {:g};".format(lsl),
            "  USPEC {:g};".format(usl),
            "  POOLED;",
            "  AMR;",
            "  UNBIASED;",
            "  OBIASED;",
            "  TOLER 6;",
            "  WITHIN;",
            "  OVERALL;",
            "  NOCI;",
            "  PPM;",
            '  GSAVE "{}";'.format(gsave),
            "  OVERALL.",
        ]
        lines = [
            'NAME C1 "{}"'.format(col),
        ] + set_block + [""] + capa_lines
        mtb_file.write_text("\n".join(lines), encoding="latin1")
        logger.info("MTB written: %s", mtb_file)
        logger.info("MTB preview:\n%s", "\n".join(lines)[:300])

        try:
            r = subprocess.run(
                [mtb_path, str(mtb_file)],
                timeout=30
            )
            _time.sleep(0.5)
            if r.returncode != 0:
                logger.warning("Minitab exit code %s: %s", r.returncode, r.stderr[:100])
        except Exception as e:
            logger.warning("Minitab run failed: %s", e)

        # Return {item: chart_path} for each item
        return {item: str(out_dir / "cpk_{}.jpg".format(item.replace('_', '')))
                for item in items}

    @staticmethod
    def run_all_minitab(df: pd.DataFrame, items: list,
                         minitab_path: str) -> dict:
        """
        Build one MTB with per-item SET blocks (no CSV files),
        then call Mtb.exe directly.
        """
        import time as _time
        out_dir = Path.home() / "cpk_charts"
        out_dir.mkdir(exist_ok=True)
        ts = int(_time.time() * 1000)
        mtb_file = out_dir / "cpk_batch_{}.mtb".format(ts)

        # Kill existing Minitab
        try:
            subprocess.run(["taskkill", "/F", "/IM", "Mtb.exe"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
        _time.sleep(1.0)

        # Build SET-based CAPA blocks (no CSV, no READ)
        capa_blocks = []
        for item in items:
            data = pd.to_numeric(df[item], errors="coerce").dropna()
            specs = CPK_SPECS.get(item, None)
            if specs:
                lsl, usl = specs
            else:
                # Try reading from df columns (populated by json_parser from JSON)
                lsl_col_name = f"{item}_lsl"
                usl_col_name = f"{item}_usl"
                lsl = float(df[lsl_col_name].dropna().iloc[0])                     if lsl_col_name in df.columns and len(df[lsl_col_name].dropna()) > 0 else None
                usl = float(df[usl_col_name].dropna().iloc[0])                     if usl_col_name in df.columns and len(df[usl_col_name].dropna()) > 0 else None

            vals = [str(float(v)) for v in data.values]  # keep decimal values
            rows = [" ".join(vals[i:i+12]) for i in range(0, len(vals), 12)]
            set_block = ["SET C1"] + rows + ["END."]

            gsave = str(out_dir / "cpk_{}.jpg".format(item.replace('_', '')))
            capa_lines = ["CAPA C1 5;"]
            if lsl is not None:
                capa_lines.append("  LSPEC {:g};".format(lsl))
            if usl is not None:
                capa_lines.append("  USPEC {:g};".format(usl))
            capa_lines += [
                "  POOLED;",
                "  AMR;",
                "  UNBIASED;",
                "  OBIASED;",
                "  TOLER 6;",
                "  WITHIN;",
                "  NOCI;",
                "  PPM;",
                '  GSAVE "{}";'.format(gsave),
                "  OVERALL.",
            ]
            block_lines = [
                'NAME C1 "{}"'.format(item),
            ] + set_block + [""] + capa_lines
            capa_blocks.append("\n".join(block_lines))

        mtb_content = "\n\n".join(capa_blocks)
        mtb_file.write_text(mtb_content, encoding="latin1")
        logger.info("MTB written: %s", mtb_file)
        logger.info("MTB preview:\n%s", mtb_content[:400])

        import time as _mt
        _t0 = _mt.time()
        chart_files = [str(out_dir / "cpk_{}.jpg".format(it.replace('_', ''))) for it in items]
        try:
            # No capture_output=True: Minitab is a GUI app; we rely on polling
            # chart files instead of waiting for stdout/stderr
            r = subprocess.run(
                [minitab_path, str(mtb_file)],
                timeout=30
            )
            _elapsed = _mt.time() - _t0
            logger.info("Minitab started (%.1fs), polling for %d chart files…", _elapsed, len(chart_files))
            # Poll until all chart files exist (Minitab renders after exit)
            for _polling in range(120):   # up to 10 min total
                if all(Path(f).exists() for f in chart_files):
                    break
                _time.sleep(5.0)
            _elapsed2 = _mt.time() - _t0
            found = sum(1 for f in chart_files if Path(f).exists())
            logger.info("CPK charts ready: %d/%d in %.1fs", found, len(chart_files), _elapsed2)
            if r.returncode != 0:
                logger.warning("Minitab exit code: %s stderr: %s", r.returncode, (r.stderr or b"")[:200])
        except Exception as e:
            logger.warning("Minitab run failed: %s", e)

        # Return {item: chart_path} for each item
        return {item: str(out_dir / "cpk_{}.jpg".format(item.replace('_', '')))
                for item in items}

