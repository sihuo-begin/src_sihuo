import pandas as pd
from pathlib import Path

class ExcelParser:
    def parse(self, excel_dir):
        results = []

        for file in Path(excel_dir).glob("*.xlsx"):
            df = pd.read_excel(file)

            results.append({
                "file": file.name,
                "columns": df.columns.tolist(),
                "data": df
            })

        return results