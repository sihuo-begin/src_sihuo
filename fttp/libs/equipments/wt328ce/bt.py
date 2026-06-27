"""
BT / BLE 功能驱动类，继承 BaseRFDevice。
从原 rf_driver.py 迁移 BT 相关方法与数据模型。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.libs.equipments.wt328ce.inst_base import BaseRFDevice, WT328CEError


@dataclass
class BtPowerFrameResult:
    frame_count: Optional[int] = None
    power_dbm: Optional[float] = None
    max_carrier_frequency_hz: Optional[float] = None
    init_freq_err_khz: Optional[float] = None


@dataclass
class BtDeltaF1Result:
    delta_f1_avg_khz: Optional[float] = None
    delta_f1_max_khz: Optional[float] = None
    delta_f1_min_khz: Optional[float] = None


@dataclass
class BtDeltaF2DriftResult:
    delta_f2_avg_khz: Optional[float] = None
    delta_f2_min_khz: Optional[float] = None
    delta_f2_max_khz: Optional[float] = None

    fn_max_khz: Optional[float] = None
    f0fn_max_khz: Optional[float] = None
    f1f0_delta_khz: Optional[float] = None
    fnfn5_max_khz: Optional[float] = None


@dataclass
class BtTxSummaryResult:
    power_dbm: Optional[float] = None
    frame_count: Optional[int] = None
    max_carrier_frequency_hz: Optional[float] = None
    init_freq_err_khz: Optional[float] = None

    delta_f1_avg_khz: Optional[float] = None
    delta_f1_max_khz: Optional[float] = None
    delta_f1_min_khz: Optional[float] = None

    delta_f2_avg_khz: Optional[float] = None
    delta_f2_min_khz: Optional[float] = None
    delta_f2_max_khz: Optional[float] = None

    fn_max_khz: Optional[float] = None
    f0fn_max_khz: Optional[float] = None
    f1f0_delta_khz: Optional[float] = None
    fnfn5_max_khz: Optional[float] = None


class BtRFDevice(BaseRFDevice):
    def __init__(self, inst, logger=None):
        super().__init__(inst, logger)

    def configure_vsa(self, freq_mhz: int, target_power_dbm: float, rf_port: int, pathloss_db: float,
                      demod: int, phy: int, is_agc: bool = False):
        cmds = [
            f"WT:BT:SENSe:CONF:FREQ {freq_mhz}e6",
            f"WT:BT:SENSe:CONF:MAXP {target_power_dbm + 5}",
            "WT:BT:SENSe:CONF:SMPT 0.001",
            "WT:BT:SENSe:CONF:SAMPle:RATE 120e6",
            f"WT:BT:SENSe:CONF:RFPO {rf_port + 1}",
            "WT:BT:SENSe:CONF:TRIGer:TYPE 2",
            "WT:BT:SENSe:CONF:TRIGer:LEVEl -31",
            "WT:SENSe:CONF:FREQuency:OFFSet 7e6",
            "WT:BT:SENSe:CONF:TRIG:TMO 1.5",
            "WT:WIFI:SENSe:CONF:TMOWaitting 13",
            f"WT:BT:SENSe:CONF:DEMOd {demod}",
            f"WT:BT:SENSe:CONF:ANALy:BTRAte {phy}",
            "WT:BT:SENSe:CONF:ANALy:PACK:TYPE 0",
            f"WT:BT:SENSe:CONF:EXT1:GAIN {pathloss_db}",
            "WT:SENSe:CONF:ANALy:FREQuency:OFFSet 7e6",
        ]
        if is_agc:
            cmds.append("WT:BT:SENSe:AGC")
        cmds.append("WT:BT:SENSe:CAPTure")

        for cmd in cmds:
            self.write(cmd)

    def fetch_power_only(self):
        """
        legacy helper: ensure frame_count valid, then get power
        """
        frame_count = int(float(self.query("WT:BT:SENSe:FETCh:POWer:FRAMe:COUNt?")))
        if not frame_count or frame_count < 1:
            raise RuntimeError("BT capture frame count invalid")
        power = float(self.query("WT:BT:SENSe:FETCh:POWer:FRAMe?"))
        return {
            "frame_count": frame_count,
            "power_dbm": power,
        }

    def fetch_delta_f1(self):
        valid = int(float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:VALId?")))
        if valid != 1:
            return {"delta_f1_avg_hz": None}
        return {
            "delta_f1_avg_hz": float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:AVGrage?"))
        }

    def fetch_delta_f2_and_ble(self):
        result = {}

        valid = int(float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:VALId?")))
        if valid == 1:
            result["delta_f2_avg_hz"] = float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:AVGrage?"))
            result["delta_f2_max_hz"] = float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:MAXimun?"))
        else:
            result["delta_f2_avg_hz"] = None
            result["delta_f2_max_hz"] = None

        result["fn_max_hz"] = float(self.query("WT:BT:SENSe:FETCh:BLE:FN:MAXimun?"))
        result["f0fn_max_hz"] = float(self.query("WT:BT:SENSe:FETCh:BLE:F0FN:MAXimun?"))
        result["f1f0_delta_hz"] = float(self.query("WT:BT:SENSe:FETCh:BLE:DELTa:F1F0?"))
        result["fnfn5_max_hz"] = float(self.query("WT:BT:SENSe:FETCh:BLE:DELTa:FNFN5:MAXimun?"))
        return result

    # start/stop VSG helpers
    def start_bt_vsg(
        self,
        freq_mhz: int,
        power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        wave_name: str,
        packets: int,
        demod: int = 9,
        wave_gap_s: float = 0.0,
        waiting_timeout_s: float = 10.0,
    ):
        sample_rate_hz = 120e6 if demod == 9 else 240e6

        cmds = [
            f"WT:SOURce:CONF:RFPO {rf_port + 1}",
            f"WT:SOURce:CONF:FREQ {freq_mhz}e+009",
            "WT:SOURce:CONFigure:FREQuency:OFFSet 0.000000e+000",
            f"WT:SOURce:CONFigure:TMOWaitting {waiting_timeout_s:e}",
            f"WT:SOURce:CONF:POW {power_dbm:.2f}",
            f"WT:SOURce:CONF:WAVE:GAP {wave_gap_s:e}",
            f"WT:SOURce:CONF:REPE {packets}",
            f"WT:SOURce:CONF:EXT1:GAIN {pathloss_db:.2f}",
            f"WT:SOURce:CONF:WAVE '{wave_name}'",
            f"WT:SOURce:CONF:SAMPle:RATE {sample_rate_hz}",
            "WT:SOURce:STARt",
        ]

        self.clear_status()
        self.reset()
        self.write("\n".join(cmds))
        self.check_error("bt vsg")

        # reuse source state polling in Base? replicate here:
        if packets == 0:
            self.wait_for_vsg_start(timeout=waiting_timeout_s)
        else:
            self.wait_for_vsg_complete(timeout=waiting_timeout_s)

    def configure_bt_vsa(
        self,
        freq_mhz: int,
        max_power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        demod: int,
        phy: int,
        is_agc: bool = True,
        reset_before_capture: bool = True,
        enable_all_psdu_bit: Optional[int] = 0,
        sample_time_s: float = 5e-4,
        sample_rate_hz: float = 120e6,
        trigger_level_dbm: float = -31,
        trigger_timeout_s: float = 2.5,
        trigger_pre_time_s: float = 1.5e-4,
        waiting_timeout_s: float = 10.0,
        frequency_offset_hz: float = 7e6,
        packet_type: int = 0,
    ):
        if reset_before_capture:
            self.clear_status()
            self.reset()

        cmds = []

        if enable_all_psdu_bit is not None:
            cmds.append(f"WT:WIFI:SENSe:CONFigure:ANALy:ALL:PSDU:BIT {enable_all_psdu_bit}")

        cmds += [
            f"WT:BT:SENSe:CONF:FREQ {freq_mhz}e+009",
            f"WT:BT:SENSe:CONFigure:FREQuency:OFFSet {frequency_offset_hz:e}",
            f"WT:BT:SENSe:CONF:MAXP {max_power_dbm:.2f}",
            f"WT:BT:SENSe:CONF:SMPT {sample_time_s:e}",
            f"WT:BT:SENSe:CONF:SAMPle:RATE {sample_rate_hz}",
            f"WT:BT:SENSe:CONFigure:RFPOrt {rf_port + 1}",
            "WT:BT:SENSe:CONFigure:TRIGer:TYPE 2",
            f"WT:BT:SENSe:CONFigure:TRIGer:LEVEl {trigger_level_dbm}",
            f"WT:BT:SENSe:CONF:TRIG:TMO {trigger_timeout_s:e}",
            f"WT:BT:SENSe:CONF:TRIG:PRET {trigger_pre_time_s:e}",
            f"WT:BT:SENSe:CONFigure:TMOWaitting {waiting_timeout_s:e}",
            f"WT:BT:SENSe:CONFigure:DEMOd {demod}",
            f"WT:BT:SENSe:CONFigure:ANALy:BTRAte {phy}",
            f"WT:BT:SENSe:CONF:ANALy:PACK:TYPE {packet_type}",
            f"WT:BT:SENSe:CONFigure:ANALy:FREQuency:OFFSet {frequency_offset_hz:e}",
            f"WT:BT:SENSe:CONF:EXT1:GAIN {pathloss_db:.2f}",
        ]

        if is_agc:
            cmds.append("WT:SENSe:AGC")

        cmds.append("WT:SENSe:CAPTure")

        self.write("\n".join(cmds))
        self.check_error("bt vsa")

    def start_bt_rx_per_tx(
        self,
        freq_mhz: int,
        power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        wave_name: str,
        packets: int = 1000,
        demod: int = 9,
        wave_gap_s: float = 0.0,
        waiting_timeout_s: float = 10.0,
    ):
        self.start_bt_vsg(
            freq_mhz=freq_mhz,
            power_dbm=power_dbm,
            rf_port=rf_port,
            pathloss_db=pathloss_db,
            wave_name=wave_name,
            packets=packets,
            demod=demod,
            wave_gap_s=wave_gap_s,
            waiting_timeout_s=waiting_timeout_s,
        )

    def stop_bt_rx_per_tx(self):
        self.stop_vsg()

    # -------------------------
    # BT fetch helpers (replicate logic from original)
    # -------------------------
    def fetch_bt_power_frame(self, with_frame_count: bool = True, with_carrier_freq: bool = True) -> BtPowerFrameResult:
        result = BtPowerFrameResult()

        if with_frame_count:
            result.frame_count = int(float(self.query("WT:BT:SENSe:FETCh:POWer:FRAMe:COUNt?")))

        result.power_dbm = float(self.query("WT:BT:SENSe:FETCh:POWer:FRAMe?"))

        if with_carrier_freq:
            result.max_carrier_frequency_hz = float(self.query("WT:BT:SENSe:FETCh:MAX:CARRer:FREQuency?"))
            result.init_freq_err_khz = result.max_carrier_frequency_hz / 1000.0

        return result

    def fetch_bt_delta_f1(self, with_max_min: bool = False, check_valid: bool = False) -> BtDeltaF1Result:
        if check_valid:
            valid = int(float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:VALId?")))
            if valid != 1:
                return BtDeltaF1Result()

        result = BtDeltaF1Result()
        result.delta_f1_avg_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:AVGrage?")) / 1000.0

        if with_max_min:
            try:
                result.delta_f1_max_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:MAXimun?")) / 1000.0
            except Exception:
                pass
            try:
                result.delta_f1_min_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F1:MINimun?")) / 1000.0
            except Exception:
                pass

        return result

    def fetch_bt_delta_f2_and_ble_drift(self, check_valid: bool = False) -> BtDeltaF2DriftResult:
        result = BtDeltaF2DriftResult()

        if check_valid:
            valid = int(float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:VALId?")))
            if valid != 1:
                return result

        result.delta_f2_avg_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:AVGrage?")) / 1000.0
        result.delta_f2_min_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:MINimun?")) / 1000.0
        result.delta_f2_max_khz = float(self.query("WT:BT:SENSe:FETCh:DELTa:F2:MAXimun?")) / 1000.0

        result.fn_max_khz = float(self.query("WT:BT:SENSe:FETCh:BLE:FN:MAXimun?")) / 1000.0

        drift_valid = int(float(self.query("WT:BT:SENSe:FETCh:BLE:DRIFt:DETAIL:VALId?")))
        if drift_valid == 1:
            result.f0fn_max_khz = float(self.query("WT:BT:SENSe:FETCh:BLE:F0FN:MAXimun?")) / 1000.0

            drift_valid = int(float(self.query("WT:BT:SENSe:FETCh:BLE:DRIFt:DETAIL:VALId?")))
            if drift_valid == 1:
                result.f1f0_delta_khz = float(self.query("WT:BT:SENSe:FETCh:BLE:DELTa:F1F0?")) / 1000.0

            drift_valid = int(float(self.query("WT:BT:SENSe:FETCh:BLE:DRIFt:DETAIL:VALId?")))
            if drift_valid == 1:
                result.fnfn5_max_khz = float(self.query("WT:BT:SENSe:FETCh:BLE:DELTa:FNFN5:MAXimun?")) / 1000.0

        return result

    def measure_bt_tx_summary(
        self,
        freq_mhz: int,
        max_power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        demod: int,
        phy: int,
        payload_type: int,
        use_agc: bool = False,
        full_product_style: bool = True,
    ) -> BtTxSummaryResult:
        self.configure_bt_vsa(
            freq_mhz=freq_mhz,
            max_power_dbm=max_power_dbm,
            rf_port=rf_port,
            pathloss_db=pathloss_db,
            demod=demod,
            phy=phy,
            is_agc=use_agc,
            reset_before_capture=full_product_style,
            enable_all_psdu_bit=0 if full_product_style else None,
            packet_type=0,
        )

        summary = BtTxSummaryResult()

        if payload_type == 0:
            r = self.fetch_bt_power_frame(with_frame_count=True, with_carrier_freq=True)
            summary.power_dbm = r.power_dbm
            summary.frame_count = r.frame_count
            summary.max_carrier_frequency_hz = r.max_carrier_frequency_hz
            summary.init_freq_err_khz = r.init_freq_err_khz

        elif payload_type == 1:
            r = self.fetch_bt_delta_f1(with_max_min=True, check_valid=False)
            summary.delta_f1_avg_khz = r.delta_f1_avg_khz
            summary.delta_f1_max_khz = r.delta_f1_max_khz
            summary.delta_f1_min_khz = r.delta_f1_min_khz

        elif payload_type == 2:
            r = self.fetch_bt_delta_f2_and_ble_drift(check_valid=False)
            summary.delta_f2_avg_khz = r.delta_f2_avg_khz
            summary.delta_f2_min_khz = r.delta_f2_min_khz
            summary.delta_f2_max_khz = r.delta_f2_max_khz
            summary.fn_max_khz = r.fn_max_khz
            summary.f0fn_max_khz = r.f0fn_max_khz
            summary.f1f0_delta_khz = r.f1f0_delta_khz
            summary.fnfn5_max_khz = r.fnfn5_max_khz

        else:
            raise WT328CEError(f"unsupported BT payload_type: {payload_type}")

        return summary
