import time
import threading
from datetime import datetime
from collections.abc import Sequence

from .uart_driver import UART, UARTCommunicationError, UARTTimeoutError
from .usb_driver import HIDCommandModule
from .telnet_driver import TelnetDriver


class ConnectionRegistry:
    """
    全局连接注册表，方便 GUI 或其他模块随时获取和管理所有连接实例。
    """

    _lock = threading.Lock()
    _instances = {}

    @classmethod
    def register(cls, name, conn):
        with cls._lock:
            cls._instances[name] = conn

    @classmethod
    def get(cls, name):
        with cls._lock:
            return cls._instances.get(name)

    @classmethod
    def all(cls):
        with cls._lock:
            return dict(cls._instances)

    @classmethod
    def remove(cls, name):
        with cls._lock:
            if name in cls._instances:
                del cls._instances[name]


class BaseConnection:
    """
    connection for import
    """

    def send(self, data):
        raise NotImplementedError

    def recv(self, *args, **kwargs):
        raise NotImplementedError

    def send_receive(self, data, *args, **kwargs):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def get_output_log(self):
        raise NotImplementedError

    def info(self):
        raise NotImplementedError


class UARTConnection(BaseConnection):
    def __init__(self, name, port, baudrate=38400, parity="N", timeout=2.0):
        self.name = name
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.timeout = timeout
        self.uart = UART(port, baudrate, parity, timeout)
        self._output_log = []
        ConnectionRegistry.register(name, self)

    def _log(self, msg):
        self._output_log.append(f"[{datetime.now()}] {msg}")

    def is_connected(self):
        """
        """
        try:
            return self.uart.probe()
        except Exception:
            return False

    def ensure_connected(self, reconnect_delay=1.5, retries=3):
        """
        """
        try:
            ok = self.uart.ensure_connected(
                reconnect=True,
                delay=reconnect_delay,
                retries=retries,
            )
            if ok:
                self._log(f"ensure_connected success: port={self.port}")
            else:
                self._log(f"ensure_connected failed: port={self.port}")
            return ok
        except Exception as e:
            self._log(f"ensure_connected exception: {e}")
            return False

    def connect(self):
        try:
            self.uart.connect()
            self._log(f"connected: port={self.port}")
            return True
        except Exception as e:
            self._log(f"connect failed: {e}")
            return False

    def send(self, data):
        self._log(f"->TX: {data}")
        try:
            return self.uart.send(data)
        except Exception as e:
            self._log(f"send failed: {e}")
            raise

    def recv(self, size=1024, timeout=None):
        try:
            res = self.uart.receive(timeout)
            self._log(f"<-RX: {res}")
            return res
        except Exception as e:
            self._log(f"recv failed: {e}")
            raise

    def send_receive(self, data, timeout=0.5):
        self._log(f"->TX: {data}")
        res = None
        for _ in range(3):
            try:
                res = self.uart.send_receive(data, timeout=timeout)
                self._log(f"<-RX: {res}")
                if res:
                    break
                time.sleep(0.15)
            except Exception as e:
                self._log(f"send_receive failed: {e}")
                time.sleep(0.15)
        return res

    def close(self):
        try:
            self.uart.close()
        finally:
            ConnectionRegistry.remove(self.name)

    def get_output_log(self):
        return "\n".join(self._output_log)

    def info(self):
        return {
            "name": self.name,
            "type": "UART",
            "port": self.port,
            "baudrate": self.baudrate,
            "timeout": self.timeout,
            "send": "send(data: bytes|list|str)",
            "recv": "recv(timeout=None) -> bytes",
        }


class TelnetConnection(BaseConnection):
    def __init__(self, name, host, port=23, timeout=5.0, newline="\r\n"):
        self.name = name
        self._output_log = []
        self.tn = TelnetDriver(host, port, timeout, newline.encode("utf-8"))
        ConnectionRegistry.register(name, self)

    def ensure_connected(self):
        if not self.tn.is_connected():
            try:
                self.tn.connect()
            except Exception as e:
                self._output_log.append(f"Connect failed: {e}")
                return False
        return True

    def send(self, data):
        self._output_log.append(f"[{datetime.now()}]->TX: {data}")
        return self.tn.send(data)

    def recv(self, size=1024, timeout=None):
        return self.tn.receive(timeout=timeout or 0.2)

    def send_receive(self, data, timeout=0.8):
        self._output_log.append(f"[{datetime.now()}]->TX: {data}")
        res = self.tn.send_receive(data, timeout=timeout)
        self._output_log.append(f"[{datetime.now()}]<-RX: {res!r}")
        return res

    def close(self):
        self.tn.close()
        ConnectionRegistry.remove(self.name)

    def get_output_log(self):
        return "\n".join(self._output_log)

    def info(self):
        return {
            "name": self.name,
            "type": "TELNET",
            "host": self.tn.host,
            "port": self.tn.port,
            "timeout": self.tn.timeout,
            "send": "send(data: bytes|str)",
            "recv": "recv(timeout=None) -> bytes",
        }


class USBHIDConnection(BaseConnection):
    def __init__(self, name, vid, pid, path, timeout=1.0, idle_time=0.1):
        self.name = name
        self._output_log = []
        self.hid = HIDCommandModule(vid, pid, path, timeout, idle_time)
        ConnectionRegistry.register(name, self)

    def ensure_connected(self):
        if not self.hid.is_connected():
            try:
                self.hid.connect()
            except Exception as e:
                self._output_log.append(f"Connect failed: {e}")
                return False
        return True

    def send(self, data):
        self._output_log.append(f"[{datetime.now()}]->TX: {data}")
        return self.hid.send_and_receive(data)

    def recv(self, *args, **kwargs):
        return None

    def send_receive(self, data, timeout=0.5, idle_factor=1):
        self._output_log.append(f"[{datetime.now()}]->TX: {data}")
        res = None
        for _ in range(3):
            res = self.hid.send_and_receive(data, idle_factor)
            if res:
                break
            time.sleep(0.15)

        if isinstance(res, Sequence) and not isinstance(res, (bytes, bytearray, list)):
            res = list(res)

        self._output_log.append(f"[{datetime.now()}]<-RX: {res}")
        return res

    def close(self):
        self.hid.disconnect()
        ConnectionRegistry.remove(self.name)

    def get_output_log(self):
        return "\n".join(self._output_log)

    def info(self):
        return {
            "name": self.name,
            "type": "USBHID",
            "vid": self.hid.vendor_id,
            "pid": self.hid.product_id,
            "timeout": self.hid.timeout,
            "send": "send(data: list[int]) -> response",
            "recv": "None",
        }


def parse_hex_or_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        if val.startswith("0x") or val.startswith("0X"):
            return int(val, 16)
        return int(val)
    raise ValueError(f"Unknown vid/pid format: {val}")


def create_connection(cfg, name=None):
    typ = cfg.get("type")
    if name is None:
        if typ in ("serial", "uart"):
            name = cfg.get("port")
        elif typ in ("usb", "hid"):
            name = f"usb_{cfg.get('vid')}_{cfg.get('pid')}"
        elif typ in ("telnet",):
            name = f"telnet_{cfg.get('host') or cfg.get('ip')}_{cfg.get('port', 23)}"
        else:
            raise ValueError("Unknown connection type and no name provided")

    existing = ConnectionRegistry.get(name)
    if existing:
        return existing

    if typ in ("serial", "uart"):
        return UARTConnection(
            name,
            cfg.get("port"),
            cfg.get("baudrate", 38400),
            cfg.get("parity", "N"),
            cfg.get("timeout", 2.0),
        )
    elif typ in ("usb", "hid"):
        vid = parse_hex_or_int(cfg["vid"])
        pid = parse_hex_or_int(cfg["pid"])
        path = cfg.get("path")
        return USBHIDConnection(
            name,
            vid,
            pid,
            path,
            cfg.get("timeout", 1.0),
            cfg.get("idle_time", 0.1),
        )
    elif typ in ("telnet",):
        host = cfg.get("host") or cfg.get("ip")
        return TelnetConnection(
            name=name,
            host=host,
            port=cfg.get("port", 23),
            timeout=cfg.get("timeout", 5.0),
            newline=cfg.get("newline", "\r\n"),
        )
    else:
        raise ValueError(f"Unknown connection type: {typ}")


def get_connection(name):
    return ConnectionRegistry.get(name)


def all_connections():
    return ConnectionRegistry.all()
