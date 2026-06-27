import nidaqmx
from nidaqmx.errors import DaqError
import nidaqmx.system
import threading


class NIEquipmentError(Exception):
    """自定义异常，统一DAQ模块的错误处理。"""

    pass


class TimeoutError(NIEquipmentError):
    """自定义超时异常。"""

    pass


class NIEquipment:
    def __init__(self, device_name, default_timeout=5.0):
        """
        :param device_name: 设备名，如 'Dev1'
        :param default_timeout: 默认超时（秒）
        """
        self.device_name = device_name
        self.default_timeout = default_timeout
        self._detect_capabilities()

    def _detect_capabilities(self):
        """检测设备支持的功能（模拟输入/输出、数字输入/输出）"""
        sys = nidaqmx.system.System.local()
        dev = None
        for device in sys.devices:
            if device.name == self.device_name:
                dev = device
                break
        if dev is None:
            raise NIEquipmentError(f"设备 {self.device_name} 未找到，请用 NI MAX 检查设备连接。")
        self.ais_supported = len(dev.ai_physical_chans) > 0
        self.aos_supported = len(dev.ao_physical_chans) > 0
        self.dios_supported = len(dev.di_lines) > 0 or len(dev.do_lines) > 0

    def read_analog(self, channel="ai0", samples=1, timeout=None):
        """模拟输入读取。"""
        if not self.ais_supported:
            raise NIEquipmentError(f"设备 {self.device_name} 不支持模拟输入。")
        timeout = timeout or self.default_timeout
        data = None
        try:

            def _read():
                nonlocal data
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan(f"{self.device_name}/{channel}")
                    data = task.read(number_of_samples_per_channel=samples, timeout=timeout)

            self._run_with_timeout(_read, timeout)
        except DaqError as e:
            raise NIEquipmentError(f"模拟输入出错: {e}")
        except TimeoutError:
            raise
        return data

    def write_analog(self, channel="ao0", voltage=0.0, timeout=None):
        """模拟输出写入。"""
        if not self.aos_supported:
            raise NIEquipmentError(f"设备 {self.device_name} 不支持模拟输出。")
        timeout = timeout or self.default_timeout
        try:

            def _write():
                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(f"{self.device_name}/{channel}")
                    task.write(voltage, timeout=timeout)

            self._run_with_timeout(_write, timeout)
        except DaqError as e:
            raise NIEquipmentError(f"outwrong: {e}")
        except TimeoutError:
            raise

    def read_digital(self, channel="port0/line0", timeout=None):
        """数字输入读取。"""
        if not self.dios_supported:
            raise NIEquipmentError(f"设备 {self.device_name} 不支持数字IO。")
        timeout = timeout or self.default_timeout
        value = None
        try:

            def _read():
                nonlocal value
                with nidaqmx.Task() as task:
                    task.di_channels.add_di_chan(f"{self.device_name}/{channel}")
                    value = task.read(timeout=timeout)

            self._run_with_timeout(_read, timeout)
        except DaqError as e:
            raise NIEquipmentError(f"数字输入出错: {e}")
        except TimeoutError:
            raise
        return value

    def write_digital(self, channel="port0/line0", value=True, timeout=None):
        """数字输出写入。"""
        if not self.dios_supported:
            raise NIEquipmentError(f"设备 {self.device_name} 不支持数字IO。")
        timeout = timeout or self.default_timeout
        try:

            def _write():
                with nidaqmx.Task() as task:
                    task.do_channels.add_do_chan(f"{self.device_name}/{channel}")
                    task.write(value, timeout=timeout)

            self._run_with_timeout(_write, timeout)
        except DaqError as e:
            raise NIEquipmentError(f"数字输出出错: {e}")
        except TimeoutError:
            raise

    def _run_with_timeout(self, func, timeout):
        """用线程实现操作超时控制。"""
        exc = []
        thread = threading.Thread(target=lambda: self._try_run(func, exc))
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            raise TimeoutError("操作超时")
        if exc:
            raise exc[0]

    def _try_run(self, func, exc):
        try:
            func()
        except Exception as e:
            exc.append(e)

    def fixture_detect_start(self, station):
        status = self.read_digital()
        if status:
            return True
        else:
            return False
