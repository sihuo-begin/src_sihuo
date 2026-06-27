# ameba_pgtool.py

import subprocess
import threading
import re
from typing import Optional


class DownloadStatus:
    def __init__(self):
        self.percent: int = 0
        self.status: str = "idle"   # idle / running / done
        self.success: Optional[bool] = None
        self.returncode: Optional[int] = None
        self.last_line: str = ""


class AmebaPGTool:
    def __init__(self, exe_path: str):
        self.exe_path = exe_path

    def _build_cmd(self, com_port, image, hash_verify, chip_erase):
        return [
            self.exe_path,
            "-download", com_port,
            "-set", "image", image,
            "-set", "hash_verify", str(hash_verify),
            "-set", "chip_erase", str(chip_erase),
        ]

    def run_blocking(self,
                     com_port="COM38",
                     image="test.bin",
                     hash_verify=1,
                     chip_erase=1) -> DownloadStatus:
        """
        阻塞执行，返回最终结果
        """
        status = DownloadStatus()
        status.status = "running"

        cmd = self._build_cmd(com_port, image, hash_verify, chip_erase)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            bufsize=1,
            universal_newlines=True
        )

        for line in iter(process.stdout.readline, ''):
            if not line:
                break

            line = line.strip()
            status.last_line = line
            # print(line)  # debug可开

            self._parse_line(line, status)

        process.wait()

        status.returncode = process.returncode

        # ✅ 最终成功判断
        if status.success is None:
            status.success = (process.returncode == 0)

        status.status = "done"
        return status

    def run_async(self,
                  com_port="COM38",
                  image="test.bin",
                  hash_verify=1,
                  chip_erase=1) -> DownloadStatus:
        """
        异步执行，返回一个 status 对象，外部可轮询
        """
        status = DownloadStatus()
        status.status = "running"

        def _worker():
            cmd = self._build_cmd(com_port, image, hash_verify, chip_erase)

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                bufsize=1,
                universal_newlines=True
            )

            for line in iter(process.stdout.readline, ''):
                if not line:
                    break

                line = line.strip()
                status.last_line = line

                self._parse_line(line, status)

            process.wait()

            status.returncode = process.returncode

            if status.success is None:
                status.success = (process.returncode == 0)

            status.status = "done"

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        return status

    def _parse_line(self, line: str, status: DownloadStatus):
        """
        统一解析逻辑（可扩展）
        """

        # ✅ 进度
        m = re.search(r'Downloading\s+---\s+%(\d+)', line)
        if m:
            status.percent = int(m.group(1))
            return

        # ✅ 状态阶段
        if "Start Download" in line:
            status.status = "running"

        elif "Hash checking" in line:
            status.status = "checking"

        elif "WORKER complete" in line:
            status.status = "done"
            status.success = True

        elif "Hash verification: Pass" in line:
            status.success = True

        elif "Fail" in line or "ERROR" in line:
            status.success = False
            status.status = "done"

#
# if __name__ == "__main__":
#      Optiion 1: sync
#     tool = AmebaPGTool(r"C:\tools\AmebaZII_PGTool.exe")
#
#     status = tool.run_blocking()
#
#     print(status.percent)  # 100
#     print(status.success)  # True
#
#     Option 2:
#     tool = AmebaPGTool(r"C:\tools\AmebaZII_PGTool.exe")
#
#     status = tool.run_async()
#
#     # external monitor
#     while status.status != "done":
#         print(f"{status.percent}%")
#
#     print("完成:", status.success)
