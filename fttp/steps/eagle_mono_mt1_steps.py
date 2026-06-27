import os.path
import time
from getpass import fallback_getpass
from math import trunc
from multiprocessing import Process, Event

from yaml import full_load

from src.ui.ask_question import ask_question

from libs.mes_xml import MESXml
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
import subprocess
import binascii
import src.libs.mes_xml
import src.libs.wcf_mes as wcf_mes

builder = NetworkFrameBuilder()

def init_steps(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    connection.connect()

    gl.set_value("test_summary", {})

def overall_test_result(connections, logger, **kwargs):
    logger.info("finalize")

    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    tester = user_config.get("TBBUID")
    fixture = user_config.get("fixture")
    test_summary = gl.get_value("test_summary")
    if len(test_summary) != 0:
        barcode = gl.get_value("barcode")
        with open(f'{barcode}.xml',"w+") as f:
            f.write(MESXml.Generate_xml("Eagle Mono",barcode,tester,fixture, test_summary))

    return common_steps.overall_test_result(connections, logger, **kwargs)

def start_test(connections, logger, **kwargs):
    logger.info("start_test")
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]

    gl.set_value("pn", cells.get("pid")[2:].lower())

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
            if answer.upper().startswith("NEM"):
                gl.set_value("barcode", answer)
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
def scan_vsn(connections, logger, **kwargs):
    answer = ask_question("Please type 'Y' to continue")
    if answer:
        if answer.upper() == "Y":
            init_steps(connections, logger, **kwargs)
            update_test_summary("Control",{
                "test_item": "scan_vsn",
                "test_value": gl.get_value("barcode"),
                "lsl": gl.get_value("barcode"),
                "usl": gl.get_value("barcode"),
                "status": "PASS",
            })
            return True, gl.get_value("barcode")
    update_test_summary("Control",{
        "test_item": "scan_vsn",
        "test_value": gl.get_value("barcode"),
        "lsl": gl.get_value("barcode"),
        "usl": gl.get_value("barcode"),
        "status": "FAIL",
    })
    return False, ""
def TBBUID(connections, logger, **kwargs):
    return True, "PASS"

def TEST_CAVITY(connections, logger, **kwargs):
    update_test_summary("Control",{
        "test_item": "TEST_CAVITY",
        "test_value": "0",
        "lsl": "",
        "usl": "",
        "status": "PASS",
    })
    return True, "0"

def power_on(connections, logger, **kwargs):
    return True, "PASS"

def power_on_current(connections, logger, **kwargs):
    return True, "PASS"

def power_on_voltage(connections, logger, **kwargs):
    return True, "PASS"

def mcu_program(connections, logger, **kwargs):
    return True, "PASS"
    stop_event = gl.get_value("stop_event")
    config = gl.get_value("layout_config")
    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")
    scanner_ip = fixture_io.get("scanner_ip")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    cli_path = user_config.get("cli_path")
    hex_path = user_config.get("hex_path")
    if not os.path.exists(cli_path):
        return False, "cli_path does not exist"
    if not os.path.exists(hex_path):
        return False, "hex_path does not exist"
    return flash_stm32(cli_path, hex_path)

def fw_check(connections, logger, **kwargs):

    config = gl.get_value("layout_config")
    fw_config = config["fw_ver"]
    connection = connections.get("serial_dut")
    if connection.ensure_connected():
        cmd_fw = builder.build_read_request_frame(
            mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x00
        )
        logger.debug(f"{cmd_fw},{list(cmd_fw)}")
        response = None
        fw = ""
        for i in range(5):
            response = connection.send_receive(cmd_fw, timeout=1)
            logger.debug(f"{fw},{response}")
            logger.debug(f"{fw},{list(response)}")
            if response[1] == 0x88 and response[2] == 0x00:
                fw = f"{response[5]}.{response[6]}.{response[7]}"
                break
        status = True
        if fw == fw_config:
            update_test_summary("Control", {
                "test_item": "fw_check",
                "test_value": fw,
                "lsl": fw_config,
                "usl": fw_config,
                "status": "PASS",
            })
            return True, fw
        else:
            update_test_summary("Control", {
                "test_item": "fw_check",
                "test_value": fw,
                "lsl": fw_config,
                "usl": fw_config,
                "status": "FAIL",
            })
            return False, fw
    else:
        update_test_summary("Control", {
            "test_item": "fw_check",
            "test_value": "",
            "lsl": fw_config,
            "usl": fw_config,
            "status": "FAIL",
        })
        return False, ""



def bist_test(connections, logger, **kwargs):
    return True, "PASS"

def heater_enablement_power_on(connections, logger, **kwargs):

    #TP512 On
    connection = connections.get("serial_dut")
    if connection.ensure_connected():

        cmd = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=14,
            count=1,
            value1=0x1008,
        )
        print(cmd)
    return True, "PASS"

def heater_enablement_power_off(connections, logger, **kwargs):
    # TP512 Off
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1009,
    )
    print(cmd)
    return True, "PASS"

def vdd3_power_on(connections, logger, **kwargs):
    # TP403
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100e,
    )
    return True, "PASS"

def vdd3_power_off(connections, logger, **kwargs):
    # TP403
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100f,
    )
    return True, "PASS"

def vio_power_on(connections, logger, **kwargs):
    # TP402
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100c,
    )
    return True, "PASS"

def vio_power_off(connections, logger, **kwargs):
    # TP402
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100d,
    )
    return True, "PASS"

def vddusb_power_on(connections, logger, **kwargs):
    # TP214
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100e,
    )
    return True, "PASS"

def vddusb_power_off(connections, logger, **kwargs):
    # TP214
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100f,
    )
    return True, "PASS"

def vd18_power_on(connections, logger, **kwargs):
    # TP707
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2000,
    )
    return True, "PASS"

def vd18_power_off(connections, logger, **kwargs):
    # TP707
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2001,
    )
    return True, "PASS"

def vd11_power_on(connections, logger, **kwargs):
    # TP708
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100e,
    )
    return True, "PASS"

def vd11_power_off(connections, logger, **kwargs):
    # TP708
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100f,
    )
    return True, "PASS"

def tac_1v8_power_on(connections, logger, **kwargs):
    # TP600
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2000,
    )
    return True, "PASS"

def tac_1v8_power_off(connections, logger, **kwargs):
    # TP600
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2001,
    )
    return True, "PASS"

def tac_2v8_power_on(connections, logger, **kwargs):
    # TP601
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2000,
    )
    return True, "PASS"

def tac_2v8_power_off(connections, logger, **kwargs):
    # TP601
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x2001,
    )
    return True, "PASS"

def vboost_out_power_on(connections, logger, **kwargs):
    #TP513
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x201c,
    )
    return True, "PASS"

def vboost_out_power_off(connections, logger, **kwargs):
    # TP513
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x201d,
    )
    return True, "PASS"

def dp2v5_power_on(connections, logger, **kwargs):
    #TP300
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100a,
    )
    return True, "PASS"

def dp2v5_power_off(connections, logger, **kwargs):
    #TP300
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100b,
    )
    return True, "PASS"

def dp3v5_power_on(connections, logger, **kwargs):
    #TP303
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100c,
    )
    return True, "PASS"

def dp3v5_power_off(connections, logger, **kwargs):
    #TP303
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100d,
    )
    return True, "PASS"

def vm_power_on(connections, logger, **kwargs):
    #TP316
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100c,
    )
    return True, "PASS"

def vm_power_off(connections, logger, **kwargs):
    #TP316
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x100d,
    )
    return True, "PASS"

def vbus_power_on(connections, logger, **kwargs):
    #TP415
    return True, "PASS"

def vbus_power_off(connections, logger, **kwargs):
    #TP415
    return True, "PASS"

def button_status_off(connections, logger, **kwargs):
    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=52,
        count=1,
    )

    return True, "PASS"

def button_status_on(connections, logger, **kwargs):
    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=52,
        count=1,
    )
    return True, "PASS"

def button_reset_test(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1005,
    )

    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
    )
    return True, "PASS"

def pre_charge_current(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1021,
    )
    return True, "PASS"

def fast_charge_current(connections, logger, **kwargs):
    return True, "PASS"

def current_after_stop(connections, logger, **kwargs):
    return True, "PASS"

def disable_charge_current(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1022,
    )
    return True, "PASS"

def haptic_on(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1005,
    )
    return True, "PASS"

def haptic_off(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1007,
    )
    return True, "PASS"

def imu_test(connections, logger, **kwargs):

    return True, "PASS"

def rt200_temperature(connections, logger, **kwargs):
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x1024,
    )

    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=17,
        count=1,
    )
    return True, "PASS"

def rt500_temperature(connections, logger, **kwargs):
    return True, "PASS"

def hall_sensor_on(connections, logger, **kwargs):
    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=53,
        count=1,
    )
    return True, "PASS"

def hall_sensor_off(connections, logger, **kwargs):
    cmd = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=53,
        count=1,
    )
    return True, "PASS"

def sleep_enter(connections, logger, **kwargs):
    return True, "PASS"

def sleep_exit(connections, logger, **kwargs):
    return True, "PASS"

def ship_mode_enter(connections, logger, **kwargs):
    return True, "PASS"

def write_pca_dusn(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    dusn = gl.get_value("dusn")[3:]
    # sn = "NEM0045007F00040000007A"
    # dusn = sn[3:]
    platform = dusn[:4]
    product = dusn[4:8]
    site = dusn[8:12]
    deviceNumber = dusn[12:20]
    platform_code = binascii.unhexlify(hex(int(platform, 16))[2:].zfill(4))
    # product_code = binascii.unhexlify(hex(int(product, 16))[2:].zfill(4))
    # site_code = binascii.unhexlify(hex(int(site, 16))[2:].zfill(4))
    # deviceNumber_code = binascii.unhexlify(hex(int(deviceNumber, 16))[2:].zfill(8))

    platform_little = int(platform, 16).to_bytes(2,"little")
    product_little = int(product, 16).to_bytes(2,"little")
    site_little = int(site, 16).to_bytes(2,"little")
    deviceNumber_little = int(deviceNumber, 16).to_bytes(4,"little")
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=2,
        count=6,
        value0=platform_little,
        value1=product_little,
        value2=site_little,
        value3=deviceNumber_little,
    )
    logger.debug(list(cmd))
    # print("**************888fffffffffffffffffffff")
    # print(cmd)
    # print(list(cmd))

    # platform_codes = list(binascii.unhexlify(hex(int(platform, 16))[2:].zfill(4)))
    # product_codes= list(binascii.unhexlify(hex(int(product, 16))[2:].zfill(4)))
    # site_codes = list(binascii.unhexlify(hex(int(site, 16))[2:].zfill(4)))
    # deviceNumber_codes = list(binascii.unhexlify(hex(int(deviceNumber, 16))[2:].zfill(8)))
    # cmd = builder.build_write_request_frame(
    #     mode="uart",
    #     reply_hop_count=0,
    #     hop_count=0,
    #     parameter=0x08,
    #     pnum=2,
    #     count=6,
    #     value0=platform_codes[1],
    #     value1=platform_codes[0],
    #     value2=product_codes[1],
    #     value3=product_codes[0],
    #     value4=site_codes[1],
    #     value5=site_codes[0],
    #     value6=deviceNumber_codes[3],
    #     value7=deviceNumber_codes[2],
    #     value8=deviceNumber_codes[1],
    #     value9=deviceNumber_codes[0],
    # )
    # print("**************888fffffffffffffffffffff22")
    # # print(cmd)
    # print(dusn)
    # print(deviceNumber_codes)
    # print(list(cmd))
    response = connection.send_receive(cmd, timeout=2)
    logger.debug(response.hex())
    # print(response.hex())
    # print("fffffffffff8888888888")

    # below program hardware version 0x0001
    cmd = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=35,
        count=1,
        value0=0x01,
        value1=0x00,
    )
    response = connection.send_receive(cmd, timeout=1)
    logger.debug(response.hex())
    gl.set_value("dusn", dusn)

    update_test_summary("Control",{
        "test_item": "write_pca_dusn",
        "test_value": dusn,
        "lsl": dusn,
        "usl": dusn,
        "status":"PASS",
    })
    return True, dusn
def read_pca_dusn__(connections, logger, **kwargs):
    dusn = "0045007f000400000001"
    logger.debug(f"dusn:{dusn}")
    gl.set_value("platform", dusn[:4])
    # gl.set_value('site_code', to_hex(res.get("site_code"), 2))
    gl.set_value("site_code", dusn[8:12])
    # gl.set_value("dusn", to_hex(res.get("device_number"), 4))
    gl.set_value("dusn", dusn)
    gl.set_value("codenticode", dusn)
    gl.set_value("pn", dusn[4:8])

    # gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
    gl.set_value("product_code", dusn[4:8])
    gl.set_value("dusn", dusn[-8:])
    return True, "PASS"
def read_pca_dusn(connections, logger, **kwargs):


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
            if response[1] == 0x89 and response[2] == 0x00:
                dusns = [f"{byte:02x}" for byte in response]
                dusn = f"{dusns[4]}{dusns[3]}{dusns[6]}{dusns[5]}{dusns[8]}{dusns[7]}{dusns[12]}{dusns[11]}{dusns[10]}{dusns[9]}".lower()
                break
        except Exception as ex:
            logger.debug(str(ex))
        time.sleep(1)

    if len(dusns) > 12 and len(dusn) > 0:
        if dusn.upper() == gl.get_value("dusn").upper():

            gl.set_value("platform", dusn[:4])
            # gl.set_value('site_code', to_hex(res.get("site_code"), 2))
            gl.set_value("site_code", dusn[8:12])
            # gl.set_value("dusn", to_hex(res.get("device_number"), 4))
            gl.set_value("dusn", dusn)
            gl.set_value("codenticode", dusn)
            # gl.set_value("pn", to_hex(res.get("product_code"), 2)[2:])
            gl.set_value("pn",dusn[4:8])

            # gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
            gl.set_value("product_code", dusn[4:8])
            print("**********************..........")

            update_test_summary("Control",{
                "test_item": "read_pca_dusn",
                "test_value": dusn,
                "lsl": gl.get_value("dusn"),
                "usl": gl.get_value("dusn"),
                "status": "PASS"
            })
            gl.set_value("dusn", dusn[-8:])
            return True, dusn
        else:
            update_test_summary("Control",{
                "test_item": "read_pca_dusn",
                "test_value": dusn,
                "lsl": gl.get_value("dusn"),
                "usl": gl.get_value("dusn"),
                "status": "FAIL"
            })

            return False, dusn
    else:
        update_test_summary("Control",{
            "test_item": "read_pca_dusn",
            "test_value": dusn,
            "lsl": gl.get_value("dusn"),
            "usl": gl.get_value("dusn"),
            "status": "FAIL"
        })
        return False, dusn


def flash_stm32(CLI_PATH,hex_file, port="SWD"):
    cmd = [
        CLI_PATH,
        "-c", f"port={port}",
        "-e", "all",
        "-w", hex_file,
        # "-v",          # 验证
        "-rst"  # 复位
    ]

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if result.returncode == 0:
            return True, "PASS"
            # print("✅ 烧录成功")
        else:
            # print("❌ 烧录失败")
            return False, "FAIL"

    except Exception as e:
        # print("异常:", e)
        return False, str(e)

#     cells = config.get("cells")[0]
#     user_config = cells.get("user_config")
#     flexflow = user_config.get("flexflow")
#     TBBUID = user_config.get("TBBUID")
#
#     if " " in codentify and len(codentify) == 17:
#         if flexflow:
#             logger.debug(flexflow)
#             status, info = routing_check(codentify, TBBUID)
#             if status:
#                 get_debug_info(info)
#                 return True, codentify
#             else:
#                 gl.set_value("Error_Code", "R001")
#                 return False, "R001"
#
#         return True, codentify
#     else:
#         return False, codentify
#
#
# def read_codentify(connections, logger, **kwargs):
#
#     connection = connections.get("serial_dut")
#     cmd_codentify = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
#     )
#
#     response = None
#
#     for i in range(15):
#         response = connection.send_receive(cmd_codentify, timeout=1)
#         if response[5] == 0x88 and response[6] == 0x03:
#             break
#         time.sleep(1)
#     codentifyCode = response[7:21].decode("utf-8").replace(" ", "")
#
#     status = False
#     if gl.get_value("codentify").replace(" ", "").upper() == codentifyCode.upper():
#         status = True
#     # gl.set_value("dusn", gl.get_value("codenticode"))
#     if not status:
#         gl.set_value("error_code", kwargs.get("error_code"))
#     return status, codentifyCode
#
#
# def read_dusn_control(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     cmd_dusn_control = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
#     )
#     response = None
#     dusns = []
#     dusn = ""
#     for i in range(15):
#         try:
#             response = connection.send_receive(cmd_dusn_control, timeout=1)
#             if response[5] == 0x89 and response[6] == 0x00:
#                 dusns = [f"{byte:02x}" for byte in response]
#                 dusn = f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}".upper()
#                 break
#         except Exception as ex:
#             print(str(ex))
#         time.sleep(1)
#
#
#
#     if len(dusns) > 12 and len(dusn) > 0:
#         gl.set_value("platform", f"{dusns[8]}{dusns[7]}")
#         gl.set_value("site_code", f"{dusns[12]}{dusns[11]}")
#         gl.set_value("dusn", dusn[-8:])
#         gl.set_value("product_code", f"{dusns[10]}{dusns[9]}")
#
#         gl.set_value("codenticode", dusn)
#         limit = kwargs.get("limit").get("min")[:8]
#         if not dusn.lower().startswith(limit.lower()):
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, dusn
#     else:
#         return False, dusn
#     return True, dusn
#
#
# def read_dusn_engine(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     cmd_dusn_engine = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
#     )
#     response = None
#     dusns = []
#     dusn = ""
#     for i in range(15):
#         response = connection.send_receive(cmd_dusn_engine, timeout=1)
#         if response[5] == 0x89 and response[6] == 0x00:
#             dusns = [f"{byte:02x}" for byte in response]
#             dusn = (
#                 f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}".upper()
#             )
#             break
#         time.sleep(1)
#
#     if len(dusns) > 12 and len(dusn) > 0:
#         limit = kwargs.get("limit").get("min")[:8]
#         if not dusn.lower().startswith(limit.lower()):
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, dusn
#     else:
#         return False, dusn
#     return True, dusn
#
#
# def read_fw_control(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     cmd_fw = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x00
#     )
#
#     response = None
#     fw = ""
#     for i in range(5):
#         response = connection.send_receive(cmd_fw, timeout=1)
#         if response[5] == 0x88 and response[6] == 0x00:
#             fw = f"{response[9]}.{response[10]}.{response[11]}"
#             break
#
#     lsl = kwargs.get("limit").get("min")
#     usl = kwargs.get("limit").get("max")
#
#     if fw == lsl and fw == usl:
#         return True, fw
#     else:
#         gl.set_value("error_code", kwargs.get("error_code"))
#         return False, fw
#
#
# def read_fw_engine(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     cmd_fw = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x00
#     )
#     response = None
#     fw = ""
#     for i in range(5):
#         response = connection.send_receive(cmd_fw, timeout=1)
#         if response[5] == 0x88 and response[6] == 0x00:
#             fw = f"{response[9]}.{response[10]}.{response[11]}"
#             break
#
#     lsl = kwargs.get("limit").get("min")
#     usl = kwargs.get("limit").get("max")
#     if fw == lsl and fw == usl:
#         return True, fw
#     else:
#         gl.set_value("error_code", kwargs.get("error_code"))
#         return False, fw
#
#
# def read_event_logs(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     cmd = bytes([0xC0, 0x10, 0x02, 0x01, 0x01, 0x75, 0xD6])
#     response = connection.send_receive(cmd, timeout=1)
#     rows = int.from_bytes(response[16:19], "little")
#     cmd = [0xC0, 0x10, 0x07, 0x01, 0x02, 0x00, 0x02]
#     event_logs = []
#     for i in range(rows):
#         for j in range(5):
#             try:
#                 ibytes = list(i.to_bytes(3, "little"))
#                 cmd_out = cmd.copy()
#                 cmd_out.extend(ibytes)
#                 cmd_out.extend(builder.crc16(bytes(cmd_out[1:])))
#                 response = connection.send_receive(bytes(cmd_out), timeout=1)
#                 usage = list(response[23:])
#                 startReason = (usage[34] & 0xE0) >> 5
#                 heatingDuration = 2 * usage[55]
#                 pauseDuration = 3 * usage[56]
#                 stopReason = usage[61]
#                 puffCount = usage[110]
#                 if startReason == 2 and heatingDuration == 0 and stopReason == 5:
#                     continue
#                 event_logs.append(
#                     {
#                         "startReason": startReason,
#                         "heatingDuration": heatingDuration,
#                         "pauseDuration": pauseDuration,
#                         "stopReason": stopReason,
#                         "puffCount": puffCount,
#                     }
#                 )
#                 break
#             except Exception as e:
#                 logger.error(f"error: {e}")
#             time.sleep(2)
#
#     stop_filters = [3, 9, 12]
#
#     event_logs_valid = []
#     total_logs = []
#     pause_logs = []
#     debug = False
#     status = True
#     error = "PASS"
#     puffCount = 0
#     rawPuffCount = 0
#     puffCountList = []
#     for log in event_logs:
#         if log["startReason"] == 1:
#             if log["heatingDuration"] == 366:
#                 if log["stopReason"] == 2:
#                     event_logs_valid.append(log)
#                     total_logs.append(log)
#                 elif log["stopReason"] in stop_filters:
#                     total_logs.append(log)
#                 else:
#                     status = False
#                     error = f"E003,Stop Reason Fail,{log['stopReason']},2,2"
#                     # break
#             else:
#                 if log["stopReason"] in stop_filters:
#                     total_logs.append(log)
#                 elif log["stopReason"] == 5 and log["heatingDuration"] == 0:
#                     pass
#                 else:
#                     status = False
#                     error = f"E003,Stop Reason Fail,{log['stopReason']},2,2"
#                     # break
#         else:
#             status = False
#             error = f"E002,Start Reason Fail,{log['startReason']},1,1"
#             # break
#         if log["heatingDuration"] != 366 and not log["stopReason"] in stop_filters and status:
#             if log["stopReason"] == 5 and log["heatingDuration"] == 0:
#                 pass
#             else:
#                 status = False
#                 error = f"E004,Heat duration Fail,{log['heatingDuration']},366,366"
#             # break
#         if log["pauseDuration"] > 0:
#             pause_logs.append(log)
#     puffLogs = event_logs_valid
#     if debug:
#         puffLogs = event_logs_valid[-8:]
#     for log in puffLogs:
#         puffCount = puffCount + log["puffCount"]
#     lsl = 8
#     usl = 12
#     if debug:
#         usl = 20
#     if len(event_logs_valid) >= lsl:
#         if len(event_logs_valid) > usl:
#             status = False
#             error = f"E001,Heat count Fail,{len(event_logs_valid)},{lsl},{usl}"
#     else:
#         status = False
#         error = f"E001,Heat count Fail,{len(event_logs_valid)},{lsl},{usl}"
#     if status and len(pause_logs) == 0 and (not gl.get_value("X_PAUSE")):
#         status = False
#         error = f"E005,Pause count Fail,{len(pause_logs)},1,99999"
#     if status and puffCount > 6:
#         status = False
#         error = f"E009,Puff count fail,{puffCount},0,6"
#
#     for log in event_logs_valid:
#         puffCountList.append(log["puffCount"])
#         if log["puffCount"] > 2:
#             status = False
#             rawPuffCount = log["puffCount"]
#             error = f"E008,Puff count fail,{log['puffCount']},0,2"
#             break
#     if status:
#         rawPuffCount = max(puffCountList)
#     error_code = error.split(",")[0]
#     if not status:
#         gl.set_value("error_code", error_code)
#     gl.set_value("error", error)
#     gl.set_value("debug", debug)
#     gl.set_value("autostart_count", len(event_logs_valid))
#     gl.set_value("pause_logs", len(pause_logs))
#     gl.set_value("event_logs", event_logs)
#     gl.set_value("puff_count", puffCount)
#     gl.set_value("raw_puff_count", rawPuffCount)
#
#     event_log_name = f"Unit_Log_{time.strftime('%Y-%m-%d')}.csv"
#     log_path = os.path.join(os.path.abspath(''), "log")
#     if not os.path.exists(log_path):
#         os.makedirs(log_path)
#     first_row = False
#     log_full_path = os.path.join(log_path, event_log_name)
#     if not os.path.exists(log_full_path):
#         first_row = True
#     with open(log_full_path,"a+") as f:
#         if first_row:
#             f.write(f"SN,event_count,start_reason, heating_duration, pause_duration, stop_reason, raw_puff_count, puff_count\n")
#         f.write(f"{gl.get_value('codentify_code')},{gl.get_value('autostart_count')},{check_start_reason(connections, logger, **kwargs)[-1]},{check_heating_duration(connections, logger, **kwargs)[-1]},{check_pause_duration(connections, logger, **kwargs)[-1]},{check_stop_reason(connections, logger, **kwargs)[-1]},{gl.get_value('raw_puff_count')},{gl.get_value('puff_count')}\n")
#
#     return True, "PASS"
#     # return status, error.split(",")[0]
#
#
# def check_autostart_count(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     autostart_count = gl.get_value("autostart_count")
#     if error == "PASS":
#         return True, str(autostart_count)
#     else:
#         errors = error.split(",")
#         if errors[0] == "E001":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, str(autostart_count)
#         else:
#             return True, str(autostart_count)
#
#
# def check_start_reason(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     if error == "PASS":
#         return True, "1"
#     else:
#         errors = error.split(",")
#         if errors[0] == "E002":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, errors[2]
#         else:
#             return True, str(1)
#
#
# def check_stop_reason(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     if error == "PASS":
#         return True, str(2)
#     else:
#         errors = error.split(",")
#         if errors[0] == "E003":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, errors[2]
#         else:
#             return True, str(2)
#
#
# def check_heating_duration(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     if error == "PASS":
#         return True, "366"
#     else:
#         errors = error.split(",")
#         if errors[0] == "E004":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, errors[2]
#         else:
#             return True, "366"
#
#
# def check_pause_duration(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     pause_count = gl.get_value("pause_logs")
#     if error == "PASS":
#         return True, str(pause_count)
#     else:
#         errors = error.split(",")
#         if errors[0] == "E005":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, "0"
#         else:
#             return True, str(pause_count)
#
# def check_raw_puff_count(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     raw_puff_count = gl.get_value("raw_puff_count")
#     if error == "PASS":
#         return True, str(raw_puff_count)
#     else:
#         errors = error.split(",")
#         if errors[0] == "E008":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, f"{raw_puff_count}"
#         else:
#             return True, str(raw_puff_count)
# def check_puff_count(connections, logger, **kwargs):
#     error = gl.get_value("error")
#     puff_count = gl.get_value("puff_count")
#     if error == "PASS":
#         return True, str(puff_count)
#     else:
#         errors = error.split(",")
#         if errors[0] == "E009":
#             gl.set_value("error_code", kwargs.get("error_code"))
#             return False, f"{puff_count}"
#         else:
#             return True, str(puff_count)
#
#
# def write_codentify_code_control(connections, logger, **kwargs):
#     connection = connections.get("serial_dut")
#     codentify = kwargs.get("codentify").replace(" ", "")
#     codentify_write_frame = builder.build_write_request_frame(
#         mode="hid",
#         reply_hop_count=0,
#         hop_count=0,
#         parameter=0x08,
#         pnum=37,
#         count=7,
#         value=codentify,
#     )
#     response = connection.send_receive(codentify_write_frame, timeout=1)
#     logger.debug(response)
#     cmd_codentify = builder.build_read_request_frame(
#         mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
#     )
#     response = None
#
#     for i in range(3):
#         response = connection.send_receive(cmd_codentify, timeout=1)
#         logger.debug(response)
#         if response[5] == 0x88 and response[6] == 0x03:
#             break
#         time.sleep(0.3)
#     codentify_read = response[7:21].decode("utf-8")
#     if codentify == codentify_read:
#         return True
#     return False
#
#
def read_station(connections, logger, **kwargs):
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")

    step_result = {
        "test_item": "TBBUID",
        "test_value": TBBUID,
        "lsl":TBBUID,
        "usl":TBBUID,
        "status": "PASS"
    }
    update_test_summary("Control",step_result)

    if TBBUID:
        return True, TBBUID
    return False, TBBUID

def update_test_summary(group_name, step_result:dict):
    test_summary = gl.get_value("test_summary")
    if group_name in test_summary:
        test_summary[group_name].append(step_result)
    else:
        test_summary[group_name] = [step_result]
    gl.set_value("test_summary", test_summary)