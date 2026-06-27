import re
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Pattern, Sequence, Union

Terminator = Union[str, Pattern[str], Callable[[str], bool]]
_WORD_TOKENS = {"OK", "ERROR"}  # 只保留最常见，避免过度推断


class ATError(RuntimeError):
    pass


class ATTimeout(TimeoutError):
    pass


@dataclass
class ATResponse:
    ok: bool
    lines: List[str]          # payload lines (excluding OK/ERROR)
    status_line: str          # "OK" or "ERROR" (or last line)
    raw: List[str]            # all lines including OK/ERROR


def _now() -> float:
    return time.monotonic()


def _norm(s: str) -> str:
    s = s.replace("\r", "").replace("\n", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


class ATClient:
    """
    Minimal line-oriented AT client based on a user-provided connection.

    connection must provide:
      - send(data)
      - recv(...)
      - optionally send_receive(...)
      - optionally close()
    """
    def __init__(self, connection, timeout: float = 0.1):
        self.conn = connection
        self.timeout = timeout
        self._rx_buf = ""

    # def close(self):
    #     try:
    #         close_fn = getattr(self.conn, "close", None)
    #         if callable(close_fn):
    #             close_fn()
    #     except Exception:
    #         pass
    def close(self):
        # shared DUT connection, do not close externally owned connection here
        pass

    def flush_input(self):
        """
        Try to drain any pending input from connection.
        Assumes recv() will return empty/None or raise on timeout/no data.
        """
        end = _now() + 0.2
        while _now() < end:
            try:
                chunk = self.conn.recv()
            except Exception:
                break
            if not chunk:
                break

    def _to_text(self, data) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)

    def _readline(self) -> Optional[str]:
        deadline = _now() + self.timeout

        while _now() < deadline:
            if "\n" in self._rx_buf:
                line, self._rx_buf = self._rx_buf.split("\n", 1)
                return line.strip("\r\n")

            try:
                chunk = self.conn.recv()
            except Exception:
                chunk = None

            if not chunk:
                continue

            self._rx_buf += self._to_text(chunk)

        return None

    @staticmethod
    def _match_terminator(line: str, t: Terminator) -> bool:
        # Pattern 才是“正则方式”
        if isinstance(t, re.Pattern):
            return bool(t.search(line))

        # callable
        if callable(t) and not isinstance(t, str):
            return bool(t(line))

        # 字符串：字面量 + 自动自适应
        s = _norm(t)
        if not s:
            return False

        l = _norm(line)

        su = s.upper()
        lu = l.upper()
        if su in _WORD_TOKENS:
            if re.search(rf"(^|\W){re.escape(su)}(\W|$)", lu):
                return True
        if lu == su:
            return True
        if lu.startswith(su):
            return True
        return su in lu

    def exec2(
        self,
        cmd: str,
        *,
        timeout: float = 2.0,
        terminators: Optional[Sequence[Terminator]] = None,
        ok_terminators: Sequence[Terminator] = ("OK", "# "),
        err_terminators: Sequence[Terminator] = ("ERROR",),
        include_terminator_in_lines: bool = True,
        echo_cmd: bool = False,
    ) -> ATResponse:
        """
        Read until any terminator matches, or timeout.

        - terminators: if provided, these are checked FIRST
        - ok_terminators / err_terminators: common fallbacks
        """
        self.flush_input()

        data = cmd + "\r\n"
        self.conn.send(data)

        deadline = _now() + timeout
        raw: List[str] = []
        payload: List[str] = []

        # Build check order
        primary_terms = list(terminators) if terminators else []
        ok_terms = list(ok_terminators) if ok_terminators else []
        err_terms = list(err_terminators) if err_terminators else []

        while _now() < deadline:
            line = self._readline()
            if line is None:
                continue
            if line == "":
                continue

            raw.append(line)

            # Some modules echo back the command; optionally ignore it
            if (not echo_cmd) and line.strip() == cmd.strip():
                continue

            # 1) custom terminators first
            for t in primary_terms:
                if self._match_terminator(line, t):
                    if include_terminator_in_lines:
                        payload.append(line)
                    ok = True
                    for et in err_terms:
                        if self._match_terminator(line, et):
                            ok = False
                            break
                    return ATResponse(ok=ok, lines=payload, status_line=line, raw=raw)

            # 2) error terminators
            for t in err_terms:
                if self._match_terminator(line, t):
                    if include_terminator_in_lines:
                        payload.append(line)
                    return ATResponse(ok=False, lines=payload, status_line=line, raw=raw)

            # 3) ok terminators
            for t in ok_terms:
                if self._match_terminator(line, t):
                    if include_terminator_in_lines:
                        payload.append(line)
                    return ATResponse(ok=True, lines=payload, status_line=line, raw=raw)

            payload.append(line)

        raise ATTimeout(f"Timeout waiting for response to: {cmd!r}. Raw so far: {raw}")

    # Backwards-compatible wrapper
    def exec(self, cmd: str, expect: str = "OK", timeout: float = 2.0) -> ATResponse:
        return self.exec2(cmd, timeout=timeout, ok_terminators=(expect,))


def _parse_mac12(s: str) -> Optional[bytes]:
    """
    Find 12-hex MAC (aabbccddeeff) in a string. Return 6 bytes.
    """
    m = re.search(r"([0-9a-fA-F]{12})", s)
    if not m:
        return None
    h = m.group(1)
    return bytes.fromhex(h)


def _format_mac12(mac: bytes) -> str:
    if len(mac) != 6:
        raise ValueError("MAC must be 6 bytes")
    return mac.hex()  # aabbccddeeff


def to_mac(s: str) -> str:
    # keep only hex chars (so it also works if input contains separators/spaces)
    hexs = ''.join(c for c in s.strip() if c.lower() in '0123456789abcdef')
    if len(hexs) != 12:
        raise ValueError(f"Expected 12 hex digits, got {len(hexs)}: {hexs!r}")
    return ':'.join(hexs[i:i+2] for i in range(0, 12, 2))


def _parse_rssi_dbm(lines: List[str]) -> int:
    """
    Try to find an RSSI integer (typically negative) from response lines.
    Accepts patterns like:
      RSSI=-55
      +RSSI:-55
      -55
    """
    for line in lines:
        m = re.search(r"(-?\d+)", line)
        if m:
            val = int(m.group(1))
            if -127 <= val <= 0:
                return val
    raise ATError(f"Failed to parse RSSI from lines: {lines}")


class RTL8720MP_STA:
    def __init__(self, connection):
        self.at = ATClient(connection)

    def sta_scan(self) -> List[str]:
        r = self.at.exec("ATWS", timeout=8.0)
        if not r.ok:
            raise ATError(f"Scan failed: {r.raw}")
        return r.lines

    def sta_set_ssid(self, ssid: str):
        self.at.exec(f"ATW0={ssid}")

    def sta_set_bssid(self, bssid: str) -> None:
        if not re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", bssid):
            raise ValueError("bssid must be like '88:11:22:33:44:55'")
        r = self.at.exec(f"ATW6={bssid}", timeout=2.0)
        if not r.ok:
            raise ATError(f"Set BSSID failed: {r.raw}")

    def sta_set_passphrase(self, psk: str) -> None:
        r = self.at.exec(f"ATW1={psk}", timeout=2.0)
        if not r.ok:
            raise ATError(f"Set passphrase failed: {r.raw}")

    def sta_join(self):
        r = self.at.exec("ATWC", timeout=15)
        if not r.ok:
            raise ATError(r.raw)

    def sta_get_mac(self) -> bytes:
        r = self.at.exec("ATWZ=read_mac", timeout=2.0, expect="ATWZ")
        if not r.ok:
            raise ATError(f"Read MAC failed: {r.raw}")
        for line in (r.lines + r.raw):
            mac = _parse_mac12(line)
            if mac:
                return mac
        raise ATError(f"Could not find MAC in response: {r.raw}")

    def sta_set_ap_mac(self, mac: str) -> None:
        mac = to_mac(mac)
        r = self.at.exec(f"ATWZ=write_mac,{mac}", timeout=2.0)
        if not r.ok:
            raise ATError(f"Set AP MAC failed: {r.raw}")

    def sta_disconnect(self):
        self.at.exec("ATWD", timeout=5)

    def sta_get_rssi(self) -> int:
        r = self.at.exec("ATWR")
        return _parse_rssi_dbm(r.lines or r.raw)

    def sta_connect(self, ssid: str, psk: str, bssid: Optional[str] = None) -> None:
        self.sta_set_ssid(ssid)
        self.sta_set_passphrase(psk)
        if bssid:
            self.sta_set_bssid(bssid)
        self.sta_join()


# ===========================
# AP 控制
# ===========================

class RTL8720MP_AP:
    def __init__(self, connection):
        self.ap = ATClient(connection)

    def send_enter_ap(self):
        self.ap.exec("\r\n", expect="#", timeout=1)

    def ap_set_ssid(self, ssid: str) -> None:
        if not ssid:
            raise ValueError("ssid is empty")
        r = self.ap.exec(f"ATW3={ssid}", timeout=2.0, expect="#")
        if not r.ok:
            raise ATError(f"AP set SSID failed: {r.raw}")

    def ap_set_key(self, key: str) -> None:
        r = self.ap.exec(f"ATW4={key}", timeout=2.0, expect="#")
        if not r.ok:
            raise ATError(f"AP set key failed: {r.raw}")

    def ap_start(self) -> None:
        r = self.ap.exec("ATWA", timeout=8.0, expect="Starting AP")
        if not r.ok:
            raise ATError(f"AP start failed: {r.raw}")

    def ap_config_and_start(self, ssid: str, key: str) -> None:
        self.ap_set_ssid(ssid)
        self.ap_set_key(key)
        self.ap_start()
        self.send_enter_ap()


class RTL8720MP(RTL8720MP_AP, RTL8720MP_STA):
    def __init__(self, sta_connection, ap_connection):
        # self.sta = ATClient(sta_connection)
        # self.ap = ATClient(ap_connection)
        RTL8720MP_AP.__init__(self, ap_connection)
        RTL8720MP_STA.__init__(self, sta_connection)

    def close(self):
        self.ap.close()

    # ---- General ----
    def factory_reset(self) -> None:
        r = self.ap.exec("ATSY", timeout=8.0, expect="Available heap")
        if not r.ok:
            raise ATError(f"Factory reset failed: {r.raw}")

    def get_version(self) -> str:
        r = self.ap.exec("ATS?", timeout=2.0, expect="SW VERSION: v.7.1.20260408")
        if not r.ok:
            raise ATError(f"Get version failed: {r.raw}")
        return "\n".join(r.lines) if r.lines else ""
