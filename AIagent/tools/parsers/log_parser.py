import re

class LogParser:

    FAIL_PATTERNS = [
        r"FAIL",
        r"NG",
        r"ERROR",
        r"TIMEOUT"
    ]

    def parse(self, log_path):
        fail_lines = []

        with open(log_path, "r", errors="ignore") as f:
            for line in f:
                if any(re.search(p, line, re.IGNORECASE)
                       for p in self.FAIL_PATTERNS):
                    fail_lines.append(line.strip())

        return fail_lines