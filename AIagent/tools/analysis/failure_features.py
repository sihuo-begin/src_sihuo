from collections import Counter

def extract_features(fail_lines):
    keywords = []

    for line in fail_lines:
        if "POWER" in line.upper():
            keywords.append("POWER")
        if "CLK" in line.upper():
            keywords.append("TIMING")
        if "I2C" in line.upper():
            keywords.append("INTERFACE")

    return Counter(keywords)