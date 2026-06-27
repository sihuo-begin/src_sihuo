voltage_mv = "mV"
voltage_v = "V"
acceleration = "mG"
current_ma = "mA"
current_ua = "uA"
percent = "%"
temperature = "degC"
freq_hz = "Hz"
freq_mhz = "mHz"
freq_ghz = "GHz"
register = "Ohm"
register_k = "KOhm"
register_m = "MOhm"
power = "dB"
time_ms = "ms"
time_s = "s"
time_m = "m"
time_h = "h"


prodcut_map = {
    "007b": "Beta_Charger",
    "ffff": "Hermes_Mid",
    "0063": "Beta_Holder_engine",
    "006a": "Hermes_Mid",
    "0xffff": "Hermes_Mid",
    "0069": "Hermes_Prime",
    "0066": "Hermes_Holder",
    "007a": "Beta_Holder",
    "000a": "rd",
    "007f": "eaglemono"
}

product_family_map = {
    "007b": "beta",
    "0063": "beta",
    "007a": "beta",
    "006a": "hermes",
    "0069": "hermes",
    "0066": "hermes",
    "ffff": "beta",
    "000a": "rd",
    "007f": "eaglemono"
}

led_cmd_mapping = {
    "holder": {0: {"red": 0xA3, "white": 0xA9}, 1: {"white": 0xC1}},
    "charger": {
        1: {"red": 0xA4, "white": 0xA5, "amber": 0xAA},
        2: {"white": 0xA6},
        3: {"white": 0xA7},
        4: {"white": 0xA8},
    },
}

# stations_mapping = {
#     "Beta_MT1_holder_control": "SFT2344",
#     "Beta_MT1_holder_engine": "SFT2345",
#     "Beta_MT1_charger": "SFT2346",
#     "Beta_holder_MT4A": "SFT2347",
#     "Beta_holder_MT7CTS": "SFT2348",
#     "Beta_holder_MT7LED": "SFT2349",
#     "Beta_holder_MT7VC": "SFT2350",
#     "Beta_holder_MT7H": "SFT2351",
#     "Beta_holder_Event_log_Check": "SFT2352",
#     "Beta_holder_MT11C": "SFT2353",
#     "Beta_charger_MT7BLE": "SFT2354",
#     "Beta_charger_MT7": "SFT2355",
#     "Beta_charger_MT11C": "SFT2356",
#
#     "BRINGUP_MT0": "SFT0001",
#     "Eaglemono_MT2": "SFT0002",
# }

stations_mapping = {
    "Beta": {
                            "Beta_MT1_holder_control": "SFT2344",
                            "Beta_MT1_holder_engine": "SFT2345",
                            "Beta_MT1_charger": "SFT2346",
                            "Beta_holder_MT4A": "SFT2347",
                            "Beta_holder_MT7CTS": "SFT2348",
                            "Beta_holder_MT7LED": "SFT2349",
                            "Beta_holder_MT7VC": "SFT2350",
                            "Beta_holder_MT7H": "SFT2351",
                            "Beta_holder_Event_log_Check": "SFT2352",
                            "Beta_holder_MT11C": "SFT2353",
                            "Beta_charger_MT7BLE": "SFT2354",
                            "Beta_charger_MT7": "SFT2355",
                            "Beta_charger_MT11C": "SFT2356",
                            },
    "RD": {"BRINGUP_MT0": "SFT0000",
            "Rd_MT0": "SFT0001"
           },
    "Eaglemono": {
        "Eaglemono_MT1": "SFT0001",
        "Eaglemono_MT2": "SFT0002",
        "Eaglemono_MT10": "SFT0010"
    },
}

ch_mapping = {
    2404: 0x01,
    2442: 0x14,
    2478: 0x26,
    2480: 0x27,
}

power_mapping = {
    -20: 0x01,
    -14.7: 0x02,
    -11.7: 0x03,
    -11.4: 0x04,
    -8.4: 0x05,
    -8.1: 0x06,
    -5.1: 0x07,
    -4.9: 0x08,
    -2.1: 0x09,
    -1.6: 0x0A,
    1.4: 0x0B,
    1.7: 0x0C,
    4.7: 0x0D,
    5.0: 0x0E,
    8: 0x0F,
    6: 0x1F,
    0: 0x00,
}

charger_m11c_io_mapping = {
    "Cell1_pass": "port0/line0",
    "Cell1_fail": "port3/line0",
    "Cell2_pass": "port0/line1",
    "Cell2_fail": "port3/line1",
    "Cell3_pass": "port0/line2",
    "Cell3_fail": "port3/line2",
    "Cell4_pass": "port0/line3",
    "Cell4_fail": "port3/line3",
    "Cell5_pass": "port6/line0",
    "Cell5_fail": "port9/line0",
    "Cell6_pass": "port6/line1",
    "Cell6_fail": "port9/line1",
    "Cell7_pass": "port6/line2",
    "Cell7_fail": "port9/line2",
    "Cell8_pass": "port6/line3",
    "Cell8_fail": "port9/line3",
    "Cell9_pass": "port1/line0",
    "Cell9_fail": "port4/line0",
    "Cell10_pass": "port1/line1",
    "Cell10_fail": "port4/line1",
    "Cell11_pass": "port1/line2",
    "Cell11_fail": "port4/line2",
    "Cell12_pass": "port1/line3",
    "Cell12_fail": "port4/line3",
    "Cell13_pass": "port7/line0",
    "Cell13_fail": "port10/line0",
    "Cell14_pass": "port7/line1",
    "Cell14_fail": "port10/line1",
    "Cell15_pass": "port7/line2",
    "Cell15_fail": "port10/line2",
    "Cell16_pass": "port7/line3",
    "Cell16_fail": "port10/line3",
    "Cell17_pass": "port2/line0",
    "Cell17_fail": "port5/line0",
    "Cell18_pass": "port2/line1",
    "Cell18_fail": "port5/line1",
    "Cell19_pass": "port2/line2",
    "Cell19_fail": "port5/line2",
    "Cell20_pass": "port2/line3",
    "Cell20_fail": "port5/line3",
    "Cell21_pass": "port8/line0",
    "Cell21_fail": "port11/line0",
    "Cell22_pass": "port8/line1",
    "Cell22_fail": "port11/line1",
    "Cell23_pass": "port8/line2",
    "Cell23_fail": "port11/line2",
    "Cell24_pass": "port8/line3",
    "Cell24_fail": "port11/line3",
}
battery_vendor_mapping = {
    "LES": "3",
    "BYD": "9",
    "Y": "9",
    "G": "3",
}
battery_tech_mapping = {"N": "4", "1": "4", "2": "8", "3": "D"}
model_id_mapping = {"hermes_prime": "M0021", "hermes_mid": "M0022"}
