from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Type,  Union, List
import serial
import time
from src.libs.connection import UARTConnection


class ScannerError(Exception):
    pass
class ScannerTimeoutError(Exception):
    pass

class ScannerBase(ABC):
    """统一接口：上层只依赖这个。"""
    @abstractmethod
    def scan(self,uart:UARTConnection,cmds: list, delay: int = 0.2) -> str:
        pass


@dataclass(frozen=True)
class CommandSpec:
    keyence_cmd: list = ["LON\n","LOFF\n"],
    zebra_cmd: list = [0x04, 0xE4, 0x04, 0x80, 0xFE, 0x94],


class CommandMappedScanner(ScannerBase):
    def scan(self,uart:UARTConnection,cmds: list, delay: float = 1.5) -> str:
        data = None
        for cmd in cmds:
            uart.send(cmd)
            time.sleep(delay)
            data =uart.recv(cmd, timeout=delay)
        return data

class ScannerDriver:
    def __init__(self, connection, logger, scanner_type = "zebra"):
        self.logger = logger
        self.connection = connection
        self.logger.info(scanner_type)
        self.scanner_type = scanner_type


    def trigger_scan(self):
        cmds = None
        barcode = None
        if self.scanner_type == "keyence":
            cmds = [x for x in CommandSpec.keyence_cmd[0]]
        elif self.scanner_type == "zebra":
            cmds = [CommandSpec.zebra_cmd[0]]
        scanner = CommandMappedScanner()
        # self.logger.info("scanner", scanner)
        barcode = ""
        if cmds is not None:
            for _ in range(10):
                barcodes = scanner.scan(uart=self.connection, cmds=cmds, delay=0.2)
                self.logger.info(f"barcode: {barcodes}")
                splitCmd = b'\x04\xd0\x00\x00\xff,'
                if len(barcodes) > 6:
                    try:
                        if splitCmd in barcodes:
                            if barcodes.startswith(splitCmd):
                                barcodes = barcodes.split(splitCmd)[-1]
                            if len(barcodes) > 5:
                                if splitCmd in barcodes:
                                    barcode = barcodes.split(splitCmd)[0].decode("utf-8")
                                    break
                                else:
                                    barcode = barcodes.decode("utf-8")
                                    if len(barcode) == 17:
                                        break

                    except Exception as e:
                        self.logger.error(f"barcode error: {e}")
                time.sleep(1)

            # self.logger.info("barcode", barcode.encode())
        return barcode

# if __name__ == '__main__':
#     uart_scanner = UartScan("COM3")
#     cmds = []
#     scanner_type = "keyence"
#     scanner_type = "zebra"
#     scanner = CommandMappedScanner()
#     if scanner_type == "keyence":
#         cmds = [CommandSpec.keyence_cmd_on[0], CommandSpec.keyence_cmd_off[0]]
#     elif scanner_type == "zebra":
#         cmds = [CommandSpec.zebra_cmd[0]]
#     barcode = scanner.scan(uart=uart_scanner, cmds = cmds, delay = 0.2)
#     # print(barcode)

