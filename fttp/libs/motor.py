import yaml
import time
import serial
import sys
import os
from src.libs.common import resource_path


class MotorSerial:
    def __init__(self, port, baudrate=38400, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def open(self):
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

    def send(self, cmd, wait=0.05):
        if self.serial and self.serial.is_open:
            self.serial.write(cmd.encode("utf-8"))
            time.sleep(wait)

    def send_receive(self, cmd, wait=0.05):
        if self.serial and self.serial.is_open:
            self.serial.write(cmd.encode("utf-8"))
            time.sleep(wait)
            return self.serial.readline().decode("utf-8")
        return None


class MotorController:
    def __init__(self, port_x, port_z, baudrate=38400):
        self.settings_file = "settings.yaml"
        if hasattr(sys, "_MEIPASS"):
            self.base_file_path = sys._MEIPASS
            self.setting_dir = os.path.join(self.base_file_path, "src", "config")
            self.setting_path = os.path.join(self.setting_dir, self.settings_file)
        else:
            self.setting_dir = os.path.join("src", "config")
            self.setting_path = os.path.join(self.setting_dir, self.settings_file)
        with open(self.setting_path, encoding="utf-8") as f:
            self.settings = yaml.safe_load(f)
        self.motor_x = MotorSerial(port_x, baudrate)
        self.motor_z = MotorSerial(port_z, baudrate)
        self.button0_x = self.settings["BUTTON0_X_PULSE"]
        self.button1_x = self.settings["BUTTON1_X_PULSE"]
        self.button2_x = self.settings["BUTTON2_X_PULSE"]
        self.button_z_raise = self.settings["RAISE_Z_PULSE"]
        self.button0_z = self.settings["BUTTON0_Z_PULSE"]
        self.button1_z = self.settings["BUTTON1_Z_PULSE"]
        self.button2_z = self.settings["BUTTON2_Z_PULSE"]
        self.xspeed_min = self.settings["XSPEED_MIN"]
        self.xspeed_max = self.settings["XSPEED_MAX"]
        self.xspeed_time = self.settings["XSPEED_TIME"]
        self.zspeed_min = self.settings["ZSPEED_MIN"]
        self.zspeed_max = self.settings["ZSPEED_MAX"]
        self.zspeed_time = self.settings["ZSPEED_TIME"]

    def open(self):
        self.motor_x.open()
        self.motor_z.open()

    def close(self):
        self.motor_x.close()
        self.motor_z.close()

    def pre_init(self):
        pass

    def set_xspeed(self):
        s = self.motor_x
        s.send_receive(f"D:1S{self.xspeed_min}F{self.xspeed_max}R{self.xspeed_time}\r\n")

    def set_zspeed(self):
        s = self.motor_z
        s.send_receive(f"D:1S{self.zspeed_min}F{self.zspeed_max}R{self.zspeed_time}\r\n")

    def move_x_button_origin(self):
        s = self.motor_x
        s.send_receive(f"M:1+P{self.button0_x}\r\n")
        s.send_receive("G:\r\n")

    def move_z_button_origin(self):
        s = self.motor_z
        s.send_receive(f"M:1+P{self.button_z_raise}\r\n")
        s.send_receive("G:\r\n")

    def move_x_sequence(self):
        s = self.motor_x
        s.send_receive("C:11\r\n")
        s.send_receive("H:1\r\n")

    def move_x1_sequence(self, down=True):
        s = self.motor_x
        if down:
            s.send_receive(f"M:1+P{self.button1_x}\r\n")
            s.send_receive("G:\r\n")
        else:
            s.send_receive(f"M:1-P{self.button1_x}\r\n")
            s.send_receive("G:\r\n")

    def move_x2_sequence(self, down=True):
        s = self.motor_x
        button0_origin = self.button1_x + self.button2_x
        if down:
            s = self.motor_x
            s.send_receive(f"M:1+P{self.button2_x}\r\n")
            s.send_receive("G:\r\n")
        else:
            s.send_receive(f"M:1-P{button0_origin}\r\n")
            s.send_receive("G:\r\n")

    def move_z_sequence(self):
        s = self.motor_z
        s.send("C:11\r\n")
        s.send("H:1\r\n")

    def move_z0_sequence(self, down=True):
        s = self.motor_z
        if down:
            s.send_receive(f"M:1-P{self.button0_z}\r\n")
            s.send_receive("G:\r\n")
        else:
            s.send_receive(f"M:1+P{self.button0_z}\r\n")
            s.send_receive("G:\r\n")

    def move_z1_sequence(self, down=True):
        s = self.motor_z
        if down:
            s.send_receive(f"M:1-P{self.button1_z}\r\n")
            s.send_receive("G:\r\n")
        else:
            s.send_receive(f"M:1+P{self.button1_z}\r\n")
            s.send_receive("G:\r\n")

    def move_z2_sequence(self, down=True):
        s = self.motor_z
        if down:
            s.send_receive(f"M:1-P{self.button2_z}\r\n")
            s.send_receive("G:\r\n")
        else:
            s.send_receive(f"M:1+P{self.button2_z}\r\n")
            s.send_receive("G:\r\n")

    # def run(self):
    #     self.open()
    #     try:
    #         self.move_x_sequence()
    #         self.move_y_sequence()
    #     finally:
    #         self.close()


#
# if __name__ == "__main__":
#     controller = XYMotorController(
#         yaml_path='src/config/settings.yaml',
#         port_x='COM3',  # X轴串口
#         port_y='COM4'   # Y轴串口
#     )
#     controller.run()
