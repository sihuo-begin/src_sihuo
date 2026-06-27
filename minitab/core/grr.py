import os
import win32com.client


class GrrAnalyzer:

    def __init__(self, config):
        self.config = config

    def run_minitab(self, data_path):
        """
        ✅ Gage R&R 分析 + 自动导图
        """

        image_dir = self.config["paths"]["images"]
        os.makedirs(image_dir, exist_ok=True)

        grr_img = os.path.join(image_dir, "grr.jpg").replace("\\", "/")

        try:
            app = win32com.client.DispatchEx("Mtb.Application")
            app.Visible = False

            project = app.ActiveProject
            project.Open(data_path)

            # ✅ 默认：
            # C1 = Measurement
            # C2 = Part
            # C3 = Operator

            commands = f"""
            GageRR C1 C2 C3;
              StudyVar 6;
              Parts 10;
              Operators 3.

            GSAVE "{grr_img}";
              JPEG.
            """

            project.ExecuteCommand(commands)

            return {
                "image": grr_img
            }

        except Exception as e:
            raise Exception(f"GRR分析失败: {str(e)}")