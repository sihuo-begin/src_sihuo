from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StepResult:
    ok: bool
    value: str = ""
    message: str = ""

    @classmethod
    def success(cls, value: object = "", message: str = "") -> "StepResult":
        return cls(ok=True, value=_stringify(value), message=message)

    @classmethod
    def failure(cls, value: object = "", message: str = "") -> "StepResult":
        return cls(ok=False, value=_stringify(value), message=message)


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)