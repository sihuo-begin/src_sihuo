from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

import numpy as np
import sounddevice as sd
from scipy.signal import get_window


def pick_input_device_index(name_contains: Optional[str] = None) -> int:
    if name_contains is None:
        default_in = sd.default.device[0]
        if default_in is None or default_in < 0:
            raise RuntimeError("No default input device found. Please specify name_contains.")
        return int(default_in)

    devices = sd.query_devices()
    matches = []
    for i, d in enumerate(devices):
        d = dict(d)
        if int(d.get("max_input_channels", 0)) <= 0:
            continue
        name = str(d.get("name", ""))
        if name_contains.lower() in name.lower():
            matches.append((i, name, int(d.get("max_input_channels", 0)), float(d.get("default_samplerate", 0.0))))

    if not matches:
        print("Available INPUT devices:")
        for i, d in enumerate(devices):
            d = dict(d)
            if int(d.get("max_input_channels", 0)) > 0:
                print(f"  [{i}] {d.get('name')} (in_ch={d.get('max_input_channels')}, default_sr={d.get('default_samplerate')})")
        raise RuntimeError(f'No input device matched name_contains="{name_contains}".')

    matches.sort(key=lambda t: t[3], reverse=True)
    best = matches[0]
    print(f'Selected device: index={best[0]}, name="{best[1]}", in_ch={best[2]}, default_sr={best[3]}')
    return int(best[0])


def _parabolic_interpolation(mag: np.ndarray, k: int) -> float:
    if k <= 0 or k >= len(mag) - 1:
        return float(k)
    a, b, c = float(mag[k - 1]), float(mag[k]), float(mag[k + 1])
    denom = (a - 2.0 * b + c)
    if denom == 0.0:
        return float(k)
    delta = 0.5 * (a - c) / denom
    return float(k) + float(delta)


def _next_pow2(n: int) -> int:
    return 1 if n <= 1 else 2 ** int(np.ceil(np.log2(n)))


def _robust_stats_floor(x: np.ndarray) -> float:
    """
    用中位数作为噪声底的鲁棒估计；必要时可换成分位数/trimmed mean。
    """
    x = np.asarray(x)
    return float(np.median(x))


@dataclass
class VibFreqConfig:
    fs: int = 48000
    device: Optional[int] = None
    channels: int = 1
    window: str = "hann"
    remove_mean: bool = True
    refine_peak: bool = True
    fmin: float = 5.0
    fmax: Optional[float] = None
    dtype: str = "float32"

    # --- 新增：抗噪参数 ---
    welch_segments: int = 4          # 把时域切成几段做平均（>=1；1 表示退化为单段FFT）
    welch_overlap: float = 0.5       # 段间重叠比例 [0,1)
    pad_to_pow2: bool = True         # 每段 FFT 是否 pad 到 2^k（提升插值精度，不改变真实分辨率本质）
    min_peak_to_median: float = 8.0  # 峰值需至少是“频带中位数”的多少倍，否则认为噪声/不稳定
    require_harmonic: bool = False   # 是否要求 2f 附近也有能量（更严格，适合转速/周期信号）
    harmonic_tol_hz: float = 3.0     # 谐波检查的容差范围
    harmonic_min_ratio: float = 0.15 # 2f 幅值至少达到主峰的该比例（经验值）
    return_debug: bool = False       # 是否返回调试信息


class VibFreqEstimator:
    def __init__(self, config: VibFreqConfig | None = None):
        self.config = config or VibFreqConfig()

        if self.config.fs <= 0:
            raise ValueError("config.fs must be > 0")
        if self.config.channels <= 0:
            raise ValueError("config.channels must be >= 1")
        if self.config.fmin < 0:
            raise ValueError("config.fmin must be >= 0")
        if self.config.welch_segments <= 0:
            raise ValueError("welch_segments must be >= 1")
        if not (0.0 <= self.config.welch_overlap < 1.0):
            raise ValueError("welch_overlap must be in [0, 1)")
        if self.config.min_peak_to_median <= 1.0:
            raise ValueError("min_peak_to_median should be > 1")

    @staticmethod
    def list_devices() -> List[Dict]:
        devices = sd.query_devices()
        return [dict(d) for d in devices]

    def record(self, duration: float) -> np.ndarray:
        if duration <= 0:
            raise ValueError("duration must be > 0")

        frames = int(round(duration * self.config.fs))
        if frames < 8:
            raise ValueError("duration too short for FFT")

        data = sd.rec(
            frames=frames,
            samplerate=self.config.fs,
            channels=self.config.channels,
            dtype=self.config.dtype,
            device=self.config.device,
            blocking=True,
        )
        x = np.asarray(data[:, 0], dtype=np.float64)
        return x

    def _band_indices(self, freqs: np.ndarray) -> Tuple[int, int, np.ndarray]:
        fs = float(self.config.fs)
        fmax = self.config.fmax if self.config.fmax is not None else fs / 2.0
        if fmax <= 0 or fmax > fs / 2.0:
            fmax = fs / 2.0

        band = np.where((freqs >= self.config.fmin) & (freqs <= fmax))[0]
        if band.size < 3:
            return 0, -1, band
        k0 = int(band[0])
        k1 = int(band[-1])
        k0 = max(k0, 1)
        return k0, k1, band

    def estimate_from_array(self, x: np.ndarray) -> Optional[float]:
        # 兼容你原版：单段 FFT 主峰
        x = np.asarray(x)
        if x.ndim != 1:
            x = x.reshape(-1)

        n = int(len(x))
        if n < 8:
            return None

        fs = float(self.config.fs)

        x = x.astype(np.float64, copy=False)
        if self.config.remove_mean:
            x = x - np.mean(x)

        w = get_window(self.config.window, n, fftbins=True)
        X = np.fft.rfft(x * w)
        mag = np.abs(X)
        freqs = np.fft.rfftfreq(n, d=1.0 / fs)

        k0, k1, band = self._band_indices(freqs)
        if band.size < 3:
            return None

        k_peak = k0 + int(np.argmax(mag[k0 : k1 + 1]))
        if self.config.refine_peak:
            k_peak_fine = _parabolic_interpolation(mag, k_peak)
            f_peak = k_peak_fine * fs / n
        else:
            f_peak = float(freqs[k_peak])
        return float(f_peak)

    def estimate_from_array_robust(self, x: np.ndarray):
        """
        抗噪版本：
        - 将信号切段做（幅度谱或功率谱）平均，减少随机尖峰
        - 对峰做 peak-to-median 门限
        - 可选检查二次谐波
        """
        x = np.asarray(x)
        if x.ndim != 1:
            x = x.reshape(-1)

        n = int(len(x))
        if n < 8:
            return (None, {}) if self.config.return_debug else None

        fs = float(self.config.fs)
        x = x.astype(np.float64, copy=False)
        if self.config.remove_mean:
            x = x - np.mean(x)

        # --- Welch-like 分段 ---
        segs = int(self.config.welch_segments)
        if segs == 1:
            # 退化：和原来一致，但加可信度判定
            n_fft = _next_pow2(n) if self.config.pad_to_pow2 else n
            w = get_window(self.config.window, n, fftbins=True)
            X = np.fft.rfft(x * w, n=n_fft)
            P = (np.abs(X) ** 2)  # power
            freqs = np.fft.rfftfreq(n_fft, d=1.0 / fs)
        else:
            seg_len = n // segs
            if seg_len < 8:
                return (None, {"reason": "segment too short"}) if self.config.return_debug else None

            hop = int(round(seg_len * (1.0 - float(self.config.welch_overlap))))
            hop = max(1, hop)

            # 取尽量多的段
            starts = list(range(0, n - seg_len + 1, hop))
            if len(starts) < 1:
                return (None, {"reason": "no segments"}) if self.config.return_debug else None

            n_fft = _next_pow2(seg_len) if self.config.pad_to_pow2 else seg_len
            w = get_window(self.config.window, seg_len, fftbins=True)
            acc = None
            for st in starts:
                seg = x[st : st + seg_len]
                seg = seg - np.mean(seg)  # 每段再去均值，抗漂移更强
                X = np.fft.rfft(seg * w, n=n_fft)
                Pk = (np.abs(X) ** 2)
                acc = Pk if acc is None else (acc + Pk)
            P = acc / float(len(starts))
            freqs = np.fft.rfftfreq(n_fft, d=1.0 / fs)

        k0, k1, band = self._band_indices(freqs)
        if band.size < 3:
            return (None, {"reason": "band too small"}) if self.config.return_debug else None

        # 选峰
        k_peak = k0 + int(np.argmax(P[k0 : k1 + 1]))
        peak = float(P[k_peak])
        floor = _robust_stats_floor(P[k0 : k1 + 1])

        debug = {
            "k_peak": int(k_peak),
            "f_bin": float(freqs[k_peak]),
            "peak_power": peak,
            "floor_median_power": floor,
            "peak_to_median": (peak / floor) if floor > 0 else float("inf"),
            "n_fft": int(len(freqs) * 2 - 2),
        }

        # 可信度门限：峰值必须显著高于噪声底
        if floor <= 0:
            # floor=0 只会在全 0 之类情况出现
            return (None, {"reason": "floor<=0", **debug}) if self.config.return_debug else None

        if peak / floor < float(self.config.min_peak_to_median):
            return (None, {"reason": "low_snr", **debug}) if self.config.return_debug else None

        # 峰值细化（对 power 也可以做 3 点插值）
        if self.config.refine_peak:
            k_peak_fine = _parabolic_interpolation(P, k_peak)
            f_peak = float(k_peak_fine) * fs / float((len(freqs) - 1) * 2)
        else:
            f_peak = float(freqs[k_peak])

        debug["f_peak"] = float(f_peak)

        # 可选：二次谐波检查
        if self.config.require_harmonic:
            f2 = 2.0 * f_peak
            if f2 <= freqs[-1]:
                # 找 f2 附近最大值
                tol = float(self.config.harmonic_tol_hz)
                idx = np.where((freqs >= f2 - tol) & (freqs <= f2 + tol))[0]
                if idx.size > 0:
                    p2 = float(np.max(P[idx]))
                    debug["harm2_power"] = p2
                    debug["harm2_ratio"] = p2 / peak
                    if (p2 / peak) < float(self.config.harmonic_min_ratio):
                        return (None, {"reason": "harmonic_missing", **debug}) if self.config.return_debug else None
                else:
                    return (None, {"reason": "harmonic_out_of_bins", **debug}) if self.config.return_debug else None

        return (float(f_peak), debug) if self.config.return_debug else float(f_peak)

    def estimate_robust(self, duration: float):
        x = self.record(duration=duration)
        return self.estimate_from_array_robust(x)


# if __name__ == "__main__":
#     # 你原来是 0.5s；如果环境噪声明显，建议先拉到 1.0s 再试（分辨率+平均都更稳）
#     cfg = VibFreqConfig(
#         fs=48000,
#         device=None,
#         fmin=10,
#         fmax=2000,
#         welch_segments=4,          # 0.5s 会被切成 4 段，每段约 0.125s
#         welch_overlap=0.5,
#         min_peak_to_median=10.0,   # 适当调大可更保守（减少误报，但可能更容易返回 None）
#         require_harmonic=False,    # 如果是电机/转速类信号，开 True 往往更稳
#         return_debug=True,
#     )
#
#     est = VibFreqEstimator(cfg)
#     f, dbg = est.estimate_robust(duration=0.5)
#     print("freq:", f)
#     print("debug:", dbg)