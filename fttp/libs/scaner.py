import time


class KeyenceScanner:
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger

    def send_command(self, cmd):
        """send command and get recieved data"""
        return self.connection.send_receive(cmd)

    def auto_scan(self):
        """autoscan and capture scan data"""
        self.connection.send("LOFF\r")
        resp = self.connection.send_receive("LON\r")
        self.connection.send("LOFF\r")
        self.logger.debug(f"capture return: {resp}")
        return bytes(resp).decode("utf-8").strip()

    def clear_scan_buffer(self):
        """clear scanner"""
        self.connection.send("BCLR\r")
        print("scan cleared")

    def read_scan(self):
        """read scanner"""
        self.send_command("write_read\n")
        res = self.send_command("read_command\n")
        data = res.strip().upper()
        return data.decode("utf-8")

    def close(self):
        """close connection"""
        self.send_command("close_command\n")
        print("port was closed")


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
