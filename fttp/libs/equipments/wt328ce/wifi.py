"""
WiFi 功能驱动类，继承 BaseRFDevice。
将原 rf_driver.py 中 WiFi 相关 SCPI 方法与解析迁移到这里。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from src.libs.equipments.wt328ce.inst_base import BaseRFDevice, WT328CEError


# -------------------------
# Result models
# -------------------------
@dataclass
class WifiBaseResult:
    raw: List[float]

    power_frame_dbm: float
    power_all_dbm: float
    power_peak_dbm: float

    evm_all_db: float
    evm_peak_db: float
    evm_data_db: float
    evm_pilot_db: float
    evm_psdu_db: float
    evm_shrphr_db: float

    freq_offset_hz: float
    freq_err_ppm: Optional[float]

    carrier_leakage_db: float
    sync_clk_err_hz: float
    phase_err_deg: float
    iq_imb_amp: float
    iq_imb_phase_deg: float

    mask_err_percent: Optional[float] = None


@dataclass
class WifiMimoResult:
    composite: WifiBaseResult
    streams: List[WifiBaseResult]


@dataclass
class WifiTxMetrics:
    power_dbm: Optional[float] = None
    peak_dbm: Optional[float] = None
    evm_db: Optional[float] = None
    freq_err_hz: Optional[float] = None
    mask_margin_db: Optional[float] = None
    raw: Dict[str, Any] = None


# -------------------------
# Parser
# -------------------------
def parse_wifi_base_result(
    values: List[float],
    center_freq_hz: float,
    mask_err_percent: Optional[float] = None,
) -> WifiBaseResult:
    if len(values) != 15:
        raise WT328CEError(f"BASEresult must contain 15 values, got {len(values)}: {values}")

    freq_offset_hz = values[9]
    freq_err_ppm = None
    if center_freq_hz and freq_offset_hz != -999.99:
        freq_err_ppm = freq_offset_hz / center_freq_hz * 1e6

    return WifiBaseResult(
        raw=values,

        power_frame_dbm=values[0],
        power_all_dbm=values[1],
        power_peak_dbm=values[2],

        evm_all_db=values[3],
        evm_peak_db=values[4],
        evm_data_db=values[5],
        evm_pilot_db=values[6],
        evm_psdu_db=values[7],
        evm_shrphr_db=values[8],

        freq_offset_hz=freq_offset_hz,
        freq_err_ppm=freq_err_ppm,

        carrier_leakage_db=values[10],
        sync_clk_err_hz=values[11],
        phase_err_deg=values[12],
        iq_imb_amp=values[13],
        iq_imb_phase_deg=values[14],

        mask_err_percent=mask_err_percent,
    )


# -------------------------
# Wifi device class
# -------------------------
class WifiRFDevice(BaseRFDevice):
    def __init__(self, inst, logger=None):
        super().__init__(inst, logger)

    # VSA configuration
    def configure_wifi_vsa(
        self,
        rf_ports: List[int],
        freq_mhz: int,
        sample_rate_hz: float,
        demod: int,
        target_power_dbm: float = 0.0,
        pathloss_list: Optional[List[float]] = None,
        is_agc: bool = True,
        sample_time_us: int = 500,
        trigger_level_dbm: float = -31,
        trigger_timeout_s: float = 1.0,
        waiting_timeout_s: float = 8.0,
        pre_time_s: float = 2e-5,
        reset_before_capture: bool = False,
        enable_all_psdu_bit: Optional[int] = None,
        analyzer_freq_offset_hz: float = 0.0,
        eq_smoothing: Optional[int] = None,
    ):
        if pathloss_list is None:
            pathloss_list = [0.0 for _ in rf_ports]

        if reset_before_capture:
            self.clear_status()
            self.reset()

        power_csv = ",".join([f"{target_power_dbm + 12.0}" for _ in rf_ports])
        port_csv = ",".join([str(v + 1) for v in rf_ports])
        pathloss_csv = ",".join(str(v) for v in pathloss_list)

        cmds = []

        if enable_all_psdu_bit is not None:
            cmds.append(f"WT:WIFI:SENSe:CONFigure:ANALy:ALL:PSDU:BIT {enable_all_psdu_bit}")

        cmds += [
            "WT:SENSe:STOP:CAPTure",
            "WT:SENSe:CONFigure:TRIGer:TYPE 2",
            f"WT:SENSe:CONFigure:FREQuency {freq_mhz}e+06",
            "WT:SENSe:CONFigure:FREQuency:OFFSet 0",
            f"WT:SENSe:CONFigure:MAXPower {power_csv}",
            f"WT:SENSe:CONFigure:TRIGer:LEVEl {trigger_level_dbm}",
            f"WT:SENSe:CONFigure:RFPOrt {port_csv}",
            f"WT:SENSe:CONFigure:DEMOd {demod}",
            "WT:SENSe:CONFigure:MAX:IFG 0.2",
            f"WT:SENSe:CONFigure:TRIGer:TMO {trigger_timeout_s}",
            f"WT:WIFI:SENSe:CONFigure:TRIGer:PRETime {pre_time_s}",
            f"WT:SENSe:CONFigure:SMPTime {sample_time_us}e-6",
            f"WT:SENSe:CONFigure:SAMPle:RATE {sample_rate_hz}",
            f"WT:SENSe:CONFigure:TMOWaitting {waiting_timeout_s}",
            f"WT:SENSe:CONFigure:EXT1:GAIN {pathloss_csv}",
            "WT:WIFI:SENSe:CONFigure:ANALy:BANDwidth:MODE 0",
            f"WT:WIFI:SENSe:CONFigure:ANALy:DEMOd {demod}",
            f"WT:WIFI:SENSe:CONFigure:ANALy:FREQuency:OFFSet {analyzer_freq_offset_hz}",
            "WT:WIFI:SENSe:CONFigure:ANALy:DSSS:DC:REMOval 0",
            "WT:WIFI:SENSe:CONFigure:ANALy:DSSS:EVM:METHod 1",
            "WT:WIFI:SENSe:CONFigure:ANALy:DSSS:PH:CORR 2",
            "WT:WIFI:SENSe:CONFigure:ANALy:DSSS:EQ:TAPS 1",
            "WT:WIFI:SENSe:CONFigure:ANALy:OFDM:PH:CORR 2",
            "WT:WIFI:SENSe:CONFigure:ANALy:OFDM:CH:ESTImate 1",
            "WT:WIFI:SENSe:CONFigure:ANALy:OFDM:SYM:TIME:CORR 2",
            "WT:WIFI:SENSe:CONFigure:ANALy:OFDM:FREQ:SYNC 2",
            "WT:WIFI:SENSe:CONFigure:ANALy:OFDM:AMPL:TRACk 1",
            "WT:WIFI:SENSe:CONFigure:ANALy:CLOCk:RATE 1",
            "WT:SENSe:CONFigure:ANALy:FRAMe:INDEx 1",
        ]

        if eq_smoothing is not None:
            cmds.append(f"WT:WIFI:SENSe:CONFigure:ANALy:OFDM:EQUAlizer:SMOOthing {eq_smoothing}")

        if is_agc:
            cmds.append("WT:SENSe:AGC")

        cmds.append("WT:SENSe:CAPTure")

        self.write("\n".join(cmds))
        self.check_error("wifi vsa")

    # VSG
    def start_wifi_vsg(
        self,
        rf_ports: List[int],
        freq_mhz: int,
        sample_rate_hz: float,
        packets: int,
        wave_file: str,
        power_list: Optional[List[float]] = None,
        pathloss_list: Optional[List[float]] = None,
        wave_gap_s: float = 5e-5,
        waiting_timeout_s: float = 8.0,
    ):
        if power_list is None:
            power_list = [-10.0 for _ in rf_ports]
        if pathloss_list is None:
            pathloss_list = [0.0 for _ in rf_ports]

        power_csv = ",".join(str(v) for v in power_list)
        port_csv = ",".join(str(v + 1) for v in rf_ports)
        pathloss_csv = ",".join(str(v) for v in pathloss_list)

        cmds = [
            f"WT:SOURce:CONFigure:REPEat {packets}",
            f"WT:SOURce:CONFigure:WAVE:GAP {wave_gap_s}",
            f"WT:SOURce:CONFigure:WAVE '{wave_file}'",
            f"WT:SOURce:CONFigure:FREQuency {freq_mhz}e+06",
            f"WT:SOURce:CONFigure:SAMPle:RATE {sample_rate_hz}",
            f"WT:SOURce:CONFigure:POWer {power_csv}",
            f"WT:SOURce:CONFigure:RFPOrt {port_csv}",
            f"WT:SOURce:CONFigure:TMOWaitting {waiting_timeout_s}",
            "WT:SOURce:CONFigure:FREQuency:OFFSet 0",
            f"WT:SOURce:CONFigure:EXT1:GAIN {pathloss_csv}",
            "WT:SOURce:STARt",
        ]
        self.write("\n".join(cmds))
        self.check_error("wifi vsg")

        if packets == 0:
            self.wait_for_vsg_start(timeout=waiting_timeout_s)
        else:
            self.wait_for_vsg_complete(timeout=waiting_timeout_s)

    # -------------------------
    # fetch results / metrics
    # -------------------------
    def fetch_wifi_base_result(self, center_freq_hz: float,
                               stream: tuple[int, int] | None = None) -> WifiBaseResult:
        if stream is None:
            raw = self.query_ascii_values("WT:WIFI:SENSe:FETCh:BASEresult?")
            mask = float(self.query("WT:WIFI:SENSe:FETC:SPECtrum:MASK:ERROr:PERCent?"))
        else:
            raw = self.query_ascii_values(f"WT:WIFI:SENSe:FETCh:BASEresult? {stream[0]},{stream[1]}")
            mask = float(self.query(f"WT:WIFI:SENSe:FETC:SPECtrum:MASK:ERROr:PERCent? {stream[0]},{stream[1]}"))

        return parse_wifi_base_result(
            values=raw,
            center_freq_hz=center_freq_hz,
            mask_err_percent=mask,
        )

    def fetch_wifi_composite_result(self, center_freq_hz: float) -> WifiBaseResult:
        raw = self.query_ascii_values("WT:WIFI:SENSe:FETCh:BASEresult:COMPosite?")
        return parse_wifi_base_result(
            values=raw,
            center_freq_hz=center_freq_hz,
            mask_err_percent=None,
        )

    def fetch_tx_metrics(self):
        pass

    # Measurement helpers (wrapping configure + fetch)
    def measure_wifi_tx_all(
        self,
        rf_ports: List[int],
        freq_mhz: int,
        sample_rate_hz: float,
        demod: int,
        target_power_dbm: float = 0.0,
        pathloss_list: Optional[List[float]] = None,
        is_agc: bool = True,
        use_full_product_style: bool = False,
    ) -> WifiBaseResult:
        self.configure_wifi_vsa(
            rf_ports=rf_ports,
            freq_mhz=freq_mhz,
            sample_rate_hz=sample_rate_hz,
            demod=demod,
            target_power_dbm=target_power_dbm,
            pathloss_list=pathloss_list,
            is_agc=is_agc,
            reset_before_capture=use_full_product_style,
            enable_all_psdu_bit=0 if use_full_product_style else None,
            trigger_level_dbm=-34 if use_full_product_style else -31,
            trigger_timeout_s=2.5 if use_full_product_style else 1.0,
            waiting_timeout_s=10.0 if use_full_product_style else 8.0,
            analyzer_freq_offset_hz=0.0,
            eq_smoothing=0 if use_full_product_style else None,
        )
        return self.fetch_wifi_base_result(center_freq_hz=freq_mhz * 1e6)

    def measure_wifi_mimo_tx_all(
        self,
        rf_ports: List[int],
        freq_mhz: int,
        sample_rate_hz: float,
        demod: int,
        stream_count: int = 2,
        target_power_dbm: float = 0.0,
        pathloss_list: Optional[List[float]] = None,
    ) -> WifiMimoResult:
        self.configure_wifi_vsa(
            rf_ports=rf_ports,
            freq_mhz=freq_mhz,
            sample_rate_hz=sample_rate_hz,
            demod=demod,
            target_power_dbm=target_power_dbm,
            pathloss_list=pathloss_list,
            is_agc=True,
        )
        comp = self.fetch_wifi_composite_result(center_freq_hz=freq_mhz * 1e6)
        streams = []
        for i in range(stream_count):
            streams.append(self.fetch_wifi_base_result(center_freq_hz=freq_mhz * 1e6, stream=(i, 0)))
        return WifiMimoResult(composite=comp, streams=streams)

    def measure_wifi_freq_error_ppm(
        self,
        rf_port: int,
        freq_mhz: int,
        sample_rate_hz: float,
        demod: int,
        target_power_dbm: float = 0.0,
        pathloss_db: float = 0.0,
        use_full_product_style: bool = False,
    ) -> float:
        result = self.measure_wifi_tx_all(
            rf_ports=[rf_port],
            freq_mhz=freq_mhz,
            sample_rate_hz=sample_rate_hz,
            demod=demod,
            target_power_dbm=target_power_dbm,
            pathloss_list=[pathloss_db],
            is_agc=True,
            use_full_product_style=use_full_product_style,
        )
        if result.freq_err_ppm is None:
            raise WT328CEError("wifi freq_err_ppm is None")
        return result.freq_err_ppm

    def measure_wifi_power_dbm(
        self,
        rf_port: int,
        freq_mhz: int,
        sample_rate_hz: float,
        demod: int,
        target_power_dbm: float = 0.0,
        pathloss_db: float = 0.0,
        use_power_field: str = "power_frame",
        use_full_product_style: bool = False,
    ) -> float:
        result = self.measure_wifi_tx_all(
            rf_ports=[rf_port],
            freq_mhz=freq_mhz,
            sample_rate_hz=sample_rate_hz,
            demod=demod,
            target_power_dbm=target_power_dbm,
            pathloss_list=[pathloss_db],
            is_agc=True,
            use_full_product_style=use_full_product_style,
        )
        if use_power_field == "power_all":
            return result.power_all_dbm
        if use_power_field == "power_peak":
            return result.power_peak_dbm
        return result.power_frame_dbm

    # OFDMA / MU helpers
    def fetch_ofdma_user_information(self):
        return self.query_ascii_values("WT:WIFI:SENSe:FETCh:OFDM:RU:USER:INFO?")

    def fetch_mu_ru_count_information(self):
        return self.query_ascii_values("WT:WIFI:SENSe:FETCh:OFDM:MU:RU:COUNt:INFO?")

    def fetch_mu_ru_information(self, ru_index: int):
        return self.query_ascii_values(f"WT:WIFI:SENSe:FETCh:OFDM:MU:RU:INFO? {ru_index}")

    def fetch_mu_ru_user_information(self, ru_index: int, user_index: int):
        return self.query_ascii_values(
            f"WT:WIFI:SENSe:FETCh:OFDM:MU:RU:USER:INFO? {ru_index},{user_index}"
        )
