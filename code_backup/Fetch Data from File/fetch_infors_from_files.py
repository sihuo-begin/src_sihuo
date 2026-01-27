import json
import os
import re
import time
import textwrap

import pandas as pd
import numpy as np

# from src.definition.product_mapping import voltage_v

# read_folder_path = "C:\Json"
read_folder_path = "C:\cell_logs"
read_folder_path = "C:\Check_Result\cell_logs20260120/oqa"
# read_file_path = "{}\cell_0_0x00000001_20250906_110825.log".format(read_folder_path)
write_folder_path = "C:\Check_Result"
write_file_path = "{}\check_result.txt".format(write_folder_path)
# pattern1 = "\[(.*?)\].*battery ADC:\s*(\d+)"
pattern1 = "\[(.*?)\].*battery_voltage is:\s*(\d+)"
pattern2 = "battery_charge is:\s*(\d+)"
# pattern2 = "battery charge:\s*(\d+)"
pattern3 = "read battery voltage is ([\d\.]+)"

if not os.path.exists(write_folder_path):
    os.makedirs(write_folder_path)
    with open(r"{}".format(write_file_path), 'w+') as f:
        f.write("Below is check result list\r")
        f.close()
# if os.path.exists(r"{}".format(read_file_path)):
#     # all_dirs = os.listdir(read_folder_path)
#     # print(all_dirs)
#     with open(r"{}".format(read_file_path), "r") as f:
#         file_content = f.readlines()
#         for line in file_content:
#             match1 = re.search(r"{}".format(pattern1), line)
#             match2 = re.search(r"{}".format(pattern2), line)
#             match3 = re.search(r"{}".format(pattern3), line)
#             if match1:
#                 with open(r"{}".format(write_file_path), "a") as write_f:
#                     write_f.write("{} {} ".format(match1[1], match1[2]))
#                 write_f.close()
#             if match2:
#                 with open(r"{}".format(write_file_path), "a") as write_f:
#                     write_f.write("{} ".format(match2[1]))
#                 write_f.close()
#             if match3:
#                 with open(r"{}".format(write_file_path), "a") as write_f:
#                     write_f.write("{}\r".format(match3[1]))
#                 write_f.close()
#         else:
#             f.close()
#             print("end")
###############################################################################################################################
# print(''' create excl file directly''')
# data = {
#     "Date_Time": [],
#     "Battery_ADC": [],
#     "Battery_Capacity": [],
#     "Battery_Level": [],
# }
# with open(r"{}".format(read_file_path), "r") as f:
#     file_content = f.readlines()
#     for line in file_content:
#         match1 = re.search(r"{}".format(pattern1), line)
#         match2 = re.search(r"{}".format(pattern2), line)
#         match3 = re.search(r"{}".format(pattern3), line)
#         if match1:
#             data["Date_Time"].append(match1[1])
#             data["Battery_ADC"].append(int(match1[2]))
#         if match2:
#             data["Battery_Capacity"].append(int(match2[1]))
#         if match3:
#             data["Battery_Level"].append(float(match3[1]))
#     else:
#         df = pd.DataFrame(data)
#         df.to_excel("{}\\beta_unit.xlsx".format(write_folder_path), index=True)
#         f.close()

# data = {
#     "Date_Time": [],
#     "Battery_ADC": [],
#     "Battery_Capacity": [],
#     "Battery_Level": [],
# }
dirs = os.listdir("{}".format(read_folder_path))
print(dirs)
pattern1 = "\[(.*?)\].*'battery_voltage':\s(\d+)"
pattern3 = ".'battery_current':\s(\d+)"
pattern2 = "'battery_soc':\s(\d+)"
data = {
    "Date_Time": [],
    "codentify_code": [],
    "Battery_current": [],
    "Battery_Capacity": [],
    "Battery_Level": [],
}
with pd.ExcelWriter('{}\\check_result_oqa_0121.xlsx'.format(write_folder_path), engine='openpyxl') as writer:
    for sub_dir in dirs:
        with open(r"{}\\{}".format(read_folder_path, sub_dir), "r") as f:
            Date_Time = ''
            Battery_Level = ''
            Battery_Capacity = ''
            Battery_current = ''
            file_content = f.readlines()
            # print(file_content)
            for line in file_content:
                match1 = re.search(r"{}".format(pattern1), line)
                match2 = re.search(r"{}".format(pattern2), line)
                match3 = re.search(r"{}".format(pattern3), line)
                if match1:
                    if len(Date_Time)==0:
                        # data["Date_Time"].append(match1[1])
                        Date_Time = match1[1]
                    Battery_Level = Battery_Level + match1[2] + " "
                    # data["Battery_Level"].append(int(match1[2]))
                if match2:
                    Battery_Capacity = Battery_Capacity + match2[1] + " "
                    # data["Battery_Capacity"].append(int(match2[1]))
                if match3:
                    Battery_current = Battery_current + match3[1] + " "
                    # data["Battery_Level"].append(float(match3[1]))
            else:
                data["Date_Time"].append(Date_Time)
                data["codentify_code"].append(sub_dir[7:24])
                data["Battery_Level"].append(Battery_Level)
                data["Battery_Capacity"].append(Battery_Capacity)
                data["Battery_current"].append(Battery_current)
                print(data)
                # df = pd.DataFrame(data)
                # # df.to_excel(writer, sheet_name=sub_dir[7:17], index=True)
                # df.to_excel(writer, sheet_name=sub_dir, index=True)
                # f.close()
                # print("end")
        print(data)
    df = pd.DataFrame(data)
    df.to_excel(writer, index=True)
# with pd.ExcelWriter('{}\\chager_voltage.xlsx'.format(write_folder_path), engine='openpyxl') as writer:
#     pattern2 = "\[(.*?)\].*battery charge:\s*(\d+)"
#     pattern3 = "\[(.*?)\].*read battery voltage is ([\d\.]+)"
#     data = {
#         # "Date_Time": [],
#         "Dusn": [],
#         # "Battery_ADC": [],
#         "Battery_Capacity": [],
#         # "Battery_Level": [],
#         "Battery_capacity_up_timeneed": [],
#         # "Battery_level_up_timeneed": [],
#     }
#     for sub_dir in dirs:
#         # data = {
#         #     # "Date_Time": [],
#         #     "Dusn": [],
#         #     # "Battery_ADC": [],
#         #     "Battery_Capacity": [],
#         #     # "Battery_Level": [],
#         #     "Battery_capacity_up_timeneed": [],
#         #     # "Battery_level_up_timeneed": [],
#         # }
#         with open(r"{}\\{}".format(read_folder_path, sub_dir), "r") as f:
#             file_content = f.readlines()
#             soc_pre = 0
#             time_pre = time.time()
#             # adc_pre = 0
#             # voltage_pre = 0
#             for line in file_content:
#                 match1 = re.search(r"{}".format(pattern1), line)
#                 match2 = re.search(r"{}".format(pattern2), line)
#                 match3 = re.search(r"{}".format(pattern3), line)
#                 # if match1:
#                 #     # data["Date_Time"].append(match1[1])
#                 #     # data["Battery_ADC"].append(int(match1[2]))
#                 #     if adc_pre != int(match1[2]):
#                 #         data["Battery_ADC"].append(int(match1[2]))
#                 #         time_struct = time.strptime(match1[1][:19], "%Y-%m-%d %H:%M:%S")
#                 #         current_time = time.mktime(time_struct)
#                 #         data["Battery_level_up_timeneed"].append(current_time-time_pre)
#                 #         adc_pre = int(match1[2])
#                 #         time_pre = current_time
#                 if match2:
#                     # data["Battery_Capacity"].append(int(match2[1]))
#                     if soc_pre != int(match2[2]):
#                         data["Dusn"].append(sub_dir[7:17])
#                         data["Battery_Capacity"].append(int(match2[2]))
#                         time_struct = time.strptime(match2[1][:19], "%Y-%m-%d %H:%M:%S")
#                         current_time = time.mktime(time_struct)
#                         data["Battery_capacity_up_timeneed"].append(current_time-time_pre)
#                         soc_pre = int(match2[2])
#                         time_pre = current_time
#                 # if match3:
#                 #     if voltage_pre != float(match3[2]):
#                 #         data["Battery_Level"].append(float(match3[2]))
#                 #         time_struct = time.strptime(match3[1][:19], "%Y-%m-%d %H:%M:%S")
#                 #         current_time = time.mktime(time_struct)
#                 #         data["Battery_level_up_timeneed"].append(current_time - time_pre)
#                 #         voltage_pre = float(match3[2])
#                 #         time_pre = current_time
#             else:
#                 # df = pd.DataFrame(data)
#                 # df.to_excel(writer, sheet_name=sub_dir[7:17], index=True)
#                 f.close()
#     df = pd.DataFrame(data)
#     df.to_excel(writer, index=True)
# print("end")

#+++++++++==============================================================================================================
# data = {
#     "Codentify_code": [],
#     "DUSN": [],
#     "Battery_SN": [],
#     "MT7_Read_Voltage": [],
#     "MT7_Battery_Percentage": [],
# }
# if os.path.exists(r"{}".format(read_folder_path)):
#     main_dirs = os.listdir(read_folder_path)
#     for sub_dirs in main_dirs:
#         sub_dirs1 = os.listdir("{}\\{}".format(read_folder_path, sub_dirs))
#         for sub_dirs2 in sub_dirs1:
#             with open(r"{}\\{}\\{}".format(read_folder_path, sub_dirs, sub_dirs2), 'r', encoding="utf-8") as f:
#                 content = json.load(f)
#                 test_data = content.get("Hermes_Mid_Charger_MT7_SFT1578").get("test")
#                 if len(test_data) < 80:
#                     continue
#                 for step in test_data:
#                     if step["pnum"] == "1284":
#                         data["Codentify_code"].append(step.get("actual", ''))
#                     if step["pnum"] == "1288":
#                         data["DUSN"].append(step.get("actual", ''))
#                     if step["pnum"] == "1556":
#                         data["Battery_SN"].append(step.get("actual", ''))
#                     if step["pnum"] == "1524":
#                         data["MT7_Read_Voltage"].append(step.get("actual", ""))
#                     if step["pnum"] == "1572":
#                         data["MT7_Battery_Percentage"].append(step.get("actual", ''))
# df = pd.DataFrame(data)
#
# df.to_excel(r'{}\check_result.xlsx'.format(write_folder_path), index=True)
# print("end")

# data = {}
# if os.path.exists(r"{}".format(write_folder_path)):
#     print("1")
#     if os.path.exists(r'{}\\check_result.xlsx'.format(write_folder_path)):
#         print("2")
#         df = pd.read_excel(r'{}\check_result.xlsx'.format(write_folder_path))
        # data = df.to_dict(orient='list')
        # print("data1 {}".format(data))
        # data = df.to_json(orient='records')
        # print("data2 {}".format(data))
# print(data)


########  json file update...........................................................................................
#
# write_folder_path = "C:\Check_Result\write"
# dirs = os.listdir("{}".format(read_folder_path))
# for sub_dir in dirs:
#     with open(r"{}\\{}".format(read_folder_path, sub_dir), 'r', encoding="utf-8") as f:
#         json_content = json.load(f)
#         print(json_content)
#         try:
#             for data in json_content["Beta_charger_MT7_SFT2355_R1"]["test"]:
#                 if "USB_CC_ADC_SIDE_B_TEST" in data["reference"]:
#                     data["pnum"] = "4015"
#                     break
#             else:
#                 break
#         except Exception as e:
#             for data in json_content["Beta_charger_MT7_SFT2355"]["test"]:
#                 if "USB_CC_ADC_SIDE_B_TEST" in data["reference"]:
#                     data["pnum"] = "4015"
#                     break
#             else:
#                 break
#     key_data = json_content["%device_crypto"]['data']
#     json_content["%device_crypto"]['data'] = []
#     update_path = os.path.join(
#         write_folder_path,
#         sub_dir,
#     )
#     print(update_path)
#     json_text = json.dumps(json_content, indent=2)
#     if key_data:
#         key_text = json.dumps(key_data)
#         wrapped_lines = textwrap.wrap(key_text, width=80)
#         wrapped_lines = [line.replace(" ", "") for line in wrapped_lines]
#         key_result = "\n    ".join(wrapped_lines)
#         json_text = json_text.replace('"data": []', f'"data":{key_result}')
#     with open(update_path, "w", encoding="utf-8") as f:
#         f.write(json_text)