"""Agilent 34970A driver"""

import serial
import time


class UARTTimeoutError(Exception):
    pass

class UARTCommunicationError(Exception):
    pass

class Agilent34970A_:
    def __init__(self, port, baudrate=9600, timeout=2.0):
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

    def send(self, data):
        """
        发送数据：支持bytes，list[int]（自动转bytes），str（自动转utf-8 bytes）
        """
        try:
            to_send = (data + '\n').encode()
            self.ser.write(to_send)
        except Exception as e:
            raise UARTCommunicationError(f"发送数据失败: {e}")

    def receive(self, timeout=None):
        """
        连续接收数据，直到空闲idle_interval后自动返回，或总超时timeout
        """
        res = self.ser.readline().decode().strip()
        return res

    def send_receive(self, data, timeout=None):
        timeout = timeout if timeout is not None else self.timeout
        try:
            self.send(data)
            time.sleep(0.15)
            return self.receive(timeout)
        except (UARTTimeoutError, UARTCommunicationError) as e:
            raise

    def open(self):
        self.ser.open()

    def close(self):
        self.ser.close()

    def is_open(self):
        return self.ser.is_open

    def reset(self):
        return self.send("*RST")

    def clear(self):
        return self.send("*CLS")

    def self_check(self):
        return self.send_receive("*IDN?")

    def get_equipment_error(self):
        return self.send_receive('SYST:ERR?')

    def query_equipment_slots(self, slot_number):
        pass

    def query_voltage_by_slot(self, slot_number):
        self.reset()
        self.clear()
        self.get_equipment_error()
        if slot_number< 1 or slot_number > 3:
            return []
        try:
            self.send(f"CONF:VOLT:DC 10,0.001,(@{slot_number}01:{slot_number}20)")
            self.send(f"ROUT:SCAN (@{slot_number}01:{slot_number}20)")
            self.send("TRIG:SOUR IMM")
            self.send("TRIG:COUN 1")
            self.send("INIT")
            datas = self.send_receive('FETC?', timeout=5).split(",")
            return [float(x) for x in datas]
        except:

            return []


    def query_voltage_by_channel(self, slot_number, channel_number):
        self.reset()
        self.clear()
        self.get_equipment_error()
        if slot_number< 1 or slot_number > 3:
            return -1
        if channel_number< 1 or channel_number > 20:
            return -1
        try:
            if channel_number>=10:
                self.send(f'CONF:VOLT:DC (@{slot_number}{channel_number})\n')
            else:
                self.send(f'CONF:VOLT:DC (@{slot_number}0{channel_number})\n')
            time.sleep(0.1)
            data = self.send_receive('READ?')
            return float(data.strip())
        except:
            return -1

class Agilent34970A:
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger

    def reset(self):
        return self.connection.send("*RST\n")

    def clear(self):
        return self.connection.send("*CLS\n")

    def self_check(self):
        return self.connection.send_receive("*IDN?\n").decode().strip()

    def get_equipment_error(self):
        return self.connection.send_receive('SYST:ERR?\n').decode().strip()
    def query_voltage_by_slot(self, slot_number):
        self.reset()
        self.clear()
        self.get_equipment_error()
        if slot_number< 1 or slot_number > 3:
            return []
        try:
            self.connection.send(f"CONF:VOLT:DC 10,0.001,(@{slot_number}01:{slot_number}20)\n")
            self.connection.send(f"ROUT:SCAN (@{slot_number}01:{slot_number}20)\n")
            self.connection.send("TRIG:SOUR IMM\n")
            self.connection.send("TRIG:COUN 1\n")
            self.connection.send("INIT\n")
            datas = self.connection.send_receive('FETC?\n', timeout=5).decode().split(",")
            return [float(x) for x in datas]
        except:

            return []
    def query_voltage_by_channel(self, slot_number, channel_number):
        self.reset()
        self.clear()
        self.get_equipment_error()
        if slot_number< 1 or slot_number > 3:
            return -1
        if channel_number< 1 or channel_number > 20:
            return -1
        try:
            if channel_number>=10:
                self.connection.send(f'CONF:VOLT:DC (@{slot_number}{channel_number})\n')
            else:
                self.connection.send(f'CONF:VOLT:DC (@{slot_number}0{channel_number})\n')
            time.sleep(0.1)
            data = self.connection.send_receive('READ?\n').decode()

            return float(data.strip())
        except:
            return -1