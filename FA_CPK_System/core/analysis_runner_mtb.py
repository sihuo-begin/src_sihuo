import os
import traceback
from datetime import datetime
from core.csv_exporter import CsvExporter
from core.minitab_runner_exe import MinitabRunnerEXE
from core.macro_builder import MtbMacroBuilder
from core.runner_worker import RunnerWorker

class AnalysisRunnerMtb:

    def __init__(self, config):

        self.output = config["minitab"]["output_dir"]
        os.makedirs(self.output, exist_ok=True)

        self.log_file = os.path.join(self.output, "logs.txt")

        self.csv = CsvExporter(self.output)
        self.macro = MtbMacroBuilder(self.output)
        self.runner = MinitabRunnerEXE(
            config["minitab"]["exe_path"]
        )

    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)

        with open(self.log_file, "a") as f:
            f.write(line + "\n")

    def run(self, data):

        self.log("========== START ==========")

        try:
            # ✅ Step1 CSV
            self.log("Step1: 生成CSV")
            csv_path, n_cols = self.csv.export_all(data)

            if not os.path.exists(csv_path):
                raise Exception("CSV未生成")

            self.log(f"CSV OK: {csv_path}")

            # ✅ Step2 Macro
            self.log("Step2: 生成Macro")
            macro_path = self.macro.generate_full_macro(data)

            if not os.path.exists(macro_path):
                raise Exception("Macro未生成")

            self.log(f"Macro OK: {macro_path}")

            # ✅ Step3 图片路径
            imgs = [
                os.path.join(self.output, f"{item}.png")
                for item in data.keys()
            ]

            # ✅ Step4 Run
            self.log("Step3: 执行 Mtb.exe")
            self.runner.run(macro_path, imgs, self.log)

            self.log("========== DONE ==========")

        except Exception as e:
            self.log(f"❌ ERROR: {e}")
            self.log(traceback.format_exc())
            raise