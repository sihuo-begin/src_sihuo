import time
import numpy
from multiprocessing import Process, Event
from src.ui.ask_question import ask_question

# from src.libs import global_var as gl
from src.libs.cmd_generator import NetworkFrameBuilder
from src.libs.fifo_lock import LockManager
from src.definition.product_mapping import *
from src.libs.common import *
from src.libs.ble_driver import init, main, rssi_measure
import multiprocessing
from src.libs.ble_dangle import tx_run, Nrf
from src.steps import common_steps

builder = NetworkFrameBuilder()


TEMP_TO_ADC = [
    3986, 3981, 3974, 3968, 3961, 3953, 3945, 3937, 3929, 3920,
    3911, 3902, 3892, 3882, 3871, 3860, 3848, 3836, 3824, 3811,
    3797, 3783, 3769, 3754, 3739, 3723, 3706, 3689, 3672, 3654,
    3635, 3616, 3596, 3576, 3555, 3534, 3512, 3489, 3466, 3443,
    3418, 3394, 3368, 3343, 3316, 3289, 3262, 3234, 3205, 3176,
    3147, 3117, 3087, 3056, 3025, 2993, 2961, 2929, 2896, 2863,
    2830, 2796, 2762, 2728, 2694, 2659, 2625, 2590, 2555, 2520,
    2484, 2449, 2414, 2378, 2343, 2308, 2272, 2237, 2202, 2167,
    2132, 2097, 2063, 2028, 1994, 1960, 1926, 1893, 1860, 1827,
    1794, 1762, 1730, 1698, 1667, 1636, 1605, 1575, 1545, 1516,
    1487
]


def adc_to_temp_interp(value):
    for i in range(len(TEMP_TO_ADC) - 1):
        if TEMP_TO_ADC[i] >= value >= TEMP_TO_ADC[i + 1]:

            x1 = TEMP_TO_ADC[i]
            x2 = TEMP_TO_ADC[i + 1]

            ratio = (value - x2) / (x1 - x2)

            return i + (1 - ratio)

    return len(TEMP_TO_ADC) - 1


def detect_dut(connections, logger, **kwargs):
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    connection_type = customer_config.get("connection_type")
    logger.debug(f"connection_type{connection_type}")
    connection = connections.get(connection_type)
    hop_count = kwargs.get("hop_count", 0)
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                if connection_type == "hid":
                    cmd_frame = builder.build_read_request_frame(
                        mode="hid",
                        read_only=True,
                        reply_hop_count=hop_count,
                        hop_count=0,
                        parameter=0x01,
                    )
                    logger.debug(f"build cmd: {cmd_frame.hex()}")
                    response = connection.send_receive(cmd_frame, timeout=1)
                    logger.debug("Get DUT response:{}".format(response))
                    if response:
                        break
                    else:
                        time.sleep(1)
                        continue
                else:
                    cmd_frame = builder.build_read_request_frame(
                        mode="uart", read_only=True, reply_hop_count=0, hop_count=hop_count, parameter=0x01
                    )
                    logger.debug(f"build cmd: { cmd_frame.hex()}")
                    response = connection.send_receive(cmd_frame, timeout=1)
                    logger.debug("Get DUT response:{}".format(list(response[len(cmd_frame) :])))
                    print(list(response[len(cmd_frame) :]))
                    if len(list(response[len(cmd_frame) :])) > 0:
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
    gl.set_value("pn", "000a")
    gl.set_value("product_code", f"{prodcut_map.get(hex(res.get('product_code')))}")
    return res, to_hex(res.get("device_number"), 4)


def read_bba_command(connection, logger, parameter, mode, hop_count=0, pnum=None, count=1):
    logger.info(f"pnum is:{pnum}")
    uart_frame = builder.build_read_request_frame(
        mode=mode, read_only=True, reply_hop_count=hop_count,
        hop_count=hop_count, parameter=parameter, pnum=pnum, count=count
    )
    logger.info(f"build frame is:{uart_frame.hex()}")
    response = connection.send_receive(uart_frame, timeout=1)
    if mode == "serial":
        logger.info(f"read response is:{response.hex()}")
    else:
        hex_str = ' '.join(f"{x:02X}" for x in response)
        logger.info(f"read response is:{hex_str}")
    return response


def loop_get_touch_value(connections, logger, **kwargs):
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    connection_type = customer_config.get("connection_type")
    logger.debug(f"connection_type{connection_type}")
    connection = connections.get(connection_type)
    cmd_raw = kwargs.get("cmd")
    loop = kwargs.get("loop")
    delay = kwargs.get("delay", 0.001)
    hop_count = kwargs.get("hop_count", 0)
    logger.debug(f"hop_count {hop_count}")
    loop_count = 0
    while not stop_event.is_set():
        time.sleep(delay)
        loop_count += 1
        try:
            response = read_bba_command(connection, parameter=0x83, mode=connection_type, hop_count=hop_count, pnum=None, logger=logger)
            logger.debug(response)
            if connection_type == "serial":
                res = builder.unpack_payload_fields(
                    payload=response,
                    offset=7,
                    fields=[
                        ("battery_volt", 2),
                        ("battery_temp", 2),
                    ],
                )
            else:
                res = builder.unpack_payload_fields(
                    payload=response,
                    offset=5,
                    fields=[
                        ("battery_volt", 2),
                        ("battery_temp", 2),
                    ],
                )
            temp_adc = res.get("battery_temp")
            temp = adc_to_temp_interp(temp_adc)
            logger.debug(f"get read temp count: {loop_count} touch data:{res}, temp:{temp}")
        except Exception as e:
            logger.debug(f"Meet run error {e}")
            continue

    return True, "Pass"


def loop_get_touch_value2(connections, logger, **kwargs):
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    connection_type = customer_config.get("connection_type")
    logger.debug(f"connection_type{connection_type}")
    connection = connections.get(connection_type)
    cmd_raw = kwargs.get("cmd")
    loop = kwargs.get("loop")
    delay = kwargs.get("delay", 0.001)
    hop_count = kwargs.get("hop_count", 0)
    loop_count = 0
    while not stop_event.is_set():
        time.sleep(delay)
        loop_count += 1
        try:
            response = read_bba_command(connection, pnum=1540, logger=logger, count=12)
            logger.debug(response)
            logger.info(response.hex())
            res = builder.unpack_payload_fields(
                payload=response,
                offset=13,
                fields=[
                    ("Key_value1", 2),
                    ("Key_value2", 2),
                    ("Key_value3", 2),
                    ("Delta1", 2),
                    ("Delta2", 2),
                    ("Delta3", 2),
                    ("ref1", 2),
                    ("ref2", 2),
                    ("ref3", 2),
                    ("key_status1", 2),
                    ("key_status2", 2),
                    ("key_status3", 2),
                ],
            )
            logger.debug(f"get touch count: {loop_count} touch data:{res}")
        except Exception as e:
            logger.debug(e)
            continue

    return True, "Pass"


def rd_loop_test(connections, logger, **kwargs):
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    connection_type = customer_config.get("connection_type")
    logger.debug(f"connection_type{connection_type}")
    connection = connections.get(connection_type)
    cmd_raw = kwargs.get("cmd")
    loop = kwargs.get("loop")
    hop_count = kwargs.get("hop_count", 0)
    try:
        # 支持输入"3f08c044..."或"3f 08 c0..."格式
        # cmd_str = cmd.strip().replace(" ", "")
        # if len(cmd_str) % 2 != 0:
        #     raise ValueError("Hex string长度应为偶数")
        # data = [int(cmd_str[i:i + 2], 16) for i in range(0, len(cmd_str), 2)]
        # logger.debug("Hex number:", data)
        for _ in range(loop):
            if isinstance(cmd_raw, list):
                for cmd in cmd_raw:
                    cmd_str = cmd.strip().replace(" ", "")
                    if len(cmd_str) % 2 != 0:
                        raise ValueError("Hex string长度应为偶数")
                    data = [int(cmd_str[i : i + 2], 16) for i in range(0, len(cmd_str), 2)]
                    logger.debug("Hex number:", data)
                    response = connection.send_receive(data)
                    if connection_type == "uart":
                        response = response[len(data) :]
                    if response:
                        logger.debug("设备返回：", " ".join([f"{x:02x}" for x in response]))
                        time.sleep(0.1)
                    else:
                        ask_question("请检查端口 通信无返回! 回车可继续")
                        logger.debug("无响应或超时。")
            else:
                cmd_str = cmd_raw.strip().replace(" ", "")
                if len(cmd_str) % 2 != 0:
                    raise ValueError("Hex string长度应为偶数")
                data = [int(cmd_str[i : i + 2], 16) for i in range(0, len(cmd_str), 2)]
                logger.debug("Hex number:", data)
                response = connection.send_receive(data)
                if connection_type == "uart":
                    response = response[len(data) :]
                if response:
                    logger.debug("设备返回：", " ".join([f"{x:02x}" for x in response]))
                else:
                    ask_question("请检查端口 通信无返回! 回车可继续")
                    logger.debug("无响应或超时。")
    except Exception as e:
        logger.debug(f"命令格式错误：{e}")
        return False, "FAIL"
    return True, "PASS"


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


def overall_test_result(connections, logger, **kwargs):
    result, value = common_steps.overall_test_result(connections, logger, **kwargs)
    return result, value
