# M600099 GRR & CPK Analyzer

> GRR (Gauge Repeatability & Reproducibility) 和 CPK (Process Capability) 分析工具，支持从 MT7 测试站的 Jason Logs 原始数据自动生成专业报告。

---

## 支持的数据格式

### 工作流 A — Jason Logs → 中间 Excel → 分析报告
```
GRR Jason Logs (原始 JSON 文件)
        ↓ [App: 📁 Parse Jason Logs 模式]
HVTE-M600099_GRR_data.xlsx (中间格式)
        ↓ [App: 📂 Load Intermediate Excel 模式]
Beta-GRR-Charger_MT7-HVTE-M600099_YYYYMMDD.docx (最终报告)
```

### 工作流 B — 直接加载中间 Excel
```
HVTE-M600099_GRR_data.xlsx (已有中间文件)
        ↓ [App: 📂 Load Intermediate Excel 模式]
Beta-GRR-Charger_MT7-HVTE-M600099_YYYYMMDD.docx (最终报告)
```

---

## GRR 数据格式

### GRR From Sheet (FORM-004090)
| 字段 | 说明 |
|------|------|
| Sample | 零件编号（1-10） |
| Inspector | 检验员编号 |
| PNUM-4024 ~ PNUM-4056 | 9 个 LED 强度值 |
| 3 次重复测量 × 3 个检验员 × 10 个零件 = 270 条记录 |

### 支持的 LED 指标
| PNUM | 指标 | LSL | USL |
|------|------|-----|-----|
| 4024 | LED_RED_D303 | 13000 | 65555 |
| 4028 | LED_RED_D304 | 8000 | 65555 |
| 4032 | LED_WHITE_D305 | 11500 | 65555 |
| 4036 | LED_WHITE_D306 | 11500 | 65555 |
| 4040 | LED_WHITE_D307 | 15000 | 65555 |
| 4044 | LED_WHITE_D308 | 10000 | 65555 |
| 4048 | LED_WHITE_D309 | 15000 | 65555 |
| 4052 | LED_AMBER_D310 | 4500 | 65555 |
| 4056 | LED_WHITE_D311 | 15000 | 65555 |

---

## 安装

```bash
pip install -r requirements.txt
```

### 依赖
- `PyQt5` ≥ 5.15 — GUI 框架
- `pandas` ≥ 1.3 — 数据处理
- `numpy` ≥ 1.21 — 数值计算
- `scipy` ≥ 1.7 — 统计函数
- `openpyxl` ≥ 3.0 — Excel 读写
- `python-docx` ≥ 0.8.10 — Word 报告生成
- `pyinstaller` ≥ 5.0 — 打包为 exe

---

## 使用方法

### 方式一：Jason Logs → 报告（完整流程）

1. 启动应用，选择 **📁 Parse Jason Logs** 模式
2. 设置 GRR 结构参数（零件数/操作员数/重复次数）
3. 点击 **Browse** 选择包含 JSON 日志文件的文件夹
4. 点击 **▶ Parse & Generate Intermediate Excel** 生成中间 Excel
5. 解析完成后，切换到 **📂 Load Intermediate Excel** 模式
6. 加载生成的中间 Excel，选择要分析的 LED 项目
7. 勾选 GRR / CPK 分析选项，点击 **▶ Run Selected**
8. 报告自动保存到 `output/` 文件夹

### 方式二：直接加载中间 Excel

1. 启动应用，选择 **📂 Load Intermediate Excel** 模式
2. 点击 **Load Excel File** 加载 `HVTE-M600099_GRR_data.xlsx`
3. 选择 Sheet（通常是 `log_YYYYMMDDHHMMSS`）
4. 勾选要分析的 LED 项目
5. 设置分析选项，点击 **▶ Run Selected**
6. 报告自动保存到 `output/` 文件夹

---

## GRR 分析方法

**AIAG 均值极差法（X̄–R 法）**

| 指标 | 说明 | 判定标准 |
|------|------|----------|
| EV (Repeatability) | 设备重复性变异 | — |
| PV (Reproducibility) | 操作员再现性变异 | — |
| TV (Total Variation) | 总体变异 | — |
| %GR&R | GRR 占容差比例 | ≤10% 优秀，≤30% 可接受，>30% 不可接受 |
| NDC | 可区分类别数 | ≥5 可接受，≥10 优秀 |
| %P/T | 重复性占容差比例 | ≤10% |

## CPK 分析方法

**组内标准差 + 整体标准差双算法**

| 指标 | 说明 |
|------|------|
| Cp / Cpk | 组内 sigma（短期能力） |
| Pp / Ppk | 整体 sigma（长期能力） |

---

## Minitab 图表集成（可选）

1. 安装 Minitab 22
2. 在分析选项中点击 **Browse** 指定 `C:\Program Files\Minitab\Minitab 22\Mtb.exe`
3. 勾选 **Insert Minitab charts into report**
4. 报告中的图表将由 Minitab 自动生成并嵌入

---

## 输出报告格式

`output/Beta-GRR-Charger_MT7-HVTE-M600099_YYYYMMDD_HHMMSS.docx`

包含：
- 封面（产品/工站/日期/审批信息）
- 汇总表（所有项目 %GR&R / %P/T / NDC）
- 明细表（每个 LED 指标的完整分析结果）
- Minitab 图表（可选嵌入）

---

## 打包为 Windows exe

```batch
build_windows.bat
```

输出：`dist/M600099_GRR_CPK_Analyzer.exe`

---

## 架构

```
m600099_grr_cpk_app/
├── main.py                  # 入口（自动检测 PyQt5 / tkinter）
├── core/
│   ├── json_parser.py      # Jason logs → 中间 Excel 解析器
│   ├── data_loader.py       # Excel 读取（MT7 log / GRR template 双格式）
│   ├── grr_analyzer.py     # AIAG 均值极差法 GRR
│   └── cpk_analyzer.py     # CPK/Ppk 计算
├── ui/
│   ├── main_window.py      # PyQt5 主窗口（双工作流）
│   ├── tkinter_window.py   # tkinter 后备窗口
│   └── styles.py           # Qt 样式表
├── report/
│   └── report_generator.py # Word 报告生成器
└── utils/
    └── config.py           # LED 规格限配置
```

---

## 版本

- **v1.1.0** — 新增 Jason Logs 解析模块，双工作流支持
- **v1.0.0** — 初始版本，GRR/CPK 分析

---

🦞 simon's claw
