import time
import telnetlib
from typing import Union, List


class TelnetDriver:
    def __init__(self, host, port=23, timeout=5.0, newline=b"\r\n"):
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)
        self.newline = newline
        self._tn = None

    def is_connected(self):
        return self._tn is not None

    def connect(self):
        self._tn = telnetlib.Telnet(self.host, self.port, self.timeout)

    def close(self):
        if self._tn:
            try:
                self._tn.close()
            finally:
                self._tn = None

    def send(self, data: Union[bytes, str]):
        if not self.is_connected():
            self.connect()

        if isinstance(data, str):
            data = data.encode("utf-8")

        # 统一换行：把 \n 转成 \r\n（Cisco 场景通常 OK）
        data = data.replace(b"\n", self.newline)
        self._tn.write(data)
        return True

    def receive(self, timeout=0.2):
        """在 timeout 时间内把当前可读数据尽量读出来。"""
        if not self.is_connected():
            self.connect()

        end = time.time() + (timeout or 0)
        buf = b""
        while time.time() < end:
            chunk = self._tn.read_very_eager()
            if chunk:
                buf += chunk
            else:
                time.sleep(0.02)
        return buf

    def send_receive(self, data, timeout=0.8, read_idle=0.2):
        """发送后读取：直到总 timeout 到，或连续 read_idle 没新数据。"""
        self.send(data)

        end = time.time() + timeout
        last_rx = time.time()
        buf = b""

        while time.time() < end:
            chunk = self._tn.read_very_eager()
            if chunk:
                buf += chunk
                last_rx = time.time()
            else:
                if time.time() - last_rx >= read_idle:
                    break
                time.sleep(0.02)

        return buf
