from __future__ import annotations
import time

from src.libs.models import StepResult
from src.libs.chip.rtl8722f.state_store import get_or_create_state
from src.libs.chip.rtl8722f.dut_interface import RTL8722FDutInterface
from src.libs.chip.rtl8722f.bt_sdk import (
    RealtekBtSdk,
    RealtekBtSdkError,
    BT_PARAMETER,
    LE5_TX_1M_PHY,
    LE5_TX_2M_PHY,
    LE5_TX_CODED_PHY_S8,
    LE5_TX_CODED_PHY_S2,
    LE5_RX_1M_PHY,
    LE5_RX_2M_PHY,
    LE5_RX_CODED_PHY,
    BT_PKT_LE,
    BT_PKT_LE_2M,
    BT_PKT_LE_CODED_S8,
    BT_PKT_LE_CODED_S2,
    BT_LE_PAYLOAD_TYPE_PRBS9,
    BT_LE_PAYLOAD_TYPE_1111_0000,
    BT_LE_PAYLOAD_TYPE_1010,
    LE_TX_DUT_TEST_CMD,
    LE_RX_DUT_TEST_CMD,
    LE_DUT_TEST_END_CMD,
    TX_POWER_GAIN_K,
    TX_POWER_FLATNESS,
    REPORT_ALL,
    REPORT_LE_RX,
    STANDARD_MODULATION_INDEX,
    STABLE_MODULATION_INDEX,
)
from src.libs.equipments.wt328ce.driver import WT328CEDriver
from src.libs.calibration.pathloss import PathlossTable
from src.libs.calibration.rate_normalizer import normalize_bt_phy


def _map_phy_name_to_sdk_tx(phy_name: str) -> int:
    name = str(phy_name).upper()
    if name in ("BLE1M", "1M"):
        return LE5_TX_1M_PHY
    if name in ("BLE2M", "2M"):
        return LE5_TX_2M_PHY
    if name in ("BLE125K", "CODED_S8", "S8", "125K"):
        return LE5_TX_CODED_PHY_S8
    if name in ("BLE500K", "CODED_S2", "S2", "500K"):
        return LE5_TX_CODED_PHY_S2
    return LE5_TX_1M_PHY


def _map_phy_name_to_sdk_rx(phy_name: str) -> int:
    name = str(phy_name).upper()
    if name in ("BLE1M", "1M"):
        return LE5_RX_1M_PHY
    if name in ("BLE2M", "2M"):
        return LE5_RX_2M_PHY
    if name in ("BLE125K", "BLE500K", "CODED", "CODED_S8", "CODED_S2", "S8", "S2", "125K", "500K"):
        return LE5_RX_CODED_PHY
    return LE5_RX_1M_PHY


def _map_phy_name_to_packet_type(phy_name: str) -> int:
    name = str(phy_name).upper()
    if name in ("BLE1M", "1M"):
        return BT_PKT_LE
    if name in ("BLE2M", "2M"):
        return BT_PKT_LE_2M
    if name in ("BLE125K", "CODED_S8", "S8", "125K"):
        return BT_PKT_LE_CODED_S8
    if name in ("BLE500K", "CODED_S2", "S2", "500K"):
        return BT_PKT_LE_CODED_S2
    return BT_PKT_LE


def _map_payload_to_le_payload(payload: str) -> int:
    name = str(payload).upper()
    if name == "PRBS9":
        return BT_LE_PAYLOAD_TYPE_PRBS9
    if name in ("11110000", "0F"):
        return BT_LE_PAYLOAD_TYPE_1111_0000
    if name in ("10101010", "55"):
        return BT_LE_PAYLOAD_TYPE_1010
    return BT_LE_PAYLOAD_TYPE_PRBS9


def _modulation_index(stable_modulation: bool) -> int:
    return STABLE_MODULATION_INDEX if stable_modulation else STANDARD_MODULATION_INDEX


class BtProdController:
    """
    BT production controller aligned with RtlBluetoothMP.h and current bt_sdk.py.

    Current implementation model:
    - sdk.init(): BuildInterfaceRTK + BuildBluetoothModule
    - sdk.le_tx_test_start(): UpDataParameter + ActionControlExcute for LE TX
    - sdk.le_rx_test_start(): UpDataParameter + ActionControlExcute for LE RX
    - sdk.le_test_end(): LE_DUT_TEST_END_CMD
    - sdk.action_report(): ActionReport
    """

    def __init__(self, connections, ip: str, logger):
        self.connections = connections
        self.logger = logger
        self.dut = RTL8722FDutInterface(connections, logger)
        self.sdk = RealtekBtSdk(logger)
        self.wt = WT328CEDriver(logger)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _get_bt_port_info(self, port_no=None, baudrate=None):
        if port_no is None:
            if hasattr(self.connections, "bt_port_no"):
                port_no = self.connections.bt_port_no
            elif hasattr(self.connections, "port_no"):
                port_no = self.connections.port_no
            else:
                port_no = 0

        if baudrate is None:
            if hasattr(self.connections, "bt_baudrate"):
                baudrate = self.connections.bt_baudrate
            elif hasattr(self.connections, "baudrate"):
                baudrate = self.connections.baudrate
            else:
                baudrate = 115200

        return int(port_no), int(baudrate)

    def _ensure_bt_ready(self):
        state = get_or_create_state()
        if not state.bt.entered_bt_mode or not state.bt.initialized:
            raise RuntimeError("BT mode not entered")

    def _get_bt_pathloss(self, rf_port: int, phy_name: str, freq_mhz: int) -> float:
        state = get_or_create_state()

        table = getattr(state.runtime, "pathloss_table", None)
        yaml_path = getattr(state.runtime, "pathloss_yaml", None)

        if table is None and yaml_path:
            self.logger.info("[PATHLOSS] lazy load from yaml_path=%s", yaml_path)
            table = PathlossTable.load_or_empty(yaml_path)
            state.runtime.pathloss_table = table

        if table is None:
            self.logger.warning(
                "[PATHLOSS] no BT table loaded, use 0.0; rf_port=%s phy=%s freq=%s",
                rf_port, phy_name, freq_mhz
            )
            return 0.0

        mod_key = normalize_bt_phy(phy_name)
        loss = float(table.get_loss("bt", rf_port, mod_key, freq_mhz, default=0.0))
        self.logger.info(
            "[PATHLOSS] bt rf_port=%s phy=%s mod_key=%s freq=%s loss=%.2f",
            rf_port, phy_name, mod_key, freq_mhz, loss
        )
        return loss

    def _build_param(
        self,
        parameter_index: int,
        channel: int | None = None,
        phy_name: str | None = None,
        payload: str | None = None,
        stable_modulation: bool = True,
        tx_gain_index: int | None = None,
        tx_gain_value: int | None = None,
        hopping_fix_channel: int = 1,
    ) -> BT_PARAMETER:
        p = BT_PARAMETER()
        p.ParameterIndex = int(parameter_index)

        if channel is not None:
            p.mChannelNumber = int(channel)

        if phy_name is not None:
            if parameter_index == LE_RX_DUT_TEST_CMD:
                p.PHY = int(_map_phy_name_to_sdk_rx(phy_name))
            else:
                p.PHY = int(_map_phy_name_to_sdk_tx(phy_name))
            p.mPacketType = int(_map_phy_name_to_packet_type(phy_name))

        if payload is not None:
            p.mPayloadType = int(_map_payload_to_le_payload(payload))

        p.ModulationIndex = int(_modulation_index(stable_modulation))
        p.bHoppingFixChannel = int(hopping_fix_channel)

        if tx_gain_index is not None:
            p.mTxGainIndex = int(tx_gain_index) & 0xFF
        if tx_gain_value is not None:
            p.mTxGainValue = int(tx_gain_value) & 0xFF

        return p

    def _read_common_report_fields(self, report) -> dict:
        return {
            "rx_rssi": int(report.RxRssi),
            "ber": float(report.ber),
            "cfo": float(report.Cfo),
            "thermal": int(report.CurrThermalValue),
            "total_rx_bits": int(report.TotalRXBits),
            "total_rx_counts": int(report.TotalRxCounts),
            "total_rx_error_bits": int(report.TotalRxErrorBits),
            "rx_recv_pkt_cnts": int(report.RXRecvPktCnts),
        }

    def _bt_rx_verify_profile(self, phy_name: str) -> tuple[int, str]:
        phy_norm = str(phy_name).strip().upper()

        if phy_norm in ("BLE1M", "1M"):
            return 9, "BLE.bwv"

        if phy_norm in ("BLE2M", "2M"):
            return 9, "BLE2M.bwv"

        raise ValueError(f"no tester waveform available for bt rx verify phy: {phy_name}")

    def _estimate_bt_rx_tx_time(
            self,
            packet_count: int,
            phy_name: str,
            payload_bytes: int = 37,
    ) -> float:
        phy_norm = str(phy_name).upper()

        if phy_norm in ("BLE1M", "1M"):
            phy_rate_mbps = 1.0
        elif phy_norm in ("BLE2M", "2M"):
            phy_rate_mbps = 2.0
        elif phy_norm in ("BLE125K", "CODED_S8", "S8", "125K"):
            phy_rate_mbps = 0.125
        elif phy_norm in ("BLE500K", "CODED_S2", "S2", "500K"):
            phy_rate_mbps = 0.5
        else:
            phy_rate_mbps = 1.0

        bits_per_packet = (int(payload_bytes) + 20) * 8
        total_bits = bits_per_packet * int(packet_count)
        tx_time_s = total_bits / (phy_rate_mbps * 1e6)

        return max(0.2, tx_time_s * 3.0)

    def _wait_bt_vsg_done(
            self,
            packet_count: int,
            phy_name: str,
            payload_bytes: int = 37,
            extra_guard_s: float = 0.2,
    ):
        estimated = self._estimate_bt_rx_tx_time(
            packet_count=packet_count,
            phy_name=phy_name,
            payload_bytes=payload_bytes,
        )

        timeout_s = float(estimated + extra_guard_s + 2.0)

        if hasattr(self.wt.bt, "wait_for_vsg_complete"):
            try:
                self.wt.bt.wait_for_vsg_complete(timeout=timeout_s)
                return
            except Exception:
                pass

        time.sleep(float(estimated + extra_guard_s))

    def _wait_bt_rx_report_settle(self, settle_s: float = 0.1):
        time.sleep(float(settle_s))

    # ------------------------------------------------------------------
    # mode switch
    # ------------------------------------------------------------------
    def switch_wifi_to_bt(self, port_no: int | None = None, baudrate: int | None = None, **kwargs) -> StepResult:
        state = get_or_create_state()

        try:
            self.dut.bt_power_on()
            self.dut.bt_grant_bt()
            self.dut.bt_bridge_open()

            port_no, baudrate = self._get_bt_port_info(port_no=port_no, baudrate=baudrate)
            self.sdk.init(port_no=port_no, baudrate=baudrate)

            state.runtime.active_interface = "bt"
            state.runtime.phase = "bt_entered"
            state.bt.entered_bt_mode = True
            state.bt.initialized = True
            state.bt.reset_done = False

            return StepResult.success("bt")
        except Exception as exc:
            self.logger.exception("switch_wifi_to_bt failed: %s", exc)
            return StepResult.failure(str(exc))

    # ------------------------------------------------------------------
    # calibration
    # ------------------------------------------------------------------
    def bt_calibration(
        self,
        channel: int = 19,
        freq_mhz: int = 2440,
        target_power_dbm: float = 10.0,
        phy_name: str = "BLE1M",
        payload: str = "PRBS9",
        flatness_channels: list[int] | None = None,
        rf_port: int = 1,
        pathloss_db: float | None = None,
        stable_modulation: bool = True,
        **kwargs,
    ) -> StepResult:
        """
        Current practical implementation:
        - center point TX verify measurement
        - derive gain_k from measured vs target delta
        - write gain_k by sdk.write_gain_k()
        - optional flatness placeholder based on provided channels

        Note:
        This is a practical bridge implementation until a full DLL-side
        calibration formula/command document is integrated.
        """
        state = get_or_create_state()
        self._ensure_bt_ready()

        if flatness_channels is None:
            flatness_channels = [0, 19, 39]

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_bt_pathloss(
                rf_port=rf_port,
                phy_name=phy_name,
                freq_mhz=freq_mhz,
            )

        try:
            tx_result = self.bt_tx_verify(
                channel=channel,
                freq_mhz=freq_mhz,
                target_power_dbm=target_power_dbm,
                phy_name=phy_name,
                payload=payload,
                rf_port=rf_port,
                pathloss_db=actual_pathloss_db,
                stable_modulation=stable_modulation,
            )
            if not tx_result.ok:
                return tx_result

            state = get_or_create_state()
            metrics = state.bt.tx_verify_last.get("metrics", {})
            measured_power = metrics.get("power_dbm")
            if measured_power is None:
                return StepResult.failure("bt_calibration_no_measured_power")

            power_err = float(target_power_dbm) - float(measured_power)

            # 0.5 dB / step encoding
            gain_k = int(round(power_err / 0.5)) & 0xFF
            self.sdk.write_gain_k(gain_k)

            flatness_bytes: list[int] = []
            center_freq = int(freq_mhz)

            for ch in flatness_channels:
                ch_freq = 2402 + int(ch) * 2
                loss_db = self._get_bt_pathloss(rf_port=rf_port, phy_name=phy_name, freq_mhz=ch_freq)

                tx_vfy = self.bt_tx_verify(
                    channel=int(ch),
                    freq_mhz=ch_freq,
                    target_power_dbm=target_power_dbm,
                    phy_name=phy_name,
                    payload=payload,
                    rf_port=rf_port,
                    pathloss_db=loss_db,
                    stable_modulation=stable_modulation,
                )
                if not tx_vfy.ok:
                    return tx_vfy

                ch_metrics = get_or_create_state().bt.tx_verify_last.get("metrics", {})
                ch_power = ch_metrics.get("power_dbm")
                if ch_power is None:
                    return StepResult.failure(f"bt_flatness_no_measured_power_ch_{ch}")

                delta_db = float(ch_power) - float(measured_power)
                flatness_byte = int(round(delta_db / 0.25)) & 0xFF
                flatness_bytes.append(flatness_byte)

            if flatness_bytes:
                self.sdk.write_flatness(flatness_bytes)

            try:
                rpt = self.sdk.action_report(REPORT_ALL)
                state.bt.thermal_bt = int(rpt.CurrThermalValue)
            except Exception:
                pass

            state.bt.gain_k = int(gain_k)
            state.bt.flatness_bytes = [int(x) & 0xFF for x in flatness_bytes]
            state.bt.center_channel = int(channel)
            state.bt.center_freq_mhz = int(center_freq)
            state.bt.center_power_dbm = float(measured_power)

            valid_bits = 0x00
            valid_bits |= (1 << 1)
            if flatness_bytes:
                valid_bits |= (1 << 2)
            valid_bits |= (0x2 << 3)
            state.bt.valid_bits = valid_bits & 0xFF

            state.bt.cal_done = True
            state.runtime.phase = "bt_calibrated"

            thermal_hex = "NA" if state.bt.thermal_bt is None else f"0x{state.bt.thermal_bt:02X}"
            flatness_str = "[" + ",".join(f"0x{x:02X}" for x in state.bt.flatness_bytes) + "]"

            return StepResult.success(
                f"gaink=0x{state.bt.gain_k:02X},"
                f"flatness={flatness_str},"
                f"thermal={thermal_hex},"
                f"valid=0x{state.bt.valid_bits:02X}"
            )

        except RealtekBtSdkError as exc:
            self.logger.exception("bt_calibration sdk failed: %s", exc)
            return StepResult.failure(str(exc))
        except Exception as exc:
            self.logger.exception("bt_calibration failed: %s", exc)
            return StepResult.failure(str(exc))

    # ------------------------------------------------------------------
    # TX verify
    # ------------------------------------------------------------------
    def bt_tx_verify(
        self,
        channel: int,
        freq_mhz: int,
        target_power_dbm: float,
        phy_name: str = "BLE1M",
        payload: str = "PRBS9",
        rf_port: int = 1,
        pathloss_db: float | None = None,
        demod: int = 9,
        stable_modulation: bool = True,
        tx_gain_index: int | None = None,
        tx_gain_value: int | None = None,
        **kwargs,
    ) -> StepResult:
        state = get_or_create_state()
        self._ensure_bt_ready()

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_bt_pathloss(
                rf_port=rf_port,
                phy_name=phy_name,
                freq_mhz=freq_mhz,
            )

        phy_tx = _map_phy_name_to_sdk_tx(phy_name)
        packet_type = _map_phy_name_to_packet_type(phy_name)
        payload_type = _map_payload_to_le_payload(payload)

        try:
            # use existing sdk wrapper for LE TX start
            self.sdk.le_tx_test_start(
                channel=channel,
                phy=phy_tx,
                payload_type=payload_type,
                packet_type=packet_type,
            )

            self.wt.bt.configure_vsa(
                freq_mhz=freq_mhz,
                target_power_dbm=target_power_dbm,
                rf_port=rf_port,
                pathloss_db=actual_pathloss_db,
                demod=demod,
                phy=phy_tx,
                is_agc=True,
            )

            metrics = {}
            payload_upper = str(payload).upper()
            if payload_upper == "PRBS9":
                metrics.update(self.wt.bt.fetch_power_only())
            elif payload_upper in ("11110000", "0F"):
                metrics.update(self.wt.bt.fetch_delta_f1())
            elif payload_upper in ("10101010", "55"):
                metrics.update(self.wt.bt.fetch_delta_f2_and_ble())
            else:
                metrics.update(self.wt.bt.fetch_power_only())

            try:
                rpt = self.sdk.action_report(REPORT_ALL)
                metrics["report_rx_rssi"] = int(rpt.RxRssi)
                metrics["report_cfo"] = float(rpt.Cfo)
                metrics["report_thermal"] = int(rpt.CurrThermalValue)
                metrics["report_total_tx_bits"] = int(rpt.TotalTXBits)
                metrics["report_total_tx_counts"] = int(rpt.TotalTxCounts)
                if metrics.get("init_freq_err_hz") is None:
                    metrics["init_freq_err_hz"] = float(rpt.Cfo)
            except Exception:
                pass

            state.bt.tx_verify_last = {
                "channel": int(channel),
                "freq_mhz": int(freq_mhz),
                "phy": str(phy_name),
                "payload": str(payload),
                "pathloss_db": float(actual_pathloss_db),
                "metrics": metrics,
            }
            state.bt.tx_verify_freq_err_hz = metrics.get("init_freq_err_hz")
            state.runtime.phase = "bt_tx_verified"

            return StepResult.success(metrics.get("power_dbm", metrics))

        except RealtekBtSdkError as exc:
            self.logger.exception("bt_tx_verify sdk failed: %s", exc)
            return StepResult.failure(str(exc))
        except Exception as exc:
            self.logger.exception("bt_tx_verify failed: %s", exc)
            return StepResult.failure(str(exc))
        finally:
            try:
                self.sdk.le_test_end()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # RX verify
    # ------------------------------------------------------------------
    def bt_rx_verify(
            self,
            channel: int,
            phy_name: str = "BLE1M",
            payload: str = "PRBS9",
            freq_mhz: int | None = None,
            tester_power_dbm: float | None = None,
            packet_count: int = 1000,
            rf_port: int = 1,
            pathloss_db: float | None = None,
            per_limit: float = 10.0,
            payload_bytes: int = 37,
            stable_modulation: bool = True,
            **kwargs,
    ) -> StepResult:
        state = get_or_create_state()
        self._ensure_bt_ready()

        if freq_mhz is None:
            freq_mhz = 2402 + channel * 2

        actual_pathloss_db = pathloss_db
        if actual_pathloss_db is None:
            actual_pathloss_db = self._get_bt_pathloss(
                rf_port=rf_port,
                phy_name=phy_name,
                freq_mhz=freq_mhz,
            )

        if tester_power_dbm is None:
            phy_norm = str(phy_name).upper()
            if phy_norm in ("BLE125K", "CODED_S8", "S8", "125K"):
                tester_power_dbm = -82.0
            elif phy_norm in ("BLE500K", "CODED_S2", "S2", "500K"):
                tester_power_dbm = -75.0
            else:
                tester_power_dbm = -70.0

        phy_rx = _map_phy_name_to_sdk_rx(phy_name)
        packet_type = _map_phy_name_to_packet_type(phy_name)
        payload_type = _map_payload_to_le_payload(payload)

        demod, wave_name = self._bt_rx_verify_profile(phy_name)
        tester_output_power_dbm = float(tester_power_dbm) + float(actual_pathloss_db)

        try:
            start_ts = time.time()

            self.sdk.le_rx_test_start(
                channel=channel,
                phy=phy_rx,
                payload_type=payload_type,
                packet_type=packet_type,
            )

            self.wt.bt.start_bt_vsg(
                freq_mhz=int(freq_mhz),
                power_dbm=float(tester_output_power_dbm),
                rf_port=int(rf_port) - 1,
                pathloss_db=float(actual_pathloss_db),
                wave_name=wave_name,
                packets=int(packet_count),
                demod=int(demod),
            )

            # wait tester send complete first
            self._wait_bt_vsg_done(
                packet_count=int(packet_count),
                phy_name=phy_name,
                payload_bytes=int(payload_bytes),
            )

            # then allow DUT/report side to settle briefly
            self._wait_bt_rx_report_settle(settle_s=0.1)

            self.sdk.le_test_end()
            rpt = self.sdk.action_report(REPORT_LE_RX)

            elapsed = round(time.time() - start_ts, 2)

            dut_receive_count = int(rpt.RXRecvPktCnts)
            if packet_count > 0:
                per_percent = (1.0 - (dut_receive_count / float(packet_count))) * 100.0
                pass_percent = 100.0 - per_percent
            else:
                per_percent = None
                pass_percent = None

            passed = bool(per_percent is not None and per_percent <= float(per_limit))

            report_dict = {
                "channel": int(channel),
                "freq_mhz": int(freq_mhz),
                "phy": str(phy_name),
                "payload": str(payload),
                "rf_port": int(rf_port),
                "tester_send_count": int(packet_count),
                "tester_power_dbm": float(tester_power_dbm),
                "tester_output_power_dbm": float(tester_output_power_dbm),
                "pathloss_db": float(actual_pathloss_db),
                "dut_receive_count": dut_receive_count,
                "total_rx_bits": int(rpt.TotalRXBits),
                "total_rx_counts": int(rpt.TotalRxCounts),
                "total_rx_error_bits": int(rpt.TotalRxErrorBits),
                "rx_rssi": int(rpt.RxRssi),
                "ber": float(rpt.ber),
                "cfo": float(rpt.Cfo),
                "thermal": int(rpt.CurrThermalValue),
                "per_percent": per_percent,
                "pass_percent": pass_percent,
                "per_limit": float(per_limit),
                "passed": passed,
                "test_time_sec": float(elapsed),
                "wave_name": str(wave_name),
            }

            state.bt.rx_verify_last = report_dict
            state.runtime.phase = "bt_rx_verified"

            return StepResult.success(report_dict)

        except RealtekBtSdkError as exc:
            self.logger.exception("bt_rx_verify sdk failed: %s", exc)
            return StepResult.failure(str(exc))
        except Exception as exc:
            self.logger.exception("bt_rx_verify failed: %s", exc)
            return StepResult.failure(str(exc))
        finally:
            try:
                self.wt.bt.stop_vsg()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------
    def leave_bt_to_wifi(self) -> StepResult:
        state = get_or_create_state()

        try:
            self.dut.bt_bridge_close()
            self.dut.bt_grant_wifi()

            # current sdk has no explicit close(); safe to ignore if absent
            if hasattr(self.sdk, "close"):
                try:
                    self.sdk.close()
                except Exception:
                    pass

            state.runtime.active_interface = "wifi"
            state.runtime.phase = "wifi_restored"
            return StepResult.success("wifi")
        except Exception as exc:
            self.logger.exception("leave_bt_to_wifi failed: %s", exc)
            return StepResult.failure(str(exc))

    def bt_read_thermal(self, **kwargs) -> StepResult:
        state = get_or_create_state()

        try:
            rpt = self.sdk.action_report(REPORT_ALL)
            thermal = int(rpt.CurrThermalValue)
            state.bt.thermal_bt = thermal
            return StepResult.success(str(thermal))
        except Exception as exc:
            return StepResult.failure(str(exc))
