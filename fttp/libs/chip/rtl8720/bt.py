import re
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Pattern, Sequence, Union


Terminator = Union[str, Pattern[str], Callable[[str], bool]]


class BTError(RuntimeError):
    pass


class BTTimeout(TimeoutError):
    pass


@dataclass
class BTResponse:
    ok: bool
    lines: List[str]
    status_line: str
    raw: List[str]


@dataclass
class ScanEvent:
    addr: str
    addr_type: Optional[str]
    adv_type: Optional[str]
    rssi_dbm: int
    raw_block: List[str]


def _now() -> float:
    return time.monotonic()


def _norm(s: str) -> str:
    s = s.replace("\r", "").replace("\n", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


class BTATClient:
    """
    BLE AT client based on a platform connection.

    Required connection methods:
      - send(data)
      - recv()

    Optional:
      - close()

    Notes:
      - This client owns only the RX thread.
      - It does NOT own the external connection lifecycle.
      - close() stops background RX thread only.
    """

    def __init__(self, connection, recv_poll_interval: float = 0.01):
        self.conn = connection
        self.recv_poll_interval = recv_poll_interval

        self._rx_buf = ""
        self._rx_lines: List[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

    def close(self):
        self._stop.set()
        try:
            self._rx_thread.join(timeout=1.0)
        except Exception:
            pass

    def _to_text(self, data) -> str:
        if data is None:
            return ""
        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        return str(data)

    def _send_text(self, text: str):
        try:
            self.conn.send(text)
        except TypeError:
            self.conn.send(text.encode("utf-8"))

    def _rx_loop(self):
        while not self._stop.is_set():
            try:
                chunk = self.conn.recv()
            except Exception:
                time.sleep(self.recv_poll_interval)
                continue

            if not chunk:
                time.sleep(self.recv_poll_interval)
                continue

            self._rx_buf += self._to_text(chunk)

            while "\n" in self._rx_buf:
                line, self._rx_buf = self._rx_buf.split("\n", 1)
                line = line.strip("\r\n")
                if not line:
                    continue
                with self._lock:
                    self._rx_lines.append(line)

    def flush_input(self, drain_time: float = 0.2):
        """
        Clear buffered lines collected by RX thread.
        """
        end = _now() + drain_time
        while _now() < end:
            with self._lock:
                if self._rx_lines:
                    self._rx_lines.clear()
            time.sleep(0.01)

    def send_cmd(self, cmd: str):
        self._send_text(cmd + "\r\n")

    @staticmethod
    def _match(line: str, t: Terminator) -> bool:
        if isinstance(t, re.Pattern):
            return bool(t.search(line))

        if callable(t) and not isinstance(t, str):
            return bool(t(line))

        s = _norm(t)
        l = _norm(line)
        if not s or not l:
            return False

        su = s.upper()
        lu = l.upper()

        if lu == su:
            return True
        if lu.startswith(su):
            return True
        return su in lu

    def exec(
        self,
        cmd: str,
        *,
        timeout: float = 5.0,
        success_terms: Sequence[Terminator],
        error_terms: Sequence[Terminator] = ("ERROR",),
        echo_cmd: bool = False,
        include_status_line: bool = True,
        flush_before_send: bool = True,
    ) -> BTResponse:
        """
        Send command and wait until any success term or error term appears.
        """
        if flush_before_send:
            self.flush_input()

        self.send_cmd(cmd)

        deadline = _now() + timeout
        raw: List[str] = []
        payload: List[str] = []

        cursor = 0

        while _now() < deadline:
            with self._lock:
                new_lines = self._rx_lines[cursor:]
                cursor = len(self._rx_lines)

            if not new_lines:
                time.sleep(0.01)
                continue

            for line in new_lines:
                raw.append(line)

                if (not echo_cmd) and _norm(line) == _norm(cmd):
                    continue

                for t in error_terms:
                    if self._match(line, t):
                        if include_status_line:
                            payload.append(line)
                        return BTResponse(
                            ok=False,
                            lines=payload,
                            status_line=line,
                            raw=raw,
                        )

                for t in success_terms:
                    if self._match(line, t):
                        if include_status_line:
                            payload.append(line)
                        return BTResponse(
                            ok=True,
                            lines=payload,
                            status_line=line,
                            raw=raw,
                        )

                payload.append(line)

        raise BTTimeout(f"Timeout waiting response for {cmd!r}, raw={raw}")

    def collect_lines(self, duration: float) -> List[str]:
        """
        Collect async lines for a duration.
        """
        end = _now() + duration
        out: List[str] = []

        with self._lock:
            cursor = len(self._rx_lines)

        while _now() < end:
            with self._lock:
                new_lines = self._rx_lines[cursor:]
                cursor = len(self._rx_lines)
            if new_lines:
                out.extend(new_lines)
            time.sleep(0.02)

        return out


class BTCommonOps:
    """
    Common helpers shared by Central / Peripheral / General ops.

    Required members on self:
      - self.central_at: BTATClient
      - self.peripheral_at: BTATClient
    """

    RE_CONN_ID = re.compile(r"\bconn_id\s+(\d+)\b", re.IGNORECASE)
    RE_BT_ADDR = re.compile(r"\b([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\b")
    RE_HEX12 = re.compile(r"\b([0-9a-fA-F]{12})\b")
    RE_RSSI = re.compile(r"\brssi\b\s*(-?\d+)\b", re.IGNORECASE)
    RE_ADDRTYPE = re.compile(r"\bAddrType\b\s*(public|random)\b", re.IGNORECASE)
    RE_ADVTYPE = re.compile(
        r"^\s*(NON_CONNECTABLE|CONNECTABLE|SCAN_RSP|ADV_[A-Z0-9_]+)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def _client_of(channel: str, central_at: BTATClient, peripheral_at: BTATClient) -> BTATClient:
        ch = channel.strip().lower()
        if ch in ("sta", "central"):
            return central_at
        if ch in ("ap", "peripheral"):
            return peripheral_at
        raise ValueError(
            f"Unsupported channel: {channel!r}, expected 'sta'/'central' or 'ap'/'peripheral'"
        )

    @staticmethod
    def _mac12(mac: str) -> str:
        hexs = "".join(c for c in mac.strip() if c.lower() in "0123456789abcdef")
        if len(hexs) != 12:
            raise ValueError(f"Invalid MAC: {mac!r}")
        return hexs.lower()

    @staticmethod
    def _mac_colon(mac: str) -> str:
        hexs = "".join(c for c in mac.strip() if c.lower() in "0123456789abcdef")
        if len(hexs) != 12:
            raise ValueError(f"Invalid MAC: {mac!r}")
        return ":".join(hexs[i:i + 2] for i in range(0, 12, 2)).lower()

    @classmethod
    def _extract_bd_addr(cls, lines: List[str]) -> Optional[str]:
        """
        Parse address from lines like:
          BT ADDRESS: 2c:05:47:88:f2:ca
          local bd addr: 0x2c:05:47:88:f2:ca

        Return normalized aa:bb:cc:dd:ee:ff
        """
        for line in lines:
            s = line.replace("0x", "")
            m = cls.RE_BT_ADDR.search(s)
            if m:
                return m.group(1).lower()
        return None

    @classmethod
    def _parse_conn_id(cls, lines: List[str]) -> int:
        for line in lines:
            m = cls.RE_CONN_ID.search(line)
            if m:
                return int(m.group(1))
        raise BTError(f"conn_id not found in response: {lines}")

    @staticmethod
    def _parse_read_value(lines: List[str]) -> bytes:
        for line in lines:
            if "READ VALUE:" in line:
                vals = re.findall(r"0x([0-9A-Fa-f]{2})", line)
                return bytes(int(x, 16) for x in vals)
        raise BTError(f"READ VALUE not found in response: {lines}")


class BTGeneralOps(BTCommonOps):
    """
    Common commands that can be sent on either channel.
    """

    def get_sw_version(self, channel: str = "sta") -> str:
        client = self._client_of(channel, self.central_at, self.peripheral_at)
        r = client.exec(
            "ATS?",
            timeout=2.0,
            success_terms=(
                "SW VERSION",
                re.compile(r"v\.\d+\.\d+\.\d+", re.I),
            ),
        )
        if not r.ok:
            raise BTError(f"ATS? failed on {channel}: {r.raw}")
        return "\n".join(r.lines)

    def factory_reset(self, channel: str = "sta") -> None:
        client = self._client_of(channel, self.central_at, self.peripheral_at)
        r = client.exec(
            "ATSY",
            timeout=10.0,
            success_terms=("Available heap", "available heap"),
        )
        if not r.ok:
            raise BTError(f"Factory reset failed on {channel}: {r.raw}")

    def get_ble_stack_version(self, channel: str = "sta") -> str:
        client = self._client_of(channel, self.central_at, self.peripheral_at)
        r = client.exec(
            "ATBV",
            timeout=2.0,
            success_terms=("btgap_buildnum",),
        )
        if not r.ok:
            raise BTError(f"ATBV failed on {channel}: {r.raw}")
        return "\n".join(r.lines)


class BTCentralOps(BTCommonOps):
    """
    Central role operations.
    All commands in this mixin go through self.central_at.
    """

    def __init__(self):
        self.latest_scan: Dict[str, ScanEvent] = {}
        self.central_local_bd_addr: Optional[str] = None
        self.default_peer_addr: Optional[str] = None
        self.last_connected_peer: Optional[str] = None

    def set_default_peer_addr(self, mac: str) -> None:
        self.default_peer_addr = self._mac_colon(mac)

    def get_default_peer_addr(self) -> Optional[str]:
        return self.default_peer_addr

    def get_central_local_bd_addr(self) -> Optional[str]:
        return self.central_local_bd_addr

    def central_start(self) -> Optional[str]:
        """
        Start BLE central role and parse local bd addr if present.
        """
        r = self.central_at.exec(
            "ATBc=1",
            timeout=20.0,
            success_terms=(
                "Start upperStack",
                "local bd addr:",
                "available heap",
            ),
        )
        if not r.ok:
            raise BTError(f"ATBc=1 failed: {r.raw}")

        addr = self._extract_bd_addr(r.raw)
        if addr:
            self.central_local_bd_addr = addr

        return self.central_local_bd_addr

    def central_stop(self) -> None:
        r = self.central_at.exec(
            "ATBc=0",
            timeout=5.0,
            success_terms=(
                "[BLE Central]BT Stack deinitalized",
                "_AT_BLE_CENTRAL_[OFF]",
            ),
        )
        if not r.ok:
            raise BTError(f"ATBc=0 failed: {r.raw}")

    def connect(self, peripheral_mac: Optional[str] = None) -> int:
        """
        Connect to a peripheral via central connection.

        Priority:
          1. explicit peripheral_mac
          2. self.default_peer_addr
        """
        target = peripheral_mac or self.default_peer_addr
        if not target:
            raise ValueError("peripheral_mac is not provided and no default_peer_addr is set")

        target_colon = self._mac_colon(target)
        target_mac12 = self._mac12(target_colon)

        r = self.central_at.exec(
            f"ATBC=P,{target_mac12}",
            timeout=10.0,
            success_terms=("Connected success conn_id",),
        )
        if not r.ok:
            raise BTError(f"ATBC connect failed: {r.raw}")

        self.last_connected_peer = target_colon
        return self._parse_conn_id(r.raw)

    def disconnect(self, conn_id: int) -> None:
        r = self.central_at.exec(
            f"ATBD={conn_id}",
            timeout=5.0,
            success_terms=("# Disconnect conn_id",),
        )
        if not r.ok:
            raise BTError(f"ATBD failed: {r.raw}")

    def get_connection_info(self) -> str:
        r = self.central_at.exec(
            "ATBI",
            timeout=3.0,
            success_terms=("active link num",),
        )
        if not r.ok:
            raise BTError(f"ATBI failed: {r.raw}")
        return "\n".join(r.lines)

    def discover_services(self, conn_id: int) -> List[str]:
        r = self.central_at.exec(
            f"ATBG=ALL,{conn_id}",
            timeout=5.0,
            success_terms=(
                re.compile(r"ALL SRV UUID16", re.I),
                re.compile(r"uuid16\s+0x[0-9a-f]+", re.I),
            ),
        )
        if not r.ok:
            raise BTError(f"ATBG failed: {r.raw}")
        return r.lines

    def write_char(self, conn_id: int, handle: int, data: bytes, write_type: int = 1) -> None:
        """
        Example:
          ATBW=0,1,0x11,0x4,0xAA,0xBB,0xCC,0xDD

        Format:
          ATBW=conn_id,write_type,handle,len,byte_array
        """
        if not data:
            raise ValueError("data is empty")

        byte_items = ",".join(f"0x{b:02X}" for b in data)
        cmd = f"ATBW={conn_id},{write_type},0x{handle:X},0x{len(data):X},{byte_items}"

        r = self.central_at.exec(
            cmd,
            timeout=5.0,
            success_terms=("# WRITE RESULT: cause 0x0",),
        )
        if not r.ok:
            raise BTError(f"ATBW failed: {r.raw}")

    def read_char(self, conn_id: int, handle: int) -> bytes:
        r = self.central_at.exec(
            f"ATBR={conn_id},0x{handle:X}",
            timeout=5.0,
            success_terms=("READ VALUE:",),
        )
        if not r.ok:
            raise BTError(f"ATBR failed: {r.raw}")
        return self._parse_read_value(r.raw)

    def parse_scan_events_from_lines(self, lines: List[str]) -> List[ScanEvent]:
        events: List[ScanEvent] = []

        block: List[str] = []
        addr: Optional[str] = None
        rssi: Optional[int] = None
        addr_type: Optional[str] = None
        adv_type: Optional[str] = None

        def flush_if_ready():
            nonlocal block, addr, rssi, addr_type, adv_type
            if addr and rssi is not None:
                ev = ScanEvent(
                    addr=addr.lower(),
                    addr_type=addr_type.lower() if addr_type else None,
                    adv_type=adv_type.upper() if adv_type else None,
                    rssi_dbm=int(rssi),
                    raw_block=block[:],
                )
                self.latest_scan[ev.addr] = ev
                events.append(ev)
                block = []
                addr = None
                rssi = None
                addr_type = None
                adv_type = None

        for line in lines:
            if line.startswith("#"):
                continue

            block.append(line)

            m = self.RE_ADVTYPE.search(line)
            if m and adv_type is None:
                adv_type = m.group(1)

            m = self.RE_ADDRTYPE.search(line)
            if m:
                addr_type = m.group(1)

            m = self.RE_BT_ADDR.search(line)
            if m:
                addr = m.group(1)

            m = self.RE_RSSI.search(line)
            if m:
                rssi = int(m.group(1))

            flush_if_ready()

        return events

    def collect_scan_events(self, duration: float = 5.0) -> List[ScanEvent]:
        lines = self.central_at.collect_lines(duration)
        return self.parse_scan_events_from_lines(lines)

    def get_latest_rssi(self, addr: str) -> Optional[int]:
        ev = self.latest_scan.get(self._mac_colon(addr))
        return ev.rssi_dbm if ev else None


class BTPeripheralOps(BTCommonOps):
    """
    Peripheral role operations.
    All commands in this mixin go through self.peripheral_at.
    """

    def __init__(self):
        self.peripheral_local_bd_addr: Optional[str] = None

    def get_peripheral_local_bd_addr(self) -> Optional[str]:
        return self.peripheral_local_bd_addr

    def peripheral_start(self) -> str:
        """
        Start BLE peripheral advertising and parse local bd addr from logs.

        Returns:
            local bd addr, like '2c:05:47:88:f2:ca'
        """
        r = self.peripheral_at.exec(
            "ATBp=1",
            timeout=20.0,
            success_terms=(
                "GAP adv start",
                "[BLE peripheral] GAP stack ready",
                "local bd addr:",
                "BT ADDRESS:",
            ),
        )
        if not r.ok:
            raise BTError(f"ATBp=1 failed: {r.raw}")

        addr = self._extract_bd_addr(r.raw)
        if addr:
            self.peripheral_local_bd_addr = addr
            # 常见workflow：peripheral启动后，这个地址就是central要连接的目标地址
            self.default_peer_addr = addr

        if not self.peripheral_local_bd_addr:
            raise BTError(
                f"Peripheral started, but local bd addr not found in response: {r.raw}"
            )

        return self.peripheral_local_bd_addr

    def peripheral_stop(self) -> None:
        r = self.peripheral_at.exec(
            "ATBp=0",
            timeout=5.0,
            success_terms=(
                "[BLE Peripheral]BT Stack deinitalized",
                "_AT_BLE_PERIPHERAL_[OFF]",
            ),
        )
        if not r.ok:
            raise BTError(f"ATBp=0 failed: {r.raw}")


class RTL8720BT(BTGeneralOps, BTCentralOps, BTPeripheralOps):
    """
    Unified BLE facade with separated connections:

      - sta_connection -> BLE central command channel
      - ap_connection  -> BLE peripheral command channel
    """

    def __init__(self, sta_connection, ap_connection, recv_poll_interval: float = 0.01):
        self.central_at = BTATClient(ap_connection, recv_poll_interval=recv_poll_interval)
        self.peripheral_at = BTATClient(sta_connection, recv_poll_interval=recv_poll_interval)

        BTCentralOps.__init__(self)
        BTPeripheralOps.__init__(self)

    def close(self):
        """
        Stop both RX threads.
        Do NOT close externally-owned physical connections here.
        """
        err: Optional[Exception] = None

        try:
            self.central_at.close()
        except Exception as e:
            err = e

        try:
            self.peripheral_at.close()
        except Exception as e:
            if err is None:
                err = e

        if err is not None:
            raise err

    # backward-style aliases
    @property
    def at(self) -> BTATClient:
        """
        'at' alias -> central channel
        """
        return self.central_at

    @property
    def ap(self) -> BTATClient:
        """
        'ap' alias -> peripheral channel
        """
        return self.peripheral_at
