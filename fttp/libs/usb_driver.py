import threading
import time

import pywinusb.hid as hid
from src.libs.cmd_generator import NetworkFrameBuilder


class HIDCommandModule:
    def __init__(self, vendor_id, product_id, path=None, timeout=1.0, idle_time=0.1):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.report_size = 64
        self.device = None
        self.running = False
        self.last_error = None
        self._response = None
        self._event = threading.Event()
        self.timeout = timeout
        self.target_path = path
        self.idle_time = idle_time

    def connect(self):
        try:
            devices = hid.HidDeviceFilter(vendor_id=self.vendor_id, product_id=self.product_id).get_devices()
            if not devices:
                raise IOError(f"No HID device found with VID: {hex(self.vendor_id)}, PID: {hex(self.product_id)}")
            if self.target_path:
                for dev in devices:
                    print(f"device_path: {dev.device_path}")
                    print(f"serial_number: {getattr(dev, 'serial_number', None)}")
                    print("------")
                for dev in devices:
                    # if dev.device_path == self.target_path:
                    if self.target_path in dev.device_path:
                        self.device = dev
                        break
                if not self.device:
                    raise IOError(
                        f"No HID device found with VID: {hex(self.vendor_id)}, PID: {hex(self.product_id)}, path: {self.target_path}"
                    )
            else:
                self.device = devices[0]
            self.device.open()
            self.device.set_raw_data_handler(self._read_handler)
            self.running = True
            self.listener_thread = threading.Thread(target=self._connection_monitor, daemon=True)
            self.listener_thread.start()
            # 自动获取report长度
            out_reports = self.device.find_output_reports()
            if out_reports:
                self.report_size = len(out_reports[0].get_raw_data())
                print(f"Output report size: {self.report_size}")
                for item in out_reports:
                    if item.report_id == 0x3F:
                        print(f"right report id {hex(item.report_id)}")
            else:
                print(f"Warning: No output report found, fallback to default size: {self.report_size}")
            print("Device connected.")
        except Exception as e:
            self.last_error = str(e)
            print(f"Connection failed: {e}")

    def is_connected(self):
        """
        判断当前HID设备是否已连接并打开。
        """
        return self.device is not None and getattr(self.device, "is_plugged", lambda: False)() and self.running

    def disconnect(self):
        self.running = False
        if self.device:
            try:
                self.device.close()
                print("Device disconnected.")
            except Exception as e:
                print(f"Error on disconnect: {e}")
        self.device = None

    def send_and_receive(self, data, idle_factor=1):
        """
        data: list of ints，首字节为report_id（如3f），不自动添加
        返回：input report原始数据list，或None（超时）
        """
        if not self.device:
            print("Device not connected.")
            return None
        self._event.clear()
        self._response = None
        try:
            out_reports = self.device.find_output_reports()
            if not out_reports:
                print("No output report found on device.")
                return None
            out_report = out_reports[0]
            for item in out_reports:
                if item.report_id == 0x3F:
                    out_report = item
                    break
            report_size = len(out_report.get_raw_data())
            buffer = list(data)
            if len(buffer) < report_size:
                buffer += [0x00] * (report_size - len(buffer))
            elif len(buffer) > report_size:
                buffer = buffer[:report_size]
            out_report.set_raw_data(buffer)
            out_report.send()
            print("Sent:    ", [f"0x{x:02X}" for x in buffer])
            time.sleep(self.idle_time * idle_factor)
            if self._event.wait(self.timeout):
                return self._response
            else:
                print("Timeout waiting for device response.")
                return None
        except Exception as e:
            self.last_error = str(e)
            print(f"Send failed: {e}")
            return None

    def _connection_monitor(self):
        try:
            while self.running:
                if not self.device or not self.device.is_plugged():
                    print("Device disconnected!")
                    self.disconnect()
                    break
                time.sleep(1)
        except Exception as e:
            self.last_error = str(e)
            print(f"Monitor error: {e}")

    def _read_handler(self, data):
        print("Received:", [f"0x{x:02X}" for x in data])
        self._response = data
        self._event.set()

    def get_last_error(self):
        return self.last_error


# if __name__ == "__main__":
#     VID = 0x2759  # 替换为你的设备VID
#     PID = 0x0003  # 替换为你的设备PID
#     module = HIDCommandModule(VID, PID, timeout=3.0)
#     module.connect()
#
#     try:
#         while module.running:
#             builder = NetworkFrameBuilder()
#             # hid_frame = builder.build_read_request_frame(
#             #             mode='hid',
#             #             read_only=True,
#             #             reply_hop_count=0,
#             #             hop_count=0,
#             #             parameter=0x08,
#             #             # stats_utype=0x00
#             #             pnum=260,
#             #             count=3,
#             #             values=[0x0000, 0x0000, 0x0000]
#             #         )
#             # hid_frame = builder.build_write_request_frame(
#             #     mode='hid',
#             #     reply_hop_count=0,
#             #     hop_count=0,
#             #     parameter=0x8c,
#             #     # pnum=263,
#             #     # count=2,
#             #     type=0x01,
#             #     channel=0x00,
#             #     tx_power=0x0a,
#             #     tx_payload_type=0x04,
#             #     tx_payload_length=0x05,
#             #     secret_key=0xC001BABE
#             # )
#
#             # hid_frame = builder.build_read_request_frame(
#             #     mode='hid',
#             #     read_only=True,
#             #     reply_hop_count=0,
#             #     hop_count=0,
#             #     parameter=0x08,
#             #     pnum=19,
#             #     count=1
#             # )
#             #
#             # hid_frame = builder.build_write_request_frame(
#             #     mode='hid',
#             #     reply_hop_count=0,
#             #     hop_count=0,
#             #     parameter=0x08,
#             #     pnum=14,
#             #     count=2,
#             #     value=0x00d1
#             # )
#
#             # hid_frame = builder.build_write_request_frame(
#             #     mode='hid',
#             #     reply_hop_count=0,
#             #     hop_count=0,
#             #     parameter=0x08,
#             #     pnum=14,
#             #     count=1,
#             #     value=0x00be
#             # )
#
#             # cmd = input("请输入命令(如 3f 08 c0 44 02 0e 10 a3 00 57)：")
#             cmd = hid_frame.hex()
#             print("cmd hex", cmd)
#             # if cmd.lower() in ("exit", "quit"):
#             #     break
#             try:
#                 # 支持输入"3f08c044..."或"3f 08 c0..."格式
#                 # cmd_str = cmd.strip().replace(" ", "")
#                 # if len(cmd_str) % 2 != 0:
#                 #     raise ValueError("Hex string长度应为偶数")
#                 # data = [int(cmd_str[i:i + 2], 16) for i in range(0, len(cmd_str), 2)]
#                 # print("Hex number:", data)
#                 response = module.send_and_receive(hid_frame)
#                 if response:
#                     print("设备返回：", " ".join([f"{x:02x}" for x in response]))
#                     break
#                 else:
#                     print("无响应或超时。")
#             except Exception as e:
#                 print(f"命令格式错误：{e}")
#     finally:
#         module.disconnect()
