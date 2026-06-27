import sys
import time
from queue import Queue, Empty
from pc_ble_driver_py.observers import *

# TARGET_DEV_NAME = "Nordic_UART"
TARGET_DEV_NAME = None
TARGET_MAC = "C06A0654A5A0"
notify_handle = None
write_handle = None
UUID = None
CFG_TAG = 1


def init(conn_ic_id):
    global config, BLEDriver, BLEAdvData, BLEEvtID, BLEAdapter, BLEEnableParams, BLEGapTimeoutSrc, BLEUUID, BLEConfigCommon, BLEConfig, BLEConfigConnGatt, BLEGapScanParams, BLEGapConnParams
    from pc_ble_driver_py import config

    config.__conn_ic_id__ = conn_ic_id
    from pc_ble_driver_py.ble_driver import (
        BLEDriver,
        BLEAdvData,
        BLEEvtID,
        BLEEnableParams,
        BLEGapTimeoutSrc,
        BLEUUID,
        BLEGapScanParams,
        BLEGapConnParams,
        BLEConfigCommon,
        BLEConfig,
        BLEConfigConnGatt,
    )
    from pc_ble_driver_py.ble_adapter import BLEAdapter

    global nrf_sd_ble_api_ver
    nrf_sd_ble_api_ver = config.sd_api_ver_get()


class HRCollector(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter, target_mac):
        super(HRCollector, self).__init__()
        self.adapter = adapter
        self.conn_q = Queue()
        self.found = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.adapter.default_mtu = 250
        self.packet_count = 0
        self.target_mac = target_mac
        self.last_packet_time = None
        self.notification_interval_list = []

    def open(self):
        self.adapter.driver.open()
        if config.__conn_ic_id__.upper() == "NRF51":
            self.adapter.driver.ble_enable(
                BLEEnableParams(
                    vs_uuid_count=1,
                    service_changed=0,
                    periph_conn_count=0,
                    central_conn_count=1,
                    central_sec_count=0,
                )
            )
        elif config.__conn_ic_id__.upper() == "NRF52":
            gatt_cfg = BLEConfigConnGatt()
            gatt_cfg.att_mtu = self.adapter.default_mtu
            gatt_cfg.tag = CFG_TAG
            self.adapter.driver.ble_cfg_set(BLEConfig.conn_gatt, gatt_cfg)
            self.adapter.driver.ble_enable()

    def close(self):
        self.adapter.driver.close()

    def on_gap_evt_rssi_changed(self, ble_driver, conn_handle, rssi):
        print(f"RSSI update: Connection {conn_handle}, RSSI={rssi} dBm")

    def rssi_discover(self, conn_params=None, tx_power=None, scan_timeout=10):
        scan_params = BLEGapScanParams(interval_ms=100, window_ms=50, timeout_s=scan_timeout)
        self.adapter.driver.ble_gap_scan_start(scan_params=scan_params)
        try:
            rssi = self.conn_q.get(timeout=scan_timeout)
            if rssi:
                return rssi
        except Exception as e:
            print(f"RSSI discovery error{e}")
        return None

    def connect_and_discover(self, conn_params=None, tx_power=None, scan_timeout=10):
        scan_params = BLEGapScanParams(interval_ms=100, window_ms=50, timeout_s=scan_timeout)
        self.adapter.driver.ble_gap_scan_start(scan_params=scan_params)
        try:
            new_conn = self.conn_q.get(timeout=scan_timeout)
            if tx_power is not None:
                try:
                    self.adapter.driver.ble_gap_tx_power_set(tx_power)
                    print(f"Set TX power to {tx_power} dBm (global)")
                except Exception as e:
                    print(f"TX power set failed: {e}")
            if conn_params is not None:
                try:
                    self.adapter.driver.ble_gap_conn_param_update(new_conn, conn_params)
                    print(
                        f"connections: min/max_interval={conn_params.min_conn_interval_ms}/{conn_params.max_conn_interval_ms} ms, "
                        f"slave_latency={conn_params.slave_latency}, timeout={conn_params.conn_sup_timeout_ms} ms"
                    )
                except Exception as e:
                    print(f"Conn param update failed: {e}")
            print(">>>>>>>>>>>>>>>>>>")
            try:
                self.adapter.service_discovery(new_conn)
            except KeyError as e:
                print(f"Service discovery failed (KeyError): {e}. Try reconnect...")
                try:
                    self.adapter.disconnect(new_conn)
                except Exception:
                    pass
                return None
            except Exception as e:
                print(f"Service discovery failed: {e}")
                try:
                    self.adapter.disconnect(new_conn)
                except Exception:
                    pass
                return None
            services = self.adapter.db_conns[new_conn].services
            print("services:", services)
            try:
                self.adapter.driver.ble_gap_rssi_start(new_conn, threshold_dbm=5, skip_count=1)
                print("Started RSSI reporting for connection", new_conn)
            except Exception as e:
                print("Failed to start RSSI reporting:", e)
            global write_handle, notify_handle, write_uuid, notify_uuid
            write_handle = None
            notify_handle = None
            write_uuid = None
            notify_uuid = None
            for s in services:
                print(f"Service: {s.uuid}")
                for c in s.chars:
                    if hasattr(c, "char_props") and (c.char_props.write or c.char_props.write_wo_resp):
                        write_handle = int(c.handle_value)
                        write_uuid = c.uuid
                        print(f"wirite: uuid={c.uuid} handle={c.handle_value}")
                    if hasattr(c, "char_props") and (c.char_props.write or c.char_props.write_wo_resp):
                        write_handle = int(c.handle_value)
                    if hasattr(c, "char_props") and c.char_props.notify:
                        notify_handle = int(c.handle_value)
                    if hasattr(c, "properties"):
                        print(f"  Char: {c.uuid} properties: {c.properties}")
                        notify = getattr(c.properties, "notify", False)
                    elif hasattr(c, "char_props"):
                        print(f"  Char: {c.uuid} char_props: {c.char_props}")
                        notify = getattr(c.char_props, "notify", False)
                    else:
                        print(f"  Char: {c.uuid} (unkown)")
                        notify = False
                    if hasattr(c, "char_props") and c.char_props.notify:
                        notify_handle = int(c.handle_value)
                        notify_uuid = c.uuid
                        try:
                            self.adapter.enable_notification(new_conn, notify_uuid)
                            print(f"notify: {notify_uuid}")
                        except Exception as e:
                            print(f"failure notify: {notify_uuid} {e}")
            return new_conn
        except Empty:
            print(f"No device advertising with name {TARGET_DEV_NAME} found. {Empty}")
            return None

    def on_gap_evt_connected(self, ble_driver, conn_handle, peer_addr, role, conn_params):
        print("New connection: {}".format(conn_handle))
        self.conn_q.put(conn_handle)

    def on_gap_evt_disconnected(self, ble_driver, conn_handle, reason):
        print("Disconnected: {} {}".format(conn_handle, reason))

    def on_gap_evt_adv_report(self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data):
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]
        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return
        dev_name = "".join(chr(e) for e in dev_name_list)
        address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        print(
            "Received advertisment report, address: 0x{}, device_name: {} RSSI:{}".format(
                address_string, dev_name, rssi
            )
        )

        # if dev_name == TARGET_DEV_NAME:
        #     self.adapter.connect(peer_addr, tag=CFG_TAG)
        print("self.target_mac", self.target_mac)
        print("address_string", address_string)
        if address_string == self.target_mac:
            print(f"Found target MAC: {address_string}, connecting...")
            # self.adapter.connect(peer_addr, tag=CFG_TAG)
            self.rssi = rssi
            self.conn_q.put(rssi)

        address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
        print(
            "Received advertisment report, address: 0x{}, device_name: {}".format(
                address_string,
                "".join(chr(e) for e in adv_data.records.get(BLEAdvData.Types.complete_local_name, [])),
            )
        )
        # if address_string == TARGET_MAC:
        #     self.rssi = rssi
        #     self.adapter.connect(peer_addr, tag=CFG_TAG)

    def on_notification(self, ble_adapter, conn_handle, uuid, data):
        now = time.time()
        self.packet_count += 1
        if self.last_packet_time is not None:
            interval = now - self.last_packet_time
            self.notification_interval_list.append(interval)
        self.last_packet_time = now
        if len(data) > 32:
            data = "({}...)".format(data[0:10])
        print("Connection: {}, {} = {}, total packets: {}".format(conn_handle, uuid, data, self.packet_count))

    def reset_packet_count(self):
        self.packet_count = 0
        self.notification_interval_list = []
        self.last_packet_time = None

    def get_packet_count(self):
        return self.packet_count

    def get_notification_stats(self):
        if len(self.notification_interval_list) == 0:
            return 0, 0, 0
        avg_interval = sum(self.notification_interval_list) / len(self.notification_interval_list)
        min_interval = min(self.notification_interval_list)
        max_interval = max(self.notification_interval_list)
        return avg_interval, min_interval, max_interval


def rssi_read(collector, adapter, conn_params, tx_power, timeout=5):
    print(f"==== parameters ====")
    print(
        f"conn: min/max_interval={conn_params.min_conn_interval_ms}/{conn_params.max_conn_interval_ms} ms, "
        f"slave_latency={conn_params.slave_latency}, timeout={conn_params.conn_sup_timeout_ms} ms"
    )
    print(f"TX power: {tx_power} dBm")
    print("=================")
    for i in range(3):
        rssi = collector.rssi_discover(conn_params=conn_params, tx_power=tx_power, scan_timeout=20)
        print("received rssi:", rssi)
        if rssi is not None:
            return rssi
        print(f"Connect attempt {i + 1} failed, retrying...")
        time.sleep(1)
    print("Retry 3 times failed rssi")
    return None


def test_packet_loss(collector, adapter, conn_params, tx_power, target_count=2000, timeout=5):
    print(f"==== parameters ====")
    print(
        f"conn: min/max_interval={conn_params.min_conn_interval_ms}/{conn_params.max_conn_interval_ms} ms, "
        f"slave_latency={conn_params.slave_latency}, timeout={conn_params.conn_sup_timeout_ms} ms"
    )
    print(f"TX power: {tx_power} dBm")
    print(f"target pacage: {target_count} 个, timeout {timeout} 秒")
    print("=================")
    for i in range(3):
        conn = collector.connect_and_discover(conn_params=conn_params, tx_power=tx_power, scan_timeout=20)
        if conn is not None:
            return conn
        print(f"Connect attempt {i + 1} failed, retrying...")
        time.sleep(1)
    print("All connect attempts failed.")
    # conn = collector.connect_and_discover(conn_params=conn_params, tx_power=tx_power)
    if conn is not None:
        collector.reset_packet_count()
        if write_uuid is not None:
            test_data = bytes([0xFF, 0xFF]) * 100
            try:
                adapter.write_cmd(conn, write_uuid, test_data)
                print(f"writed uuid={write_uuid} writing，triger notify")
            except Exception as e:
                print(f"write failure: {e}")
        else:
            print("no found write uuid，cannot write")
        print("counts...")
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            time.sleep(0.2)
        total = collector.get_packet_count()
        avg, mini, maxi = collector.get_notification_stats()
        print(f"received: {total} counts")
        if total > 1:
            print(f"average: {avg:.3f} s, min: {mini:.3f} s, max: {maxi:.3f} s")
        else:
            print("received too low")
        try:
            adapter.disconnect(conn)
        except Exception as e:
            print(f"Disconnect failed: {e}")
        time.sleep(3)
    else:
        print("no connection.")


def main(selected_serial_port):
    driver = BLEDriver(
        serial_port=selected_serial_port,
        auto_flash=False,
        baud_rate=1000000,
        log_severity_level="info",
    )
    adapter = BLEAdapter(driver)
    collector = HRCollector(adapter)
    collector.open()

    conn_params_list = [
        BLEGapConnParams(
            min_conn_interval_ms=80,
            max_conn_interval_ms=100,
            slave_latency=0,
            conn_sup_timeout_ms=4000,
        ),
    ]
    tx_power_list = [4]  # dBm

    for conn_params in conn_params_list:
        for tx_power in tx_power_list:
            # test_packet_loss(collector, adapter, conn_params, tx_power, test_duration=10)
            time.sleep(0.3)
            test_packet_loss(collector, adapter, conn_params, tx_power, target_count=2000, timeout=5)

    collector.close()


def rssi_measure(selected_serial_port, target_mac):
    driver = BLEDriver(
        serial_port=selected_serial_port,
        auto_flash=False,
        baud_rate=1000000,
        log_severity_level="info",
    )
    adapter = BLEAdapter(driver)
    collector = HRCollector(adapter, target_mac)
    collector.open()

    conn_params_list = [
        BLEGapConnParams(
            min_conn_interval_ms=80,
            max_conn_interval_ms=100,
            slave_latency=0,
            conn_sup_timeout_ms=4000,
        )
    ]
    tx_power = 0
    # test_packet_loss(collector, adapter, conn_params, tx_power, test_duration=10)
    time.sleep(0.3)
    tx_power_list = [0]
    for conn_params in conn_params_list:
        for tx_power in tx_power_list:
            rssi = rssi_read(collector, adapter, conn_params, tx_power, timeout=10)
    collector.close()
    return rssi


# if __name__ == "__main__":
#     # 你可以根据需求修改串口号
#     init("NRF52")
#     serial_port = "COM6"  # 根据你的PC实际端口调整
#     # main(serial_port)
#     rssi = rssi_measure(serial_port)
