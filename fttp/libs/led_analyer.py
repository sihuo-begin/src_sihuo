"""LED Analyzer driver"""


class FeasaLEDAnalyzer:
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger

    def send_command(self, cmd):
        """send cmd"""
        return self.connection.send_receive(cmd)

    def capture(self, brightness=1):
        """data collect"""
        try:
            resp = self.send_command("CAPTURE{}\r".format(brightness))
            self.logger.debug(f"capture return: {resp}")
        except Exception as e:
            self.logger.debug(f"error is  {e}")
            resp = self.send_command("CAPTURE{}\r".format(brightness))
            self.logger.debug(f"capture return: {resp}")
        # return bytes(resp).strip()=="OK"  # 一般返回OK
        return bytes(resp).strip()  # 一般返回OK

    def get_rgbi(self, channel=0):
        """Get RBG"""
        try:
            resp = self.send_command(f"getrgbi{channel}\r")
            self.logger.debug(f"getrgbi{channel} return: {resp}")
        except Exception as e:
            self.logger.debug(f"error is  {e}")
            resp = self.send_command(f"getrgbi{channel}\r")
            self.logger.debug(f"getrgbi{channel} return: {resp}")
        fields = bytes(resp).decode("utf-8").strip().split(" ")
        if len(fields) < 4:
            return None
        return {
            # 'channel': int(fields[0]),
            "R": int(fields[0]),
            "G": int(fields[1]),
            "B": int(fields[2]),
            "I": float(fields[3]),
        }

    def get_intensity_all(self):
        """
        get channel RGBI data
        new: getrgbiN
        :return: ch,R,G,B,I
        """
        data_dict = {}
        try:
            resp = self.send_command(f"getintensityall\r")
            self.logger.debug(f"getintensityall return: {resp}")
        except Exception as e:
            self.logger.debug(f"error is  {e}")
            resp = self.send_command(f"getintensityall\r")
            self.logger.debug(f"getintensityall return: {resp}")
        fields = bytes(resp).decode("utf-8").strip()
        if len(fields) < 5:
            return None
        for line in fields.strip().split("\n"):
            key, value = line.split()
            data_dict[key] = int(value)  # converting the value to an integer
        return data_dict

    def get_xyzi(self, channel=0):
        """
        getXYZIda
        new: getxyziN
        :return: ch,X,Y,Z,I
        """
        resp = self.send_command(f"getxyzi{channel}")
        self.logger.debug(f"getxyzi{channel} return: {resp}")
        fields = resp.strip().split(",")
        if len(fields) < 5:
            return None
        return {
            "channel": int(fields[0]),
            "X": float(fields[1]),
            "Y": float(fields[2]),
            "Z": float(fields[3]),
            "I": float(fields[4]),
        }

    def is_red(self, R, G, B):
        return R > 120 and G < 80 and B < 80 and (R - max(G, B)) > 50

    def is_white(self, R, G, B):
        return abs(R - G) < 20 and abs(R - B) < 20 and min(R, G, B) > 150

    def is_amber(self, R, G, B):
        ratio = R / G if G > 0 else 0
        return R > 120 and 60 < G < 150 and B < 60 and 1.1 < ratio < 2.2

    def test_color(self, channel=0):
        self.capture()
        rgb_data = self.get_rgbi(channel)
        if not rgb_data:
            self.logger.debug("wrong RGBI format")
            return None
        R, G, B = rgb_data["R"], rgb_data["G"], rgb_data["B"]
        if self.is_red(R, G, B):
            result = "RED"
        elif self.is_white(R, G, B):
            result = "WHITE"
        elif self.is_amber(R, G, B):
            result = "AMBER"
        else:
            result = "UNKNOWN"
        self.logger.debug(f"result: {result}")
        return result, rgb_data
