# FCST Waterfall 比对工具

将客户每周提供的 3 份 FCST 报表上传，自动生成项目工程师标准格式的比对 Excel 报表。

## 核心功能

- **3 份 xlsx 上传 → 1 份比对报表**：在浏览器中上传 3 份按时间顺序排列的 FCST，自动生成 8 个 Sheet
- **完全本地处理**：数据不上传云端，适合企业敏感数据
- **可视化进度**：实时日志 + 进度条
- **一键下载**：处理完成后直接下载

## 报表输出结构

| Sheet | 内容 |
|---|---|
| Summary | 整体指标 (Kit/Holder/PC/Total) + 3 Snapshot 差异 + Sheet 索引 |
| V_Kit_Holder | VERSION CODE × Kit+Holder 合并 |
| V_Kit_PC | VERSION CODE × Kit+Pocket Charger 合并 |
| V_Kit_Holder_Color | VERSION × Kit/Holder × COLOR |
| V_Kit_PC_Color | VERSION × Kit/PC × COLOR |
| V_Kit_Holder_Market | VERSION × Kit/Holder × MARKET |
| V_Kit_PC_Market | VERSION × Kit/PC × MARKET |
| SKU | 按 SKU 全量明细 (V+IG+Color+Market) |

每个 Sheet 内部含 2 套表：
- 【按周比较】 67 个自然周 × 1 列
- 【按月比较】 18 个月 × 1 列

每行块 5 行：WK21 SF04 → WK22 SF05 → WK23 SF05 → ΔWK21→22 → ΔWK22→23

## 使用方法

### 1. 启动服务

```bash
cd fcst_tool
./start.sh
```

或直接：
```bash
python3 app.py
```

启动后访问：**http://localhost:8765**

### 2. 上传报表

按时间顺序上传 3 份 xlsx（最早 → 中间 → 最新）：
- Snapshot 1: 较早的 FCST (例：SF04 WK21)
- Snapshot 2: 中间 FCST (例：SF05 WK22)
- Snapshot 3: 最新 FCST (例：SF05 WK23)

填写报表名称（默认 `FCST_Waterfall_比对`）。

### 3. 生成 + 下载

点击「🚀 生成比对报表」，等待进度条 100%，点击「⬇️ 下载报表」。

## 目录结构

```
fcst_tool/
├── fcst_engine.py    # 核心引擎（解析 + 报表生成）
├── app.py            # FastAPI 后端
├── static/
│   └── index.html    # 前端页面
├── start.sh          # 启动脚本
├── README.md         # 本文档
├── uploads/          # 临时上传（处理完自动清理）
└── outputs/          # 生成的报表
```

## 引擎 API

如需在自己的脚本中调用：

```python
from fcst_engine import parse_fcst_xlsx, build_report

# 1. 解析 3 份 xlsx
all_data, weeks = parse_fcst_xlsx(
    'WK21.xlsx', 'WK22.xlsx', 'WK23.xlsx',
    progress_cb=lambda m: print(m)
)

# 2. 生成比对报表
build_report(
    all_data, weeks,
    'output.xlsx',
    progress_cb=lambda m: print(m)
)
```

数据格式：
```python
all_data['WK21'] = [
    {'version': 'ILUMAI', 'item_group': 'Kit', 'market': 'Poland',
     'sku': 'DC002272.00', 'core_color': 'Slate',
     'monthly': [0, 0, ..., 100, 50, 0],  # 12 个月
     'total': 150.0},
    ...
]
```

## 环境要求

- Python 3.8+
- fastapi
- uvicorn
- python-multipart
- openpyxl

启动脚本会自动安装缺失依赖。

## 端口配置

默认 8765，可通过环境变量修改：
```bash
PORT=9000 ./start.sh
```

## 停止服务

`Ctrl + C` 或：
```bash
pkill -f "python3 app.py"
```

## 故障排查

| 问题 | 解决方案 |
|---|---|
| `Form data requires python-multipart` | `pip install python-multipart` |
| 端口被占用 | `PORT=9000 ./start.sh` |
| xlsx 解析失败 | 确保文件包含 `2026` 工作表（项目工程师的 FCST 标准结构） |
| 浏览器打不开 | 确认防火墙允许 8765 端口 |

## 数据安全

- 所有文件仅在本地处理，不上传到任何云端
- 上传文件处理完成后自动清理
- 生成的报表保留在 `outputs/` 目录，由用户自行管理
