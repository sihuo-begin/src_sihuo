import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm


class MinitabStyleCPK:

    def plot(self, values, lsl, usl, title, save_path):

        values = np.array(values)

        # ===== 基础统计 =====
        mean = np.mean(values)
        std = np.std(values, ddof=1)
        std_within = std * 1.02  # 近似within

        # ===== Capability =====
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)

        cp = (usl - lsl) / (6 * std_within)
        cpk_w = min(
            (usl - mean) / (3 * std_within),
            (mean - lsl) / (3 * std_within)
        )

        # ===== PPM计算 =====
        def calc_ppm(mean, std, lsl, usl):
            ppm_l = norm.cdf(lsl, mean, std) * 1e6
            ppm_u = (1 - norm.cdf(usl, mean, std)) * 1e6
            return ppm_l, ppm_u, ppm_l + ppm_u

        def calc_obs(values, lsl, usl):
            n = len(values)
            below = sum(v < lsl for v in values)
            above = sum(v > usl for v in values)
            return below/n*1e6, above/n*1e6, (below+above)/n*1e6

        obs_l, obs_u, obs_t = calc_obs(values, lsl, usl)
        exp_l, exp_u, exp_t = calc_ppm(mean, std, lsl, usl)
        exp_l_w, exp_u_w, exp_t_w = calc_ppm(mean, std_within, lsl, usl)

        # ===== 画布 =====
        fig = plt.figure(figsize=(11, 8))
        fig.patch.set_facecolor('#eeeeee')

        # ===== 标题 =====
        fig.suptitle(
            f"Process Capability Report for {title}",
            fontsize=16,
            fontweight='bold'
        )

        # ===== 主图 =====
        ax = fig.add_axes([0.30, 0.35, 0.40, 0.45])
        ax.set_facecolor('#f7f7f7')
        # Histogram
        ax.hist(values, bins=15, density=True, color='#6C8EBF', edgecolor='black')

        x = np.linspace(min(values), max(values), 200)

        # Overall

        # ax.plot(x, color='red', linestyle='-', linewidth=2, label='Overall')
        #
        # # Within（黑色虚线）
        # ax.plot(x, color='black', linestyle='--', linewidth=1.5, label='Within')

        ax.plot(x, norm.pdf(x, mean, std), 'r-', linewidth=1, label="Overall")

        # Within
        ax.plot(x, norm.pdf(x, mean, std_within), 'k--', linewidth=1, label="Within")

        ax.legend(
            loc='upper left',
            bbox_to_anchor=(1.08, 1),  # ✅ 放在右侧外面
            borderaxespad=0,
            frameon=False,
            fontsize=10
        )

        # Spec lines
        # ax.axvline(lsl, color='red', linestyle='--')
        # ax.axvline(usl, color='red', linestyle='--')
        ax.axvline(lsl, color='#FF1493', linestyle='--')
        ax.axvline(usl, color='#FF1493', linestyle='--')

        # ax.text(lsl, ax.get_ylim()[1] * 1, "LSL", color='red')
        # ax.text(usl, ax.get_ylim()[1] * 1, "USL", color='red')


        # ✅ 保留横线用的 ticks
        ax.set_yticks(ax.get_yticks())

        # ✅ 不显示数字（但保留grid）
        ax.set_yticklabels([])
        ax.text(lsl, ax.get_ylim()[1] * 1, "LSL", color='#FF1493')
        ax.text(usl, ax.get_ylim()[1] * 1, "USL", color='#FF1493')
        # ✅ 画grid（横+竖）
        ax.grid(
            True,
            axis='both',
            linestyle='-',
            linewidth=0.05,
            # color='#d0d0d0'
            color='black'
        )
        # ax.set_yticks([])
        # ax.grid(True, alpha=0.3)

        # ===== 左侧 Process Data =====
        left_text = (
            f"Process Data\n\n"
            f"LSL            {lsl:.0f}\n"
            f"Target         *\n"
            f"USL            {usl:.0f}\n"
            f"Sample Mean    {mean:.1f}\n"
            f"Sample N       {len(values)}\n"
            f"StDev(Overall) {std:.2f}\n"
            f"StDev(Within)  {std_within:.2f}"
        )

        fig.text(0.07, 0.55, left_text, fontsize=11, family='monospace')

        # ===== 右侧 Capability =====
        right_text = (
            f"Overall Capability\n\n"
            f"{'':5}Pp   {(usl-lsl)/(6*std):6.2f}\n"
            f"{'':5}PPL  {cpl:6.2f}\n"
            f"{'':5}PPU  {cpu:6.2f}\n"
            f"{'':5}Ppk  {cpk:6.2f}\n"
            f"{'':5}Cpm  *\n\n"
            f"Potential (Within) Capability\n\n"
            f"{'':5}Cp   {cp:6.2f}\n"
            f"{'':5}CPL  {(mean-lsl)/(3*std_within):6.2f}\n"
            f"{'':5}CPU  {(usl-mean)/(3*std_within):6.2f}\n"
            f"{'':5}Cpk  {cpk_w:6.2f}"
        )

        fig.text(0.74, 0.40, right_text, fontsize=11, family='monospace')

        # ===== Performance Table =====
        table = (
            f"{'':15}Performance\n\n"
            f"{'':10}Observed   Expected Overall   Expected Within\n"
            f"PPM < LSL {obs_l:10.2f}   {exp_l:16.2f}   {exp_l_w:16.2f}\n"
            f"PPM > USL {obs_u:10.2f}   {exp_u:16.2f}   {exp_u_w:16.2f}\n"
            f"PPM Total {obs_t:10.2f}   {exp_t:16.2f}   {exp_t_w:16.2f}"
        )

        fig.text(0.08, 0.18, table, fontsize=11, family='monospace')

        # ===== Footer =====
        fig.text(
            0.08,
            0.08,
            "The actual process spread is represented by 6 sigma.",
            fontsize=16,
            style='italic'
        )

        plt.savefig(save_path, dpi=120)
        plt.close()
