import logging
import os
from datetime import datetime

base = os.path.dirname(__file__)
if os.path.exists(r"D:\\"):
    log_dir = r"d:\cell_logs"
else:
    log_dir = r"c:\cell_logs"


class Log:
    """
    每个cell独立logger，可在无SN时用临时名，有SN后重命名日志文件且不中断写入。
    文件名格式: cell_1_20240624_123456.log → cell_1_20240624_123456_SNxxx.log
    """

    def __init__(self, cell_id):
        os.makedirs(log_dir, exist_ok=True)
        print(f"create log for cell:{cell_id}")
        self.cell_log_id = cell_id
        self.sn = None
        self.log_dir = log_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(f"cell_{self.cell_log_id}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self._set_handler(self._temp_log_path())

    def _temp_log_path(self):
        return os.path.join(self.log_dir, f"cell_{self.cell_log_id}_{self.timestamp}.log")

    def _sn_log_path(self, sn):
        return os.path.join(self.log_dir, f"cell_{self.cell_log_id}_{sn}_{self.timestamp}.log")

    def _set_handler(self, log_path):
        for h in list(self.logger.handlers):
            if isinstance(h, logging.FileHandler):
                self.logger.removeHandler(h)
                h.close()
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d in %(funcName)s]: %(message)s")
        )
        self.logger.addHandler(handler)
        self.log_path = log_path

    def set_sn(self, sn):
        """
        获取到SN后调用，自动重命名日志文件，保留原时间戳，文件名变为 cell_{cell_id}_{timestamp}_{sn}.log
        """
        if sn and sn != self.sn:
            new_path = self._sn_log_path(sn)
            # 只有在旧文件存在且新名字不同才重命名
            try:
                if os.path.exists(self.log_path) and self.log_path != new_path:
                    os.rename(self.log_path, new_path)
            except Exception as e:
                self.logger.warning(f"Log file rename failed: {e}")
            self._set_handler(new_path)
            self.sn = sn

    def read_log(self, max_lines=200):
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return "".join(lines[-max_lines:])
        except Exception as e:
            return f"(日志读取失败: {e})"

    def clear_log(self):
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                pass
        except Exception:
            pass


def setup_main_logger(log_dir=r"C:\main_logs"):
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"main_{timestamp}.log")
    logger = logging.getLogger("main")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_path) for h in logger.handlers
    ):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d in %(funcName)s]: %(message)s")
        )
        logger.addHandler(handler)
    logger.log_path = log_path  # 方便后续读取
    return logger
