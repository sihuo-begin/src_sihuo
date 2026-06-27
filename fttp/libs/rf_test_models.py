# encoding=utf-8

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class StepResult:
    ok: bool
    value: str


@dataclass
class WifiTxMeasurement:
    power_dbm: Optional[float] = None
    evm_db: Optional[float] = None
    freq_err_ppm: Optional[float] = None
    mask_err_percent: Optional[float] = None
    raw: Any = None


@dataclass
class WifiRxMeasurement:
    tester_send_frames: Optional[int] = None
    dut_receive_frames: Optional[int] = None
    per_percent: Optional[float] = None
    target_power_dbm: Optional[float] = None
    raw: Any = None


@dataclass
class BtTxMeasurement:
    power_dbm: Optional[float] = None
    init_freq_err_khz: Optional[float] = None
    delta_f1_avg_khz: Optional[float] = None
    delta_f1_max_khz: Optional[float] = None
    delta_f1_min_khz: Optional[float] = None
    delta_f2_avg_khz: Optional[float] = None
    delta_f2_min_khz: Optional[float] = None
    delta_f2_max_khz: Optional[float] = None
    delta_f2_f1: Optional[float] = None
    fn_max_khz: Optional[float] = None
    f0fn_max_khz: Optional[float] = None
    f1f0_delta_khz: Optional[float] = None
    fnfn5_max_khz: Optional[float] = None
    f0f3_delta_khz: Optional[float] = None
    f0fn3_delta_khz: Optional[float] = None
    raw: Any = None


@dataclass
class BtRxMeasurement:
    tester_send_frames: Optional[int] = None
    dut_receive_frames: Optional[int] = None
    per_percent: Optional[float] = None
    target_power_dbm: Optional[float] = None
    raw: Any = None

