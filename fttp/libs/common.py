import sys
import os
from binascii import unhexlify
from src.libs.serial_tester import SerialTester
from src.libs.cmd_generator import NetworkFrameBuilder
import time
from src.libs import global_var as gl
import configparser
from pathlib import Path
from typing import Optional


def parse_field(data: bytes, to_int=True):
    if to_int:
        return int.from_bytes(data, "little")
    else:
        return data.hex()


def fixture_input(**kwargs):
    tester_port = kwargs.get("tester_port")
    result = ""
    if tester_port:
        tester = SerialTester(port=tester_port)
        for _ in range(300):
            fixture_pass = tester.fixture_detect_input(kwargs.get("pass"))
            fixture_fail = tester.fixture_detect_input(kwargs.get("fail"))
            result = f"{fixture_pass},{fixture_fail}"
            if fixture_pass or fixture_fail:
                break
            time.sleep(0.05)
    return result


def verify_crc(logger, data: bytes, crc_type=8, connection='uart'):
    builder = NetworkFrameBuilder()
    LENGTH_CODE_MAP = {0: 0, 1: 4, 2: 14, 3: 24}
    if connection == 'uart' and crc_type == 8:
        message_head = data[1]
        message_payload_len = LENGTH_CODE_MAP[(message_head >> 2) & 0b11]
        logger.debug(f"message_payload_len:{message_payload_len}")
        acturl_data = data[:message_payload_len + 4]
        crc = builder.crc8(acturl_data[1:message_payload_len + 3])
        logger.debug(f"crc:{crc}")
        if crc == acturl_data[-1]:
            logger.debug("passed")
            return True
        else:
            return False
    elif connection == 'hid' and crc_type == 8:
        acturl_data = data[:data[1] + 2]
        network_payload = bytes(data[3:data[1] + 1])
        crc = builder.crc8(network_payload)
        logger.debug(f"crc:{crc}")
        if crc == acturl_data[-1]:
            logger.debug("passed")
            return True
        else:
            return False
    else:
        logger.error("Unkwon connection type and crc type!!")
        return False


def fixture_start():
    config = gl.get_value("layout_config")
    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")
    stop_event = gl.get_value("stop_event")
    if tester_port:
        tester = SerialTester(port=tester_port)
        while not stop_event.is_set():
            fixture_start_status = tester.fixture_detect_input(fixture_io.get("start"))
            if fixture_start_status:
                break
            time.sleep(0.05)


def to_hex(val, nbytes):
    return f"0x{val:0{nbytes*2}x}"


def to_hex_without_head(val, nbytes):
    return f"{val:0{nbytes*2}x}"


def hello():
    time.sleep(2)
    return True


def hexstr_to_bytes(s):
    return bytes(int(x, 16) for x in s.replace("0x", "").replace(",", " ").split())


def verify_limit(value, limit_def, name=None):
    """
    value:
    limit_def: limit
    name:
    return: (ok: bool, msg: str)
    """
    # 支持元组/列表区间
    if isinstance(limit_def, tuple) and len(limit_def) == 2:
        low, high = limit_def
        if low <= value <= high:
            return True, f"{name or ''}={value} in range[{low}, {high}]"
        else:
            return False, f"{name or ''}={value} out of range[{low}, {high}]"
    # 支持dict格式
    if isinstance(limit_def, dict):
        # min/max
        low = limit_def.get("min", limit_def.get("low", None))
        high = limit_def.get("max", limit_def.get("high", None))
        if low is not None and value < low:
            return False, f"{name or ''}={value} lower min{low}"
        if high is not None and value > high:
            return False, f"{name or ''}={value} higher max{high}"
        if "enum" in limit_def:
            if value not in limit_def["enum"]:
                return False, f"{name or ''}={value} not in {limit_def['enum']}"
        if "range" in limit_def:
            low, high = limit_def["range"]
            if not (low <= value <= high):
                return False, f"{name or ''}={value} out of [{low}, {high}]"
        return True, f"{name or ''}={value} pass"

    if isinstance(limit_def, (int, float, str)):
        if value == limit_def:
            return True, f"{name or ''}={value} equal{limit_def}"
        else:
            return False, f"{name or ''}={value} != {limit_def}"
    if isinstance(limit_def, list):
        if value in limit_def:
            return True, f"{name or ''}={value} in list {limit_def}"
        else:
            return False, f"{name or ''}={value} not in list{limit_def}"
    return False, f"{name or ''}={value} unkown format:{limit_def}"


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def _candidates_for_src_config() -> list[Path]:
    """
    返回按优先级排列的候选路径，目标都是 src/config/version.ini。
    1) PyInstaller 解包目录下的 src/config/version.ini
    2) 可执行文件所在目录的 src/config/version.ini
    3) 本模块所在包的 src/config/version.ini（开发模式）
    4) 当前工作目录下的 src/config/version.ini
    """
    candidates: list[Path] = []

    # 1) PyInstaller 解包目录（onefile/onedir）
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None
        if meipass:
            candidates.append(meipass / "src" / "config" / "version.ini")
            candidates.append(meipass / "version.ini")
    # 2) 可执行文件所在目录（当把数据放在 exe 同目录或部署在同级目录时）
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "src" / "config" / "version.ini")
        candidates.append(exe_dir / "version.ini")
    except Exception:
        pass

    # 3) 模块自身目录（开发/安装为包时）
    this_module_dir = Path(__file__).resolve().parent
    candidates.append(this_module_dir / "version.ini")  # src/config/version.ini when module located there
    # 如果运行时 module 位置不同，尝试以模块父目录为基准查找项目结构
    candidates.append(this_module_dir.parents[0] / "src" / "config" / "version.ini")
    candidates.append(this_module_dir.parents[1] / "src" / "config" / "version.ini")

    # 4) 当前工作目录下的候选
    cwd = Path.cwd()
    candidates.append(cwd / "src" / "config" / "version.ini")
    candidates.append(cwd / "version.ini")

    return candidates


def get_version_ini_path() -> Optional[Path]:
    """
    返回第一个存在的 src/config/version.ini 的绝对 Path；找不到返回 None。
    """
    for p in _candidates_for_src_config():
        try:
            if p and p.exists():
                return p
        except Exception:
            continue
    return None


def read_version() -> dict:
    """
    读取 version.ini 并返回 {"commit": "...", "build_time": "..."} 的字典。
    找不到文件或解析失败则返回合理的默认值。
    """
    p = get_version_ini_path()
    result = {"commit": "unknown", "build_time": ""}
    if p is None:
        return result

    cfg = configparser.ConfigParser()
    try:
        cfg.read(p, encoding="utf-8")
        result["commit"] = cfg.get("version", "commit", fallback=result["commit"])
        result["build_time"] = cfg.get("version", "build_time", fallback=result["build_time"])
    except Exception:
        # 保守回退，不抛出异常
        pass
    return result

#
# if __name__ == "__main__":
#     s = '0x10 0x20 0x3A 0x50 0xA0 0x70 0x80 0x90 0x1A 0x1B'
#
#     crc8Add("080e10a700")
#
#     data = hexstr_to_bytes(s)
#
#     device = DeviceInfo(data)
#     data = device.product_code_hex
#     print(data)
