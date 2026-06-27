from __future__ import annotations

from src.libs.models import StepResult
from src.libs.chip.rtl8722f.state_store import get_or_create_state, reset_state
from src.libs.chip.rtl8722f.wifi_prod_controller import WifiProdController
from src.libs.chip.rtl8722f.bt_prod_controller import BtProdController
from src.libs.chip.rtl8722f.efuse_mapper import build_efuse_image_from_state, build_write_commands
from src.libs.chip.rtl8722f.efuse_writer import (
    execute_write_commands,
    dump_realmap,
    compare_realmap_with_image,
)
from src.libs.chip.rtl8720.user_prod_controller import UserProdController


DEFAULT_EFUSE_IMAGE = bytes([
    0x50, 0x50, 0x50, 0x50, 0x50, 0x50,   # 0x20 ~ 0x25
    0x50, 0x50, 0x50, 0x50, 0x50,         # 0x26 ~ 0x2A
    0x02,                                 # 0x2B
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,   # 0x2C ~ 0x31
    0x50, 0x50, 0x50, 0x50, 0x50, 0x50,   # 0x32 ~ 0x37
    0x50, 0x50, 0x50, 0x50, 0x50, 0x50,   # 0x38 ~ 0x3D
    0x50, 0x50,                           # 0x3E ~ 0x3F
    0x02,                                 # 0x40
])


class RFTestAPI:
    """
    Final RF test API facade.

    Entry shape:
        steps -> RFTestAPI -> wifi/bt controller -> dut/sdk/wt -> state
    """

    def __init__(self, connections, logger):
        self.connections = connections
        self.logger = logger
        self.wifi = WifiProdController(connections, logger)
        self.bt = BtProdController(connections, logger)
        self.user_prod = UserProdController(connections, logger)

    # ------------------------------------------------------------------
    # WiFi flow
    # ------------------------------------------------------------------
    def rf_mp_init(self, **kwargs) -> StepResult:
        reset_state()
        return self.wifi.rf_mp_init()

    def wifi_read_thermal(self, **kwargs) -> StepResult:
        return self.wifi.wifi_read_thermal(**kwargs)

    def rf_preheat(self, **kwargs) -> StepResult:
        return self.wifi.rf_preheat(**kwargs)

    def wifi_crystal_calibration(self, **kwargs) -> StepResult:
        return self.wifi.wifi_crystal_calibration(**kwargs)

    def wifi_tx_calibration(self, **kwargs) -> StepResult:
        return self.wifi.wifi_tx_calibration(**kwargs)

    def wifi_tx_calibration_finalize(self, **kwargs) -> StepResult:
        return self.wifi.wifi_tx_calibration_finalize()

    def wifi_tx_verify(self, **kwargs) -> StepResult:
        return self.wifi.wifi_tx_verify(**kwargs)

    def wifi_tx_verify_extract_evm(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        value = state.wifi.tx_verify_evm
        if value is None:
            return StepResult.failure("no_wifi_tx_verify_evm")
        return StepResult.success(value)

    def wifi_tx_verify_extract_freq_err(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        value = state.wifi.tx_verify_freq_err_hz
        if value is None:
            return StepResult.failure("no_wifi_tx_verify_freq_err")
        return StepResult.success(value)

    def wifi_rx_verify(self, **kwargs) -> StepResult:
        return self.wifi.wifi_rx_verify(**kwargs)

    # ------------------------------------------------------------------
    # WiFi -> BT switch
    # ------------------------------------------------------------------
    def switch_wifi_to_bt(self, **kwargs) -> StepResult:
        """
        DUT path switch by command, then BT SDK init by DLL.
        """
        return self.bt.switch_wifi_to_bt(**kwargs)

    # ------------------------------------------------------------------
    # BT flow
    # ------------------------------------------------------------------
    def bt_calibration(self, **kwargs) -> StepResult:
        return self.bt.bt_calibration(**kwargs)

    def bt_tx_verify(self, **kwargs) -> StepResult:
        return self.bt.bt_tx_verify(**kwargs)

    def bt_tx_verify_extract_freq_err(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        freq = state.bt.tx_verify_freq_err_hz
        if freq is None:
            metrics = state.bt.tx_verify_last.get("metrics", {})
            freq = metrics.get("init_freq_err_hz")
        if freq is None:
            return StepResult.failure("no_bt_tx_verify_freq_err")

        return StepResult.success(freq)

    def bt_rx_verify(self, **kwargs) -> StepResult:
        return self.bt.bt_rx_verify(**kwargs)

    def bt_read_thermal(self, **kwargs) -> StepResult:
        return self.bt.bt_read_thermal(**kwargs)

    # ------------------------------------------------------------------
    # efuse / save
    # ------------------------------------------------------------------
    def save_calibration_data(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        try:
            wifi_mac = "00:11:22:33:44:55"
            bt_mac = "00:11:22:33:44:66"

            image = build_efuse_image_from_state(
                state,
                wifi_mac=wifi_mac,
                bt_mac=bt_mac,
            )
            state.efuse.image = image
            state.efuse.saved = True
            state.runtime.phase = "calibration_saved"
            return StepResult.success("PASS")
        except Exception as exc:
            self.logger.exception("save_calibration_data failed: %s", exc)
            return StepResult.failure(str(exc))

    def write_efuse(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        if not state.efuse.image:
            return StepResult.failure("efuse_image_not_ready")

        try:
            commands = build_write_commands(state.efuse.image)
            outputs = execute_write_commands(
                connections=self.connections,
                logger=self.logger,
                commands=commands,
            )

            state.efuse.write_commands = commands
            state.efuse.write_outputs = outputs
            state.efuse.written = True
            state.runtime.phase = "efuse_written"

            return StepResult.success(outputs)
        except Exception as exc:
            self.logger.exception("write_efuse failed: %s", exc)
            return StepResult.failure(str(exc))

    def check_efuse_write(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        if not state.efuse.image:
            return StepResult.failure("efuse_image_not_ready")

        try:
            realmap = dump_realmap(
                connections=self.connections,
                logger=self.logger,
            )
            ok, diff = compare_realmap_with_image(realmap, state.efuse.image)

            state.efuse.realmap_dump = realmap
            state.efuse.checked = bool(ok)
            state.runtime.phase = 'wifi_finished'

            if ok:
                return StepResult.success(True)
            return StepResult.failure(diff)
        except Exception as exc:
            self.logger.exception("check_efuse_write failed: %s", exc)
            return StepResult.failure(str(exc))

    # ------------------------------------------------------------------
    # post-efuse connectivity check
    # ------------------------------------------------------------------
    def wt_wifi_connect(self, **kwargs) -> StepResult:
        return self.user_prod.wt_wifi_connect(
            ssid=kwargs.get("ssid", ""),
            password=kwargs.get("password", ""),
            bssid=kwargs.get("bssid"),
        )

    def wt_wifi_get_rssi(self, **kwargs) -> StepResult:
        return self.user_prod.wt_wifi_get_rssi()

    def wt_wifi_disconnect(self, **kwargs) -> StepResult:
        return self.user_prod.wt_wifi_disconnect()

    def wt_bt_peripheral_start(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_peripheral_start()

    def wt_bt_central_start(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_central_start()

    def wt_bt_connect(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_connect()

    def wt_bt_check_link(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_check_link()

    def wt_bt_disconnect(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_disconnect(
            conn_id=kwargs.get("conn_id"),
        )

    def wt_bt_stop(self, **kwargs) -> StepResult:
        return self.user_prod.wt_bt_stop()

    def show_verify_summary(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        parts = []

        # WiFi verify status
        parts.append("wifi_tx=ok" if state.wifi.tx_verify_last else "wifi_tx=na")
        parts.append("wifi_rx=ok" if state.wifi.rx_verify_last else "wifi_rx=na")

        # BT verify status
        parts.append("bt_tx=ok" if state.bt.tx_verify_last else "bt_tx=na")
        parts.append("bt_rx=ok" if state.bt.rx_verify_last else "bt_rx=na")

        # WiFi calibration summary
        if getattr(state.wifi, "xcap_final", None) is not None:
            parts.append(f"xcap=0x{state.wifi.xcap_final:02X}")
        if getattr(state.wifi, "thermal_wifi", None) is not None:
            parts.append(f"wifi_thermal=0x{state.wifi.thermal_wifi:02X}")
        elif getattr(state.wifi, "thermal_after_preheat", None) is not None:
            parts.append(f"wifi_thermal=0x{state.wifi.thermal_after_preheat:02X}")

        # BT calibration summary
        if getattr(state.bt, "gain_k", None) is not None:
            parts.append(f"bt_gaink=0x{state.bt.gain_k:02X}")

        flatness = list(getattr(state.bt, "flatness_bytes", []) or [])
        if flatness:
            flatness_str = "[" + ",".join(f"0x{x:02X}" for x in flatness) + "]"
            parts.append(f"bt_flatness={flatness_str}")

        if getattr(state.bt, "thermal_bt", None) is not None:
            parts.append(f"bt_thermal=0x{state.bt.thermal_bt:02X}")

        if getattr(state.bt, "valid_bits", None) is not None:
            parts.append(f"bt_valid=0x{state.bt.valid_bits:02X}")

        # efuse/save/check status
        if getattr(state.efuse, "saved", False):
            parts.append("cal_saved=ok")
        else:
            parts.append("cal_saved=na")

        if getattr(state.efuse, "written", False):
            parts.append("efuse_written=ok")
        else:
            parts.append("efuse_written=na")

        if getattr(state.efuse, "checked", False):
            parts.append("efuse_check=ok")
        else:
            parts.append("efuse_check=na")

        return StepResult.success(",".join(parts))

    # ------------------------------------------------------------------
    # finish
    # ------------------------------------------------------------------
    def rf_mp_finish(self, **kwargs) -> StepResult:
        """
        If current path still stays in BT, switch back to WiFi first.
        Then stop WiFi MP mode.
        """
        state = get_or_create_state()

        try:
            if state.runtime.active_interface == "bt":
                leave_result = self.bt.leave_bt_to_wifi()
                if not leave_result.ok:
                    return leave_result

            return self.wifi.rf_mp_finish()
        except Exception as exc:
            self.logger.exception("rf_mp_finish failed: %s", exc)
            return StepResult.failure(str(exc))
