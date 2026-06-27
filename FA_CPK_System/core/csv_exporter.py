import pandas as pd
import os

class CsvExporter:

    def __init__(self, output):
        self.output = output

    def export_all(self, data):

        max_len = max(len(v["values"]) for v in data.values())

        df_dict = {}

        for item, info in data.items():
            values = info["values"]
            padded = values + [None] * (max_len - len(values))
            df_dict[item] = padded

        df = pd.DataFrame(df_dict)

        csv_path = os.path.abspath(
            os.path.join(self.output, "all_data.csv")
        )

        # ✅ ✅ 核心：无header（避免READ问题）
        df.to_csv(csv_path, index=False, header=False)

        print("✅ CSV生成:", csv_path)

        for i, item in enumerate(data.keys(), start=1):
            print(f"C{i} -> {item}")

        return csv_path, len(df_dict)
