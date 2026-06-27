import serial
import time
from typing import Union, List
from src.libs import global_var as gl

# from .cmd_generator import NetworkFrameBuilder
from src.definition.tester_io_mapping import start_mapping


class UARTTimeoutError(Exception):
    pass


class UARTCommunicationError(Exception):
    pass


class SerialTester:
    def __init__(self, port, baudrate=115200, timeout=2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.idle_interval = 0.2
        try:
            # self.ser = serial.Serial(port, baudrate, timeout=timeout)
            self.ser = serial.Serial()
            self.ser.port = port
            self.ser.baudrate = baudrate
            self.ser.timeout = timeout
        except Exception as e:
            raise UARTCommunicationError(f"初始化串口失败: {e}")

    def send(self, data: Union[bytes, List[int], str]):
        """
        发送数据：支持bytes，list[int]（自动转bytes），str（自动转utf-8 bytes）
        """
        try:
            if isinstance(data, bytes):
                to_send = data
            elif isinstance(data, list):
                to_send = bytes(data)
            elif isinstance(data, str):
                to_send = data.encode("utf-8")
            else:
                raise UARTCommunicationError("不支持的数据类型")
            self.ser.write(to_send)

        except Exception as e:
            raise UARTCommunicationError(f"发送数据失败: {e}")

    def receive(self, timeout=None):
        """
        连续接收数据，直到空闲idle_interval后自动返回，或总超时timeout
        """
        return self.ser.read_all()

    def send_receive(self, data: Union[bytes, List[int], str], timeout=None):
        timeout = timeout if timeout is not None else self.timeout
        try:
            self.send(data)
            time.sleep(0.05)
            return self.receive(timeout)
        except (UARTTimeoutError, UARTCommunicationError) as e:
            raise

    def open(self):
        self.ser.open()

    def close(self):
        self.ser.close()

    def is_open(self):
        return self.ser.is_open

    def fixture_detect_start(self, station):
        stop_event = gl.get_value("stop_event")
        status = False

        try:
            if not self.is_open():
                self.open()
            print(f"is open...{self.is_open()}")

            start_port = start_mapping.get(station)
            print(start_port, self.is_open())
            sensors = {}
            command = bytes([0x01, 0x03, 0x10, 0x01, 0x02, 0x00, 0x11, 0xAA])

            response = self.send_receive(command)
            data = list(response)
            sports1 = f"{data[4]:08b}"[::-1]
            sports2 = f"{data[5]:08b}"[::-1]
            for i in range(8):
                sensors[f"S{i + 1}"] = sports1[i] == "1"
            for i in range(4):
                sensors[f"S{i + 9}"] = sports2[i] == "1"
            print(sensors)
            status = sensors[start_port]

            self.close()

        except Exception as e:
            print(f"Error: {e}")

        return status

    def fixture_detect_start_t(self, station):
        stop_event = gl.get_value("stop_event")
        status = False
        print("fixture start...")
        try:
            if not self.is_open():

                self.open()
            print(f"is open...{self.is_open()}")
            while not stop_event.is_set():
                start_port = start_mapping.get(station)
                print(start_port, self.is_open())
                sensors = {}
                command = bytes([0x01, 0x03, 0x10, 0x01, 0x02, 0x00, 0x11, 0xAA])

                response = self.send_receive(command)
                data = list(response)
                sports1 = f"{data[4]:08b}"[::-1]
                sports2 = f"{data[5]:08b}"[::-1]
                for i in range(8):
                    sensors[f"S{i + 1}"] = sports1[i] == "1"
                for i in range(4):
                    sensors[f"S{i + 9}"] = sports2[i] == "1"
                print(sensors)
                status = sensors[start_port]
                if status:
                    break

            self.close()
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")

        return status

    def fixture_detect_input(self, channel):
        try:
            if not self.is_open():
                self.open()
            sensors = {}
            command = bytes([0x01, 0x03, 0x10, 0x01, 0x02, 0x00, 0x11, 0xAA])
            response = self.send_receive(command)
            data = list(response)
            sports1 = f"{data[4]:08b}"[::-1]
            sports2 = f"{data[5]:08b}"[::-1]
            for i in range(8):
                sensors[f"S{i + 1}"] = sports1[i] == "1"
            for i in range(4):
                sensors[f"S{i + 9}"] = sports2[i] == "1"
            self.close()
            return sensors[channel]
        except Exception as e:
            print(f"Error: {e}")
