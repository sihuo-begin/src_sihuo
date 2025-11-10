import time
import serial
from src.libs import logger


class KeyenceScanner:
    def __init__(self, connection, logger):
        self.logger = logger
        self.connection = connection
        # self.port = port
        # self.baudrate = baudrate
        # self.parity = parity
        # self.timeout = timeout
        # # self.ser_com = None
        # self.ser_com = serial.Serial(
        #     port=self.port,
        #     baudrate=self.baudrate,
        #     parity=self.parity,
        #     timeout=self.timeout,
        # )
        # self.serial.close()
        # self.serial.open()

    # def connect(self):
    #     if self.ser_com is not None and self.ser.is_open:
    #         self.ser_com.close()
    #     try:
    #         self.ser_com = serial.Serial(
    #             port=self.port,
    #             baudrate=self.baudrate,
    #             parity=self.parity,
    #             timeout=self.timeout,
    #         )
    #     except Exception as e:
    #         self.ser_com = None
    #         raise serial.SerialException(f"串口连接失败: {e}")
    # def is_connected(self):
    #     return self.ser_com is not None and self.ser_com.is_open
    # def close(self):
    #     if self.ser_com and self.serial.is_open:
    #         self.ser_com.close()
    #
    # def send(self, cmd, wait=0.05):
    #     if self.ser_com and self.ser_com.is_open:
    #         self.ser_com.write(cmd.encode("utf-8"))
    #         time.sleep(wait)
    #
    # def send_receive(self, cmd, wait=1):
    #     if self.ser_com and self.ser_com.is_open:
    #         self.ser_com.write(cmd.encode("utf-8"))
    #         time.sleep(wait)
    #         # self.logger("!!!! {} decode {}".format(, resp.decode("utf-8")))
    #         return self.ser_com.read().decode("utf-8")
    #     return None
    #
    # def close(self):
    #     self.ser_com.close()
    #
    # def send(self, cmd, wait=0.05):
    #     self.ser_com.write(cmd.encode("utf-8"))
    #     time.sleep(wait)
    #
    # def send_receive(self, cmd, wait=1):
    #     self.ser_com.write(cmd.encode("utf-8"))
    #     time.sleep(wait)
    #     resp = self.ser_com.read()
    #     self.logger("!!!! {} decode {}".format(resp, resp.decode("utf-8")))
    #     return resp

    def auto_scan(self):
        """autoscan and capture scan data"""
        # self.clear_scan_buffer()
        self.connection.send("LOFF\r")
        resp = self.connection.send_receive("LON\r")
        self.connection.send("LOFF\r")
        self.logger.debug(f"capture return: {resp}")
        return bytes(resp).decode("utf-8").strip()

    def clear_scan_buffer(self):
        """clear scanner"""
        self.connection.send("BCLR\r")
        print("scan cleared")


# 使用示例
# if __name__ == "__main__":
#     scanner = KeyenceScanner(port='COM3')  # 替换为实际的串口
#     try:
#         scanner.auto_scan()
#         time.sleep(1)
#         scanned_data = scanner.read_scan()
#         print("扫描内容:", scanned_data)
#         scanner.clear_scan()
#     finally:
#         scanner.close()
