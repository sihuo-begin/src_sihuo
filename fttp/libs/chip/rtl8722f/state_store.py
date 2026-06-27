from __future__ import annotations

from src.libs.chip.rtl8722f.calibration_state import Rtl8722fCalibrationState


_STATE: Rtl8722fCalibrationState | None = None


def get_or_create_state() -> Rtl8722fCalibrationState:
    global _STATE
    if _STATE is None:
        _STATE = Rtl8722fCalibrationState()
    return _STATE


def reset_state() -> Rtl8722fCalibrationState:
    global _STATE
    _STATE = Rtl8722fCalibrationState()
    return _STATE