
def generate_fa(log_info, repair_db):
    # fa_results = [ fail in log_info["failures"]: fa_results = []
    # matched = repair_db[
    #         repair_db["error_code"] == fail["error_code"]
    #     ]
    fa_results = []
    for fail in log_info["failures"]:
        # fa_results.append(fail)
        matched = repair_db[
            repair_db["error_code"] == fail["error_code"]
            ]
        if not matched.empty:
            root_cause = matched.iloc[0]["root_cause"]
            action = matched.iloc[0]["action"]
        else:
            root_cause = "待分析（新问题）"
            action = "建议补充实验 / Debug"

        fa_results.append({
            "module": fail["module"],
            "error_code": fail["error_code"],
            "root_cause": root_cause,
            "action": action
        })

    return fa_results

