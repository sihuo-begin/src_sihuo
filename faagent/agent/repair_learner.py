import pandas as pd

def load_repair_excel(file):
    df = pd.read_excel(file)

    # 标准化字段
    df = df.rename(columns={
        "故障代码": "error_code",
        "根因": "root_cause",
        "对策": "action"
    })

    return df