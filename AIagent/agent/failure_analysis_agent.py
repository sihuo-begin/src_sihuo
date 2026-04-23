import yaml

from ..tools.analysis.root_cause_engine import infer_root_cause
from ..tools.analysis.failure_features import extract_features
from ..tools.parsers.log_parser import LogParser
from ..tools.parsers.excel_parser import ExcelParser



class FailureAnalysisAgent:
    def __init__(self,):
        self.log_parser = LogParser
        self.excel_parser = ExcelParser
        path = "AIagent/tools/power.yaml"
        with open(path, encoding="utf-8") as f:
            rules_data = yaml.safe_load(f)
        self.rules =rules_data["POWER_ISSUE"]

    def run(self, log_path, excel_path):
        logs = self.log_parser.parse(log_path)
        features = extract_features(logs)

        excel_data = self.excel_parser.parse(excel_path)

        root_cause = infer_root_cause(
            features,
            self.rules
        )

        return {
            "features": features,
            "root_cause_rank": root_cause
        }

    if __name__ == "__main__":
        FailureAnalysisAgent.run()