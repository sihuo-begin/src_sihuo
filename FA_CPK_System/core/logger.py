import os
from datetime import datetime


class Logger:

    def __init__(self, output_dir):

        log_dir = os.path.join(output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.log_path = os.path.join(log_dir, f"run_{ts}.log")
        self.latest_path = os.path.join(log_dir, "latest.log")

    def write(self, level, msg):

        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"

        print(line)

        # ✅ 写主日志
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # ✅ 写latest（方便查看）
        with open(self.latest_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ✅ 快捷接口
    def info(self, msg):
        self.write("INFO", msg)

    def warn(self, msg):
        self.write("WARN", msg)

    def error(self, msg):
        self.write("ERROR", msg)