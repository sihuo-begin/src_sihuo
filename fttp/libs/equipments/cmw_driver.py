from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

# -----------------------------
# Errors
# -----------------------------


class CMWError(Exception):
    """Base error for cmw_driver."""


class TransportError(CMWError):
    pass


class TimeoutError(CMWError):
    pass


class ScpiError(CMWError):
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []

# -----------------------------
# Result Types (no pass/fail)
# -----------------------------


@dataclass
class Trace:
    name: str
    x: List[float]
    y: List[float]
    x_unit: str = ""
    y_unit: str = ""


@dataclass
class MeasurementResult:
    kind: str
    settings: Dict[str, Any]
    metrics: Dict[str, Any]
    raw: Dict[str, str] = field(default_factory=dict)
    traces: List[Trace] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

# -----------------------------
# Transport abstraction
# -----------------------------


class Transport(Protocol):
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def write(self, data: str) -> None: ...
    def query(self, data: str) -> str: ...


class LanTransport:
    """
    CMW typical SCPI socket: TCP 5025.
    """
    def __init__(self, host: str, port: int = 5025, timeout_s: float = 10.0, read_term: bytes = b"\n"):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self.read_term = read_term
        self._sock: Optional[socket.socket] = None

    def connect(self) -> None:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout_s)
            s.connect((self.host, self.port))
            self._sock = s
        except Exception as e:
            raise TransportError(f"LAN connect failed: {e}") from e

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def write(self, data: str) -> None:
        if not self._sock:
            raise TransportError("LAN transport not connected")
        if not data.endswith("\n"):
            data += "\n"
        try:
            self._sock.sendall(data.encode("utf-8"))
        except Exception as e:
            raise TransportError(f"LAN write failed: {e}") from e

    def query(self, data: str) -> str:
        self.write(data)
        return self._readline()

    def _readline(self) -> str:
        if not self._sock:
            raise TransportError("LAN transport not connected")
        chunks: List[bytes] = []
        start = time.time()
        while True:
            if time.time() - start > self.timeout_s:
                raise TimeoutError(f"LAN read timeout after {self.timeout_s}s")
            try:
                b = self._sock.recv(4096)
            except socket.timeout as e:
                raise TimeoutError(f"LAN read timeout after {self.timeout_s}s") from e
            if not b:
                raise TransportError("LAN connection closed by peer")
            chunks.append(b)
            data = b"".join(chunks)
            if self.read_term in data:
                line, _sep, _rest = data.partition(self.read_term)
                return line.decode("utf-8", errors="replace").strip()

# ---- Serial / GPIB skeletons (enable when you install deps) ----


class SerialTransport:
    """
    Requires: pyserial
    """
    def __init__(self, port: str, baudrate: int = 115200, timeout_s: float = 10.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self._ser = None  # type: ignore

    def connect(self) -> None:
        try:
            import serial  # type: ignore
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout_s)
        except Exception as e:
            raise TransportError(f"Serial connect failed: {e}") from e

    def close(self) -> None:
        if self._ser:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def write(self, data: str) -> None:
        if not self._ser:
            raise TransportError("Serial transport not connected")
        if not data.endswith("\n"):
            data += "\n"
        try:
            self._ser.write(data.encode("utf-8"))
        except Exception as e:
            raise TransportError(f"Serial write failed: {e}") from e

    def query(self, data: str) -> str:
        self.write(data)
        try:
            line = self._ser.readline()  # type: ignore
            return line.decode("utf-8", errors="replace").strip()
        except Exception as e:
            raise TransportError(f"Serial read failed: {e}") from e


class GpibTransport:
    """
    Requires: pyvisa
    resource example:
      "GPIB0::20::INSTR" or "TCPIP0::10.0.0.5::inst0::INSTR"
    """
    def __init__(self, resource: str, timeout_ms: int = 10_000):
        self.resource = resource
        self.timeout_ms = timeout_ms
        self._inst = None  # type: ignore

    def connect(self) -> None:
        try:
            import pyvisa  # type: ignore
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(self.resource)
            inst.timeout = self.timeout_ms
            self._inst = inst
        except Exception as e:
            raise TransportError(f"VISA connect failed: {e}") from e

    def close(self) -> None:
        if self._inst:
            try:
                self._inst.close()
            finally:
                self._inst = None

    def write(self, data: str) -> None:
        if not self._inst:
            raise TransportError("VISA transport not connected")
        try:
            self._inst.write(data)
        except Exception as e:
            raise TransportError(f"VISA write failed: {e}") from e

    def query(self, data: str) -> str:
        if not self._inst:
            raise TransportError("VISA transport not connected")
        try:
            return str(self._inst.query(data)).strip()
        except Exception as e:
            raise TransportError(f"VISA query failed: {e}") from e

# -----------------------------
# SCPI Session (robustness)
# -----------------------------


class ScpiSession:
    def __init__(
        self,
        transport: Transport,
        *,
        check_errors: bool = True,
        opc_timeout_s: float = 30.0,
        logger: Optional[Any] = None,
    ):
        self.t = transport
        self.check_errors = check_errors
        self.opc_timeout_s = opc_timeout_s
        self.logger = logger

    def connect(self) -> None:
        self.t.connect()

    def close(self) -> None:
        self.t.close()

    def write(self, cmd: str) -> None:
        self._log("->", cmd)
        self.t.write(cmd)

    def query(self, cmd: str) -> str:
        self._log("->", cmd)
        resp = self.t.query(cmd)
        self._log("<-", resp)
        return resp

    def idn(self) -> str:
        return self.query("*IDN?")

    def rst(self) -> None:
        self.write("*RST")
        self.wait_opc()
        if self.check_errors:
            self.raise_if_error()

    def cls(self) -> None:
        self.write("*CLS")

    def wait_opc(self) -> None:
        """
        Wait for Operation Complete using *OPC?.
        """
        start = time.time()
        while True:
            if time.time() - start > self.opc_timeout_s:
                raise TimeoutError(f"OPC timeout after {self.opc_timeout_s}s")
            try:
                r = self.query("*OPC?")
                if r.strip() == "1":
                    return
            except TimeoutError:
                raise
            except Exception:
                # allow transient errors to surface via error queue after timeout
                time.sleep(0.1)

    def raise_if_error(self) -> None:
        """
        Drain error queue. If any non-zero error, raise ScpiError.
        """
        errors: List[str] = []
        for _ in range(50):  # avoid infinite loop
            e = self.query("SYST:ERR?")
            # Typical format: 0,"No error"
            if e.startswith("0") or "No error" in e:
                break
            errors.append(e)
        if errors:
            raise ScpiError("SCPI error(s) occurred", errors=errors)

    def _log(self, direction: str, msg: str) -> None:
        if self.logger:
            try:
                self.logger(f"{direction} {msg}")
            except Exception:
                pass

# -----------------------------
# BLE / Wi-Fi domain APIs (SCPI filled from Rohde-Schwarz example)
# -----------------------------


class BLETx:
    def __init__(self, s: ScpiSession):
        self.s = s

    def measure_power_freq_error(self, *, channel: int, phy: str = "LE1M", power_dbm: Optional[float] = None) -> MeasurementResult:
        """
        BLE TX measurement: power, freq error, modulation quality (from Rohde-Schwarz example).
        Assumes LE PHY and advertiser packet; adjust for your needs.
        """
        settings = {"channel": channel, "phy": phy, "power_dbm": power_dbm}
        raw: Dict[str, str] = {}

        # Reset and configure (based on RsCmwBt example)
        self.s.rst()  # *RST

        # Routing: assume RF1/RX1 (adjust to your setup, e.g., R11,RX11)
        self.s.write("ROUT:BLU:MEAS:SCEN:SAL R1,RX1")  # ROUTe:BLUetooth:MEAS:SCENario:SALone

        # Input signal: auto detect, burst type LE, PHY LE1M, packet type ADV
        self.s.write("CONF:BLU:MEAS:ISIG:DMO AUTO")  # CONFigure:BLUetooth:MEAS:ISIGnal:DMODe AUTO
        self.s.write("CONF:BLU:MEAS:ISIG:BTY LE")  # CONFigure:BLUetooth:MEAS:ISIGnal:BTYPe LE
        self.s.write(f"CONF:BLU:MEAS:ISIG:LEN:PHY {phy}")  # CONFigure:BLUetooth:MEAS:ISIGnal:LENergy:PHY LE1M
        self.s.write("CONF:BLU:MEAS:ISIG:PTY:LEN:LE1M ADV")  # CONFigure:BLUetooth:MEAS:ISIGnal:PTYPe:LENergy:LE1M ADV

        # RF settings: frequency from channel (BLE channel 0=2402MHz, etc.)
        freq_mhz = 2402 + channel * 2  # BLE channel formula
        self.s.write(f"CONF:BLU:MEAS:RFSET:FREQ {freq_mhz}")  # CONFigure:BLUetooth:MEAS:RFSettings:FREQuency

        # RX quality: advertiser index (example 37)
        self.s.write("CONF:BLU:MEAS:RXQ:AIND 37")  # CONFigure:BLUetooth:MEAS:RXQuality:AINDex 37
        self.s.write("CONF:BLU:MEAS:RXQ:STOP NONE")  # CONFigure:BLUetooth:MEAS:RXQuality:STOPCondition NONE
        self.s.write("CONF:BLU:MEAS:RXQ:MEXC OFF")  # CONFigure:BLUetooth:MEAS:RXQuality:MEXCeption OFF

        # Measurement evaluation: enable modulation/PvT views, stat count 1
        self.s.write("CONF:BLU:MEAS:MEV:PVT:VIEW PVT")  # CONFigure:BLUetooth:MEAS:MEValuation:PVTime:VIEW PVTime
        self.s.write("CONF:BLU:MEAS:MEV:MOD:VIEW MOD")  # CONFigure:BLUetooth:MEAS:MEValuation:MODulation:VIEW MODulation
        self.s.write("CONF:BLU:MEAS:MEV:MOD:SCON 1")  # CONFigure:BLUetooth:MEAS:MEValuation:MODulation:SCONt 1
        self.s.write("CONF:BLU:MEAS:MEV:PVT:SCON 1")  # CONFigure:BLUetooth:MEAS:MEValuation:PVTime:SCONt 1

        # Instrument address (example)
        self.s.write('CONF:BLU:MEAS:MEV:IADD "123456789AB"')  # CONFigure:BLUetooth:MEAS:MEValuation:IADDress
        self.s.write("CONF:BLU:MEAS:MEV:IATY PUB")  # CONFigure:BLUetooth:MEAS:MEValuation:IATYpe PUBlic

        # ARB generation ON (for TX)
        self.s.write("SOUR:BLU:MEAS:ARB:GEN ON")  # SOURce:BLUetooth:MEAS:ARB:GENeration ON

        # Initiate TX measurement
        self.s.write("INIT:BLU:MEAS:TX:MEAS")  # INITiate:BLUetooth:MEAS:TX:MEASurement
        self.s.wait_opc()  # Wait for completion

        # Fetch results (example: assumes fetch returns comma-separated values)
        raw["tx_result"] = self.s.query("FETC:BLU:MEAS:TX?")  # FETCh:BLUetooth:MEAS:TX?

        self.s.raise_if_error()

        # Parse raw to metrics (adjust based on actual response format, e.g., "power,freq_error,...")
        parts = raw["tx_result"].split(",")
        metrics = {}
        if len(parts) > 0:
            metrics["power_dbm"] = float(parts[0]) if parts[0] else None
        if len(parts) > 1:
            metrics["freq_error_hz"] = float(parts[1]) if parts[1] else None
        # Add more based on full fetch response (modulation error, etc.)

        return MeasurementResult(kind="ble_tx_power_freq_error", settings=settings, metrics=metrics, raw=raw)


class BLERx:
    def __init__(self, s: ScpiSession):
        self.s = s

    def measure_per(self, *, channel: int, phy: str, rx_power_dbm: float, packets: int = 1000) -> MeasurementResult:
        settings = {"channel": channel, "phy": phy, "rx_power_dbm": rx_power_dbm, "packets": packets}
        raw: Dict[str, str] = {}

        # Similar config to TX, but for RX (adjust as needed)
        self.s.rst()
        self.s.write("ROUT:BLU:MEAS:SCEN:SAL R1,RX1")
        self.s.write("CONF:BLU:MEAS:ISIG:DMO AUTO")
        self.s.write("CONF:BLU:MEAS:ISIG:BTY LE")
        self.s.write(f"CONF:BLU:MEAS:ISIG:LEN:PHY {phy}")
        freq_mhz = 2402 + channel * 2
        self.s.write(f"CONF:BLU:MEAS:RFSET:FREQ {freq_mhz}")
        self.s.write("CONF:BLU:MEAS:RXQ:AIND 37")
        self.s.write("CONF:BLU:MEAS:RXQ:STOP NONE")
        self.s.write("CONF:BLU:MEAS:RXQ:MEXC OFF")
        self.s.write("CONF:BLU:MEAS:MEV:MOD:VIEW MOD")
        self.s.write("CONF:BLU:MEAS:MEV:MOD:SCON 1")
        self.s.write('CONF:BLU:MEAS:MEV:IADD "123456789AB"')
        self.s.write("CONF:BLU:MEAS:MEV:IATY PUB")

        # Set RX power (if CMW supports, may need SOUR:POW)
        self.s.write(f"SOUR:BLU:MEAS:POW {rx_power_dbm}")  # Adjust command if needed

        # Initiate RX measurement
        self.s.write("INIT:BLU:MEAS:RX:MEAS")  # INITiate:BLUetooth:MEAS:RX:MEASurement
        self.s.wait_opc()

        # Fetch PER (assume FETC returns PER as first value)
        raw["rx_result"] = self.s.query("FETC:BLU:MEAS:RX?")  # FETCh:BLUetooth:MEAS:RX?

        self.s.raise_if_error()

        parts = raw["rx_result"].split(",")
        metrics = {"per": float(parts[0]) if parts else None}

        return MeasurementResult(kind="ble_rx_per", settings=settings, metrics=metrics, raw=raw)

    def sensitivity_search(
        self,
        *,
        channel: int,
        phy: str,
        per_target: float = 0.1,
        start_power_dbm: float = -60.0,
        stop_power_dbm: float = -100.0,
        step_db: float = 1.0,
        packets: int = 1000,
    ) -> MeasurementResult:
        steps: List[Dict[str, Any]] = []
        p = start_power_dbm
        final_est: Optional[float] = None

        while p >= stop_power_dbm:
            r = self.measure_per(channel=channel, phy=phy, rx_power_dbm=p, packets=packets)
            per = r.metrics.get("per", None)
            steps.append({"power_dbm": p, "per": per, "raw": r.raw})
            if per is not None and per > per_target:
                final_est = p + step_db
                break
            p -= step_db

        return MeasurementResult(
            kind="ble_rx_sensitivity_search",
            settings={
                "channel": channel, "phy": phy, "per_target": per_target,
                "start_power_dbm": start_power_dbm, "stop_power_dbm": stop_power_dbm,
                "step_db": step_db, "packets": packets
            },
            metrics={"final_sensitivity_dbm_est": final_est, "steps": steps},
        )


class BLE:
    def __init__(self, s: ScpiSession):
        self.tx = BLETx(s)
        self.rx = BLERx(s)


class WifiTx:
    def __init__(self, s: ScpiSession):
        self.s = s

    def measure(
        self,
        *,
        standard: str,
        band: str,
        channel: int,
        bandwidth_mhz: int,
        mcs: int,
        power_dbm: Optional[float] = None,
        antenna: str = "RF1",
        averaging: int = 10,
        want_mask: bool = True,
        want_evm: bool = True,
    ) -> MeasurementResult:
        settings = {
            "standard": standard, "band": band, "channel": channel, "bandwidth_mhz": bandwidth_mhz,
            "mcs": mcs, "power_dbm": power_dbm, "antenna": antenna, "averaging": averaging,
            "want_mask": want_mask, "want_evm": want_evm,
        }
        raw: Dict[str, str] = {}

        # TODO: Fill WLAN SCPI from Rohde-Schwarz WLAN example (similar structure: CONF:WLAN, ROUT, INIT, FETC)
        # Example skeleton (replace with real commands):
        self.s.rst()
        self.s.write(f"CONF:WLAN:MEAS:STAN {standard}")  # Standard e.g., N, AC
        # ... add routing, channel, bw, mcs, power, etc.
        self.s.write("INIT:WLAN:MEAS:TX:MEAS")
        self.s.wait_opc()
        raw["power"] = self.s.query("FETC:WLAN:MEAS:TX:POW?")
        raw["evm"] = self.s.query("FETC:WLAN:MEAS:TX:EVM?")
        raw["mask"] = self.s.query("FETC:WLAN:MEAS:TX:MASK?")
        self.s.raise_if_error()

        metrics = {}  # Parse raw
        return MeasurementResult(kind="wifi_tx_measure", settings=settings, metrics=metrics, raw=raw)


class WifiRx:
    def __init__(self, s: ScpiSession):
        self.s = s

    def measure_per(
        self,
        *,
        standard: str,
        band: str,
        channel: int,
        bandwidth_mhz: int,
        mcs: int,
        rx_power_dbm: float,
        packets: int = 1000,
    ) -> MeasurementResult:
        settings = {
            "standard": standard, "band": band, "channel": channel, "bandwidth_mhz": bandwidth_mhz,
            "mcs": mcs, "rx_power_dbm": rx_power_dbm, "packets": packets,
        }
        raw: Dict[str, str] = {}

        # TODO: Fill WLAN RX SCPI (similar to BLE)
        self.s.rst()
        # ... config
        self.s.write("INIT:WLAN:MEAS:RX:MEAS")
        self.s.wait_opc()
        raw["per"] = self.s.query("FETC:WLAN:MEAS:RX:PER?")
        self.s.raise_if_error()

        metrics = {"per": float(raw["per"]) if raw["per"] else None}
        return MeasurementResult(kind="wifi_rx_per", settings=settings, metrics=metrics, raw=raw)

    def sensitivity_search(
        self,
        *,
        standard: str,
        band: str,
        channel: int,
        bandwidth_mhz: int,
        mcs: int,
        per_target: float = 0.1,
        start_power_dbm: float = -40.0,
        stop_power_dbm: float = -100.0,
        step_db: float = 1.0,
        packets: int = 1000,
    ) -> MeasurementResult:
        steps: List[Dict[str, Any]] = []
        p = start_power_dbm
        final_est: Optional[float] = None

        while p >= stop_power_dbm:
            r = self.measure_per(
                standard=standard, band=band, channel=channel, bandwidth_mhz=bandwidth_mhz,
                mcs=mcs, rx_power_dbm=p, packets=packets
            )
            per = r.metrics.get("per", None)
            steps.append({"power_dbm": p, "per": per, "raw": r.raw})
            if per is not None and per > per_target:
                final_est = p + step_db
                break
            p -= step_db

        return MeasurementResult(
            kind="wifi_rx_sensitivity_search",
            settings={
                "standard": standard, "band": band, "channel": channel, "bandwidth_mhz": bandwidth_mhz,
                "mcs": mcs, "per_target": per_target,
                "start_power_dbm": start_power_dbm, "stop_power_dbm": stop_power_dbm,
                "step_db": step_db, "packets": packets
            },
            metrics={"final_sensitivity_dbm_est": final_est, "steps": steps},
        )

class Wifi:
    def __init__(self, s: ScpiSession):
        self.tx = WifiTx(s)
        self.rx = WifiRx(s)

# -----------------------------
# Main Driver
# -----------------------------

class CMWDriver:
    def __init__(self, transport: Transport, *, check_errors: bool = True, logger: Optional[Any] = None):
        self.session = ScpiSession(transport, check_errors=check_errors, logger=logger)
        self.ble = BLE(self.session)
        self.wifi = Wifi(self.session)

    def connect(self) -> None:
        self.session.connect()

    def close(self) -> None:
        self.session.close()

    def idn(self) -> str:
        return self.session.idn()

    def reset(self) -> None:
        self.session.rst()

    def clear(self) -> None:
        self.session.cls()