import math
import os.path
import time
from getpass import fallback_getpass

import numpy
from multiprocessing import Process, Event
from src.ui.ask_question import ask_question

from src.libs import global_var as gl
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.common import *
from src.libs.scaner import KeyenceScanner
from src.libs.tcpip import TCPClient
# from src.libs.ble_driver import init, main, rssi_measure
import multiprocessing

# from src.libs.ble_dangle_Se import tx_run, Nrf
from src.steps import common_steps

from src.libs.ble_dangle import tx_run, Nrf
from src.libs.Scanner_Uart import ScannerDriver

builder = NetworkFrameBuilder()


# def scan(connections, logger, **kwargs):
#     dusn = ask_question("Please scan DUSN=>", image_path=r'energy.jpeg',
#                         auto_trigger={"func_name": r"hello"})
#     # dusn = ask_question("Please scan DUSN=>")
#     logger.debug(f"scane dusn:{dusn}")
#     if not dusn:
#         if dusn is None or dusn == "":
#             logger.warning("User cancel")
#             return False, "User cancel"
#     logger.info("Scanning device (simulate scan)...")
#     return True, "SCANNED_OK"


def detect_dut_pre(connections, logger, **kwargs):
    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")

    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode="hid",
                    read_only=True,
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x01,
                )
                logger.debug(f"build cmd: { cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.debug(response)
                if response:
                    if not os.path.exists("log.log"):
                        with open("log.log", "w") as f:
                            f.write("")
                        break
                    else:
                        continue
                else:
                    if os.path.exists("log.log"):
                        os.remove("log.log")
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            logger.debug(e)
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
    gl.set_value("codentify_code", codenticode)

    # gl.set_value('platform_code', to_hex(res.get("platform_code"), 2))
    gl.set_value("platform", codenticode[:4])

    # gl.set_value('site_code', to_hex(res.get("site_code"), 2))
    gl.set_value("site_code", codenticode[8:12])
    # gl.set_value("dusn", to_hex(res.get("device_number"), 4))
    gl.set_value("dusn", codenticode)
    gl.set_value("pn", to_hex(res.get("product_code"), 2)[2:])

    # gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
    gl.set_value("product_code", codenticode[4:8])
    # return res, to_hex(res.get("device_number"), 4)
    error_code = gl.get_value("error_code")
    if error_code:
        gl.set_value("error_code", "")
    return res, ""

def scan_barcode_keyence(connections, logger, **kwargs):
    barcode = ""
    connection = connections.get("scanner")
    print(connections)
    scanner = KeyenceScanner(connection, logger)
    barcode = scanner.auto_scan()
    print(barcode)
    return barcode
def scan_barcode(connections, logger, **kwargs):
    barcode = ""
    connection = connections.get("scanner")
    logger.info(f"Get Scanner: {connection}")
    scanner = ScannerDriver(connection= connection, logger = logger)
    barcode = scanner.trigger_scan()
    print(barcode)
    logger.debug(f"Zebra barcode:{barcode}")
    return barcode
def read_barcode(ip):
    barcode = ""
    client = TCPClient(ip, 9004, timeout=5, buffer_size=2048)
    try:
        client.connect()
        for i in range(5):
            barcode = client.send_receive(b"LON\r")
            print("Received:", barcode)
            client.send(b"LOFF\r")
            if barcode:
                break
            time.sleep(0.2)
    except Exception as e:
        print("Error:", e)
    finally:
        client.disconnect()
    return barcode


def detect_dut(connections, logger, **kwargs):

    connection = connections.get("usb")
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    auto_scan = user_config.get("auto_scan")
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode="hid",
                    read_only=True,
                    reply_hop_count=0,
                    hop_count=0,
                    parameter=0x01,
                )
                logger.debug(f"build cmd: { cmd_frame.hex()}")
                response = connection.send_receive(cmd_frame, timeout=1)
                logger.debug(response)

                if response:
                    if not os.path.exists("log.log"):
                        with open("log.log", "w") as f:
                            f.write("")

                        if auto_scan:
                            time.sleep(2)
                            for _ in range(10):
                                barcode = scan_barcode(connections, logger, **kwargs)
                                if " " in barcode and len(barcode) == 17:
                                    gl.set_value("dusn", barcode)
                                    gl.set_value("codentify", barcode)
                                    gl.set_value("codentify_code", barcode)
                                    break
                                time.sleep(1)
                        break
                    else:
                        continue

                else:
                    if os.path.exists("log.log"):
                        os.remove("log.log")
                    time.sleep(1)
                    continue
            else:
                time.sleep(1)
                continue
        except Exception as e:
            logger.debug(e)
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
    dusn = "{0}{1}{2}{3}".format(
        to_hex_without_head(res.get("platform_code"), 2),
        to_hex_without_head(res.get("product_code"), 2),
        to_hex_without_head(res.get("site_code"), 2),
        to_hex_without_head(res.get("device_number"), 4),
    ).upper()

    logger.debug(f"dusn:{dusn}")



    # gl.set_value('platform_code', to_hex(res.get("platform_code"), 2))
    gl.set_value("platform", dusn[:4])

    # gl.set_value('site_code', to_hex(res.get("site_code"), 2))
    gl.set_value("site_code", dusn[8:12])
    # gl.set_value("dusn", to_hex(res.get("device_number"), 4))
    gl.set_value("dusn", dusn)
    gl.set_value("codenticode", dusn)
    gl.set_value("pn", to_hex(res.get("product_code"), 2)[2:])

    # gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
    gl.set_value("product_code", dusn[4:8])
    # return res, to_hex(res.get("device_number"), 4)
    error_code = gl.get_value("error_code")
    if error_code:
        gl.set_value("error_code", "")
    return res, ""


def start_test(connections, logger, **kwargs):
    logger.info("start_test")
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    gl.set_value("pn", cells.get("pid")[2:])
    print(gl.get_value("pn"))
    user_config = cells.get("user_config")
    auto_scan = user_config.get("auto_scan")
    if not auto_scan:

        for i in range(20):
            answer = ask_question("Please Scan barcode")
            # rootDir = os.path.abspath('')
            # logDir = os.path.join(rootDir, "log")
            # if not os.path.exists(logDir):
            #     os.makedirs(logDir)
            # logPath = os.path.join(logDir, f"log_{time.strftime('%Y%m%d')}.log")
            # with open(logPath,"a+") as f:
            #     f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{answer}\n")
            if answer:
                if " " in answer and len(answer) == 17:
                    gl.set_value("dusn", answer)
                    gl.set_value("codentify", answer)
                    gl.set_value("codentify_code", answer)
                    break
            time.sleep(1)

    return True, ""

def scan_vsn(connections, logger, **kwargs):
    error_code = gl.get_value("error_code")
    if error_code:
        return False, error_code
    codentify =  gl.get_value("codentify_code").strip()
    if " " in codentify and len(codentify) == 17:
        return True, codentify
    else:
        return False, codentify

def read_dusn_pre(connections, logger, **kwargs):
    dusn = gl.get_value("codenticode")
    gl.set_value("dusn", dusn[-8:])

    limit = kwargs.get("limit").get("min")[:8]

    if not dusn.lower().startswith(limit.lower()):
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, dusn
    return True, dusn.upper()

def read_dusn(connections, logger, **kwargs):
    connection = connections.get("usb")
    response = None
    try:
        if connection.ensure_connected():
            cmd_frame = builder.build_read_request_frame(
                mode="hid",
                read_only=True,
                reply_hop_count=0,
                hop_count=0,
                parameter=0x01,
            )
            logger.debug(f"build cmd: {cmd_frame.hex()}")
            response = connection.send_receive(cmd_frame, timeout=1)
            logger.debug(response)
            if response:
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
                dusn = "{0}{1}{2}{3}".format(
                    to_hex_without_head(res.get("platform_code"), 2),
                    to_hex_without_head(res.get("product_code"), 2),
                    to_hex_without_head(res.get("site_code"), 2),
                    to_hex_without_head(res.get("device_number"), 4),
                ).upper()

                logger.debug(f"dusn:{dusn}")
                gl.set_value("platform", dusn[:4])
                # gl.set_value('site_code', to_hex(res.get("site_code"), 2))
                gl.set_value("site_code", dusn[8:12])
                # gl.set_value("dusn", to_hex(res.get("device_number"), 4))
                gl.set_value("dusn", dusn)
                gl.set_value("codenticode", dusn)
                gl.set_value("pn", to_hex(res.get("product_code"), 2)[2:])

                # gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
                gl.set_value("product_code", dusn[4:8])
                gl.set_value("dusn", dusn[-8:])
                limit = kwargs.get("limit").get("min")[:8]
                if not dusn.lower().startswith(limit.lower()):
                    gl.set_value("error_code", kwargs.get("error_code"))
                    return False, dusn
                return True, dusn.upper()

    except Exception as e:
        return False, str(e)

    # dusn = gl.get_value("dusn")
    # gl.set_value("dusn", dusn[-8:])
    #
    # limit = kwargs.get("limit").get("min")[:8]
    #
    # if not dusn.lower().startswith(limit.lower()):
    #     gl.set_value("error_code", kwargs.get("error_code"))
    #     return False, dusn
    # return True, dusn.upper()


def read_station(connections, logger, **kwargs):
    # time.sleep(3)
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    if TBBUID:
        return True, TBBUID
    return False, TBBUID


def check_mtmode(connections, logger, **kwargs):
    connection = connections.get("usb")
    command = builder.build_read_request_frame(
        mode="hid",
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

    if response[7] == 0x00 and response[8] == 0x00:
        gl.set_value("error_code", kwargs.get("error_code"))
        return False, f"{hex(response[8])[2:]}{hex(response[7])[2:]}"
    else:
        return True, "pass"


def read_ble_package(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(f"response:{response}")
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ble_tx_rx_status", 1), ("packets", 2)])
    ble_tx_rx_status = to_hex(res["ble_tx_rx_status"], 1)
    packets = res["packets"]
    logger.debug(f"ble status:{ble_tx_rx_status}")
    logger.debug(f"--packets:{packets}")
    return packets


def end_rf(connections, logger, **kwargs):
    connection = connections.get("usb")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
    pw_hex = power_mapping.get(power)
    ch_hex = ch_mapping.get(freq)

    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
        type=0x00,
        channel=0,
        tx_power=0,
        tx_payload_type=0x00,
        tx_payload_length=0x25,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    # time.sleep(1)
    # reset_dut(connections, logger, **kwargs)

    try:
        cmd_frame = builder.build_read_request_frame(
            mode="hid",
            read_only=True,
            reply_hop_count=0,
            hop_count=0,
            parameter=0x01,
        )
        logger.debug(f"build cmd: {cmd_frame.hex()}")
        response = connection.send_receive(cmd_frame, timeout=1)
        logger.debug(response)
        if response:
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
            dusn = "{0}{1}{2}{3}".format(
                to_hex_without_head(res.get("platform_code"), 2),
                to_hex_without_head(res.get("product_code"), 2),
                to_hex_without_head(res.get("site_code"), 2),
                to_hex_without_head(res.get("device_number"), 4),
            ).upper()
            if dusn[-8:] ==  gl.get_value("dusn"):
                return True,""
            else:
                return False,dusn
    except Exception as e:
        return False, str(e)
    return True, ""

def reset_dut(connections, logger, **kwargs):
    """
        reset dut result
        :param connections:
        :param logger:
        :param kwargs:
        :return:
        """
    logger.debug("Reset DUT")
    connection = connections.get("usb")
    reset_start_time = time.time()
    cmd_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x02,
        count=1,
        value0=0x00,
    )
    logger.debug(f"build cmd: {cmd_frame.hex()}")
    response = connection.send_receive(cmd_frame, timeout=1)
    logger.debug(response)
    return True, ""


def ble_tx_test(connections, logger, **kwargs):
    serial_port = kwargs.get("serial_port")
    status = True
    rssi = 0
    # connection_dongle = connections.get("serial_dongle")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
    error_code = kwargs.get("error_code")
    pw_hex = power_mapping.get(power)
    ch_hex = ch_mapping.get(freq)
    ch = kwargs.get("ch")
    connection = connections.get("usb")
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
        type=0x01,
        channel=ch_hex,
        tx_power=pw_hex,
        tx_payload_type=0x00,
        tx_payload_length=0x00,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    # response = connection.send_receive(hid_frame, timeout=1)

    try:
        for i in range(3):
            status = True
            response = connection.send_receive(hid_frame, timeout=1)
            logger.debug(f"tx res: {response}")
            rssi = tx_run(ch=ch, port=serial_port)
            # rssi = tx_run(connection_dongle, ch=ch)
            end_rf(connections, logger, **kwargs)
            lsl = kwargs.get("limit").get("min")
            usl = kwargs.get("limit").get("max")
            logger.debug(f"lsl:{lsl},usl:{usl},rssi:{rssi}")
            if not math.isnan(rssi):
                if rssi < lsl or rssi > usl:
                    gl.set_value("error_code", error_code)
                    status = False
                    # return False, str(rssi)
                else:
                    break
            time.sleep(0.3)
    except Exception as e:
        gl.set_value("error_code", error_code)
        logger.warning(f"{e}")
        status = False
        # return False, error_code
    return status, str(rssi)


def ble_rx_test_(connections, logger, **kwargs):
    serial_port = kwargs.get("serial_port")
    # connection_dongle = connections.get("serial_dongle")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
    error_code = kwargs.get("error_code")
    pw_hex = power_mapping.get(power)
    ch_hex = ch_mapping.get(freq)
    try:
        connection = connections.get("usb")
        # end_rf(connections, logger, **kwargs)

        nrf = Nrf(port=serial_port)
        # nrf = NrfExt(connection_dongle)
        nrf.intial()
        nrf.tx_mode()
        nrf.set_rx_ch()
        nrf.package_len()
        nrf.setting_phy()
        nrf.send_package()
        time.sleep(1.25)

        hid_frame = builder.build_write_request_frame(
            mode="hid",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x8C,
            type=0x02,
            channel=0,
            tx_power=0,
            tx_payload_type=0x00,
            tx_payload_length=0x25,
            secret_key=0xC001BABE,
            phy=0x00,
            rx_mode_idx=0x00,
        )
        response = connection.send_receive(hid_frame, timeout=1)
        package = read_ble_package(connections, logger, **kwargs)
        nrf.close()
        logger.debug(f":{package}")
        rate = round((2000.0 - package) / 2000.0, 2)
        lost_rate = f"{rate}%"
        usl = kwargs.get("limit").get("max")


        if rate > usl:
            gl.set_value("error_code", error_code)
    except Exception as e:
        logger.warning(f"{e}")
        gl.set_value("error_code", error_code)
        return False, error_code
    return True, str(rate)


def ble_rx_test_end(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
        type=0x00,
        channel=0x01,
        tx_power=0,
        tx_payload_type=0x00,
        tx_payload_length=0x00,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    response = connection.send_receive(hid_frame, timeout=1)


def ble_rx_test(connections, logger, **kwargs):

    serial_port = kwargs.get("serial_port")
    # connection_dongle = connections.get("serial_dongle")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
    error_code = kwargs.get("error_code")
    pw_hex = power_mapping.get(power)
    ch_hex = ch_mapping.get(freq)
    try:
        connection = connections.get("usb")

        hid_frame = builder.build_write_request_frame(
            mode="hid",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x8C,
            type=0x02,
            channel=1,
            tx_power=0,
            tx_payload_type=0x00,
            tx_payload_length=0x00,
            secret_key=0xC001BABE,
            phy=0x00,
            rx_mode_idx=0x00,
        )

        response = connection.send_receive(hid_frame, timeout=1)

        # end_rf(connections, logger, **kwargs)

        nrf = Nrf(port=serial_port)
        # nrf = NrfExt(connection_dongle)
        nrf.intial()  # 00 00
        nrf.tx_mode()  # 09 DB
        # nrf.set_rx_ch()
        # nrf.package_len()
        nrf.setting_phy()  # 02 04
        nrf.send_package()  # 81 04
        time.sleep(1.2)
        nrf.stop_tx()
        ble_rx_test_end(connections, logger, **kwargs)
        package = read_ble_package(connections, logger, **kwargs)
        nrf.close()
        logger.debug(f":{package}")
        rate = round(abs(round((2000.0 - package) / 2000.0, 4) * 100), 2)
        usl = kwargs.get("limit").get("max")
        logger.debug(f"rx lost rate: {rate},rx usl: {usl}")
        if rate > usl:
            gl.set_value("error_code", error_code)
    except Exception as e:
        logger.warning(f"{e}")
        gl.set_value("error_code", error_code)
        return False, error_code
    return True, str(rate)


# def verify_hw_reversion(connections, logger, **kwargs):
#     logger.info("verify_hw_reversion...")
#     return True, "POWERED_ON"


# def read_info(connections, logger, **kwargs):
#     logger.info("Read device info (simulate read DUSN/PID)...")
#     return True, {"dusn": "SIMULATED_DUSN", "pid": "SIMULATED_PID"}


# def verify_dusn(connections, logger, **kwargs):
#     logger.info("Cverify_dusn")
#     return True, "SN_OK"


def overall_test_result(connections, logger, **kwargs):
    # reset_dut(connections, logger, **kwargs)
    # for name, conn in connections.items():
    #     conn.close()
    return common_steps.overall_test_result(connections, logger, **kwargs)
    # logger.info(f"finalize,{os.path.abspath('')}")
    # for name, conn in connections.items():
    #     conn.close()
    # error_code = gl.get_value("error_code")
    #
    # if error_code:
    #     if error_code != "":
    #         return False, error_code
    # return True, "0"


# def dummy_long_test(connections, logger, **kwargs):
#     import time
#     logger.info("Begin long dummy test...")
#     for i in range(3):
#         time.sleep(1)
#         logger.info(f"Dummy test step {i+1}")
#     return True, "OK"
