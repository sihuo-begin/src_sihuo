from __future__ import annotations


class RTL8722FDutInterface:
    def __init__(self, connections, logger):
        self.connections = connections
        self.logger = logger
        self.dut = self._resolve_dut(connections)

    def _resolve_dut(self, connections):
        if hasattr(connections, "dut"):
            return connections.dut
        if hasattr(connections, "chip"):
            return connections.chip
        raise AttributeError("connections has no dut/chip object")

    def _fallback_cmd(self, command: str):
        self.logger.info("DUT cmd: %s", command)
        if hasattr(self.dut, "command"):
            return self.dut.command(command)
        if hasattr(self.dut, "send"):
            self.dut.send(command)
            if hasattr(self.dut, "recv"):
                return self.dut.recv()
            return ""
        raise AttributeError("dut object has no command/write interface")

    # ---------- WiFi MP ----------
    def wifi_mp_start(self):
        if hasattr(self.dut, "wifi_mp_start"):
            return self.dut.wifi_mp_start()
        return self._fallback_cmd("iwpriv mp_start")

    def wifi_mp_stop(self):
        if hasattr(self.dut, "wifi_mp_stop"):
            return self.dut.wifi_mp_stop()
        return self._fallback_cmd("iwpriv mp_stop")

    def wifi_set_channel(self, ch: int):
        if hasattr(self.dut, "wifi_set_channel"):
            return self.dut.wifi_set_channel(ch)
        return self._fallback_cmd(f"iwpriv mp_channel {ch}")

    def wifi_set_rate(self, rate: str):
        if hasattr(self.dut, "wifi_set_rate"):
            return self.dut.wifi_set_rate(rate)
        return self._fallback_cmd(f"iwpriv mp_rate {rate}")

    def wifi_set_bandwidth(self, bandwidth: str):
        if hasattr(self.dut, "wifi_set_bandwidth"):
            return self.dut.wifi_set_bandwidth(bandwidth)
        return self._fallback_cmd(f"iwpriv mp_ctx background {bandwidth}")

    def wifi_set_txpower(self, patha: int = 64, pathb: int = 0):
        if hasattr(self.dut, "wifi_set_txpower"):
            return self.dut.wifi_set_txpower(patha=patha, pathb=pathb)
        return self._fallback_cmd(f"iwpriv mp_txpower patha={patha},pathb={pathb}")

    def wifi_start_hwtx(self, period: int, length: int, count: int = 0):
        if hasattr(self.dut, "wifi_start_hwtx"):
            return self.dut.wifi_start_hwtx(period=period, length=length, count=count)
        return self._fallback_cmd(f"iwpriv mp_hwtx period={period},len={length},count={count}")

    def wifi_stop_hwtx(self):
        if hasattr(self.dut, "wifi_stop_hwtx"):
            return self.dut.wifi_stop_hwtx()
        return self._fallback_cmd("iwpriv mp_ctx stop")

    def wifi_read_thermal(self):
        if hasattr(self.dut, "wifi_read_thermal"):
            return self.dut.wifi_read_thermal()
        return self._fallback_cmd("iwpriv mp_ther")

    def wifi_set_xcap(self, xcap: int):
        if hasattr(self.dut, "wifi_set_xcap"):
            return self.dut.wifi_set_xcap(xcap)
        return self._fallback_cmd(f"iwpriv mp_phypara xcap={xcap}")

    def wifi_start_arx(self):
        if hasattr(self.dut, "wifi_start_arx"):
            return self.dut.wifi_start_arx()
        return self._fallback_cmd("iwpriv mp_arx start")

    def wifi_stop_arx(self):
        if hasattr(self.dut, "wifi_stop_arx"):
            return self.dut.wifi_stop_arx()
        return self._fallback_cmd("iwpriv mp_arx stop")

    def wifi_reset_stats(self):
        if hasattr(self.dut, "wifi_reset_stats"):
            return self.dut.wifi_reset_stats()
        return self._fallback_cmd("iwpriv mp_reset_stats")

    def wifi_get_arx_report(self):
        if hasattr(self.dut, "wifi_get_arx_report"):
            return self.dut.wifi_get_arx_report()
        return self._fallback_cmd("iwpriv mp_arx phy")

    # ---------- WiFi <-> BLE Switch ----------
    def bt_power_on(self):
        if hasattr(self.dut, "bt_power_on"):
            return self.dut.bt_power_on()
        return self._fallback_cmd("ATM2=bt_power_on")

    def bt_grant_bt(self):
        if hasattr(self.dut, "bt_grant_bt"):
            return self.dut.bt_grant_bt()
        return self._fallback_cmd("ATM2=gnt_bt,bt")

    def bt_grant_wifi(self):
        if hasattr(self.dut, "bt_grant_wifi"):
            return self.dut.bt_grant_wifi()
        return self._fallback_cmd("ATM2=gnt_bt,wifi")

    def bt_bridge_open(self):
        if hasattr(self.dut, "bt_bridge_open"):
            return self.dut.bt_bridge_open()
        return self._fallback_cmd("ATM2=bridge")

    def bt_bridge_close(self):
        if hasattr(self.dut, "bt_bridge_close"):
            return self.dut.bt_bridge_close()
        return self._fallback_cmd("ATM2=bridge_close")
