from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Dict, Any, Literal

Direction = Literal["RX_VSG_to_DUT", "TX_DUT_to_VSA"]

@dataclass
class PathLoss:
    meta: Dict[str, Any]
    loss_db: Dict[Direction, Dict[int, float]]

    @staticmethod
    def load(path: str) -> "PathLoss":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        loss_db = {}
        for k, mp in d.get("loss_db", {}).items():
            loss_db[k] = {int(freq): float(val) for freq, val in mp.items()}
        return PathLoss(meta=d.get("meta", {}), loss_db=loss_db)

    def loss(self, direction: Direction, freq_mhz: int) -> float:
        table = self.loss_db.get(direction, {})
        if not table:
            raise ValueError(f"no pathloss table for direction={direction}")

        if freq_mhz in table:
            return float(table[freq_mhz])

        xs = sorted(table.keys())
        if freq_mhz <= xs[0]:
            return float(table[xs[0]])
        if freq_mhz >= xs[-1]:
            return float(table[xs[-1]])

        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            if x0 <= freq_mhz <= x1:
                y0, y1 = table[x0], table[x1]
                t = (freq_mhz - x0) / (x1 - x0)
                return float(y0 + t * (y1 - y0))

        return float(table[xs[-1]])

def compensate_vsg_power_dbm(target_at_dut_dbm: float, loss_rx_db: float) -> float:
    # VSG setpoint = target at DUT + pathloss
    return target_at_dut_dbm + loss_rx_db