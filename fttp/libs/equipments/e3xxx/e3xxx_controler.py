import time

# 可选接口
import pyvisa
import serial


class E3xxxController:
    """
    Keysight E3634A Power Supply 控制模块
    支持 VISA（GPIB/USB） / 串口（RS232）
    """

    def __init__(self, interface="visa", resource=None, baudrate=9600, timeout=2):
        """
        interface: "visa" or "serial"
        resource:
            - visa: "GPIB0::5::INSTR"
            - serial: "COM3" 或 "/dev/ttyUSB0"
        """
        self.interface = interface
        self.resource = resource
        self.timeout = timeout

        self.inst = None
        self.serial = None
        self.baudrate = baudrate

    # ---------------------------
    # 基础连接
    # ---------------------------
    def connect(self):
        if self.interface == "visa":
            rm = pyvisa.ResourceManager()
            self.inst = rm.open_resource(self.resource)
            self.inst.timeout = int(self.timeout * 1000)
            self.inst.write_termination = '\n'
            self.inst.read_termination = '\n'

        elif self.interface == "serial":
            self.serial = serial.Serial(
                self.resource,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(1)

        else:
            raise ValueError("Unsupported interface")

    def disconnect(self):
        if self.inst:
            self.inst.close()
        if self.serial:
            self.serial.close()

    # ---------------------------
    # SCPI通信封装
    # ---------------------------
    def _write(self, cmd):
        if self.inst:
            self.inst.write(cmd)
        elif self.serial:
            self.serial.write((cmd + '\n').encode())

    def _query(self, cmd):
        if self.inst:
            return self.inst.query(cmd).strip()

        elif self.serial:
            self.serial.write((cmd + '\r\n').encode())
            return self.serial.readline().decode().strip()

    # ---------------------------
    # 核心功能
    # ---------------------------

    def reset(self):
        """复位设备"""
        self._write("*RST")

    def identify(self):
        """equipment"""
        return self._query("*IDN?")

    # ---------------------------
    # output control
    # ---------------------------
    def output_on(self):
        """上电"""
        self._write("OUTP ON")

    def output_off(self):
        """下电"""
        self._write("OUTP OFF")

    def is_output_on(self):
        """查询输出状态"""
        return self._query("OUTP?") == "1"

    # ---------------------------
    # volt
    # ---------------------------
    def set_voltage_current(self, voltage, current):
        """
        设置电压和限流
        """
        self._write(f"VOLT {voltage}")
        self._write(f"CURR {current}")

    def set_voltage(self, voltage):
        self._write(f"VOLT {voltage}")

    def set_current(self, current):
        self._write(f"CURR {current}")

    def apply_volt_curr(self, voltage, current):
        self._write(f"APPL {voltage}, {current}")

    # ---------------------------
    # 读取
    # ---------------------------
    def get_voltage(self):
        """volt"""
        return float(self._query("VOLT?"))

    def get_error(self):
        """volt"""
        return float(self._query("ERR?"))

    def get_current(self):
        """current"""
        return float(self._query("CURR?"))

    def measure_voltage(self):
        """volt"""
        return float(self._query("MEAS:VOLT?"))

    def measure_current(self):
        """测量实际输出电流"""
        return float(self._query("MEAS:CURR?"))

    # ---------------------------
    # save
    # ---------------------------
    def set_ovp(self, voltage):
        """over volt"""
        self._write(f"VOLT:PROT {voltage}")

    def enable_ovp(self, enable=True):
        self._write(f"VOLT:PROT {'ON' if enable else 'OFF'}")

    def set_ocp(self, enable=True):
        self._write(f"CURR:PROT {'ON' if enable else 'OFF'}")
