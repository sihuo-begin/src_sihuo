from __future__ import annotations


def normalize_wifi_rate(rate: str) -> str:
    r = str(rate).strip().upper()

    if r in ("11M", "CCK11M", "CCK-11M"):
        return "11M"

    if r in ("54M", "108", "OFDM54M", "OFDM-54M"):
        return "54M"

    if r in ("HT20-MCS7", "HT20-7", "MCS7-B20", "HT20_MCS7"):
        return "HT20-MCS7"

    if r in ("HT40-MCS7", "HT40-7", "MCS7-B40", "HT40_MCS7"):
        return "HT40-MCS7"

    return rate


def normalize_bt_phy(phy_name: str) -> str:
    p = str(phy_name).strip().upper()

    if p in ("BLE", "BLE1M", "LE1M"):
        return "BLE1M"

    if p in ("BLE2M", "LE2M"):
        return "BLE2M"

    return phy_name
