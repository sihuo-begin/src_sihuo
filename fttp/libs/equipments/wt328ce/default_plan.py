from __future__ import annotations
from .models_wifi import (
    WifiTestPlan, WifiTxPowerCalPoint, WifiTxVerifyPoint, WifiRxPerPoint,
    WifiChannelPoint, WifiRate
)
from .models_bt import (
    BtTestPlan, BtTxPowerIndexCalPoint, BtTxVerifyPoint, BtRxPerPoint,
    BtChannelPoint, BtPhy
)

WIFI_PLAN = WifiTestPlan(
    tx_power_cal=[
        WifiTxPowerCalPoint(WifiChannelPoint(2412, 1),  WifiRate("HT40-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2427, 4),  WifiRate("HT40-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2442, 7),  WifiRate("HT40-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2457, 10), WifiRate("HT40-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2472, 13), WifiRate("HT40-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2442, 7),  WifiRate("54M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2442, 7),  WifiRate("HT20-MCS7")),
        WifiTxPowerCalPoint(WifiChannelPoint(2412, 1),  WifiRate("11M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2427, 4),  WifiRate("11M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2442, 7),  WifiRate("11M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2457, 10), WifiRate("11M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2472, 13), WifiRate("11M")),
        WifiTxPowerCalPoint(WifiChannelPoint(2484, 14), WifiRate("11M")),
    ],
    tx_verify=[
        WifiTxVerifyPoint(WifiChannelPoint(2412, 1),  WifiRate("11M")),
        WifiTxVerifyPoint(WifiChannelPoint(2442, 7),  WifiRate("11M")),
        WifiTxVerifyPoint(WifiChannelPoint(2472, 13), WifiRate("11M")),
        WifiTxVerifyPoint(WifiChannelPoint(2412, 1),  WifiRate("54M")),
        WifiTxVerifyPoint(WifiChannelPoint(2442, 7),  WifiRate("54M")),
        WifiTxVerifyPoint(WifiChannelPoint(2472, 13), WifiRate("54M")),
        WifiTxVerifyPoint(WifiChannelPoint(2412, 1),  WifiRate("HT20-MCS7")),
        WifiTxVerifyPoint(WifiChannelPoint(2442, 7),  WifiRate("HT20-MCS7")),
        WifiTxVerifyPoint(WifiChannelPoint(2472, 13), WifiRate("HT20-MCS7")),
        WifiTxVerifyPoint(WifiChannelPoint(2422, 3),  WifiRate("HT40-MCS7")),
        WifiTxVerifyPoint(WifiChannelPoint(2437, 6),  WifiRate("HT40-MCS7")),
        WifiTxVerifyPoint(WifiChannelPoint(2462, 11), WifiRate("HT40-MCS7")),
    ],
    rx_per=[
        WifiRxPerPoint(WifiChannelPoint(2412, 1), WifiRate("11M"),  frames=1000, per_limit=0.10, input_power_dbm=-76.0),
        WifiRxPerPoint(WifiChannelPoint(2442, 7), WifiRate("54M"),  frames=1000, per_limit=0.10, input_power_dbm=-65.0),
        WifiRxPerPoint(WifiChannelPoint(2472, 13), WifiRate("HT20-MCS7"), frames=1000, per_limit=0.10),
        WifiRxPerPoint(WifiChannelPoint(2422, 3),  WifiRate("HT40-MCS7"), frames=1000, per_limit=0.10),
        WifiRxPerPoint(WifiChannelPoint(2462, 11), WifiRate("HT40-MCS7"), frames=1000, per_limit=0.10),
    ],
)

BT_PLAN = BtTestPlan(
    tx_power_index_cal=[
        BtTxPowerIndexCalPoint(BtChannelPoint(2402, 0)),
        BtTxPowerIndexCalPoint(BtChannelPoint(2428, 4)),
        BtTxPowerIndexCalPoint(BtChannelPoint(2442, 15)),
        BtTxPowerIndexCalPoint(BtChannelPoint(2452, 25)),
        BtTxPowerIndexCalPoint(BtChannelPoint(2462, 35)),
    ],
    tx_verify=[
        BtTxVerifyPoint(BtChannelPoint(2422, 10), BtPhy("BLE1M")),
        BtTxVerifyPoint(BtChannelPoint(2442, 20), BtPhy("BLE1M")),
        BtTxVerifyPoint(BtChannelPoint(2480, 39), BtPhy("BLE1M")),
        BtTxVerifyPoint(BtChannelPoint(2402, 0),  BtPhy("BLE2M")),
        BtTxVerifyPoint(BtChannelPoint(2442, 20), BtPhy("BLE2M")),
        BtTxVerifyPoint(BtChannelPoint(2480, 39), BtPhy("BLE2M")),
        BtTxVerifyPoint(BtChannelPoint(2402, 0),  BtPhy("BLE125K")),
        BtTxVerifyPoint(BtChannelPoint(2480, 39), BtPhy("BLE500K")),
    ],
    rx_per=[
        BtRxPerPoint(BtChannelPoint(2402, 0), BtPhy("BLE1M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2442, 20), BtPhy("BLE1M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2480, 39), BtPhy("BLE1M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2402, 0), BtPhy("BLE2M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2442, 20), BtPhy("BLE2M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2480, 39), BtPhy("BLE2M"), input_power_dbm=-70.0),
        BtRxPerPoint(BtChannelPoint(2402, 0), BtPhy("BLE125K"), input_power_dbm=-82.0),
        BtRxPerPoint(BtChannelPoint(2480, 39), BtPhy("BLE500K"), input_power_dbm=-75.0),
    ],
)
