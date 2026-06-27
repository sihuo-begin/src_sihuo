from dataclasses import dataclass


@dataclass
class DeviceInfo:
    product_code_bytes: bytes

    @property
    def product_code_int(self):
        return int.from_bytes(self.product_code_bytes, "little")

    @property
    def product_code_hex(self):
        return self.product_code_bytes.hex()
