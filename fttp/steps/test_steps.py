import time
import numpy
from multiprocessing import Process, Event
from src.ui.ask_question import ask_question

from src.libs import global_var as gl
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.common import *
from src.libs.ble_driver import init, main, rssi_measure
import multiprocessing
from src.libs.ble_dangle import tx_run, Nrf
from src.steps import common_steps

builder = NetworkFrameBuilder()


def scan(connections, logger, **kwargs):
    print(f"get current cell_id:{gl.get_current_cell_id()}\n")
    gl.set_value("error_code", kwargs.get("cell_name"))
    logger.debug(f'layout_config:{gl.get_value("layout_config")}')
    logger.debug(f"get cell_name:{kwargs.get('cell_name')}\n")
    print(f'layout_config:{gl.get_value("layout_config")}')
    try:
        dusn = ask_question(
            "Please scan DUSN=>",
            # image_path=r"energy.jpeg",
            # auto_trigger={"func_name": r"hello"},
        )
    except Exception as e:
        print(e)
    logger.debug(f"scane dusn:{dusn}")
    if not dusn:
        if dusn is None or dusn == "":
            logger.warning("User cancel")
            return False, "User cancel"
    logger.info("Scanning device (simulate scan)...")
    return True, "SCANNED_OK"


def detect_dut(connections, logger, **kwargs):
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
                print(response)
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
    gl.set_value("platform_code", to_hex(res.get("platform_code"), 2))
    gl.set_value("site_code", to_hex(res.get("site_code"), 2))
    gl.set_value("dusn", to_hex(res.get("device_number"), 4))
    gl.set_value("pn", to_hex(res.get("product_code"), 2))
    gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
    return res, to_hex(res.get("device_number"), 4)


def led_off(connections, loger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0xA0,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    loger.debug(response)
    return True, "OFF"


def ui_led_test(connections, loger, **kwargs):
    connection = connections.get("usb")
    module = kwargs.get("module")
    color = kwargs.get("color")
    bank = kwargs.get("bank")
    loger.debug(f"module:{module}, color:{color}, bank:{bank}")
    cmd_hex = led_cmd_mapping.get(module, {})[bank].get(color)
    time.sleep(0.1)
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=cmd_hex,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    loger.debug(response)
    return True, color


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
    gl.set_value("ble_mac", mac)
    return True, mac


def enable_ble_broadcast(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value=0x00BE,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    logger.debug(response)
    return True, "BLE_ENABLE"


def read_ble_status(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_read_request_frame(
        mode="hid",
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
            ("ble_status", 2),
        ],
    )
    status = to_hex(res["ble_status"], 2)
    print(f"ble status:{status}")
    return True, status


def rssi_worker(serial_port, mac):
    try:
        print("serial_port", serial_port)
        target_mac = mac
        init("NRF52")
        rssi = rssi_measure(serial_port, target_mac)
        print("rssi_worker finished")
        return True, rssi
    except Exception as e:
        print(f"Got dangle issue:{e}")
        return False, -999


def read_rssi(connections, logger, **kwargs):
    serial_port = kwargs.get("serial_port")
    mac = gl.get_value("ble_mac")
    with multiprocessing.Pool(1) as pool:
        async_result = pool.apply_async(rssi_worker, (serial_port, mac))
        try:
            result = async_result.get(timeout=15)
        except multiprocessing.TimeoutError:
            result = (False, "TIMEOUT")
    logger.debug(f"result {result}")
    if result[1] < -70:
        return False, result[1]
    return result[0], result[1]


# def read_rssi(connections, logger, **kwargs):
#     serial_port = kwargs.get("serial_port")
#     stop_event = gl.get_value("stop_event")
#     while not stop_event.is_set():
#         time.sleep(2)
#         # try:
#         #     init("NRF52")
#         #     rssi = rssi_measure(serial_port)
#         # except Exception as e:
#         #     logger.debug(f"Got dangle issue:{e}")
#         #     return False, 'ERROR RSSI'
#     return True, str(rssi)


def read_ble_rf_status(connections, logger, **kwargs):
    connection = connections.get("usb")
    hid_frame = builder.build_read_request_frame(
        mode="hid",
        read_only=True,
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ble_tx_rx_status", 1), ("packets", 2)])
    ble_tx_rx_status = to_hex(res["ble_tx_rx_status"], 1)
    packets = res["packets"]
    print(f"ble status:{ble_tx_rx_status}")
    print(f"packets:{packets}")
    return True, ble_tx_rx_status


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
    res = builder.unpack_payload_fields(payload=response, offset=5, fields=[("ble_tx_rx_status", 1), ("packets", 2)])
    ble_tx_rx_status = to_hex(res["ble_tx_rx_status"], 1)
    packets = res["packets"]
    print(f"ble status:{ble_tx_rx_status}")
    print(f"packets:{packets}")
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
        channel=ch_hex,
        tx_power=pw_hex,
        tx_payload_type=0x00,
        tx_payload_length=0x25,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    return True, "END_RF_OK"


def ble_tx_test(connections, logger, **kwargs):
    serial_port = kwargs.get("serial_port")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
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
        tx_payload_length=0x25,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    time.sleep(0.1)
    rssi = tx_run(ch=ch, port=serial_port)
    end_rf(connections, logger, **kwargs)
    return True, str(rssi)


def ble_rx_test(connections, logger, **kwargs):
    serial_port = kwargs.get("serial_port")
    freq = kwargs.get("freq", 2402)
    power = kwargs.get("power")
    pw_hex = power_mapping.get(power)
    ch_hex = ch_mapping.get(freq)
    connection = connections.get("usb")
    # end_rf(connections, logger, **kwargs)
    nrf = Nrf(port=serial_port)
    nrf.intial()
    nrf.tx_mode()
    nrf.set_rx_ch()
    nrf.package_len()
    nrf.setting_phy()
    nrf.send_package()
    time.sleep(1.2)
    hid_frame = builder.build_write_request_frame(
        mode="hid",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x8C,
        type=0x02,
        channel=ch_hex,
        tx_power=pw_hex,
        tx_payload_type=0x00,
        tx_payload_length=0x25,
        secret_key=0xC001BABE,
        phy=0x00,
        rx_mode_idx=0x00,
    )
    response = connection.send_receive(hid_frame, timeout=1)
    package = read_ble_package(connections, logger, **kwargs)
    nrf.close()
    rate = round((2000.0 - package) / 2000.0, 2)
    lost_rate = f"{rate}%"
    return True, lost_rate


def overall_test_result(connections, logger, **kwargs):
    result, value = common_steps.overall_test_result(connections, logger, **kwargs)
    return result, value
