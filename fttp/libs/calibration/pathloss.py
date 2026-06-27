from __future__ import annotations

from pathlib import Path
from typing import Any, Union, Optional

import yaml


class PathlossTable:
    def __init__(self, table: Optional[dict[str, Any]] = None):
        self.table = table or {}

    @classmethod
    def load_or_empty(cls, yaml_path: Union[str, Path, None]) -> "PathlossTable":
        if not yaml_path:
            return cls({})
        p = Path(yaml_path)
        if not p.exists():
            return cls({})
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)

    def save_yaml(self, yaml_path: Union[str, Path]):
        p = Path(yaml_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.table, f, sort_keys=False, allow_unicode=True)

    def set_loss(self, technology: str, port: Union[int, str], modulation: str, freq_mhz: int, loss_db: float):
        tech_key = self._normalize_technology(technology)
        port_key = self._normalize_port(port)
        self.table.setdefault(tech_key, {}).setdefault(port_key, {}).setdefault(modulation, {})[int(freq_mhz)] = round(float(loss_db), 2)

    def get_loss(self, technology: str, port: Union[int, str], modulation: str, freq_mhz: int, default: float = 0.0) -> float:
        tech_key = self._normalize_technology(technology)
        port_key = self._normalize_port(port)
        mod_table = self.table.get(tech_key, {}).get(port_key, {}).get(modulation, {})
        if not mod_table:
            return float(default)

        freq_map = {int(k): float(v) for k, v in mod_table.items()}
        if int(freq_mhz) in freq_map:
            return float(freq_map[int(freq_mhz)])

        return self._interpolate(freq_map, int(freq_mhz), default=float(default))

    def _normalize_technology(self, technology: str) -> str:
        t = str(technology).strip().lower()
        if t in ("wifi", "wlan"):
            return "wifi"
        if t in ("bt", "ble", "bluetooth"):
            return "bt"
        return t

    def _normalize_port(self, port: Union[int, str]) -> str:
        p = str(port).strip().lower()
        if p.startswith("port"):
            return p
        return f"port{p}"

    def _interpolate(self, freq_map: dict[int, float], target_freq: int, default: float = 0.0) -> float:
        if not freq_map:
            return float(default)

        freqs = sorted(freq_map.keys())

        if target_freq <= freqs[0]:
            return float(freq_map[freqs[0]])

        if target_freq >= freqs[-1]:
            return float(freq_map[freqs[-1]])

        for i in range(len(freqs) - 1):
            f1, f2 = freqs[i], freqs[i + 1]
            if f1 <= target_freq <= f2:
                l1 = float(freq_map[f1])
                l2 = float(freq_map[f2])
                ratio = (target_freq - f1) / (f2 - f1)
                return l1 + (l2 - l1) * ratio

        return float(default)