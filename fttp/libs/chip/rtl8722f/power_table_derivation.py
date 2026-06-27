# encoding=utf-8

from __future__ import annotations

from collections import defaultdict

from .calibration_state import Rtl8722fCalibrationState


class WifiPowerTableDerivationService:
    def build_runtime_table_from_cal_points(self, cal: Rtl8722fCalibrationState) -> Rtl8722fCalibrationState:
        band_2g = defaultdict(dict)
        band_5g = defaultdict(dict)

        for p in cal.measured_points:
            rate_u = p.rate.upper()

            if rate_u in ("11M", "CCK", "CCK11M"):
                key = "11B"
            elif rate_u in ("54M", "OFDM", "OFDM54M", "11G"):
                key = "11G"
            elif rate_u in ("HT20-MCS7", "HT20", "MCS7-B20"):
                key = "HT20"
            elif rate_u in ("HT40-MCS7", "HT40", "MCS7-B40"):
                key = "HT40"
            else:
                key = rate_u

            if p.freq_mhz < 5000:
                band_2g[p.channel][key] = p.final_index
            else:
                band_5g[p.channel][key] = p.final_index

        cal.runtime_power_table_2g = dict(band_2g)
        cal.runtime_power_table_5g = dict(band_5g)
        return cal

    def build_otp_group_table_from_runtime(self, cal: WifiTxCalibrationResult) -> WifiTxCalibrationResult:
        table_2g = cal.runtime_power_table_2g
        table_5g = cal.runtime_power_table_5g

        cck_groups = [
            self._pick_group_value(table_2g, [1, 2], "11B"),
            self._pick_group_value(table_2g, [3, 4, 5], "11B"),
            self._pick_group_value(table_2g, [6, 7, 8], "11B"),
            self._pick_group_value(table_2g, [9, 10, 11], "11B"),
            self._pick_group_value(table_2g, [12, 13], "11B"),
            self._pick_group_value(table_2g, [14], "11B"),
        ]

        bw20_2g_groups = [
            self._pick_group_value(table_2g, [1, 2], "HT40"),
            self._pick_group_value(table_2g, [3, 4, 5], "HT40"),
            self._pick_group_value(table_2g, [6, 7, 8], "HT40"),
            self._pick_group_value(table_2g, [9, 10, 11], "HT40"),
            self._pick_group_value(table_2g, [12, 13], "HT40"),
        ]

        bw40_2g_groups = [
            self._pick_group_value(table_2g, [1, 2], "HT40"),
            self._pick_group_value(table_2g, [3, 4, 5], "HT40"),
            self._pick_group_value(table_2g, [6, 7, 8], "HT40"),
            self._pick_group_value(table_2g, [9, 10, 11], "HT40"),
            self._pick_group_value(table_2g, [12, 13], "HT40"),
        ]

        bw40_5g_groups = [
            self._pick_group_value(table_5g, [36, 38, 40], "HT40"),
            self._pick_group_value(table_5g, [44, 46, 48], "HT40"),
            self._pick_group_value(table_5g, [52, 54, 56], "HT40"),
            self._pick_group_value(table_5g, [60, 62, 64], "HT40"),
            self._pick_group_value(table_5g, [100, 102, 104], "HT40"),
            self._pick_group_value(table_5g, [108, 110, 112], "HT40"),
            self._pick_group_value(table_5g, [116, 118, 120], "HT40"),
            self._pick_group_value(table_5g, [124, 126, 128], "HT40"),
            self._pick_group_value(table_5g, [132, 134, 136], "HT40"),
            self._pick_group_value(table_5g, [140, 142, 144], "HT40"),
            self._pick_group_value(table_5g, [149, 151, 153], "HT40"),
            self._pick_group_value(table_5g, [157, 159, 161], "HT40"),
            self._pick_group_value(table_5g, [165, 167, 169], "HT40"),
            self._pick_group_value(table_5g, [173, 175, 177], "HT40"),
        ]

        cal.otp_cck_2g_groups = cck_groups
        cal.otp_bw40_2g_groups = bw40_2g_groups
        cal.otp_bw40_5g_groups = bw40_5g_groups
        cal.otp_diff_2g = 0x02
        cal.otp_diff_5g = 0x02
        return cal

    @staticmethod
    def _pick_group_value(table: dict, channels: list[int], key: str) -> int:
        values = []
        for ch in channels:
            if ch in table and key in table[ch]:
                values.append(table[ch][key])
        if not values:
            return 0xFF
        return int(round(sum(values) / len(values)))
