import os


class MtbMacroBuilder:

    def __init__(self, output):
        self.output = output

    def generate_full_macro(self, data):

        macro_path = os.path.join(self.output, "run_all.mtb")

        lines = []

        # ✅ SET 数据
        for i, (item, info) in enumerate(data.items(), start=1):

            values = info["values"]

            # ✅ 防止坏数据
            if len(values) == 0 or len(set(values)) <= 1:
                print(f"⚠️ 跳过 {item}")
                continue

            lines.append(f"SET C{i}")

            for v in values:
                lines.append(str(int(v)))

            lines.append("END.\n")

        # ✅ 分析 + 定位日志
        for i, (item, info) in enumerate(data.items(), start=1):

            img = os.path.abspath(
                os.path.join(self.output, f"{item}.png")
            )

            lines.append(f'''
NOTE "RUNNING {item}";

CAPABILITY C{i};
LSL {info["lsl"]};
USL {info["usl"]}.

GSAVE "{img}";
JPEG.

ERASE ALL;
''')

        lines.append("QUIT.")

        with open(macro_path, "w") as f:
            f.write("\n".join(lines))

        print("✅ run_all.mtb:", macro_path)

        return macro_path