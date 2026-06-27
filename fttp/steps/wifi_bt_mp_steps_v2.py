# encoding=utf-8

from __future__ import annotations

from src.libs.rf_test_api import RFTestAPI
from src.libs.calibration.pathloss import PathlossTable
from src.libs.chip.rtl8722f.state_store import get_or_create_state
from src.steps.common_steps import detect_dut
from src.libs.common import *
from src.ui.ask_question import ask_question
from src.libs.equipments.e3xxx.e3xxx_controler import E3xxxController
from src.libs.chip.rtl8720.chip_programming import AmebaPGTool


def _run(method_name: str, connections, logger, **kwargs):
    try:
        api = RFTestAPI(connections=connections, logger=logger)
        method = getattr(api, method_name)
        result = method(**kwargs)
        return result.ok, result.value
    except Exception as exc:
        logger.exception("step %s failed: %s", method_name, exc)
        return False, str(exc)


def step_detect_dut(connections, logger, **kwargs):
    return detect_dut(connections, logger, **kwargs)


def rf_mp_init(connections, logger, **kwargs):
    return _run("rf_mp_init", connections, logger, **kwargs)


def rf_preheat(connections, logger, **kwargs):
    return _run("rf_preheat", connections, logger, **kwargs)


def wifi_crystal_calibration(connections, logger, **kwargs):
    return _run("wifi_crystal_calibration", connections, logger, **kwargs)


def wifi_tx_calibration(connections, logger, **kwargs):
    return _run("wifi_tx_calibration", connections, logger, **kwargs)


def wifi_tx_calibration_finalize(connections, logger, **kwargs):
    return _run("wifi_tx_calibration_finalize", connections, logger, **kwargs)


def wifi_tx_verify(connections, logger, **kwargs):
    return _run("wifi_tx_verify", connections, logger, **kwargs)


def wifi_tx_verify_extract_evm(connections, logger, **kwargs):
    return _run("wifi_tx_verify_extract_evm", connections, logger, **kwargs)


def wifi_tx_verify_extract_freq_err(connections, logger, **kwargs):
    return _run("wifi_tx_verify_extract_freq_err", connections, logger, **kwargs)


def wifi_rx_verify(connections, logger, **kwargs):
    return _run("wifi_rx_verify", connections, logger, **kwargs)


def switch_wifi_to_bt(connections, logger, **kwargs):
    return _run("switch_wifi_to_bt", connections, logger, **kwargs)


def bt_calibration(connections, logger, **kwargs):
    return _run("bt_calibration", connections, logger, **kwargs)


def bt_tx_verify(connections, logger, **kwargs):
    return _run("bt_tx_verify", connections, logger, **kwargs)


def bt_tx_verify_extract_freq_err(connections, logger, **kwargs):
    return _run("bt_tx_verify_extract_freq_err", connections, logger, **kwargs)


def bt_rx_verify(connections, logger, **kwargs):
    return _run("bt_rx_verify", connections, logger, **kwargs)


def save_calibration_data(connections, logger, **kwargs):
    return _run("save_calibration_data", connections, logger, **kwargs)


def write_efuse(connections, logger, **kwargs):
    return _run("write_efuse", connections, logger, **kwargs)


def check_efuse_write(connections, logger, **kwargs):
    return _run("check_efuse_write", connections, logger, **kwargs)


def rf_mp_finish(connections, logger, **kwargs):
    return _run("rf_mp_finish", connections, logger, **kwargs)


def show_verify_summary(connections, logger, **kwargs):
    api = RFTestAPI(connections, logger)
    result = api.show_verify_summary(**kwargs)
    return result.ok, result.value


def sdk_programming(connections, logger, **kwargs):
    for _ in range(3):
        try:
            tool = AmebaPGTool(r"C:\tools\AmebaZII_PGTool.exe")
            status = tool.run_blocking()
            logger.debug(status.percent)
            logger.debug(status.success)
            if not status.success:
                return False, "FAIL"
            return True, "PASS"
        except Exception as e:
            logger.debug("programming failure!")
            time.sleep(1)
            continue
    else:
        return False, "FAIL"


def power_on(connections, logger, **kwargs):
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    port = customer_config.get("ps_port")
    ps = E3xxxController(
            interface="serial",
            resource=port,   # 或 /dev/ttyUSB0
            baudrate=9600
            )
    ps.connect()
    ps.set_voltage(3.3)
    ps.output_on()
    return True, "PASS"


def power_off(connections, logger, **kwargs):
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")

    port = customer_config.get("ps_port")
    ps = E3xxxController(
            interface="serial",
            resource=port,
            baudrate=9600
            )
    ps.output_off()
    ps.disconnect()
    return True, "PASS"


def power_cycle(connections, logger, **kwargs):
    layout_config = gl.get_value("layout_config")
    cells = layout_config.get("cells")[0]
    customer_config = cells.get("customer_config")
    port = customer_config.get("ps_port")
    ps = E3xxxController(
        interface="serial",
        resource=port,
        baudrate=9600
    )
    ps.output_off()
    time.sleep(1)
    ps.set_voltage(3.3)
    ps.output_on()
    return True, "PASS"

def load_pathloss_table_step(
    connections,
    logger,
    yaml_path: str,
    required_ports: list[int] | None = None,
    strict: bool = True,
    **kwargs,
):
    table = PathlossTable.load_or_empty(yaml_path)
    raw = getattr(table, "table", {}) or {}

    if not raw:
        msg = f"pathloss table is empty or not found: {yaml_path}"
        logger.error("[PATHLOSS] %s", msg)
        return (False, msg) if strict else (True, msg)

    wifi_ports = sorted((raw.get("wifi") or {}).keys())
    bt_ports = sorted((raw.get("bt") or {}).keys())

    if required_ports:
        missing = []
        for p in required_ports:
            key = f"port{int(p)}"
            if key not in (raw.get("wifi") or {}):
                missing.append(f"wifi:{key}")
            if key not in (raw.get("bt") or {}):
                missing.append(f"bt:{key}")

        if missing:
            msg = f"pathloss table missing required logical ports: {missing}, yaml={yaml_path}"
            logger.error("[PATHLOSS] %s", msg)
            return (False, msg) if strict else (True, msg)

    state = get_or_create_state()
    state.runtime.pathloss_yaml = yaml_path
    state.runtime.pathloss_table = table

    logger.info(
        "[PATHLOSS] loaded logical-port table: %s, wifi_ports=%s, bt_ports=%s",
        yaml_path,
        wifi_ports,
        bt_ports,
    )
    return True, "PASS"


def scan_dut(connections, logger, **kwargs):
    logger.debug(f"get current cell_id:{gl.get_current_cell_id()}\n")
    gl.set_value("error_code", kwargs.get("cell_name"))
    logger.debug(f'layout_config:{gl.get_value("layout_config")}')
    logger.debug(f"get cell_name:{kwargs.get('cell_name')}\n")
    logger.debug(f'layout_config:{gl.get_value("layout_config")}')
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
    return True, "PASS"
