from .serial_tester import SerialTester


def query_fixture_sensor_status(tester_port, sensor):
    status = False
    try:

        serial_tester = SerialTester(tester_port, timeout=1)

        serial_tester.open()
        status = get_fixture_sensor_status(serial_tester, sensor)

        serial_tester.close()
    except Exception as e:
        print(str(e))
    return status


def get_fixture_sensor_status(connection, sensor):
    sensors = {}
    command = bytes([0x01, 0x03, 0x10, 0x01, 0x02, 0x00, 0x11, 0xAA])
    response = connection.send_receive(command, timeout=1)
    data = list(response)
    sports1 = f"{data[4]:08b}"[::-1]
    sports2 = f"{data[5]:08b}"[::-1]
    for i in range(8):
        sensors[f"S{i + 1}"] = sports1[i] == "1"
    for i in range(4):
        sensors[f"S{i + 9}"] = sports2[i] == "1"
    return sensors[sensor]
