from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass(frozen=True)
class BtChannelPoint:
    freq_mhz: int  # 2402/2422/2442/2480
    ch: int        # 0/10/20/39 etc

@dataclass(frozen=True)
class BtPhy:
    # "BLE1M", "BLE2M", "BLE125K", "BLE500K"
    name: str

@dataclass
class BtTxPowerIndexCalPoint:
    ch: BtChannelPoint
    pattern: str = "PRBS9"
    measure_power: bool = True
    measure_flatness: bool = True

@dataclass
class BtTxVerifyPoint:
    ch: BtChannelPoint
    phy: BtPhy
    measure_power: bool = True
    measure_init_freq_err: bool = True
    measure_delta_f1_avg: bool = True
    measure_delta_f2_avg: bool = True
    measure_delta_f2_f1: bool = True
    measure_delta_f2_min: bool = True
    measure_delta_f2_max: bool = True
    measure_fn_max: bool = True
    measure_f0fn_max: bool = True
    measure_f1f0_delta: bool = True
    measure_fnfn5_max: bool = True
    # 125K ：F0F3, F0Fn3 等，可在 raw 中扩展

@dataclass
class BtTxMetrics:
    power_dbm: Optional[float] = None
    init_freq_err_hz: Optional[float] = None
    delta_f1_avg: Optional[float] = None
    delta_f2_avg: Optional[float] = None
    delta_f2_f1: Optional[float] = None
    delta_f2_min: Optional[float] = None
    delta_f2_max: Optional[float] = None
    fn_max: Optional[float] = None
    f0fn_max: Optional[float] = None
    f1f0_delta: Optional[float] = None
    fnfn5_max: Optional[float] = None
    raw: Dict[str, Any] = None

@dataclass
class BtRxPerPoint:
    ch: BtChannelPoint
    phy: BtPhy
    input_power_dbm: float     # 例如 -70 / -82 / -75
    frames: int = 1000
    per_limit: float = 0.10

@dataclass
class BtRxPerResult:
    per: float
    pass_fail: Optional[bool] = None
    raw: Dict[str, Any] = None

@dataclass
class BtTestPlan:
    tx_power_index_cal: List[BtTxPowerIndexCalPoint]
    tx_verify: List[BtTxVerifyPoint]
    rx_per: List[BtRxPerPoint]