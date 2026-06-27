from __future__ import annotations

from pathlib import Path

from src.libs.calibration.pathloss import PathlossTable
from src.libs.calibration.pathloss_plan import DEFAULT_PATHLOSS_PLAN
from src.libs.calibration.rate_normalizer import normalize_wifi_rate, normalize_bt_phy
from src.libs.models import StepResult
from src.libs.equipments.wt328ce.driver import WT328CEDriver


class PathlossCalibrationController:
    def __init__(self, connections, logger):
        self.connections = connections
        self.logger = logger
        self.wt = WT328CEDriver(connections, logger)
        self.station = getattr(connections, "station", None)

    def pathloss_calibration(
        self,
        output_yaml: str,
        ports: list[int],
        plan: dict | None = None,
        wifi_cal_power_dbm: float = 4.0,
        bt_cal_power_dbm: float = 2.0,
        overwrite: bool = True,
        wifi_port_map: dict | None = None,
        bt_port_map: dict | None = None,
        **kwargs,
    ) -> StepResult:
        self.wifi_port_map = wifi_port_map or {}
        self.bt_port_map = bt_port_map or {}
        plan = plan or DEFAULT_PATHLOSS_PLAN
        table = PathlossTable({}) if overwrite else PathlossTable.load_or_empty(output_yaml)

        for port in ports:
            self.logger.info(f"[PATHLOSS] start port={port}")

            for modulation, freq_list in plan.get("wifi", {}).items():
                for freq_mhz in freq_list:
                    loss_db = self._measure_wifi_pathloss(
                        port=port,
                        modulation=modulation,
                        freq_mhz=freq_mhz,
                        cal_power_dbm=wifi_cal_power_dbm,
                    )
                    table.set_loss("wifi", port, modulation, freq_mhz, loss_db)
                    self.logger.info(
                        f"[PATHLOSS][WIFI] port={port} mod={modulation} "
                        f"freq={freq_mhz} cal_power={wifi_cal_power_dbm:.2f} "
                        f"loss={loss_db:.2f}"
                    )

            for modulation, freq_list in plan.get("bt", {}).items():
                for freq_mhz in freq_list:
                    loss_db = self._measure_bt_pathloss(
                        port=port,
                        modulation=modulation,
                        freq_mhz=freq_mhz,
                        cal_power_dbm=bt_cal_power_dbm,
                    )
                    table.set_loss("bt", port, modulation, freq_mhz, loss_db)
                    self.logger.info(
                        f"[PATHLOSS][BT] port={port} mod={modulation} "
                        f"freq={freq_mhz} cal_power={bt_cal_power_dbm:.2f} "
                        f"loss={loss_db:.2f}"
                    )

        table.save_yaml(output_yaml)
        return StepResult.success(str(Path(output_yaml)))

    def _wifi_pathloss_profile(self, modulation: str) -> tuple[int, float, str]:
        mod = normalize_wifi_rate(modulation)

        # demod values align with your existing mp sequence:
        # 54M -> 0, HT20/HT40 -> 2, 11M -> 3
        if mod == "11M":
            return 3, 40e6, "wifi_11m.wv"
        if mod == "54M":
            return 0, 80e6, "wifi_54m.wv"
        if mod == "HT20-MCS7":
            return 2, 80e6, "wifi_ht20_mcs7.wv"
        if mod == "HT40-MCS7":
            return 2, 160e6, "wifi_ht40_mcs7.wv"

        raise ValueError(f"unsupported wifi modulation for pathloss calibration: {mod}")

    def _bt_pathloss_profile(self, modulation: str) -> tuple[int, int, str]:
        mod = normalize_bt_phy(modulation)

        # demod 9 seems to be your BLE default in driver
        # phy values need to match WT analyzer setting
        if mod == "BLE1M":
            return 9, 1, "ble_1m.wv"
        if mod == "BLE2M":
            return 9, 2, "ble_2m.wv"

        raise ValueError(f"unsupported bt modulation for pathloss calibration: {mod}")

    def _resolve_path_ports(self, port: int, mapping: dict | None, default_tx: int = 0, default_rx: int = 1) -> tuple[
        int, int]:
        if not mapping:
            return int(default_tx), int(default_rx)

        item = mapping.get(port)
        if item is None:
            item = mapping.get(str(port))

        if not item:
            return int(default_tx), int(default_rx)

        tx_port = item.get("tx_port", default_tx)
        rx_port = item.get("rx_port", default_rx)
        return int(tx_port), int(rx_port)

    def _measure_wifi_pathloss(self, port: int, modulation: str, freq_mhz: int, cal_power_dbm: float) -> float:
        mod = normalize_wifi_rate(modulation)
        measured_power_dbm = self._measure_wifi_cable_power(
            port=port,
            modulation=mod,
            freq_mhz=freq_mhz,
            cal_power_dbm=cal_power_dbm,
        )
        loss_db = float(cal_power_dbm) - float(measured_power_dbm)
        return round(loss_db, 2)

    def _measure_bt_pathloss(self, port: int, modulation: str, freq_mhz: int, cal_power_dbm: float) -> float:
        mod = normalize_bt_phy(modulation)
        measured_power_dbm = self._measure_bt_cable_power(
            port=port,
            modulation=mod,
            freq_mhz=freq_mhz,
            cal_power_dbm=cal_power_dbm,
        )
        loss_db = float(cal_power_dbm) - float(measured_power_dbm)
        return round(loss_db, 2)

    def _get_wt(self):
        # 1) prefer already-connected WT object from runtime connections
        wt = getattr(self.connections, "wt", None)
        if wt is not None:
            return wt

        # 2) fallback: build from connection config
        wt_ip = None
        for attr in ("wt_ip", "tester_ip", "ip"):
            if hasattr(self.connections, attr):
                wt_ip = getattr(self.connections, attr)
                if wt_ip:
                    break

        if not wt_ip:
            raise RuntimeError("WT connection is not available: no connections.wt and no wt_ip/tester_ip/ip found")

        from src.libs.equipments.wt328ce.driver import WT328CEDriver

        wt = WT328CEDriver(ip=str(wt_ip), logger=self.logger)
        wt.connect()
        return wt

    def _measure_wifi_cable_power(self, port: int, modulation: str, freq_mhz: int, cal_power_dbm: float) -> float:

        demod, sample_rate_hz, wave_file = self._wifi_pathloss_profile(modulation)

        wifi_port_map = getattr(self, "wifi_port_map", None)
        tx_port, rx_port = self._resolve_path_ports(
            port=port,
            mapping=wifi_port_map,
            default_tx=0,
            default_rx=1,
        )

        self.logger.info(
            "[PATHLOSS][WIFI] measure path_port=%s tx_port=%s rx_port=%s mod=%s freq=%s cal_power=%.2f",
            port, tx_port, rx_port, modulation, freq_mhz, cal_power_dbm
        )

        self.wt.wifi.start_wifi_vsg(
            rf_ports=[int(tx_port)],
            freq_mhz=int(freq_mhz),
            sample_rate_hz=float(sample_rate_hz),
            packets=0,
            wave_file=wave_file,
            power_list=[float(cal_power_dbm)],
            pathloss_list=[0.0],
        )

        try:
            measured_power_dbm = wt.wifi.measure_wifi_power_dbm(
                rf_port=int(rx_port),
                freq_mhz=int(freq_mhz),
                sample_rate_hz=float(sample_rate_hz),
                demod=int(demod),
                target_power_dbm=float(cal_power_dbm),
                pathloss_db=0.0,
                use_power_field="power_frame",
                use_full_product_style=False,
            )

            self.logger.info(
                "[PATHLOSS][WIFI] measured path_port=%s tx_port=%s rx_port=%s freq=%s power=%.2f",
                port, tx_port, rx_port, freq_mhz, measured_power_dbm
            )
            return float(measured_power_dbm)
        finally:
            try:
                wt.wifi.stop_vsg()
            except Exception:
                pass

    def _measure_bt_cable_power(self, port: int, modulation: str, freq_mhz: int, cal_power_dbm: float) -> float:

        demod, phy, wave_name = self._bt_pathloss_profile(modulation)

        bt_port_map = getattr(self, "bt_port_map", None)
        tx_port, rx_port = self._resolve_path_ports(
            port=port,
            mapping=bt_port_map,
            default_tx=0,
            default_rx=1,
        )

        self.logger.info(
            "[PATHLOSS][BT] measure path_port=%s tx_port=%s rx_port=%s mod=%s freq=%s cal_power=%.2f",
            port, tx_port, rx_port, modulation, freq_mhz, cal_power_dbm
        )

        self.wt.bt.start_bt_vsg(
            freq_mhz=int(freq_mhz),
            power_dbm=float(cal_power_dbm),
            rf_port=int(tx_port),
            pathloss_db=0.0,
            wave_name=wave_name,
            packets=0,
            demod=int(demod),
        )

        try:
            summary = wt.bt.measure_bt_tx_summary(
                freq_mhz=int(freq_mhz),
                max_power_dbm=float(cal_power_dbm + 5.0),
                rf_port=int(rx_port),
                pathloss_db=0.0,
                demod=int(demod),
                phy=int(phy),
                payload_type=0,
                use_agc=True,
                full_product_style=False,
            )

            if summary.power_dbm is None:
                raise RuntimeError(f"BT cable measure failed: path_port={port}, freq={freq_mhz}, mod={modulation}")

            self.logger.info(
                "[PATHLOSS][BT] measured path_port=%s tx_port=%s rx_port=%s freq=%s power=%.2f",
                port, tx_port, rx_port, freq_mhz, summary.power_dbm
            )
            return float(summary.power_dbm)
        finally:
            try:
                wt.bt.stop_vsg()
            except Exception:
                pass
