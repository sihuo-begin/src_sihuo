# -*- mode: python ; coding: utf-8 -*-
import re
import binascii
import time
import numpy as np
from multiprocessing import Process, Event
import yaml
from datetime import datetime, timezone, timedelta
from src.ui.ask_question import ask_question
from src.libs import global_var as gl
from src.libs.ni import NIEquipment
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.common import *
from src.libs.raw_data import *
from src.libs.uut import Uut
from src.libs.motor import MotorController
from src.steps import common_steps

# from src.libs.ble_driver import init, main, rssi_measure

ONCE = False
POC_BUILD = False
builder = NetworkFrameBuilder()
uut = Uut()


def start_test(connections, logger, **kwargs):
    config = gl.get_value("layout_config")
    logger.info(config)
    station = config.get("station")
    TBBUID = config.get("TBBUID", " ")
    cell_id = kwargs.get("cell_name", "")
    cell_number = re.findall(r"\d+", cell_id)
    if "MT7VC" in station and not POC_BUILD:
        init_motor(connections, logger)
    if not POC_BUILD and "MT7VC" not in station:
        detect_previous_dut(connections, logger)
        unlock_dummy_charger(connections, logger)
        if "holder_MT11C" in station:
            remove_cavity_file(cavity_id=cell_number[0])
    if not POC_BUILD and "MT7VC" in station:
        ni_detect_start(connections, logger)
    if "MT7VC" in station:
        detect_dut_mt7vc(connections, logger)
    if "holder_MT11C" in station:
        detect_dut_mt11c_control(connections, logger)
        create_cavity_file(cavity_id=str(cell_number[0]))
    if "MT1_holder_control" in station:
        detect_dut_mt3c(connections, logger)
    if "MT1_holder_control" not in station:
        read_codentify_code(connections=connections, logger=logger, station=station)

    if TBBUID:
        return True, TBBUID

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, TBBUID


def read_station(connections, logger, **kwargs):
    config = gl.get_value("layout_config")
    logger.info(config)
    station = config.get("station")
    TBBUID = config.get("TBBUID", " ")
    if "holder_MT11C" in station:
        detect_dut_mt11c_engine(connections, logger, **kwargs)
    if TBBUID:
        return True, TBBUID

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, TBBUID


def get_cell_number(connections, logger, **kwargs):
    cell_id = kwargs.get("cell_name", "")
    cell_number = re.findall(r"\d+", cell_id)
    # cell_id = '1'   # Hardcode for POC build
    logger.info(f"CELL ID is {cell_number[0]}")

    return True, cell_number[0]


def unlock_dummy_charger(connections, logger):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_write_request_frame(
                    mode="hid",
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x05,
                    value=0x00,
                    value1=0x00,
                )
                logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.info(response)
                if response:
                    break
            else:
                time.sleep(1)
                continue
        except Exception as e:
            logger.debug(e)
            time.sleep(1)
            continue
    return


def ni_detect_start(connections, logger, **kwargs):
    logger.debug("detect start button and dut put in")
    ni_device = NIEquipment(device_name="Dev1")
    start = gl.get_value("layout_config").get("fixture_io").get("start")
    dut = gl.get_value("layout_config").get("fixture_io").get("uut")
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            response = ni_device.read_digital(dut, timeout=1)  # Detect UUT in Tester
            # logger.debug(response)
            if response:
                break
            else:
                time.sleep(0.05)
                continue
        except Exception as e:
            # logger.debug(e)
            time.sleep(0.05)
            continue
    time.sleep(0.5)
    logger.info(f"detected dut already put in tester")
    while not stop_event.is_set():
        try:
            response = ni_device.read_digital(start, timeout=1)  # Start button
            # logger.debug(response)
            if response:
                break
            else:
                time.sleep(0.05)
                continue
        except Exception as e:
            # logger.debug(e)
            time.sleep(0.05)
            continue
    time.sleep(1)
    logger.info(f"detected start button passed")

    return


def detect_previous_dut(connections, logger):
    config = gl.get_value("layout_config")
    logger.info(config)
    station = config.get("station")
    stop_event = gl.get_value("stop_event")
    if "MT7VC" in station:
        connection = connections.get("uart")
        logger.info(f"connection is :{connection}.")
        while not stop_event.is_set():
            try:
                if connection.ensure_connected():
                    cmd_frame = builder.build_read_request_frame(
                        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
                    )
                    logger.debug(f"build cmd: {cmd_frame.hex()}")
                    response = connection.send_receive(cmd_frame, timeout=1)
                    logger.debug(response.hex())
                    if "c0010015" == response.hex():
                        break
                    else:
                        time.sleep(1)
                        continue
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                logger.debug(e)
                time.sleep(1)
                break
        # dut = gl.get_value("layout_config").get("fixture_io").get("uut")
        # ni_device = NIEquipment(device_name="Dev1")
        # while True:
        #     try:
        #         response = ni_device.read_digital(dut, timeout=1)  # Detect UUT Put in Tester
        #         logger.debug(response)
        #         if not response:
        #             break
        #         else:
        #             time.sleep(0.05)
        #             continue
        #     except Exception as e:
        #         logger.debug(e)
        #         time.sleep(0.05)
        #         continue
        # time.sleep(2)
        # logger.info(f'detected dut already not in tester')
    if "holder_MT11C" in station:
        connection = connections.get("usb")
        logger.info(f"connection is :{connection}.")
        while not stop_event.is_set():
            try:
                if connection.ensure_connected():
                    cmd_frame = builder.build_read_request_frame(
                        mode="hid", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
                    )
                    logger.debug(f"build cmd: {cmd_frame.hex()}")
                    response = connection.send_receive(cmd_frame, timeout=1)
                    logger.debug(response)
                    if not response:
                        break
                    else:
                        time.sleep(1)
                        continue
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                logger.debug(e)
                time.sleep(1)
                break
    logger.info(f"detect previous dut already removed")

    return


def scan(connections, logger, **kwargs):
    dusn = ask_question("Please scan DUSN=>", image_path=r"C:\picture\111.jpg", auto_trigger={"func_name": r"hello"})
    logger.debug(f"scane dusn:{dusn}")
    if not dusn:
        if dusn is None or dusn == "":
            logger.warning("User cancel")
            return False, "User cancel"
    logger.info("Scanning device (simulate scan)...")
    return True, "SCANNED_OK"


def detect_dut_mt11c_control(connections, logger, **kwargs):  # for MT11C
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    logger.info(f"connection is :{connection}.")
    mode = "uart" if "UART" in str(connection) else "hid"
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode=mode, read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
                )
                # logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                crc = verify_crc(logger=logger, data=response, connection='hid')
                logger.info(f'CRC value is {crc}')
                # logger.debug(response)
                if response and crc:
                    break
                else:
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            # logger.debug(e)
            time.sleep(1)
            continue
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("platform_code", 2),
            ("product_code", 2),
            ("site_code", 2),
            ("device_number", 4),
            ("hardware_revision", 2),
            ("reserve", 2),
        ],
    )
    logger.debug(res)
    codenticode = "{0}{1}{2}{3}".format(
        to_hex_without_head(res.get("platform_code"), 2),
        to_hex_without_head(res.get("product_code"), 2),
        to_hex_without_head(res.get("site_code"), 2),
        to_hex_without_head(res.get("device_number"), 4),
    )
    logger.debug(f"codenticode:{codenticode}")
    gl.set_value("codenticode", codenticode)
    gl.set_value("platform_code", (to_hex(res.get("platform_code"), 2))[2:])
    gl.set_value("platform", (to_hex(res.get("platform_code"), 2))[2:])
    gl.set_value("site_code", (to_hex(res.get("site_code"), 2))[2:])
    gl.set_value("dusn", (to_hex(res.get("device_number"), 4))[2:])
    gl.set_value("pn", (to_hex(res.get("product_code"), 2))[2:])
    gl.set_value("product_code", f"{prodcut_map.get((hex(res.get('product_code')))[2:])}")

    gl.set_value("control_codenticode", codenticode)
    gl.set_value("control_pn", (to_hex(res.get("product_code"), 2))[2:])
    gl.set_value("control_dusn", (to_hex(res.get("device_number"), 4))[2:])
    gl.set_value("control_platform", (to_hex(res.get("platform_code"), 2))[2:])

    # return True, (to_hex(res.get("device_number"), 4)[2:])
    return


def detect_dut_mt11c_engine(connections, logger, **kwargs):  # for MT11C
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    logger.info(f"connection is :{connection}.")
    mode = "uart" if "UART" in str(connection) else "hid"
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode=mode, read_only=True, reply_hop_count=2, hop_count=2, parameter=0x01
                )
                logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.debug(response)
                crc = verify_crc(logger=logger, data=response, connection='hid')
                logger.info(f'CRC value is {crc}')
                if response and crc:
                    break
                else:
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            logger.debug(e)
            time.sleep(1)
            continue
    res1 = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("platform_code_e", 2),
            ("product_code_e", 2),
            ("site_code_e", 2),
            ("device_number_e", 4),
            ("hardware_revision_e", 2),
            ("reserve_e", 2),
        ],
    )
    logger.debug(res1)
    engine_codenticode = "{0}{1}{2}{3}".format(
        to_hex_without_head(res1.get("platform_code_e"), 2),
        to_hex_without_head(res1.get("product_code_e"), 2),
        to_hex_without_head(res1.get("site_code_e"), 2),
        to_hex_without_head(res1.get("device_number_e"), 4),
    )
    logger.debug(f"codenticode:{engine_codenticode}")
    gl.set_value("engine_codenticode", engine_codenticode)
    gl.set_value("engine_pn", (to_hex(res1.get("product_code_e"), 2))[2:])
    gl.set_value("engine_dusn", (to_hex(res1.get("device_number_e"), 4))[2:])
    gl.set_value("engine_platform", (to_hex(res1.get("platform_code_e"), 2))[2:])
    gl.set_value("engine_site_code", (to_hex(res1.get("site_code_e"), 2))[2:])

    # return True, (to_hex(res1.get("device_number_e"), 4)[2:])
    return


def check_dusn_engine(connections, logger, **kwargs):
    platform_code = gl.get_value("engine_platform")
    product_code = gl.get_value("engine_pn")
    device_number = gl.get_value("engine_dusn")
    site_code = gl.get_value("engine_site_code")
    config = gl.get_value("layout_config")
    config_site_code = config.get("site_code", "")
    dusn = platform_code + product_code + site_code + device_number
    device_number_int = int("0x" + device_number, 16)
    if platform_code != "0029":
        logger.warning("check platform code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, platform_code
    if product_code != "0063":
        logger.warning("check platform code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, product_code
    if device_number_int < 805306368:
        logger.warning("check device number failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, device_number
    if site_code != config_site_code:
        logger.warning("check site code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, site_code
    if "00290063" not in dusn:
        logger.warning("check DUSN failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, dusn.upper()
    logger.info(f"DUSN: {dusn}")

    return True, dusn.upper()


def check_dusn(connections, logger, **kwargs):
    platform_code = gl.get_value("platform_code")
    product_code = gl.get_value("pn")
    device_number = gl.get_value("dusn")
    site_code = gl.get_value("site_code")
    config = gl.get_value("layout_config")
    config_site_code = config.get("site_code", "")
    device_number_int = int("0x" + device_number, 16)
    limit_dusn = kwargs.get("limit").get("max")
    limit_platform = limit_dusn[:4]
    limit_product = limit_dusn[4:8]
    if platform_code != limit_platform:
        logger.warning("check platform code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, platform_code
    if product_code.upper() != limit_product:
        logger.warning("check product code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, product_code
    if device_number_int >= 805306368:
        logger.warning("check device number failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, device_number
    if site_code != config_site_code:
        logger.warning("check site code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, site_code
    dusn = platform_code + product_code + site_code + device_number
    logger.info(f"DUSN: {dusn}")
    # if '00390066' not in dusn:
    if limit_dusn[:4] not in dusn.upper() or limit_dusn[4:8] not in dusn.upper():
        logger.warning("check DUSN failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, dusn.upper()

    return True, dusn.upper()


def detect_dut_mt7vc(connections, logger, **kwargs):  # for MT7VC
    connection = connections.get("uart")
    stop_event = gl.get_value("stop_event")
    logger.info(f"connection is :{connection}.")
    mode = "uart" if "UART" in str(connection) else "hid"
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode=mode, read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
                )
                # logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                response1 = response.replace(cmd_frame, b"")
                crc = verify_crc(logger=logger, data=response1, connection='uart')
                logger.info(f'CRC value is {crc}')
                # logger.debug(response)
                if "c0010015" != response.hex() and crc:
                    break
                else:
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            # logger.debug(e)
            time.sleep(1)
            continue
    res = builder.unpack_payload_fields(
        payload=response,
        offset=7,
        fields=[
            ("platform_code", 2),
            ("product_code", 2),
            ("site_code", 2),
            ("device_number", 4),
            ("hardware_revision", 2),
            ("reserve", 2),
        ],
    )
    logger.debug(res)
    codenticode = "{0}{1}{2}{3}".format(
        to_hex_without_head(res.get("platform_code"), 2),
        to_hex_without_head(res.get("product_code"), 2),
        to_hex_without_head(res.get("site_code"), 2),
        to_hex_without_head(res.get("device_number"), 4),
    )
    logger.debug(f"codenticode:{codenticode}")
    gl.set_value("codenticode", codenticode)
    gl.set_value("platform_code", (to_hex(res.get("platform_code"), 2))[2:])
    gl.set_value("platform", (to_hex(res.get("platform_code"), 2))[2:])
    gl.set_value("site_code", (to_hex(res.get("site_code"), 2))[2:])
    gl.set_value("dusn", (to_hex(res.get("device_number"), 4))[2:])
    gl.set_value("pn", (to_hex(res.get("product_code"), 2))[2:])
    gl.set_value("product_code", f"{prodcut_map.get((hex(res.get('product_code')))[2:])}")

    # return True, (to_hex(res.get("device_number"), 4))[2:]
    return


def detect_dut_mt3c(connections, logger, **kwargs):
    connection = connections.get("uart")
    stop_event = gl.get_value("stop_event")
    logger.info(f"connection is :{connection}.")
    mode = "uart" if "UART" in str(connection) else "hid"
    while not stop_event.is_set():
        if connection.ensure_connected():
            cmd_frame = builder.build_read_request_frame(
                mode=mode, read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response.hex())
            if "c0010015" != response.hex() and "" != response.hex():
                break
            else:
                time.sleep(1)
                continue
        else:
            time.sleep(1)
            continue
    gl.set_value("platform_code", "0041")
    gl.set_value("platform", "0041")
    gl.set_value("site_code", "0004")
    gl.set_value("pn", "007a")
    gl.set_value("dusn", "00000001")

    # return True, gl.get_value('dusn')
    return


def mt1_ask_question(connections, logger, **kwargs):
    logger.debug("Scan DUSN into dut for board: Control")
    device_number = None
    device_number = ask_question("请扫描Control Device Number(DUSN)=>")
    device_number = device_number.strip()
    if not device_number:
        if device_number is None or device_number == "":
            logger.warning("User Scan cancel")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "False"
    if len(device_number) != 20:
        logger.warning("User Scan Control DUSN len incorrect")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    gl.set_value("mt3_control_device_number", device_number)

    logger.debug("Scan DUSN into dut for board: engine")
    device_number = None
    device_number = ask_question("请扫描Engine Device Number(DUSN)=>")
    device_number = device_number.strip()
    if not device_number:
        if device_number is None or device_number == "":
            logger.warning("User Scan cancel")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "False"
    if len(device_number) != 20:
        logger.warning("User Scan Engine DUSN len incorrect")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    gl.set_value("mt3_engine_device_number", device_number)

    question = ask_question("请放入UUT开始测试输入Y开始测试")

    return True, "True"


def read_dusn(connection, logger, i):
    cmd_dusn = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=i, hop_count=i, parameter=0x001
    )
    logger.debug(cmd_dusn)
    response = None
    for i in range(5):
        response = connection.send_receive(cmd_dusn, timeout=1)
        if response[5] == 0x89 and response[6] == 0x00:
            print("**********************Correctly")
            break
    logger.debug(response)
    res = builder.unpack_payload_fields(
        payload=response,
        offset=7,
        fields=[
            ("platform_code", 2),
            ("product_code", 2),
            ("site_code", 2),
            ("device_number", 4),
            ("hardware_revision", 2),
            ("reserve", 2),
        ],
    )
    logger.debug(res)
    dusn = "{0}{1}{2}{3}{4}".format(
        to_hex_without_head(res.get("platform_code"), 2),
        to_hex_without_head(res.get("product_code"), 2),
        to_hex_without_head(res.get("site_code"), 2),
        to_hex_without_head(res.get("device_number"), 4),
        to_hex_without_head(res.get("hardware_revision"), 2),
    )
    logger.debug(dusn)

    return dusn


def write_dusn_control(connections, logger, **kwargs):
    """
    platform_code = 0x0039
    product_code = 0x0066
    site_code = 0x0004
    device_number = 0xffffffff
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("uart")
    dusn_read = read_dusn(connection=connection, logger=logger, i=0)
    if "ffffffffffffffffffff" in dusn_read:
        logger.debug(f"Control Dusn is :{dusn_read}, need to write")
    else:
        return True, dusn_read
    # device_number = ask_question("请扫描Control Device Number(DUSN)=>")
    logger.debug("Write DUSN into dut for board: Control")
    # if not device_number:
    #     if device_number is None or device_number == "":
    #         logger.warning("User Scan cancel")
    #         gl.set_value('error_code', kwargs.get("error_code"))
    #         return False, "False"
    gl_device_number = gl.get_value("mt3_control_device_number")
    device_number = gl_device_number[12:]
    if len(device_number) != 8:
        logger.debug(f"Scan incorrect device number:{device_number}")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, device_number
    device_number = int("0x" + device_number, 16)
    logger.debug(f"Scan Device number:{device_number}")
    platform_code = 0x0041
    product_code = 0x007A
    site_code = 0x0004
    hardware_version = 0x0001

    if device_number >= 805306368:
        logger.warning("User Scan incorrect control DUSN")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    hex_device_number = to_hex_without_head(device_number, 4)
    hex_platform_code = to_hex_without_head(int(platform_code), 2)
    hex_product_code = to_hex_without_head(int(product_code), 2)
    hex_site_code = to_hex_without_head(int(site_code), 2)
    hex_hardware_version = to_hex_without_head(int(hardware_version), 2)

    logger.debug(f"Scan Device number hex:{hex_device_number}")

    dusn = f"{hex_platform_code}{hex_product_code}{hex_site_code}{hex_device_number}{hex_hardware_version}"
    logger.debug(f"Control Dusn is :{dusn}")
    dusn1 = f"{hex_platform_code}{hex_product_code}{hex_site_code}{hex_device_number}"

    platform_code = list(binascii.unhexlify(hex(platform_code)[2:].zfill(4)))
    product_code = list(binascii.unhexlify(hex(product_code)[2:].zfill(4)))
    site_code = list(binascii.unhexlify(hex(site_code)[2:].zfill(4)))
    device_number = list(binascii.unhexlify(hex(int(device_number))[2:].zfill(8)))
    hardware_version = list(binascii.unhexlify(hex(hardware_version)[2:].zfill(4)))

    # write platform_code
    dusn_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=2,
        count=6,
        value0=platform_code[1],
        value1=platform_code[0],
        value2=product_code[1],
        value3=product_code[0],
        value4=site_code[1],
        value5=site_code[0],
        value6=device_number[3],
        value7=device_number[2],
        value8=device_number[1],
        value9=device_number[0],
    )
    response = connection.send_receive(dusn_write_frame, timeout=1)
    logger.debug(response.hex())

    # below program hardware version
    dusn_write_frame1 = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=35,
        count=1,
        value0=hardware_version[1],
        value1=hardware_version[0],
    )
    response = connection.send_receive(dusn_write_frame1, timeout=1)
    logger.debug(response.hex())

    logger.debug(f"codenticode:{dusn1}")
    gl.set_value("codenticode", dusn1)
    gl.set_value("platform_code", hex_platform_code)
    gl.set_value("platform", hex_platform_code)
    gl.set_value("site_code", hex_site_code)
    gl.set_value("dusn", hex_device_number)
    gl.set_value("pn", hex_product_code)
    gl.set_value("product_code", f"{prodcut_map.get(hex_product_code)}")

    gl.set_value("control_codenticode", dusn1)
    gl.set_value("control_pn", hex_product_code)
    gl.set_value("control_dusn", hex_device_number)
    gl.set_value("control_platform", hex_platform_code)

    # check DUSN
    dusn_read = read_dusn(connection=connection, logger=logger, i=0)
    if dusn == dusn_read:
        return True, dusn_read

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, dusn_read


def write_dusn_engine(connections, logger, **kwargs):
    """
    platform_code = 0x0039
    product_code = 0x0066
    site_code = 0x0004
    device_number = 0xffffffff
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("uart")
    dusn_read = read_dusn(connection=connection, logger=logger, i=1)
    if "ffffffffffffffffffff" in dusn_read:
        logger.debug(f"Engine Dusn is :{dusn_read}, need to write")
    else:
        return True, dusn_read
    # device_number = ask_question("请扫描Engine Device Number(DUSN)=>")
    logger.debug("Write DUSN into dut for board: engine")
    # if not device_number:
    #     if device_number is None or device_number == "":
    #         logger.warning("User Scan cancel")
    #         gl.set_value('error_code', kwargs.get("error_code"))
    #         return False, "False"
    gl_device_number = gl.get_value("mt3_engine_device_number")
    device_number = gl_device_number[12:]
    if len(device_number) != 8:
        logger.debug(f"Scan incorrect device number:{device_number}")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, device_number
    device_number = int("0x" + device_number, 16)
    logger.debug(f"Scan Device number:{device_number}")
    platform_code = 0x0029
    product_code = 0x0063
    site_code = 0x0004
    hardware_version = 0x0003
    if device_number < 805306368:
        logger.warning("User Scan incorrect engine DUSN")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    hex_device_number = to_hex_without_head(device_number, 4)
    hex_platform_code = to_hex_without_head(int(platform_code), 2)
    hex_product_code = to_hex_without_head(int(product_code), 2)
    hex_site_code = to_hex_without_head(int(site_code), 2)
    hex_hardware_version = to_hex_without_head(int(hardware_version), 2)

    logger.debug(f"Scan Device number hex:{hex_device_number}")

    dusn = f"{hex_platform_code}{hex_product_code}{hex_site_code}{hex_device_number}{hex_hardware_version}"
    logger.debug(f"Engine Dusn is :{dusn}")
    dusn1 = f"{hex_platform_code}{hex_product_code}{hex_site_code}{hex_device_number}"

    platform_code = list(binascii.unhexlify(hex(platform_code)[2:].zfill(4)))
    product_code = list(binascii.unhexlify(hex(product_code)[2:].zfill(4)))
    site_code = list(binascii.unhexlify(hex(site_code)[2:].zfill(4)))
    device_number = list(binascii.unhexlify(hex(int(device_number))[2:].zfill(8)))
    hardware_version = list(binascii.unhexlify(hex(hardware_version)[2:].zfill(4)))

    # write platform_code
    dusn_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=2,
        count=6,
        value0=platform_code[1],
        value1=platform_code[0],
        value2=product_code[1],
        value3=product_code[0],
        value4=site_code[1],
        value5=site_code[0],
        value6=device_number[3],
        value7=device_number[2],
        value8=device_number[1],
        value9=device_number[0],
    )
    response = connection.send_receive(dusn_write_frame, timeout=1)
    logger.debug(response.hex())

    # below program hardware version
    dusn_write_frame1 = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=35,
        count=1,
        value0=hardware_version[1],
        value1=hardware_version[0],
    )
    response = connection.send_receive(dusn_write_frame1, timeout=1)
    logger.debug(response.hex())

    gl.set_value("engine_codenticode", dusn1)
    gl.set_value("engine_pn", hex_product_code)
    gl.set_value("engine_dusn", hex_device_number)
    gl.set_value("engine_platform", hex_platform_code)
    gl.set_value("engine_site_code", hex_site_code)

    # check DUSN
    dusn_read = read_dusn(connection=connection, logger=logger, i=1)
    if dusn == dusn_read:
        return True, dusn_read

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, dusn_read


def write_codentify_code_control(connections, logger, **kwargs):
    connection = connections.get("uart")
    codentify = ask_question("请扫描Codentify Code=>")
    if not codentify:
        if codentify is None or codentify == "":
            logger.warning("User cancel")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "None"
    codentify_code = codentify.replace(" ", "")
    if len(codentify_code) != 14:
        logger.warning("codentify_code not correct")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, codentify_code
    logger.debug(f"Scan Codentify Code:{codentify_code}")
    gl.set_value("codentify_code", codentify_code)

    codentify_code_ascii = [ord(char) for char in codentify_code]
    logger.debug(codentify_code_ascii)
    codentify_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=37,
        count=7,
        value0=codentify_code_ascii[0],
        value1=codentify_code_ascii[1],
        value2=codentify_code_ascii[2],
        value3=codentify_code_ascii[3],
        value4=codentify_code_ascii[4],
        value5=codentify_code_ascii[5],
        value6=codentify_code_ascii[6],
        value7=codentify_code_ascii[7],
        value8=codentify_code_ascii[8],
        value9=codentify_code_ascii[9],
        value10=codentify_code_ascii[10],
        value11=codentify_code_ascii[11],
        value12=codentify_code_ascii[12],
        value13=codentify_code_ascii[13],
    )
    response = connection.send_receive(codentify_write_frame, timeout=1)
    logger.debug(response.hex())
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x0C
    )
    logger.debug(cmd_codentify)
    response = None

    for i in range(3):
        response = connection.send_receive(cmd_codentify, timeout=1)
        logger.debug(response.hex())
        if "c08803" in response.hex():
            break
        time.sleep(0.3)
    logger.debug(response)
    logger.debug(f"codentify response: {response.hex()}")
    match = re.findall(r"x03([A-Z0-9]+)", str(response).strip())
    codentify_read = match[0]
    logger.debug(f"codentify code read: {codentify_read}")
    # if codentify_code == codentify_read:
    if codentify_code in codentify_read:
        return True, codentify_code

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, codentify_code


def write_codentify_code_engine(connections, logger, **kwargs):
    connection = connections.get("uart")
    codentify_code = gl.get_value("codentify_code")
    logger.debug(f"Get GL Codentify Code:{codentify_code}")
    codentify_code_ascii = [ord(char) for char in codentify_code]
    logger.debug(codentify_code_ascii)
    codentify_write_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=37,
        count=7,
        value0=codentify_code_ascii[0],
        value1=codentify_code_ascii[1],
        value2=codentify_code_ascii[2],
        value3=codentify_code_ascii[3],
        value4=codentify_code_ascii[4],
        value5=codentify_code_ascii[5],
        value6=codentify_code_ascii[6],
        value7=codentify_code_ascii[7],
        value8=codentify_code_ascii[8],
        value9=codentify_code_ascii[9],
        value10=codentify_code_ascii[10],
        value11=codentify_code_ascii[11],
        value12=codentify_code_ascii[12],
        value13=codentify_code_ascii[13],
    )
    response = connection.send_receive(codentify_write_frame, timeout=1)
    logger.debug(response)
    cmd_codentify = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x0C
    )
    logger.debug(cmd_codentify)
    response = None

    for i in range(3):
        response = connection.send_receive(cmd_codentify, timeout=1)
        logger.debug(response)
        if "c08803" in response.hex():
            break
        time.sleep(0.3)
    logger.debug(response)
    logger.debug(f"codentify response: {response.hex()}")
    match = re.findall(r"x03([A-Z0-9]+)", str(response).strip())
    codentify_read = match[0]
    logger.debug(f"codentify code read: {codentify_read}")
    if codentify_code in str(codentify_read):
        return True, codentify_code
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, codentify_code


def write_authentication_key_control(connections, logger, **kwargs):
    logger.debug("Write Authentication Key into dut for control")
    connection = connections.get("uart")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=215,
        count=8,
        raw_bytes=True,
        value=bytes(holder_cont_authkey0),
        # value0 = holder_cont_authkey0[0],
        # value1 = holder_cont_authkey0[1],
        # value2 = holder_cont_authkey0[2],
        # value3 = holder_cont_authkey0[3],
        # value4 = holder_cont_authkey0[4],
        # value5 = holder_cont_authkey0[5],
        # value6 = holder_cont_authkey0[6],
        # value7 = holder_cont_authkey0[7],
        # value8 = holder_cont_authkey0[8],
        # value9 = holder_cont_authkey0[9],
        # value10 = holder_cont_authkey0[10],
        # value11 = holder_cont_authkey0[11],
        # value12 = holder_cont_authkey0[12],
        # value13 = holder_cont_authkey0[13],
        # value14 = holder_cont_authkey0[14],
        # value15 = holder_cont_authkey0[15],
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        count=8,
        pnum=223,
        raw_bytes=True,
        # value0=holder_cont_authkey1[0],
        # value1=holder_cont_authkey1[1],
        # value2=holder_cont_authkey1[2],
        # value3=holder_cont_authkey1[3],
        # value4=holder_cont_authkey1[4],
        # value5=holder_cont_authkey1[5],
        # value6=holder_cont_authkey1[6],
        # value7=holder_cont_authkey1[7],
        # value8=holder_cont_authkey1[8],
        # value9=holder_cont_authkey1[9],
        # value10=holder_cont_authkey1[10],
        # value11=holder_cont_authkey1[11],
        # value12=holder_cont_authkey1[12],
        # value13=holder_cont_authkey1[13],
        # value14=holder_cont_authkey1[14],
        # value15=holder_cont_authkey1[15],
        value=bytes(holder_cont_authkey1),
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AC,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(1)
    logger.debug("Control Write Authentication Finish")

    return True, "True"


def write_authentication_key_engine(connections, logger, **kwargs):
    logger.debug("Write Authentication Key into dut for Engine")
    connection = connections.get("uart")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=215,
        count=8,
        raw_bytes=True,
        value0=bytes(holder_eng_authkey0),
        # value0=authentication_key,
        # value1=authentication_key,
        # value2=authentication_key,
        # value3=authentication_key,
        # value4=authentication_key,
        # value5=authentication_key,
        # value6=authentication_key,
        # value7=authentication_key,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        count=8,
        pnum=223,
        raw_bytes=True,
        # value0=authentication_key,
        # value1=authentication_key,
        # value2=authentication_key,
        # value3=authentication_key,
        # value4=authentication_key,
        # value5=authentication_key,
        # value6=authentication_key,
        # value7=authentication_key,
        value0=bytes(holder_eng_authkey1),
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AC,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    logger.debug("Engine Write Authentication Key Finish")

    return True, "True"


def check_authentication_control_key0(connections, logger, **kwargs):
    connection = connections.get("uart")
    logger.debug("read control authentication key from UUT Key0")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AD,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response.hex())
    time.sleep(1)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        count=8,
        pnum=231,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    res = builder.unpack_payload_fields(payload=response, offset=13, fields=[("auth_response", 16)])
    # logger.info(res)
    # read_auth_key1 = list(res1["auth_response1"])
    # read_auth_key1 = list(res1["auth_response1"].to_bytes(16, 'big'))
    read_auth_key = list(reversed(binascii.unhexlify(hex(res["auth_response"])[2:].zfill(16))))
    if read_auth_key != holder_cont_authkey0_resp:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    read_key = int.from_bytes(read_auth_key[:2], "little")
    # logger.debug(f'read key:{read_key}')
    time.sleep(0.1)
    if read_key != 44988:
        logger.debug("check authentication key0 failed for board: control")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(read_key)

    return True, str(read_key)


def check_authentication_control_key1(connections, logger, **kwargs):
    connection = connections.get("uart")
    logger.debug("read control authentication key from UUT Key1")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AD,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.2)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        count=8,
        pnum=239,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    res = builder.unpack_payload_fields(payload=response, offset=13, fields=[("auth_response", 16)])
    # logger.info(res)
    # read_auth_key1 = list(res1["auth_response1"])
    # read_auth_key1 = list(res1["auth_response1"].to_bytes(16, 'big'))
    read_auth_key = list(reversed(binascii.unhexlify(hex(res["auth_response"])[2:].zfill(16))))
    if read_auth_key != holder_cont_authkey1_resp:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    read_key = int.from_bytes(read_auth_key[:2], "little")
    # logger.debug(f'read key:{read_key}')
    time.sleep(0.1)
    if read_key != 7116:
        logger.debug("check authentication key1 failed for board: control")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(read_key)

    return True, str(read_key)


def check_authentication_engine_key0(connections, logger, **kwargs):
    connection = connections.get("uart")
    logger.debug("read authentication key from UUT Key0")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AD,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.5)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        count=8,
        pnum=231,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    res = builder.unpack_payload_fields(payload=response, offset=13, fields=[("auth_response", 16)])
    # logger.info(res)
    # read_auth_key1 = list(res1["auth_response1"])
    # read_auth_key1 = list(res1["auth_response1"].to_bytes(16, 'big'))
    read_auth_key = list(reversed(binascii.unhexlify(hex(res["auth_response"])[2:].zfill(16))))
    if read_auth_key != holder_eng_authkey0_resp:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    read_key = int.from_bytes(read_auth_key[:2], "little")
    # logger.debug(f'read key:{read_key}')
    time.sleep(0.1)
    if read_key != 56001:
        logger.debug("check authentication key0 failed for board: engine")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(read_key)

    return True, str(read_key)


def check_authentication_engine_key1(connections, logger, **kwargs):
    connection = connections.get("uart")
    logger.debug("read authentication key from UUT Key1")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AD,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.5)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        count=8,
        pnum=239,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    res = builder.unpack_payload_fields(payload=response, offset=13, fields=[("auth_response", 16)])
    # logger.info(res)
    # read_auth_key1 = list(res1["auth_response1"])
    # read_auth_key1 = list(res1["auth_response1"].to_bytes(16, 'big'))
    read_auth_key = list(reversed(binascii.unhexlify(hex(res["auth_response"])[2:].zfill(16))))
    if read_auth_key != holder_eng_authkey1_resp:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"
    read_key = int.from_bytes(read_auth_key[:2], "little")
    # logger.debug(f'read key:{read_key}')
    time.sleep(0.1)
    if read_key != 30164:
        logger.debug("check authentication key1 failed for board: engine")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(read_key)

    return True, str(read_key)


def check_authentication_engine(connections, logger, **kwargs):
    connection = connections.get("uart")

    authentication_key1 = holder_eng_authkey0_resp
    authentication_key2 = holder_eng_authkey1_resp
    logger.debug("read authentication key from UUT")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00AD,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response.hex())
    time.sleep(0.1)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        count=8,
        pnum=231,
    )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    response1 = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response1.hex())  # below offset need to confirm with board test
    res1 = builder.unpack_payload_fields(payload=response1, offset=13, fields=[("auth_response1", 16)])
    # read_auth_key1 = list(res1["auth_response1"])
    read_auth_key1 = list(reversed(binascii.unhexlify(hex(res1["auth_response1"])[2:].zfill(16))))
    # read_auth_key1 = list(res1["auth_response1"].to_bytes(16, 'big')))
    # logger.debug(f'read key1:{key1_read}')
    read_key1 = int.from_bytes(read_auth_key1[:2], "little")
    # logger.debug(f'read key:{read_key1}')
    time.sleep(0.1)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x08,
        count=8,
        pnum=239,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response2 = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response2.hex())  # below offset need to confirm with board test
    # key2_read = response2.hex()[26:58]
    res2 = builder.unpack_payload_fields(payload=response2, offset=13, fields=[("auth_response2", 16)])
    # read_auth_key2 = list(res2["auth_response2"])
    read_auth_key2 = list(reversed(binascii.unhexlify(hex(res2["auth_response2"])[2:].zfill(16))))
    # read_auth_key2 = reversed(list(res2["auth_response2"].to_bytes(16, 'big')))
    # logger.debug(f'read key2:{key2_read}')
    read_key2 = int.from_bytes(read_auth_key2[:2], "little")
    # logger.debug(f'read key:{read_key2}')
    time.sleep(0.1)
    # if key1_read != authentication_key or key2_read != authentication_key:
    #     return False, key1_read
    if read_key1 != 56001 or read_key2 != 30164:
        logger.debug("check authentication key failed for board: engine")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    return True, "True"


def fuel_program(connections, logger, **kwargs):
    connection = connections.get("uart")
    for i in range(5):
        time.sleep(1)
        logger.info("loop:{} for programming".format(i))
        response = write_bba_command(connection, logger, value=0x0002, pnum=17)
        logger.info(response.hex())
        time.sleep(1)
        for i in range(30):
            uart_frame = builder.build_read_request_frame(
                mode="uart",
                read_only=True,
                reply_hop_count=0,
                hop_count=0,
                parameter=0x08,
                pnum=17,
                count=2,
            )
            response = connection.send_receive(uart_frame, timeout=1)
            logger.info(response.hex())
            if "a402" not in response.hex() and "0000002000000000000000000" in response.hex():
                uart_frame = builder.build_write_request_frame(
                    mode="uart",
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x02,
                    value=0x00,
                )
                response = connection.send_receive(uart_frame, timeout=1)
                logger.info(response.hex())
                logger.debug("reset device ok")
                break
            if "a402" not in response.hex() and "0000000000000000000000000" in response.hex():
                return True, "True"
            time.sleep(1.6)
        else:
            uart_frame = builder.build_write_request_frame(
                mode="uart",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x02,
                value=0x00,
            )
            response = connection.send_receive(uart_frame, timeout=1)
            logger.info(response.hex())
            logger.debug("reset device ok")
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"


def fuel_functional_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    response = write_bba_command(connection, logger, value=0x00A7, pnum=14)
    logger.info(response)
    time.sleep(0.1)
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        response = read_bba_command(connection, logger, pnum=14)
        logger.info(response.hex())
        time.sleep(2)
        # if response == [192, 4, 2, 14, 16, 0, 0, 6, 192, 132, 2, 14, 16, 0, 0, 234]:
        if "c084020e100000" in response.hex():
            break
    time.sleep(0.5)
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=250,
        count=3,
    )
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(response.hex())
    # if 97 not in response or 21 not in response or 3 not in response or 1 not in response:
    #     return False, "False"
    if "0611503010000" not in response.hex():
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    return True, "True"


def fuel_measurement_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    for i in range(3):
        response = write_bba_command(connection, logger, value=0x00A8, pnum=14)
        logger.info(response.hex())
        time.sleep(0.1)
        response = read_bba_command(connection, logger, pnum=14)
        logger.info(response.hex())
        time.sleep(1)
        response = read_bba_command(connection, logger, pnum=249)
        logger.info(response.hex())
    time.sleep(0.5)
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=247,
        count=2,
    )
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(response.hex())

    return True, "PASS"


def check_firmware_control(connections, logger, **kwargs):
    connection = connections.get("usb")
    config = gl.get_value("layout_config")
    logger.info(config)
    fw_ver = config.get("fw_ver")
    logger.info(fw_ver)
    firmware_version = get_firmware_revision(connection, logger, c=1)
    if not firmware_version:
        logger.warning("get control firmware version failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"
    if fw_ver[0] != firmware_version:
        logger.warning("control check firmware version failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, firmware_version

    return True, firmware_version


def check_firmware_engine(connections, logger, **kwargs):
    connection = connections.get("usb")
    config = gl.get_value("layout_config")
    logger.info(config)
    fw_ver = config.get("fw_ver")
    logger.info(fw_ver)
    firmware_version = get_firmware_revision(connection, logger, c=2)
    if not firmware_version:
        logger.warning("get engine firmware version failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"
    if fw_ver[1] != firmware_version:
        logger.warning("engine check firmware version failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, firmware_version

    return True, firmware_version


def get_firmware_revision(connection, logger, c):
    bd = "control" if c == 1 else "engine"
    for i in range(5):
        time.sleep(0.5)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=c,
            hop_count=c,
            parameter=0x00,
        )
        logger.info(f"get_firmware_revision:{bd} uart_frame: {uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        time.sleep(0.2)
        logger.info(response)
        if response:
            break
    else:
        logger.info(f'get firmware version failed with 5retry')
        return None
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("identification", 2),
            ("major", 1),
            ("minor", 1),
            ("path", 1),
        ],
    )
    logger.debug(res)
    major = res.get("major")
    minor = res.get("minor")
    path = res.get("path")
    # major = binascii.unhexlify(hex(res['major'])).decode('ascii')
    # minor = binascii.unhexlify(hex(res['minor'])).decode('ascii')
    # path = binascii.unhexlify(hex(res['path'])).decode('ascii')
    # major = ''.join(reversed(major))
    # minor = ''.join(reversed(minor))
    # path = ''.join(reversed(path))
    firmware_version = f"{major}.{minor}.{path}"
    logger.debug(f"board: {bd} firmware_version: {firmware_version}")

    return firmware_version


def check_mt_mode(connections, logger, **kwargs):
    connection = connections.get("uart")
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=36,
        count=1,
    )
    logger.info(f"check_mt_mode uart_frame: {uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"check_mt_mode response: {response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=13,
        fields=[
            ("mt_status", 2),
        ],
    )
    logger.debug(res)
    logger.debug(hex(res.get("mt_status")))
    read_value = to_hex_without_head(res.get("mt_status"), 2)
    logger.debug(read_value)
    if read_value != kwargs.get("limit").get("max"):
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_value

    return True, read_value


def check_mt_mode_mt11c_control(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(5):
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x08,
            pnum=36,
            count=1,
        )
        logger.info(f"check_mt_mode uart_frame: {uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response)
        if response:
            break
    if not response:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, response
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("mt_mode", 2)])
    logger.debug(res)
    read_value = to_hex(res["mt_mode"], 2)[2:]
    logger.debug(read_value)

    if read_value != kwargs.get("limit").get("max"):
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_value

    return True, read_value


def check_mt_mode_mt11c_engine(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(5):
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=2,
            hop_count=2,
            parameter=0x08,
            pnum=36,
            count=1,
        )
        logger.info(f"check_mt_mode uart_frame: {uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response)
        if response:
            break
    if not response:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, response
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("mt_mode", 2)])
    logger.debug(res)
    read_value = to_hex(res["mt_mode"], 2)[2:]
    logger.debug(read_value)

    if read_value != kwargs.get("limit").get("max"):
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_value

    return True, read_value


def check_unlock_status_level(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(5):
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x05,
            feature=0x00,
        )
        logger.info(uart_frame)
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        if response:
            break
    if not response:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, response
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("lock_status", 2),
        ],
    )
    logger.debug(hex(res.get("lock_status")))
    # read_value = to_hex_without_head(res.get("lock_status"), 1)
    read_value = to_hex(res["lock_status"], 2)[2:]
    logger.debug(read_value)
    if read_value != kwargs.get("limit").get("max"):
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_value

    return True, read_value


def charging_to_dut(connection, logger):
    uart_frame = builder.build_write_request_frame(
        mode='hid',
        reply_hop_count=1,
        hop_count=1,
        parameter=0x081,
        value0 = 0x01,
        value1 = 0x00,
        value2 = 0x03
    )
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)
    return


def battery_charge_status(connections, logger, **kwargs):
    connection = connections.get("usb")
    timeout = 1800
    battery_rsoc = False
    while timeout > 0 and not battery_rsoc:
        time.sleep(2)
        timeout -= 2
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x091,
        )
        for i in range(3):
            response = connection.send_receive(uart_frame, timeout=1)
            logger.debug(response)
            if 165 != response[3]:
                break
        else:
            logger.debug(f"query_rsoc_fail")
        res = builder.unpack_payload_fields(
            payload=response,
            offset=5,
            fields=[
                ("battery_rsoc", 1),
            ],
        )
        logger.debug((res.get("battery_rsoc")))  # Product line use 83 to 93

        if res.get("battery_rsoc") >= 0:  # GQL
            logger.info("Battery rsoc in range")
            battery_rsoc = True
            for i in range(3):
                if 229 != stop_charging_dut(connection=connection, logger=logger)[3]:
                    break
            else:
                logger.warning("STOP_CHARGING_FAIL")

    if battery_rsoc:
        return True, "Battery Charged"

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, "Battery in Charge"


def battery_charge_status1(connections, logger, **kwargs):
    connection = connections.get("usb")
    battery_charging_status = None
    status = {"00": "Battery Charged", "01": "Battery in Charge", "02": "Charging Required"}
    timeout = 1800
    while battery_charging_status != "00" and timeout > 0:
        time.sleep(2)
        timeout -= 2
        hid_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x081,
        )
        logger.debug(hid_frame)
        response = connection.send_receive(hid_frame, timeout=1)
        # logger.debug(response.hex())
        logger.debug(response)
        res = builder.unpack_payload_fields(
            payload=response,
            offset=5,
            fields=[
                ("battery_charging_status", 1),
            ],
        )
        logger.debug(to_hex_without_head(res.get("battery_charging_status"), 1))
        battery_charging_status = to_hex_without_head(res.get("battery_charging_status"), 1)
    for i in range(3):
        if 229 != stop_charging_dut(connection=connection, logger=logger)[3]:
            break
    else:
        logger.warning("STOP_CHARGING_FAIL")
        # return True, 'STOP_CHARGING_FAIL'

    battery_charging_status = status.get(battery_charging_status)
    if battery_charging_status == "Battery Charged":
        return True, battery_charging_status
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, battery_charging_status


def get_soc_value(connections, logger):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    uart_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x091,
    )
    logger.info(f"uart_frame: {uart_frame}")
    for i in range(6):
        time.sleep(0.5)
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        if response:
            if 165 != response[3]:
                break
    else:
        logger.debug(f"query_rsoc_fail")
        connection.close()
        while not stop_event.is_set():
            try:
                if connection.ensure_connected():
                    break
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                time.sleep(1)
                continue
        logger.debug(f"Query SOC again after reconnect")
        time.sleep(5)
        for i in range(5):
            time.sleep(0.5)
            response = connection.send_receive(uart_frame, timeout=1)
            logger.debug(response)
            if response:
                if 165 != response[3]:
                    break
        else:
            logger.debug(f"After reconnect, Query SOC still failed")
            return None
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("battery_rsoc", 1),
        ],
    )
    logger.debug((res.get("battery_rsoc")))

    return res.get("battery_rsoc")


def battery_heating_soc(connections, logger, **kwargs):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    soc = get_soc_value(connections, logger)
    if not soc:
        logger.info(f'get SOC failed')
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, 'Fail'
    if kwargs.get("limit").get("min") <= soc <= kwargs.get("limit").get("max"):
        logger.info(f"SOC: 28 <= {soc} <= 30, Dut not need to heating, return passed")
        if stop_charging_dut_soc(connection, logger):
            return True, str(soc)
        else:
            logger.info(f'stop charging failed')
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, 'Fail'

    if soc < kwargs.get("limit").get("min"):
        logger.info(f"SOC: {soc} < 28 , start charging")
        turn_holder_charging_soc(connection=connection, logger=logger)
        charging_to_dut(connection=connection, logger=logger)
        while not stop_event.is_set():
            time.sleep(0.5)
            soc = get_soc_value(connections, logger)
            if not soc:
                logger.info(f'get SOC failed')
                gl.set_value("error_code", kwargs.get("error_code"))
                return False, 'Fail'
            if soc > 30:
                logger.info(f'Charging SOC > 30, got to heating')
                break
            if soc == 30:
                if stop_charging_dut_soc(connection, logger):
                    return True, str(soc)
                else:
                    logger.warning("STOP_CHARGING_FAIL")
                    gl.set_value("error_code", kwargs.get("error_code"))
                    return False, "Fail"
            else:
                logger.info(f'Continue charging holder with SOC: {soc}')

    if soc > kwargs.get("limit").get("max"):
        if not turn_on_heating(connections, logger):
            logger.warning(f"first time turn on heating failed")
            turn_holder_charging_soc(connection=connection, logger=logger)
            logger.info(f"start reset charger for charging holder")
            hid_frame = builder.build_write_request_frame(
                mode="hid",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x02,
                count=1,
                value=0x00,
            )
            response = connection.send_receive(hid_frame, timeout=1)
            logger.debug(response)
            logger.info(f"charger reset ok")
            time.sleep(20)
            if not turn_on_heating(connections, logger):
                logger.warning(f"second time turn on heating still failed")
                gl.set_value("error_code", kwargs.get("error_code"))
                return False, "Fail"
        turn_holder_charging_soc(connection=connection, logger=logger)

    battery_rsoc = False
    while not stop_event.is_set():
        time.sleep(2)
        soc = get_soc_value(connections, logger)
        if not soc:
            logger.info(f'get SOC failed')
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, 'Fail'
        if soc <= 30 and check_heating_status(connections, logger):
            logger.info(f"SOC meet 30% and heating is finish")
            battery_rsoc = True
            break
        if soc <= 30 and not check_heating_status(connections, logger):
            logger.info(f"SOC meet 30%, but heating is not finish")
            if turn_off_heating(connections, logger):
                battery_rsoc = True
                break
            else:
                logger.warning("STOP_HEATING_FAIL")
                gl.set_value("error_code", kwargs.get("error_code"))
                return False, "Fail"
        if soc > 30 and check_heating_status(connections, logger):
            logger.info(f"heating finish but SOC not meet 30%, need reset charger")
            hid_frame = builder.build_write_request_frame(
                mode="hid",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x02,
                count=1,
                value=0x00,
            )
            response = connection.send_receive(hid_frame, timeout=1)
            logger.debug(response)
            logger.info(f"charger reset ok")
            time.sleep(14)
            timeout = 240
            detect_dut = False
            while timeout > 0 and not detect_dut:
                time.sleep(1)
                timeout -= 2
                try:
                    if connection.ensure_connected():
                        cmd_frame = builder.build_read_request_frame(
                            mode="hid", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
                        )
                        response = connection.send_receive(cmd_frame, timeout=1)
                        logger.info(f"response: {response}")
                        if response:
                            detect_dut = True
                            break
                        else:
                            if timeout == 200:
                                connection.close()
                            time.sleep(1)
                            continue
                    else:
                        time.sleep(1)
                        continue
                except Exception as e:
                    time.sleep(1)
                    continue
            if not detect_dut:
                logger.warning(f"after reset detected dut failed")
                break
            # charging_to_dut(connection=connection, logger=logger)
            # time.sleep(10)
            if not turn_on_heating(connections, logger):
                logger.warning(f"after heating turn on heating failed")
                break

    if battery_rsoc:
        if stop_charging_dut_soc(connection, logger):
            if kwargs.get("limit").get("min") <= soc <= kwargs.get("limit").get("max"):
                logger.info(f"SOC: 28 <= {soc} <= 30 in range after heating, return passed")
                return True, str(soc)
            else:
                gl.set_value("error_code", kwargs.get("error_code"))
                return False, str(soc)
        else:
            logger.warning("STOP_CHARGING_FAIL")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "Fail"
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(soc)


def battery_heating_status(connections, logger, **kwargs):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    soc = get_soc_value(connections, logger)
    if soc > 30:
        if not turn_on_heating(connections, logger):
            logger.warning(f"first time turn on heating failed")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "False"
    else:
        for i in range(3):
            if 229 != stop_charging_dut(connection=connection, logger=logger)[3]:
                break
        else:
            logger.warning("STOP_CHARGING_FAIL")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "False"
        logger.info(f"SOC: {soc} <= 30 not need to heating, return passed")
        return True, "True"

    battery_rsoc = False
    while not stop_event.is_set():
        time.sleep(2)
        soc = get_soc_value(connections, logger)
        if soc <= 30 and check_heating_status(connections, logger):
            logger.info(f"SOC meet 30% and heating is finish")
            battery_rsoc = True
            break
        if soc <= 30 and not check_heating_status(connections, logger):
            logger.info(f"SOC meet 30%, but heating is not finish")
            if turn_off_heating(connections, logger):
                battery_rsoc = True
                break
            else:
                logger.warning("STOP_HEATING_FAIL")
                gl.set_value("error_code", kwargs.get("error_code"))
                return False, "False"
        if soc > 30 and check_heating_status(connections, logger):
            logger.info(f"heating finish but SOC not meet 30%, need reset charger")
            hid_frame = builder.build_write_request_frame(
                mode="hid",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x02,
                count=1,
                value=0x00,
            )
            response = connection.send_receive(hid_frame, timeout=1)
            logger.debug(response)
            logger.info(f"charger reset ok")
            # time.sleep(3)
            # hid_frame = builder.build_write_request_frame(
            #     mode='hid',
            #     reply_hop_count=1,
            #     hop_count=1,
            #     parameter=0x02,
            # )
            # response = connection.send_receive(hid_frame, timeout=1)
            # logger.debug(response)
            # logger.info(f'holder reset ok')
            time.sleep(10)
            timeout = 240
            detect_dut = False
            while timeout > 0 and not detect_dut:
                time.sleep(1)
                timeout -= 2
                try:
                    if connection.ensure_connected():
                        cmd_frame = builder.build_read_request_frame(
                            mode="hid", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
                        )
                        response = connection.send_receive(cmd_frame, timeout=1)
                        logger.info(f"response: {response}")
                        if response:
                            detect_dut = True
                            break
                        else:
                            time.sleep(1)
                            continue
                    else:
                        time.sleep(1)
                        continue
                except Exception as e:
                    time.sleep(1)
                    continue
            if not detect_dut:
                logger.warning(f"after reset detected dut failed")
                break
            if not turn_on_heating(connections, logger):
                logger.warning(f"after heating turn on heating failed")
                break
    for i in range(3):
        if 229 != stop_charging_dut(connection=connection, logger=logger)[3]:
            break
    else:
        logger.warning("STOP_CHARGING_FAIL")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    if battery_rsoc:
        return True, "True"

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, "False"


def check_heating_status(connections, logger):
    connection = connections.get("usb")
    hid_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x081,
    )
    logger.debug(hid_frame)
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("heating_status", 1),
        ],
    )
    logger.debug(to_hex_without_head(res.get("heating_status"), 1))
    heating_status = to_hex_without_head(res.get("heating_status"), 1)
    heating_status_bin = bin(int(heating_status, 16))[2:].zfill(8)
    heating_status = heating_status_bin[2:4]
    logger.info(f"Heating status: {heating_status}")
    if heating_status == "00":  # need confirm
        return True
    else:
        return False


def stop_charging_dut_soc(connection, logger):
    stop_holder_charging_soc(connection, logger)
    for i in range(3):
        hid_frame = builder.build_write_request_frame(
            mode="hid", reply_hop_count=1, hop_count=1, parameter=0x081, value0=0x02, value1=0x00, value2=0x03
        )
        logger.debug(hid_frame)
        response = connection.send_receive(hid_frame, timeout=1)
        logger.debug(response)
        if 229 != response[3]:
            break
    else:
        return False

    return True


def turn_holder_charging_soc(connection, logger):
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x0101,
        value0_len=2,
    )
    logger.debug(hid_frame.hex())
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)

    return


def stop_holder_charging_soc(connection, logger):
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x0201,
        value0_len=2,
    )
    logger.debug(hid_frame.hex())
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)

    return


def stop_charging_dut(connection, logger):
    hid_frame = builder.build_write_request_frame(
        mode="hid", reply_hop_count=1, hop_count=1, parameter=0x081, value0=0x02, value1=0x00, value2=0x03
    )
    logger.debug(hid_frame)
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)

    return response


def stop_charger_charging(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x0200,
        value0_len=2,
    )
    logger.debug(hid_frame.hex())
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)

    return True, "Ture"


def turn_on_heating(connections, logger):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    uart_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x0081,
        value0=0x10,
        value1=0x00,
        value2=0x30,
        value3=0x00,
    )
    for i in range(10):
        time.sleep(1)
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        if response:
            if 229 != response[3]:
                break
            else:
                time.sleep(10)
    else:
        logger.info(f'turn on heating retry with reconnect')
        connection.close()
        while not stop_event.is_set():
            try:
                if connection.ensure_connected():
                    break
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                time.sleep(1)
                continue
        time.sleep(10)
        for i in range(5):
            time.sleep(1)
            response = connection.send_receive(uart_frame, timeout=1)
            logger.debug(response)
            if response:
                if 229 != response[3]:
                    break
                else:
                    time.sleep(10)
        else:
            logger.info(f'turn on heating failed after reconnect')
            return False

    return True


def query_battery_fg_rsoc(connections, logger, **kwargs):
    connection = connections.get("usb")
    # if not turn_on_heating(connection, logger):
    #     logger.debug(f'turn_on_heating failed')
    timeout = 4
    battery_rsoc = False
    while timeout > 0 and not battery_rsoc:
        time.sleep(2)
        timeout -= 2
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x091,
        )
        for i in range(3):
            response = connection.send_receive(uart_frame, timeout=1)
            logger.debug(response)
            if 165 != response[3]:
                break
        else:
            logger.debug(f"query_rsoc_fail")
        res = builder.unpack_payload_fields(
            payload=response,
            offset=5,  # GQL need confirm
            fields=[
                ("battery_rsoc", 1),
            ],
        )
        logger.debug((res.get("battery_rsoc")))  # Product line use 83 to 93

        if (
            kwargs.get("limit").get("min") <= res.get("battery_rsoc") <= kwargs.get("limit").get("max")
        ):  # min:65, max:75  Need check
            logger.info("check battery rsoc in range")
            battery_rsoc = True
    # if not turn_off_heating(connections, logger):
    #     logger.debug(f'turn_off_heating failed')
    if battery_rsoc:
        return True, str(res.get("battery_rsoc"))
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(res.get("battery_rsoc"))


def turn_off_heating(connections, logger):
    connection = connections.get("usb")
    uart_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x0081,
        value=0x00,
        value1=0x00,
        value2=0x30,
        value3=0x00,
    )
    for i in range(3):
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        if 229 != response[3]:
            break
    else:
        return False

    return True


def read_thermistor_temperature(connections, logger, **kwargs):
    connection = connections.get("uart")
    response = write_bba_command(connection, logger, value=0x00B4, pnum=14)
    logger.info(f"read temp (0x0B4) response is:{response.hex()}")
    response = read_bba_command(connection, logger, pnum=254)
    logger.info(f"read temp (pnum 254) response is:{response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=13,
        fields=[
            ("thermistor_temperature", 2),
        ],
    )
    logger.debug(f'thermistor_temperature:{res.get("thermistor_temperature")}')
    temp = int(res.get("thermistor_temperature"))
    if kwargs.get("limit").get("min") <= temp <= kwargs.get("limit").get("max"):  # range(15,40)
        logger.info("Check Thermistor Temperature Passed")
        return True, str(temp)

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(temp)


def read_battery_temperature(connections, logger, **kwargs):
    connection = connections.get("uart")
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x080,
    )
    logger.info(f"read temp (0x080) uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"read temp (0x080) response is:{response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=11,
        fields=[
            ("t1", 1),
            ("t2", 1),
            ("ADC1", 2),
            ("ADC2", 2),
        ],
    )
    logger.debug(f't1:{res.get("t1")}')
    logger.debug(f't2:{res.get("t2")}')
    logger.debug(f'ADC1:{res.get("ADC1")}')
    logger.debug(f'ADC2:{res.get("ADC2")}')
    T1 = res.get("t1")
    T2 = res.get("t2")
    ADC1 = res.get("ADC1")
    ADC2 = res.get("ADC2")
    # Following capture ADC data
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x083,
    )
    logger.info(f"read temp (0x083)uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"read temp (0x083) response is:{response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=9,
        fields=[
            ("battery_ADC", 2),
        ],
    )
    logger.debug(f'battery_ADC:{res.get("battery_ADC")}')
    battery_ADC = res.get("battery_ADC")
    temp = T1 + (T2 - T1) * ((battery_ADC - ADC1) / (ADC2 - ADC1))
    if kwargs.get("limit").get("min") <= temp <= kwargs.get("limit").get("max"):  # range(20,35)
        logger.info("Check Battery Temperature Passed")
        return True, str(round(temp))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(temp))


def time_sync(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(3):
        logger.info(f'RTC check in loop{i}')
        current_time = time.mktime(time.gmtime())
        time_struct = time.strptime("2010-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
        window_dut_time_offset = time.mktime(time_struct)
        logger.debug("offset of epoch time is:{}".format(window_dut_time_offset))
        set_dut_time = int(current_time - window_dut_time_offset)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x04,
        )
        logger.debug(f"build cmd: {uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
        logger.debug(res)
        uut_time = time.ctime(res["dut_time"] + window_dut_time_offset)
        logger.debug("Current DUT UTC Time: {}".format(uut_time))
        time_delta = current_time - (res["dut_time"] + window_dut_time_offset)
        if abs(time_delta) > 20:
            cmd_frame = builder.build_write_request_frame(
                mode="hid", reply_hop_count=1, hop_count=1, parameter=0x04, value=set_dut_time + 1
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response)
            time.sleep(0.5)
            cmd_frame = builder.build_read_request_frame(
                mode="hid",
                read_only=True,
                reply_hop_count=1,
                hop_count=1,
                parameter=0x04,
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response)
            res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
            logger.debug(res)
            uut_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res["dut_time"] + window_dut_time_offset))
            logger.debug("Reset New Current DUT UTC Time: {}".format(uut_time))
            time_delta = int(time.mktime(time.gmtime()) - (res["dut_time"] + window_dut_time_offset))
            if abs(time_delta) <= 20:
                break
        else:
            break
    if abs(time_delta) > 20:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(round(time_delta))

    return True, str(round(time_delta))


def time_sync_olde(connections, logger, **kwargs):
    connection = connections.get("usb")
    current_time = time.mktime(time.gmtime())
    time_struct = time.strptime("2010-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
    window_dut_time_offset = time.mktime(time_struct)
    logger.debug("offset of epoch time is:{}".format(window_dut_time_offset))
    uart_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=1,
        hop_count=1,
        parameter=0x04,
    )
    logger.debug(f"build cmd: {uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
    logger.debug(res)
    uut_time = time.ctime(res["dut_time"] + window_dut_time_offset)
    logger.debug("Current DUT UTC Time: {}".format(uut_time))
    time_delta = current_time - (res["dut_time"] + window_dut_time_offset)
    if abs(time_delta) > 20:
        time_set_value = int(time_delta + res["dut_time"])
        logger.debug("time_set_value: {}".format(time_set_value))
        # write the offset time
        cmd_frame = builder.build_write_request_frame(
            mode="hid",
            reply_hop_count=1,
            hop_count=1,
            parameter=0x04,
            value=time_set_value,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        time.sleep(0.5)
        # Read again
        cmd_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x04,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
        logger.debug(res)
        uut_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res["dut_time"] + window_dut_time_offset))
        logger.debug("Reset New Current DUT UTC Time: {}".format(uut_time))
        time_delta = int(time.mktime(time.gmtime()) - (res["dut_time"] + window_dut_time_offset))
    if abs(time_delta) > 20:  # range( +/-20 seconds)
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(int(time_delta - 20))

    return True, str(int(time_delta - 20))


def read_codentify_code(connections, logger, station):
    if "MT7VC" in station:
        connection = connections.get("uart")
        for i in range(5):
            uart_frame = builder.build_read_request_frame(
                mode="uart",
                read_only=True,
                reply_hop_count=0,
                hop_count=0,
                parameter=0x0C,
            )
            response = connection.send_receive(uart_frame, timeout=1)
            response1 = response.replace(uart_frame, b"")
            crc = verify_crc(logger=logger,data=response1, connection='uart')
            logger.info(f'CRC value is {crc}')
            logger.debug(response)
            if response and crc:
                break
            else:
                time.sleep(0.1)
                continue
        res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("read_codentify_code", 14)])
        logger.debug(res)
        codentify = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
        codentify = "".join(reversed(codentify))
    else:
        connection = connections.get("usb")
        for i in range(10):
            try:
                if connection.ensure_connected():
                    time.sleep(1)
                    uart_frame = builder.build_read_request_frame(
                        mode="hid",
                        read_only=True,
                        reply_hop_count=1,
                        hop_count=1,
                        parameter=0x0C,
                    )
                    response = connection.send_receive(uart_frame, timeout=1)
                    logger.debug(response)
                    crc = verify_crc(logger=logger, data=response, connection='hid')
                    logger.info(f'CRC value is {crc}')
                    if response and crc:
                        break
                    else:
                        connection.close()
                        time.sleep(1)
                        continue
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                time.sleep(1)
                continue
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("read_codentify_code", 14)])
        logger.debug(res)
        codentify = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
        codentify = "".join(reversed(codentify))
    read_codentify_code = codentify[:4] + " " + codentify[4:7:] + " " + codentify[7:10] + " " + codentify[10:]
    logger.debug("read codentify code is {}".format(read_codentify_code))
    gl.set_value("codentify_code", read_codentify_code)

    return


def check_codentify_code_mt7vc(connections, logger, **kwargs):
    connection = connections.get("uart")
    for i in range(5):
        uart_frame = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x0C,
        )
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        if response:
            break
        else:
            time.sleep(0.1)
            continue
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("read_codentify_code", 14)])
    logger.debug(res)
    read_codentify_code = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
    read_codentify_code = "".join(reversed(read_codentify_code))
    # match = re.findall(r'x03([A-Z0-9]+)', str(response).strip())
    # codentify_code = match[0]
    logger.debug(read_codentify_code)
    if len(read_codentify_code) != 14:
        logger.warning("get codentify failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_codentify_code

    return True, read_codentify_code


def check_codentify_code_mt11c(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(5):
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x0C,
        )
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        crc = verify_crc(logger=logger, data=response, connection='hid')
        logger.info(f'CRC value is {crc}')
        if response and crc:
            break
    if not response:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, response
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("read_codentify_code", 14)])
    logger.debug(res)
    read_codentify_code = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
    read_codentify_code = "".join(reversed(read_codentify_code))
    logger.debug("read codentify code is {}".format(read_codentify_code))
    if len(read_codentify_code) != 14:
        logger.debug("check codentify code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_codentify_code

    return True, read_codentify_code


def check_codentify_code_mt11c_engine(connections, logger, **kwargs):
    connection = connections.get("usb")
    for i in range(5):
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=2,
            hop_count=2,
            parameter=0x0C,
        )
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        crc = verify_crc(logger=logger, data=response, connection='hid')
        logger.info(f'CRC value is {crc}')
        if response and crc:
            break
    if not response:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, response
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("read_codentify_code", 14)])
    logger.debug(res)
    read_codentify_code = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
    read_codentify_code = "".join(reversed(read_codentify_code))
    logger.debug("read codentify code is {}".format(read_codentify_code))
    if len(read_codentify_code) != 14:
        logger.debug("check codentify code failed")
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, read_codentify_code

    return True, read_codentify_code


def voltage_conversion_factor(connection, logger, **kwargs):
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x80,
    )
    logger.info(f"voltage_conversion_factor uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"voltage_conversion_factor response is:{response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=9,
        fields=[
            ("voltage_conversion", 2),
        ],
    )
    logger.debug(hex(res.get("voltage_conversion")))
    conversion_factor = res.get("voltage_conversion")
    logger.debug(f"voltage conversion factor: {conversion_factor}")

    return conversion_factor


def get_battery_statuts(connection, logger, **kwargs):
    uart_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x83,
    )
    logger.info(f"get_battery_statuts uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"get_battery_statuts response is:{response.hex()}")
    res = builder.unpack_payload_fields(
        payload=response,
        offset=7,
        fields=[
            ("battery_level", 2),
        ],
    )
    logger.debug(hex(res.get("battery_level")))
    battery_statuts = res.get("battery_level")
    logger.debug(f"battery status: {battery_statuts}")

    return battery_statuts


def read_battery_code(connections, logger, **kwargs):
    connection = connections.get("uart")
    conversion_factor = voltage_conversion_factor(connection, logger)
    # time.sleep(0.3)
    battery_statuts = get_battery_statuts(connection, logger)
    value = ((conversion_factor + 1) * battery_statuts) * 1000 // 65536
    logger.info(value)
    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def read_bba_command(connection, logger, pnum):
    logger.info(f"pnum is:{pnum}")
    uart_frame = None
    uart_frame = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x08, pnum=pnum, count=1
    )
    logger.info(f"read uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"read response is:{response.hex()}")
    return response


def write_bba_command(connection, logger, value, pnum):
    logger.info(f"pnum is:{pnum}")
    uart_frame = None
    uart_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=pnum,
        count=1,
        value=value,
    )
    logger.info(f"write uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(f"write response is:{response.hex()}")
    return response


def haptics_off_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    # time.sleep(1.5)
    expected_value = ["c004020e10000006c084020e100000ea"]
    # Step1 write C0
    for i in range(3):
        uart_frame = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C0
        )
        logger.info(f"step1: write uart_frame is:{uart_frame.hex()}")
        connection.send(uart_frame)
        time.sleep(0.1)
        response = connection.recv(timeout=1)
        logger.info(f"Step1 write response: {response.hex()}")
        if "c044020e10c0009dc0c4020e10c00071" in response.hex():
            break
        else:
            logger.debug(f"step:1 check write response fail:{response.hex()} in loop{i}")
            time.sleep(0.1)
    else:
        uart_frame = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
        )
        logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response.hex())
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    # Step2
    # time.sleep(0.05)
    uart_frame = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1
    )
    logger.info(f"step2: read uart_frame is:{uart_frame.hex()}")
    for i in range(5):
        time.sleep(0.05)
        logger.info(f"step2 in loop:{i}")
        connection.send(uart_frame)
        time.sleep(0.1)
        response = connection.recv(timeout=1)
        logger.info(f"step2 receive: {response.hex()}")
        if expected_value[0] not in response.hex():
            logger.debug(f"step:2 check execution status fail:{response.hex()} in loop{i}")
        else:
            break
    else:
        uart_frame = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
        )
        logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response.hex())
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"

    # Step3 write C1
    for i in range(3):
        time.sleep(0.1)
        logger.info(f"step3: pnum:14, value:0x00C1")
        response = write_bba_command(connection, logger, value=0x00C1, pnum=14)
        logger.info(f"Step3 write response: {response.hex()}")
        if "c044020e10c10088c0c4020e10c10064" in response.hex():
            break
        else:
            logger.debug(f"step:3 check write response fail:{response.hex()} in loop{i}")
    else:
        uart_frame = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
        )
        logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response.hex())
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    # Step4
    # time.sleep(0.05)
    for i in range(5):
        time.sleep(0.05)
        logger.info(f"step4 in loop:{i}")
        response = read_bba_command(connection, logger, pnum=14)
        logger.info(response.hex())
        if response.hex() not in expected_value:
            logger.debug(f"step:4 check execution status fail:{response.hex()}")
        else:
            break
    else:
        uart_frame = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
        )
        logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(response.hex())
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"

    cmd_read_haptic_min = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=287,
        count=3,
    )
    print(f"cmd_read_haptic_min: {cmd_read_haptic_min.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_min.hex()}")
    response = connection.send_receive(cmd_read_haptic_min, timeout=1)
    logger.info(response.hex())
    x_min = int.from_bytes(response[13:15], "little")
    y_min = int.from_bytes(response[15:17], "little")
    z_min = int.from_bytes(response[17:19], "little")
    logger.info(f"X_min:{x_min}, Y_min:{y_min}, Z_min:{z_min}")
    rms_min = np.sqrt(np.mean(np.square([x_min, y_min, z_min])))
    logger.info(f"{rms_min}")
    cmd_read_haptic_max = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=293,
        count=3,
    )
    print(f"cmd_read_haptic_max: {cmd_read_haptic_max.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_max.hex()}")
    response = connection.send_receive(cmd_read_haptic_max, timeout=1)
    logger.info(response.hex())
    x_max = int.from_bytes(response[13:15], "little")
    y_max = int.from_bytes(response[15:17], "little")
    z_max = int.from_bytes(response[17:19], "little")
    logger.info(f"X_max:{x_max}, Y_max:{y_max}, Z_max:{z_max}")
    rms_max = np.sqrt(np.mean(np.square([x_max, y_max, z_max])))
    logger.info(f"{rms_max}")
    result = rms_max - rms_min
    if (rms_max - rms_min) <= 5735:
        result = (rms_max - rms_min) * 0.35 / 5.735
    if (rms_max - rms_min) > 5735:
        result = (rms_max - rms_min) / 16.393
    logger.info(f"{result}")
    # Close IMU
    uart_frame = builder.build_write_request_frame(
        mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
    )
    logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(response.hex())
    time.sleep(0.1)

    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, str(round(result))
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(result))


def haptics_off_test_0916(connections, logger, **kwargs):
    connection = connections.get("uart")
    com_list = [
        {"step": 1, "pnum": 14},
        {"step": 2, "pnum": 14},
        {"step": 3, "pnum": 14},
        {"step": 4, "pnum": 14},
    ]
    expected_value = ["c004020e10000006c084020e100000ea"]
    for value in com_list:
        step = value.get("step")
        pnum = value.get("pnum")
        logger.debug(f"step:{step},value:{pnum}")
        if step == 1:
            data = 0x00C0
        if step == 3:
            data = 0x00C1
        if step == 2 or step == 4:
            time.sleep(0.05)
        if step == 3:
            time.sleep(0.10)
        if step == 1 or step == 3:
            response = write_bba_command(connection, logger, value=data, pnum=pnum)
        else:
            response = read_bba_command(connection, logger, pnum=pnum)
        logger.debug(response)
        logger.info(response.hex())
        if (step == 2 or step == 4) and response.hex() not in expected_value:
            logger.debug(f"step:{step} check execution status fail:{response.hex()}")
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "None"
    # time.sleep(0.05)
    cmd_read_haptic_min = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=287,
        count=3,
    )
    print(f"cmd_read_haptic_min: {cmd_read_haptic_min.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_min.hex()}")
    response = connection.send_receive(cmd_read_haptic_min, timeout=1)
    logger.info(response.hex())
    x_min = int.from_bytes(response[13:15], "little")
    y_min = int.from_bytes(response[15:17], "little")
    z_min = int.from_bytes(response[17:19], "little")
    logger.info(f"X_min:{x_min}, Y_min:{y_min}, Z_min:{z_min}")
    rms_min = np.sqrt(np.mean(np.square([x_min, y_min, z_min])))
    logger.info(f"{rms_min}")
    cmd_read_haptic_max = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=293,
        count=3,
    )
    print(f"cmd_read_haptic_max: {cmd_read_haptic_max.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_max.hex()}")
    response = connection.send_receive(cmd_read_haptic_max, timeout=1)
    logger.info(response.hex())
    x_max = int.from_bytes(response[13:15], "little")
    y_max = int.from_bytes(response[15:17], "little")
    z_max = int.from_bytes(response[17:19], "little")
    logger.info(f"X_max:{x_max}, Y_max:{y_max}, Z_max:{z_max}")
    rms_max = np.sqrt(np.mean(np.square([x_max, y_max, z_max])))
    logger.info(f"{rms_max}")
    result = rms_max - rms_min
    if (rms_max - rms_min) <= 5735:
        result = (rms_max - rms_min) * 0.35 / 5.735
    if (rms_max - rms_min) > 5735:
        result = (rms_max - rms_min) / 16.393
    logger.info(f"{result}")
    # Close MU
    uart_frame = builder.build_write_request_frame(
        mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00C1
    )
    logger.info(f"last step: write uart_frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.info(response.hex())
    time.sleep(0.1)

    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, str(round(result))
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(result))


def haptics_off_test_poc(connections, logger, **kwargs):
    connection = connections.get("uart")
    com_list = [
        {"step": 1, "pnum": 14},
        {"step": 2, "pnum": 14},
        {"step": 3, "pnum": 14},
        {"step": 4, "pnum": 14},
    ]
    expected_value = ["c004020e10000006c084020e100000ea"]
    value_list = []
    test_result = None
    for i in range(11):
        logger.info(f"Start haptics_off test in loop: {i}")
        for value in com_list:
            step = value.get("step")
            pnum = value.get("pnum")
            logger.debug(f"step:{step},value:{pnum}")
            if step == 1:
                data = 0x00C0
            if step == 3:
                data = 0x00C1
            if step == 2 or step == 3 or step == 4:
                time.sleep(0.15)
            if step == 1 or step == 3:
                response = write_bba_command(connection, logger, value=data, pnum=pnum)
            else:
                response = read_bba_command(connection, logger, pnum=pnum)
            logger.debug(response)
            logger.info(response.hex())
            if (step == 2 or step == 4) and response.hex() not in expected_value:
                logger.debug(f"step:{step} check execution status fail:{response.hex()}")
                # gl.set_value('error_code', kwargs.get("error_code"))   # POC build skip this
                # return False, 'None'
        time.sleep(0.05)
        cmd_read_haptic_min = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=287,
            count=3,
        )
        print(f"cmd_read_haptic_min: {cmd_read_haptic_min.hex()}")
        logger.debug(f"build cmd: {cmd_read_haptic_min.hex()}")
        response = connection.send_receive(cmd_read_haptic_min, timeout=1)
        logger.info(response.hex())
        x_min = int.from_bytes(response[13:15], "little")
        y_min = int.from_bytes(response[15:17], "little")
        z_min = int.from_bytes(response[17:19], "little")
        logger.info(f"loop:{i}, X_min:{x_min}, Y_min:{y_min}, Z_min:{z_min}")
        rms_min = np.sqrt(np.mean(np.square([x_min, y_min, z_min])))
        logger.info(f"loop:{i}, rms_min:{rms_min}")
        cmd_read_haptic_max = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=293,
            count=3,
        )
        print(f"cmd_read_haptic_max: {cmd_read_haptic_max.hex()}")
        logger.debug(f"build cmd: {cmd_read_haptic_max.hex()}")
        response = connection.send_receive(cmd_read_haptic_max, timeout=1)
        logger.info(response.hex())
        x_max = int.from_bytes(response[13:15], "little")
        y_max = int.from_bytes(response[15:17], "little")
        z_max = int.from_bytes(response[17:19], "little")
        logger.info(f"loop:{i}, X_max:{x_max}, Y_max:{y_max}, Z_max:{z_max}")
        rms_max = np.sqrt(np.mean(np.square([x_max, y_max, z_max])))
        logger.info(f"loop:{i}, rms_max:{rms_max}")
        result = rms_max - rms_min
        if (rms_max - rms_min) <= 5735:
            result = (rms_max - rms_min) * 0.35 / 5.735
        if (rms_max - rms_min) > 5735:
            result = (rms_max - rms_min) / 16.393
        logger.info(f"loop:{i}, result:{result}")
        logger.info(f"End haptics_off test in loop: {i}")
        value_list.append(result)
        if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
            if i == 0:
                return True, str(round(result))
        else:
            if i == 0:
                test_result = str(round(result))

    logger.info(value_list)
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, test_result


def haptics_on_test1(connections, logger, **kwargs):
    connection = connections.get("uart")
    com_list = [
        {"step": 1, "pnum": 14},
        {"step": 2, "pnum": 14},
        {"step": 3, "pnum": 14},
        {"step": 4, "pnum": 14},
    ]
    expected_value = ["c004020e10000006c084020e100000ea"]
    for value in com_list:
        step = value.get("step")
        pnum = value.get("pnum")
        logger.debug(f"step:{step},value:{pnum}")
        if step == 1:
            data = 0x00A5
        if step == 3:
            data = 0x00A6
        if step == 3:
            time.sleep(1.5)
        if step == 2 or step == 4:
            time.sleep(0.05)
        if step == 1 or step == 3:
            response = write_bba_command(connection, value=data, pnum=pnum, logger=logger)
        else:
            response = read_bba_command(connection, pnum=pnum, logger=logger)
        logger.debug(response)
        logger.info(response.hex())
        if (step == 2 or step == 4) and response.hex() not in expected_value:
            logger.debug(f"step:{step} check execution status fail:{response.hex()}")
            return False, response.hex()

    # rms_max = get_maximum_rms_value(connection=connection, logger=logger)
    # rms_min = get_minimum_rms_value(connection=connection, logger=logger)

    time.sleep(0.05)
    cmd_read_haptic_min = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=287,
        count=3,
    )
    print(f"cmd_read_haptic_min: {cmd_read_haptic_min.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_min.hex()}")
    response = connection.send_receive(cmd_read_haptic_min, timeout=1)
    x_min = int.from_bytes(response[13:15], "little")
    y_min = int.from_bytes(response[15:17], "little")
    z_min = int.from_bytes(response[17:19], "little")
    rms_min = np.sqrt(np.mean(np.square([x_min, y_min, z_min])))
    cmd_read_haptic_max = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=293,
        count=3,
    )
    print(f"cmd_read_haptic_max: {cmd_read_haptic_max.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_max.hex()}")
    response = connection.send_receive(cmd_read_haptic_max, timeout=1)
    x_max = int.from_bytes(response[13:15], "little")
    y_max = int.from_bytes(response[15:17], "little")
    z_max = int.from_bytes(response[17:19], "little")
    rms_max = np.sqrt(np.mean(np.square([x_max, y_max, z_max])))

    result = rms_max - rms_min
    if (rms_max - rms_min) <= 5735:
        result = (rms_max - rms_min) * 0.35 / 5.735
    if (rms_max - rms_min) > 5735:
        result = (rms_max - rms_min) / 16.393

    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, round(result)
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, round(result)


def get_maximum_rms_value(connection, logger):
    com_list = [{"step": 1, "pnum": 293}, {"step": 2, "pnum": 294}, {"step": 3, "pnum": 295}]
    maximum_value = get_accelerometer_rms_value(connection, logger, com_list)

    return maximum_value


def get_minimum_rms_value(connection, logger):
    com_list = [{"step": 1, "pnum": 287}, {"step": 2, "pnum": 288}, {"step": 3, "pnum": 289}]
    minimum_value = get_accelerometer_rms_value(connection, logger, com_list)

    return minimum_value


def get_accelerometer_rms_value(connection, logger, com_list):
    value_list = []
    for value in com_list:
        step = value.get("step")
        pnum = value.get("pnum")
        logger.debug(f"step:{step},value:{pnum}")
        response = read_bba_command(connection, pnum=pnum, logger=logger)
        logger.debug(response)
        logger.info(response.hex())
        res = builder.unpack_payload_fields(
            payload=response,
            offset=13,
            fields=[
                ("accelerometer_value", 2),
            ],
        )
        logger.debug(hex(res.get("accelerometer_value")))
        logger.debug(res.get("accelerometer_value"))
        accelerometer_value = res.get("accelerometer_value")
        value_list.append(accelerometer_value)
    logger.info(f"accelerometer_value list is: {value_list}")
    rms = get_rms_value(value_list)
    logger.info(f"accelerometer_value RMS value is: {rms}")

    return rms


def haptics_on_test(connections, logger, **kwargs):
    print("Haptic on test")
    expected_value = ["c004020e10000006c084020e100000ea"]
    connection = connections.get("uart")
    for i in range(3):
        cmd_trigger_haptic_on = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00A5
        )
        print(f"cmd_trigger_haptic_on: {cmd_trigger_haptic_on.hex()}")
        logger.debug(f"build cmd: {cmd_trigger_haptic_on.hex()}")
        response = connection.send_receive(cmd_trigger_haptic_on, timeout=1)
        logger.info(f'Step1 write response: {response.hex()}')
        if "c044020e10a50029c0c4020e10a500c5" in response.hex():
            break
        else:
            logger.debug(f"step:1 check write response fail:{response.hex()} in loop{i}")
            time.sleep(0.1)
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    # time.sleep(0.05)
    # cmd_check_haptic = builder.build_read_request_frame(
    #     mode="uart",
    #     read_only=True,
    #     reply_hop_count=0,
    #     hop_count=0,
    #     parameter=0x08,
    #     pnum=14,
    #     count=1,

    # )
    # print(f"cmd_check_haptic: {cmd_check_haptic.hex()}")
    # logger.debug(f"build cmd: {cmd_check_haptic.hex()}")
    # response = connection.send_receive(cmd_check_haptic, timeout=1)

    uart_frame = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1
    )
    logger.info(f"step2: read uart_frame is:{uart_frame.hex()}")
    for i in range(5):
        time.sleep(0.05)
        logger.info(f"step2 in loop:{i}")
        connection.send(uart_frame)
        time.sleep(0.1)
        response = connection.recv(timeout=1)
        logger.info(f"step2 receive: {response.hex()}")
        if expected_value[0] not in response.hex():
            logger.debug(f"step:2 check execution status fail:{response.hex()} in loop{i}")
        else:
            break
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"

    time.sleep(1.5)
    for i in range(3):
        cmd_trigger_haptic_off = builder.build_write_request_frame(
            mode="uart", reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1, value1=0x00A6
        )
        print(f"cmd_trigger_haptic_off: {cmd_trigger_haptic_off.hex()}")
        logger.debug(f"build cmd: {cmd_trigger_haptic_off.hex()}")
        response = connection.send_receive(cmd_trigger_haptic_off, timeout=1)
        logger.info(f'Step3 write response: {response.hex()}')
        if "c044020e10a60016c0c4020e10a600fa" in response.hex():
            break
        else:
            logger.debug(f"step:3 check write response fail:{response.hex()} in loop{i}")
            time.sleep(0.1)
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "False"

    # time.sleep(0.05)
    uart_frame = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x08, pnum=14, count=1
    )
    logger.info(f"step4: read uart_frame is:{uart_frame.hex()}")
    for i in range(20):
        time.sleep(0.05)
        logger.info(f"step4 in loop:{i}")
        connection.send(uart_frame)
        time.sleep(0.1)
        response = connection.recv(timeout=1)
        logger.info(f"step4 receive: {response.hex()}")
        if expected_value[0] not in response.hex():
            logger.debug(f"step:4 check execution status fail:{response.hex()} in loop{i}")
        else:
            break
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, "None"

    time.sleep(0.05)
    cmd_read_haptic_min = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=287,
        count=3,
    )
    print(f"cmd_read_haptic_min: {cmd_read_haptic_min.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_min.hex()}")
    response = connection.send_receive(cmd_read_haptic_min, timeout=1)
    x_min = int.from_bytes(response[13:15], "little")
    y_min = int.from_bytes(response[15:17], "little")
    z_min = int.from_bytes(response[17:19], "little")
    logger.info(f"X_min:{x_min}, Y_min:{y_min}, Z_min:{z_min}")
    logger.debug(f"numpy path：{np.__path__}")
    rms_min = np.sqrt(np.mean(np.square([x_min, y_min, z_min])))
    cmd_read_haptic_max = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=293,
        count=3,
    )
    print(f"cmd_read_haptic_max: {cmd_read_haptic_max.hex()}")
    logger.debug(f"build cmd: {cmd_read_haptic_max.hex()}")
    response = connection.send_receive(cmd_read_haptic_max, timeout=1)
    x_max = int.from_bytes(response[13:15], "little")
    y_max = int.from_bytes(response[15:17], "little")
    z_max = int.from_bytes(response[17:19], "little")
    logger.info(f"X_max:{x_max}, Y_max:{y_max}, Z_max:{z_max}")
    rms_max = np.sqrt(np.mean(np.square([x_max, y_max, z_max])))

    delta = rms_max - rms_min
    haptic = -1
    if delta <= 5735:
        haptic = int(delta * 0.35 / 5.735)
    else:
        haptic = int(delta / 16.393)
    logger.info(f"{haptic}")
    if POC_BUILD:
        button = ask_question("请确实是否有震动，有回复Y，没有回复N=>")
        if button == "Y" or button == "y":
            return True, "True"
        else:
            gl.set_value("error_code", kwargs.get("error_code"))
            return False, "False"
    else:
        if int(kwargs.get("limit").get("min")) <= haptic <= int(kwargs.get("limit").get("max")):
            return True, str(round(haptic))

        gl.set_value("error_code", kwargs.get("error_code"))
        return False, str(round(haptic))  # here need update


def get_rms_value(data):
    # 示例数据
    # data = [1, 2, 3, 4, 5]
    # 计算均方根
    rms = np.sqrt(np.mean(np.square(data)))
    print("RMS:", rms)

    return rms


def accelerometer_capture_value(connection, logger):
    cmd_acc = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=293,
        count=3,
    )
    print(f"cmd_acc: {cmd_acc.hex()}")
    logger.debug(f"build cmd: {cmd_acc.hex()}")
    response = connection.send_receive(cmd_acc, timeout=1)
    logger.info(response.hex())
    acc_x = int.from_bytes(response[13:15], "little")
    acc_y = int.from_bytes(response[15:17], "little")
    acc_z = int.from_bytes(response[17:19], "little")
    logger.info(f"ACC_X:{acc_x}, ACC_Y:{acc_y}, ACC_Z:{acc_z}")
    gl.set_value("acc_x", acc_x)
    gl.set_value("acc_y", acc_y)
    gl.set_value("acc_z", acc_z)
    return


def accelerometer_x_test(connections, logger, **kwargs):
    # connection = connections.get("uart")
    # response = read_bba_command(connection, pnum=293, logger=logger)
    # logger.debug(response)
    # logger.info(response.hex())
    # res = builder.unpack_payload_fields(payload=response,
    #                                     offset=13,
    #                                     fields=[
    #                                         ('maximum_value', 2),
    #                                     ])
    # logger.debug(hex(res.get("maximum_value")))
    # maximum_value = res.get("maximum_value")
    connection = connections.get("uart")
    accelerometer_capture_value(connection, logger)
    maximum_value = gl.get_value("acc_x")
    logger.debug(maximum_value)
    if maximum_value <= 5735:
        value = maximum_value * 0.35 // 5.735
    elif maximum_value > 5735:
        value = maximum_value // 16.393
    else:
        value = maximum_value
    logger.debug(f"ACC X Max value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def accelerometer_y_test(connections, logger, **kwargs):
    # connection = connections.get("uart")
    # response = read_bba_command(connection, pnum=294, logger=logger)
    # logger.debug(response)
    # logger.info(response.hex())
    # res = builder.unpack_payload_fields(payload=response,
    #                                     offset=13,
    #                                     fields=[
    #                                         ('maximum_value', 2),
    #                                     ])
    # logger.debug(hex(res.get("maximum_value")))
    # maximum_value = res.get("maximum_value")
    maximum_value = gl.get_value("acc_y")
    logger.debug(maximum_value)

    if maximum_value <= 5735:
        value = maximum_value * 0.35 // 5.735
    elif maximum_value > 5735:
        value = maximum_value // 16.393
    else:
        value = maximum_value
    logger.debug(f"ACC Y Max value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def accelerometer_z_test(connections, logger, **kwargs):
    # connection = connections.get("uart")
    # response = read_bba_command(connection, pnum=295, logger=logger)
    # logger.debug(response)
    # logger.info(response.hex())
    # res = builder.unpack_payload_fields(payload=response,
    #                                     offset=13,
    #                                     fields=[
    #                                         ('maximum_value', 2),
    #                                     ])
    # logger.debug(hex(res.get("maximum_value")))
    # maximum_value = res.get("maximum_value")
    maximum_value = gl.get_value("acc_z")
    logger.debug(maximum_value)

    if maximum_value <= 5735:
        value = maximum_value * 0.35 // 5.735
    elif maximum_value > 5735:
        value = maximum_value // 16.393
    else:
        value = maximum_value
    logger.debug(f"ACC Z Max value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def angular_x_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    response = read_bba_command(connection, pnum=296, logger=logger)
    logger.debug(response)
    logger.info(response.hex())
    res = builder.unpack_payload_fields(
        payload=response,
        offset=13,
        fields=[
            ("maximum_value", 2),
        ],
    )
    logger.debug(hex(res.get("maximum_value")))
    maximum_value = res.get("maximum_value")
    logger.debug(maximum_value)

    if maximum_value <= 5714:
        value = maximum_value * 0.4 / 5.714
    elif maximum_value > 5714:
        value = maximum_value * 0.8 / 11.428
    else:
        value = maximum_value
    logger.debug(f"Angular X value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def angular_y_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    response = read_bba_command(connection, pnum=297, logger=logger)
    logger.debug(response)
    logger.info(response.hex())
    res = builder.unpack_payload_fields(
        payload=response,
        offset=13,
        fields=[
            ("maximum_value", 2),
        ],
    )
    logger.debug(hex(res.get("maximum_value")))
    maximum_value = res.get("maximum_value")

    if maximum_value <= 5714:
        value = maximum_value * 0.4 / 5.714
    elif maximum_value > 5714:
        value = maximum_value * 0.8 / 11.428
    else:
        value = maximum_value
    logger.debug(f"Angular Y value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def angular_z_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    response = read_bba_command(connection, pnum=298, logger=logger)
    logger.debug(response)
    logger.info(response.hex())
    res = builder.unpack_payload_fields(
        payload=response,
        offset=13,
        fields=[
            ("maximum_value", 2),
        ],
    )
    logger.debug(hex(res.get("maximum_value")))
    maximum_value = res.get("maximum_value")

    if maximum_value <= 5714:
        value = maximum_value * 0.4 / 5.714
    elif maximum_value > 5714:
        value = maximum_value * 0.8 / 11.428
    else:
        value = maximum_value
    logger.debug(f"Angular Z value is :{value}")

    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def trigger_capacitive_touch_test(connection, logger):
    expected_value = ["c004020e10000006c084020e100000ea"]
    response = write_bba_command(connection, value=0x00C4, pnum=14, logger=logger)
    logger.info(f'response:{response}')
    time.sleep(0.1)
    for i in range(5):
        response = read_bba_command(connection, pnum=14, logger=logger)
        logger.debug(response)
        logger.info(response.hex())
        if response.hex() not in expected_value:
            logger.debug(f"loop {i} check execution status fail:{response.hex()}")
        else:
            break
    else:
        return False

    return True


def get_touch_value(connection, logger, data_pnum):
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            response = read_bba_command(connection, pnum=data_pnum, logger=logger)
            logger.debug(response)
            logger.info(response.hex())
            res = builder.unpack_payload_fields(
                payload=response,
                offset=13,
                fields=[
                    ("touch_value", 2),
                ],
            )
            logger.debug(hex(res.get("touch_value")))
            logger.debug(res.get("touch_value"))
            touch_value = res.get("touch_value")
            break
        except Exception as e:
            logger.debug(e)
            continue

    return touch_value


def untouch_button0_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    if not trigger_capacitive_touch_test(connection=connection, logger=logger):
        logger.info(f'trigger touch test failed')
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, 'Fail'
    data_pnum = 262
    value = get_touch_value(connection, logger=logger, data_pnum=data_pnum)
    gl.set_value("button0_ut", value)
    logger.debug(value)
    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def untouch_button1_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    data_pnum = 261
    value = get_touch_value(connection, logger=logger, data_pnum=data_pnum)
    gl.set_value("button1_ut", value)
    logger.debug(value)
    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def untouch_button2_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    data_pnum = 260
    value = get_touch_value(connection, logger=logger, data_pnum=data_pnum)
    gl.set_value("button2_ut", value)
    logger.debug(value)
    if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
        return True, str(round(value))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(value))


def touch_button0_test(connections, logger, **kwargs):
    connection_ut = connections.get("uart")
    port_x = gl.get_value("layout_config").get("port_x")
    port_z = gl.get_value("layout_config").get("port_z")
    motor = MotorController(port_x, port_z)

    if POC_BUILD:
        button = ask_question("请按Button后回复Y=>")  # GQL
    else:
        motor.open()
        motor.move_z0_sequence(down=True)
        time.sleep(2)

    # trigger_capacitive_touch_test(connection=connection_ut, logger=logger)
    if not trigger_capacitive_touch_test(connection=connection_ut, logger=logger):
        logger.info(f'trigger touch test failed')
        motor.move_z0_sequence(down=False)
        gl.set_value("error_code", kwargs.get("error_code"))
        time.sleep(2)
        return False, 'Fail'
    data_pnum = 262
    button0_t = get_touch_value(connection_ut, logger=logger, data_pnum=data_pnum)

    if not POC_BUILD:
        motor.move_z0_sequence(down=False)
        time.sleep(2)
        # motor.close()

    button0_ut = gl.get_value("button0_ut")
    logger.info(f"buuton0 touch value: {button0_t} untouch value: {button0_ut}")
    result = button0_ut - button0_t
    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, str(round(result))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(result))


def touch_button1_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    port_x = gl.get_value("layout_config").get("port_x")
    port_z = gl.get_value("layout_config").get("port_z")
    motor = MotorController(port_x, port_z)
    if not POC_BUILD:
        motor.open()
        motor.move_x1_sequence(down=True)
        motor.move_z1_sequence(down=True)
        time.sleep(2)

    # trigger_capacitive_touch_test(connection=connection, logger=logger)
    if not trigger_capacitive_touch_test(connection=connection, logger=logger):
        logger.info(f'trigger touch test failed')
        motor.move_z1_sequence(down=False)
        motor.move_x1_sequence(down=False)
        motor.close()
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, 'Fail'
    data_pnum = 261
    button1_t = get_touch_value(connection, logger=logger, data_pnum=data_pnum)

    if not POC_BUILD:
        motor.move_z1_sequence(down=False)
        time.sleep(2)
        # motor.close()

    button1_ut = gl.get_value("button1_ut")
    logger.info(f"buuton1 touch value: {button1_t} untouch value: {button1_ut}")
    result = button1_ut - button1_t
    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, str(round(result))

    if not POC_BUILD:
        motor.move_x1_sequence(down=False)
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(result))


def touch_button2_test(connections, logger, **kwargs):
    connection = connections.get("uart")
    port_x = gl.get_value("layout_config").get("port_x")
    port_z = gl.get_value("layout_config").get("port_z")
    motor = MotorController(port_x, port_z)
    if not POC_BUILD:
        motor.open()
        motor.move_x2_sequence(down=True)
        motor.move_z2_sequence(down=True)
        time.sleep(2)

    # trigger_capacitive_touch_test(connection=connection, logger=logger)
    if not trigger_capacitive_touch_test(connection=connection, logger=logger):
        logger.info(f'trigger touch test failed')
        gl.set_value("error_code", kwargs.get("error_code"))
        motor.move_z2_sequence(down=False)
        motor.move_x2_sequence(down=False)
        time.sleep(2)
        motor.close()
        return False, 'Fail'
    data_pnum = 260
    button2_t = get_touch_value(connection, logger=logger, data_pnum=data_pnum)

    if not POC_BUILD:
        motor.move_z2_sequence(down=False)
        motor.move_x2_sequence(down=False)
        time.sleep(2)
        motor.close()

    button2_ut = gl.get_value("button2_ut")
    # button = ask_question("请松开Button后回复Y=>")   # GQL
    logger.info(f"buuton2 touch value: {button2_t} untouch value: {button2_ut}")
    result = button2_ut - button2_t
    if kwargs.get("limit").get("min") <= result <= kwargs.get("limit").get("max"):
        return True, str(round(result))

    gl.set_value("error_code", kwargs.get("error_code"))
    return False, str(round(result))


def init_motor(connections, logger, **kwargs):
    global ONCE
    response = None
    ni_device = NIEquipment(device_name="Dev1")
    response = ni_device.read_digital("port0/line2", timeout=1)  # Detect UUT Put in Tester
    logger.info(response)
    # time.sleep(0.5)
    if not ONCE and not response:
        port_x = gl.get_value("layout_config").get("port_x")
        port_z = gl.get_value("layout_config").get("port_z")
        logger.info(f"{port_x}, {port_z}")
        motor = MotorController(port_x, port_z)
        motor.open()
        motor.set_xspeed()
        time.sleep(2)
        motor.set_zspeed()
        time.sleep(2)
        motor.move_x_sequence()
        time.sleep(10)
        motor.move_z_sequence()
        time.sleep(10)
        motor.move_z_button_origin()
        time.sleep(8)
        motor.move_x_button_origin()
        time.sleep(8)
        motor.close()
        logger.info(f"Init motor finish")
        ONCE = True
    else:
        logger.info(f"Not first start or UUT Put in Tester, Not need init motor")

    return


def load_yaml_config():
    relative_path = r"src/config/settings.yaml"
    path = resource_path(relative_path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def gsc_controller_sequence(connections, logger, **kwargs):
    setting_value = load_yaml_config()
    # the following command for X to origin
    connection = connections.get("serial")
    response = connection.send("C:11\r\n", timeout=1)
    response = connection.send("H:1\r\n", timeout=1)
    time.sleep(15)
    # the following command for Z to origin
    connection = connections.get("serial1")
    response = connection.send("C:11\r\n", timeout=1)
    response = connection.send("H:1\r\n", timeout=1)

    # Following for X controller
    connection = connections.get("serial")
    BUTTON1_X = setting_value["BUTTON1_X_PULSE"]
    button_cmd = "M:1+P{}\r\n".format(BUTTON1_X)
    response = connection.send(button_cmd)
    response = connection.send("G:\r\n")
    time.sleep(20)

    BUTTON2_X = setting_value["BUTTON2_X_PULSE"]
    button_cmd = "M:1+P{}\r\n".format(BUTTON2_X)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)
    time.sleep(20)

    BUTTON0_ORI = BUTTON1_X + BUTTON2_X
    button_cmd = "M:1-P{}\r\n".format(BUTTON0_ORI)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)
    time.sleep(20)

    # Following for Z controller
    connection = connections.get("serial1")
    BUTTON0_Z = setting_value["BUTTON0_Z_PULSE"]
    button_cmd = "M:1-P{}\r\n".format(BUTTON0_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    button_cmd = "M:1+P{}\r\n".format(BUTTON0_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    connection = connections.get("serial1")
    BUTTON1_Z = setting_value["BUTTON1_Z_PULSE"]
    button_cmd = "M:1-P{}\r\n".format(BUTTON1_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    button_cmd = "M:1+P{}\r\n".format(BUTTON1_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    connection = connections.get("serial1")
    BUTTON2_Z = setting_value["BUTTON2_Z_PULSE"]
    button_cmd = "M:1-P{}\r\n".format(BUTTON2_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    button_cmd = "M:1+P{}\r\n".format(BUTTON2_Z)
    response = connection.send_receive(button_cmd, timeout=1)
    response = connection.send_receive("G:\r\n", timeout=1)

    return response


def exit_mt_mode(connections, logger, **kwargs):
    connection = connections.get("uart")
    # uart_frame = [0xc9, 0x44, 0x02, 0xd5, 0x10, 0x2e, 0x1c, 0x1b, 0x08, 0xc4, 0x02, 0xd5,
    #               0x10, 0x2e, 0x1c, 0xf7]
    uart_frame = [0xC9, 0x44, 0x02, 0xD5, 0x10, 0xB8, 0x19, 0x9F]
    time.sleep(1)
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)
    for i in [1, 0]:
        uart_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=i,
            hop_count=i,
            parameter=0x08,
            pnum=36,
            count=1,
            value=0x600D,
        )
        response = connection.send_receive(uart_frame, timeout=1)
        logger.debug(response)
        time.sleep(0.5)
        res = builder.unpack_payload_fields(
            payload=response,
            offset=13,
            fields=[
                ("mt_status", 2),
            ],
        )
        logger.debug(res)
        logger.debug(hex(res.get("mt_status")))
        value = res.get("mt_status")
        time.sleep(0.5)

    # if kwargs.get("limit").get("min") <= value <= kwargs.get("limit").get("max"):
    return True, value
    # gl.set_value('error_code', kwargs.get("error_code"))
    # return False, value


def reset(connections, logger, **kwargs):
    connection = connections.get("uart")
    time.sleep(1)
    uart_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x02,
        value=0x00,
    )
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)

    return True, "RESET_OK"


def set_yap_status(connection, logger, **kwargs):
    # connection = connections.get("usb")
    uart_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x05,
        value=0x01,
        value1=0x03,
    )
    logger.debug(f"build cmd: {uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)
    for i in range(5):
        time.sleep(1)
        cmd_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x05,
            value0=0x03,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("yap_mode_status", 2)])
        logger.debug(res)
        yap_value = res["yap_mode_status"]
        yap_status = "".join(f"{a:02x}" for a in list(yap_value.to_bytes(2, "little")))
        logger.info(f"yap status: {yap_status}")
        if yap_status == '0103':
            return True
    else:
        logger.debug(f'get wrong yap status')
        # gl.set_value("error_code", kwargs.get("error_code"))
        return False


def set_ship_mode(connections, logger, **kwargs):
    connection = connections.get("usb")
    # if not set_yap_status(connection=connection, logger=logger):
    #     logger.debug(f'set yap status failed')
    #     return False, 'Fail'
    uart_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=1,
        hop_count=1,
        parameter=0x05,
        value=0x01,
        value1=0x02,
    )
    logger.debug(f"build cmd: {uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    logger.debug(response)
    for i in range(5):
        time.sleep(1)
        cmd_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x05,
            value0=0x02,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ship_mode_status", 2)])
        logger.debug(res)
        ship_mode_value = res["ship_mode_status"]
        ship_status = "".join(f"{a:02x}" for a in list(ship_mode_value.to_bytes(2, "little")))
        logger.info(f"ship status: {ship_status}")
        if POC_BUILD:
            if ship_status == kwargs.get("limit").get("max"):
                return True, ship_status
        else:
            if ship_status == kwargs.get("limit").get("max") and check_ship_mode_evt(connections, logger):
                return True, ship_status
    else:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, ship_status


def check_ship_mode_evt(connections, logger):
    connection = connections.get("usb")
    for i in range(20):
        time.sleep(2)
        try:
            cmd_frame = builder.build_read_request_frame(
                mode="hid", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response)
            if response:
                continue
            else:
                return True
        except Exception as e:
            logger.debug(e)
            return True
    else:
        return False


def check_ship_mode(connections, logger, **kwargs):
    connection = connections.get("uart")
    question = ask_question("请将UUT从charger里拔出来后放入到串口吸铁头后输入Y")
    logger.info(f"connection is :{connection}.")
    mode = "uart" if "UART" in str(connection) else "hid"
    time.sleep(5)
    for i in range(4):
        time.sleep(3)
        try:
            cmd_frame = builder.build_read_request_frame(
                mode=mode, read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response.hex())
            if "c0010015" == response.hex() or "" == response.hex():
                return True, "True"
        except Exception as e:
            logger.debug(e)
            time.sleep(0.1)
            return True, "True"
    else:
        logger.debug(f"retry 2 times still can detect dut")
        question = ask_question("请将UUT从里串口吸铁头拔出后再放入到charger中后输入Y")
        time.sleep(5)
        question = ask_question("请再一次将UUT从charger里拔出来后放入到串口吸铁头后输入Y")
        for i in range(4):
            try:
                time.sleep(3)
                cmd_frame = builder.build_read_request_frame(
                    mode=mode, read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
                )
                logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.debug(response.hex())
                if "c0010015" == response.hex() or "" == response.hex():
                    return True, "True"
            except Exception as e:
                logger.debug(e)
                time.sleep(0.1)
                return True, "True"
    gl.set_value("error_code", kwargs.get("error_code"))
    return False, "False"


def read_ble_mac(connections, logger, **kwargs):
    """SDD data:0x40 0x30 actual pnum:64, count=3
    should put data=0x3040, for revert to 40 30
    """
    connection = connections.get("usb")
    hid_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=64,
        count=3,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    res = builder.unpack_payload_fields(
        payload=response,
        offset=7,
        fields=[
            ("mac1", 2),
            ("mac2", 2),
            ("mac3", 2),
        ],
    )
    mac = f"{res['mac1']:04X}{res['mac2']:04X}{res['mac3']:04X}"
    return True, mac


def overall_test_result_mt7vc(connections, logger, **kwargs):
    logger.info("overall_test_result")
    error_code = gl.get_value("error_code")
    if error_code:
        return False, error_code
    else:
        return True, kwargs.get("limit").get("equal")


def overall_test_result(connections, logger, **kwargs):
    result, value = common_steps.overall_test_result(connections, logger, **kwargs)
    # config = gl.get_value("layout_config")
    # logger.info(config)
    # station = config.get("station")
    # cell_id = kwargs.get("cell_name", "")
    # cell_number = re.findall(r"\d+", cell_id)
    # if "holder_MT11C" in station:
    #     if result:
    #         test_result = "PASS"
    #     else:
    #         test_result = "FAIL"
    #     create_result_file(cavity_id=str(cell_number[0]), result=test_result)

    return result, value


def dummy_long_test(connections, logger, **kwargs):
    import time

    logger.info("Begin long dummy test...")
    for i in range(3):
        time.sleep(1)
        logger.info(f"Dummy test step {i+1}")
    return True, "OK"


def battery_cell_information(connections, logger, **kwargs):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode="hid", read_only=True, reply_hop_count=1, hop_count=1, parameter=0x01
                )
                logger.debug(f"build cmd: {cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.debug(response)
                if response:
                    break
                else:
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            logger.debug(e)
            time.sleep(1)
            continue
    while not stop_event.is_set():
        time.sleep(1)
        uart_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x080,
        )
        logger.info(f"read temp (0x080) uart_frame is:{uart_frame}")
        response = connection.send_receive(uart_frame, timeout=1)
        logger.info(f"read temp (0x080) response is:{response}")
        res = builder.unpack_payload_fields(
            payload=response,
            offset=9,
            fields=[
                ("t1", 1),
                ("t2", 1),
                ("ADC1", 2),
                ("ADC2", 2),
            ],
        )
        logger.debug(f'80_t1:{res.get("t1")}')
        logger.debug(f'80_t2:{res.get("t2")}')
        logger.debug(f'80_ADC1:{res.get("ADC1")}')
        logger.debug(f'80_ADC2:{res.get("ADC2")}')
        T1 = res.get("t1")
        T2 = res.get("t2")
        ADC1 = res.get("ADC1")
        ADC2 = res.get("ADC2")
        # Following capture ADC data
        uart_frame1 = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x083,
        )
        logger.info(f"read temp (0x083)uart_frame is:{uart_frame1.hex()}")
        response = connection.send_receive(uart_frame1, timeout=1)
        logger.info(f"read temp (0x083) response is:{response}")
        res = builder.unpack_payload_fields(
            payload=response,
            offset=5,
            fields=[
                ("83_volt", 2),
                ("battery_ADC", 2),
            ],
        )
        # logger.debug(f'battery_ADC:{res.get("battery_ADC")}')
        battery_ADC = res.get("battery_ADC")
        voltage_83 = res.get("83_volt")
        logger.info(f'83_temperature is {battery_ADC}')
        logger.info(f'83_voltage: {voltage_83}')
        temp = T1 + (T2 - T1) * ((battery_ADC - ADC1) / (ADC2 - ADC1))
        temp =int(temp)

        time.sleep(2)
        cmd_read = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=1,
            hop_count=1,
            parameter=0x0285,
        )
        print(f"cmd_read: {cmd_read.hex()}")
        logger.debug(f"build cmd: {cmd_read.hex()}")
        response = connection.send_receive(cmd_read, timeout=1)
        logger.info(response)
        res = builder.unpack_payload_fields(
            payload=response,
            offset=5,
            fields=[
                ("Temperature", 2),
                ("Voltage", 2),
                ("Current", 2),
                ("Remaining_capacity", 2),
                ("Full_charge_capacity", 2),
                ("Relative_state_of_charge", 2),
                ("State_of_health", 2),
            ],
        )
        logger.info(f'Temperature:{res.get("Temperature")}')
        logger.info(f'Voltage:{res.get("Voltage")}')
        logger.info(f'Current:{res.get("Current")}')
        logger.info(f'Remaining capacity:{res.get("Remaining_capacity")}')
        logger.info(f'Full charge capacity:{res.get("Full_charge_capacity")}')
        logger.info(f'Relative state of charge:{res.get("Relative_state_of_charge")}')
        logger.info(f'State of health:{res.get("State_of_health")}')

    return True, response.hex()


def battery_cell_information_uart(connections, logger, **kwargs):
    connection = connections.get("uart")
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        time.sleep(2)
        cmd_read = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x0285,
        )
        print(f"cmd_read: {cmd_read.hex()}")
        logger.debug(f"build cmd: {cmd_read.hex()}")
        response = connection.send_receive(cmd_read, timeout=1)
        logger.info(response)
        res = builder.unpack_payload_fields(
            payload=response,
            offset=7,
            fields=[
                ("Temperature", 2),
                ("Voltage", 2),
                ("Current", 2),
                ("Remaining_capacity", 2),
                ("Full_charge_capacity", 2),
                ("Relative_state_of_charge", 2),
                ("State_of_health", 2),
            ],
        )
        logger.info(f'value start.......')
        logger.info(f'83_Temperature_trans:{temp}')
        logger.info(f'83_Voltage:{voltage_83}')
        logger.info(f'285_Temperature:{res.get("Temperature")}')
        logger.info(f'285_Voltage:{res.get("Voltage")}')
        logger.info(f'285_Current:{res.get("Current")}')
        logger.info(f'285_Remaining capacity:{res.get("Remaining_capacity")}')
        logger.info(f'285_Full charge capacity:{res.get("Full_charge_capacity")}')
        logger.info(f'285_Relative state of charge:{res.get("Relative_state_of_charge")}')
        logger.info(f'285_State of health:{res.get("State_of_health")}')
        logger.info(f'value end......')

    return True, response.hex()


def create_cavity_file(cavity_id="0"):
    """
    create_cavity_file
    :param cavity_id:
    :return:
    """
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    civity_save_path = "{}:\Cavity".format(root_path)
    with LockManager(lock_name="reate_cavity_file", timeout=7200):
        if os.path.exists(r"{}".format(civity_save_path)):
            with open(r"{}\{}.txt".format(civity_save_path, cavity_id), "w+") as f:
                f.write("cavity {} start test\r".format(cavity_id))
            f.close()
        else:
            os.makedirs(r"{}".format(civity_save_path), exist_ok=True)
            with open(r"{}\{}.txt".format(civity_save_path, cavity_id), "w+") as f:
                f.write("cavity {} start test\r".format(cavity_id))
            f.close()
    return True


def create_result_file(cavity_id="0", result=""):
    """
    create_passed_file
    :param cavity_id:
    :return:
    """
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    result_save_path = "{}:\cavity".format(root_path)
    config = gl.get_value("layout_config")
    Fixture = config.get("Fixture", "")
    file_name = f'fixture,{Fixture}-{cavity_id},{result}'
    with LockManager(lock_name="reate_cavity_file", timeout=7200):
        if os.path.exists(r"{}".format(result_save_path)):
            with open(r"{}\{}.txt".format(result_save_path, file_name), "w+") as f:
                f.write("cavity {} test finish\r".format(cavity_id))
            f.close()
        else:
            os.makedirs(r"{}".format(result_save_path), exist_ok=True)
            with open(r"{}\{}.txt".format(result_save_path, file_name), "w+") as f:
                f.write("cavity {} test finish\r".format(cavity_id))
            f.close()
    return


def remove_cavity_file(cavity_id=1):
    """
    remove_cavity_file
    :param cavity_id:
    :return:
    """
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    civity_save_path = "{}:\Cavity".format(root_path)
    if os.path.exists(r"{}\{}.txt".format(civity_save_path, cavity_id)):
        os.remove(r"{}\{}.txt".format(civity_save_path, cavity_id))
    return True


def get_charger_latest_date(connections, logger):
    connection = connections.get("usb")
    cmd1 = bytes([0x3F, 0x07, 0xC9, 0x10, 0x02, 0x01, 0x01, 0x75, 0xD6])
    logger.info(f'cmd: {cmd1}')
    response = connection.send_receive(cmd1, timeout=1)
    logger.info(f'response: {response}')
    line = int.from_bytes(response[19:21], "little")
    logger.info(f'line is {line}')
    cmd = [0x3F, 0x0C, 0xC9, 0x10, 0x07, 0x01, 0x02, 0x01, 0x01]
    i = int(line) - 2
    time.sleep(3)
    ibytes = list(i.to_bytes(3, "little"))
    copy_cmd = cmd.copy()
    copy_cmd.extend(ibytes)
    copy_cmd.extend(builder.crc16(bytes(copy_cmd[3:])))
    logger.info(f'bytes cmd: {bytes(copy_cmd)}')
    response = connection.send_receive(bytes(copy_cmd), timeout=1)
    logger.info(f'response:{i} is {response}')
    charger_date = int.from_bytes(response[19:23], "little")
    logger.info(charger_date)
    base = datetime(2010, 1, 1, tzinfo=timezone.utc)
    latest_autostart = (base + timedelta(seconds=charger_date)).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f'latest auto startup time: {latest_autostart}')
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f'current_time:{current_time}')
    datetime1 = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
    datetime2 = datetime.strptime(str(latest_autostart), "%Y-%m-%d %H:%M:%S")

    date1 = datetime1.date()
    date2 = datetime2.date()

    delta = date1 - date2

    logger.info(f"Delta：{delta.days}")

    return delta
