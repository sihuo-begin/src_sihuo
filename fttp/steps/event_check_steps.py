import os.path
import time
from getpass import fallback_getpass
from math import trunc
from multiprocessing import Process, Event

from yaml import full_load

from src.ui.ask_question import ask_question
from src.libs import global_var as gl
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.cts_fixture import get_fixture_sensor_status
from src.libs.common import *
from src.definition import limits

# from src.libs.ble_driver import init, main, rssi_measure
import numpy as np
from src.libs.mes import routing_check
import xml.etree.ElementTree as ET
import datetime
from src.steps import common_steps


builder = NetworkFrameBuilder()


def overall_test_result(connections, logger, **kwargs):
    logger.info("finalize")
    # for name, conn in connections.items():
    #     conn.close()
    error_code = gl.get_value("error_code")
    if error_code:

        if gl.get_value("event_logs"):
            root_path = os.path.abspath("")
            usage_log_path = os.path.join(root_path, "rawlog")
            if not os.path.exists(usage_log_path):
                os.makedirs(usage_log_path)

            usage_log = os.path.join(usage_log_path, f"usage_raw_{time.strftime('%Y%m%d')}.csv")
            log_exist = True
            if not os.path.exists(usage_log):
                log_exist = False
            with open(usage_log, "a+") as f:
                if not log_exist:
                    f.write("sn,start_reason,heating_duration,stop_reason,pause_duration\n")
                for log in gl.get_value("event_logs"):
                    f.write(
                        f'{gl.get_value("codenticode")},{log["startReason"]},{log["heatingDuration"]},{log["stopReason"]},{log["pauseDuration"]}\n'
                    )

    return common_steps.overall_test_result(connections, logger, **kwargs)
    #     return False, error_code
    # return True, "0"


# def dummy_long_test(connections, logger, **kwargs):
#     import time
#     logger.info("Begin long dummy test...")
#     for i in range(3):
#         time.sleep(1)
#         logger.info(f"Dummy test step {i+1}")
#     return True, "OK"

def start_test(connections, logger, **kwargs):
    logger.info("start_test")
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    gl.set_value("pn", cells.get("pid")[2:])

    for i in range(20):
        answer = ask_question("Please Scan barcode")
        if answer:
            rootDir = os.path.abspath('')
            logDir = os.path.join(rootDir, "log")
            if not os.path.exists(logDir):
                os.makedirs(logDir)
            logPath = os.path.join(logDir, f"log_{time.strftime('%Y%m%d')}.log")
            with open(logPath,"a+") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{answer}\n")
            if " " in answer and len(answer) == 17:
                gl.set_value("dusn", answer)
                gl.set_value("codentify", answer)
                gl.set_value("codentify_code", answer)
                break
        time.sleep(1)
    return True, ""


def start_test_shake_hands(connections, logger, **kwargs):
    logger.info("start_test")
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]

    user_config = cells.get("user_config")
    SNPath = user_config.get("SNPath")
    SNResult = user_config.get("SNResult")
    SNCopy = user_config.get("SNCopy")
    stop_event = gl.get_value("stop_event")

    gl.set_value("pn", cells.get("pid")[2:])

    for i in range(20):
        answer = ask_question("Please Scan barcode")
        if answer:
            rootDir = os.path.abspath('')
            logDir = os.path.join(rootDir, "log")
            if not os.path.exists(logDir):
                os.makedirs(logDir)
            logPath = os.path.join(logDir, f"log_{time.strftime('%Y%m%d')}.log")
            with open(logPath, "a+") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{answer}\n")
            if " " in answer and len(answer) == 17:
                gl.set_value("dusn", answer)
                gl.set_value("codentify", answer)
                gl.set_value("codentify_code", answer)

                shake_hand_file = os.path.join(SNPath, f"{answer}.txt")
                with open(shake_hand_file, "w") as f:
                    pass
                sn_result_start = datetime.datetime.now()
                while not stop_event.is_set():
                    delta_time = datetime.datetime.now() - sn_result_start
                    if delta_time.total_seconds() > 30:
                        return False, "MESAssistant Error"
                    shake_hand_files = os.listdir(SNResult)
                    logger.debug(f"{SNResult},{shake_hand_files}")
                    for shake_file in shake_hand_files:
                        logger.debug(f"{shake_file},{answer},{shake_file.startswith(answer)}")
                        shakes = shake_file.split(".")[0].split('_')
                        if shake_file.startswith(answer):
                            if shakes[1] == "0000":
                                gl.set_value("X_PAUSE", True)
                            else:
                                gl.set_value("X_PAUSE", False)
                            if shakes[-1].endswith("FAIL"):
                                return False, "Routing Error"
                            else:
                                return True, ""
                    time.sleep(0.1)
        time.sleep(1)
    return True, ""


def get_debug_info(info):
    # info = "<UnitInfo><UnitData><Name>BatterySN</Name><Value>S049101010017752504039</Value></UnitData><UnitData><Name>SerialNumber</Name><Value>T4H4 V7A QEF 6S6U</Value></UnitData><UnitData><Name>ReadUID</Name><Value></Value></UnitData><UnitData><Name>DeviceFirmwareVersion</Name><Value></Value></UnitData><UnitData><Name>CoilModule</Name><Value>ECS250619003566IM90307003103CC</Value></UnitData><UnitData><Name>EngineDUSN</Name><Value>00290063000430000003</Value></UnitData><UnitData><Name>ControlDUSN</Name><Value>0041007A000400000065</Value></UnitData><UnitData><Name>EventCheck</Name><Value>0</Value></UnitData><UnitData><Name>EventCheckFailTimes</Name><Value>0</Value></UnitData></UnitInfo>"
    root = ET.fromstring(info)
    for unitdata in root.findall("UnitData"):
        if unitdata.find("Name").text == "EventCheckFailTimes":
            if unitdata.find("Value").text.strip() == "0":
                gl.set_value("debug", False)
            else:
                gl.set_value("debug", True)
        if unitdata.find("Name").text == "PAUSE":
            if unitdata.find("Value").text.strip() == "0":
                gl.set_value("X_PAUSE", False)
            else:
                gl.set_value("X_PAUSE", True)



def scan_codentify(connections, logger, **kwargs):
    codentify = gl.get_value("dusn")

    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    flexflow = user_config.get("flexflow")
    TBBUID = user_config.get("TBBUID")

    if " " in codentify and len(codentify) == 17:
        if flexflow:
            logger.debug(flexflow)
            status, info = routing_check(codentify, TBBUID)
            if status:
                get_debug_info(info)
                return True, codentify
            else:
                gl.set_value("Error_Code", "R001")
                return False, "R001"

        return True, codentify
    else:
        return False, codentify


def read_codentify(connections, logger, **kwargs):

    connection = connections.get("serial_dut")
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
    )

    response = None

    for i in range(15):
        response = connection.send_receive(cmd_codentify, timeout=1)
        if response[5] == 0x88 and response[6] == 0x03:
            break
        time.sleep(1)
    codentifyCode = response[7:21].decode("utf-8").replace(" ", "")

    status = False
    if gl.get_value("codentify").replace(" ", "").upper() == codentifyCode.upper():
        status = True
    # gl.set_value("dusn", gl.get_value("codenticode"))
    if not status:
        gl.set_value("error_code", kwargs.get("error_code"))
    return status, codentifyCode


def read_dusn_control(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_dusn_control = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
    )
    response = None
    dusns = []
    dusn = ""
    for i in range(15):
        try:
            response = connection.send_receive(cmd_dusn_control, timeout=1)
            if response[5] == 0x89 and response[6] == 0x00:
                dusns = [f"{byte:02x}" for byte in response]
                dusn = f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}".upper()
                break
        except Exception as ex:
            print(str(ex))
        time.sleep(1)



    if len(dusns) > 12 and len(dusn) > 0:
        gl.set_value("platform", f"{dusns[8]}{dusns[7]}")
        gl.set_value("site_code", f"{dusns[12]}{dusns[11]}")
        gl.set_value("dusn", dusn[-8:])
        gl.set_value("product_code", f"{dusns[10]}{dusns[9]}")

        gl.set_value("codenticode", dusn)
        limit = kwargs.get("limit").get("min")[:8]
        if not dusn.lower().startswith(limit.lower()):
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, dusn
    else:
        return False, dusn
    return True, dusn


def read_dusn_engine(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_dusn_engine = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
    )
    response = None
    dusns = []
    dusn = ""
    for i in range(15):
        response = connection.send_receive(cmd_dusn_engine, timeout=1)
        if response[5] == 0x89 and response[6] == 0x00:
            dusns = [f"{byte:02x}" for byte in response]
            dusn = (
                f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}".upper()
            )
            break
        time.sleep(1)

    if len(dusns) > 12 and len(dusn) > 0:
        limit = kwargs.get("limit").get("min")[:8]
        if not dusn.lower().startswith(limit.lower()):
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, dusn
    else:
        return False, dusn
    return True, dusn


def read_fw_control(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_fw = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x00
    )

    response = None
    fw = ""
    for i in range(5):
        response = connection.send_receive(cmd_fw, timeout=1)
        if response[5] == 0x88 and response[6] == 0x00:
            fw = f"{response[9]}.{response[10]}.{response[11]}"
            break

    lsl = kwargs.get("limit").get("min")
    usl = kwargs.get("limit").get("max")

    if fw == lsl and fw == usl:
        return True, fw
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, fw


def read_fw_engine(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_fw = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x00
    )
    response = None
    fw = ""
    for i in range(5):
        response = connection.send_receive(cmd_fw, timeout=1)
        if response[5] == 0x88 and response[6] == 0x00:
            fw = f"{response[9]}.{response[10]}.{response[11]}"
            break

    lsl = kwargs.get("limit").get("min")
    usl = kwargs.get("limit").get("max")
    if fw == lsl and fw == usl:
        return True, fw
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, fw


def read_event_logs(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd = bytes([0xC0, 0x10, 0x02, 0x01, 0x01, 0x75, 0xD6])
    response = connection.send_receive(cmd, timeout=1)
    rows = int.from_bytes(response[16:19], "little")
    cmd = [0xC0, 0x10, 0x07, 0x01, 0x02, 0x00, 0x02]
    event_logs = []
    for i in range(rows):
        for j in range(5):
            try:
                ibytes = list(i.to_bytes(3, "little"))
                cmd_out = cmd.copy()
                cmd_out.extend(ibytes)
                cmd_out.extend(builder.crc16(bytes(cmd_out[1:])))
                response = connection.send_receive(bytes(cmd_out), timeout=1)
                usage = list(response[23:])
                startReason = (usage[34] & 0xE0) >> 5
                heatingDuration = 2 * usage[55]
                pauseDuration = 3 * usage[56]
                stopReason = usage[61]
                puffCount = usage[110]
                if startReason == 2 and heatingDuration == 0 and stopReason == 5:
                    continue
                event_logs.append(
                    {
                        "startReason": startReason,
                        "heatingDuration": heatingDuration,
                        "pauseDuration": pauseDuration,
                        "stopReason": stopReason,
                        "puffCount": puffCount,
                    }
                )
                break
            except Exception as e:
                logger.error(f"error: {e}")
            time.sleep(2)

    stop_filters = [3, 9, 12]

    event_logs_valid = []
    total_logs = []
    pause_logs = []
    debug = False
    status = True
    error = "PASS"
    puffCount = 0
    rawPuffCount = 0
    puffCountList = []
    for log in event_logs:
        if log["startReason"] == 1:
            if log["heatingDuration"] == 366:
                if log["stopReason"] == 2:
                    event_logs_valid.append(log)
                    total_logs.append(log)
                elif log["stopReason"] in stop_filters:
                    total_logs.append(log)
                else:
                    status = False
                    error = f"E003,Stop Reason Fail,{log['stopReason']},2,2"
                    # break
            else:
                if log["stopReason"] in stop_filters:
                    total_logs.append(log)
                elif log["stopReason"] == 5 and log["heatingDuration"] == 0:
                    pass
                else:
                    status = False
                    error = f"E003,Stop Reason Fail,{log['stopReason']},2,2"
                    # break
        else:
            status = False
            error = f"E002,Start Reason Fail,{log['startReason']},1,1"
            # break
        if log["heatingDuration"] != 366 and not log["stopReason"] in stop_filters and status:
            if log["stopReason"] == 5 and log["heatingDuration"] == 0:
                pass
            else:
                status = False
                error = f"E004,Heat duration Fail,{log['heatingDuration']},366,366"
            # break
        if log["pauseDuration"] > 0:
            pause_logs.append(log)
    puffLogs = event_logs_valid
    if debug:
        puffLogs = event_logs_valid[-8:]
    for log in puffLogs:
        puffCount = puffCount + log["puffCount"]
    lsl = 8
    usl = 12
    if debug:
        usl = 20
    if len(event_logs_valid) >= lsl:
        if len(event_logs_valid) > usl:
            status = False
            error = f"E001,Heat count Fail,{len(event_logs_valid)},{lsl},{usl}"
    else:
        status = False
        error = f"E001,Heat count Fail,{len(event_logs_valid)},{lsl},{usl}"
    if status and len(pause_logs) == 0 and (not gl.get_value("X_PAUSE")):
        status = False
        error = f"E005,Pause count Fail,{len(pause_logs)},1,99999"
    if status and puffCount > 6:
        status = False
        error = f"E009,Puff count fail,{puffCount},0,6"

    for log in event_logs_valid:
        puffCountList.append(log["puffCount"])
        if log["puffCount"] > 2:
            status = False
            rawPuffCount = log["puffCount"]
            error = f"E008,Puff count fail,{log['puffCount']},0,2"
            break
    if status:
        rawPuffCount = max(puffCountList)
    error_code = error.split(",")[0]
    if not status:
        gl.set_value("error_code", error_code)
    gl.set_value("error", error)
    gl.set_value("debug", debug)
    gl.set_value("autostart_count", len(event_logs_valid))
    gl.set_value("pause_logs", len(pause_logs))
    gl.set_value("event_logs", event_logs)
    gl.set_value("puff_count", puffCount)
    gl.set_value("raw_puff_count", rawPuffCount)

    event_log_name = f"Unit_Log_{time.strftime('%Y-%m-%d')}.csv"
    log_path = os.path.join(os.path.abspath(''), "log")
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    first_row = False
    log_full_path = os.path.join(log_path, event_log_name)
    if not os.path.exists(log_full_path):
        first_row = True
    with open(log_full_path,"a+") as f:
        if first_row:
            f.write(f"SN,event_count,start_reason, heating_duration, pause_duration, stop_reason, raw_puff_count, puff_count\n")
        f.write(f"{gl.get_value('codentify_code')},{gl.get_value('autostart_count')},{check_start_reason(connections, logger, **kwargs)[-1]},{check_heating_duration(connections, logger, **kwargs)[-1]},{check_pause_duration(connections, logger, **kwargs)[-1]},{check_stop_reason(connections, logger, **kwargs)[-1]},{gl.get_value('raw_puff_count')},{gl.get_value('puff_count')}\n")

    return True, "PASS"
    # return status, error.split(",")[0]


def check_autostart_count(connections, logger, **kwargs):
    error = gl.get_value("error")
    autostart_count = gl.get_value("autostart_count")
    if error == "PASS":
        return True, str(autostart_count)
    else:
        errors = error.split(",")
        if errors[0] == "E001":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, str(autostart_count)
        else:
            return True, str(autostart_count)


def check_start_reason(connections, logger, **kwargs):
    error = gl.get_value("error")
    if error == "PASS":
        return True, "1"
    else:
        errors = error.split(",")
        if errors[0] == "E002":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, errors[2]
        else:
            return True, str(1)


def check_stop_reason(connections, logger, **kwargs):
    error = gl.get_value("error")
    if error == "PASS":
        return True, str(2)
    else:
        errors = error.split(",")
        if errors[0] == "E003":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, errors[2]
        else:
            return True, str(2)


def check_heating_duration(connections, logger, **kwargs):
    error = gl.get_value("error")
    if error == "PASS":
        return True, "366"
    else:
        errors = error.split(",")
        if errors[0] == "E004":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, errors[2]
        else:
            return True, "366"


def check_pause_duration(connections, logger, **kwargs):
    error = gl.get_value("error")
    pause_count = gl.get_value("pause_logs")
    if error == "PASS":
        return True, str(pause_count)
    else:
        errors = error.split(",")
        if errors[0] == "E005":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "0"
        else:
            return True, str(pause_count)

def check_raw_puff_count(connections, logger, **kwargs):
    error = gl.get_value("error")
    raw_puff_count = gl.get_value("raw_puff_count")
    if error == "PASS":
        return True, str(raw_puff_count)
    else:
        errors = error.split(",")
        if errors[0] == "E008":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, f"{raw_puff_count}"
        else:
            return True, str(raw_puff_count)
def check_puff_count(connections, logger, **kwargs):
    error = gl.get_value("error")
    puff_count = gl.get_value("puff_count")
    if error == "PASS":
        return True, str(puff_count)
    else:
        errors = error.split(",")
        if errors[0] == "E009":
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, f"{puff_count}"
        else:
            return True, str(puff_count)


def write_codentify_code_control(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    codentify = kwargs.get("codentify").replace(" ", "")
    codentify_write_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=37,
        count=7,
        value=codentify,
    )
    response = connection.send_receive(codentify_write_frame, timeout=1)
    logger.debug(response)
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
    )
    response = None

    for i in range(3):
        response = connection.send_receive(cmd_codentify, timeout=1)
        logger.debug(response)
        if response[5] == 0x88 and response[6] == 0x03:
            break
        time.sleep(0.3)
    codentify_read = response[7:21].decode("utf-8")
    if codentify == codentify_read:
        return True
    return False


def read_station(connections, logger, **kwargs):
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    if TBBUID:
        return True, TBBUID
    return False, TBBUID
