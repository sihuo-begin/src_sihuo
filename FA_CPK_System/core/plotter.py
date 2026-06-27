# core/plotter.py

import matplotlib.pyplot as plt
import numpy as np
import os


class Plotter:

    def plot_cpk(self, values, lsl, usl, save_path):

        values = np.array(values)

        mean = np.mean(values)
        std = np.std(values, ddof=1)

        plt.figure(figsize=(6, 4))

        # ✅ 直方图
        plt.hist(values, bins=30, density=True, alpha=0.6)

        # ✅ 正态分布曲线
        x = np.linspace(min(values), max(values), 100)
        y = (1/(std*np.sqrt(2*np.pi))) * np.exp(-(x-mean)**2/(2*std**2))
        plt.plot(x, y)

        # ✅ 规格线
        plt.axvline(lsl, color='red', linestyle='--')
        plt.axvline(usl, color='red', linestyle='--')

        plt.title("CPK Chart")

        plt.savefig(save_path)
        plt.close()

    def plot_grr(self, values, save_path):

        plt.figure(figsize=(4, 3))
        plt.boxplot(values)

        plt.title("GRR Boxplot")

        plt.savefig(save_path)
        plt.close()
