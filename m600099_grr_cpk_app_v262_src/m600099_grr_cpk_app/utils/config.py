# ──────────────────────────────────────────────
#  Application Configuration
# ──────────────────────────────────────────────
from pathlib import Path

APP_NAME    = "M600099 GRR & CPK Analyzer"
APP_VERSION = "2.0.6"
AUTHOR      = "simon's claw 🦞"

# File locations
BASE_DIR      = Path(__file__).parent.resolve()
DATA_DIR      = BASE_DIR / "data"
OUTPUT_DIR    = Path("C:/output")
TEMPLATE_DIR  = BASE_DIR / "templates"
MINTAB_PATH   = r"C:\Program Files\Minitab\Minitab 22\Mtb.exe"

# Logging
LOG_FILE = BASE_DIR / "app.log"

# LED intensity column names (in intermediate Excel / JSON logs)
LED_INTENSITY_COLS = [
    "LED_RED_D303_INTENSITY",
    "LED_RED_D304_INTENSITY",
    "LED_WHITE_D305_INTENSITY",
    "LED_WHITE_D306_INTENSITY",
    "LED_WHITE_D307_INTENSITY",
    "LED_WHITE_D308_INTENSITY",
    "LED_WHITE_D309_INTENSITY",
    "LED_AMBER_D310_INTENSITY",
    "LED_WHITE_D311_INTENSITY",
]

# PNUM → LED column mapping (for FORM-004090 template)
PNUM_MAPPING = {
    "PNUM-4024": "LED_RED_D303_INTENSITY",
    "PNUM-4028": "LED_RED_D304_INTENSITY",
    "PNUM-4032": "LED_WHITE_D305_INTENSITY",
    "PNUM-4036": "LED_WHITE_D306_INTENSITY",
    "PNUM-4040": "LED_WHITE_D307_INTENSITY",
    "PNUM-4044": "LED_WHITE_D308_INTENSITY",
    "PNUM-4048": "LED_WHITE_D309_INTENSITY",
    "PNUM-4052": "LED_AMBER_D310_INTENSITY",
    "PNUM-4056": "LED_WHITE_D311_INTENSITY",
}
# LED specification limits
LED_SPECS = {
    col: {
        "lsl":   lo,
        "usl":   hi,
        "pnum":  pnum,
        "nominal": (lo + hi) / 2,
        "tol":   hi - lo,
    }
    for pnum, (col, lo, hi) in {
        4024: ("LED_RED_D303_INTENSITY",    13000, 65555),
        4028: ("LED_RED_D304_INTENSITY",     8000, 65555),
        4032: ("LED_WHITE_D305_INTENSITY",   11500, 65555),
        4036: ("LED_WHITE_D306_INTENSITY",   11500, 65555),
        4040: ("LED_WHITE_D307_INTENSITY",   15000, 65555),
        4044: ("LED_WHITE_D308_INTENSITY",   10000, 65555),
        4048: ("LED_WHITE_D309_INTENSITY",   15000, 65555),
        4052: ("LED_AMBER_D310_INTENSITY",   4500, 65555),
        4056: ("LED_WHITE_D311_INTENSITY",   15000, 65555),
    }.items()
}

# Backward-compatible alias
CPK_SPECS = {col: (spec["lsl"], spec["usl"]) for col, spec in LED_SPECS.items()}

# Maps bare LED name -> _INTENSITY suffixed name (intermediate Excel from JSON parser)
# e.g. "LED_RED_D303" -> "LED_RED_D303_INTENSITY"
LED_MAPPING = {
    col.replace("_INTENSITY", ""): col
    for col in LED_SPECS
}

def _norm_led(col: str) -> str:
    # Normalize: bare or _INTENSITY -> _INTENSITY form for spec lookup
    return LED_MAPPING.get(col, col)


# ── GRR Operator IDs ──────────────────────────────────────────────────────────
#  Operator IDs in the order they appear in the GRR Excel file.
#  GRR operator IDs used in SET C2 (Minitab GageRR).
#  Mapped by position: first unique operator in data → GRR_OPS[0], etc.
#  Example: ["462111", "495577", "421359"]
GRR_OPS = [
    "462111",
    "495577",
    "421359",
]


# GRR tolerance: ±20% of nominal (midpoint of spec)
def grr_tolerance(lo, hi):
    nominal = (lo + hi) / 2
    return nominal * 0.20   # 20% of nominal as tolerance half-width


# ── GRR Chart Layout ─────────────────────────────────────────────
#  Position and size for the Minitab charts embedded into each per-item
#  sheet. The template (Beta-GRR-Charger...xlsx) has 2 charts per item:
#    - Left  (col 2 / B, row 3)  :  main GageRR panel
#    - Right (col 8 / H, row 4)  :  X-bar / R breakdown
#  Tuple format: (col, row, width_px, height_px, colOff_px, rowOff_px)
GRR_CHART_LAYOUT = {
    "main":  (2, 3, 540, 400, 0, 0),   # B3, 540×400 (left)
    "xbar":  (8, 4, 460, 340, 0, 0),   # H4, 460×340 (right)
}

# Sheet-naming rule for per-item GRR sheets.
#   "pnum"      → "4024"
#   "pnum_dash" → "PNUM-4024"
GRR_SHEET_NAMING = "pnum"


# ── GRR Template File ─────────────────────────────────────────────
#  Excel file used as the base template for new GRR reports.
#  If the file exists, the generator loads it and preserves the first
#  4 sheets (Cover Page, GRR Form, Summary, Summary) as-is.
#  Falls back to building a blank workbook from scratch if missing.
GRR_TEMPLATE_PATH = str(Path(__file__).parent.parent / "report" / "GR_R_Template.xlsx")


# ── GRR Form Defaults ───────────────────────────────────────────────────────
#  Default values for the GRR Form sheet metadata.
#  Edit these to match your company's report standards.
#  Can be overridden in the GRR Config dialog.
#
#  inspector_numbers: used to populate SET C2 in the Minitab script.
#    With 10 parts × 3 ops × 3 reps = 90 measurements, the values are split
#    into three contiguous blocks of 30:
#      rows 1–30  → inspector_numbers[0]
#      rows 31–60 → inspector_numbers[1]
#      rows 61–90 → inspector_numbers[2]
GRR_FORM_DEFAULTS = {
    "part_number":        "PMMGH-DAC1471",
    "instrument":         "Charger MT7 Tester",
    "instrument_no":      "HVTE-M600099",
    "department":         "TE",
    "reported_by":        "Simon Huo",   # used as Minitab GageRR "User" field
    "report_date":        "",            # "" = use today's date; format e.g. "Jun 10 2026"
    "project_name":       "Beta",
    "measurement_unit":   "",
    "inspector_numbers":  ["2572744", "693109", "2566142"],   # default 3 inspectors
    "n_parts":            10,   # expected unique parts; extra SNs collapse to last index
}


# ── AR&R Chart Layout ─────────────────────────────────────────────────────
#  Position and size for each Minitab-generated chart embedded into the
#  AR&R Report sheet. Used as fallback defaults; can be overridden in the
#  AR&R Config dialog.
#  Tuple: (filename, col, row, width_px, height_px, colOff_px, rowOff_px)
#  Columns are 1-indexed: B=2, G=7, L=12
ARR_LAYOUT = [
    # Slide 1: B-row banner + chart
    ("slide01_shape02.png",  2,  3, 280,  90,  7,  7),
    ("slide01_shape03.png",  2,  7, 280,  27,  7,  9),
    ("slide01_shape04.png",  2,  9, 280,  90,  7, 13),
    # Slide 2: G-row banner + chart
    ("slide02_shape02.png",  7,  4, 280,  27, 12, 13),
    ("slide02_shape03.png",  7,  7, 280, 120,  9,  8),
    # Slide 3: L-row (top) banner + chart
    ("slide03_shape03.png", 12,  3, 280,  27,  8,  1),
    ("slide03_shape04.png", 12,  4, 280,  90,  6,  5),
    # Slide 4: L-row (bottom) banner + chart
    ("slide04_shape02.png", 12,  8, 280,  22, 14,  9),
    ("slide04_shape03.png", 12,  9, 280,  90,  5, 10),
    # Slide 5: B16 big chart
    ("slide05_shape01.png",  2, 16, 420, 280,  7,  4),
]


# ── GRR Chart Layout ────────────────────────────────────────────────────────
#  Position and size for each Minitab-generated chart embedded into the
#  GRR per-item sheet (PNUM-XXXX). Mirrors the AR&R layout pattern.
#  Tuple: (filename, col, row, width_px, height_px, colOff_px, rowOff_px)
#  Columns are 1-indexed: B=2, G=7, L=12
GRR_LAYOUT = [
    # Slide 1: B-row banner + chart
    ("slide01_shape04.png", 2, 3, 380, 25, 7, 9),
    ("slide02_shape01.png", 2, 5, 380, 140, 7, 9),
    ("slide02_shape02.png", 2, 12, 380, 25, 7, 13),
    # Slide 2: G-row banner + chart
    ("slide02_shape03.png", 2, 13, 380, 140, 12, 13),
    ("slide02_shape04.png", 2, 21, 380, 25, 9, 8),
    # Slide 3: L-row (top) banner + chart
    ("slide04_shape01.png", 8, 5, 480, 280, 8, 1),
]


# ── AR&R Form Defaults ───────────────────────────────────────────────────
#  Default values for the AR&R Form sheet metadata.
#  Edit these to match your company's report standards.
#  Can be overridden in the AR&R Config dialog.
#  V260: inspector_numbers and reported_by are hard-coded
#  here (not shared with GRR_FORM_DEFAULTS) per user request.
#  AR&R defaults:
#    - reported_by:       "Simon Huo"  (ARR report's Minitab "User" field)
#    - inspector_numbers: ["2572744", "693109", "2566142"]
#  The AR&R Config dialog values take precedence over these defaults.
ARR_FORM_DEFAULTS = {
    "part_number":    "PMMEH-ASM5286",
    "description":    "Alpha Finished ",
    "instrument":     "Alpha MT7H",
    "instrument_no":  "HVTE-M600271",
    "department":     "TE",
    "reported_by":    "Simon Huo",
    "fixture_no":     "HVTE-M600271",
    "project_name":   "Alpha",
    "date_format":    "%b %d, %Y",     # Python strftime for date_inspected default
    "date_placeholder": "Apr 08, 2026 (leave blank for today)",
    "inspector_numbers": ["2572744", "693109", "2566142"],
    "inspector_placeholders": ["e.g. 2572744", "e.g. 693109", "e.g. 2566142"],
}


# ── AR&R Sample Mapping Defaults ───────────────────────────────────────────
#  Default per-sample expected result and error code mapping.
#  Used by the AR&R Config dialog as initial values and by the quick-fill buttons.
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


# ── AR&R Faults Map Defaults ──────────────────────────────────────────────
#  Default fault code + description mapping for the Faults Simulation sheet.
DEFAULT_FAULTS = {
    1: ("CH709", "CONTROL_MT_MODE_STATE"),
    2: ("CH715", "CONTROL_VBATT_VOLTAGE"),
    3: ("EH719", "MEAS_HOT_GS_VLOAD"),
    4: ("EH717", "HOT_GS_ENGINE_THERMISTER_TEMPERATURE_BEFORE_HEAT"),
}


# ── AR&R Test Structure Defaults ──────────────────────────────────────────
#  Default counts for samples, appraisers, and trials.
ARR_TEST_STRUCTURE = {
    "n_samples":    10,
    "n_appraisers": 3,
    "n_trials":     3,
    "n_samples_range":   (1, 100),
    "n_appraisers_range": (1, 20),
    "n_trials_range":     (1, 10),
}


# ── AR&R Quick-Fill Templates ─────────────────────────────────────────────
#  Used by the "Set samples 1–4 as Known Bad" / "Set samples 5–10 as Known Good"
#  buttons in the config dialog.
QUICK_FILL_BAD_SAMPLES = {
    1: ("Known bad DUT 1",  "CONTROL_MT_MODE_STATE"),
    2: ("Known bad DUT 2",  "CONTROL_VBATT_VOLTAGE"),
    3: ("Known bad DUT 3",  "MEAS_HOT_GS_VLOAD"),
    4: ("Known bad DUT 4",  "HOT_GS_ENGINE_THERMISTER_TEMPERATURE_BEFORE_HEAT"),
}


def ensure_dirs():
    """Create necessary directories."""
    for d in (DATA_DIR, OUTPUT_DIR, TEMPLATE_DIR):
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()
