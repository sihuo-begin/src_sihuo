# encoding=utf-8

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional

import pyvisa
from pyvisa import constants


class WT328CEError(Exception):
    pass


# =========================================================
# Result models
# =========================================================

@dataclass
class WifiBaseResult:
    """
    Parsed result of:
      WT:WIFI:SENSe:FETCh:BASEresult?

    Field order from SCPI manual:
      0  PowerFrame
      1  PowerAll
      2  PowerPeak
      3  EvmAll
      4  EvmPeak
      5  EvmData
      6  EvmPilot
      7  EvmPsdu
      8  EvmShrPhr
      9  FreqOffset      (Hz)
      10 CarrierLeakage  (dB)
      11 SyncClkErr      (Hz)
      12 PhaseErr        (deg)
      13 IQImbAmp
      14 IQImbPhase      (deg)
    """
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
    """
    Unified BT TX result for BLE/BT basic production use.
    """
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


@dataclass
class SleBasicResult:
    """
    SLE result based on provided examples.
    """
    power_frame_dbm: Optional[float] = None
    power_all_dbm: Optional[float] = None
    power_peak_dbm: Optional[float] = None

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

    base_result: Optional[WifiBaseResult] = None


# =========================================================
# Parse helpers
# =========================================================

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


# =========================================================
# Driver
# =========================================================

class WT328CEDriver:
    """
    Consolidated WT328CE driver.

    Covered:
    - connect / close / clear / reset / check_error
    - upload waveform
    - add mimo tester
    - Wi-Fi VSG / VSA
    - Wi-Fi BASEresult / mask fetch
    - Wi-Fi MIMO / OFDMA / MU helpers
    - BT/BLE VSG / VSA
    - BT/BLE power / carrier freq / delta F1/F2 / drift fetch
    - SLE VSA config / SLE fetch basics

    Notes:
    - This driver is tester-side only
    - Product pass/fail policy should be implemented in steps, not here
    """

    def __init__(self, ip: str, logger=None, timeout_ms: int = 10000):
        self.ip = ip
        self.logger = logger
        self.timeout_ms = timeout_ms
        self.rm: Optional[pyvisa.ResourceManager] = None
        self.inst = None

    # -----------------------------------------------------
    # basic io
    # -----------------------------------------------------
    def _log(self, msg: str):
        if self.logger:
            self.logger.info(msg)

    def connect(self) -> str:
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(f"TCPIP0::{self.ip}::5025::SOCKET")
        self.inst.timeout = self.timeout_ms
        self.inst.read_termination = "\r\n"
        idn = self.inst.query("*IDN?")
        self.inst.write("WT:SYSTem:CMD:RESPonse 0")
        self._log(f"[WT328CE] connected: {idn.strip()}")
        return idn.strip()

    def close(self):
        if self.inst:
            self.inst.close()
            self.inst = None
        if self.rm:
            self.rm.close()
            self.rm = None

    def identify(self) -> str:
        return self.query("*IDN?")

    def write(self, cmd: str):
        self._log(f"[WT328CE][WRITE] {cmd}")
        self.inst.write(cmd)

    def query(self, cmd: str) -> str:
        self._log(f"[WT328CE][QUERY] {cmd}")
        return self.inst.query(cmd).strip()

    def query_ascii_values(self, cmd: str) -> List[float]:
        self._log(f"[WT328CE][QUERY_ASCII] {cmd}")
        return self.inst.query_ascii_values(cmd)

    def check_error(self, func: str):
        errinfo = self.inst.query(":SYSTem:ERRor?")
        if '0,"No error"' not in errinfo:
            raise WT328CEError(f"{func} error: {errinfo}")

    def clear_status(self):
        self.write("*CLS")

    def reset(self):
        self.write("*RST")

    # -----------------------------------------------------
    # waveform management
    # -----------------------------------------------------
    def upload_vsg_waveform(self, file_path: str) -> str:
        file_name = os.path.basename(file_path)
        self.inst.set_visa_attribute(constants.VI_ATTR_TERMCHAR_EN, constants.VI_TRUE)
        with open(file_path, "rb") as f:
            data = f.read()
            self.inst.write_binary_values(
                f'WT:SOURce:CONFigure:SAVE:WAVE "{file_name}",0,',
                data,
                datatype="s",
                termination="\n",
            )
        self.check_error(f"upload waveform {file_name}")
        return file_name

    def load_capture_wave_to_vsa(
        self,
        demod: int,
        local_wave: str,
        freq_mhz: int = 2412,
        rf_port: int = 2,
        sample_rate_hz: float = 240e6,
    ) -> str:
        cmds = [
            "WT:SENSe:STOP:CAPTure",
            "WT:SENSe:CONFigure:TRIGer:TYPE 2",
            f"WT:SENSe:CONFigure:FREQuency {freq_mhz}e+06",
            "WT:SENSe:CONFigure:FREQuency:OFFSet 0",
            "WT:SENSe:CONFigure:MAXPower 0",
            "WT:SENSe:CONFigure:TRIGer:LEVEl -31",
            f"WT:SENSe:CONFigure:RFPOrt {rf_port}",
            f"WT:SENSe:CONFigure:DEMOd {demod}",
            "WT:SENSe:CONFigure:MAX:IFG 0.2",
            "WT:SENSe:CONFigure:TRIGer:TMO 1",
            "WT:WIFI:SENSe:CONFigure:TRIGer:PRETime 2E-05",
            "WT:SENSe:CONFigure:SMPTime 500e-6",
            f"WT:SENSe:CONFigure:SAMPle:RATE {sample_rate_hz}",
            "WT:SENSe:CONFigure:TMOWaitting 8",
            "WT:SENSe:CONFigure:EXT1:GAIN 0",
            "WT:WIFI:SENSe:CONFigure:ANALy:BANDwidth:MODE 0",
            f"WT:WIFI:SENSe:CONFigure:ANALy:DEMOd {demod}",
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
        self.write("\n".join(cmds))
        self.check_error("load capture wave to vsa config")

        file_name = os.path.basename(local_wave)
        with open(local_wave, "rb") as f:
            data = f.read()
            self.inst.write_binary_values(
                f'WT:WIFI:SENSe:LOAD:FILE:CAPT "{file_name}",0,',
                data,
                datatype="s",
                termination="\n",
            )
        self.check_error("load capture wave to vsa wave")
        return file_name

    def add_mimo_tester(self, ip_list: List[str]):
        ip_cmd = ",".join([f'"{ip}"' for ip in ip_list])
        self.write(f"WT:REM:CONNect {ip_cmd}")
        self.check_error("add_mimo_tester")

    # -----------------------------------------------------
    # source state
    # -----------------------------------------------------
    def wait_for_vsg_complete(self, timeout=5):
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise WT328CEError("vsg state timeout")
            state = self.query("WT:SOURce:CURRent:STATe?")
            if state == "0":
                return
            elif state in ("1", "4"):
                continue
            elif state == "2":
                raise WT328CEError("vsg state timeout")
            raise WT328CEError(f"vsg state error: {state}")

    def wait_for_vsg_start(self, timeout=5):
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise WT328CEError("vsg state timeout")
            state = self.query("WT:SOURce:CURRent:STATe?")
            if state == "1":
                return
            elif state == "0":
                raise WT328CEError("vsg state done")
            elif state in ("4",):
                continue
            elif state == "2":
                raise WT328CEError("vsg state timeout")
            raise WT328CEError(f"vsg state error: {state}")

    def stop_vsg(self):
        self.write("WT:SOURce:STOP")

    # -----------------------------------------------------
    # Wi-Fi VSG
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # Wi-Fi VSA
    # -----------------------------------------------------
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

    def fetch_wifi_base_result(self, center_freq_hz: float, stream: tuple[int, int] | None = None) -> WifiBaseResult:
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

    # -----------------------------------------------------
    # OFDMA / MU helpers
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # BT / BLE VSG
    # -----------------------------------------------------
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

        if packets == 0:
            self.wait_for_vsg_start(timeout=waiting_timeout_s)
        else:
            self.wait_for_vsg_complete(timeout=waiting_timeout_s)

    # -----------------------------------------------------
    # BT / BLE VSA
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # BT fetch helpers
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # SLE / Wi-SUN like example helpers from provided script
    # -----------------------------------------------------
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
