from datetime import datetime
class MESXml:
    def __init__(self):
        pass

    @classmethod
    def GenerateStepXml(cls,stepName, description, result, lsl, usl, status, comment=""):
        return f'<TEST NAME="{stepName}" DESCRIPTION="{description}" UNIT="" VALUE="{result}" HILIM="{usl}" LOLIM="{lsl}" STATUS="{status}" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT="{comment}"/>'

    @classmethod
    def GenerateGroupXml(cls,project, status, stepsXml: list):
        return f'<GROUP NAME ="{project}" STEPGROUP="" GROUPINDEX="" LOOPINDEX="" TYPE="" RESOURCE="" MODULETIME="" TOTALTIME="" TIMESTAMP="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" STATUS="{status}" >{"".join(stepsXml)}</GROUP>'

    @classmethod
    def GenerateResultXml(cls, project, serialNumber, tester, fixture, status, groupXml: list):
        return f'<?xml version="1.0" ?><BATCH TIMESTAMP="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" SYNTAX_REV="1.0" COMPATIBLE_REV=""><FACTORY NAME="FS" LINE="" TESTER="{tester}" FIXTURE="{fixture}" SHIFT="" USER="admin" /><PRODUCT NAME="{project}" REVISION="1" FAMILY="" CUSTOMER="{project}"/><REFS SEQ_REF="" FTS_REF="" LIM_REF="fftester.ini" CFG_REF="" CAL_REF="" INSTR_REF="" /><PANEL ID="Undef" COMMENT="" RUNMODE="PRODUCTION" TIMESTAMP="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" TESTTIME="" WAITTIME=\"\" STATUS=\"{status}\"><DUT ID="{serialNumber}" COMMENT="" PANEL="" SOCKET="" TIMESTAMP="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" TESTTIME="1" STATUS="{status}">{"".join(groupXml)}</DUT></PANEL></BATCH>'

    @classmethod
    def Generate_xml(cls,project, sn, station, fixture, test_summarys: dict):
        final_result = "PASS"
        groupxmls = []
        for key in test_summarys:
            test_summary = test_summarys[key]
            step_xmls = []
            for step in test_summary:
                step_xml = cls.GenerateStepXml(step["test_item"], "", step["test_value"], step["lsl"], step["usl"],
                                           step["status"])
                if step["status"] == "FAIL" and final_result == "PASS":
                    final_result = "FAIL"
                step_xmls.append(step_xml)

            groupXml = cls.GenerateGroupXml(key, final_result, step_xmls)
            groupxmls.append(groupXml)

        return cls.GenerateResultXml(project, sn, station, fixture, final_result, groupxmls)

# if __name__ == '__main__':
#     test_summary_dict = {"controls":[
#                 {
#                     "test_item": "scan_vsn",
#                     "test_value": "123",
#                     "lsl": "123",
#                     "usl": "123",
#                     "status": "PASS",
#                 },
#                 {
#                     "test_item": "scan_vsn2",
#                     "test_value":"456",
#                     "lsl": "456",
#                     "usl": "456",
#                     "status": "PASS",
#                 }
#     ],
#     "engine":[{
#                     "test_item": "scan_vsn",
#                     "test_value": "123",
#                     "lsl": "123",
#                     "usl": "123",
#                     "status": "PASS",
#                 },
#                 {
#                     "test_item": "scan_vsn2",
#                     "test_value":"456",
#                     "lsl": "456",
#                     "usl": "456",
#                     "status": "PASS",
#                 }]
#     }
# xml_text = MESXml.Generate_xml("Eagle Mono", "NEM0045007F000400000001", "MT1-0001", "HVTE-0001", test_summary_dict)
# print(xml_text)