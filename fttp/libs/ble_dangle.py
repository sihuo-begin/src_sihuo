import serial
import time
from typing import Union, List, Optional
from src.libs.cmd_generator import NetworkFrameBuilder
import numpy as np


class UARTTimeoutError(Exception):
    pass


class UARTCommunicationError(Exception):
    pass


class Nrf:
    def __init__(self, port: str,
        baudrate: int = 19200,
        timeout: float = 2.0,
        idle_interval: float = 0.003,
        flush_before_send: bool = True,
        read_size: int = 256,):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.idle_interval = idle_interval
        self.flush_before_send = flush_before_send
        self.read_size = read_size
        self.channel_mapping = {
            "ch0": [0x41, 0x00],
            "ch18": [0x54, 0x00],
            "ch36": [0x66, 0x00],
        }
        self.rx_ch = [0x01, 0x00]
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
        except Exception as e:
            raise UARTCommunicationError(f"initial failed: {e}")

    def send(self, data: Union[bytes, List[int], str]):
        """send bytes / list[int] / str(utf-8)"""
        try:
            if self.flush_before_send:
                self.ser.reset_input_buffer()
            if isinstance(data, bytes):
                to_send = data
            elif isinstance(data, list):
                to_send = bytes(data)
            elif isinstance(data, str):
                to_send = data.encode("utf-8")
            else:
                raise UARTCommunicationError("unsupported data type")

            self.ser.write(to_send)
        except Exception as e:
            raise UARTCommunicationError(f"send failed: {e}")

    def receive(self, timeout: Optional[float] = None, idle_interval: Optional[float] = None) -> bytes:
        """
        读取“不定长回包”的推荐方式：idle gap判定结束 + 总超时兜底
        - 当收到数据后，如果连续 idle_interval 没再收到新字节 -> 认为本次回包结束
        - 若一直没数据，直到 timeout -> 抛 UARTTimeoutError
        """
        timeout = self.timeout if timeout is None else timeout
        idle_interval = self.idle_interval if idle_interval is None else idle_interval

        data = bytearray()
        start = time.time()
        last_rx = None

        # 使用短超时轮询，使“空闲判定”准确且返回更快
        old_timeout = self.ser.timeout
        self.ser.timeout = idle_interval

        try:
            while True:
                waiting = self.ser.in_waiting
                n = waiting if waiting > 0 else 1
                if n > self.read_size:
                    n = self.read_size

                chunk = self.ser.read(n)

                now = time.time()
                if chunk:
                    data.extend(chunk)
                    last_rx = now
                    continue
                if data:
                    if last_rx is not None and (now - last_rx) >= idle_interval:
                        break
                if (now - start) >= timeout:
                    break

            if not data:
                raise UARTTimeoutError("timeout: no data received")
            return bytes(data)
        except UARTTimeoutError:
            raise
        except Exception as e:
            raise UARTCommunicationError(f"receive failed: {e}")
        finally:
            self.ser.timeout = old_timeout

    def receive_data(self):
        """
        连续接收数据，直到空闲idle_interval后自动返回，或总超时timeout
        """
        time.sleep(0.01)
        return self.ser.read_all()

    def send_receive(self, data: Union[bytes, List[int], str], timeout=None):
        timeout = timeout if timeout is not None else self.timeout
        try:
            self.send(data)
            return self.receive_data()
            # return self.receive(timeout)
        except (UARTTimeoutError, UARTCommunicationError) as e:
            raise

    def close(self):
        self.ser.close()

    def intial(self):
        response = self.send_receive([0x00, 0x00])
        print(response)

    def rx_mode(self):
        response = self.send_receive([0x09, 0x00])
        print(response)

    def setting_phy(self):
        response = self.send_receive([0x02, 0x04])
        print(response)

    def setting_ch(self, ch):
        ch_data = self.channel_mapping[ch]
        response = self.send_receive(ch_data)
        print(response)

    def read_rssi(self):
        response = self.send_receive([0xC0, 0x00])
        print("stop:", response)
        response = self.send_receive([0x80, 0x17])
        print("rssi", response)
        return response

    def stop_tx(self):
        response = self.send_receive([0xC0, 0x00])
        print("stop:", response)

    def tx_mode(self):
        # response = self.send_receive([0x80, 0x0B])
        response = self.send_receive([0x09, 0xDB])
        print("tx_mode:", response)

    def set_rx_ch(self):
        response = self.send_receive(self.rx_ch)
        print("rx_ch", response)

    def package_len(self):
        response = self.send_receive([0x03, 0x00])
        print("rx_ch", response)

    def send_package(self):
        response = self.send_receive([0x81, 0x94])
        print("package start:", response)


def tx_run(ch="ch1", port="COM3"):
    nrf = Nrf(port=port)
    nrf.intial()
    nrf.rx_mode()
    nrf.setting_phy()
    # nrf.setting_ch(ch=ch)
    rssi_list = []
    for _ in range(3):
        nrf.setting_ch(ch=ch)
        rssi = list(nrf.read_rssi())[1] * -1
        rssi_list.append(rssi)
    # rssi = round(np.average(rssi_list), 0)
    rssi = round(np.average(rssi_list[1:]), 0)
    nrf.stop_tx()
    nrf.close()
    return rssi


# if __name__ == "__main__":
#     nrf = nrf(port="COM3")
#     nrf.intial()
#     # nrf.rx_mode()
#     # nrf.setting_phy()
#     # nrf.setting_ch(ch='ch1')
#     # rssi = list(nrf.read_rssi())
#     # print(rssi)
#     nrf.tx_mode()
#     nrf.set_rx_ch()
#     nrf.package_len()
#     nrf.setting_phy()
#     nrf.send_package()
#     # time.sleep(1.25)
#     # nrf.stop_tx()
