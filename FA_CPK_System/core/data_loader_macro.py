import os
import pandas as pd


class DataLoaderMacro:

    def __init__(self, output, chunk_size=1000):
        self.output = output
        self.chunk_size = chunk_size

    def build_from_csv(self, csv_path):

        df = pd.read_csv(csv_path, header=None)

        macro_path = os.path.join(self.output, "data_loader.mtb")
        # macro_path = ".\output\charts\\data_loader.mtb"

        lines = []

        for col in range(df.shape[1]):

            col_data = df[col].dropna().astype(int).tolist()

            print(f"✅ C{col+1} points: {len(col_data)}")

            # ✅ 分块写入
            for i in range(0, len(col_data), self.chunk_size):

                chunk = col_data[i:i+self.chunk_size]

                lines.append(f"SET C{col+1}")

                for v in chunk:
                    lines.append(str(v))

                lines.append("END.\n")

        with open(macro_path, "w") as f:
            f.write("\n".join(lines))

        print("✅ data_loader.mtb (分块模式)")

        return os.path.abspath(macro_path)