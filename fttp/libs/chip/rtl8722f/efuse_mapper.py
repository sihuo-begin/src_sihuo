from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from src.libs.chip.rtl8722f.calibration_state import Rtl8722fCalibrationState


def _u8(value: int | None, default: int = 0xFF) -> int:
    if value is None:
        return default & 0xFF
    return int(value) & 0xFF


def _ensure_range(image: Dict[int, int], start: int, end: int, fill: int = 0xFF) -> None:
    for addr in range(start, end + 1):
        image.setdefault(addr, fill & 0xFF)


def _write_bytes(image: Dict[int, int], start_addr: int, values: Sequence[int]) -> None:
    for i, value in enumerate(values):
        image[start_addr + i] = _u8(value, default=0xFF)


def _normalize_mac_bytes(mac) -> List[int] | None:
    if mac is None:
        return None

    if isinstance(mac, str):
        text = mac.strip().replace("-", "").replace(":", "").replace(".", "")
        if len(text) != 12:
            raise ValueError(f"Invalid MAC string: {mac}")
        return [int(text[i:i + 2], 16) & 0xFF for i in range(0, 12, 2)]

    if isinstance(mac, (bytes, bytearray)):
        if len(mac) != 6:
            raise ValueError(f"MAC bytes length must be 6, got {len(mac)}")
        return [b & 0xFF for b in mac]

    values = list(mac)
    if len(values) != 6:
        raise ValueError(f"MAC sequence length must be 6, got {len(values)}")

    return [_u8(v, default=0xFF) for v in values]


def _extract_wifi_table(state: Rtl8722fCalibrationState) -> dict:
    if getattr(state.wifi, "tx_cal_otp_table", None):
        return state.wifi.tx_cal_otp_table
    if getattr(state.wifi, "final_power_table", None):
        return state.wifi.final_power_table
    return {}


def _encode_wifi_otp_locations(table: dict) -> Dict[int, int]:
    image: Dict[int, int] = {}

    # builtin defaults
    for addr in range(0x20, 0x26):
        image[addr] = 0x60
    for addr in range(0x26, 0x2B):
        image[addr] = 0x50
    image[0x2B] = 0x02
    for addr in range(0x32, 0x40):
        image[addr] = 0x50
    image[0x40] = 0x02

    wifi_2g = table.get("2g", {})
    wifi_5g = table.get("5g", {})

    table_2g_11b = wifi_2g.get("11b", {})
    table_2g_ht40 = wifi_2g.get("ht40", {})
    table_2g_11g = wifi_2g.get("11g", {})

    table_5g_ht40 = wifi_5g.get("ht40", {})
    table_5g_11g = wifi_5g.get("11g", {})

    channels_2g_cck = [1, 4, 7, 10, 13, 14]
    for i, ch in enumerate(channels_2g_cck):
        addr = 0x20 + i
        image[addr] = _u8(table_2g_11b.get(ch, image[addr]), default=image[addr])

    channels_2g_bw40 = [1, 4, 7, 10, 13]
    for i, ch in enumerate(channels_2g_bw40):
        addr = 0x26 + i
        image[addr] = _u8(table_2g_ht40.get(ch, image[addr]), default=image[addr])

    image[0x2B] = _u8(table_2g_11g.get(7, image[0x2B]), default=image[0x2B])

    channels_5g_bw40 = [38, 46, 54, 62, 102, 110, 118, 126, 134, 142, 151, 159, 167, 175]
    for i, ch in enumerate(channels_5g_bw40):
        addr = 0x32 + i
        image[addr] = _u8(table_5g_ht40.get(ch, image[addr]), default=image[addr])

    image[0x40] = _u8(table_5g_11g.get(100, image[0x40]), default=image[0x40])

    return image


def _build_bt_default_image() -> Dict[int, int]:
    """
    New BT efuse table:
      0x190~0x195 : BT Address
      0x196       : Function Enable (default 0x08)
      0x197       : Tx Gain K
      0x198~0x199 : Flatness K
      0x19A~0x19B : Reserved
      0x19C       : Max TX Gain LE1M (default 0x2A)
      0x19D~0x19F : Reserved
      0x1A0       : BT Thermal Meter
    """
    image: Dict[int, int] = {}

    for addr in range(0x190, 0x196):
        image[addr] = 0xFF

    image[0x196] = 0x0E
    image[0x197] = 0xFF
    image[0x198] = 0xFF
    image[0x199] = 0xFF
    image[0x19A] = 0xFF
    image[0x19B] = 0xFF
    image[0x19C] = 0x2A
    image[0x19D] = 0xFF
    image[0x19E] = 0xFF
    image[0x19F] = 0xFF
    image[0x1A0] = 0xFF

    return image


def _build_bt_function_enable(state: Rtl8722fCalibrationState) -> int:
    value = 0x08

    gain_k = getattr(state.bt, "gain_k", None)
    flatness = list(getattr(state.bt, "flatness_bytes", []) or [])

    if gain_k is not None:
        value |= 0x02

    if flatness:
        value |= 0x04

    return value & 0xFF


def _encode_bt_otp_locations(
    state: Rtl8722fCalibrationState,
    bt_mac=None,
) -> Dict[int, int]:
    image = _build_bt_default_image()

    bt_mac_bytes = _normalize_mac_bytes(bt_mac)
    if bt_mac_bytes is not None:
        _write_bytes(image, 0x190, bt_mac_bytes)

    gain_k = getattr(state.bt, "gain_k", None)
    flatness = list(getattr(state.bt, "flatness_bytes", []) or [])

    if gain_k is not None or flatness:
        image[0x196] = _build_bt_function_enable(state)

    if gain_k is not None:
        image[0x197] = _u8(gain_k, default=image[0x197])

    if len(flatness) > 0:
        image[0x198] = _u8(flatness[0], default=image[0x198])
    if len(flatness) > 1:
        image[0x199] = _u8(flatness[1], default=image[0x199])

    if getattr(state.bt, "thermal_bt", None) is not None:
        image[0x1A0] = _u8(state.bt.thermal_bt, default=image[0x1A0])

    return image


def build_efuse_image_from_state(
    state: Rtl8722fCalibrationState,
    wifi_mac=None,
    bt_mac=None,
) -> Dict[int, int]:
    image: Dict[int, int] = {}

    _ensure_range(image, 0x20, 0x40, fill=0xFF)
    _ensure_range(image, 0xC9, 0xCA, fill=0xFF)
    _ensure_range(image, 0x11A, 0x11F, fill=0xFF)  # WiFi MAC
    _ensure_range(image, 0x13B, 0x13D, fill=0xFF)
    _ensure_range(image, 0x190, 0x1A0, fill=0xFF)  # BT MAC + BT calibration

    # WiFi calibration/default
    wifi_table = _extract_wifi_table(state)
    image.update(_encode_wifi_otp_locations(wifi_table))

    if getattr(state.wifi, "xcap_final", None) is not None:
        image[0xC9] = _u8(state.wifi.xcap_final, default=0x6C)
    else:
        image[0xC9] = 0x6C

    if getattr(state.wifi, "thermal_wifi", None) is not None:
        image[0xCA] = _u8(state.wifi.thermal_wifi, default=0x18)
    elif getattr(state.wifi, "thermal_after_preheat", None) is not None:
        image[0xCA] = _u8(state.wifi.thermal_after_preheat, default=0x18)

    # WiFi MAC from external input
    wifi_mac_bytes = _normalize_mac_bytes(wifi_mac)
    if wifi_mac_bytes is not None:
        _write_bytes(image, 0x11A, wifi_mac_bytes)

    # BT calibration/default + BT MAC from external input
    image.update(_encode_bt_otp_locations(state, bt_mac=bt_mac))

    return image


def build_aligned_16byte_blocks(
    image: Dict[int, int],
    fill: int = 0xFF,
    skip_all_ff: bool = True,
) -> List[Tuple[int, bytes]]:
    if not image:
        return []

    min_addr = min(image.keys())
    max_addr = max(image.keys())

    start = min_addr & ~0x0F
    end = max_addr | 0x0F

    blocks: List[Tuple[int, bytes]] = []
    addr = start

    while addr <= end:
        data = bytes(image.get(addr + i, fill & 0xFF) & 0xFF for i in range(16))

        if skip_all_ff and all(b == (fill & 0xFF) for b in data):
            addr += 16
            continue

        blocks.append((addr, data))
        addr += 16

    return blocks


def build_write_commands(image: Dict[int, int]) -> List[str]:
    commands: List[str] = []

    blocks = build_aligned_16byte_blocks(
        image=image,
        fill=0xFF,
        skip_all_ff=True,
    )

    for addr, data in blocks:
        hex_bytes = "".join(f"{b:02X}" for b in data)
        commands.append(f"iwpriv config_set wmap,0x{addr:03X},{hex_bytes}")

    return commands
