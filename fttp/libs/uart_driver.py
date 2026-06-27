import time
from typing import Union, List, Optional

import serial


class UARTTimeoutError(Exception):
    pass


class UARTCommunicationError(Exception):
    pass


class UART:
    def __init__(self, port, baudrate=38400, parity="N", timeout=2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.idle_interval = 0.05
        self.ser: Optional[serial.Serial] = None
        # self.connect()

    def _normalize_parity(self):
        parity_map = {
            "N": serial.PARITY_NONE,
            "E": serial.PARITY_EVEN,
            "O": serial.PARITY_ODD,
            "M": serial.PARITY_MARK,
            "S": serial.PARITY_SPACE,
        }
        return parity_map.get(str(self.parity).upper(), serial.PARITY_NONE)

    def _invalidate_serial(self):
        """
        废弃当前串口句柄。
        不负责自动恢复，只负责清理。
        """
        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except Exception:
                pass
            finally:
                self.ser = None

    def _reset_buffers(self):
        if self.ser is None:
            return
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass
        try:
            self.ser.reset_output_buffer()
        except Exception:
            pass

    def _to_bytes(self, data: Union[bytes, bytearray, List[int], str]):
        if isinstance(data, bytes):
            return data
        if isinstance(data, bytearray):
            return bytes(data)
        if isinstance(data, list):
            return bytes(data)
        if isinstance(data, str):
            return data.encode("utf-8")
        raise UARTCommunicationError(f"不支持的数据类型: {type(data)}")

    def connect(self):
        """
        显式连接/重连串口。
        """
        self._invalidate_serial()
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=self._normalize_parity(),
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self._reset_buffers()
            return True
        except Exception as e:
            self.ser = None
            raise UARTCommunicationError(f"串口 {self.port} 连接失败: {e}")

    def reconnect(self, delay=1.0, retries=3):
        """
        显式重连，不在 send/receive 中自动调用。
        """
        last_error = None
        self._invalidate_serial()

        for _ in range(retries):
            try:
                if delay > 0:
                    time.sleep(delay)
                self.connect()
                return True
            except Exception as e:
                last_error = e

        raise UARTCommunicationError(f"串口 {self.port} 重连失败: {last_error}")

    def close(self):
        self._invalidate_serial()

    def is_connected(self):
        """
        仅表示对象层 open 状态。
        """
        return self.ser is not None and self.ser.is_open

    def probe(self):
        """
        显式健康检查，不做自动恢复。
        """
        ser = self.ser
        if ser is None:
            return False

        try:
            if not ser.is_open:
                self._invalidate_serial()
                return False

            _ = ser.in_waiting
            try:
                _ = ser.cts
            except Exception:
                pass
            return True
        except Exception:
            self._invalidate_serial()
            return False

    def ensure_connected(self, reconnect=True, delay=1.0, retries=3):
        """
        显式恢复接口，供上层主动调用。
        """
        if self.probe():
            return True

        if not reconnect:
            return False

        try:
            self.reconnect(delay=delay, retries=retries)
            return self.probe()
        except Exception:
            return False

    def send(self, data: Union[bytes, bytearray, List[int], str]):
        """
        真实发送。
        不做预检查，不自动恢复。
        一旦失败，立即作废坏句柄并抛异常。
        """
        ser = self.ser
        if ser is None:
            raise UARTCommunicationError(f"串口 {self.port} 未连接")

        try:
            to_send = self._to_bytes(data)
            written = ser.write(to_send)
            ser.flush()
            return written
        except Exception as e:
            self._invalidate_serial()
            raise UARTCommunicationError(f"发送数据失败: {e}")

    def receive(self, timeout=None):
        """
        真实接收。
        不做预恢复。
        一旦失败，立即作废坏句柄并抛异常。
        """
        ser = self.ser
        if ser is None:
            raise UARTCommunicationError(f"串口 {self.port} 未连接")

        timeout = self.timeout if timeout is None else timeout
        idle_interval = self.idle_interval

        data = bytearray()
        start_time = time.time()
        last_recv_time = None
        old_timeout = ser.timeout

        try:
            poll = min(0.05, idle_interval)
            ser.timeout = poll

            while True:
                n = ser.in_waiting
                chunk = ser.read(n if n > 0 else 256)
                now = time.time()

                if chunk:
                    data += chunk
                    last_recv_time = now
                    continue

                if (now - start_time) >= timeout:
                    break

                if last_recv_time is not None:
                    idle = now - last_recv_time
                    if idle >= idle_interval:
                        chunk2 = ser.read(ser.in_waiting or 256)
                        if chunk2:
                            data += chunk2
                            last_recv_time = time.time()
                            continue
                        break

            if not data:
                raise UARTTimeoutError("接收超时: 未收到任何数据")

            return bytes(data)

        except UARTTimeoutError:
            raise
        except Exception as e:
            self._invalidate_serial()
            raise UARTCommunicationError(f"接收数据失败: {e}")
        finally:
            current_ser = self.ser
            if current_ser is not None:
                try:
                    current_ser.timeout = old_timeout
                except Exception:
                    pass

    def send_receive(self, data: Union[bytes, bytearray, List[int], str], timeout=None):
        """
        真实收发。
        不做自动恢复。
        """
        timeout = self.timeout if timeout is None else timeout
        self.send(data)
        time.sleep(0.15)
        return self.receive(timeout)