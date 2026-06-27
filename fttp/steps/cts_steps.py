import os.path
import time
from multiprocessing import Process, Event

# from async_timeout import timeout

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
from src.libs.common import fixture_start
from src.libs.mes import routing_check
from src.steps import common_steps

builder = NetworkFrameBuilder()


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


def overall_test_result(connections, logger, **kwargs):
    logger.info("finalize")
    connection = connections.get("serial_dut")
    # for name, conn in connections.items():
    #     conn.close()
    cmd_frame_led_off = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00A4,
    )
    response = connection.send_receive(cmd_frame_led_off, timeout=1)
    return common_steps.overall_test_result(connections, logger, **kwargs)
    # error_code = gl.get_value("error_code")
    # if error_code != "":
    #     return False, error_code
    # return True, "0"


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


def start_test(connections, logger, **kwargs):
    logger.info("start_test")
    stop_event = gl.get_value("stop_event")
    gl.set_value("error_code", "")
    config = gl.get_value("layout_config")

    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")
    scanner_ip = fixture_io.get("scanner_ip")
    cells = config.get("cells")[0]
    gl.set_value("pn", cells.get("pid")[2:])
    user_config = cells.get("user_config")
    picture_path = user_config.get("picture_path")
    gl.set_value("picture_path", picture_path)
    fixture_start()
    barcode = "00000000000000000000"
    try:
        barcode = read_barcode(scanner_ip).decode("utf-8").strip()
    except Exception as e:
        logger.debug(str(e))
    gl.set_value("dusn", barcode)
    return True, ""


def scan_barcode(connections, logger, **kwargs):
    stop_event = gl.get_value("stop_event")
    config = gl.get_value("layout_config")
    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")
    scanner_ip = fixture_io.get("scanner_ip")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    flexflow = user_config.get("flexflow")
    TBBUID = user_config.get("TBBUID")

    barcode = gl.get_value("dusn")

    if barcode.strip() == "00000000000000000000":
        gl.set_value("error_code", "E000")
        return False, barcode.strip()
    elif flexflow:
        logger.debug(flexflow)
        status, info = routing_check(barcode.strip(), TBBUID)
        if status:
            return True, barcode.strip()
        else:
            gl.set_value("error_code", "R001")
            return False, "R001"

    return True, barcode.strip()


def read_dusn_control_(connections, logger, **kwargs):

    connection = connections.get("serial_dut")
    cmd_dusn_control = builder.build_read_request_frame(
        mode="uart", read_only=True, reply_hop_count=0, hop_count=0, parameter=0x01
    )

    response = None
    for i in range(5):
        response = connection.send_receive(cmd_dusn_control, timeout=1)
        if response[5] == 0x89 and response[6] == 0x00:
            break

    dusns = [f"{byte:02x}" for byte in response]
    dusn = (
        f"{dusns[8]}{dusns[7]}{dusns[10]}{dusns[9]}{dusns[12]}{dusns[11]}{dusns[16]}{dusns[15]}{dusns[14]}{dusns[13]}"
    )
    gl.set_value("platform", f"{dusns[8]}{dusns[7]}")
    gl.set_value("site_code", f"{dusns[12]}{dusns[11]}")
    gl.set_value("dusn", dusn[-8:])
    gl.set_value("product_code", f"{dusns[10]}{dusns[9]}")

    gl.set_value("codenticode", dusn)
    limit = kwargs.get("limit").get("min")[:8]

    if dusn.lower().startswith(limit.lower()):
        return True, dusn
    else:
        gl.set_value("error_code", "E002")
    return False, dusn

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
def screen_touch(connections, logger, **kwargs):
    connection = connections.get("serial_dut")

    logger.info("screen_touch")
    cmd_frame_touch_enter = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00C4,
    )
    logger.debug(f"build cmd: {cmd_frame_touch_enter.hex()}")
    status = True
    first = -1
    second = -1
    third = -1
    for j in range(5):
        try:
            response = connection.send_receive(cmd_frame_touch_enter, timeout=1)

            cmd_frame_touch_complete = builder.build_write_request_frame(
                mode="uart",
                reply_hop_count=0,
                hop_count=0,
                parameter=0x08,
                pnum=14,
                count=1,
                value1=0x0000,
            )
            logger.debug(f"build cmd: {cmd_frame_touch_complete.hex()}")

            cmd_frame_touch_read = builder.build_read_request_frame(
                mode="uart",
                read_only=True,
                reply_hop_count=0,
                hop_count=0,
                parameter=0x08,
                pnum=260,
                count=3,
            )

            response = connection.send_receive(cmd_frame_touch_read, timeout=1)
            data = list(response)
            status = False
            first_before = data[13]
            second_before = data[15]
            third_before = data[17]

            for i in range(100):
                response = connection.send_receive(cmd_frame_touch_read, timeout=1)
                data = list(response)
                first_after = data[13]
                second_after = data[15]
                third_after = data[17]
                first = abs(first_after - first_before)
                second = abs(second_after - second_before)
                third = abs(third_after - third_before)
                lsl = kwargs.get("limit").get("min")
                if first >= lsl and second >= lsl:
                    status = True
                    break
                elif second >= lsl and third >= lsl:
                    status = True
                    break
                elif first >= lsl and third >= lsl:
                    status = True
                    break
                if status:
                    break
                first_before = first_after
                second_before = second_after
                third_before = third_after
                time.sleep(0.2)
            break
        except Exception as e:
            print(str(e))
            logger.debug(str(e))
            status = False
            continue
        time.sleep(1)

    if not status:
        gl.set_value("error_code", "E003")
    return status, f"{first}, {second}, {third}"


def led_r(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    logger.info("led_r")

    config = gl.get_value("layout_config")
    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")
    result = ""
    cmd_frame_led_r = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=263,
        count=2,
        value1=0xFF80,
        value2=0x07FF,
    )
    logger.debug(f"build cmd: {cmd_frame_led_r.hex()}")
    response = connection.send_receive(cmd_frame_led_r, timeout=1)
    cmd_frame_led_on = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00C5,
    )
    response = connection.send_receive(cmd_frame_led_on, timeout=1)

    logger.debug(f"build cmd: {cmd_frame_led_on.hex()}")

    picture_path = gl.get_value("picture_path")

    params = {
        "tester_port": tester_port,
        "pass": fixture_io.get("pass"),
        "fail": fixture_io.get("fail"),
    }
    results = []
    if tester_port:
        result = ask_question(
            "Led_R is On?",
            image_path=os.path.join(picture_path, "step2.jpg"),
            auto_trigger={"func_name": r"fixture_input", "params": params},
        )
        results = result.split(",")
    else:
        result = ask_question("Led_R is On?", image_path=os.path.join(picture_path, "step2.jpg"))
        if result.strip().upper() == "Y":
            results.append("True")
        else:
            results.append("False")

    status = False
    info = "FAIL"
    results = result.split(",")
    if results[0] == "True":
        status = True
        info = "PASS"

    status = False
    info = "FAIL"
    results = result.split(",")
    if results[0] == "True":
        status = True
        info = "PASS"
    if not status:
        gl.set_value("error_code", "E004")
    return status, info


def led_l(connections, logger, **kwargs):
    connection = connections.get("serial_dut")
    logger.info("led_l")
    config = gl.get_value("layout_config")
    fixture_io = config.get("fixture_io")
    tester_port = config.get("tester_port")

    cmd_frame_led_l = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=263,
        count=2,
        value1=0x007F,
        value2=0x0000,
        value3=0x0000,
    )
    logger.debug(f"build cmd: {cmd_frame_led_l.hex()}")
    response = connection.send_receive(cmd_frame_led_l, timeout=1)
    cmd_frame_led_on = builder.build_write_request_frame(
        mode="uart",
        reply_hop_count=0,
        hop_count=0,
        parameter=0x08,
        pnum=14,
        count=1,
        value1=0x00C5,
    )
    response = connection.send_receive(cmd_frame_led_on, timeout=1)
    logger.debug(f"build cmd: {cmd_frame_led_on.hex()}")

    picture_path = gl.get_value("picture_path")
    params = {
        "tester_port": tester_port,
        "pass": fixture_io.get("pass"),
        "fail": fixture_io.get("fail"),
    }
    results = []
    if tester_port:
        result = ask_question(
            "Led_L is On?",
            image_path=os.path.join(picture_path, "step3.jpg"),
            auto_trigger={"func_name": r"fixture_input", "params": params},
        )
        results = result.split(",")
    else:
        result = ask_question("Led_l is On?", image_path=os.path.join(picture_path, "step3.jpg"))
        if result.strip().upper() == "Y":
            results.append("True")
        else:
            results.append("False")
    status = False
    info = "FAIL"
    results = result.split(",")
    if results[0] == "True":
        status = True
        info = "PASS"
    # cmd_frame_led_off = builder.build_write_request_frame(mode='uart', reply_hop_count=0, hop_count=0, parameter=0x08,
    #                                                      pnum=14, count=1, value1=0x00A4)
    # response = connection.send_receive(cmd_frame_led_off, timeout=1)
    if not status:
        gl.set_value("error_code", "E005")
    return status, info


def read_station(connections, logger, **kwargs):
    config = gl.get_value("layout_config")
    cells = config.get("cells")[0]
    user_config = cells.get("user_config")
    TBBUID = user_config.get("TBBUID")
    if TBBUID:
        return True, TBBUID
    return False, TBBUID

def read_and_validate_xyz(connection, builder):
    """
    向设备发送写请求（parameter=0x08, pnum=14, count=1, value=0x15），
    并从响应的 payload 中 offset=5 起解析 x/y/z（每个2字节，假定无符号、设备端与 builder 缺省字节序一致），
    然后校验每个值都在 [0, 300] 范围内。

    Returns:
        dict: {
           "x": int, "y": int, "z": int,
           "raw_response": bytes
        }

    Raises:
        ValueError: 当响应为空、长度不足、或字段值不在范围时抛出。
        RuntimeError: 当底层通信异常时抛出。
    """
    # 1) 组包下发（按你给的参数）
    try:
        hid_frame = builder.build_write_request_frame(
            mode="hid",
            reply_hop_count=0,
            hop_count=0,
            parameter=0x08,
            pnum=14,
            count=1,       # 你写的 "count1" 我按 count=1 处理
            value=0x15,    # 你给定的 value
        )
    except Exception as e:
        raise RuntimeError(f"构造写请求帧失败: {e}")

    # 2) 发送并接收响应
    try:
        response = connection.send_receive(hid_frame, timeout=1)
    except Exception as e:
        raise RuntimeError(f"发送/接收失败: {e}")

    if not response:
        raise ValueError("设备无响应或响应为空。")

    # 3) 解析：从 offset=5 开始，取 x/y/z 各 2 字节
    #    如果你的协议中 x/y/z 并非紧随 offset=5，请调整 offset 或先解析前置字段再顺移。
    xyz_fields = [
        ("x", 2),
        ("y", 2),
        ("z", 2),  # 如果第三个字段也叫 x，请改成 ("x2", 2)
    ]

    # 先做长度兜底（offset + 6 字节）
    offset = 5
    min_len = offset + sum(sz for _, sz in xyz_fields)
    if len(response) < min_len:
        raise ValueError(f"响应长度不足：期望≥{min_len} 字节，实际 {len(response)} 字节。")

    # 使用你示例同款风格的解析方法
    try:
        xyz = builder.unpack_payload_fields(
            payload=response,
            offset=offset,
            fields=xyz_fields,
        )
        # 假定返回的是 dict（多数情况下该风格会返回形如 {"x":..., "y":..., "z":...}）
        # 如果你的 builder 返回其他结构（比如列表/元组），请按你的实际返回稍作改造。
        x = int(xyz["x"])
        y = int(xyz["y"])
        z = int(xyz["z"])
    except Exception as e:
        raise ValueError(f"payload 解析失败（offset={offset}）：{e}")

    # 4) 校验范围 [0, 300]
    def _check_range(name, val, lo=0, hi=300):
        if not (lo <= val <= hi):
            raise ValueError(f"{name} 超出范围 [{lo}, {hi}]：{val}")

    _check_range("x", x)
    _check_range("y", y)
    _check_range("z", z)

    # 一切正常则返回
    return {
        "x": x,
        "y": y,
        "z": z,
        "raw_response": response,
    }
