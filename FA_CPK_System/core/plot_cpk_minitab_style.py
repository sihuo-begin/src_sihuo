# core/plot_cpk_minitab_style.py

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm


class CpkPlotter:

    def plot(self, values, lsl, usl, title, save_path):

        values = np.array(values)

        mean = np.mean(values)
        std = np.std(values, ddof=1)

        # ✅ within std（近似）
        std_within = std * 1.02

        # ✅ Capability
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)

        # ========= 布局 =========
        fig = plt.figure(figsize=(10, 7))
        fig.patch.set_facecolor('#f0f0f0')

        # ===== Title =====
        fig.suptitle(f"Process Capability Report for {title}",
                     fontsize=16, fontweight='bold')

        # ===== 中间图 =====
        ax = plt.axes([0.25, 0.3, 0.4, 0.45])

        # Histogram
        ax.hist(values, bins=15, density=True, color='#4C72B0')

        x = np.linspace(min(values), max(values), 200)

        # Overall
        ax.plot(x, norm.pdf(x, mean, std), 'r', label='Overall')

        # Within
        ax.plot(x, norm.pdf(x, mean, std_within),
                'k--', label='Within')

        # Spec Limits
        ax.axvline(lsl, color='red', linestyle='--')
        ax.axvline(usl, color='red', linestyle='--')
        ax.grid(True, linestyle='-', alpha=0.3)
        ax.set_xticks(np.linspace(lsl, usl, 7))
        ax.set_yticks([])
        ax.set_facecolor('#f7f7f7')

        # ===== 左侧数据 =====
        left_text = f"""
Process Data
LSL            {lsl}
USL            {usl}
Mean           {mean:.1f}
Sample N       {len(values)}
StDev(Overall) {std:.2f}
StDev(Within)  {std_within:.2f}
"""
        fig.text(0.05, 0.45, left_text, fontsize=10, family='monospace')

        # ===== 右侧能力 =====
        right_text = f"""
Overall Capability
Pp   {round((usl-lsl)/(6*std),2)}
PPL  {round(cpl,2)}
PPU  {round(cpu,2)}
Ppk  {round(cpk,2)}

Potential (Within)
Cp   {round((usl-lsl)/(6*std_within),2)}
CPL  {round((mean-lsl)/(3*std_within),2)}
CPU  {round((usl-mean)/(3*std_within),2)}
Cpk  {round(min((usl-mean)/(3*std_within),
                (mean-lsl)/(3*std_within)),2)}
"""
        fig.text(0.72, 0.45, right_text, fontsize=10, family='monospace')

        # ===== 底部 =====
        fig.text(0.3, 0.15,
                 "The actual process spread is represented by 6 sigma.",
                 fontsize=10, style='italic')
        plt.rcParams['font.family'] = 'Arial'
        plt.savefig(save_path, dpi=120)
        plt.close()