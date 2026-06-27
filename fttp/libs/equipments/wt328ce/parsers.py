from __future__ import annotations

from typing import Dict, Any


def _to_float(value: str):
    try:
        return float(value.strip())
    except Exception:
        return None


def parse_wifi_base_result(response: str) -> Dict[str, Any]:
    parts = [p.strip() for p in response.split(",")]
    result = {"raw": response, "parts": parts}

    if len(parts) >= 15:
        result["power_dbm"] = _to_float(parts[0])
        result["peak_dbm"] = _to_float(parts[1]) if len(parts) > 1 else None
        result["evm_db"] = _to_float(parts[3]) if len(parts) > 3 else None
        result["freq_err_hz"] = _to_float(parts[4]) if len(parts) > 4 else None
    return result


def parse_wifi_mask_error(response: str):
    return _to_float(response)


def parse_bt_power(response: str):
    return _to_float(response)


def parse_bt_metric(response: str):
    return _to_float(response)


def parse_int(response: str):
    try:
        return int(str(response).strip())
    except Exception:
        return None