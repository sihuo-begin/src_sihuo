def normalize_bin_table(df):
    return {
        "bin": df["BIN"].value_counts().to_dict(),
        "total": len(df)
    }


def normalize_param(df):
    violations = df[
        (df["VALUE"] < df["LSL"]) |
        (df["VALUE"] > df["USL"])
    ]

    return {
        "total": len(df),
        "violations": len(violations),
        "violation_rate": len(violations) / len(df)
    }