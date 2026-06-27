# import numpy as np
# data = [17336, 18862, 19686, 22339, 18222, 21430, 22160, 25624, 23039, 22692, 17336, 18862, 19686, 22692, 18222, 21055, 22160, 25925, 23380, 22516, 17561, 18862, 19686, 22866, 18222, 21055, 22160, 25925, 23716, 22692, 17783, 19071, 19686, 23039, 18222, 21055, 22160, 26075, 23380, 22339, 17561, 19071, 19686, 23380, 18222, 21055, 22160, 26075, 23716, 22160, 17561, 19071, 19686, 23882, 18222, 21055, 22339, 26075, 23716, 22160, 17783, 19071, 19686, 23882, 18437, 21055, 22339, 26075, 23716, 22160, 17561, 18862, 19686, 24209, 18437, 21055, 22339, 26072, 23716, 22160, 17783, 19071, 19686, 24371, 18222, 21055, 22339, 26075, 23549, 22160]
# # class MinitabCPK:
#
#     def __init__(self, data=data, lsl=4500, usl=65555):
#         self.data = np.array(data, dtype=np.float64)
#         self.lsl = lsl
#         self.usl = usl
#
#     # ✅ Step1：均值
#     def mean(self):
#         return np.mean(self.data)
#
#     # ✅ Step2：Moving Range
#     def moving_range(self):
#         return np.abs(np.diff(self.data))
#
#     # ✅ Step3：σ_within（关键）
#     def sigma_within(self):
#         mr = self.moving_range()
#         mr_bar = np.mean(mr)
#
#         d2 = 1.128  # MR subgroup size=2
#         return mr_bar / d2
#
#     # ✅ Step4：Cpk
#     def cpk(self):
#         mu = self.mean()
#         sigma = self.sigma_within()
#
#         cpu = (self.usl - mu) / (3 * sigma) if self.usl is not None else np.inf
#         cpl = (mu - self.lsl) / (3 * sigma) if self.lsl is not None else np.inf
#
#         return min(cpu, cpl)
#
#     # ✅ Step5：Cp（可选）
#     def cp(self):
#         sigma = self.sigma_within()
#         return (self.usl - self.lsl) / (6 * sigma)
#
#     # ✅ 总输出
#     def summary(self):
#         print(self.cpk())
#         return {
#             "mean": self.mean(),
#             "sigma_within": self.sigma_within(),
#             "Cp": self.cp() if self.lsl and self.usl else None,
#             "Cpk": self.cpk()
#         }

# import numpy as np
#
# class MinitabCPK_Pooled:
#
#     def __init__(self, data=data, subgroup_size=6, lsl=4500, usl=65555):
#         self.data = np.array(data, dtype=np.float64)
#         print(self.data)
#         self.subgroup_size = subgroup_size
#         self.lsl = lsl
#         self.usl = usl
#
#     # ✅ 分组
#     def split_groups(self):
#         n = self.subgroup_size
#         return self.data[:len(self.data)//n*n].reshape(-1, n)
#
#     # ✅ pooled sigma（核心）
#     def sigma_within(self):
#         groups = self.split_groups()
#         print(groups)
#         n = self.subgroup_size
#
#         variances = np.var(groups, axis=1, ddof=1)
#
#         numerator = np.sum((n - 1) * variances)
#         denominator = np.sum((n - 1) * np.ones(len(groups)))
#
#         return np.sqrt(numerator / denominator)
#
#     # ✅ Cpk
#     def cpk(self):
#         mu = np.mean(self.data)
#         sigma = self.sigma_within()
#         print(sigma)
#         cpu = (self.usl - mu) / (3 * sigma) if self.usl else np.inf
#         cpl = (mu - self.lsl) / (3 * sigma) if self.lsl else np.inf
#
#         return min(cpu, cpl)
#
#     # ✅ Cp
#     def cp(self):
#         sigma = self.sigma_within()
#         return (self.usl - self.lsl) / (6 * sigma)
#
#     def summary(self):
#         return {
#             "mean": np.mean(self.data),
#             "sigma_within": self.sigma_within(),
#             "Cpk": self.cpk(),
#             "Cp": self.cp(),
#         }
#
#     import numpy as np
#
    # def c4(n):
    #     # 常用值（你用6就够）
    #     c4_table = {
    #         2: 0.7979,
    #         3: 0.8862,
    #         4: 0.9213,
    #         5: 0.9400,
    #         6: 0.9515,
    #         7: 0.9594,
    #         8: 0.9650,
    #         9: 0.9693,
    #         10: 0.9727
    #     }
    #     return c4_table.get(n, 1.0)
#
#     def pooled_sigma(data, subgroup_size, unbiased=True):
#         data = np.array(data, dtype=np.float64)
#
#         groups = data[:len(data) // subgroup_size * subgroup_size]
#         groups = groups.reshape(-1, subgroup_size)
#
#         variances = np.var(groups, axis=1, ddof=1)
#         n = subgroup_size
#
#         sigma = np.sqrt(np.sum((n - 1) * variances) / np.sum((n - 1) * np.ones(len(groups))))
#
#         if unbiased:
#             sigma = sigma / c4(n)
#
#         return sigma
#
#     def cpk(data, lsl, usl, subgroup_size=6, unbiased=True):
#         mu = np.mean(data)
#         sigma = pooled_sigma(data, subgroup_size, unbiased)
#
#         cpu = (usl - mu) / (3 * sigma)
#         cpl = (mu - lsl) / (3 * sigma)
#
#         return min(cpu, cpl)
# import numpy as np
# import math
#
#
# class CapabilityEngine:
#
#     def __init__(
#         self,
#         data = data,
#         lsl=4500,
#         usl=65555,
#         subgroup_size=6,
#         mode="POOLED",          # POOLED / AMR
#         bias="UNBIASED",        # UNBIASED / OBIASED
#         toler=6                 # 对应 TOLER
#     ):
#         self.data = np.array(data, dtype=np.float64)
#         self.lsl = lsl
#         self.usl = usl
#         self.subgroup_size = subgroup_size
#         self.mode = mode.upper()
#         self.bias = bias.upper()
#         self.toler = toler
#
#     # ✅ c4常数（无偏修正）
#     def c4(self, n=6):
#         # return math.sqrt(2/(n-1)) * (math.gamma(n/2) / math.gamma((n-1)/2))
#         # return 0.9693
#         # return 0.9515
#         return 0.9978
#
#     # ✅ 分组
#     def split_groups(self):
#         n = self.subgroup_size
#         usable_len = len(self.data) // n * n
#         return self.data[:usable_len].reshape(-1, n)
#
#     # ✅ pooled sigma
#     def sigma_pooled(self):
#         groups = self.split_groups()
#         n = self.subgroup_size
#
#         variances = np.var(groups, axis=1, ddof=1)
#
#         numerator = np.sum((n - 1) * variances)
#         denominator = (n - 1) * len(groups)
#
#         sigma = math.sqrt(numerator / denominator)
#
#         # ✅ bias correction
#         if self.bias == "UNBIASED":
#             sigma = sigma / self.c4(n)
#
#         return sigma
#
#     # ✅ AMR sigma（移动极差）
#     def sigma_amr(self):
#         mr = np.abs(np.diff(self.data))
#         mr_bar = np.mean(mr)
#
#         d2 = 1.128  # MR subgroup size=2
#
#         sigma = mr_bar / d2
#
#         # AMR一般不做c4修正（Minitab逻辑）
#         return sigma
#
#     # ✅ 统一σ入口
#     def sigma_within(self):
#         if self.mode == "POOLED":
#             return self.sigma_pooled()
#         elif self.mode == "AMR":
#             return self.sigma_amr()
#         else:
#             raise ValueError(f"Unsupported mode: {self.mode}")
#
#     # ✅ overall sigma（用于Ppk）
#     def sigma_overall(self):
#         return np.std(self.data, ddof=1)
#
#     # ✅ Cp
#     def cp(self):
#         sigma = self.sigma_within()
#         return (self.usl - self.lsl) / (self.toler * sigma)
#
#     # ✅ Cpk
#     def cpk(self):
#         mu = np.mean(self.data)
#         print(mu)
#         sigma = self.sigma_within()
#         print(sigma)
#
#         cpu = (self.usl - mu) / (self.toler/2 * sigma)
#         cpl = (mu - self.lsl) / (self.toler/2 * sigma)
#         print(cpu,cpl)
#         return min(cpu, cpl)
#
#     # ✅ Ppk
#     def ppk(self):
#         mu = np.mean(self.data)
#         sigma = self.sigma_overall()
#
#         cpu = (self.usl - mu) / (3 * sigma)
#         cpl = (mu - self.lsl) / (3 * sigma)
#
#         return min(cpu, cpl)
#
#     # ✅ 汇总
#     def summary(self):
#         return {
#             "mean": np.mean(self.data),
#             "sigma_within": self.sigma_within(),
#             "sigma_overall": self.sigma_overall(),
#             "Cp": self.cp(),
#             "Cpk": self.cpk(),
#             "Ppk": self.ppk(),
#         }
#
# result = CapabilityEngine()
# print(result.summary())
# import cv2
# import pytesseract
# import re
# from PIL import Image
#
#
# class CPKImageExtractor:
#
#     def __init__(self, image_path= "C:\\Users\dmnsihuo\cpk_charts\cpk_LEDAMBERD310INTENSITY.jpg"):
#         self.image_path = image_path


# import easyocr
#
# reader = easyocr.Reader(['en'])  # 英文
#
# result = reader.readtext('C:\\Users\dmnsihuo\cpk_charts\cpk_LEDAMBERD310INTENSITY.jpg')
# # print(result)
# len_item = len(result)
# for key in range(len_item):
#     # print(key)
#     # print(result[key])
#     # print(len(result[key]))
#     if "Cpk" in result[key]:
#         cpk = result[key+1][1]
#         print("cpk is {}".format(cpk))

import easyocr
import cv2
import re
path = 'C:\\Users\dmnsihuo\AppData\Local\Temp\\tmp6vyimvwv.png'
# ✅ 全局初始化（关键）
reader = easyocr.Reader(['en'], gpu=False)


def fast_extract_cpk(path):
    img = cv2.imread(path)

    h, w = img.shape[:2]
    print(h, w)
    # # ✅ 裁剪右上角
    # roi = img[0:int(h), int(w):w]
    # roi = img[0:int(h*0.7), int(w*0.6):w]

    # ✅ 降采样
    roi = cv2.resize(img, None, fx=0.6, fy=0.6)

    # ✅ 灰度
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # ✅ OCR
    results = reader.readtext(
        roi,
        # gray,
        # detail=0,
        # allowlist='Cpk0123456789.'
    )
    print(results)
    len_item = len(results)
    for key in range(len_item):
        # print(key)
        # print(result[key])
        # print(len(result[key]))
        if "Cpk" in results[key]:
            cpk = results[key+1][1]
            print("cpk is {}".format(cpk))
            break
    # text = " ".join(results)
    # print(text)

    # # ✅ 提取
    # match = re.search(r'Cpk\s*=?\s*([0-9]+\.[0-9]+)', text)
    #
    # if match:
    #     return float(match.group(1))
    #
    # nums = re.findall(r'\d+\.\d+', text)
    # return float(max(nums)) if nums else None
fast_extract_cpk(path=path)
