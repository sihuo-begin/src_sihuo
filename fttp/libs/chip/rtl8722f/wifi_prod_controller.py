from __future__ import annotations

import re
import time
from copy import deepcopy

from src.libs.models import StepResult
from src.libs.chip.rtl8722f.state_store import get_or_create_state
from src.libs.chip.rtl8722f.dut_interface import RTL8722FDutInterface
from src.libs.equipments.wt328ce.driver import WT328CEDriver
from src.libs.calibration.pathloss import PathlossTable
from src.libs.calibration.rate_normalizer import normalize_wifi_rate


class WifiProdController:
    """
    WiFi production controller.

    Rules:
    - pathloss is loaded once into state.runtime.pathloss_table by test step
    - controller public methods auto-resolve pathloss when pathloss_db is None
    - helper methods only receive already-resolved pathloss_db
    """

    WIFI_TX_CAL_LAYOUT = {
        "2g_ht40": {
            "measured_channels": [4, 10],
            "all_channels": [1, 4, 7, 10, 13],
            "table_family": "2g",
            "rate_key": "ht40",
        },
        "2g_11b": {
            "measured_channels": [4, 10],
            "all_channels": [1, 4, 7, 10, 13, 14],
            "table_family": "2g",
            "rate_key": "11b",
        },
        "2g_54m": {
            "measured_channels": [7],
            "all_channels": [1, 4, 7, 10, 13],
            "table_family": "2g",
            "rate_key": "11g",
        },
        "2g_ht20": {
            "measured_channels": [7],
            "all_channels": [1, 4, 7, 10, 13],
            "table_family": "2g",
            "rate_key": "ht20",
        },
        "5g_ht40_band1": {
            "measured_channels": [38, 46],
            "all_channels": [36, 38, 40, 44, 46, 48],
            "table_family": "5g",
            "rate_key": "ht40",
        },
        "5g_ht40_band2": {
            "measured_channels": [54, 62],
            "all_channels": [52, 54, 56, 60, 62, 64],
            "table_family": "5g",
            "rate_key": "ht40",
        },
        "5g_ht40_band3": {
            "measured_channels": [102, 142],
            "all_channels": [100, 102, 104, 106, 108, 110, 112, 116, 118, 120, 122, 124, 126, 128, 132, 134, 136, 140, 142, 144],
            "table_family": "5g",
            "rate_key": "ht40",
        },
        "5g_ht40_band4": {
            "measured_channels": [151, 175],
            "all_channels": [149, 151, 153, 157, 159, 161, 165, 167, 169, 173, 175, 177],
            "table_family": "5g",
            "rate_key": "ht40",
        },
        "5g_54m_band3": {
            "measured_channels": [100],
            "all_channels": [36, 44, 60, 100, 120, 165],
            "table_family": "5g",
            "rate_key": "11g",
        },
        "5g_ht20_band3": {
            "measured_channels": [100],
            "all_channels": [36, 48, 100, 144, 177],
            "table_family": "5g",
            "rate_key": "ht20",
        },
    }

    def __init__(self, connections, logger):
        self.connections = connections
        self.logger = logger
        self.dut = RTL8722FDutInterface(connections, logger)
        self.wt = WT328CEDriver(logger)

    # ---------------------------------------------------------------------
    # basic flow
    # ---------------------------------------------------------------------
    def rf_mp_init(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        try:
            self.dut.wifi_mp_start()
            state.runtime.active_interface = "wifi"
            state.runtime.phase = "wifi_initialized"
            return StepResult.success("wifi_mp_init_ok")
        except Exception as exc:
            self.logger.exception("rf_mp_init failed: %s", exc)
            return StepResult.failure(str(exc))

    def rf_preheat(
        self,
        duration_sec: int = 1,
        channel: int = 7,
        rate: str = "54M",
        patha: int = 64,
        pathb: int = 0,
        **kwargs,
    ) -> StepResult:
        state = get_or_create_state()
        try:
            self.dut.wifi_set_channel(channel)
            self.dut.wifi_set_rate(rate)
            self.dut.wifi_set_txpower(patha=patha, pathb=pathb)
            self.dut.wifi_start_hwtx(period=100, length=1500, count=0)
            time.sleep(duration_sec)
            self.dut.wifi_stop_hwtx()

            state.wifi.preheated = True
            state.runtime.phase = "wifi_preheated"
            return StepResult.success(duration_sec)
        except Exception as exc:
            self.logger.exception("rf_preheat failed: %s", exc)
            return StepResult.failure(str(exc))

    def wifi_read_thermal(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        try:
            # replace with your actual DUT thermal read
            thermal = 0x00
            state.wifi.thermal_wifi = thermal
            return StepResult.success(str(thermal))
        except Exception as exc:
            return StepResult.failure(str(exc))

    # ---------------------------------------------------------------------
    # helpers
    # ---------------------------------------------------------------------
    def _safe_int_from_text(self, value) -> int | None:
        try:
            m = re.search(r"-?\d+", str(value))
            return int(m.group(0)) if m else None
        except Exception:
            return None

    def _get_wifi_pathloss(self, rf_port: int, rate: str, freq_mhz: int) -> float:
        state = get_or_create_state()

        table = getattr(state.runtime, "pathloss_table", None)
        yaml_path = getattr(state.runtime, "pathloss_yaml", None)

        if table is None and yaml_path:
            self.logger.info("[PATHLOSS] lazy load from yaml_path=%s", yaml_path)
            table = PathlossTable.load_or_empty(yaml_path)
            state.runtime.pathloss_table = table

        if table is None:
            self.logger.warning(
                "[PATHLOSS] no table loaded, use 0.0; rf_port=%s rate=%s freq=%s",
                rf_port, rate, freq_mhz
            )
            return 0.0

        mod_key = normalize_wifi_rate(rate)
        loss = float(table.get_loss("wifi", rf_port, mod_key, freq_mhz, default=0.0))
        self.logger.info(
            "[PATHLOSS] wifi rf_port=%s rate=%s mod_key=%s freq=%s loss=%.2f",
            rf_port, rate, mod_key, freq_mhz, loss
        )
        return loss

    def _read_initial_power_table(self) -> dict:
        state = get_or_create_state()
        if getattr(state.wifi, "initial_power_table", None):
            return state.wifi.initial_power_table

        return {
            "2g": {
                "ht40": {ch: 0x50 for ch in range(1, 15)},
                "ht20": {ch: 0 for ch in range(1, 15)},
                "11g": {ch: 2 for ch in range(1, 15)},
                "11b": {ch: 0x50 for ch in range(1, 15)},
                "offset": {"ht20": 0, "ag": 4, "offset_from_rom_ht20": 0, "offset_from_rom_ag": 2},
            },
            "5g": {
                "ht40": {ch: 0x50 for ch in [
                    36, 38, 40, 44, 46, 48,
                    52, 54, 56, 60, 62, 64,
                    100, 102, 104, 106, 108, 110, 112, 116, 118, 120, 122, 124, 126, 128, 132, 134, 136, 140, 142, 144,
                    149, 151, 153, 157, 159, 161, 165, 167, 169, 173, 175, 177
                ]},
                "ht20": {ch: 0 for ch in [
                    36, 38, 40, 44, 46, 48,
                    52, 54, 56, 60, 62, 64,
                    100, 102, 104, 106, 108, 110, 112, 116, 118, 120, 122, 124, 126, 128, 132, 134, 136, 140, 142, 144,
                    149, 151, 153, 157, 159, 161, 165, 167, 169, 173, 175, 177
                ]},
                "11g": {ch: 2 for ch in [
                    36, 38, 40, 44, 46, 48,
                    52, 54, 56, 60, 62, 64,
                    100, 102, 104, 106, 108, 110, 112, 116, 118, 120, 122, 124, 126, 128, 132, 134, 136, 140, 142, 144,
                    149, 151, 153, 157, 159, 161, 165, 167, 169, 173, 175, 177
                ]},
                "offset": {"ht20": 0, "ag": 4, "offset_from_rom_ht20": 0, "offset_from_rom_ag": 2},
            },
        }

    def _wifi_rx_verify_profile(self, rate: str) -> tuple[float, str]:
        rate_norm = str(rate).strip().upper()

        if rate_norm == "11M":
            return 40e6, "11 Mbps(CCK).bwv"

        if rate_norm == "HT20-MCS0":
            return 80e6, "HT20-MCS0.bwv"

        if rate_norm == "HT40-MCS7":
            return 160e6, "HT40-MCS7.bwv"

        raise ValueError(f"no tester waveform available for wifi rx verify rate: {rate}")

    def _normalize_rate_key(self, rate: str) -> str:
        r = str(rate).upper()
        if r in ("HT40-MCS7", "HT40-7", "MCS7-B40", "MCS7_B40"):
            return "ht40"
        if r in ("HT20-MCS7", "HT20-7", "MCS7-B20", "MCS7_B20"):
            return "ht20"
        if r in ("11M", "CCK-11M", "CCK11M"):
            return "11b"
        if r in ("54M", "OFDM54M", "108"):
            return "11g"
        return r.lower()

    def _resolve_table_family(self, channel: int) -> str:
        return "2g" if channel <= 14 else "5g"

    def _resolve_layout_key(self, channel: int, rate: str) -> str:
        rate_key = self._normalize_rate_key(rate)
        if channel <= 14:
            if rate_key == "ht40":
                return "2g_ht40"
            if rate_key == "11b":
                return "2g_11b"
            if rate_key == "11g":
                return "2g_54m"
            if rate_key == "ht20":
                return "2g_ht20"
        else:
            if rate_key == "ht40":
                if 36 <= channel <= 48:
                    return "5g_ht40_band1"
                if 52 <= channel <= 64:
                    return "5g_ht40_band2"
                if 100 <= channel <= 144:
                    return "5g_ht40_band3"
                return "5g_ht40_band4"
            if rate_key == "11g":
                return "5g_54m_band3"
            if rate_key == "ht20":
                return "5g_ht20_band3"

        raise ValueError(f"unsupported calibration layout for channel={channel}, rate={rate}")

    def _get_initial_index(self, family: str, rate_key: str, channel: int) -> int:
        state = get_or_create_state()
        table = state.wifi.initial_power_table or self._read_initial_power_table()
        value = table.get(family, {}).get(rate_key, {}).get(channel)
        if value is None:
            if rate_key == "11b":
                return 0x50
            if rate_key in ("ht40",):
                return 0x50
            if rate_key in ("ht20",):
                return 0
            if rate_key in ("11g",):
                return 2
            return 0x50
        return int(value)

    def _ensure_runtime_tables(self):
        state = get_or_create_state()
        if not getattr(state.wifi, "initial_power_table", None):
            state.wifi.initial_power_table = self._read_initial_power_table()
        if not getattr(state.wifi, "tx_cal_runtime_table", None):
            state.wifi.tx_cal_runtime_table = deepcopy(state.wifi.initial_power_table)
        if not getattr(state.wifi, "final_power_table", None):
            state.wifi.final_power_table = {}

    def _set_runtime_index(self, family: str, rate_key: str, channel: int, index: int):
        state = get_or_create_state()
        self._ensure_runtime_tables()
        state.wifi.tx_cal_runtime_table.setdefault(family, {}).setdefault(rate_key, {})[channel] = int(index)

    def _apply_power_index_by_channel(self, rate: str, channel: int, index: int):
        self.logger.info("apply WiFi power index: rate=%s channel=%s index=%s", rate, channel, index)

    def _measure_tx_power_once(
        self,
        channel: int,
        freq_mhz: int,
        rate: str,
        demod: int,
        rf_port: int,
        pathloss_db: float,
        target_power_dbm: float,
        patha: int = 64,
        pathb: int = 0,
    ) -> tuple[float | None, dict]:
        self.dut.wifi_set_channel(channel)
        self.dut.wifi_set_rate(rate)
        self.dut.wifi_set_txpower(patha=patha, pathb=pathb)
        self.dut.wifi_start_hwtx(period=100, length=1500, count=0)

        self.wt.wifi.configure_wifi_vsa(
            freq_mhz=freq_mhz,
            target_power_dbm=target_power_dbm,
            rf_ports=[rf_port],
            pathloss_list=[pathloss_db],
            demod=demod,
            is_agc=True,
        )
        metrics = self.wt.wifi.fetch_tx_metrics()

        self.dut.wifi_stop_hwtx()
        return metrics.get("power_dbm"), metrics

    def _calc_next_power_index(
        self,
        current_index: int,
        measured_power_dbm: float,
        target_power_dbm: float,
        min_index: int = 0x00,
        max_index: int = 0x7F,
    ) -> int:
        delta = (target_power_dbm - measured_power_dbm) / 0.25
        next_index = round(current_index + delta)
        next_index = max(min_index, min(max_index, next_index))
        return next_index

    def _find_power_index_for_point(
        self,
        initial_index: int,
        channel: int,
        freq_mhz: int,
        rate: str,
        demod: int,
        target_power_dbm: float,
        rf_port: int,
        pathloss_db: float,
        tolerance_db: float = 0.5,
        max_iter: int = 6,
    ) -> dict:
        current_index = int(initial_index)
        final_metrics = {}
        final_power = None
        iterations = []

        for _ in range(max_iter):
            self._apply_power_index_by_channel(rate=rate, channel=channel, index=current_index)

            measured_power, metrics = self._measure_tx_power_once(
                channel=channel,
                freq_mhz=freq_mhz,
                rate=rate,
                demod=demod,
                rf_port=rf_port,
                pathloss_db=pathloss_db,
                target_power_dbm=target_power_dbm,
            )

            final_metrics = metrics
            final_power = measured_power
            iterations.append({
                "index": current_index,
                "measured_power_dbm": measured_power,
            })

            if measured_power is None:
                break

            if (target_power_dbm - tolerance_db) < measured_power < (target_power_dbm + tolerance_db):
                break

            next_index = self._calc_next_power_index(
                current_index=current_index,
                measured_power_dbm=measured_power,
                target_power_dbm=target_power_dbm,
            )
            if next_index == current_index:
                break
            current_index = next_index

        return {
            "channel": int(channel),
            "freq_mhz": int(freq_mhz),
            "rate": str(rate),
            "initial_index": int(initial_index),
            "final_index": int(current_index),
            "measured_power_dbm": final_power,
            "metrics": final_metrics,
            "iterations": iterations,
        }

    def _linear_interpolate_indices(self, measured_map: dict[int, int], channels: list[int]) -> dict[int, int]:
        result = {}
        points = sorted((int(ch), int(idx)) for ch, idx in measured_map.items())

        if not points:
            return result

        if len(points) == 1:
            idx = points[0][1]
            for ch in channels:
                result[int(ch)] = int(idx)
            return result

        first_ch, first_idx = points[0]
        second_ch, second_idx = points[1]
        left_slope = (second_idx - first_idx) / (second_ch - first_ch)
        for ch in channels:
            ch = int(ch)
            if ch <= first_ch:
                result[ch] = round(first_idx + (ch - first_ch) * left_slope)

        for i in range(len(points) - 1):
            ch1, idx1 = points[i]
            ch2, idx2 = points[i + 1]
            slope = (idx2 - idx1) / (ch2 - ch1)
            for ch in channels:
                ch = int(ch)
                if ch1 <= ch <= ch2:
                    result[ch] = round(idx1 + (ch - ch1) * slope)

        prev_ch, prev_idx = points[-2]
        last_ch, last_idx = points[-1]
        right_slope = (last_idx - prev_idx) / (last_ch - prev_ch)
        for ch in channels:
            ch = int(ch)
            if ch >= last_ch:
                result[ch] = round(last_idx + (ch - last_ch) * right_slope)

        return result

    def _build_wifi_summary_string(self, family: str, rate_key: str, final_map: dict[int, int]) -> str:
        if not final_map:
            return f"{family}-{rate_key}:empty"
        channels = sorted(final_map.keys())
        values = [final_map[ch] for ch in channels]
        return f"{family}-{rate_key}:ch{channels[0]}={values[0]},ch{channels[-1]}={values[-1]}"

    # ---------------------------------------------------------------------
    # public API
    # ---------------------------------------------------------------------
    def wifi_tx_calibration(
        self,
        channel: int,
        freq_mhz: int,
        rate: str,
        target_power_dbm: float,
        rf_port: int = 1,
        pathloss_db: float | None = None,
        demod: int = 2,
        tolerance_db: float = 0.5,
        max_iter: int = 6,
        **kwargs,
    ) -> StepResult:
        state = get_or_create_state()
        self._ensure_runtime_tables()

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_wifi_pathloss(
                rf_port=rf_port,
                rate=rate,
                freq_mhz=freq_mhz,
            )

        family = self._resolve_table_family(channel)
        rate_key = self._normalize_rate_key(rate)
        layout_key = self._resolve_layout_key(channel, rate)

        initial_index = self._get_initial_index(family, rate_key, channel)
        point_result = self._find_power_index_for_point(
            initial_index=initial_index,
            channel=channel,
            freq_mhz=freq_mhz,
            rate=rate,
            demod=demod,
            target_power_dbm=target_power_dbm,
            rf_port=rf_port,
            pathloss_db=actual_pathloss_db,
            tolerance_db=tolerance_db,
            max_iter=max_iter,
        )

        final_index = point_result["final_index"]
        measured_power = point_result["measured_power_dbm"]

        self._set_runtime_index(family, rate_key, channel, final_index)

        state.wifi.tx_cal_points.append({
            "layout_key": layout_key,
            "family": family,
            "rate_key": rate_key,
            "channel": int(channel),
            "freq_mhz": int(freq_mhz),
            "target_power_dbm": float(target_power_dbm),
            "initial_index": int(initial_index),
            "final_index": int(final_index),
            "measured_power_dbm": measured_power,
            "pathloss_db": float(actual_pathloss_db),
            "iterations": point_result["iterations"],
        })
        state.wifi.tx_cal_done = True
        state.runtime.phase = "wifi_tx_calibrated"

        if measured_power is None:
            return StepResult.failure("measure_failed")

        return StepResult.success(f"pwr={measured_power:.2f},idx={final_index}")

    def wifi_crystal_calibration(
        self,
        channel: int = 7,
        freq_mhz: int = 2442,
        rate: str = "108",
        rf_port: int = 1,
        pathloss_db: float | None = None,
        demod: int = 0,
        patha: int = 64,
        pathb: int = 0,
        init_xcap: int = 0x3F,
        target_ppm: float = 0.0,
        ppm_tolerance: float = 2.0,
        max_iter: int = 6,
        required_consecutive_pass: int = 1,
        **kwargs,
    ) -> StepResult:
        state = get_or_create_state()

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_wifi_pathloss(
                rf_port=rf_port,
                rate=rate,
                freq_mhz=freq_mhz,
            )

        xcap = max(0x00, min(0x7F, int(init_xcap)))
        state.wifi.xcap_init = xcap
        state.wifi.xcap_final = None
        state.wifi.crystal_done = False
        state.wifi.crystal_freq_err_ppm = None
        state.wifi.crystal_iterations = []

        self.dut.wifi_set_channel(channel)
        self.dut.wifi_set_rate(rate)
        self.dut.wifi_set_txpower(patha=patha, pathb=pathb)

        final_ppm = None
        consecutive_pass = 0

        try:
            for _ in range(max_iter):
                self.dut.wifi_set_xcap(xcap)
                self.dut.wifi_start_hwtx(period=100, length=1500, count=0)

                self.wt.wifi.configure_wifi_vsa(
                    freq_mhz=freq_mhz,
                    target_power_dbm=0.0,
                    rf_ports=rf_port,
                    pathloss_list=[actual_pathloss_db],
                    demod=demod,
                    is_agc=True,
                )
                metrics = self.wt.wifi.fetch_tx_metrics()

                freq_err_hz = metrics.get("freq_err_hz")
                if freq_err_hz is None:
                    return StepResult.failure("wifi_crystal_measure_failed")

                measured_ppm = (freq_err_hz / (freq_mhz * 1e6)) * 1e6
                final_ppm = measured_ppm

                state.wifi.crystal_freq_err_ppm = measured_ppm
                state.wifi.crystal_iterations.append({
                    "xcap": int(xcap),
                    "freq_err_hz": float(freq_err_hz),
                    "ppm": float(measured_ppm),
                    "pathloss_db": float(actual_pathloss_db),
                })

                if abs(measured_ppm - target_ppm) <= ppm_tolerance:
                    consecutive_pass += 1
                    if consecutive_pass >= required_consecutive_pass:
                        state.wifi.xcap_final = int(xcap)
                        state.wifi.crystal_done = True
                        state.runtime.phase = "wifi_crystal_done"
                        return StepResult.success(str(xcap))
                else:
                    consecutive_pass = 0

                delta = (measured_ppm - target_ppm) * freq_mhz / 2500.0
                next_xcap = round(xcap - delta)
                next_xcap = max(0x00, min(0x7F, next_xcap))

                if next_xcap == xcap:
                    break

                xcap = next_xcap

            state.wifi.xcap_final = int(xcap)
            state.wifi.crystal_done = True
            state.runtime.phase = "wifi_crystal_done"

            if final_ppm is None:
                return StepResult.failure("wifi_crystal_no_result")

            return StepResult.success(str(xcap))

        finally:
            try:
                self.dut.wifi_stop_hwtx()
            except Exception:
                pass

    def wifi_tx_calibration_finalize(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        self._ensure_runtime_tables()

        measured_points_by_bucket: dict[tuple[str, str], dict[int, int]] = {}

        for item in getattr(state.wifi, "tx_cal_points", []):
            family = item["family"]
            rate_key = item["rate_key"]
            channel = int(item["channel"])
            final_index = int(item["final_index"])
            measured_points_by_bucket.setdefault((family, rate_key), {})[channel] = final_index

        final_table = deepcopy(state.wifi.tx_cal_runtime_table)

        for layout_key, layout in self.WIFI_TX_CAL_LAYOUT.items():
            family = layout["table_family"]
            rate_key = layout["rate_key"]
            all_channels = [int(ch) for ch in layout["all_channels"]]

            measured_map = {}
            for ch in all_channels:
                if (family, rate_key) in measured_points_by_bucket and ch in measured_points_by_bucket[(family, rate_key)]:
                    measured_map[ch] = measured_points_by_bucket[(family, rate_key)][ch]

            if not measured_map:
                continue

            filled = self._linear_interpolate_indices(measured_map=measured_map, channels=all_channels)
            final_table.setdefault(family, {}).setdefault(rate_key, {})
            for ch, idx in filled.items():
                final_table[family][rate_key][int(ch)] = int(idx)

        if "2g" in state.wifi.tx_cal_runtime_table and "offset" in state.wifi.tx_cal_runtime_table["2g"]:
            final_table.setdefault("2g", {})["offset"] = deepcopy(state.wifi.tx_cal_runtime_table["2g"]["offset"])
        if "5g" in state.wifi.tx_cal_runtime_table and "offset" in state.wifi.tx_cal_runtime_table["5g"]:
            final_table.setdefault("5g", {})["offset"] = deepcopy(state.wifi.tx_cal_runtime_table["5g"]["offset"])

        state.wifi.final_power_table = final_table
        state.wifi.tx_cal_otp_table = deepcopy(final_table)
        state.runtime.phase = "wifi_tx_cal_finalize"

        summaries = []
        for family in ("2g", "5g"):
            for rate_key in ("ht40", "ht20", "11g", "11b"):
                fm = final_table.get(family, {}).get(rate_key, {})
                if fm:
                    summaries.append(self._build_wifi_summary_string(family, rate_key, fm))

        if not summaries:
            return StepResult.failure("no_final_wifi_power_table")

        return StepResult.success("; ".join(summaries))

    def wifi_tx_verify(
        self,
        channel: int,
        freq_mhz: int,
        rate: str,
        target_power_dbm: float,
        rf_port: int = 1,
        pathloss_db: float = 1.0,
        demod: int = 2,
        patha: int = 64,
        pathb: int = 0,
        **kwargs,
    ) -> StepResult:
        state = get_or_create_state()

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_wifi_pathloss(
                rf_port=rf_port,
                rate=rate,
                freq_mhz=freq_mhz,
            )

        self.dut.wifi_set_channel(channel)
        self.dut.wifi_set_rate(rate)
        self.dut.wifi_set_txpower(patha=patha, pathb=pathb)
        self.dut.wifi_start_hwtx(period=100, length=1500, count=0)

        try:
            self.wt.wifi.configure_wifi_vsa(
                freq_mhz=freq_mhz,
                target_power_dbm=target_power_dbm,
                rf_ports=rf_port,
                pathloss_list=[actual_pathloss_db],
                demod=demod,
                is_agc=True,
            )

            metrics = self.wt.wifi.fetch_tx_metrics()

            state.wifi.tx_verify_last = {
                "channel": int(channel),
                "freq_mhz": int(freq_mhz),
                "rate": str(rate),
                "pathloss_db": float(actual_pathloss_db),
                "metrics": metrics,
            }
            state.wifi.tx_verify_evm = metrics.get("evm_db")
            state.wifi.tx_verify_freq_err_hz = metrics.get("freq_err_hz")
            state.runtime.phase = "wifi_tx_verified"

            return StepResult.success(metrics.get("power_dbm", metrics))
        except Exception as exc:
            self.logger.exception("wifi_tx_verify failed: %s", exc)
            return StepResult.failure(str(exc))
        finally:
            try:
                self.dut.wifi_stop_hwtx()
            except Exception:
                pass

    def _estimate_wifi_rx_tx_time(
            self,
            packet_count: int,
            rate: str,
            payload_bytes: int = 1500,
    ) -> float:
        rate_key = self._normalize_rate_key(rate)

        # rough engineering estimate, enough for timeout / fallback sleep
        if rate_key == "11b":
            phy_rate_mbps = 11.0
        elif rate_key == "11g":
            phy_rate_mbps = 54.0
        elif rate_key == "ht20":
            phy_rate_mbps = 65.0
        elif rate_key == "ht40":
            phy_rate_mbps = 135.0
        else:
            phy_rate_mbps = 24.0

        bits_per_packet = (int(payload_bytes) + 200) * 8
        total_bits = bits_per_packet * int(packet_count)
        tx_time_s = total_bits / (phy_rate_mbps * 1e6)

        # add large guard margin for waveform gap / tester scheduling / command overhead
        return max(0.2, tx_time_s * 2.5)

    def _wait_wifi_vsg_done(
            self,
            packet_count: int,
            rate: str,
            payload_bytes: int = 1500,
            extra_guard_s: float = 0.3,
    ):
        estimated = self._estimate_wifi_rx_tx_time(
            packet_count=packet_count,
            rate=rate,
            payload_bytes=payload_bytes,
        )

        timeout_s = float(estimated + extra_guard_s + 2.0)

        # If the tester-side API supports explicit completion wait, prefer it.
        if hasattr(self.wt.wifi, "wait_for_vsg_complete"):
            try:
                self.wt.wifi.wait_for_vsg_complete(timeout=timeout_s)
                return
            except Exception:
                pass

        # Fallback: sleep by estimated duration
        time.sleep(float(estimated + extra_guard_s))

    def _wait_wifi_rx_counter_settle(
            self,
            poll_interval_s: float = 0.05,
            stable_rounds: int = 3,
            timeout_s: float = 0.5,
    ) -> int:
        deadline = time.time() + float(timeout_s)
        last_value = None
        stable = 0

        while time.time() < deadline:
            current = int(self.dut.wifi_get_arx_report())

            if last_value is not None and current == last_value:
                stable += 1
                if stable >= int(stable_rounds):
                    return current
            else:
                stable = 0
                last_value = current

            time.sleep(float(poll_interval_s))

        return int(self.dut.wifi_get_arx_report())

    def wifi_rx_verify(
            self,
            channel: int,
            rate: str,
            freq_mhz: int | None = None,
            rf_port: int = 1,
            pathloss_db: float | None = None,
            tester_power_dbm: float = -61.0,
            packet_count: int = 1000,
            wave_file: str | None = None,
            sample_rate_hz: float | None = None,
            payload_bytes: int = 1500,
            per_limit: float = 10.0,
            **kwargs,
    ) -> StepResult:
        state = get_or_create_state()

        if freq_mhz is None:
            if channel <= 14:
                freq_mhz = 2407 + channel * 5
                if channel == 14:
                    freq_mhz = 2484
            else:
                freq_mhz = 5000 + channel * 5

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_wifi_pathloss(
                rf_port=rf_port,
                rate=rate,
                freq_mhz=freq_mhz,
            )

        try:
            default_sample_rate_hz, default_wave_file = self._wifi_rx_verify_profile(rate)

            if sample_rate_hz is None:
                sample_rate_hz = default_sample_rate_hz
            if wave_file is None:
                wave_file = default_wave_file

            # target DUT input power + cable/fixture pathloss = tester source output power
            tester_output_power_dbm = float(tester_power_dbm) + float(actual_pathloss_db)

            start_ts = time.time()

            # DUT enter RX verify mode
            self.dut.wifi_set_channel(channel)
            self.dut.wifi_set_rate(rate)

            # Replace these with your real DUT RX APIs
            self.dut.wifi_reset_stats()
            self.dut.wifi_start_arx()

            self.wt.wifi.start_wifi_vsg(
                rf_ports=[int(rf_port) - 1],
                freq_mhz=int(freq_mhz),
                sample_rate_hz=float(sample_rate_hz),
                packets=int(packet_count),
                wave_file=wave_file,
                power_list=[float(tester_output_power_dbm)],
                pathloss_list=[float(actual_pathloss_db)],
            )

            # Wait for SG/VSG send complete, not for DUT receive count to reach packet_count
            self._wait_wifi_vsg_done(
                packet_count=int(packet_count),
                rate=rate,
                payload_bytes=int(payload_bytes),
            )

            # Let DUT RX counter settle briefly after source completes
            dut_receive_count = self._wait_wifi_rx_counter_settle(
                poll_interval_s=0.05,
                stable_rounds=3,
                timeout_s=0.5,
            )

            elapsed = round(time.time() - start_ts, 2)

            if int(packet_count) > 0:
                pass_percent = (float(dut_receive_count) / float(packet_count)) * 100.0
                per_percent = 100.0 - pass_percent
            else:
                pass_percent = None
                per_percent = None

            passed = bool(per_percent is not None and per_percent <= float(per_limit))

            report = {
                "channel": int(channel),
                "freq_mhz": int(freq_mhz),
                "rate": str(rate),
                "rf_port": int(rf_port),
                "packet_count": int(packet_count),
                "tester_power_dbm": float(tester_power_dbm),
                "tester_output_power_dbm": float(tester_output_power_dbm),
                "pathloss_db": float(actual_pathloss_db),
                "dut_receive_count": int(dut_receive_count),
                "pass_percent": pass_percent,
                "per_percent": per_percent,
                "per_limit": float(per_limit),
                "passed": passed,
                "wave_file": str(wave_file),
                "sample_rate_hz": float(sample_rate_hz),
                "payload_bytes": int(payload_bytes),
                "test_time_sec": float(elapsed),
            }

            state.wifi.rx_verify_last = report
            state.runtime.phase = "wifi_rx_verified"

            return StepResult.success(report)

        except Exception as exc:
            self.logger.exception("wifi_rx_verify failed: %s", exc)
            return StepResult.failure(str(exc))
        finally:
            try:
                self.wt.wifi.stop_vsg()
            except Exception:
                pass
            try:
                self.dut.wifi_stop_rx_per()
            except Exception:
                pass

    def rf_mp_finish(self, **kwargs) -> StepResult:
        state = get_or_create_state()
        try:
            state.runtime.phase = "wifi_finished"
            return StepResult.success("wifi_mp_finish_ok")
        except Exception as exc:
            self.logger.exception("rf_mp_finish failed: %s", exc)
            return StepResult.failure(str(exc))