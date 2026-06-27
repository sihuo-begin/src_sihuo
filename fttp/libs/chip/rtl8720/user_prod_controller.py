from __future__ import annotations

from src.libs.models import StepResult
from src.libs.chip.rtl8720.wifi import RTL8720MP
from src.libs.chip.rtl8720.bt import RTL8720BT


class UserProdController:
    """
    Post-efuse user functionality checks for RTL8720 on a shared single DUT UART.

    Important:
      - WiFi and BT share the same DUT connection
      - They must NOT stay active at the same time
      - BT module has a background rx thread, so we must switch ownership explicitly
    """

    def __init__(self, connections, logger):
        self.connections = connections
        self.logger = logger

        self.dut_connection = self._get_dut_connection("sta")
        self.ap_connection = self._get_dut_connection("ap")

        self._wifi = None
        self._bt = None
        self._bt_conn_id = None

    def _get_dut_connection(self, connection_type):
        if isinstance(self.connections, dict):
            if "sta" == connection_type:
                return self.connections["dut"]
            if "ap" == connection_type:
                return self.connections["ap"]
        raise KeyError("DUT connection not found in connections")

    def _close_wifi(self):
        if self._wifi is not None:
            try:
                self._wifi.close()
            except Exception as exc:
                self.logger.warning("close wifi module failed: %s", exc)
            finally:
                self._wifi = None

    def _close_bt(self):
        if self._bt is not None:
            try:
                self._bt.close()
            except Exception as exc:
                self.logger.warning("close bt module failed: %s", exc)
            finally:
                self._bt = None
                self._bt_conn_id = None

    def _ensure_wifi(self) -> RTL8720MP:
        if self._bt is not None:
            self._close_bt()

        if self._wifi is None:
            self._wifi = RTL8720MP(self.dut_connection, self.ap_connection)

        return self._wifi

    def _ensure_bt(self) -> RTL8720BT:
        if self._wifi is not None:
            self._close_wifi()

        if self._bt is None:
            self._bt = RTL8720BT(self.dut_connection, self.ap_connection)

        return self._bt

    def close(self):
        self._close_wifi()
        self._close_bt()

    # ------------------------------------------------------------------
    # WiFi
    # ------------------------------------------------------------------
    def wt_wifi_connect(self, *, ssid: str, password: str, bssid=None) -> StepResult:
        try:
            if not ssid:
                return StepResult.failure("missing_ssid")

            wifi = self._ensure_wifi()
            wifi.send_enter_ap()
            wifi.sta_connect(ssid=ssid, psk=password, bssid=bssid)
            return StepResult.success(True)
        except Exception as exc:
            self.logger.exception("wt_wifi_connect failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_wifi_get_rssi(self) -> StepResult:
        try:
            wifi = self._ensure_wifi()
            rssi = wifi.sta_get_rssi()
            return StepResult.success(rssi)
        except Exception as exc:
            self.logger.exception("wt_wifi_get_rssi failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_wifi_disconnect(self) -> StepResult:
        try:
            wifi = self._ensure_wifi()
            wifi.sta_disconnect()
            return StepResult.success(True)
        except Exception as exc:
            self.logger.exception("wt_wifi_disconnect failed: %s", exc)
            return StepResult.failure(str(exc))

    # ------------------------------------------------------------------
    # BT
    # ------------------------------------------------------------------
    def wt_bt_peripheral_start(self) -> StepResult:
        try:
            bt = self._ensure_bt()
            addr = bt.peripheral_start()
            return StepResult.success(addr)
        except Exception as exc:
            self.logger.exception("wt_bt_peripheral_start failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_bt_central_start(self) -> StepResult:
        try:
            bt = self._ensure_bt()
            addr = bt.central_start()
            return StepResult.success(addr if addr else True)
        except Exception as exc:
            self.logger.exception("wt_bt_central_start failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_bt_connect(self) -> StepResult:
        try:
            bt = self._ensure_bt()
            conn_id = bt.connect()
            self._bt_conn_id = conn_id
            return StepResult.success(conn_id)
        except Exception as exc:
            self.logger.exception("wt_bt_connect failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_bt_check_link(self) -> StepResult:
        try:
            bt = self._ensure_bt()
            info = bt.get_connection_info()
            if "active link num 1" not in info:
                return StepResult.failure(info)
            return StepResult.success(info)
        except Exception as exc:
            self.logger.exception("wt_bt_check_link failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_bt_disconnect(self, *, conn_id=None) -> StepResult:
        try:
            bt = self._ensure_bt()
            use_conn_id = self._bt_conn_id if conn_id is None else conn_id
            if use_conn_id is None:
                return StepResult.failure("missing_conn_id")

            bt.disconnect(use_conn_id)
            self._bt_conn_id = None
            return StepResult.success(True)
        except Exception as exc:
            self.logger.exception("wt_bt_disconnect failed: %s", exc)
            return StepResult.failure(str(exc))

    def wt_bt_stop(self) -> StepResult:
        try:
            bt = self._ensure_bt()
            errors = []

            try:
                bt.central_stop()
            except Exception as exc:
                errors.append(f"central_stop: {exc}")

            try:
                bt.peripheral_stop()
            except Exception as exc:
                errors.append(f"peripheral_stop: {exc}")

            self._bt_conn_id = None

            if errors:
                msg = "; ".join(errors)
                self.logger.warning("wt_bt_stop partial failure: %s", msg)
                return StepResult.failure(msg)

            return StepResult.success(True)
        except Exception as exc:
            self.logger.exception("wt_bt_stop failed: %s", exc)
            return StepResult.failure(str(exc))
