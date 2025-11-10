import pywinusb.hid as hid

VID = 0x2759  # 替换为你的设备VID
PID = 0x0003  # 替换为你的设备PID

def list_usb_devices():
    all_devices = hid.HidDeviceFilter(vendor_id=VID, product_id=PID).get_devices()
    for device in all_devices:
        print(f"device_path: {device.device_path}")
        print(f"serial_number: {getattr(device, 'serial_number', None)}")
        print("================================================================================================")

list_usb_devices()
