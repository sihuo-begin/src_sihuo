"""
BaseRFDevice - 基础设备类，封装通用 SCPI I/O 操作。
子设备( WiFi/BT/SLE ) 继承该类并使用 self.write/self.query/self.query_ascii_values 等方法。
"""
from __future__ import annotations

import os
import time
from typing import List, Optional

from pyvisa import constants


class WT328CEError(Exception):
    pass


class BaseRFDevice:
    def __init__(self, inst, logger=None):
        """
        inst: 已打开的 pyvisa instrument/resource
        logger: 可选 logger
        """
        self.inst = inst
        self.logger = logger

    # -------------------------
    # logging / io wrappers
    # -------------------------
    def _log(self, msg: str):
        if self.logger:
            self.logger.info(msg)

    def write(self, cmd: str):
        self._log(f"[WT328CE][WRITE] {cmd}")
        return self.inst.write(cmd)

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

    # -------------------------
    # waveform helpers
    # -------------------------
    def upload_vsg_waveform(self, file_path: str) -> str:
        """
        Upload waveform to source (SOURce:CONFigure:SAVE:WAVE ...).
        Uses write_binary_values on underlying instrument.
        """
        file_name = os.path.basename(file_path)
        # ensure termination char is enabled if instrument supports set_visa_attribute
        try:
            self.inst.set_visa_attribute(constants.VI_ATTR_TERMCHAR_EN, constants.VI_TRUE)
        except Exception:
            # not critical; some pyvisa backends might not expose set_visa_attribute
            pass

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

    def load_capture_wave_to_vsa(self, demod: int, local_wave: str, freq_mhz: int = 2412,
                                rf_port: int = 2, sample_rate_hz: float = 240e6) -> str:
        """
        Generic capture load (kept for compatibility). Subclasses may override/build on it.
        """
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
