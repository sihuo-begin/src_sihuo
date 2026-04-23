import json

def parse_test_log(file):
    log = json.load(file)

    failures = []
    for item in log.get("tests", []):
        if item.get("result") == "FAIL":
            failures.append({
                "module": item.get("module"),
                "error_code": item.get("error_code"),
                "message": item.get("message"),
            })

    return {
        "sn": log.get("sn"),
        "station": log.get("station"),
        "version": log.get("fw_version"),
        "failures": failures
    }