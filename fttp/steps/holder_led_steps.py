import datetime
import os.path
import shutil
import time
from distutils.command.install_egg_info import install_egg_info
from math import trunc
from multiprocessing import Process, Event
from multiprocessing.util import debug
from selectors import SelectSelector

from Tools.scripts.make_ctype import values
from async_timeout import timeout

from src.ui.ask_question import ask_question
from src.libs import global_var as gl
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.cts_fixture import get_fixture_sensor_status
from src.libs.common import *
from src.definition import limits

# from src.libs.ble_driver import init, main, rssi_measure
from src.libs.tcpip import TCPClient
from src.libs.cts_fixture import query_fixture_sensor_status
from src.libs.ni import NIEquipment
from src.libs.mes import routing_check
import xml.etree.ElementTree as ET
from src.steps import common_steps

builder = NetworkFrameBuilder()


def read_barcode(ip):
    barcode = ""
    client = TCPClient(ip, 9004, timeout=5, buffer_size=2048)
    try:
        client.connect()
        for i in range(5):
            barcode = client.send_receive(b"LON\r").decode("utf-8")
            print("Received:", barcode)
            client.send(b"LOFF\r")
            if barcode:
                break
            time.sleep(0.2)
    except Exception as e:
        print("Error:", e)
    finally:
        client.disconnect()
    return barcode.strip()


def overall_test_result(connections, logger, **kwargs):
    logger.info("finalize")
    config = gl.get_value("layout_config")
    device_name = config.get("device_name")
    # for name, conn in connections.items():
    #     conn.close()
    # error_code  = gl.get_value("error_code")
    led_off(connections, logger, **kwargs)
    fixture_io = config.get("fixture_io")
    fixture_in = fixture_io.get("fixture_in")
    door_down = fixture_io.get("door_down")
    ni = NIEquipment(device_name)
    ni.write_digital(door_down, False)
    time.sleep(1)
    ni.write_digital(fixture_in, False)
    return common_steps.overall_test_result(connections, logger, **kwargs)
    # if error_code:
    #     return False, error_code
    # return True, "0"


def get_flexflow_color(info):
    # info = "<UnitInfo><UnitData><Name>BatterySN</Name><Value>S049101010017752504039</Value></UnitData><UnitData><Name>SerialNumber</Name><Value>T4H4 V7A QEF 6S6U</Value></UnitData><UnitData><Name>ReadUID</Name><Value></Value></UnitData><UnitData><Name>DeviceFirmwareVersion</Name><Value></Value></UnitData><UnitData><Name>CoilModule</Name><Value>ECS250619003566IM90307003103CC</Value></UnitData><UnitData><Name>EngineDUSN</Name><Value>00290063000430000003</Value></UnitData><UnitData><Name>ControlDUSN</Name><Value>0041007A000400000065</Value></UnitData><UnitData><Name>EventCheck</Name><Value>0</Value></UnitData><UnitData><Name>EventCheckFailTimes</Name><Value>0</Value></UnitData></UnitInfo>"
    root = ET.fromstring(info)
    for unitdata in root.findall("UnitData"):
        if unitdata.find("Name").text == "MT7LEDColour":
            gl.set_value("lens_color_config", unitdata.find("Value").text.strip())
        if unitdata.find("Name").text == "NVCM LED Brightness":
            gl.set_value("brightness", unitdata.find("Value").text.strip())
        if unitdata.find("Name").text == "RoutingCheck":
            gl.set_value("FlexFlowRoutingCheck", unitdata.find("Value").text.strip())


def start_test_or(connections, logger, **kwargs):
    logger.info("start_test")
    FlexFlowRoutingCheck = True
    config = gl.get_value("layout_config")
    gl.set_value("camera_ip", config.get("camera_ip"))
    gl.set_value("scanner_ip", config.get("scanner_ip"))

    lens_color = None

    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    gl.set_value("TBBUID", TBBUID)

    gl.set_value("pn", cells.get("pid")[2:])
    device_name = config.get("device_name")
    fixture_io = config.get("fixture_io")
    start = fixture_io.get("start")
    uut = fixture_io.get("uut")
    fixture_in = fixture_io.get("fixture_in")
    door_down = fixture_io.get("door_down")
    stop_event = gl.get_value("stop_event")
    logger.debug(f"device_name:{device_name}")

    ni = NIEquipment(device_name)
    while not stop_event.is_set():
        if ni.read_digital(start, 2):
            break
        time.sleep(0.5)

    ni.write_digital(fixture_in, True)
    barcode = read_barcode(config.get("scanner_ip"))

    logger.debug(f"barcode:{barcode}")
    if barcode == "":
        ni.write_digital(fixture_in, False)
        gl.set_value("error_code", kwargs.get("error_code"))
        return True, "Error Scan"
    try:
        if barcode:
            gl.set_value("dusn", barcode)
            gl.set_value("codentify", barcode)
            gl.set_value("codentify_code", barcode)
            gl.set_value("barcode", barcode)
            status, info = routing_check(barcode, TBBUID)
            online = config.get("online")
            logger.debug(f"online:{online},status:{status},info:{info}")
            if online:
                get_flexflow_color(info)
                # FlexFlowRoutingCheck = gl.get_value("FlexFlowRoutingCheck")
                # if FlexFlowRoutingCheck != "0":
                #     return False, ""
                lens_color = gl.get_value("lens_color_config").upper()
            else:
                lens_color = config.get("lens_color").upper()
                gl.set_value("lens_color", lens_color)

            if lens_color:
                if lens_color != "MID HOLDER":
                    uut_color = config.get("uut_color")
                    if uut_color:
                        for index in uut_color:
                            for item in uut_color[index]:
                                if str(item).replace("_", " ") == lens_color:
                                    gl.set_value("brightness", uut_color[index][item])
                                    gl.set_value("lens_color_config", lens_color)
                                    logger.debug(f"brightness:{uut_color[index][item]},lens_color:{lens_color}")
                else:
                    gl.set_value("lens_color_config", "MID HOLDER")
            else:
                return False, ""
        else:
            return False, ""
    except Exception as e:
        ni.write_digital(fixture_in, False)
        gl.set_value("error_code", kwargs.get("error_code"))
        return True, str(e)

    datas = get_camera_data(9, logger)
    logger.debug(datas)
    lens_color_camera = []
    if datas[0] == "1":
        lens_color_camera = ["GARNET RED", "REMIX SILVER"]
    if datas[0] == "2":
        lens_color_camera = ["BREEZE BLUE", "REMIX BLUE"]
    if datas[0] == "3":
        lens_color_camera = ["MID HOLDER"]
    if datas[0] == "4":
        lens_color_camera = ["MIDNIGHT BLACK"]
    if datas[0] == "5":
        lens_color_camera = ["ASPEN GREEN"]
    if datas[0] == "6":
        lens_color_camera = ["ELECTRIC PURPLE"]

    logger.debug(f"lens_color_camera:{lens_color_camera}")
    logger.debug(f"lens_color_config:{lens_color}")

    if len(lens_color_camera) == 0:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, ""
    elif lens_color in lens_color_camera:
        gl.set_value("lens_color", lens_color)
        ni.write_digital(door_down, True)
        return True, ""
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, "Wrong LENS Color"

def start_test_20260120(connections, logger, **kwargs):
    logger.info("start_test")
    FlexFlowRoutingCheck = True
    config = gl.get_value("layout_config")
    gl.set_value("camera_ip", config.get("camera_ip"))
    gl.set_value("scanner_ip", config.get("scanner_ip"))

    lens_color = None

    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    gl.set_value("TBBUID", TBBUID)

    gl.set_value("pn", cells.get("pid")[2:])
    device_name = config.get("device_name")
    fixture_io = config.get("fixture_io")
    start = fixture_io.get("start")
    uut = fixture_io.get("uut")
    fixture_in = fixture_io.get("fixture_in")
    door_down = fixture_io.get("door_down")
    stop_event = gl.get_value("stop_event")
    logger.debug(f"device_name:{device_name}")

    ni = NIEquipment(device_name)
    on_line_check = True
    try:
        for _ in range(100):
            while not stop_event.is_set():
                if ni.read_digital(start, 2):
                    break
                time.sleep(0.5)

            ni.write_digital(fixture_in, True)
            barcode = read_barcode(config.get("scanner_ip"))

            logger.debug(f"barcode:{barcode}")
            if barcode == "":
                ni.write_digital(fixture_in, False)
                gl.set_value("error_code", kwargs.get("error_code"))
                return True, "Error Scan"
            else:
                gl.set_value("dusn", barcode)
                gl.set_value("codentify", barcode)
                gl.set_value("codentify_code", barcode)
                gl.set_value("barcode", barcode)
                status, info = routing_check(barcode, TBBUID)
                online = config.get("online")
                logger.debug(f"online:{online},status:{status},info:{info}")
                if online:
                    get_flexflow_color(info)
                    lens_color = gl.get_value("lens_color_config").upper()
                    if gl.get_value("FlexFlowRoutingCheck") != "0":
                        on_line_check = False
                        ni.write_digital(fixture_in, False)
                else:
                    lens_color = config.get("lens_color").upper()
                    gl.set_value("lens_color", lens_color)
                if on_line_check:
                    if lens_color:
                        if lens_color != "MID HOLDER":
                            uut_color = config.get("uut_color")
                            if uut_color:
                                for index in uut_color:
                                    for item in uut_color[index]:
                                        if str(item).replace("_", " ") == lens_color:
                                            gl.set_value("brightness", uut_color[index][item])
                                            gl.set_value("lens_color_config", lens_color)
                                            logger.debug(f"brightness:{uut_color[index][item]},lens_color:{lens_color}")
                        else:
                            gl.set_value("lens_color_config", "MID HOLDER")
                    else:
                        return False, ""
                    break
            time.sleep(1)
    except Exception as e:
        ni.write_digital(fixture_in, False)
        gl.set_value("error_code", kwargs.get("error_code"))
        return True, str(e)
    datas = get_camera_data(9, logger)
    logger.debug(datas)
    lens_color_camera = []
    if datas[0] == "1":
        lens_color_camera = ["GARNET RED", "REMIX SILVER"]
    if datas[0] == "2":
        lens_color_camera = ["BREEZE BLUE", "REMIX BLUE"]
    if datas[0] == "3":
        lens_color_camera = ["MID HOLDER"]
    if datas[0] == "4":
        lens_color_camera = ["MIDNIGHT BLACK"]
    if datas[0] == "5":
        lens_color_camera = ["ASPEN GREEN"]
    if datas[0] == "6":
        lens_color_camera = ["ELECTRIC PURPLE"]

    logger.debug(f"lens_color_camera:{lens_color_camera}")
    logger.debug(f"lens_color_config:{lens_color}")

    if len(lens_color_camera) == 0:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, ""
    elif lens_color in lens_color_camera:
        gl.set_value("lens_color", lens_color)
        ni.write_digital(door_down, True)
        return True, ""
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, "Wrong LENS Color"


def start_test(connections, logger, **kwargs):
    logger.info("start_test")
    FlexFlowRoutingCheck = False
    config = gl.get_value("layout_config")
    gl.set_value("camera_ip", config.get("camera_ip"))
    gl.set_value("scanner_ip", config.get("scanner_ip"))

    lens_color = None

    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    gl.set_value("TBBUID", TBBUID)
    SNPath = user_config.get("SNPath")
    SNResult = user_config.get("SNResult")
    SNCopy = user_config.get("SNCopy")
    snPathFiles = os.listdir(SNPath)
    snResultFiles = os.listdir(SNResult)
    if len(snPathFiles) > 0:
        for file in snPathFiles:
            os.remove(os.path.join(SNPath, file))
    if len(snResultFiles) > 0:
        for file in snResultFiles:
            os.rmdir(os.path.join(SNResult, file))

    gl.set_value("pn", cells.get("pid")[2:])
    device_name = config.get("device_name")
    fixture_io = config.get("fixture_io")
    start = fixture_io.get("start")
    uut = fixture_io.get("uut")
    fixture_in = fixture_io.get("fixture_in")
    door_down = fixture_io.get("door_down")
    stop_event = gl.get_value("stop_event")
    logger.debug(f"device_name:{device_name}")
    ni = NIEquipment(device_name)
    on_line_check = True
    status = True

    try:
        for _ in range(100):
            while not stop_event.is_set():
                if ni.read_digital(start, 2):
                    break
                time.sleep(0.5)

            ni.write_digital(fixture_in, True)
            barcode = read_barcode(config.get("scanner_ip"))

            logger.debug(f"barcode:{barcode}")
            if barcode == "":
                ni.write_digital(fixture_in, False)
                gl.set_value("error_code", kwargs.get("error_code"))
                return True, "Error Scan"
            else:
                gl.set_value("dusn", barcode)
                gl.set_value("codentify", barcode)
                gl.set_value("codentify_code", barcode)
                gl.set_value("barcode", barcode)
                online = config.get("online")
                if online:
                    shake_hand_file = os.path.join(SNPath, f"{barcode}.txt")
                    with open(shake_hand_file,"w") as f:
                        pass
                    sn_result_start = datetime.datetime.now()
                    shake_file_name = ""

                    while not stop_event.is_set():
                        delta_time = datetime.datetime.now() - sn_result_start
                        logger.debug(f"delta time: {delta_time}")
                        if delta_time.total_seconds() > 30:
                            return True, "MESAssistant Error"
                        shake_hand_files = os.listdir(SNResult)
                        logger.debug(f"{SNResult},{shake_hand_files}")
                        for shake_file in shake_hand_files:
                            logger.debug(f"{shake_file},{barcode},{shake_file.startswith(barcode)}")
                            if shake_file.startswith(barcode):
                                logger.debug(f"{shake_file},{barcode},{shake_file.startswith(barcode)},{shake_file.split('.')[0].endswith('FAIL')}")
                                if shake_file.split(".")[0].endswith("FAIL"):
                                    FlexFlowRoutingCheck = False
                                    ni.write_digital(fixture_in, False)
                                    gl.set_value("error_code", kwargs.get("error_code"))
                                    shake_file_name_path = os.path.join(SNResult, shake_file)
                                    os.remove(shake_file_name_path)
                                    return True, "Routing Error"
                                else:
                                    lens_color = shake_file.split('_')[1]
                                    shake_file_name = shake_file
                                    FlexFlowRoutingCheck = True
                                    break
                        if FlexFlowRoutingCheck:
                            break
                        time.sleep(0.1)
                    logger.debug(f"lens_color,{lens_color}")
                    logger.debug(f"lens_color,{lens_color},{shake_file_name}")
                    if shake_file_name != "":
                        shake_file_name_path = os.path.join(SNResult, shake_file_name)
                        shake_file_name_path_target = os.path.join(SNCopy, shake_file_name)
                        if os.path.exists(shake_file_name_path_target):
                            os.remove(shake_file_name_path_target)
                        if not os.path.exists(shake_file_name_path_target):
                            shutil.copy(shake_file_name_path, shake_file_name_path_target)
                            if os.path.exists(shake_file_name_path_target):
                                os.remove(shake_file_name_path)
                    else:
                        return False, ""
                    # online = config.get("online")
                    logger.debug(f"online:{online},status:{status},Color:{lens_color}")
                # if online:
                    if not FlexFlowRoutingCheck:
                        on_line_check = False
                        ni.write_digital(fixture_in, False)
                else:
                    lens_color = config.get("lens_color").upper()
                    gl.set_value("lens_color", lens_color)
                if on_line_check:
                    if lens_color:
                        if lens_color != "MID HOLDER":
                            uut_color = config.get("uut_color")
                            if uut_color:
                                for index in uut_color:
                                    for item in uut_color[index]:
                                        if str(item).replace("_", " ") == lens_color:
                                            gl.set_value("brightness", uut_color[index][item])
                                            gl.set_value("lens_color_config", lens_color)
                                            logger.debug(f"brightness:{uut_color[index][item]},lens_color:{lens_color}")
                        else:
                            gl.set_value("lens_color_config", "MID HOLDER")
                    else:
                        return False, ""
                    break
            time.sleep(1)
    except Exception as e:
        ni.write_digital(fixture_in, False)
        gl.set_value("error_code", kwargs.get("error_code"))
        return True, str(e)
    datas = get_camera_data(9, logger)
    logger.debug(datas)
    lens_color_camera = []
    if datas[0] == "1":
        lens_color_camera = ["GARNET RED", "REMIX SILVER"]
    if datas[0] == "2":
        lens_color_camera = ["BREEZE BLUE", "REMIX BLUE"]
    if datas[0] == "3":
        lens_color_camera = ["MID HOLDER"]
    if datas[0] == "4":
        lens_color_camera = ["MIDNIGHT BLACK"]
    if datas[0] == "5":
        lens_color_camera = ["ASPEN GREEN"]
    if datas[0] == "6":
        lens_color_camera = ["ELECTRIC PURPLE"]

    logger.debug(f"lens_color_camera:{lens_color_camera}")
    logger.debug(f"lens_color_config:{lens_color}")

    if len(lens_color_camera) == 0:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, ""
    elif lens_color in lens_color_camera:
        gl.set_value("lens_color", lens_color)
        ni.write_digital(door_down, True)
        return True, ""
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        ni.write_digital(door_down, False)
        time.sleep(1.5)
        ni.write_digital(fixture_in, False)
        return False, "Wrong LENS Color"


def scan_vsn(connections, logger, **kwargs):
    error_code = gl.get_value("error_code")
    if error_code:
        return False, error_code
    return True, gl.get_value("dusn")


def tbbuid(connections, logger, **kwargs):
    return True, gl.get_value("TBBUID")


def log_build_number(connections, logger, **kwargs):
    return True, "MT7L_1016.EMS2.3"


def control_pca_dusn(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_dusn_control = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
    )
    logger.debug(f"build cmd: {cmd_dusn_control.hex()}")
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
        logger.debug(f"control dusn:{dusn}")
        gl.set_value("platform_code", f"{dusns[8]}{dusns[7]}")
        gl.set_value("site_code", f"{dusns[12]}{dusns[11]}")
        gl.set_value("dusn", dusn)
        gl.set_value("product_code", f"{dusns[10]}{dusns[9]}")

        gl.set_value("control_codenticode", dusn)
        gl.set_value("control_dusn", dusn)

        gl.set_value("control_pn", f"{dusns[10]}{dusns[9]}")
        gl.set_value("control_platform", f"{dusns[8]}{dusns[7]}")
        gl.set_value("control_dusn", f"{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}")

        limit = kwargs.get("limit").get("min")[:8]
        gl.set_value("control_pn", limit.lower()[4:8])
        if dusn.lower().startswith(limit.lower()):
            return True, dusn
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
    return False, dusn


def engine_pca_dusn(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_dusn = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
    )
    logger.debug(f"build cmd: {cmd_dusn.hex()}")
    response = None
    dusns = []
    dusn = ""
    for i in range(15):
        try:
            response = connection.send_receive(cmd_dusn, timeout=1)
            if response[5] == 0x89 and response[6] == 0x00:
                dusns = [f"{byte:02x}" for byte in response]
                dusn = f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}".upper()
                break
        except Exception as ex:
            print(str(ex))
        time.sleep(1)

    if len(dusns) > 12 and len(dusn) > 0:
        logger.debug(f"engine dusn:{dusn}")
        gl.set_value("platform_code", f"{dusns[8]}{dusns[7]}")
        gl.set_value("site_code", f"{dusns[12]}{dusns[11]}")
        gl.set_value("dusn", dusn)
        gl.set_value("product_code", f"{dusns[10]}{dusns[9]}")
        gl.set_value("engine_codenticode", dusn)
        gl.set_value("engine_dusn", dusn)
        gl.set_value("engine_pn", f"{dusns[10]}{dusns[9]}")
        gl.set_value("engine_platform", f"{dusns[8]}{dusns[7]}")
        gl.set_value("engine_dusn", f"{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}")
        limit = kwargs.get("limit").get("min")[:8]
        gl.set_value("engine_pn", limit.lower()[4:8])
        if dusn.lower().startswith(limit.lower()):
            return True, dusn
        else:
            gl.set_value("error_code", kwargs.get("error_code"))

    return False, dusn


def control_mt_mode_state(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    command = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=36,
        count=1,
    )
    logger.debug(f"build cmd: {command.hex()}")
    response = connection.send_receive(command, timeout=1)
    logger.debug(f"MTMode:{response}")
    if response[-2] == 0xBE and response[-3] == 0xEF:
        # return True, f"{hex(response[-2])[2:]}{hex(response[-3])[2:]}"
        return True, "PASS"
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        # return False,f"{hex(response[-2])[2:]}{hex(response[-3])[2:]}"
        return False, "FAIL"


def query_dgs_lens_color(connections, logger, **kwargs):
    lens_color_config = gl.get_value("lens_color_config")
    if lens_color_config:
        return True, str(lens_color_config)
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(lens_color_config)


def pil_lens_color(connections, logger, **kwargs):
    lens_color_config = gl.get_value("lens_color_config")
    if lens_color_config:
        return True, str(lens_color_config)
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(lens_color_config)


def compare_color_result(connections, logger, **kwargs):
    lens_color_config = gl.get_value("lens_color_config")
    if lens_color_config:
        return True, str(lens_color_config).replace(" ","_")
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(lens_color_config).replace(" ","_")


def query_existing_configuration_code(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    command = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=279,
        count=2,
    )
    logger.debug(f"build cmd: {command.hex()}")
    response = connection.send_receive(command, timeout=1)
    logger.debug(f"MTMode:{response}")
    codes = [f"{byte:02x}" for byte in response]
    config_code = f"{codes[16]}{codes[15]}{codes[14]}{codes[13]}"
    gl.set_value("config_code_exist", config_code)
    return True, config_code


def write_nvcm_configuration_code(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    code_exist = gl.get_value("config_code_exist")
    logger.debug(f'gl.get_value("lens_color"):{gl.get_value("lens_color")}')
    if gl.get_value("lens_color") != "MID HOLDER":

        code_exists = list(code_exist)
        code_exists[5] = "1"
        code_exist = "".join(code_exists)
        gl.set_value("config_code_write", code_exist)
        command = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=279,
            count=2,
            value1=bytes.fromhex(code_exist)[::-1],
        )
        logger.debug(list(command))
        response = connection.send_receive(command, timeout=1)
        return True, code_exist
    else:
        gl.set_value("config_code_write", code_exist)
        return True, code_exist


def query_nvcm_configuration_code(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    command = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=279,
        count=2,
    )
    logger.debug(f"build cmd: {command.hex()}")
    response = connection.send_receive(command, timeout=1)
    logger.debug(f"query_nvcm_configuration_code:{response}")
    codes = [f"{byte:02x}" for byte in response]

    config_code = f"{codes[16]}{codes[15]}{codes[14]}{codes[13]}"
    if config_code == gl.get_value("config_code_write"):
        return True, config_code
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, config_code


def write_nvcm_led_brightness(connections, logger, **kwargs):
    les_co = gl.get_value('lens_color')
    logger.debug(f"lens_color....,{les_co}")
    connection = connections.get("serial_dut")
    if gl.get_value("lens_color") != "MID HOLDER":
        gl.get_value("brightness")
        command = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=279,
            count=2,
            value1=int(gl.get_value("brightness"), 16),
        )
        logger.debug(list(command))
        response = connection.send_receive(command, timeout=1)
        return True, "pass"
    else:
        return True, ""


def query_nvcm_led_brightness(connections, logger, **kwargs):
    if gl.get_value("lens_color") != "MID HOLDER":
        connection = connections.get("serial_dut")
        command = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=266,
            count=1,
        )
        logger.debug(f"build cmd: {command.hex()}")
        response = connection.send_receive(command, timeout=1)
        logger.debug(f"MTMode:{response}")
        codes = [f"{byte:02x}" for byte in response]
        print(codes)
        brightness = f"{codes[14]}{codes[13]}"
        if gl.get_value("brightness") == brightness:
            return True, brightness
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, brightness
    else:
        return True, ""

def led_test(connections, logger, **kwargs):
    # print(kwargs)
    connection = connections.get("serial_dut")
    status = True
    time.sleep(0.025)
    # camera_channel = 2 #led off channel
    rgbPositions = {"RED":0,"GREEN":1,"BLUE":2,"INTENSITY":3} # rgb data in camera data position
    commands = {"R1_LED_RED":[0x8880,0x0088, 5,"r1_status",["r1","r5","r9","r13","r17"]],
                "R2_LED_RED":[0x1100,0x0111, 6,"r2_status",["r2","r6","r10","r14","r18"]],
                "R3_LED_RED":[0x2200,0x0222, 7,"r3_status",["r3","r7","r11","r15","r19"]],
                "R4_LED_RED":[0x4400,0x0444, 8,"r4_status",["r4","r8","r12","r16","r20"]],
                "L2_LED_RED":[0x002A,0x0000, 3,"l2_status",["l2","l4","l6"]],
                "L1_LED_RED":[0x0055,0x0000, 4,"l1_status",["l1","l3","l5","l7"]],
                "RING_LED_LEAKAGE":[0x00A2,0x0000, 10,"",[]],
                "OFF_LED_RED":[0x00A4,0x0000, 2, "off_status",["off"]],
                "SEGMENT_LED_LEAKAGE_1":[0x0014,0x0000,11,"",[]],
                "SEGMENT_LED_LEAKAGE_2":[0x0041,0x0000,12,"",[]],
                "SEGMENT_LED_LEAKAGE_3":[0x0008,0x0000,13,"",[]],
                "SEGMENT_LED_LEAKAGE_4":[0x0022,0x0000,14,"",[]],
                }
    step = kwargs.get("step")
    lsl = kwargs.get("limit").get("min")
    usl = kwargs.get("limit").get("max")
    datas = [""]
    test_value = -1
    for i in range(5):
        if step in commands.keys():
            command = commands[step]
            led_off(connections, logger, **kwargs)
            cmd_led_select = None
            if "RING" in step or "OFF" in step:
                cmd_led_select = builder.build_write_request_frame(
                    mode="uart",
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x08,
                    pnum=14,
                    count=1,
                    value1=command[0],
                )
            else:
                cmd_led_select = builder.build_write_request_frame(
                    mode="uart",
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x08,
                    pnum=263,
                    count=2,
                    value1= command[0],
                    value2= command[1],
                    value3=0x0000,
                )
            res = connection.send_receive(cmd_led_select)
            logger.debug(f"build cmd led_r: {list(res)}")
            if "RING" in step or "OFF" in step:
                pass
            else:
                led_on(connections, logger, **kwargs)
            datas = get_camera_data(command[2], logger)
            if command[3] != "":
                if datas[0] == "0":
                    gl.set_value(command[3], True)
                else:
                    gl.set_value(command[3], False)
                index = 1
                for led in command[4]:
                    gl.set_value(led, datas[index:index+4])
                    index = index + 4
        if str(kwargs.get("step")).startswith("SEGMENT_DIM_CHECK"):
            check_number = str(kwargs.get("step"))[-1]
            test_value = abs(float(gl.get_value("l1")[3]) - float(gl.get_value("l7")[3]))
            if check_number == "2":
                test_value = abs(float(gl.get_value("l3")[3]) - float(gl.get_value("l5")[3]))
            lsl = kwargs.get("limit").get("min")
            usl = kwargs.get("limit").get("max")
            test_value = round(test_value, 2)
        elif "LED_POSITION" in step:
                status = False
                ledPos = int(kwargs.get("step")[-1])
                if ledPos < 5:
                    status = gl.get_value(f'r{ledPos}_status')
                elif ledPos == 5:
                    status = gl.get_value('l2_status')
                elif ledPos == 6:
                    status = gl.get_value('l1_status')
                if status:
                    test_value = "0"
                else:
                    gl.set_value("error_code", kwargs.get("error_code"))
                    test_value = "1"
        elif "LED_LEAKAGE" in step:
                leak_index = step[-1]
                if leak_index == "1":
                    test_value = max([float(datas[1:5][-1]), float(datas[13:17][-1])])
                elif leak_index == "2":
                    test_value = max([float(datas[5:9][-1]), float(datas[9:13][-1])])
                else:
                    test_value = max(
                        [
                            float(datas[1:5][-1]),
                            float(datas[5:9][-1]),
                            float(datas[9:13][-1]),
                            float(datas[13:17][-1]),
                        ]
                    )
                test_value = round(test_value, 2)
        else:
            # test RGB data
            key = kwargs.get("step").split("_")[0].lower()
            rgbPosKey = step.split('_')[-1]
            rgbPos = rgbPositions[rgbPosKey]
            test_value = float(gl.get_value(key)[rgbPos])
        if not isinstance(test_value, str):
            if lsl <= test_value <= usl:
                status = True
            else:
                status = False
        if status:
            break
        time.sleep(1)
    if not status:
        gl.set_value("error_code", kwargs.get("error_code"))
    status_value = str(test_value)
    return status, status_value

def led_on(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_frame_led_on = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00C5,
    )
    logger.debug(f"led_on: {list(cmd_frame_led_on)}")

    res = connection.send_receive(cmd_frame_led_on)
    logger.debug(res)
    return True, "PASS"


def led_off(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_frame_led_off = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00A4,
    )
    logger.debug(f"led off: {list(cmd_frame_led_off)}")

    res = connection.send_receive(cmd_frame_led_off)
    logger.debug(res)
    logger.debug(res)
    return True, "PASS"

def set_control_pcba_codentifier(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
    )
    response = None

    for i in range(15):
        response = connection.send_receive(cmd_codentify, timeout=1)
        if response[5] == 0x88 and response[6] == 0x03:
            # print("**********************Correctly")
            break
        time.sleep(1)
    if response[7] == 0xFF and response[8] == 0xFF:
        status, codentify = write_codentify_code_control(connections, logger, **kwargs)
        if status:
            return True, codentify
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentify
    else:
        codentifyCode = response[7:21].decode("utf-8").replace(" ", "")
        codentifyScan = gl.get_value("codentify_code").replace(" ", "")
        logger.debug(f"codentifyCode:{codentifyCode},codentifyScan:{codentifyScan}")

        if codentifyCode == codentifyScan:
            return True, codentifyCode
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentifyCode


def read_control_pcba_codentifier(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
    )
    response = None

    for i in range(15):
        response = connection.send_receive(cmd_codentify, timeout=1)
        if response[5] == 0x88 and response[6] == 0x03:
            # print("**********************Correctly")
            break
        time.sleep(1)
    if response[7] == 0xFF and response[8] == 0xFF:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, ""
    codentifyCode = response[7:21].decode("utf-8").replace(" ", "")
    if codentifyCode:
        if len(codentifyCode) == 14:
            return True, codentifyCode
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentifyCode
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, gl.get_value("barcode")


def set_engine_pcba_codentifier(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x0C
    )
    response = None

    for i in range(15):
        response = connection.send_receive(cmd_codentify, timeout=1)
        if response[5] == 0x88 and response[6] == 0x03:
            # print("**********************Correctly")
            break
        time.sleep(1)
    if response[7] == 0xFF and response[8] == 0xFF:
        status, codentify = write_codentify_code_engine(connections, logger, **kwargs)
        if status:
            return True, codentify
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentify
    else:
        codentifyCode = response[7:21].decode("utf-8").replace(" ", "")
        codentifyScan = gl.get_value("codentify_code").replace(" ", "")
        if codentifyCode == codentifyScan:
            return True, codentifyCode
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentifyCode

    # if codentifyCode:
    #     if len(codentifyCode) == 14:
    #         return True, codentifyCode
    #     else:
    #         gl.set_value("error_code", kwargs.get("error_code"))
    #         return False, codentifyCode
    # else:
    #     status = write_codentify_code_engine(connections, logger, **kwargs)
    #     if status:
    #         return True, codentifyCode
    #     else:
    #         gl.set_value("error_code", kwargs.get("error_code"))
    #         return False, codentifyCode


def read_engine_pcba_codentifier(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x0C
    )
    response = None

    for i in range(15):
        response = connection.send_receive(cmd_codentify, timeout=1)
        if response[5] == 0x88 and response[6] == 0x03:
            # print("**********************Correctly")
            break
        time.sleep(1)
    if response[7] == 0xFF and response[8] == 0xFF:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, ""
    codentifyCode = response[7:21].decode("utf-8").replace(" ", "")
    if codentifyCode:
        if len(codentifyCode) == 14:
            return True, codentifyCode
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, codentifyCode
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, codentifyCode


def write_codentify_code_control(connections, logger, **kwargs):
    # codentify = gl.get_value("barcode")
    connection = connections.get("serial_dut")
    codentify = gl.get_value("codentify_code").replace(" ", "")
    codentify_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=37,
        count=7,
        value=codentify,
    )
    logger.debug(f"codentify_write_frame.hex():{codentify_write_frame.hex()}")
    response = connection.send_receive(codentify_write_frame, timeout=1)
    if response:
        return True, codentify
    # else:
    #     gl.set_value("error_code", kwargs.get("error_code"))
    return False, codentify


def write_codentify_code_engine(connections, logger, **kwargs):

    connection = connections.get("serial_dut")
    codentify = gl.get_value("codentify_code").replace(" ", "")
    codentify_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=37,
        count=7,
        value=codentify,
    )
    response = connection.send_receive(codentify_write_frame, timeout=1)
    if response:
        return True, codentify
    return False, codentify


def get_camera_data(branch: int, logger) -> list:

    datas = []
    client = TCPClient(gl.get_value("camera_ip"), 8500, timeout=5, buffer_size=2048)
    try:
        client.connect()
        seq = f"IW,#branch,{branch}\r"
        data = client.send_receive(seq.encode("utf-8")).decode("utf-8")
        logger.debug("get camera...")
        logger.debug(data)
        logger.debug(str(data).upper().startswith("IW"))
        if str(data).upper().startswith("IW"):

            info = "T1\r"
            data = client.send_receive(info.encode("utf-8")).decode("utf-8")
            logger.debug(data)
            if str(data).startswith("T1"):
                data = client.receive().decode("utf-8")
                logger.debug(data)
                datas = data.split(",")
    except Exception as e:
        logger.debug(f"Error Camera: {e}")
        print("Error:", e)
    finally:
        client.disconnect()
    return datas
