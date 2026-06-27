from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

@dataclass(frozen=True)
class WifiRate:
    # e.g. "11M", "54M", "HT20-MCS7", "HT40-MCS7"
    name: str

@dataclass(frozen=True)
class WifiChannelPoint:
    freq_mhz: int       # 2412
    ch: int             # 1

@dataclass
class WifiTxPowerCalPoint:
    chan: WifiChannelPoint
    rate: WifiRate
    target_power_dbm: Optional[float] = None   # 若你们有目标功率可填
    tolerance_db: Optional[float] = None

@dataclass
class WifiTxVerifyPoint:
    chan: WifiChannelPoint
    rate: WifiRate
    measure_evm: bool = True
    measure_peak: bool = True
    measure_power: bool = True
    measure_mask: bool = True
    measure_freq_err: bool = True

@dataclass
class WifiTxMetrics:
    power_dbm: Optional[float] = None
    peak_dbm: Optional[float] = None
    evm_db: Optional[float] = None
    freq_err_hz: Optional[float] = None
    mask_margin_db: Optional[float] = None
    raw: Dict[str, Any] = None

@dataclass
class WifiRxPerPoint:
    chan: WifiChannelPoint
    rate: WifiRate
    frames: int = 1000
    per_limit: float = 0.10
    input_power_dbm: Optional[float] = None   # 例如 -76 / -65 / 未给就 None

@dataclass
class WifiRxPerResult:
    per: float
    rssi_dbm: Optional[float] = None
    pass_fail: Optional[bool] = None
    raw: Dict[str, Any] = None

@dataclass
class WifiTestPlan:
    tx_power_cal: List[WifiTxPowerCalPoint]
    tx_verify: List[WifiTxVerifyPoint]
    rx_per: List[WifiRxPerPoint]