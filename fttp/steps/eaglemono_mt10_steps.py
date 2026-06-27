import binascii
import os
import re
import time
import shutil

from src.definition.product_mapping import *
from src.libs import global_var as gl, global_var, logger
from src.libs import mes
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.common import *
from src.libs.fifo_lock import LockManager, FIFOLock
from src.libs.led_analyer import FeasaLEDAnalyzer
from src.libs.ni import NIEquipment
from src.libs.raw_data import *
from src.libs.scaner import KeyenceScanner

# from src.libs.version import *
from src.ui.ask_question import ask_question
from zeep import Client
import csv

builder = NetworkFrameBuilder()
try_count_max = 5


def scan(connections, logger, **kwargs):
    """
    Scan DU SN
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Scanning DU SN")
    # scan_infor = ask_question("请扫描 DU SN=>", auto_trigger={"Y":"1", "N":"2"})
    scan_infor = ask_question("请扫描 DU SN=>")
    logger.debug(f"scanned dusn:{scan_infor}")
    scan_infor = scan_infor.strip().lower()
    if len(scan_infor) != 20:
        if scan_infor is None or scan_infor == "":
            logger.warning("User cancel")
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        else:
            return False, "fail"
    # gl.set_value("device_number", scan_infor)
    gl.set_value("device_number", scan_infor[-8:])
    # codenticode = "{0}{1}{2}{3}".format(
    #     to_hex_without_head(gl.get_value("layout_config").get("platform_code"), 2),
    #     to_hex_without_head(gl.get_value("layout_config").get("product_code"), 2),
    #     to_hex_without_head(gl.get_value("layout_config").get("site_code"), 2),
    #     to_hex_without_head(int(scan_infor, 16), 4),
    # )
    codenticode = scan_infor
    logger.debug(f"codenticode:{codenticode}")
    gl.set_value("codenticode", codenticode)
    # gl.set_value("dusn", to_hex(int(scan_infor, 16), 4))
    gl.set_value("dusn", to_hex_without_head(int(scan_infor[-8:], 16), 4))
    gl.set_value(
        "platform",
        to_hex_without_head(gl.get_value("layout_config").get("platform_code"), 2),
    )
    gl.set_value(
        "site_code",
        to_hex_without_head(gl.get_value("layout_config").get("site_code"), 2),
    )
    gl.set_value("pn", to_hex_without_head(gl.get_value("layout_config").get("product_code"), 2))
    return True, to_hex_without_head(int(scan_infor, 16), 10)


# def scan_device_barcode(connections, logger, **kwargs):
#     """
#     Scan codentify code
#     :param connections:
#     :param logger:
#     :param kwargs:
#     :return:
#     """
#     logger.info("Scanning codentify code")
#     cell_id = kwargs.get("cell_name", "")
#     with LockManager(lock_name="scan_barcode", timeout=7200):
#         try:
#             scan_infor = ask_question("请扫描 {} codentify code ->".format(cell_id))
#         except Exception as e:
#             logger.debug(e)
#             FIFOLock.release()
#     equal_value = kwargs.get("limit").get("min")
#     scan_infor = scan_infor.strip()
#     if not scan_infor:
#         if scan_infor is None or scan_infor == "":
#             logger.warning("User cancel")
#             gl.set_value("error_code", kwargs.get("error_code", ""))
#             return False, "fail"
#     gl.set_value("codentify_code", scan_infor.upper())
#     logger.info("Scanning device (simulate scan)...")
#     verify_status, meg = verify_limit(len(scan_infor), equal_value, "codentify_code_length")
#     if not verify_status:
#         gl.set_value("error_code", kwargs.get("error_code", ""))
#         return False, scan_infor.upper()
#     else:
#         if "MT11C" in gl.get_value("layout_config").get("station").upper():
#             create_cavity_file(cavity_id=kwargs.get("cell_name")[4:])
#         return True, scan_infor.upper()


def scan_device_barcode(connections, logger, **kwargs):
    """
    Scan codentify code
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Scanning codentify code")
    cell_id = kwargs.get("cell_name", "")
    equal_value = kwargs.get("limit").get("min")
    stop_event = gl.get_value("stop_event")
    with LockManager(lock_name="scan_barcode", timeout=7200):
        while not stop_event.is_set():
            scan_infor = ask_question("请扫描 {} codentify code ->".format(cell_id))
            scan_infor = scan_infor.strip()
            verify_status, meg = verify_limit(len(scan_infor), equal_value, "codentify_code_length")
            if not verify_status:
                continue
            else:
                if "MT11C" in gl.get_value("layout_config").get("station").upper():
                    create_cavity_file(cavity_id=kwargs.get("cell_name")[4:])
                # FIFOLock.release()
                gl.set_value("codentify_code", scan_infor.upper())
                break
    return True, scan_infor.upper()


def scan_tbbuid(connections, logger, **kwargs):
    """
    Scan tbbuid code
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Scanning tbbuid code")
    equal_value = kwargs.get("limit").get("min")
    scan_infor = ask_question("请扫描 tbbuid ->")
    scan_infor = scan_infor.strip()
    if not scan_infor:
        if scan_infor is None or scan_infor == "":
            logger.warning("User cancel")
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    scan_infor = scan_infor.replace(" ", "")
    gl.set_value("tbbuid_code", scan_infor.upper())
    logger.info("Scanning tbbuid {} (simulate scan)...".format(scan_infor))
    verify_status, msg = verify_limit(len(scan_infor), equal_value, "tbbuid_code_length")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, scan_infor.upper()
    else:
        return True, scan_infor.upper()


def qr_scan(connections, logger, **kwargs):
    """
    Scan QR codes
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Scanning QR code...")
    connection = connections.get("scanner")
    equal_value = kwargs.get("limit").get("min")
    scan_infor = kwargs.get("scan_infor", "")
    scanner = KeyenceScanner(connection, logger)
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            scan_qr_data = scanner.auto_scan()
            if len(scan_qr_data) == equal_value:
                break
            else:
                continue
        except Exception as e:
            logger.debug(e)
            continue
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, scan_qr_data.upper()
    gl.set_value("{}".format(scan_infor), scan_qr_data)
    check_golden_unit(logger)
    ni_device = NIEquipment(device_name="Dev1")
    # time.sleep(0.1)
    ni_device.write_digital("port0/line1", value=True, timeout=1)
    # time.sleep(0.3)
    # ni_device.write_digital("port0/line3", value=True, timeout=1)
    time.sleep(0.5)
    move_confentify_sn(logger, **kwargs)
    save_confentify_sn(confentify_sn=scan_qr_data.upper())
    return True, scan_qr_data.upper()


def initialize_configs(connections, logger, **kwargs):
    """
    initialize_configs
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Initializing configs...")
    station_configs = gl.get_value("layout_config")
    gl.set_value("product_code", to_hex_without_head(station_configs.get("product_code", ""), 2))
    gl.set_value("pn", to_hex_without_head(station_configs.get("product_code", ""), 2))
    gl.set_value("site_code", to_hex_without_head(station_configs.get("site_code", ""), 2))
    gl.set_value("platform", to_hex_without_head(station_configs.get("platform_code", ""), 2))
    gl.set_value("hardware_version", to_hex(station_configs.get("hardware_version", ""), 1))
    gl.set_value("trs", station_configs.get("trs", ""))
    gl.set_value("trs_version", station_configs.get("trs_version", ""))
    gl.set_value("station_id", station_configs.get("station_id", ""))
    gl.set_value("fixture_id", station_configs.get("station_id", ""))
    gl.set_value("station", station_configs.get("station", ""))
    gl.set_value("TBBUID", station_configs.get("TBBUID", ""))
    gl.set_value("golden_unit_flag", station_configs.get("golden_unit_flag", False))
    gl.set_value("fw_ver", station_configs.get("fw_ver", ""))
    gl.set_value("sn_path", station_configs.get("sn_path", ""))
    gl.set_value("golden_sn_path", station_configs.get("golden_sn_path", ""))
    gl.set_value("picture_path", station_configs.get("picture_path", ""))
    return True, "pass"


def detect_pre_dut(connections, logger, **kwargs):
    """
    detect DUT infors
    :param connections:
    :param logger:
    :param kwargs:.
    :return:
    """
    print(connections)
    connection = connections.get("serial_dut")
    stop_event = gl.get_value("stop_event")
    if "MT11C" in gl.get_value("layout_config").get("station").upper():
        ni_device = NIEquipment(device_name="Dev1")
        # time.sleep(0.1)
    while not stop_event.is_set():
        if connection.ensure_connected():
            cmd_frame = builder.build_read_request_frame(
                mode="uart",
                read_only=True,
                reply_hop_count=0,
                hop_count=0,
                parameter=0x01,
            )
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response)
            if response:
                # time.sleep(2)
                continue
            else:
                if "MT11C" in gl.get_value("layout_config").get("station").upper():
                    time.sleep(2)
                    with LockManager(lock_name="ni_device", timeout=7200):
                        # ni_device = NIEquipment(device_name="Dev1")
                        ni_device.write_digital(
                            charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))],
                            value=False,
                            timeout=1,
                        )
                        # time.sleep(0.1)
                        ni_device.write_digital(
                            charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))],
                            value=False,
                            timeout=1,
                        )
                    remove_cavity_file(cavity_id=kwargs.get("cell_name")[4:])
                break
                logger.info("SImon _____")
        else:
            time.sleep(0.1)
            connection.close()
            continue
    return True


def detect_dut(connections, logger, **kwargs):
    """
    detect DUT infors
    :param connections:
    :param logger:
    :param kwargs:.
    :return:
    """
    print(connections)
    connection = connections.get("serial_dut")
    logger.info(f"connection is :{connection}.")
    stop_event = gl.get_value("stop_event")
    if "MT7" in gl.get_value("layout_config").get("station", ""):
        switch_usb_a_on(connections, logger)
        ni_device = NIEquipment(device_name="Dev1")
        # time.sleep(0.1)
        ni_device.write_digital("port0/line0", value=False, timeout=1)
        # time.sleep(0.1)
        ni_device.write_digital("port0/line3", value=False, timeout=1)
        # time.sleep(0.1)
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        ni_device.write_digital("port0/line1", value=False, timeout=1)
    if "MT7" not in gl.get_value("layout_config").get("station", ""):
        detect_pre_dut(connections, logger, **kwargs)
    if "MT11C" in gl.get_value("layout_config").get("station").upper():
        ni_device = NIEquipment(device_name="Dev1")
        # time.sleep(0.1)
    while not stop_event.is_set():
        try:
            if "MT7" in gl.get_value("layout_config").get("station", ""):
                start_button_detection(connections, logger, **kwargs)
            if connection.ensure_connected():
                logger.info("SImon _____")
                cmd_frame = builder.build_read_request_frame(
                    mode="uart",
                    read_only=True,
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x01,
                )
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.info("SImon _____")
                logger.debug(response)
                if response:
                    time.sleep(1)
                    res = builder.unpack_payload_fields(
                        payload=response,
                        offset=3,
                        fields=[
                            ("platform_code", 2),
                            ("product_code", 2),
                            ("site_code", 2),
                            ("device_number", 4),
                            ("hardware_revision", 2),
                            ("reserve", 2),
                        ],
                    )
                    codenticode = "{0}{1}{2}{3}".format(
                        to_hex_without_head(res.get("platform_code"), 2),
                        to_hex_without_head(res.get("product_code"), 2),
                        to_hex_without_head(res.get("site_code"), 2),
                        to_hex_without_head(res.get("device_number"), 4),
                    )
                    gl.set_value("dusn", to_hex_without_head(res.get("device_number"), 4))
                    # time.sleep(3)
                    # reset_dut(connections, logger, **kwargs)
                    break
                else:
                    # if "MT11C" in gl.get_value("layout_config").get("station").upper() and clear_indicator:
                    #     with LockManager(lock_name="ni_device", timeout=7200):
                    #         # ni_device = NIEquipment(device_name="Dev1")
                    #         ni_device.write_digital(charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))],
                    #                                 value=False,
                    #                                 timeout=1)
                    #         ni_device.write_digital(charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))],
                    #                                 value=False,
                    #                                 timeout=1)
                    #     clear_indicator = False
                    if "MT11C" in gl.get_value("layout_config").get("station").upper():
                        time.sleep(2)
                    continue
            else:
                time.sleep(0.1)
                connection.close()
                continue
        except Exception as e:
            time.sleep(0.1)
            continue
    if "MT1" not in gl.get_value("layout_config").get("station").upper():
        pattern = (
            str(to_hex_without_head(gl.get_value("layout_config").get("platform_code"), 2)).lower()
            + str(to_hex_without_head(gl.get_value("layout_config").get("product_code"), 2)).lower()
            + str(to_hex_without_head(gl.get_value("layout_config").get("site_code"), 2)).lower()
        )
    else:
        pattern = "."
    match = re.findall(pattern, codenticode)
    if match:
        if "MT11C" in gl.get_value("layout_config").get("station").upper():
            with LockManager(lock_name="ni_device", timeout=7200):
                # ni_device = NIEquipment(device_name="Dev1")
                ni_device.write_digital(
                    charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))],
                    value=True,
                    timeout=1,
                )
                # time.sleep(0.1)
                ni_device.write_digital(
                    charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))],
                    value=True,
                    timeout=1,
                )
            # create_cavity_file(cavity_id=kwargs.get("cell_name")[4:])
        gl.set_value("codenticode", codenticode)
        return True, codenticode.upper()
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, codenticode.upper()


def read_dusn(connections, logger, **kwargs):
    """
    read_dusn
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read DUSN")
    first_time_read = kwargs.get("first_time_read", False)
    connection = connections.get("serial_dut")
    response = read_send_receive(connections, logger, parameter=0x01, **kwargs)
    if not response:
        if first_time_read:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            connection.close()
            time.sleep(1)
            connection.ensure_connected()
            time.sleep(5)
        return False, "fail"
    crc = verify_crc(logger=logger, data=response, connection="hid")
    logger.info(f"CRC value is {crc}")
    if not crc:
        if first_time_read:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            time.sleep(1)
        return False, "fail"
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
    product_code = to_hex_without_head(res.get("product_code"), 2)
    platform_code = to_hex_without_head(res.get("platform_code"), 2)
    site_code = to_hex_without_head(res.get("site_code"), 2)
    device_number = to_hex_without_head(res.get("device_number"), 4)
    dusn = platform_code + product_code + site_code + device_number
    logger.debug(f"dusn:{dusn}")
    if first_time_read:
        pattern = (
            gl.get_value("platform").lower() + gl.get_value("product_code").lower() + gl.get_value("site_code").lower()
        )
        match = re.findall(pattern, dusn)
        if match:
            codenticode = dusn
            gl.set_value("codenticode", codenticode)
        else:
            logger.debug("product infors wrong")
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, dusn.upper()
    verify_status, msg = verify_limit(dusn, gl.get_value("codenticode"), "dusn_content")
    if verify_status:
        return True, dusn.upper()
    else:
        return False, dusn.upper()


def led_off(connections, logger, **kwargs):
    """
    LED off
    :param connections:
    :param loger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    led_connection = connections.get("led_analyzer")
    intensity_min = kwargs.get("intensity_min")
    intensity_max = kwargs.get("intensity_max")
    capture = kwargs.get("capture")
    led_number = "%02d" % kwargs.get("led_number")
    logger.debug(f"channel:{led_number}")
    if capture:
        led_analyzer = FeasaLEDAnalyzer(led_connection, logger)
        hid_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=14,
            count=1,
            value=0xA0,
        )
        response = connection.send_receive(hid_frame, timeout=1)
        logger.debug(response)
        for i in range(3):
            if "OK" not in str(led_analyzer.capture()).upper():
                time.sleep(0.1)
                continue
            break
        else:
            gl.set_value("error_code", kwargs.get("red_error_code", ""))
            return False, "fail"
        led_received_data = led_analyzer.get_intensity_all()
        logger.debug(led_received_data)
        gl.set_value("led_received_data", led_received_data)
    verify_status, meg = verify_limit(
        gl.get_value("led_received_data")[led_number],
        limit_def=(intensity_min, intensity_max),
        name="LED OFF",
    )
    if not verify_status:
        gl.set_value("error_code", kwargs.get("red_error_code", ""))
        return False, str(int(gl.get_value("led_received_data")[led_number]))
    else:
        return True, str(int(gl.get_value("led_received_data")[led_number]))


def ui_led_test(connections, logger, **kwargs):
    """
    UI LED test
    :param connections:
    :param loger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    led_connection = connections.get("led_analyzer")
    capture = kwargs.get("capture")
    led_test_item = kwargs.get("rgb_item")
    min = kwargs.get("limit").get("min")
    max = kwargs.get("limit").get("max")
    if capture:
        led_analyzer = FeasaLEDAnalyzer(led_connection, logger)
        channel = "%02d" % kwargs.get("channel")
        logger.debug(f"channel:{channel}")
        module = kwargs.get("module")
        color = kwargs.get("color")
        bank = kwargs.get("bank")
        brightness = kwargs.get("capture_brihgtness")
        logger.debug(f"module:{module}, color:{color}, bank:{bank}")
        cmd_hex = led_cmd_mapping.get(module, {})[bank].get(color)
        hid_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=14,
            count=1,
            value=cmd_hex,
        )
        response = connection.send_receive(hid_frame, timeout=1)
        logger.debug(response)
        for i in range(3):
            if "OK" not in str(led_analyzer.capture(brightness=brightness)).upper():
                time.sleep(0.1)
                continue
            break
        else:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        rgb_received = led_analyzer.get_rgbi(channel)
        gl.set_value("red_value", rgb_received.get("R"))
        gl.set_value("green_value", rgb_received.get("G"))
        gl.set_value("blue_value", rgb_received.get("B"))
        gl.set_value("intensity_value", rgb_received.get("I"))
        logger.debug("LED analyzer R G B I received is {}".format(rgb_received))
    if "red" in led_test_item:
        led_value = gl.get_value("red_value")
    if "green" in led_test_item:
        led_value = gl.get_value("green_value")
    if "blue" in led_test_item:
        led_value = gl.get_value("blue_value")
    if "intensity" in led_test_item:
        led_value = gl.get_value("intensity_value")
    verify_status, meg = verify_limit(led_value, (min, max))
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(int(led_value))
    else:
        return True, str(int(led_value))


def read_ble_mac(connections, logger, **kwargs):
    """
    SDD data:0x40 0x30 actual pnum:64, count=3
        should put data=0x3040, for revert to 40 30
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    # enable_ble_broadcast(connections, logger)
    equal_value = kwargs.get("limit").get("min")
    time.sleep(0.2)
    response = bba_read_send_receive(connections, logger, pnum=64, count=4, **kwargs)
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
    mac = ":".join(mac[i : i + 2] for i in range(0, len(mac), 2))
    verify_status, meg = verify_limit(len(mac), equal_value, "ble_mac_length")
    if verify_status and mac[:4] != "FF:FF":
        return True, mac
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, mac


def enable_ble_broadcast(connections, logger, **kwargs):
    """
    Enable ble Broadcast
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    hid_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0x00BE,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)
    if response:
        time.sleep(0.1)
        return True, "pass"
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"


def read_ble_status(connections, logger, **kwargs):
    """
    read ble status
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    ble_status = kwargs.get("ble_status", None)
    if ble_status == "disabled":
        ble_status_read = "0101"
    elif ble_status == "enable":
        ble_status_read = "0001"
    logger.debug(f"ble_status:{ble_status}")
    logger.debug(f"ble_status_read:{ble_status_read}")
    hid_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x05,
        feature=0x01,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("ble_status", 4),
        ],
    )
    logger.debug(res)
    status = to_hex(res["ble_status"], 4)
    print(f"ble status:{status}")
    if ble_status_read not in status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, ble_status_read
    else:
        return True, ble_status_read


def read_ble_rf_status(connections, logger, **kwargs):
    """
    read ble rf status
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    response = read_send_receive(connections, logger, parameter=0x8C, **kwargs)
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ble_tx_rx_status", 1), ("packets", 2)])
    ble_tx_rx_status = to_hex(res["ble_tx_rx_status"], 1)
    packets = res["packets"]
    print(f"ble status:{ble_tx_rx_status}")
    print(f"packets:{packets}")
    return True, ble_tx_rx_status


def verify_hw_revision(connections, logger, **kwargs):
    """
    verify hw reversion
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("verify_hw_revision...")
    hardware_version = gl.get_value("hardware_version")
    connection = connections.get("serial_dut")
    response = bba_read_send_receive(connections, logger, pnum=35, count=1, **kwargs)
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("hardware_revision", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(to_hex(res.get("hardware_revision"), 1), hardware_version, "hardware_revision")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex(res.get("hardware_revision"), 1)
    else:
        return True, to_hex(res.get("hardware_revision"), 1)


def write_hw_reversion(connections, logger, **kwargs):
    """
    write hw reversion
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("write_hw_reversion...")
    connection = connections.get("serial_dut")
    hardware_version = gl.get_value("layout_config").get("hardware_version")
    hardware_version = list(binascii.unhexlify(hex(hardware_version)[2:].zfill(4)))
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=35,
        count=1,
        value0=hardware_version[1],
        value1=hardware_version[0],
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    return True, "pass"


def finalize(connections, logger, **kwargs):
    """
    test finalize
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("finalize")
    for name, conn in connections.items():
        conn.close()
    return True, "pass"


def dummy_long_test(connections, logger, **kwargs):
    """
    dummy long test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    import time

    logger.info("Begin long dummy test...")
    for i in range(3):
        time.sleep(1)
        logger.info(f"Dummy test step {i+1}")
    return True, "pass"


def start_button_detection(connections, logger, press_button=False, **kwargs):
    """
    start button detection
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    ni_device = NIEquipment(device_name="Dev1")
    # time.sleep(0.1)
    stop_event = gl.get_value("stop_event")
    if press_button:
        ni_device.write_digital("port0/line2", value=True, timeout=1)
        time.sleep(1)
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        time.sleep(4)
    else:
        while not stop_event.is_set():
            try:
                response = ni_device.read_digital("port1/line0", timeout=1)
                if response:
                    break
                else:
                    time.sleep(0.1)
                    continue
            except Exception as e:
                time.sleep(0.1)
                continue
        else:
            return False, "fail"
        ni_device.write_digital("port0/line0", value=True, timeout=1)
        # time.sleep(0.1)
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        time.sleep(0.5)
        ni_device.write_digital("port0/line3", value=True, timeout=1)
    return True, "pass"


# def switch_usb_b_on(connections, logger, delay_time=1, **kwargs):
#     """
#     switch usb a
#     :param connections:
#     :param logger:
#     :param kwargs:
#     :return:
#     """
#     logger.info("Test USB B on")
#     ni_device = NIEquipment(device_name="Dev1")
#     ni_device.write_digital("port1/line2", value=False, timeout=1)
#     ni_device.write_digital("port1/line1", value=True, timeout=1)
#     ni_device.write_digital("port0/line4", value=False, timeout=1)
#     ni_device.write_digital("port0/line5", value=False, timeout=1)
#     ni_device.write_digital("port0/line6", value=True, timeout=1)
#     time.sleep(delay_time)
#     return True, "pass"


def switch_usb_b_on(connections, logger, delay_time=1, **kwargs):
    """
    switch usb a
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.info("Test USB B on")
    ni_device = NIEquipment(device_name="Dev1")
    ni_device.write_digital("port1/line2", value=False, timeout=1)
    ni_device.write_digital("port1/line1", value=True, timeout=1)
    ni_device.write_digital("port0/line4", value=False, timeout=1)
    ni_device.write_digital("port0/line5", value=False, timeout=1)
    ni_device.write_digital("port0/line6", value=True, timeout=1)
    # ni_device.write_digital("port0/line6", value=True, timeout=1)
    time.sleep(delay_time)
    return True, "pass"


def read_mt_mode(connections, logger, **kwargs):
    """
    read mt mode
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Start read MT mode")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = bba_read_send_receive(connections, logger, pnum=36, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        connection.close()
        time.sleep(1)
        connection.ensure_connected()
        time.sleep(5)
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("mt_mode", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(to_hex_without_head(res["mt_mode"], 2), "0000", "DUT_mode")
    if verify_status:
        gl.set_value("exit_mt_mode", True)
        # return True, to_hex_without_head(res["mt_mode"], 2), "Reset_DUT"
        return True, "pass", "Reset_DUT"
    else:
        gl.set_value("exit_mt_mode", False)
        # return True, to_hex_without_head(res["mt_mode"], 2)
        return True, "pass"


def read_fw_id(connections, logger, **kwargs):
    """
    read fw id
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Start reading fw ID")
    connection = connections.get("serial_dut")
    equal_value = gl.get_value("fw_ver", "")
    response = read_send_receive(connections, logger, parameter=0x00, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        connection.close()
        time.sleep(1)
        connection.ensure_connected()
        time.sleep(5)
        return False, "fail"
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("app_id", 2),
            ("app_major", 1),
            ("app_minor", 1),
            ("app_patch", 1),
            ("build number", 2),
        ],
    )
    logger.debug(res)
    app_version = str(res["app_major"]) + "." + str(res["app_minor"]) + "." + str(res["app_patch"])
    gl.set_value("app_version", app_version)
    gl.set_value("build number", to_hex(res.get("build number"), 2))
    res = builder.unpack_payload_fields(payload=response, offset=18, fields=[("sbl_major_id", 1)])
    logger.debug(res)
    gl.set_value("sbl_major_id", to_hex(res.get("sbl_major_id"), 1))
    if kwargs.get("engineer_mode"):
        return True, app_version
    verify_status, msg = verify_limit(app_version, equal_value, "app_version")
    logger.debug("config fw is {}, verify status is {}".format(equal_value, verify_status))
    if verify_status:
        return True, app_version
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, app_version


def read_app_id(connections, logger, **kwargs):
    """
    read app id
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("read app_id")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = read_send_receive(connections, logger, parameter=0x00, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(
        payload=response,
        offset=5,
        fields=[
            ("app_id", 2),
        ],
    )
    logger.debug(res)
    if to_hex_without_head(res.get("app_id"), 1) == "0F":
        gl.set_value("error_code", "0004")
        if gl.get_value("exit_mt_mode"):
            gl.set_value("error_code", "003A")
        return False, str(to_hex_without_head(res.get("app_id"), 1))
    verify_status, msg = verify_limit(to_hex_without_head(res.get("app_id"), 1), equal_value, "app_id")
    if verify_status:
        return True, str(to_hex_without_head(res.get("app_id"), 1))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(to_hex_without_head(res.get("app_id"), 1))


def retrieve_sbl_major_id(connections, logger, **kwargs):
    """
    retrieve sbl major id
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("retrieve_sbl_major_id")
    equal_value = kwargs.get("limit").get("min")
    logger.debug(gl.get_value("sbl_major_id"))
    verify_status, msg = verify_limit(gl.get_value("sbl_major_id")[2:], equal_value, "sbl_major_id")
    if verify_status:
        return True, str(gl.get_value("sbl_major_id")[2:])
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(gl.get_value("sbl_major_id")[2:])


def holder_presence_detection(connections, logger, **kwargs):
    """
    holder presence detection
    :param cconnections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    logger.debug("Start holder presence detection")
    equal_value = kwargs.get("limit").get("min")
    if gl.get_value("exit_mt_mode"):
        logger.debug(" unit not in MT mode")
        response = read_send_receive(connections, logger, parameter=0x85, **kwargs)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=9, fields=[("holder_presence_status", 1)])
        logger.debug(res)
        if to_hex(res.get("holder_presence_status"), 1) == "0x03":
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, str(to_hex(res.get("holder_presence_status"), 1))
        else:
            logger.debug("Holder Presence Detection Successful")
            return True, str(to_hex(res.get("holder_presence_status"), 1))
    else:
        logger.debug(" unit in mt mode")
        cmd_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=14,
            count=1,
            value=0xD5,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
        time.sleep(0.1)
        response = bba_read_send_receive(connections, logger, pnum=19, count=1, **kwargs)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("holder_presence_status", 1)])
        logger.debug(res)
        verify_status, msg = verify_limit(res.get("holder_presence_status"), equal_value, "holder_presence")
        if verify_status:
            return True, str(res.get("holder_presence_status"))
        else:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            logger.debug("Read holder presence Test Failed, read value {}".format(res.get("holder_presence_status")))
            return False, str(res.get("holder_presence_status"))


def read_station_id(connections, logger, **kwargs):
    """
    read station id
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Start read station id")
    station_id = gl.get_value("station_id", "")
    # verify_status, msg = verify_limit(
    #     len(station_id), kwargs.get("limit").get("min"), "id length"
    # )
    # if verify_status:
    return True, str(station_id)
    # else:
    #     gl.set_value("error_code", kwargs.get("error_code", ""))
    #     return False, station_id


def logging_test_cell(connections, logger, **kwargs):
    """
    logging test cell number
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Start logging test cell number")
    cell_number = kwargs.get("cell_name")[4:]
    return True, str(cell_number)


def logging_build_number(connections, logger, **kwargs):
    """
    logging software build number
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("logging software build number")
    build_number = build_time + "_" + commit
    return True, str(build_number)


def read_usb_c_infors(connections, logger, **kwargs):
    """
    read USB C infors
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug(" unit with USB C info")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xD1,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(0.1)
    response = bba_read_send_receive(connections, logger, pnum=19, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("usb_c_infors", 1)])
    logger.debug(res)
    verify_status, msg = verify_limit(res.get("usb_c_infors"), equal_value, "usb_c_value")
    if verify_status:
        return True, str(res.get("usb_c_infors"))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug("Read USB C infors Test Failed, read value {}".format(res.get("usb_c_infors")))
        return False, str(res.get("usb_c_infors"))


def usb_c_adc_side_a_test(connections, logger, **kwargs):
    """
    usb_c_adc_side_a_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug(" unit with USB CC ADC side A Test")
    connection = connections.get("serial_dut")
    min_value, max_value = kwargs.get("limit").get("min"), kwargs.get("limit").get("max")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00D2,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(0.2)
    response = bba_read_send_receive(connections, logger, pnum=19, count=2, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(
        payload=response,
        offset=7,
        fields=[("usb_c_adc_side_a_value", 2), ("usb_c_adc_side_b_value", 2)],
    )
    logger.debug("usb c side a adc value is {}".format(res))
    verify_status, msg = verify_limit(
        res.get("usb_c_adc_side_a_value"),
        (min_value, max_value),
        "usb_c_adc_side_a_value",
    )
    if verify_status:
        return True, str(res.get("usb_c_adc_side_a_value"))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug("USB a adc value test Failed, value is {}".format(res.get("usb_c_adc_side_a_value")))
        return False, str(res.get("usb_c_adc_side_a_value"))


def usb_orientation_a_test(connections, logger, **kwargs):
    """
    usb_orientation_a_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("usb_orientation_a_test")
    if gl.get_value("skip_user_mode_side_switch", False):
        logger.debug("USB A B side already be covered in MT mode steps")
        return True, "skipped"
    switch_usb_a_on(connections, logger, **kwargs)
    connection = connections.get("serial_dut")
    connection.close()
    connection.ensure_connected()
    for i in range(3):
        status, dusn = read_dusn(connections, logger)
        if not status:
            # switch_usb_a_on(connections, logger, delay_time=3, **kwargs)
            if "MT7" in gl.get_value("layout_config").get("station", ""):
                switch_usb_b_on(connections, logger)
                switch_usb_a_on(connections, logger, delay_time=3, **kwargs)
                ni_device = NIEquipment(device_name="Dev1")
                ni_device.write_digital("port0/line2", value=True, timeout=1)
                time.sleep(15)
                ni_device.write_digital("port0/line2", value=False, timeout=1)
                time.sleep(5)
            continue
        else:
            break
    logger.debug("read dusn is  {}".format(dusn))
    if not status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, dusn
    else:
        return True, dusn


def usb_orientation_b_test(connections, logger, **kwargs):
    """
    usb_orientation_b_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("usb_orientation_b_test")
    if gl.get_value("skip_user_mode_side_switch", False):
        logger.debug("USB A B side already be covered in MT mode steps")
        return True, "skipped"
    switch_usb_b_on(connections, logger, **kwargs)
    connection = connections.get("serial_dut")
    connection.close()
    connection.ensure_connected()
    for i in range(3):
        status, dusn = read_dusn(connections, logger)
        if not status:
            if "MT7" in gl.get_value("layout_config").get("station", ""):
                switch_usb_a_on(connections, logger)
                switch_usb_b_on(connections, logger, delay_time=3, **kwargs)
                ni_device = NIEquipment(device_name="Dev1")
                ni_device.write_digital("port0/line2", value=True, timeout=1)
                time.sleep(17)
                ni_device.write_digital("port0/line2", value=False, timeout=1)
                time.sleep(5)
            continue
        else:
            break
    logger.debug("read dusn is  {}".format(dusn))
    if not status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, dusn
    else:
        # if gl.get_value("exit_mt_mode"):
        #     enable_holder_charging(connections, logger, **kwargs)
        return True, dusn


# def switch_usb_a_on(connections, logger, delay_time=1, **kwargs):
#     """
#     switch_usb_a_on
#     :param connections:
#     :param logger:
#     :param kwargs:
#     :return:
#
#     """
#     logger.debug(" unit with USB A ON")
#     ni_device = NIEquipment(device_name="Dev1")
#     ni_device.write_digital("port1/line1", value=False, timeout=1)
#     ni_device.write_digital("port1/line2", value=True, timeout=1)
#     ni_device.write_digital("port0/line4", value=True, timeout=1)
#     ni_device.write_digital("port0/line5", value=True, timeout=1)
#     ni_device.write_digital("port0/line6", value=False, timeout=1)
#     time.sleep(delay_time)
#     return True, "pass"


def switch_usb_a_on(connections, logger, delay_time=1, **kwargs):
    """
    switch_usb_a_on
    :param connections:
    :param logger:
    :param kwargs:
    :return:

    """
    logger.debug(" unit with USB A ON")
    ni_device = NIEquipment(device_name="Dev1")
    ni_device.write_digital("port1/line1", value=False, timeout=1)
    ni_device.write_digital("port1/line2", value=True, timeout=1)
    ni_device.write_digital("port0/line4", value=True, timeout=1)
    ni_device.write_digital("port0/line5", value=True, timeout=1)
    ni_device.write_digital("port0/line6", value=False, timeout=1)
    ni_device.write_digital("port0/line7", value=False, timeout=1)
    time.sleep(delay_time)
    return True, "pass"


def usb_c_adc_side_b_test(connections, logger, **kwargs):
    """
    usb_c_adc_side_b_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug(" unit with USB CC ADC side B Test")
    connection = connections.get("serial_dut")
    min_value, max_value = kwargs.get("limit").get("min"), kwargs.get("limit").get("max")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0x00D2,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send(cmd_frame)
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(0.2)
    response = bba_read_send_receive(connections, logger, pnum=20, count=2, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("usb_c_adc_side_b_value", 2)])
    logger.debug("usb b adc value is {}".format(res))
    verify_status, msg = verify_limit(
        res.get("usb_c_adc_side_b_value"),
        (min_value, max_value),
        "usb_c_adc_side_b_value",
    )
    if verify_status:
        return True, str(res.get("usb_c_adc_side_b_value"))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug("USB C side B adc value test Failed, value is {}".format(res.get("usb_c_adc_side_b_value")))
        return False, str(res.get("usb_c_adc_side_b_value"))


def bist_test(connections, logger, **kwargs):
    """
    bist_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("start BIST test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=281,
        count=1,
        value=0x02,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send(cmd_frame)
    time.sleep(0.01)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xFFFF,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send(cmd_frame)
    time.sleep(0.1)
    response = bba_read_send_receive(connections, logger, pnum=15, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("bist_status", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(res.get("bist_status"), int(equal_value), "bist test")
    if verify_status:
        return True, to_hex_without_head(res.get("bist_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res.get("bist_status"), 2)


def read_rwk_key_length(connections, logger, **kwargs):
    """
    read_rwk_key_length
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = bba_read_send_receive(connections, logger, pnum=67, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("rwk_key_length", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(res.get("rwk_key_length") * 2, equal_value, "rwk_key_length")
    if verify_status:
        logger.debug("Get key length PASS")
        return True, str(res.get("rwk_key_length") * 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(res.get("rwk_key_length") * 2)


def read_rwk_key(connections, logger, **kwargs):
    """
    read_rwk_key
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("read rwk key")
    connection = connections.get("serial_dut")
    encryption_key = []
    for i in list(range(68, 205, 11))[:-1]:
        response = bba_read_send_receive(connections, logger, pnum=i, count=11, **kwargs)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("rwk_key_data", 22)])
        rwk_key_data_hex = to_hex(res["rwk_key_data"], 22)[2:]
        rwk_key_data_received = list(binascii.unhexlify(rwk_key_data_hex.zfill(4)))
        for key in list(reversed(rwk_key_data_received)):
            encryption_key.append(key)
    response = bba_read_send_receive(connections, logger, pnum=200, count=5, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("rwk_key_data", 10)])
    rwk_key_data_hex = to_hex(res["rwk_key_data"], 10)[2:]
    rwk_key_data = list(binascii.unhexlify(rwk_key_data_hex.zfill(4)))
    for key in list(reversed(rwk_key_data)):
        encryption_key.append(key)
    gl.set_value("rwk_data", encryption_key)
    logger.debug("key data = {}".format(encryption_key))
    time.sleep(0.01)
    response = bba_read_send_receive(connections, logger, pnum=277, count=2, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("rwk_checksum", 4)])
    logger.debug(res)
    gl.set_value("rwk_crc", res["rwk_checksum"])
    save_temp_rwk_data()
    return True, "pass"


def retrieve_battery_data(connections, logger, **kwargs):
    """
    retrieve_battery_data
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("retrieve battery data")
    min_value = kwargs.get("limit").get("min")
    max_value = kwargs.get("limit").get("max")
    equal_value = [min_value, max_value]
    dut_data_status, dut_data = routing_check(
        connections, logger, sn=gl.get_value("codentify_code"), station="GetBatterySN"
    )
    if "SN=" in dut_data.upper():
        pattern = r"SN=(.*?)<\/Value>"
    else:
        pattern = r"<Name>BatterySN</Name><Value>(.*?)</Value>"
    # pattern = r"SN=(.*?)<\/Value>"
    match = re.search(pattern, dut_data)
    if match:
        battery_data = match.group(1).upper()
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    logger.debug("battery sn is {}".format(battery_data))
    gl.set_value("battery_data", battery_data)
    verify_status, meg = verify_limit(len(battery_data), equal_value, "battery_sn_length")
    if len(battery_data) == max_value:
        bat_tech = battery_tech_mapping["{}".format(gl.get_value("battery_data")[14])]
        bat_vendor = battery_vendor_mapping["{}".format(gl.get_value("battery_data")[:3])]
        bat_tech_generation = gl.get_value("battery_data")[15]
    if len(battery_data) == min_value:
        bat_tech = battery_tech_mapping["{}".format(gl.get_value("battery_data")[6])]
        bat_vendor = battery_vendor_mapping["{}".format(gl.get_value("battery_data")[:1])]
        bat_tech_generation = gl.get_value("battery_data")[8]
    ble_wifi_support = "0"
    battery_configs = "{}{}{}00000".format(bat_tech, bat_vendor, ble_wifi_support)
    logger.debug("battery_config code is {}".format(battery_configs))
    result, battery_sn, configuration_code, ff_dusn = get_batterysn_configuration_code(connections, logger, **kwargs)
    if not gl.get_value("golden_unit_flag"):
        if ff_dusn.lower() != gl.get_value("codenticode").lower():
            logger.debug("codentify code ff recorded dusn not match with read dusn")
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    if result and configuration_code == battery_configs:
        logger.debug("get configuration code is correct")
        battery_configs = configuration_code
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    gl.set_value("battery_configs", battery_configs)

    if verify_status:
        return True, battery_data
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, battery_data


def retrieve_battery_data_new(connections, logger, **kwargs):
    """
    retrieve_battery_data
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("retrieve battery data")
    result, battery_sn, configuration_code, ff_dusn = get_batterysn_configuration_code(connections, logger, **kwargs)
    if not gl.get_value("golden_unit_flag"):
        if ff_dusn != gl.get_value("dusn"):
            logger.debug("codentify code ff record dusn not math with read dusn")
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    if result:
        logger.debug("get configuration code is correct")
        battery_configs = configuration_code
        gl.set_value("battery_data", battery_sn)
        gl.set_value("battery_configs", battery_configs)
        return True, battery_sn
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, battery_sn


def set_battery_configuration(connections, logger, **kwargs):
    """
    set_battery_config
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("set battery config")
    connection = connections.get("serial_dut")
    # gl.set_value("battery_data", "Y049201000000232508280")
    # battery_sn = gl.get_value("battery_data")
    # if len(battery_sn) == 28:
    #     bat_tech = battery_tech_mapping["{}".format(gl.get_value("battery_data")[14])]
    #     bat_vendor = battery_vendor_mapping[
    #         "{}".format(gl.get_value("battery_data")[:3])
    #     ]
    #     bat_tech_generation = gl.get_value("battery_data")[15]
    # if len(battery_sn) == 22:
    #     bat_tech = battery_tech_mapping["{}".format(gl.get_value("battery_data")[6])]
    #     bat_vendor = battery_vendor_mapping[
    #         "{}".format(gl.get_value("battery_data")[:1])
    #     ]
    #     bat_tech_generation = gl.get_value("battery_data")[8]
    # ble_support = "0"
    # battery_configs = "{}{}{}{}0000".format(
    #     bat_tech, bat_vendor, ble_support, bat_tech_generation
    # )
    # logger.debug("battery_config code is {}".format(battery_configs))
    # gl.set_value("battery_configs", battery_configs)

    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=279,
        count=2,
        # value0=int(battery_configs, 16),
        value0=int(gl.get_value("battery_configs"), 16),
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    return True, "pass"


def read_battery_configuration(connections, logger, **kwargs):
    """
    read_battery_config
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Battery Configs Data")
    battery_configs = gl.get_value("battery_configs")
    response = read_send_receive(connections, logger, parameter=0x11, **kwargs)
    # cmd_frame = builder.build_read_request_frame(
    #     mode="uart",
    #     read_only=True,
    #     reply_hop_count=0,
    #     hop_count=0,
    #     parameter=0x11,
    #     count=2,
    # )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    # response = connection.send_receive(cmd_frame, timeout=1)
    # logger.debug(response)
    # if not response:
    #     response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
    #     logger.debug(response)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "Get_Battery_Data_Failed"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("read_battery_configs", 4)])
    logger.debug(res)
    read_battery_configs = to_hex(res["read_battery_configs"], 4)[2:]
    logger.debug(read_battery_configs)
    verify_status, meg = verify_limit(res["read_battery_configs"], int(battery_configs, 16), "battery_configuration")
    if verify_status:
        return (
            True,
            read_battery_configs,
        )
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, read_battery_configs


def retrieve_ble_stack_version(connections, logger, **kwargs):
    """
    retrieve_ble_stack_version
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("retrieve ble stack version")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xBE,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(0.1)
    cmd_frame = builder.build_read_request_frame(
        mode="uart",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x18,
        value=0x01,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=8, fields=[("ble_stack_version", 8)])
    logger.debug(res)
    charge_ble_stack_version = to_hex_without_head((res["ble_stack_version"]), 8)
    logger.debug(charge_ble_stack_version)
    verify_status, meg = verify_limit(charge_ble_stack_version, equal_value, "ble_stack_version")
    if verify_status:
        return True, str(charge_ble_stack_version)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(charge_ble_stack_version)


def release_button_test(connections, logger, **kwargs):
    """
    release_button_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Release Button Test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xB1,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(0.1)
    response = bba_read_send_receive(connections, logger, pnum=207, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("button_release_status", 1)])
    logger.debug(res)
    verify_status, meg = verify_limit(res["button_release_status"], int(equal_value), "button_release_status")
    if verify_status:
        return True, to_hex_without_head(res.get("button_release_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res.get("button_release_status"), 2)


def press_button_test(connections, logger, **kwargs):
    """
    press_button_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Press Button Test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    ni_device = NIEquipment(device_name="Dev1")
    # time.sleep(0.1)
    ni_device.write_digital("port0/line2", value=True, timeout=1)
    time.sleep(0.8)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xB1,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send(cmd_frame)
    time.sleep(0.01)
    response = bba_read_send_receive(connections, logger, pnum=207, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        time.sleep(1)
        return False, "fail"
    # if not response:
    #     gl.set_value("error_code", kwargs.get("error_code", ""))
    #     return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("button_press_status", 1)])
    logger.debug(res)
    verify_status, meg = verify_limit(res.get("button_press_status"), int(equal_value), "button_press_status")
    if verify_status:
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        time.sleep(0.5)
        return True, to_hex_without_head(res.get("button_press_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        time.sleep(1)
        return False, to_hex_without_head(res.get("button_press_status"), 2)


def hard_reset_test(connections, logger, **kwargs):
    """
    hard_reset_test
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Hard Reset by Button Test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    # time.sleep(4)
    # connection.close()
    # connection.ensure_connected()
    ni_device = NIEquipment(device_name="Dev1")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0xB5,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send_receive(cmd_frame, timeout=1)
    # time.sleep(4)
    # connection.close()
    # connection.ensure_connected()
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=281,
        count=1,
        value0=0xCD,
        value1=0xAB,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    # if not response:
    #     gl.set_value("error_code", kwargs.get("error_code", ""))
    #     return False, "fail"
    ni_device.write_digital("port0/line2", value=True, timeout=1)
    time.sleep(10)
    ni_device.write_digital("port0/line2", value=False, timeout=1)
    time.sleep(3)
    connection.close()
    connection.ensure_connected()
    response = bba_read_send_receive(connections, logger, pnum=281, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("hard_reset_status", 2)])
    logger.debug(res)
    verify_status, meg = verify_limit(res.get("hard_reset_status"), int(equal_value), "hard_reset_status")
    if verify_status:
        return True, to_hex_without_head(res.get("hard_reset_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res.get("hard_reset_status"), 2)


def codentify_code_into_dut(connections, logger, **kwargs):
    """
    write_codentify_into_dut
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Write Codentify into DUT")
    codentify_code = gl.get_value("codentify_code").replace(" ", "")
    codentify_code_ascii = [ord(char) for char in codentify_code]
    logger.debug(codentify_code_ascii)
    connection = connections.get("serial_dut")
    logger.debug("connection is {}".format(connection))
    cmd_frame = builder.build_write_request_frame(
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
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    time.sleep(0.1)
    if not response:
        connection.close()
        connection.ensure_connected()
        time.sleep(0.1)
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    response = read_send_receive(connections, logger, parameter=0x0C, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug("codentify code write wrong")
        return False, "fail"
    return True, codentify_code


def battery_sn_into_dut(connections, logger, **kwargs):
    """
    write battery sn
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Write Battery SN into DUT")
    battery_sn = gl.get_value("battery_data")
    max_count = 11
    battery_sn_0 = battery_sn[: 2 * max_count]
    battery_sn_1 = battery_sn[2 * max_count :]
    battery_sn_0_ascii = [ord(char) for char in battery_sn_0]
    battery_sn_1_ascii = [ord(char) for char in battery_sn_1]
    logger.debug(battery_sn_0_ascii)
    logger.debug(battery_sn_1_ascii)
    connection = connections.get("serial_dut")
    logger.debug("connection is {}".format(connection))
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=300,
        count=11,
        value0=battery_sn_0[0],
        value1=battery_sn_0[1],
        value2=battery_sn_0[2],
        value3=battery_sn_0[3],
        value4=battery_sn_0[4],
        value5=battery_sn_0[5],
        value6=battery_sn_0[6],
        value7=battery_sn_0[7],
        value8=battery_sn_0[8],
        value9=battery_sn_0[9],
        value10=battery_sn_0[10],
        value11=battery_sn_0[11],
        value12=battery_sn_0[12],
        value13=battery_sn_0[13],
        value14=battery_sn_0[14],
        value15=battery_sn_0[15],
        value16=battery_sn_0[16],
        value17=battery_sn_0[17],
        value18=battery_sn_0[18],
        value19=battery_sn_0[19],
        value20=battery_sn_0[20],
        value21=battery_sn_0[21],
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    time.sleep(0.1)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    if len(battery_sn) == 28:
        cmd_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=300 + max_count,
            count=5,
            value0=battery_sn_1_ascii[0],
            value1=battery_sn_1_ascii[1],
            value2=battery_sn_1_ascii[2],
            value3=battery_sn_1_ascii[3],
            value4=battery_sn_1_ascii[4],
            value5=battery_sn_1_ascii[5],
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        time.sleep(0.1)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=332,
        count=1,
        value0=0x600D,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    time.sleep(0.1)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    return True, "pass"


def verify_battery_sn(connections, logger, **kwargs):
    """
    Verify battery sn
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Verify Battery SN")
    battery_sn = gl.get_value("battery_data")
    min_value = kwargs.get("limit").get("min")
    max_value = kwargs.get("limit").get("max")
    max_count = 11
    connection = connections.get("serial_dut")
    logger.debug("connection is {}".format(connection))
    response = bba_read_send_receive(connections, logger, pnum=300, count=11, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("read_battery_sn", 22)])
    logger.debug(res)
    read_battery_sn1 = binascii.unhexlify(hex(res["read_battery_sn"])[2:]).decode("ascii")
    read_battery_sn1 = "".join(reversed(read_battery_sn1))
    logger.debug("read battery sn1 is {}".format(read_battery_sn1))
    if len(battery_sn) == max_value:
        response = bba_read_send_receive(connections, logger, pnum=300 + max_count, count=3, **kwargs)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("read_battery_sn", 10)])
        logger.debug(res)
        read_battery_sn2 = binascii.unhexlify(hex(res["read_battery_sn"])[2:]).decode("ascii")
        read_battery_sn2 = "".join(reversed(read_battery_sn2))
        logger.debug("read battery sn2 is {}".format(read_battery_sn2))
        read_battery_sn = read_battery_sn1 + read_battery_sn2
    else:
        read_battery_sn = read_battery_sn1
    verify_status, msg = verify_limit(read_battery_sn, battery_sn, "read_battery_sn")
    if verify_status:
        return True, read_battery_sn
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, read_battery_sn


def device_serialization(connections, logger, **kwargs):
    """
    device_serialization
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    logger.debug("device serialization")
    stop_event = gl.get_value("stop_event")
    product_code = gl.get_value("layout_config").get("product_code")
    site_code = gl.get_value("layout_config").get("site_code")
    platform_code = gl.get_value("layout_config").get("platform_code")
    hardware_version = gl.get_value("layout_config").get("hardware_version")
    device_number = int(gl.get_value("device_number"), 16)
    platform_code = list(binascii.unhexlify(hex(platform_code)[2:].zfill(4)))
    product_code = list(binascii.unhexlify(hex(product_code)[2:].zfill(4)))
    site_code = list(binascii.unhexlify(hex(site_code)[2:].zfill(4)))
    device_number = list(binascii.unhexlify(hex(device_number)[2:].zfill(8)))
    hardware_version = list(binascii.unhexlify(hex(hardware_version)[2:].zfill(4)))
    logger.debug(
        "hardware version is {} {} {} {} {}".format(
            product_code, platform_code, site_code, device_number, hardware_version
        )
    )
    logger.debug("connection is {}".format(connection))
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                logger.debug("connection established")
                read_status, captured_dusn = read_dusn(connections, logger, **kwargs)
                if "FFFFFFFFFFFFFFFFFFFF" in captured_dusn:
                    cmd_frame = builder.build_write_request_frame(
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
                    logger.debug(f"build cmd: {cmd_frame.hex()}")
                    time.sleep(0.1)
                    response = connection.send_receive(cmd_frame, timeout=1)
                    logger.debug(response)
                    if response:
                        break
                    else:
                        time.sleep(1)
                        continue
                else:
                    break
            else:
                time.sleep(1)
                connection.close()
                continue
        except Exception as e:
            logger.debug(e)
            time.sleep(1)
            continue
    read_status, dusn = read_dusn(connections, logger)
    if read_status:
        return True, dusn
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, dusn


def utc_time_sync(connections, logger, **kwargs):
    """
    utc_time_sync
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Set UTC Time")
    connection = connections.get("serial_dut")
    min_value = kwargs.get("limit").get("min")
    max_value = kwargs.get("limit").get("max")
    # read_only = kwargs.get("read_only", False)
    logger.debug("windows time is {}".format(time.gmtime()))
    uut_epoch_time_str = "2010-01-01 00:00:00"
    time_struct = time.strptime(uut_epoch_time_str, "%Y-%m-%d %H:%M:%S")
    logger.debug("offset time is {}".format(time_struct))
    window_dut_time_offset = time.mktime(time_struct)
    logger.debug("offset of windows and uut epoch time is {}".format(window_dut_time_offset))
    current_time = time.mktime(time.gmtime())
    response = read_send_receive(connections, logger, parameter=0x04, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
    logger.debug(res)
    uut_time = time.ctime(res["dut_time"] + window_dut_time_offset)
    logger.debug("Current UUT UTC Time: {}".format(uut_time))
    time_delta = current_time - (res["dut_time"] + window_dut_time_offset)
    if abs(time_delta) < 300 or "MT7" in gl.get_value("station").upper():
        # if not read_only:
        time_set_value = int(time_delta + res["dut_time"])
        logger.debug("time_set_value: {}".format(time_set_value))
        # write the offset time
        cmd_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x04,
            value=time_set_value + 1,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
        time.sleep(0.1)
        # Read again
        response = read_send_receive(connections, logger, parameter=0x04, **kwargs)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("dut_time", 4)])
        logger.debug(res)
        uut_time = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(res["dut_time"] + window_dut_time_offset),
        )
        logger.debug("Reset New Current DUT UTC Time: {}".format(uut_time))
        time_delta = int(time.mktime(time.gmtime()) - (res["dut_time"] + window_dut_time_offset))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(int(time_delta))
    verify_status, msg = verify_limit(time_delta, (min_value, max_value), "UTC read delta")
    if verify_status:
        return True, str(int(time_delta))
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(int(time_delta))


def write_auth_key(connections, logger, **kwargs):
    """
    write authentication key to UUT
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Write Authentication Key into DUT")
    auth_key0 = charger_authkey0
    auth_key1 = charger_authkey1
    auth_key_map = {209: auth_key0, 217: auth_key1}
    connection = connections.get("serial_dut")
    for item, key in auth_key_map.items():
        cmd_frame = builder.build_write_request_frame(
            mode="uart",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            raw_bytes=True,
            pnum=item,
            count=8,
            value0=bytes(key),
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        time.sleep(0.1)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0xBF,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    time.sleep(0.2)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    return True, "pass"


def read_auth_response(connections, logger, **kwargs):
    """
    read authentication key from UUT
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("read authentication key from UUT")
    if kwargs.get("index") == 0:
        pnum = 225
        auth_key = charger_authkey0_resp
    if kwargs.get("index") == 1:
        auth_key = charger_authkey1_resp
        pnum = 233
    connection = connections.get("serial_dut")
    logger.debug("connection is {}".format(connection))
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value0=0xC0,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send_receive(cmd_frame, timeout=1)
    time.sleep(0.01)
    response = bba_read_send_receive(connections, logger, pnum=pnum, count=8, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("auth_response", 16)])
    read_authkey_response = list(reversed(binascii.unhexlify(hex(res["auth_response"])[2:].zfill(16))))
    if read_authkey_response != auth_key:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, int.from_bytes(read_authkey_response[:2], "little")
    else:
        return True, int.from_bytes(read_authkey_response[:2], "little")


def exit_mt_mode(connections, logger, **kwargs):
    """
    exit_mt_mode
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("set exit_mt_mode")
    if gl.get_value("golden_unit_flag"):
        return True, "skipped"
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=36,
        count=1,
        value0=0x0D,
        value1=0x60,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    # if "MT7" in gl.get_value("layout_config").get("station", ""):
    #     ni_device = NIEquipment(device_name="Dev1")
    #     ni_device.write_digital("port0/line7", value=True, timeout=1)
    time.sleep(6)
    # if "MT7" in gl.get_value("layout_config").get("station", ""):
    #     ni_device.write_digital("port0/line7", value=False, timeout=1)
    #     time.sleep(3)
    # connection.close()
    # connection.ensure_connected()
    read_status, mode_value = check_exit_mt_mode(connections, logger, **kwargs)
    verify_status, msg = verify_limit(mode_value, equal_value, "dut mode")
    if verify_status:
        gl.set_value("exit_mt_mode", True)
        gl.set_value("skip_user_mode_side_switch", True)
        return True, mode_value
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, mode_value


def read_model_number(connections, logger, **kwargs):
    """
    read_mode_number
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("read_model_number")
    equal_value = kwargs.get("limit").get("min")
    # model_number = "M0022"
    model_number = gl.get_value("layout_config").get("ble_model_number")
    gl.set_value("model_number", model_number)
    verify_status, meg = verify_limit(len(model_number), equal_value, "model number length")
    if verify_status:
        return True, model_number
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, model_number


def routing_check(connections, logger, sn, station, **kwargs):
    try:
        address = "http://172.30.11.219/PMICheckRouting/WebService.asmx?wsdl"
        client = Client(address)
        res = client.service.GetRoutingInfo(SN=sn, Station=station)
        if "UnitInfo" in res:
            return True, res
        else:
            return False, res
    except Exception as e:
        return False, f"Error,{e}"


def check_charging_status(connections, logger, **kwargs):
    """
    check_charging_status
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Charging Status")
    if gl.get_value("golden_unit_flag") and not gl.get_value("exit_mt_mode"):
        return True, "skipped"
    if gl.get_value("skip_user_mode_side_switch", False):
        time.sleep(0.7)
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    gl.set_value("error_code", 0)
    response = read_send_receive(connections, logger, parameter=0x85, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("charing_status", 2)])
    logger.debug(res)
    verify_status, meg = verify_limit(
        to_hex_without_head(res["charing_status"], 2)[:2],
        equal_value,
        "charging status",
    )
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        enable_holder_charging(connections, logger, **kwargs)
        time.sleep(1)
        return False, to_hex_without_head(res["charing_status"], 2)[:2]
    else:
        stop_holder_charging(connections, logger, **kwargs)
        gl.set_value("error_code", kwargs.get("error_code", 0))
        return True, to_hex_without_head(res["charing_status"], 2)[:2]


def check_charger_charging_status(connections, logger, **kwargs):
    """
    check_Charger_charging_status
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Charger Charging Status")
    connection = connections.get("serial_dut")
    connection.close()
    connection.ensure_connected()
    response = read_send_receive(connections, logger, parameter=0x85, **kwargs)
    if not response:
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("charger_charing_status", 1)])
    logger.debug(res["charger_charing_status"])
    if to_hex_without_head(res["charger_charing_status"], 1) not in ["01", "41"]:
        logger.debug("Charger not in charging")
        return False
    else:
        logger.debug("Charger in charging")
        return True


def stop_charging(connections, logger, **kwargs):
    """
    stop charging
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Stop Charging")
    connection = connections.get("serial_dut")
    stop_charging_status = kwargs.get("limit").get("min")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x00,
        value1=0x02,
    )
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    time.sleep(0.2)
    response = read_send_receive(connections, logger, parameter=0x85, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("stop_charing_status", 2)])
    logger.debug(res)
    verify_status, meg = verify_limit(
        to_hex(res["stop_charing_status"], 2),
        stop_charging_status,
        "stop_charging status",
    )
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex(res["stop_charing_status"], 2)
    else:
        return True, to_hex(res["stop_charing_status"], 2)


def stop_charger_charging(connections, logger, **kwargs):
    """
    stop charging
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Stop Charging")
    connection = connections.get("serial_dut")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x00,
        value1=0x02,
    )
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    return True


def enable_charger_charging(connections, logger, **kwargs):
    """
    enable charging
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("enable Charging")
    connection = connections.get("serial_dut")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x00,
        value1=0x01,
    )
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    return True


def check_battery_capacity(connections, logger, **kwargs):
    """
    check_battery_capacity
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Battery Capacity")
    connection = connections.get("serial_dut")
    stop_event = gl.get_value("stop_event")
    charge_start_time = time.time()
    reset_time_cnt = time.time()
    if not check_charger_charging_status(connections, logger, **kwargs):
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    battery_data = read_battery_data(connections, logger, **kwargs)
    pre_battery_percent = battery_data["battery_soc"]
    if 30 <= battery_data["battery_soc"] <= 40:
        return True, str(30)
    if 29 <= battery_data["battery_soc"] < 30:
        time.sleep(10)
        return True, str(30)
    if 40 < battery_data["battery_soc"]:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(battery_data["battery_soc"])
    while not stop_event.is_set():
        battery_data = read_battery_data(connections, logger, **kwargs)
        if time.time() - charge_start_time > 3000:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, battery_data["battery_soc"]
        if battery_data["battery_soc"] < 25:
            if int(time.time() - reset_time_cnt) > 180 and battery_data["battery_soc"] == pre_battery_percent:
                reset_dut(connections, logger, **kwargs)
                connection.close()
                connection.ensure_connected()
                reset_time_cnt = time.time()
            time.sleep(30)
            continue
        if 25 <= battery_data["battery_soc"] < 26:
            if int(time.time() - reset_time_cnt) > 180 and battery_data["battery_soc"] == pre_battery_percent:
                reset_dut(connections, logger, **kwargs)
                connection.close()
                connection.ensure_connected()
                reset_time_cnt = time.time()
            time.sleep(10)
            continue
        if 26 <= battery_data["battery_soc"] < 27:
            for i in range(9):
                time.sleep(10)
                battery_data = read_battery_data(connections, logger, **kwargs)
                if battery_data["battery_soc"] >= 30:
                    return True, str(30)
            else:
                return True, str(29)
        if 27 <= battery_data["battery_soc"] < 28:
            for i in range(6):
                time.sleep(10)
                battery_data = read_battery_data(connections, logger, **kwargs)
                if battery_data["battery_soc"] >= 30:
                    return True, str(30)
            else:
                return True, str(29)
        if 28 <= battery_data["battery_soc"] < 29:
            for i in range(6):
                time.sleep(10)
                battery_data = read_battery_data(connections, logger, **kwargs)
                if battery_data["battery_soc"] >= 30:
                    return True, str(30)
            else:
                return True, str(29)
        if 30 <= battery_data["battery_soc"] <= 40:
            return True, str(30)
        if battery_data["battery_soc"] > 40:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, str(battery_data["battery_soc"])


def check_battery_capacity_validation(connections, logger, **kwargs):
    """
    check_battery_capacity
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Battery Capacity")
    stop_event = gl.get_value("stop_event")
    charge_start_time = time.time()
    # charging_status_check_cnt = time.time()
    enable_time_cnt = True
    if not check_charger_charging_status(connections, logger, **kwargs):
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    stop_charger_charging(connections, logger, **kwargs)
    time.sleep(5)
    battery_data = read_battery_data(connections, logger, **kwargs)
    pre_battery_percent = battery_data["battery_soc"]
    pre_battery_voltage = battery_data["battery_voltage"]
    while not stop_event.is_set():
        battery_data = read_battery_data(connections, logger, **kwargs)
        enable_charger_charging(connections, logger, **kwargs)
        time.sleep(5)
        if time.time() - charge_start_time > 3000:
            # gl.set_value("error_code", kwargs.get("error_code", ""))
            gl.set_value("error_code", "0016")
            return False, str(battery_data["battery_soc"])
        elif 34 < battery_data["battery_soc"]:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, str(battery_data["battery_soc"])
        elif 30 <= battery_data["battery_soc"] <= 34:
            if "OQA" in gl.get_value("station").upper():
                return True, str(30)
            if battery_data["battery_soc"] == pre_battery_percent:
                if battery_data["battery_voltage"] >= 3610:
                    return True, str(30)
                else:
                    time.sleep(10)
                    stop_charger_charging(connections, logger, **kwargs)
                    time.sleep(5)
                    continue
            else:
                return True, str(30)
        elif battery_data["battery_soc"] < 28:
            if enable_time_cnt:
                charging_time_cnt = time.time()
                enable_time_cnt = False
            if charging_time_cnt - time.time() > 600 and battery_data["battery_soc"] == pre_battery_percent:
                if battery_data["battery_voltage"] >= 3610 and battery_data["battery_voltage"] > pre_battery_voltage:
                    return True, str(30)
            time.sleep(55)
            stop_charger_charging(connections, logger, **kwargs)
            time.sleep(5)
            continue
        elif 28 <= battery_data["battery_soc"] < 30:
            if "OQA" in gl.get_value("station").upper():
                return True, str(30)
            if battery_data["battery_soc"] == pre_battery_percent:
                if battery_data["battery_voltage"] >= 3610:
                    time.sleep(120)
                    return True, str(30)
                else:
                    time.sleep(30)
                    stop_charger_charging(connections, logger, **kwargs)
                    time.sleep(5)
                    continue
            else:
                time.sleep(60)
                return True, str(30)


# def check_battery_capacity_validation(connections, logger, **kwargs):
#     """
#     check_battery_capacity
#     :param connections:
#     :param logger:
#     :param kwargs:
#     :return:
#     """
#     logger.debug("Check Battery Capacity")
#     stop_event = gl.get_value("stop_event")
#     charge_start_time = time.time()
#     # charging_status_check_cnt = time.time()
#     enable_time_cnt = True
#     if not check_charger_charging_status(connections, logger, **kwargs):
#         gl.set_value("error_code", kwargs.get("error_code", ""))
#         return False, "fail"
#     stop_charger_charging(connections, logger, **kwargs)
#     time.sleep(5)
#     battery_data = read_battery_data(connections, logger, **kwargs)
#     pre_battery_percent = battery_data["battery_soc"]
#     pre_battery_voltage = battery_data["battery_voltage"]
#     while not stop_event.is_set():
#         battery_data = read_battery_data(connections, logger, **kwargs)
#         enable_charger_charging(connections, logger, **kwargs)
#         time.sleep(5)
#         # if time.time() - charging_status_check_cnt > 60:
#         #     charging_status_check_cnt = time.time()
#         #     if not check_charger_charging_status(connections, logger, **kwargs):
#         #         gl.set_value("error_code", kwargs.get("error_code", ""))
#         #         return False, str(battery_data["battery_soc"])
#         #     stop_charger_charging(connections, logger, **kwargs)
#         #     time.sleep(5)
#         #     continue
#         if time.time() - charge_start_time > 30000:
#             # gl.set_value("error_code", kwargs.get("error_code", ""))
#             gl.set_value("error_code", "0016")
#             return False, str(battery_data["battery_soc"])
#         # elif 34 < battery_data["battery_soc"]:
#         #     gl.set_value("error_code", kwargs.get("error_code", ""))
#         #     return False, str(battery_data["battery_soc"])
#         # elif 30 <= battery_data["battery_soc"] <= 34:
#         #     if "OQA" in gl.get_value("station").upper():
#         #         return True, str(30)
#         #     if battery_data["battery_soc"] == pre_battery_percent:
#         #         if battery_data["battery_voltage"] >= 3610:
#         #             return True, str(30)
#         #         else:
#         #             time.sleep(10)
#         #             stop_charger_charging(connections, logger, **kwargs)
#         #             time.sleep(5)
#         #             continue
#         #     else:
#         #         return True, str(30)
#         elif battery_data["battery_soc"] < 101:
#             if enable_time_cnt:
#                 charging_time_cnt = time.time()
#                 enable_time_cnt = False
#             if charging_time_cnt - time.time() > 600 and battery_data["battery_soc"] == pre_battery_percent:
#                 if battery_data["battery_voltage"] >= 3610 and battery_data["battery_voltage"] > pre_battery_voltage:
#                     return True, str(30)
#             time.sleep(5)
#             stop_charger_charging(connections, logger, **kwargs)
#             time.sleep(5)
#             continue
#         # elif 28 <= battery_data["battery_soc"] < 30:
#         #     if "OQA" in gl.get_value("station").upper():
#         #         return True, str(30)
#         #     if battery_data["battery_soc"] == pre_battery_percent:
#         #         if battery_data["battery_voltage"] >= 3610:
#         #             time.sleep(120)
#         #             return True, str(30)
#         #         else:
#         #             time.sleep(30)
#         #             stop_charger_charging(connections, logger, **kwargs)
#         #             time.sleep(5)
#         #             continue
#         #     else:
#         #         time.sleep(60)
#         #         return True, str(30)


def check_battery_capacity_new(connections, logger, **kwargs):
    """
    check_battery_capacity
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Battery Capacity")
    connection = connections.get("serial_dut")
    stop_event = gl.get_value("stop_event")
    charge_start_time = time.time()
    reset_time_cnt = time.time()
    charging_status_check_cnt = time.time()
    if not check_charger_charging_status(connections, logger, **kwargs):
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    battery_data = read_battery_data(connections, logger, **kwargs)
    pre_battery_percent = battery_data["battery_soc"]
    if 30 <= battery_data["battery_soc"] <= 32:
        # if 30 <= battery_data["battery_soc"] <= 40:
        return True, str(30)
    if 32 < battery_data["battery_soc"]:
        # if 40 < battery_data["battery_soc"]:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(battery_data["battery_soc"])
    while not stop_event.is_set():
        if time.time() - charging_status_check_cnt > 60:
            charging_status_check_cnt = time.time()
            if not check_charger_charging_status(connections, logger, **kwargs):
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
        battery_data = read_battery_data(connections, logger, **kwargs)
        if time.time() - charge_start_time > 3000:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, battery_data["battery_soc"]
        if battery_data["battery_soc"] < 24:
            if int(time.time() - reset_time_cnt) > 180 and battery_data["battery_soc"] == pre_battery_percent:
                reset_dut(connections, logger, **kwargs)
                connection.close()
                connection.ensure_connected()
                reset_time_cnt = time.time()
            time.sleep(30)
            continue
        if 24 <= battery_data["battery_soc"] <= 26:
            pre_battery_percent = battery_data["battery_soc"]
            time.sleep(180)
            reset_dut(connections, logger, **kwargs)
            connection.close()
            connection.ensure_connected()
            battery_data = read_battery_data(connections, logger, **kwargs)
            if 26 < battery_data["battery_soc"] < 29:
                continue
            if pre_battery_percent == battery_data["battery_soc"]:
                time.sleep(240)
                return True, str(30)
        if 26 < battery_data["battery_soc"] <= 28:
            time.sleep(180)
            return True, str(30)
        if 28 < battery_data["battery_soc"] <= 29:
            time.sleep(120)
            return True, str(30)
        if 29 < battery_data["battery_soc"] <= 30:
            time.sleep(60)
            return True, str(30)
        if 30 < battery_data["battery_soc"] <= 32:
            # if 30 < battery_data["battery_soc"] <= 40:
            return True, str(30)
        if battery_data["battery_soc"] > 32:
            # if battery_data["battery_soc"] > 40:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, str(battery_data["battery_soc"])


def final_check_battery_capacity(connections, logger, **kwargs):
    """
    final_check_battery_capacity
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Final Check Battery Capacity")
    battery_data = read_battery_data(connections, logger, **kwargs)
    if 28 <= battery_data["battery_soc"] <= 34:
        # if 24 <= battery_data["battery_soc"] <= 40:
        return True, str(30)
    # if 30 <= battery_data["battery_soc"] <= 31:
    #     return True, 30
    # if 26 <= battery_data["battery_soc"] < 29:
    #     return True, str(29)
    if battery_data["battery_soc"] > 34:
        # if battery_data["battery_soc"] > 40:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(battery_data["battery_soc"])


def read_battery_data(connections, logger, **kwargs):
    """
    read_battery_data
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read_battery_data")
    connection = connections.get("serial_dut")
    step_start_time = time.time()
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            response = read_send_receive(connections, logger, parameter=0x284, **kwargs)
            res = builder.unpack_payload_fields(
                payload=response,
                offset=6,
                fields=[
                    ("battery_voltage", 2),
                    ("battery_current", 2),
                    ("battery_soc", 1),
                    ("battery_temp", 1),
                    ("mcu_temp", 1),
                ],
            )
            break
        except Exception as e:
            logger.debug(e)
            connection.close()
            time.sleep(1)
            connection.ensure_connected()
            if time.time() - step_start_time > 60:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                break
            continue
    return res


def check_codentify_code(connections, logger, **kwargs):
    """
    check_codentify_code
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Codentify Code")
    if "MT7" in gl.get_value("station").upper():
        codentify_code = gl.get_value("codentify_code").replace(" ", "")
    response = read_send_receive(connections, logger, parameter=0x0C, **kwargs)
    crc = verify_crc(logger=logger, data=response, connection="hid")
    logger.info(f"CRC value is {crc}")
    if not response or not crc:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    # if not response:
    #     gl.set_value("error_code", kwargs.get("error_code", ""))
    #     return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("read_codentify_code", 14)])
    logger.debug(res)
    read_codentify_code = binascii.unhexlify(hex(res["read_codentify_code"])[2:]).decode("ascii")
    read_codentify_code = "".join(reversed(read_codentify_code.upper()))
    logger.debug("read codentify code is {}".format(read_codentify_code))
    if "MT11C" in gl.get_value("station").upper():
        codentify_code = (
            read_codentify_code[:4]
            + " "
            + read_codentify_code[4:7]
            + " "
            + read_codentify_code[7:10]
            + " "
            + read_codentify_code[10:14]
        )
        gl.set_value("codentify_code", codentify_code)
        return True, read_codentify_code
    verify_status, msg = verify_limit(read_codentify_code, codentify_code, "read_codentify_code")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug("codentify code write wrong")
        return False, read_codentify_code
    return True, read_codentify_code


def check_device_system_error(connections, logger, **kwargs):
    """
    check_device_system_error
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Device System Error")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = read_send_receive(connections, logger, parameter=0x82, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("system_error_code", 1)])
    logger.debug(res)
    verify_status, msg = verify_limit(res["system_error_code"], int(equal_value), "system_error_code")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex(res["system_error_code"], 4)
    else:
        return True, to_hex_without_head(res["system_error_code"], 4)


def read_battery_percentage(connections, logger, **kwargs):
    """
    read_battery_percentage
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Battery Percentage")
    if gl.get_value("golden_unit_flag") and not gl.get_value("exit_mt_mode"):
        return True, "skipped"
    ready_only = kwargs.get("read_only", False)
    battery_data = read_battery_data(connections, logger, **kwargs)
    battery_percent = battery_data["battery_soc"]
    if battery_data["battery_soc"] == 255:  ## defaut value FF since battery soc very low
        battery_percent = 0
    if ready_only:
        return True, str(battery_percent)
    else:
        min_value = kwargs.get("limit").get("min")
        max_value = kwargs.get("limit").get("max")
    if "MT11C" in gl.get_value("station").upper():
        if 30 < battery_percent <= 34:
            battery_percent = 30
        if battery_percent > 34:
            reset_dut(connections, logger, **kwargs)
            battery_data = read_battery_data(connections, logger, **kwargs)
            battery_percent = battery_data["battery_soc"]
            if battery_percent > 34:
                ask_question("Battery SOC exceed 30, please contact TE/电池SOC超出30，请联系TE")
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, str(battery_percent)
    virify_status, msg = verify_limit(battery_percent, (min_value, max_value))
    if not virify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        logger.debug(msg)
        return False, str(battery_percent)
    else:
        return True, str(battery_percent)
    return True, str(battery_percent)


def read_battery_conversion_factor(connections, logger, **kwargs):
    """
    read_battery_voltage_factor
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Battery Conversion Factor")
    connection = connections.get("serial_dut")
    response = read_send_receive(connections, logger, parameter=0x80, **kwargs)
    if not response:
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("battery_factor", 2)])
    logger.debug(res)
    gl.set_value("battery_factor", res["battery_factor"])
    if res["battery_factor"] < 500:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, res["battery_factor"]
    else:
        logger.debug("Read Battery Factor OK")
        return True, res["battery_factor"]


def read_battery_level(connections, logger, read_only=False, **kwargs):
    """
    read_battery_level
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Battery Level")
    if gl.get_value("golden_unit_flag") and not gl.get_value("exit_mt_mode"):
        return True, "skipped"
    # if gl.get_value("exit_mt_mode"):
    #     time.sleep(3)
    if not read_only:
        min_value = kwargs.get("limit").get("min")
        max_value = kwargs.get("limit").get("max")
    battery_data = read_battery_data(connections, logger, **kwargs)
    battery_level = round((battery_data["battery_voltage"] / 1000), 2)
    if battery_data["battery_voltage"] == 65535:  ## defaut value FFFF since battery level very low
        battery_level = 0
    if read_only:
        return True, str(battery_level)
    else:
        if battery_level < 2.5:
            for i in range(1, 7):
                time.sleep(0.9)
                logger.debug("sleep time is {}".format(i))
                battery_data = read_battery_data(connections, logger, **kwargs)
                battery_level = round((battery_data["battery_voltage"] / 1000), 2)
                if battery_level > 2.5:
                    break
        verify_status, msg = verify_limit(battery_level, (min_value, max_value))
        if not verify_status:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            logger.debug(msg)
            return False, str(battery_level)
        else:
            return True, str(battery_level)


def battery_level_calculation(connections, logger, **kwargs):
    """
    Battery level calculation
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    read_battery_factor_status, battery_factor = read_battery_conversion_factor(connections, logger, **kwargs)
    if not read_battery_factor_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    time.sleep(0.1)
    read_battery_infor_status, read_result = read_battery_percentage(connections, logger, **kwargs)
    if not read_battery_infor_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    logger.debug("Battery ADC is {}".format(gl.get_value("battery_adc")))
    logger.debug("Battery Factor is {}".format(gl.get_value("battery_factor")))
    battery_level = round(
        (((gl.get_value("battery_factor") + 1) * gl.get_value("battery_adc")) / 65536),
        4,
    )
    logger.debug("read battery voltage is {}".format(battery_level))
    return battery_level


def set_device_ship_mode(connections, logger, **kwargs):
    """
    set_device_ship_mode
    :param cconnections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Set Device Ship Mode")
    if gl.get_value("golden_unit_flag") and not gl.get_value("exit_mt_mode"):
        return True, "skipped"
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    for i in range(3):
        cmd_frame = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x05,
            value0=0x02,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ship_mode_status", 2)])
        logger.debug(res)
        ship_mode_status = to_hex_without_head(res["ship_mode_status"], 2)
        ship_mode_status = ship_mode_status[2:] + ship_mode_status[:2]
        verify_status, msg = verify_limit(ship_mode_status, equal_value, "ship mode")
        if verify_status:
            break
        else:
            if kwargs.get("read_only"):
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, ship_mode_status
            cmd_frame = builder.build_write_request_frame(
                mode="uart",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x05,
                value0=0x01,
                value1=0x02,
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            connection.send(cmd_frame)
            time.sleep(0.1)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, ship_mode_status
    if kwargs.get("read_only"):
        time.sleep(2)
    return True, ship_mode_status


def control_unlock_device(connections, logger, **kwargs):
    """
    control_unlock_device
    :param cconnections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Device Unlock Status")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    for i in range(3):
        cmd_frame = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x05,
            value0=0x00,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if not response:
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if not response:
                gl.set_value("error_code", kwargs.get("error_code", ""))
                return False, "fail"
        res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("lock_status", 2)])
        logger.debug(res)
        verify_status, msg = verify_limit(to_hex_without_head(res["lock_status"], 2), equal_value, "lock_status")
        if verify_status:
            break
        else:
            cmd_frame = builder.build_write_request_frame(
                mode="uart",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x05,
                value0=0x00,
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            connection.send(cmd_frame)
            time.sleep(0.1)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res["lock_status"], 2)
    return True, to_hex_without_head(res["lock_status"], 2)


def read_error_log(connections, logger, **kwargs):
    """
    read error log
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Error Log")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = read_send_receive(connections, logger, parameter=0x09, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=11, fields=[("error_log", 1)])
    logger.debug(res)
    verify_status, msg = verify_limit(to_hex_without_head(res["error_log"], 2), equal_value, "error_log")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res["error_log"], 2)
    else:
        return True, to_hex_without_head(res["error_log"], 2)


def self_test_result(connections, logger, **kwargs):
    """
    self test result
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Read Self Test Result")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = read_send_receive(connections, logger, parameter=0x07, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("self_test_result", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(to_hex_without_head(res["self_test_result"], 2), equal_value, "self_test_result")
    if not verify_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    else:
        return True, to_hex_without_head(res["self_test_result"], 2)


def reset_dut(connections, logger, **kwargs):
    """
    reset dut result
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Reset DUT")
    connection = connections.get("serial_dut")
    stop_event = gl.get_value("stop_event")
    reset_start_time = time.time()
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x02,
        count=1,
        value0=0x00,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    if not response:
        response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
        logger.debug(response)
        if not response:
            gl.set_value("error_code", kwargs.get("error_code", ""))
            return False, "fail"
    time.sleep(4)
    loop_start_time = time.time()
    while not stop_event.is_set():
        connection.close()
        if connection.ensure_connected():
            read_status, dusn = read_dusn(connections, logger)
            if read_status:
                if not gl.get_value("golden_unit_flag") and "MT7" in gl.get_value("layout_config").get("station", ""):
                    stop_holder_charging(connections, logger, **kwargs)
                break
            else:
                if time.time() - loop_start_time > 15:
                    read_status = False
                    break
                time.sleep(0.2)
                # if "MT7" in gl.get_value("layout_config").get("station", ""):
                #     switch_usb_b_on(connections, logger, delay_time=3, **kwargs)
                continue
        else:
            if time.time() - loop_start_time > 15:
                read_status = False
                break
            # if "MT7" in gl.get_value("layout_config").get("station", ""):
            #     switch_usb_b_on(connections, logger, delay_time=3, **kwargs)
            time.sleep(0.1)
            continue
    if not read_status:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, dusn
    else:
        if "MT7" in gl.get_value("layout_config").get("station", ""):
            time.sleep(12 - int(time.time() - reset_start_time))
        else:
            time.sleep(10 - int(time.time() - reset_start_time))
        read_battery_data(connections, logger, **kwargs)
        enable_holder_charging(connections, logger, **kwargs)
        return True, dusn


def check_exit_mt_mode(connections, logger, **kwargs):
    """
    check exit mt mode status
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Check Exit MT MODEL Status")
    if gl.get_value("golden_unit_flag") and not gl.get_value("exit_mt_mode"):
        return True, "skipped"
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = bba_read_send_receive(connections, logger, pnum=36, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("mt_mode", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(to_hex_without_head(res["mt_mode"], 2), equal_value, "dut_mode")
    if verify_status:
        return True, to_hex_without_head(res["mt_mode"], 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res["mt_mode"], 2)


def eeprom_blank_check(connections, logger, **kwargs):
    """
    eeprom blank check
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("eeprom black check")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    stop_event = gl.get_value("stop_event")
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_write_request_frame(
                    mode="uart",
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x08,
                    pnum=14,
                    count=1,
                    value0=0xB0,
                )
                logger.debug(f"build cmd: {cmd_frame.hex()}")
                connection.send_receive(cmd_frame, timeout=1)
                time.sleep(0.4)
                response = bba_read_send_receive(connections, logger, pnum=15, count=1, **kwargs)
                res = builder.unpack_payload_fields(payload=response, offset=7, fields=[("eeprom_content", 2)])
                logger.debug(res)
                verify_status, msg = verify_limit(res["eeprom_content"], equal_value, "eeprom content check")
                if verify_status:
                    break
                else:
                    logger.debug("eeprom not blank, erase it ")
                    cmd_frame = builder.build_write_request_frame(
                        mode="uart",
                        reply_hop_count=0,
                        hop_count=0,
                        parameter=0x08,
                        pnum=17,
                        count=1,
                        value0=0x01,
                    )
                    logger.debug(f"build cmd: {cmd_frame.hex()}")
                    connection.send_receive(cmd_frame, timeout=1)
                    time.sleep(4)
                    continue
            else:
                connection.close()
                continue
        except Exception as e:
            logger.debug(e)
            continue
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, str(to_hex(res["eeprom_content"], 2))
    return True, str(to_hex(res["eeprom_content"], 2))


def overall_test_result(connections, logger, **kwargs):
    """
    logging overal test result
    :param connections:
    :param logger:
    :param kwargs:
    :return:.
    """
    logger.debug("logging overal test result")
    # equal_value = kwargs.get("limit").get("min")
    # # cell_id = kwargs.get("cell_name", "")
    # overal_test_error = gl.get_value("error_code", "0000")
    if "MT7" in gl.get_value("layout_config").get("station", ""):
        ni_device = NIEquipment(device_name="Dev1")
        # time.sleep(0.1)
        ni_device.write_digital("port0/line0", value=False, timeout=1)
        # time.sleep(0.1)
        ni_device.write_digital("port0/line3", value=False, timeout=1)
        # time.sleep(0.1)
        ni_device.write_digital("port0/line2", value=False, timeout=1)
        ni_device.write_digital("port0/line1", value=False, timeout=1)
        move_confentify_sn(logger, **kwargs)
    if gl.get_value("error_code") == 0:
        gl.set_value("error_code", 0)
    if gl.get_value("error_code") == "":
        gl.set_value("error_code", 0)
    all_step_results = kwargs.get("all_step_results")
    if not all_step_results:
        stop_charger_charging(connections, logger, **kwargs)
        return False, "NO_STEP_RESULTS"
    else:
        for result in all_step_results:
            if result.get("status") not in ["PASS", "SKIPPED"]:
                error_code = gl.get_value("error_code")
                if "MT11C" in gl.get_value("station").upper():
                    with LockManager(lock_name="ni_device", timeout=7200):
                        ni_device = NIEquipment(device_name="Dev1")
                        # time.sleep(0.1)
                        ni_device.write_digital(
                            charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))],
                            value=False,
                            timeout=1,
                        )
                        # time.sleep(0.1)
                        ni_device.write_digital(
                            charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))],
                            value=True,
                            timeout=1,
                        )
                stop_charger_charging(connections, logger, **kwargs)
                return False, error_code
        if "MT11C" in gl.get_value("station").upper():
            with LockManager(lock_name="ni_device", timeout=7200):
                ni_device = NIEquipment(device_name="Dev1")
                # time.sleep(0.1)
                ni_device.write_digital(
                    charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))],
                    value=True,
                    timeout=1,
                )
                # time.sleep(0.1)
                ni_device.write_digital(
                    charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))],
                    value=False,
                    timeout=1,
                )
        stop_charger_charging(connections, logger, **kwargs)
        return True, kwargs.get("limit").get("min")
    # verify_status, msg = verify_limit(
    #     overal_test_error, equal_value, "overal test result"
    # )
    # if not verify_status:
    #     if "MT11C" in gl.get_value("station").upper():
    #         with LockManager(lock_name="ni_device", timeout=7200):
    #             ni_device = NIEquipment(device_name="Dev1")
    #             time.sleep(0.1)
    #             ni_device.write_digital(charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))], value=False,
    #                                     timeout=1)
    #             time.sleep(0.1)
    #             ni_device.write_digital(charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))], value=True,
    #                                     timeout=1)
    #     # save_dusn(cell_id=cell_id)
    #     return False, overal_test_error
    # else:
    #     if "MT11C" in gl.get_value("station").upper():
    #         with LockManager(lock_name="ni_device", timeout=7200):
    #             ni_device = NIEquipment(device_name="Dev1")
    #             time.sleep(0.1)
    #             ni_device.write_digital(charger_m11c_io_mapping["{}_pass".format(kwargs.get("cell_name"))], value=True,
    #                                     timeout=1)
    #             time.sleep(0.1)
    #             ni_device.write_digital(charger_m11c_io_mapping["{}_fail".format(kwargs.get("cell_name"))], value=False,
    #                                     timeout=1)
    #     # save_dusn(cell_id=cell_id)
    #     return True, overal_test_error


def save_dusn(cell_id=""):
    """
    save dusn into local file
    :param dusn:
    :return:
    """
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    dusn_save_path = "{}:\save_dusn".format(root_path)
    with LockManager(lock_name="dusn_list_file", timeout=7200):
        if not os.path.exists(dusn_save_path):
            os.makedirs(dusn_save_path)
            with open(r"{}\dusn_list.txt".format(dusn_save_path), "w+") as f:
                f.write("Tested SN list\r")
            f.close()
        with open(r"{}\dusn_list.txt".format(dusn_save_path), "a") as f:
            f.writelines("{}_{}\r".format(cell_id, gl.get_value("dusn")))
        f.close()
    return True


def read_save_dusn(cell_id=""):
    """
    read save dusn
    :param dusn:
    :return:
    """
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    dusn_save_path = "{}:\save_dusn".format(root_path)
    with LockManager(lock_name="dusn_list_file", timeout=7200):
        if os.path.exists(r"{}".format(dusn_save_path)):
            if os.path.exists(r"{}\dusn_list.txt".format(dusn_save_path)):
                with open(r"{}\dusn_list.txt".format(dusn_save_path), "r") as f:
                    read_content = f.readlines()
                f.close()
                for line in read_content:
                    if "{}_{}".format(cell_id, gl.get_value("dusn")) in line.strip():
                        return False
                else:
                    return True
            else:
                with open(r"{}\dusn_list.txt".format(dusn_save_path), "w+") as f:
                    f.write("Tested SN list\r")
                f.close()
                return True
        else:
            os.makedirs(r"{}".format(dusn_save_path), exist_ok=True)
            with open(r"{}\dusn_list.txt".format(dusn_save_path), "w+") as f:
                f.write("Tested SN list\r")
            f.close()
            return True


def save_temp_rwk_data(cell_id=""):
    """
    save temp rwk_data into local file
    :return:
    """
    read_time = time.strftime("%Y-%m-%d_%H%M%S", time.localtime())
    if os.path.exists(r"D:\\"):
        root_path = "D"
    else:
        root_path = "C"
    rwk_data_save_path = "{}:\save_temp_rwk_data".format(root_path)
    with LockManager(lock_name="temp_rwk_data", timeout=7200):
        if not os.path.exists(rwk_data_save_path):
            os.makedirs(rwk_data_save_path)
            with open(
                r"{}\{}_{}.txt".format(rwk_data_save_path, gl.get_value("codenticode"), read_time),
                "w+",
            ) as f:
                f.write("rwk_data: \r")
                f.write("{}\r".format(gl.get_value("rwk_data")))
                f.write("rwk_crc: \r")
                f.write("{}\r".format(gl.get_value("rwk_crc")))
            f.close()
        else:
            with open(
                r"{}\{}_().txt".format(rwk_data_save_path, gl.get_value("codenticode"), read_time),
                "w+",
            ) as f:
                f.write("rwk_data: \r")
                f.write("{}\r".format(gl.get_value("rwk_data")))
                f.write("rwk_crc: \r")
                f.write("{}\r".format(gl.get_value("rwk_crc")))
            f.close()
    return True


# def check_golden_unit(logger, **kwargs):
#     """
#     confirm the test unit if golden unit
#     :return:
#     """
#     if os.path.exists(r"D:\\"):
#         root_path = "D"
#     else:
#         root_path = "C"
#     golden_unit_save_path = "{}:\golden_unit".format(root_path)
#     with LockManager(lock_name="golden_list_file", timeout=7200):
#         if not os.path.exists(r"{}".format(golden_unit_save_path)):
#             os.makedirs(golden_unit_save_path)
#             return True
#         else:
#             if not os.path.exists(r"{}\golden_list.txt".format(golden_unit_save_path)):
#                 return True
#             else:
#                 with open(r"{}\golden_list.txt".format(golden_unit_save_path), "r") as f:
#                     read_content = f.readlines()
#                     logger.debug("golden list: {}".format(read_content))
#                 f.close()
#                 if gl.get_value("codentify_code") in read_content:
#                     gl.set_value("golden_unit_flag", True)
#                 return True


def check_golden_unit(logger, **kwargs):
    """
    confirm the test unit if golden unit
    :return:
    """
    golden_list = []
    golden_unit_save_path = "{}".format(gl.get_value("golden_sn_path"))
    with LockManager(lock_name="golden_list_file", timeout=7200):
        if not os.path.exists(r"{}".format(golden_unit_save_path)):
            os.makedirs(golden_unit_save_path)
            return True
        else:
            with open(golden_unit_save_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) > 0:
                        golden_list.append(row[0])
            if gl.get_value("codentify_code") in golden_list:
                gl.set_value("golden_unit_flag", True)
                logger.debug("golden flag is true")
            return True


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
    cavity_save_path = "{}:\Cavity".format(root_path)
    with LockManager(lock_name="create_cavity_file", timeout=7200):
        if os.path.exists(r"{}".format(cavity_save_path)):
            with open(r"{}\{}.txt".format(cavity_save_path, cavity_id), "w+") as f:
                f.write("cavity {} start test\r".format(cavity_id))
            f.close()
        else:
            os.makedirs(r"{}".format(cavity_save_path), exist_ok=True)
            with open(r"{}\{}.txt".format(cavity_save_path, cavity_id), "w+") as f:
                f.write("cavity {} start test\r".format(cavity_id))
            f.close()
    return True


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
    cavity_save_path = "{}:\Cavity".format(root_path)
    if os.path.exists(r"{}\{}.txt".format(cavity_save_path, cavity_id)):
        os.remove(r"{}\{}.txt".format(cavity_save_path, cavity_id))
    return True


def save_confentify_sn(confentify_sn=""):
    """
    save_confentify_sn file
    :param confentify_sn:
    :return:
    """
    path = "{}\SN".format(gl.get_value("sn_path"))
    with LockManager(lock_name="save_sn_file", timeout=7200):
        if os.path.exists(r"{}".format(path)):
            with open(r"{}\{}.txt".format(path, confentify_sn), "w+") as f:
                f.close()
        else:
            os.makedirs(r"{}".format(path), exist_ok=True)
            with open(r"{}\{}.txt".format(path, confentify_sn), "w+") as f:
                f.close()
    return True


def move_confentify_sn(logger, **kwargs):
    """
    move_confentify_sn file
    :param cavity_id:
    :return:
    """
    # confentify_sn = gl.get_value("codentify_code")
    # logger.debug(confentify_sn)
    current_time = time.localtime()
    source_path = "{}\SNResult".format(gl.get_value("sn_path"))
    destination_path = "{}\SNCopy".format(gl.get_value("sn_path"))
    if not os.path.exists(r"{}".format(destination_path)):
        os.makedirs(r"{}".format(destination_path), exist_ok=True)
    if len(os.listdir(source_path)) > 0:
        for i in os.listdir(source_path):
            # if confentify_sn in i:
            file_source_path = "{}\{}".format(source_path, i)
            try:
                shutil.move(
                    file_source_path,
                    "{}\{}_{}".format(destination_path, time.strftime("%Y%m%d%H%M%S", current_time), i),
                )
                logger.debug("file was moved")
            except Exception as error:
                logger.debug(f"file moved with error: {error}")
            continue
    return True


def get_batterysn_configuration_code(connections, logger, **kwargs):
    """
    get battery sn and confifuration code
    :param confentify_sn:
    :return:
    """
    confentify_sn = gl.get_value("codentify_code")
    logger.debug(confentify_sn)
    source_path = "{}\SNResult".format(str(gl.get_value("sn_path")))
    start_time = time.time()
    time.sleep(0.001)
    while time.time() - start_time <= 20.0:
        for i in os.listdir(source_path):
            logger.debug(i)
            if confentify_sn in i:
                infor = i[:-4].split("_")
                battery_sn = infor[1]
                configuration_code = infor[2]
                ff_dusn = infor[3]
                if infor[-1] == "PASS":
                    result = True
                else:
                    result = False
                break
        else:
            time.sleep(0.2)
            continue
        break
    return result, battery_sn, configuration_code, ff_dusn


def stop_holder_charging(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Stop Holder Charging")
    connection = connections.get("serial_dut")
    connection.close()
    connection.ensure_connected()
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x01,
        value1=0x02,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    return True


def enable_holder_charging(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("Enable Holder Charging")
    connection = connections.get("serial_dut")
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x85,
        value0=0x01,
        value1=0x01,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    # time.sleep(1)
    return True


def validation_step(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    connection.close()
    connection.ensure_connected()
    # stop_charger_charging(connections, logger, **kwargs)
    for i in range(10000):
        reset_dut(connections, logger, **kwargs)
        time.sleep(1)
        logger.debug("test loops {} completed".format(i))
        continue
    return False, "validation"


def read_send_receive(connections, logger, parameter=0x00, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    for i in range(3):
        cmd_frame = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=parameter,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if response:
            break
        else:
            connection.close()
            connection.ensure_connected()
            time.sleep(0.1)
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if response:
                break
        continue
    return response


def bba_read_send_receive(connections, logger, parameter=0x08, pnum=0, count=1, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    connection = connections.get("serial_dut")
    for i in range(3):
        cmd_frame = builder.build_read_request_frame(
            mode="uart",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=parameter,
            pnum=pnum,
            count=count,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if response:
            break
        else:
            connection.close()
            connection.ensure_connected()
            time.sleep(0.1)
            response = connection.send_receive(cmd_frame, timeout=1, idle_factor=3)
            logger.debug(response)
            if response:
                break
        continue
    return response


def manual_display_check(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("start mannual display check")
    check_infor = ask_question(
        "开机后请检查产品开机后的UI界面是否和图片一致， 一致输入 Y, 不一致输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "UI.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "UI checking with error"
    check_infor = ask_question(
        "手指触摸亮度按钮，如图片所示， 检查亮度按钮是否可以激活， 可以激活输入 Y, 可以激活输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "Brightness.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "brightness icon with error"
    check_infor = ask_question(
        "手指触摸震动按钮，如图片所示， 检查震动按钮是否可以激活， 可以激活输入 Y, 可以激活输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "vibrator.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "vibrator icon with error"
    check_infor = ask_question(
        "手指触摸告警提示按钮，如图片所示， 检查告警提示是否可以激活， 可以激活输入 Y, 可以激活输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "warning.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "waring icon checking with error"
    check_infor = ask_question(
        "手指触摸触摸校准按钮，如图片所示， 检查触摸校准是否可以激活， 可以激活输入 Y, 可以激活输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "UI.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "Touchscreens icon checking with error"
    return False, "validation"


def power_on_self_test(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("power on self test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    # cmd_frame = builder.build_write_request_frame(
    #     mode="uart",
    #     reply_hop_count=0,
    #     hop_count=0,
    #     parameter=0x08,
    #     pnum=281,
    #     count=1,
    #     value=0x02,
    # )
    # logger.debug(f"build cmd: {cmd_frame.hex()}")
    # connection.send(cmd_frame)
    # time.sleep(0.01)
    cmd_frame = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0x1FFF,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    connection.send(cmd_frame)
    time.sleep(0.1)
    response = bba_read_send_receive(connections, logger, pnum=15, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=3, fields=[("bist_status", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(res.get("bist_status"), int(equal_value), "bist test")
    if verify_status:
        return True, to_hex_without_head(res.get("bist_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res.get("bist_status"), 2)


def hinge_status_test(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("hinge status test")
    connection = connections.get("serial_dut")
    equal_value = kwargs.get("limit").get("min")
    response = bba_read_send_receive(connections, logger, pnum=35, count=1, **kwargs)
    if not response:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "fail"
    res = builder.unpack_payload_fields(payload=response, offset=3, fields=[("hinge_status", 2)])
    logger.debug(res)
    verify_status, msg = verify_limit(res.get("hinge_status"), int(equal_value), "hinge status test")
    if verify_status:
        return True, to_hex_without_head(res.get("hinge_status"), 2)
    else:
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, to_hex_without_head(res.get("hinge_status"), 2)


def manual_wifi_bluetooth_test(connections, logger, **kwargs):
    """
    :param connections:
    :param logger:
    :param kwargs:
    :return:
    """
    logger.debug("manual wifi bluetooth test")
    connection = connections.get("serial_dut")
    check_infor = ask_question(
        "如图片所示，确保wifi功能被激活， 检查wifi donggle 是否可以连接产品， 连接成功输入 Y, 不成功输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "UI.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "wifi can not be connected"
    ask_question(
        "如图片所示，关闭wifi donggle 的wifi 功能",
        image_path=os.path.join(gl.get_value("picture_path"), "UI.jpg"),
    )
    check_infor = ask_question(
        "等待一会，wifi 连接断开后，如图所示产品应正常显示连接异常， 能正常显示wifi 异常输入 Y, 不能输入 N",
        image_path=os.path.join(gl.get_value("picture_path"), "UI.jpg"),
    )
    if check_infor.lower() == "n":
        gl.set_value("error_code", kwargs.get("error_code", ""))
        return False, "wifi can not be connected"

    return False, "validation"


def hex_without_prefix(number):
    """
    output hex without prefix
    :param number:
    :return:
    """
    return hex(number)[2:]


def format_hex(number, bit=2):
    """
    output format hex
    :param number:
    :return:
    """
    formatted_hex = format(number, "0{}x".format(bit))
    return formatted_hex


def ascii_bytes(str="0x00"):  # 16进制字符串
    ascii_str = bytes.fromhex(str).decode("ascii")
    return ascii_str


def string_to_hex(s):
    return " ".join([format(ord(c), "02x") for c in s])
