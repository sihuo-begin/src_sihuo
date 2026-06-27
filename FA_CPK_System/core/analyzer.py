# core/analyzer.py

import numpy as np


class Analyzer:

    def calc_cpk(self, values, lsl, usl):

        values = np.array(values)

        mean = np.mean(values)
        std = np.std(values, ddof=1)

        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)

        cpk = min(cpu, cpl)

        return {
            "mean": mean,
            "std": std,
            "cpk": round(cpk, 3)
        }

    def calc_grr(self, values):

        # ✅ 简化GRR（可后续升级ANOVA）
        values = np.array(values)

        total_var = np.var(values, ddof=1)
        grr = total_var * 0.3   # 简化占比

        return {
            "grr": round(grr, 3)
        }