from zeep import Client


class WCFMes:
    url = r'http://172.30.31.110:8081/EagleMonoPCBA?singleWsdl'
    client = Client(url)

    binding_name = '{http://tempuri.org/}BasicHttpBinding_IFFTesterService'

    service = client.create_service(
        binding_name,
        "http://172.30.31.110:8081/EagleMonoPCBA"
    )
    def __init__(self):
        pass

    @classmethod
    def routing_check(cls,sn, station):
        try:
            info = cls.service.GetUnitInfo(sn, station, "admin", "")
            print(info)
            if info["Id"] == 0:
                return True, info["Value"]
            else:
                return False, info["Value"]
        except Exception as e:
            return False, f"Error,{e}"


    @classmethod
    def save_result(cls,xml_info, station, sn, status, jsons:list):
        # xmlinfo = '''<?xml version="1.0" ?><BATCH TIMESTAMP="2026-03-24 14:47:53" SYNTAX_REV="1.0" COMPATIBLE_REV=""><FACTORY NAME="FS" LINE="" TESTER="MT7_test_3AA01ASC-01" FIXTURE="MT7_test_3AA01ASC-01" SHIFT="" USER="admin" /><PRODUCT NAME="Alpha" REVISION="1" FAMILY="" CUSTOMER="Alpha"/><REFS SEQ_REF="" FTS_REF="" LIM_REF="fftester.ini" CFG_REF="" CAL_REF="" INSTR_REF="" /><PANEL ID="Undef" COMMENT="" RUNMODE="PRODUCTION" TIMESTAMP="2026-03-24 14:47:53" TESTTIME="" WAITTIME="" STATUS="PASS"><DUT ID="TCPN D2F GP7 RKV9" COMMENT="" PANEL="" SOCKET="" TIMESTAMP="2026-03-24 14:47:53" TESTTIME="1" STATUS="PASS"><GROUP NAME="Alpha" STEPGROUP="" GROUPINDEX="" LOOPINDEX="" TYPE="" RESOURCE="" MODULETIME="" TOTALTIME="" TIMESTAMP="2026-03-24 14:47:53" STATUS="PASS" ><TEST NAME="Event Count" DESCRIPTION="" UNIT="" VALUE="9" HILIM="20" LOLIM="9" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Start Reason" DESCRIPTION="" UNIT="" VALUE="1" HILIM="1" LOLIM="1" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Heating Duration" DESCRIPTION="" UNIT="" VALUE="366" HILIM="366" LOLIM="366" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Stop Reason" DESCRIPTION="" UNIT="" VALUE="2" HILIM="2" LOLIM="2" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/></GROUP></DUT></PANEL></BATCH>
        # '''
        try:
            info = cls.service.SaveResult(xml_info, station, "admin", "", sn, status)
            print(info)
            if info["Id"] == 0:
                return True, info["Value"]
            else:
                return False, info["Value"]
        except Exception as e:
            return False, f"Error,{e}"


# if __name__ == '__main__':
#     #Routing Check and get information from FlexFlow
#     sn = "NEM0045007F000400000073"
#     station = "MT1(Auto)_3AC02A"
#     status, info = WCFMes.routing_check(sn, station)
#     if status:
#         print("allow to test in current test station")
#     else:
#         print("error")

    # #save test result to Flexflow
    # xmlinfo = '''<?xml version="1.0" ?><BATCH TIMESTAMP="2026-03-24 14:47:53" SYNTAX_REV="1.0" COMPATIBLE_REV=""><FACTORY NAME="FS" LINE="" TESTER="MT7_test_3AA01ASC-01" FIXTURE="MT7_test_3AA01ASC-01" SHIFT="" USER="admin" /><PRODUCT NAME="Alpha" REVISION="1" FAMILY="" CUSTOMER="Alpha"/><REFS SEQ_REF="" FTS_REF="" LIM_REF="fftester.ini" CFG_REF="" CAL_REF="" INSTR_REF="" /><PANEL ID="Undef" COMMENT="" RUNMODE="PRODUCTION" TIMESTAMP="2026-03-24 14:47:53" TESTTIME="" WAITTIME="" STATUS="PASS"><DUT ID="TCPN D2F GP7 RKV9" COMMENT="" PANEL="" SOCKET="" TIMESTAMP="2026-03-24 14:47:53" TESTTIME="1" STATUS="PASS"><GROUP NAME="Alpha" STEPGROUP="" GROUPINDEX="" LOOPINDEX="" TYPE="" RESOURCE="" MODULETIME="" TOTALTIME="" TIMESTAMP="2026-03-24 14:47:53" STATUS="PASS" ><TEST NAME="Event Count" DESCRIPTION="" UNIT="" VALUE="9" HILIM="20" LOLIM="9" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Start Reason" DESCRIPTION="" UNIT="" VALUE="1" HILIM="1" LOLIM="1" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Heating Duration" DESCRIPTION="" UNIT="" VALUE="366" HILIM="366" LOLIM="366" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/><TEST NAME="Stop Reason" DESCRIPTION="" UNIT="" VALUE="2" HILIM="2" LOLIM="2" STATUS="PASS" RULE="EQ" TARGET="" DATATYPE="STR" COMMENT=""/></GROUP></DUT></PANEL></BATCH>
    #         # '''
    # # Save PASS result to Flexflow
    # WCFMes.save_result(xmlinfo, station, sn, "PASS")
    # # Save FAIL result to Flexflow
    # WCFMes.save_result(xmlinfo, station, sn, "FAIL")
