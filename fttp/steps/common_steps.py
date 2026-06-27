import time
from src.libs import global_var as gl
from src.libs.common import *
from src.libs.cmd_generator import NetworkFrameBuilder
from src.definition.product_mapping import *
builder = NetworkFrameBuilder()


def overall_test_result(connections, logger, **kwargs):
    logger.info("overall_test_result")
    all_step_results = kwargs.get("all_step_results")
    if not all_step_results:
        return False, "NO_STEP_RESULTS"
    else:
        for result in all_step_results:
            if result.get("status") != "PASS":
                error_code = gl.get_value("error_code")
                return False, error_code
        return True, kwargs.get("limit", {}).get("min")


def detect_dut(connections, logger, **kwargs):
    connection = connections.get("dut")
    stop_event = gl.get_value("stop_event")
    limit = kwargs.get("limit")
    while not stop_event.is_set():
        try:
            if connection.ensure_connected():
                cmd_frame = builder.build_read_request_frame(
                    mode="uart",
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
    return True, to_hex(res.get("device_number"), 4)