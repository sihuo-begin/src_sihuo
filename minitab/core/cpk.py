import os
import win32com.client
import time


class CpkAnalyzer:

    def __init__(self, config):
        self.config = config

    def run_minitab_multi(self, data_path):
        """
        ✅ 支持多列 CPK分析
        每一列生成一个图
        """

        image_dir = self.config["paths"]["images"]
        os.makedirs(image_dir, exist_ok=True)

        usl = self.config["spec"]["USL"]
        lsl = self.config["spec"]["LSL"]
        target = self.config["spec"]["TARGET"]

        results = {}

        try:
            app = win32com.client.DispatchEx("Mtb.Application")
            # app.Visible = False
            time.sleep(20)
            # project = app.ActiveProject
            project = app.NewProject()
            if project is None:
                project = app.NewProject()
            print(project)
            project.Open(data_path)

            # 👉 假设前几列都是 Measurement（动态获取列数）
            worksheet = project.Worksheets.Item(1)
            col_count = worksheet.Columns.Count

            for i in range(1, col_count + 1):

                col_name = f"C{i}"
                img_path = os.path.join(
                    image_dir, f"cpk_{col_name}.jpg"
                ).replace("\\", "/")

                commands = f"""
                Capability {col_name};
                  USL {usl};
                  LSL {lsl};
                  Target {target};
                  Overall.

                GSAVE "{img_path}";
                  JPEG.
                """

                project.ExecuteCommand(commands)

                results[col_name] = {
                    "image": img_path
                }

            return results

        except Exception as e:
            raise Exception(f"多列CPK分析失败: {str(e)}")


    def calculate_multi(self, df):
        """
        ✅ Python本地计算（多列）
        """

        results = {}

        usl = self.config["spec"]["USL"]
        lsl = self.config["spec"]["LSL"]

        for col in df.columns:
            data = df[col]

            mean = data.mean()
            std = data.std()

            cpu = (usl - mean) / (3 * std)
            cpl = (mean - lsl) / (3 * std)
            cpk = min(cpu, cpl)

            results[col] = {
                "mean": mean,
                "std": std,
                "cpk": cpk
            }

        return results