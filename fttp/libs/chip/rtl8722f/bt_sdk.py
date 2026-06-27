from __future__ import annotations
import os
import sys
from typing import Optional
import ctypes
from ctypes import (
    Structure,
    POINTER,
    WINFUNCTYPE,
    c_int,
    c_uint,
    c_ulong,
    c_ubyte,
    c_ulonglong,
    c_void_p,
    byref,
)
from pathlib import Path


MAX_TXGAIN_TABLE_SIZE = 7
MAX_TXDAC_TABLE_SIZE = 5
MAX_USERAWDATA_SIZE = 1050
MAX_DATA_LEN = 20
REPORT_ALL = 0
REPORT_LE_RX = 11
STANDARD_MODULATION_INDEX = 0
STABLE_MODULATION_INDEX = 1


# -----------------------------
# C struct bindings
# -----------------------------

class BASE_INTERFACE_MODULE(Structure):
    pass


BASE_FP_OPEN = WINFUNCTYPE(c_int, POINTER(BASE_INTERFACE_MODULE))
BASE_FP_SEND = WINFUNCTYPE(c_int, POINTER(BASE_INTERFACE_MODULE), POINTER(c_ubyte), c_ulong)
BASE_FP_RECV = WINFUNCTYPE(c_int, POINTER(BASE_INTERFACE_MODULE), POINTER(c_ubyte), c_ulong, POINTER(c_ulong))
BASE_FP_CLOSE = WINFUNCTYPE(c_int, POINTER(BASE_INTERFACE_MODULE))
BASE_FP_WAIT_MS = WINFUNCTYPE(None, POINTER(BASE_INTERFACE_MODULE), c_ulong)
BASE_FP_SET_USER_DEFINED_DATA_POINTER = WINFUNCTYPE(None, POINTER(BASE_INTERFACE_MODULE), c_int)
BASE_FP_GET_USER_DEFINED_DATA_POINTER = WINFUNCTYPE(None, POINTER(BASE_INTERFACE_MODULE), POINTER(c_int))


BASE_INTERFACE_MODULE._fields_ = [
    ("Open", BASE_FP_OPEN),
    ("Send", BASE_FP_SEND),
    ("Recv", BASE_FP_RECV),
    ("Close", BASE_FP_CLOSE),
    ("WaitMs", BASE_FP_WAIT_MS),
    ("SetUserDefinedDataPointer", BASE_FP_SET_USER_DEFINED_DATA_POINTER),
    ("GetUserDefinedDataPointer", BASE_FP_GET_USER_DEFINED_DATA_POINTER),
    ("InterfaceType", c_ubyte),
    ("UserDefinedData", c_ulong),
    ("PortNo", c_ubyte),
    ("Baudrate", c_ulong),
    ("bUartProtocol", c_ubyte),
    ("pData", c_ubyte * MAX_DATA_LEN),
]


class BT_CHIPINFO(Structure):
    _fields_ = [
        ("HCI_Version", c_uint),
        ("HCI_SubVersion", c_uint),
        ("LMP_Version", c_uint),
        ("LMP_SubVersion", c_uint),
        ("ChipType", c_uint),
        ("Version", c_uint),
        ("Is_After_PatchCode", c_int),
    ]


class BT_PARAMETER(Structure):
    _fields_ = [
        ("ParameterIndex", c_ulong),
        ("mPGRawData", c_ubyte * MAX_USERAWDATA_SIZE),
        ("mParamData", c_ubyte * MAX_USERAWDATA_SIZE),
        ("mChannelNumber", c_ubyte),
        ("mPacketType", c_ulong),
        ("mTxGainIndex", c_ubyte),
        ("mTxGainValue", c_ubyte),
        ("mTxPacketCount", c_ulong),
        ("mPayloadType", c_ulong),
        ("mPacketHeader", c_ulong),
        ("mWhiteningCoeffValue", c_ubyte),
        ("mTxDAC", c_ubyte),
        ("mHitTarget", c_ulonglong),
        ("TXGainTable", c_ubyte * MAX_TXGAIN_TABLE_SIZE),
        ("TXDACTable", c_ubyte * MAX_TXDAC_TABLE_SIZE),
        ("bHoppingFixChannel", c_ubyte),
        ("Rtl8761Xtal", c_ulong),
        ("ExeMode", c_ubyte),
        ("PHY", c_ubyte),
        ("ModulationIndex", c_ubyte),
        ("mTxPower", c_ubyte),
        ("mPowerType", c_ubyte),
        ("mMPVersion", c_int),
    ]


class BT_DEVICE_REPORT(Structure):
    _fields_ = [
        ("TotalTXBits", c_ulong),
        ("TotalTxCounts", c_ulong),
        ("RXRecvPktCnts", c_ulong),
        ("TotalRXBits", c_ulong),
        ("TotalRxCounts", c_ulong),
        ("TotalRxErrorBits", c_ulong),
        ("RxRssi", c_int),
        ("ber", ctypes.c_float),
        ("Cfo", ctypes.c_float),
        ("CurrTXGainTable", c_ubyte * MAX_TXGAIN_TABLE_SIZE),
        ("CurrTXDACTable", c_ubyte * MAX_TXDAC_TABLE_SIZE),
        ("CurrThermalValue", c_ubyte),
        ("CurrRtl8761Xtal", c_ulong),
        ("CurrStage", c_ubyte),
        ("pBTInfo", POINTER(BT_CHIPINFO)),
        ("BTInfoMemory", BT_CHIPINFO),
        ("ReportData", c_ubyte * MAX_USERAWDATA_SIZE),
    ]


class BASE_BTMPDLL_MODULE(Structure):
    pass


BT_DLL_MODULE_FP_ACTION_REPORT = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_int, POINTER(BT_DEVICE_REPORT))
BT_DLL_MODULE_FP_UPDATA_PARAMETER = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), POINTER(BT_PARAMETER))
BT_DLL_MODULE_FP_ACTION_CONTROLEXCUTE = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE))
BT_DLL_MODULE_FP_ACTION_DLFW = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_void_p, c_int, c_int)

BT_DLL_MODULE_FP_SET_MD_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ubyte, c_ubyte, c_ubyte, c_ulong)
BT_DLL_MODULE_FP_GET_MD_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ubyte, c_ubyte, c_ubyte, POINTER(c_ulong))
BT_DLL_MODULE_FP_SET_RF_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ubyte, c_ubyte, c_ubyte, c_ulong)
BT_DLL_MODULE_FP_GET_RF_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ubyte, c_ubyte, c_ubyte, POINTER(c_ulong))
BT_DLL_MODULE_FP_SEND_HCICOMMANDWITHEVENT = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_uint, c_ubyte, POINTER(c_ubyte), c_ubyte, POINTER(c_ubyte))
BT_DLL_MODULE_FP_RECV_ANYEVENT = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), POINTER(c_ubyte))
BT_DLL_MODULE_FP_SET_SYS_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ulong, c_ubyte, c_ubyte, c_ulong)
BT_DLL_MODULE_FP_GET_SYS_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_ulong, c_ubyte, c_ubyte, POINTER(c_ulong))
BT_DLL_MODULE_FP_SET_BB_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_int, c_ulong, c_ubyte, c_ubyte, c_ulong)
BT_DLL_MODULE_FP_GET_BB_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_int, c_ulong, c_ubyte, c_ubyte, POINTER(c_ulong))
BT_DLL_MODULE_FP_SET_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_int, c_int, c_ulong, c_ubyte, c_ubyte, c_ulong)
BT_DLL_MODULE_FP_GET_REG_MASK_BITS = WINFUNCTYPE(c_int, POINTER(BASE_BTMPDLL_MODULE), c_int, c_int, c_ulong, c_ubyte, c_ubyte, POINTER(c_ulong))


BASE_BTMPDLL_MODULE._fields_ = [
    ("UpDataParameter", BT_DLL_MODULE_FP_UPDATA_PARAMETER),
    ("ActionControlExcute", BT_DLL_MODULE_FP_ACTION_CONTROLEXCUTE),
    ("ActionReport", BT_DLL_MODULE_FP_ACTION_REPORT),
    ("DownloadPatchCode", BT_DLL_MODULE_FP_ACTION_DLFW),
    ("SetMdRegMaskBits", BT_DLL_MODULE_FP_SET_MD_REG_MASK_BITS),
    ("GetMdRegMaskBits", BT_DLL_MODULE_FP_GET_MD_REG_MASK_BITS),
    ("SetRfRegMaskBits", BT_DLL_MODULE_FP_SET_RF_REG_MASK_BITS),
    ("GetRfRegMaskBits", BT_DLL_MODULE_FP_GET_RF_REG_MASK_BITS),
    ("SetSysRegMaskBits", BT_DLL_MODULE_FP_SET_SYS_REG_MASK_BITS),
    ("GetSysRegMaskBits", BT_DLL_MODULE_FP_GET_SYS_REG_MASK_BITS),
    ("SetBBRegMaskBits", BT_DLL_MODULE_FP_SET_BB_REG_MASK_BITS),
    ("GetBBRegMaskBits", BT_DLL_MODULE_FP_GET_BB_REG_MASK_BITS),
    ("SetRegMaskBits", BT_DLL_MODULE_FP_SET_REG_MASK_BITS),
    ("GetRegMaskBits", BT_DLL_MODULE_FP_GET_REG_MASK_BITS),
    ("SendHciCommandWithEvent", BT_DLL_MODULE_FP_SEND_HCICOMMANDWITHEVENT),
    ("RecvAnyHciEvent", BT_DLL_MODULE_FP_RECV_ANYEVENT),
    ("pBaseInterface", POINTER(BASE_INTERFACE_MODULE)),
    ("BuildStatus", c_int),
]


# -----------------------------
# enums used by current flow
# -----------------------------
TYPE_UART = 1

LE_TX_DUT_TEST_CMD = 22
LE_RX_DUT_TEST_CMD = 23
LE_DUT_TEST_END_CMD = 24
TX_POWER_GAIN_K = 45
TX_POWER_FLATNESS = 46

BT_PKT_LE = 9
BT_PKT_LE_2M = 11
BT_PKT_LE_CODED_S8 = 12
BT_PKT_LE_CODED_S2 = 13

BT_LE_PAYLOAD_TYPE_PRBS9 = 0
BT_LE_PAYLOAD_TYPE_1111_0000 = 1
BT_LE_PAYLOAD_TYPE_1010 = 2

LE5_TX_1M_PHY = 1
LE5_TX_2M_PHY = 2
LE5_TX_CODED_PHY_S8 = 3
LE5_TX_CODED_PHY_S2 = 4

LE5_RX_1M_PHY = 1
LE5_RX_2M_PHY = 2
LE5_RX_CODED_PHY = 3


class RealtekBtSdkError(Exception):
    pass


class RealtekBtSdk:
    def __init__(self, logger, dll_path: Optional[str] = None):
        self.logger = logger
        self.dll = None
        if dll_path:
            final_path = dll_path
        else:
            final_path = self._get_default_dll_path("RtlBluetoothMP.dll")
        if not os.path.exists(final_path):
            raise FileNotFoundError(f"DLL not found: {final_path}")
        self.dll_path = final_path
        self.dll = ctypes.WinDLL(self.dll_path)

        self.interface = BASE_INTERFACE_MODULE()
        self.interface_ptr = POINTER(BASE_INTERFACE_MODULE)()
        self.module = BASE_BTMPDLL_MODULE()

        self._bind_exports()

    def _get_default_dll_path(self, dll_name: str) -> str:
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, dll_name)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, 'source', dll_name)

    def _bind_exports(self):
        self.dll.BTMPAPI_BuildInterfaceRTK.argtypes = [
            POINTER(POINTER(BASE_INTERFACE_MODULE)),
            POINTER(BASE_INTERFACE_MODULE),
            c_uint,
            c_ubyte,
            c_ulong,
            POINTER(c_ubyte),
        ]
        self.dll.BTMPAPI_BuildInterfaceRTK.restype = c_int

        self.dll.BTMPAPI_BuildBluetoothModule.argtypes = [
            POINTER(BASE_BTMPDLL_MODULE),
            POINTER(BASE_INTERFACE_MODULE),
            c_void_p,
            POINTER(c_ubyte),
            POINTER(c_ubyte),
        ]
        self.dll.BTMPAPI_BuildBluetoothModule.restype = c_int

        self.dll.BTMPAPI_Read_MP_Data_From_Device.argtypes = [POINTER(BASE_BTMPDLL_MODULE), c_void_p]
        self.dll.BTMPAPI_Read_MP_Data_From_Device.restype = c_int

        self.dll.BTMPAPI_Write_MP_Data_To_Device.argtypes = [POINTER(BASE_BTMPDLL_MODULE), c_void_p]
        self.dll.BTMPAPI_Write_MP_Data_To_Device.restype = c_int

    def build_interface_rtk(self, port_no: int, baudrate: int, p_data: bytes = b""):
        buf = (c_ubyte * max(1, len(p_data)))(*p_data) if p_data else (c_ubyte * 1)(0)
        rc = self.dll.BTMPAPI_BuildInterfaceRTK(
            byref(self.interface_ptr),
            byref(self.interface),
            TYPE_UART,
            port_no,
            baudrate,
            buf,
        )
        if rc != 0:
            raise RealtekBtSdkError(f"BTMPAPI_BuildInterfaceRTK failed rc={rc}")
        return rc

    def build_module(self):
        tx_gain = (c_ubyte * MAX_TXGAIN_TABLE_SIZE)(*([0] * MAX_TXGAIN_TABLE_SIZE))
        tx_dac = (c_ubyte * MAX_TXDAC_TABLE_SIZE)(*([0] * MAX_TXDAC_TABLE_SIZE))

        rc = self.dll.BTMPAPI_BuildBluetoothModule(
            byref(self.module),
            self.interface_ptr,
            None,
            tx_gain,
            tx_dac,
        )
        if rc != 0:
            raise RealtekBtSdkError(f"BTMPAPI_BuildBluetoothModule failed rc={rc}")
        return rc

    def init(self, port_no: int, baudrate: int):
        self.build_interface_rtk(port_no=port_no, baudrate=baudrate)
        self.build_module()
        return True

    def update_parameter(self, param: BT_PARAMETER):
        rc = self.module.UpDataParameter(byref(self.module), byref(param))
        if rc != 0:
            raise RealtekBtSdkError(f"UpDataParameter failed rc={rc}")
        return rc

    def execute_action(self):
        rc = self.module.ActionControlExcute(byref(self.module))
        if rc != 0:
            raise RealtekBtSdkError(f"ActionControlExcute failed rc={rc}")
        return rc

    def action_report(self, active_item: int) -> BT_DEVICE_REPORT:
        report = BT_DEVICE_REPORT()
        rc = self.module.ActionReport(byref(self.module), active_item, byref(report))
        if rc != 0:
            raise RealtekBtSdkError(f"ActionReport failed rc={rc}, active_item={active_item}")
        return report

    def make_le_tx_param(self, channel: int, phy: int, payload_type: int, packet_type: int):
        p = BT_PARAMETER()
        p.ParameterIndex = LE_TX_DUT_TEST_CMD
        p.mChannelNumber = channel
        p.mPacketType = packet_type
        p.mPayloadType = payload_type
        p.PHY = phy
        return p

    def make_le_rx_param(self, channel: int, phy: int, payload_type: int, packet_type: int):
        p = BT_PARAMETER()
        p.ParameterIndex = LE_RX_DUT_TEST_CMD
        p.mChannelNumber = channel
        p.mPacketType = packet_type
        p.mPayloadType = payload_type
        p.PHY = phy
        return p

    def make_gain_k_param(self, gain_k: int):
        p = BT_PARAMETER()
        p.ParameterIndex = TX_POWER_GAIN_K
        p.mTxGainValue = gain_k & 0xFF
        return p

    def make_flatness_param(self, flatness_bytes: list[int]):
        p = BT_PARAMETER()
        p.ParameterIndex = TX_POWER_FLATNESS
        for i, v in enumerate(flatness_bytes[:MAX_USERAWDATA_SIZE]):
            p.mParamData[i] = v & 0xFF
        return p

    def le_tx_test_start(self, channel: int, phy: int, payload_type: int, packet_type: int):
        param = self.make_le_tx_param(channel, phy, payload_type, packet_type)
        self.update_parameter(param)
        self.execute_action()
        return True

    def le_rx_test_start(self, channel: int, phy: int, payload_type: int, packet_type: int):
        param = self.make_le_rx_param(channel, phy, payload_type, packet_type)
        self.update_parameter(param)
        self.execute_action()
        return True

    def le_test_end(self):
        p = BT_PARAMETER()
        p.ParameterIndex = LE_DUT_TEST_END_CMD
        self.update_parameter(p)
        self.execute_action()
        return True

    def write_gain_k(self, gain_k: int):
        self.update_parameter(self.make_gain_k_param(gain_k))
        self.execute_action()
        return True

    def write_flatness(self, flatness_bytes: list[int]):
        self.update_parameter(self.make_flatness_param(flatness_bytes))
        self.execute_action()
        return True

    def close(self):
        return True


if __name__ == "__main__":
    sdk = RealtekBtSdk()
    sdk.init(port_no=6, baudrate=115200)
    sdk.le_tx_test_start(
        channel=19,
        phy=LE5_TX_1M_PHY,
        payload_type=BT_LE_PAYLOAD_TYPE_PRBS9,
        packet_type=BT_PKT_LE,
    )

    print("LE TX test started")
