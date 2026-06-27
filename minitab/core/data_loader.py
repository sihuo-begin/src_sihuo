
import pandas as pd

class DataLoader:

    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        df = pd.read_csv(self.file_path)

        if "Measurement" not in df.columns:
            raise ValueError("缺少 Measurement 列")

        return df
