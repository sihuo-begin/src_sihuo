import time
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple

import serial


# -----------------------------
# Exceptions
# -----------------------------
class ModbusError(Exception):
    """Base class for Modbus errors."""


class ModbusTimeoutError(ModbusError):
    """No complete response frame arrived within timeout."""


class ModbusCRCError(ModbusError):
    """CRC check failed."""


class ModbusProtocolError(ModbusError):
    """Response frame malformed, mismatched, or unexpected."""


class ModbusExceptionResponse(ModbusError):
    """Modbus exception response received from slave."""

    def __init__(self, slave_id: int, function_code: int, exception_code: int):
        super().__init__(
            f"Modbus exception response: slave={slave_id} func=0x{function_code:02X} exc=0x{exception_code:02X}"
        )
        self.slave_id = slave_id
        self.function_code = function_code
        self.exception_code = exception_code


# -----------------------------
# Config
# -----------------------------
@dataclass(frozen=True)
class ModbusRTUConfig:
    port: str
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"          # 'N', 'E', 'O'
    stopbits: int = 1
    timeout_s: float = 2.0     # overall response timeout (your requirement)
    inter_char_timeout_s: float = 0.2  # gap timeout for partial frames (RTU)
    flush_before_send: bool = True


# -----------------------------
# Utils: CRC16 (Modbus)
# -----------------------------
def crc16_modbus(data: bytes) -> int:
    """Compute Modbus RTU CRC16. Returns 0-65535."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def append_crc(frame_wo_crc: bytes) -> bytes:
    crc = crc16_modbus(frame_wo_crc)
    # Modbus RTU CRC is little-endian: low byte first
    return frame_wo_crc + bytes([crc & 0xFF, (crc >> 8) & 0xFF])


def verify_crc(frame: bytes) -> bool:
    if len(frame) < 3:
        return False
    data = frame[:-2]
    recv_crc_lo = frame[-2]
    recv_crc_hi = frame[-1]
    recv_crc = recv_crc_lo | (recv_crc_hi << 8)
    calc_crc = crc16_modbus(data)
    return recv_crc == calc_crc


# -----------------------------
# RTU Driver
# -----------------------------
class ModbusRTUMasterDriver:
    """
    Synchronous, blocking Modbus RTU master (client).

    Supports:
      - Read Holding Registers (0x03)
      - Write Single Register (0x06)

    Timeout logic:
      - overall response timeout: config.timeout_s
      - inter-character timeout: config.inter_char_timeout_s (if partial bytes arrived)
    """

    def __init__(self, config: ModbusRTUConfig):
        self.config = config
        self._lock = threading.Lock()
        self._ser: Optional[serial.Serial] = None

    # ---- lifecycle ----
    def open(self) -> None:
        if self._ser and self._ser.is_open:
            return

        # Important: set serial timeout small and do our own timing
        # so we can implement inter-char timeout cleanly.
        self._ser = serial.Serial(
            port=self.config.port,
            baudrate=self.config.baudrate,
            bytesize=self.config.bytesize,
            parity=self.config.parity,
            stopbits=self.config.stopbits,
            timeout=0.05,  # short read timeout; overall is managed by us
            write_timeout=self.config.timeout_s,
        )

    def close(self) -> None:
        if self._ser:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ---- public API ----
    def read_holding_registers(self, slave_id: int, start_address: int, quantity: int) -> List[int]:
        """
        Function 0x03.
        Returns list of register values (0-65535).
        """
        if not (1 <= quantity <= 125):
            raise ValueError("quantity must be 1..125 for function 0x03")
        pdu = bytes([
            slave_id & 0xFF,
            0x03,
            (start_address >> 8) & 0xFF, start_address & 0xFF,
            (quantity >> 8) & 0xFF, quantity & 0xFF,
        ])
        req = append_crc(pdu)

        # Expected response: addr, func, byte_count, data(2*qty), crc(2)
        expected_len = 1 + 1 + 1 + 2 * quantity + 2
        resp = self._request(slave_id, 0x03, req, expected_len=expected_len)

        # Parse
        byte_count = resp[2]
        if byte_count != 2 * quantity:
            raise ModbusProtocolError(f"Unexpected byte_count={byte_count}, expected={2*quantity}")

        regs = []
        data = resp[3:-2]
        for i in range(0, len(data), 2):
            regs.append((data[i] << 8) | data[i + 1])
        return regs

    def write_single_register(self, slave_id: int, address: int, value: int) -> None:
        """
        Function 0x06.
        Writes a single holding register.
        """
        if not (0 <= value <= 0xFFFF):
            raise ValueError("value must be 0..65535")

        pdu = bytes([
            slave_id & 0xFF,
            0x06,
            (address >> 8) & 0xFF, address & 0xFF,
            (value >> 8) & 0xFF, value & 0xFF,
        ])
        req = append_crc(pdu)

        # Response is an echo of request (8 bytes)
        expected_len = 8
        resp = self._request(slave_id, 0x06, req, expected_len=expected_len)

        # Validate echo
        if resp[:-2] != req[:-2]:
            raise ModbusProtocolError("Write response does not match request (echo mismatch)")

    # ---- internal request/response core ----
    def _request(self, slave_id: int, function_code: int, request_frame: bytes, expected_len: int) -> bytes:
        if not self._ser or not self._ser.is_open:
            raise RuntimeError("Serial port not open. Call open() first.")

        with self._lock:
            if self.config.flush_before_send:
                self._flush_input()

            # Send
            self._ser.write(request_frame)
            self._ser.flush()

            # Receive
            resp = self._read_frame(expected_len=expected_len)

            # Basic checks
            if len(resp) < 5:
                raise ModbusProtocolError(f"Response too short: {len(resp)} bytes")

            if not verify_crc(resp):
                raise ModbusCRCError(f"CRC mismatch: {resp.hex()}")

            r_slave = resp[0]
            r_func = resp[1]

            if r_slave != (slave_id & 0xFF):
                raise ModbusProtocolError(f"Slave ID mismatch: got {r_slave}, expected {slave_id}")

            # Exception response: func | 0x80, length 5
            if r_func == (function_code | 0x80):
                if len(resp) != 5:
                    raise ModbusProtocolError(f"Malformed exception response length={len(resp)}")
                exc_code = resp[2]
                raise ModbusExceptionResponse(slave_id=slave_id, function_code=function_code, exception_code=exc_code)

            if r_func != (function_code & 0xFF):
                raise ModbusProtocolError(f"Function code mismatch: got 0x{r_func:02X}, expected 0x{function_code:02X}")

            return resp

    def _flush_input(self) -> None:
        # Clear any stale bytes (prevents old response bytes from confusing next request)
        try:
            self._ser.reset_input_buffer()
        except Exception:
            # fallback
            _ = self._ser.read(4096)

    def _read_frame(self, expected_len: int) -> bytes:
        """
        Read exactly one RTU response frame.
        Strategy:
          - wait until we get enough bytes to satisfy expected_len
          - apply overall timeout and inter-character timeout
        """
        deadline = time.monotonic() + self.config.timeout_s
        buf = bytearray()
        last_byte_time: Optional[float] = None

        while True:
            now = time.monotonic()

            # Overall timeout
            if now > deadline:
                raise ModbusTimeoutError(f"Response timeout after {self.config.timeout_s}s, got {len(buf)} bytes: {buf.hex()}")

            # If we already have partial data, enforce inter-character timeout
            if buf and last_byte_time is not None:
                if (now - last_byte_time) > self.config.inter_char_timeout_s:
                    raise ModbusTimeoutError(
                        f"Inter-character timeout after {self.config.inter_char_timeout_s}s, partial frame: {buf.hex()}"
                    )

            # If already got full expected length, return
            if len(buf) >= expected_len:
                return bytes(buf[:expected_len])

            # Read remaining bytes (at least 1)
            to_read = max(1, expected_len - len(buf))
            chunk = self._ser.read(to_read)

            if chunk:
                buf.extend(chunk)
                last_byte_time = time.monotonic()
                continue

            # No bytes this iteration; loop continues until deadline/inter-char triggers

    # Optional: small helper for quick connectivity check
    def ping_read_1(self, slave_id: int, address: int = 0, timeout_s: Optional[float] = None) -> int:
        """
        Read 1 holding register as a ping.
        If timeout_s is provided, temporarily override overall timeout.
        """
        if timeout_s is None:
            regs = self.read_holding_registers(slave_id, address, 1)
            return regs[0]

        # temporary override
        old = self.config
        tmp = ModbusRTUConfig(**{**old.__dict__, "timeout_s": float(timeout_s)})
        object.__setattr__(self, "config", tmp)  # bypass frozen dataclass
        try:
            regs = self.read_holding_registers(slave_id, address, 1)
            return regs[0]
        finally:
            object.__setattr__(self, "config", old)


# from modbus_rtu import ModbusRTUConfig, ModbusRTUMasterDriver, ModbusTimeoutError
#
# cfg = ModbusRTUConfig(
#     port="COM3",          # Windows 示例；Linux 如 "/dev/ttyUSB0"
#     baudrate=115200,      # 由配置决定
#     parity="N",
#     stopbits=1,
#     timeout_s=2.0,        # 你的要求
#     inter_char_timeout_s=0.2,
# )
#
# with ModbusRTUMasterDriver(cfg) as drv:
#     try:
#         regs = drv.read_holding_registers(slave_id=1, start_address=0x0000, quantity=2)
#         print("read regs:", regs)
#
#         drv.write_single_register(slave_id=1, address=0x0001, value=1234)
#         print("write ok")
#
#     except ModbusTimeoutError as e:
#         print("timeout:", e)