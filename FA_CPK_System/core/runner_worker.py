from PyQt5.QtCore import QThread, pyqtSignal


class RunnerWorker(QThread):

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    done_signal = pyqtSignal()

    def __init__(self, runner, data):
        super().__init__()
        self.runner = runner
        self.data = data

    def run(self):

        try:
            self.log_signal.emit("🚀 开始执行Minitab...")

            # ✅ 一次运行（核心）
            self.runner.run(self.data)

            self.progress_signal.emit(100)

            self.log_signal.emit("✅ 所有Item处理完成")

        except Exception as e:
            self.log_signal.emit(f"❌ 执行失败: {e}")

        self.done_signal.emit()