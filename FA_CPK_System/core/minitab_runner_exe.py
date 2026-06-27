import subprocess
import os
import time


class MinitabRunnerEXE:

    def __init__(self, exe):
        self.exe = exe

    def run(self, macro_path, expected_images, log):

        if not os.path.exists(macro_path):
            raise Exception("Macro不存在")

        log(f"RUN: {macro_path}")

        try:
            subprocess.run(
                [self.exe, macro_path],
                timeout=600,
                check=True
            )

        except subprocess.TimeoutExpired:
            log("❌ 超时：Mtb.exe 未退出（可能卡住）")
            os.system("taskkill /f /im Mtb.exe")
            raise

        except subprocess.CalledProcessError as e:
            log(f"❌ 执行失败: {e}")
            raise

        # ✅ 等待输出
        time.sleep(2)

        # ✅ 校验图片
        missing = []

        for img in expected_images:
            if not os.path.exists(img):
                missing.append(img)

        if missing:
            log(f"❌ 图片缺失: {missing}")
            raise Exception("部分图片未生成")

        log("✅ 图片全部生成")