"""
SLE 功能驱动类（Wi‑SUN 等），继承 BaseRFDevice。
迁移原 rf_driver.py 中 SLE 相关方法与结果。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.libs.equipments.wt328ce.inst_base import BaseRFDevice
from src.libs.equipments.wt328ce.wifi import parse_wifi_base_result, WifiBaseResult


@dataclass
class SleBasicResult:
    power_frame_dbm: Optional[float] = None
    power_all_dbm: Optional[float] = None
    power_peak_dbm: Optional[float] = None

    base_result: Optional[WifiBaseResult] = None

    init_freq_error_khz: Optional[float] = None
    freq_drift_khz: Optional[float] = None
    freq_drift_rate: Optional[float] = None

    delta_fd1_avg_khz: Optional[float] = None
    delta_fd1_max_khz: Optional[float] = None
    delta_fd1_min_khz: Optional[float] = None

    delta_fd2_avg_khz: Optional[float] = None
    delta_fd2_min_khz: Optional[float] = None

    evm_avg: Optional[float] = None
    evm_peak: Optional[float] = None
    evm_p99pct: Optional[float] = None

    zero_crossing_err: Optional[float] = None


class SleRFDevice(BaseRFDevice):
    def __init__(self, inst, logger=None):
        super().__init__(inst, logger)

    def configure_sle_vsa(
        self,
        freq_mhz: int,
        max_power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        frame_type: int,
        bandwidth: int,
        ctrl_info_type: int,
        sync_mode: int,
        pid: int,
        sequence_num: int,
        access_code: str,
        payload_crc_type: int,
        payload_crc_seed: int,
        payload_mode: int,
        mcs: int,
        pilot_density: int,
        scramble: int,
        channel_type: int,
        freq_range: int,
        board_index: int,
        slot_index: int,
        rrc_filter: int,
        sample_time_s: float = 2e-3,
        sample_rate_hz: float = 120e6,
        trigger_level_dbm: float = -34,
        trigger_timeout_s: float = 2.5,
        pre_trigger_s: float = 2e-5,
        waiting_timeout_s: float = 10.0,
        reset_before_capture: bool = True,
        enable_all_psdu_bit: Optional[int] = 0,
        analyzer_freq_offset_hz: float = 0.0,
    ):
        if reset_before_capture:
            self.clear_status()
            self.reset()

        cmds = []

        if enable_all_psdu_bit is not None:
            cmds.append(f"WT:WIFI:SENSe:CONFigure:ANALy:ALL:PSDU:BIT {enable_all_psdu_bit}")

        cmds += [
            "WT:SENSe:CONFigure:DEMOd 41",
            f"WT:SENSe:CONFigure:RFPOrt {rf_port + 1}",
            f"WT:SENSe:CONF:FREQ {freq_mhz}e+009",
            "WT:SENSe:CONFigure:FREQuency:OFFSet 0.000000e+000",
            f"WT:SENSe:CONF:MAXP {max_power_dbm:.2f}",
            f"WT:SENSe:CONF:SMPT {sample_time_s:e}",
            f"WT:SENSe:CONF:SAMPle:RATE {sample_rate_hz}",
            "WT:SENSe:CONFigure:TRIGer:TYPE 2",
            f"WT:SENSe:CONFigure:TRIGer:LEVEl {trigger_level_dbm}",
            f"WT:SENSe:CONF:TRIG:TMO {trigger_timeout_s:e}",
            f"WT:SENSe:CONF:TRIG:PRET {pre_trigger_s:e}",
            f"WT:SENSe:CONFigure:TMOWaitting {waiting_timeout_s:e}",
            f"WT:SENSe:CONF:EXT1:GAIN {pathloss_db:.2f}",
            f"WT:SLE:SENS:CONF:ANAL:FRAMe:TYPE {frame_type}",
            f"WT:SLE:SENS:CONF:ANAL:BAND:WIDTh {bandwidth}",
            f"WT:SLE:SENS:CONF:ANAL:CTRL:INFO:TYPE {ctrl_info_type}",
            f"WT:SLE:SENS:CONF:ANAL:SYNC:MODE {sync_mode}",
            f"WT:SLE:SENS:CONF:ANAL:PID {pid}",
            f"WT:SLE:SENS:CONF:ANAL:M:SEQUence:NUM {sequence_num}",
            f'WT:SLE:SENS:CONF:ANAL:ACCEss:CODE "{access_code}"',
            f"WT:SLE:SENS:CONF:ANAL:PAYLoad:CRC:TYPE {payload_crc_type}",
            f"WT:SLE:SENS:CONF:ANAL:PAYLoad:CRC:SEED {payload_crc_seed}",
            f"WT:SLE:SENS:CONF:ANAL:PAYLoad:MODE {payload_mode}",
            f"WT:SLE:SENS:CONF:ANAL:MCS {mcs}",
            f"WT:SLE:SENS:CONF:ANAL:PILOt:DENSity {pilot_density}",
            f"WT:SLE:SENS:CONF:ANAL:SCRAmble {scramble}",
            f"WT:SLE:SENS:CONF:ANAL:CHANnel:TYPE {channel_type}",
            f"WT:SLE:SENS:CONF:ANAL:FREQ:RANGe {freq_range}",
            f"WT:SLE:SENS:CONF:ANAL:BOARd:INDEx {board_index}",
            f"WT:SLE:SENS:CONF:ANAL:SLOT:INDEx {slot_index}",
            f"WT:SLE:SENS:CONF:ANAL:RAISed:ROOT:COSIne:FILTer {rrc_filter}",
            f"WT:SLE:SENSe:CONFigure:ANALy:FREQuency:OFFSet {analyzer_freq_offset_hz:e}",
            "WT:SENSe:CAPTure",
        ]

        self.write("\n".join(cmds))
        self.check_error("sle vsa")

    def fetch_sle_basic_result(
        self,
        center_freq_hz: float,
        need_fd1: bool = False,
        need_fd2: bool = False,
        need_evm: bool = False,
        need_zero_crossing_err: bool = False,
    ) -> SleBasicResult:
        base = parse_wifi_base_result(
            self.query_ascii_values("WT:WIFI:SENSe:FETCh:BASEresult?"),
            center_freq_hz=center_freq_hz,
            mask_err_percent=None,
        )

        result = SleBasicResult(
            power_frame_dbm=base.power_frame_dbm,
            power_all_dbm=base.power_all_dbm,
            power_peak_dbm=base.power_peak_dbm,
            base_result=base,
        )

        try:
            result.init_freq_error_khz = float(self.query("WT:SLE:SENSe:FETCh:INIT:FREQ:ERROr?"))
        except Exception:
            pass

        try:
            result.freq_drift_khz = float(self.query("WT:SLE:SENSe:FETCh:FREQ:DRIFt?"))
        except Exception:
            pass

        try:
            result.freq_drift_rate = float(self.query("WT:SLE:SENSe:FETCh:FREQ:DRIFt:RATE?"))
        except Exception:
            pass

        if need_fd1:
            try:
                result.delta_fd1_avg_khz = float(self.query("WT:SLE:SENSe:FETCh:DELTa:FD1:AVG?")) / 1000.0
            except Exception:
                pass
            try:
                result.delta_fd1_max_khz = float(self.query("WT:SLE:SENSe:FETCh:DELTa:FD1:MAX?")) / 1000.0
            except Exception:
                pass
            try:
                result.delta_fd1_min_khz = float(self.query("WT:SLE:SENSe:FETCh:DELTa:FD1:MIN?")) / 1000.0
            except Exception:
                pass

        if need_fd2:
            try:
                result.delta_fd2_avg_khz = float(self.query("WT:SLE:SENSe:FETCh:DELTa:FD2:AVG?")) / 1000.0
            except Exception:
                pass
            try:
                result.delta_fd2_min_khz = float(self.query("WT:SLE:SENSe:FETCh:DELTa:FD2:MIN?")) / 1000.0
            except Exception:
                pass

        if need_evm:
            try:
                result.evm_avg = float(self.query("WT:SLE:SENSe:FETCh:EVM:AVG?"))
            except Exception:
                pass
            try:
                result.evm_peak = float(self.query("WT:SLE:SENSe:FETCh:EVM:PEAK?"))
            except Exception:
                pass
            try:
                result.evm_p99pct = float(self.query("WT:SLE:SENSe:FETCh:EVM:P99Pct?"))
            except Exception:
                pass

        if need_zero_crossing_err:
            try:
                result.zero_crossing_err = float(self.query("WT:SLE:SENSe:FETCh:ZERO:CROSsing:ERR?"))
            except Exception:
                pass

        return result
