# core/macro_validator.py

import os


class MacroValidator:

    def __init__(self):
        pass

    def check_csv(self, csv_path):

        if not os.path.exists(csv_path):
            raise Exception(f"❌ CSV不存在: {csv_path}")

        with open(csv_path, "r") as f:
            first_line = f.readline().strip()

        # ✅ 判断是否header（是否含字母）
        has_header = any(c.isalpha() for c in first_line)

        print(f"✅ CSV Header检测: {has_header}")

        return has_header

    def check_macro(self, macro_path):

        if not os.path.exists(macro_path):
            raise Exception(f"❌ Macro不存在: {macro_path}")

        with open(macro_path, "r") as f:
            content = f.read()

        errors = []

        if "READ" not in content:
            errors.append("缺少 READ")

        if "CAPABILITY" not in content:
            errors.append("缺少 CAPABILITY")

        if "GSAVE" not in content:
            errors.append("缺少 GSAVE")

        if "QUIT" not in content:
            errors.append("缺少 QUIT")

        if errors:
            raise Exception(f"❌ Macro结构错误: {errors}")

        print("✅ Macro结构检查通过")

    def build_safe_read(self, csv_path, n_cols, has_header):

        if has_header:
            # ✅ 兼容Minitab版本写法
            return f'''
READ "{csv_path}";
SKIP 1;
C1-C{n_cols}.
'''
        else:
            return f'''
READ "{csv_path}";
C1-C{n_cols}.
'''

    def validate_environment(self, exe_path):

        if not os.path.exists(exe_path):
            raise Exception(f"❌ Minitab路径错误: {exe_path}")

        print("✅ Minitab路径正常")
