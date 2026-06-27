# core/analysis_runner.py

import os
from core.analyzer import Analyzer
from core.plotter import Plotter
from core.plot_cpk_minitab_style import CpkPlotter
from core.cpk_minitab_full import MinitabStyleCPK


class AnalysisRunner:

    def __init__(self, config):
        self.output = config["minitab"]["output_dir"]
        os.makedirs(self.output, exist_ok=True)

        self.analyzer = Analyzer()
        self.plotter = Plotter()

    def run_cpk(self, data):

        results = {}
        plotter = CpkPlotter()
        plotter = MinitabStyleCPK()
        for item, info in data.items():
            values = info["values"]
            lsl = info["lsl"]
            usl = info["usl"]
            print(lsl, usl, "___________", values)
            plotter.plot(
                values,
                lsl,
                usl,
                item,
                f"./output/charts/{item}.png"
            )
            # plotter.plot(
            #     values,
            #     lsl,
            #     usl,
            #     item,
            #     f"./output/charts/{item}.png"
            # )
            # ✅ CPK
            # cpk_res = self.analyzer.calc_cpk(values, lsl, usl)
            #
            # cpk_png = os.path.join(self.output, f"{item}.png")
            # self.plotter.plot_cpk(values, lsl, usl, cpk_png)
            #
            # results[item] = {
            #     "cpk": cpk_res,
            # }

        # return results
        return True
    def run_grr(self, data):

        results = {}

        for item, info in data.items():

            values = info["values"]
            lsl = info["lsl"]
            usl = info["usl"]

            # ✅ GRR
            grr_res = self.analyzer.calc_grr(values)

            grr_png = os.path.join(self.output, f"{item}_GRR.png")
            self.plotter.plot_grr(values, grr_png)

            results[item] = {
                "grr": grr_res
            }

        return results