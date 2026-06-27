"""
WT328CEDriver - 高层协调器，负责建立仪器连接并组合 WiFi/BT/SLE 子驱动。
外部通过该类获取 .wifi / .bt / .sle 对象来调用对应功能。
"""
from __future__ import annotations

import pyvisa
from typing import Optional
from src.libs import global_var as gl

from src.libs.equipments.wt328ce.inst_base import BaseRFDevice
from src.libs.equipments.wt328ce.wifi import WifiRFDevice
from src.libs.equipments.wt328ce.bt import BtRFDevice
from src.libs.equipments.wt328ce.sle import SleRFDevice, SleBasicResult


class WT328CEDriver:
    def __init__(self, logger=None, timeout_ms: int = 10000):
        self.ip = gl.get_value("ip", "10.1.1.100")
        self.logger = logger
        self.timeout_ms = timeout_ms

        self.rm: Optional[pyvisa.ResourceManager] = None
        self.inst = None

        # 子设备（在 connect 后实例化）`
        self.wifi: Optional[WifiRFDevice] = None
        self.bt: Optional[BtRFDevice] = None
        self.sle: Optional[SleRFDevice] = None

    def _log(self, msg: str):
        if self.logger:
            self.logger.info(msg)

    def connect(self) -> str:
        self.rm = pyvisa.ResourceManager()
        # 打开 socket resource
        self.inst = self.rm.open_resource(f"TCPIP0::{self.ip}::5025::SOCKET")
        self.inst.timeout = self.timeout_ms
        self.inst.read_termination = "\r\n"
        idn = self.inst.query("*IDN?")
        # set response mode same as original
        try:
            self.inst.write("WT:SYSTem:CMD:RESPonse 0")
        except Exception:
            pass
        self._log(f"[WT328CE] connected: {idn.strip()}")

        # instantiate device facade objects using the same instrument
        self.wifi = WifiRFDevice(self.inst, self.logger)
        self.bt = BtRFDevice(self.inst, self.logger)
        self.sle = SleRFDevice(self.inst, self.logger)

        return idn.strip()

    def close(self):
        if self.inst:
            try:
                self.inst.close()
            except Exception:
                pass
            self.inst = None
        if self.rm:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

    # convenience wrappers that call underlying instrument
    def idn(self) -> str:
        if not self.inst:
            raise RuntimeError("not connected")
        return self.inst.query("*IDN?").strip()

    def write(self, cmd: str):
        if not self.inst:
            raise RuntimeError("not connected")
        self._log("WT328CE write: %s" % cmd)
        return self.inst.write(cmd)

    def query(self, cmd: str) -> str:
        if not self.inst:
            raise RuntimeError("not connected")
        self._log("WT328CE query: %s" % cmd)
        return self.inst.query(cmd)

    def query_ascii_values(self, cmd: str):
        if not self.inst:
            raise RuntimeError("not connected")
        self._log("WT328CE query_ascii_values: %s" % cmd)
        return self.inst.query_ascii_values(cmd)

    def check_error(self, func: str):
        if not self.inst:
            raise RuntimeError("not connected")
        errinfo = self.inst.query(":SYSTem:ERRor?")
        if '0,"No error"' not in errinfo:
            raise RuntimeError(f"{func} error: {errinfo}")

    # helper: expose base waveform upload via top-level driver too
    def upload_vsg_waveform(self, file_path: str) -> str:
        if not self.wifi:
            raise RuntimeError("not connected")
        # use Wifi device which inherits BaseRFDevice that provides upload method
        return self.wifi.upload_vsg_waveform(file_path)


# if __name__ == "__main__":
#     from rf_driver import WT328CEDriver
#
#     driver = WT328CEDriver("192.168.0.10", logger=my_logger, timeout_ms=15000)
#     idn = driver.connect()
#     print("connected:", idn)
#
#     # WiFi 操作
#     wifi_dev = driver.wifi
#     wifi_dev.configure_wifi_vsa(rf_ports=[1], freq_mhz=2412, sample_rate_hz=240e6, demod=1)
#     res = wifi_dev.measure_wifi_power_dbm(rf_port=0, freq_mhz=2412, sample_rate_hz=240e6, demod=1)
#     print("power:", res)
#
#     # BT 操作
#     bt_dev = driver.bt
#     bt_dev.configure_bt_vsa(freq_mhz=2402, max_power_dbm=0.0, rf_port=0, pathloss_db=0.0, demod=9, phy=1)
#     bt_summary = bt_dev.measure_bt_tx_summary(freq_mhz=2402, max_power_dbm=0.0, rf_port=0, pathloss_db=0.0, demod=9,
#                                               phy=1, payload_type=0)
#     print(bt_summary)
#
#     driver.close()