from __future__ import annotations

import re
from typing import Dict, List, Tuple


def _resolve_dut(connections):
    if hasattr(connections, "dut"):
        return connections.dut
    if hasattr(connections, "chip"):
        return connections.chip
    if hasattr(connections, "send_receive"):
        return connections
    raise AttributeError("connections has no dut/chip object or send_receive interface")


def execute_write_commands(connections, logger, commands: List[str]) -> List[str]:
    dut = _resolve_dut(connections)
    outputs = []

    for cmd in commands:
        logger.info("EFUSE write cmd: %s", cmd)
        if hasattr(dut, "send_receive"):
            out = dut.send_receive(cmd)
        else:
            raise AttributeError("dut object has no send_receive interface")
        outputs.append("" if out is None else str(out))

    return outputs


def dump_realmap(connections, logger) -> str:
    dut = _resolve_dut(connections)
    cmd = "iwpriv config_get realmap"

    logger.info("EFUSE dump cmd: %s", cmd)
    if hasattr(dut, "send_receive"):
        out = dut.send_receive(cmd)
    else:
        raise AttributeError("dut object has no send_receive interface")

    return "" if out is None else str(out)


def _parse_realmap(realmap_text: str) -> Dict[int, int]:
    result: Dict[int, int] = {}

    patterns = [
        r"0x([0-9A-Fa-f]{1,3})\s*[:=]\s*0x?([0-9A-Fa-f]{1,2})",
        r"\[?([0-9A-Fa-f]{1,3})\]?\s*[:=]\s*([0-9A-Fa-f]{1,2})",
        r"\b([0-9A-Fa-f]{3})\b\s+([0-9A-Fa-f]{2})\b",
    ]

    lines = realmap_text.splitlines()
    for line in lines:
        for p in patterns:
            m = re.search(p, line)
            if m:
                addr = int(m.group(1), 16)
                val = int(m.group(2), 16)
                result[addr] = val
                break

    return result


def compare_realmap_with_image(
    realmap_text: str,
    image: Dict[int, int],
) -> Tuple[bool, Dict[int, Tuple[int | None, int]]]:
    realmap = _parse_realmap(realmap_text)
    diff: Dict[int, Tuple[int | None, int]] = {}

    for addr, expected in image.items():
        actual = realmap.get(addr)
        if actual != expected:
            diff[addr] = (actual, expected)

    return len(diff) == 0, diff
