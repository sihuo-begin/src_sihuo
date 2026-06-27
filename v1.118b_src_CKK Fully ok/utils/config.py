# ──────────────────────────────────────────────
#  Application Configuration
# ──────────────────────────────────────────────
from pathlib import Path

APP_NAME    = "M600099 GRR & CPK Analyzer"
APP_VERSION = "1.1.0"
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


def ensure_dirs():
    """Create necessary directories."""
    for d in (DATA_DIR, OUTPUT_DIR, TEMPLATE_DIR):
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()
