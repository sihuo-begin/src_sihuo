from zeep import Client


def routing_check(sn, station):
    try:
        address = "http://172.30.11.219/PMICheckRouting/WebService.asmx?wsdl"
        client = Client(address)
        res = client.service.GetRoutingInfo(sn, station)
        if "UnitInfo" in res:
            return True, res
        else:
            return False, res
    except Exception as e:
        return False, f"Error,{e}"
