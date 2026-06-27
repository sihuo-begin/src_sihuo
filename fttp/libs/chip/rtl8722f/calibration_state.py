from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class RuntimePhase:
    active_interface: str = "wifi"   # wifi / bt / idle
    phase: str = "init"
    pathloss_yaml: Optional[str] = None
    pathloss_table: Any = None


@dataclass
class WifiState:
    mp_initialized: bool = False
    preheated: bool = False

    initial_thermal: Optional[int] = None
    thermal_after_preheat: Optional[int] = None

    xcap_init: Optional[int] = None
    xcap_final: Optional[int] = None
    crystal_freq_err_ppm: Optional[float] = None
    crystal_done: bool = False

    initial_power_table: Dict[str, Any] = field(default_factory=dict)

    tx_cal_done: bool = False
    tx_cal_points: List[Dict[str, Any]] = field(default_factory=list)
    tx_cal_runtime_table: Dict[str, Any] = field(default_factory=dict)
    tx_cal_otp_table: Dict[str, Any] = field(default_factory=dict)
    final_power_table: Dict[str, Any] = field(default_factory=dict)
    tx_verify_last: Dict[str, Any] = field(default_factory=dict)
    tx_verify_evm: Optional[float] = None
    tx_verify_freq_err_hz: Optional[float] = None

    rx_verify_last: Dict[str, Any] = field(default_factory=dict)

    thermal_wifi: Optional[int] = None


@dataclass
class BtState:
    entered_bt_mode: bool = False
    initialized: bool = False
    reset_done: bool = False

    cal_done: bool = False
    center_channel: Optional[int] = None
    center_freq_mhz: Optional[int] = None
    center_power_dbm: Optional[float] = None

    gain_k: Optional[int] = None
    flatness_points: Dict[int, float] = field(default_factory=dict)
    flatness_bytes: List[int] = field(default_factory=list)
    thermal_bt: Optional[int] = None
    valid_bits: Optional[int] = None

    tx_verify_last: Dict[str, Any] = field(default_factory=dict)
    tx_verify_freq_err_hz: Optional[float] = None

    rx_verify_last: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EfuseState:
    image: Dict[int, int] = field(default_factory=dict)
    write_commands: List[str] = field(default_factory=list)
    write_outputs: List[str] = field(default_factory=list)
    realmap_dump: str = ""
    saved: bool = False
    written: bool = False
    checked: bool = False


@dataclass
class Rtl8722fCalibrationState:
    runtime: RuntimePhase = field(default_factory=RuntimePhase)
    wifi: WifiState = field(default_factory=WifiState)
    bt: BtState = field(default_factory=BtState)
    efuse: EfuseState = field(default_factory=EfuseState)

    finished: bool = False