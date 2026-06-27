import sys
import unittest
from unittest.mock import MagicMock, patch
from .. import test_steps


class TestTestSteps(unittest.TestCase):

    @patch.object(test_steps, "gl")
    @patch.object(test_steps, "builder")
    @patch.object(test_steps, "prodcut_map")
    @patch.object(test_steps, "to_hex_without_head")
    @patch.object(test_steps, "to_hex")
    def test_detect_dut_success(
        self,
        mock_to_hex,
        mock_to_hex_without_head,
        mock_prodcut_map,
        mock_builder,
        mock_gl,
    ):
        # Mock connection object
        mock_connection = MagicMock()
        mock_connection.ensure_connected.side_effect = [True, True]
        mock_connection.send_receive.side_effect = [
            b"\x00\x01\x00\x02\x00\x03\x04\x05\x06\x07\x0b\x0c\x0d\x0e",
            b"data",
        ]

        # Mock connections dict
        connections = {"usb": mock_connection}

        # Mock stop_event
        mock_stop_event = MagicMock()
        mock_stop_event.is_set.side_effect = [False, False, True]
        mock_gl.get_value.return_value = mock_stop_event

        # Mock builder methods
        mock_builder.build_read_request_frame.return_value = b"cmd"
        mock_builder.unpack_payload_fields.return_value = {
            "platform_code": 0x0001,
            "product_code": 0x0002,
            "site_code": 0x0003,
            "device_number": 0x04050607,
            "hardware_revision": 0x0B0C,
            "reserve": 0x0D0E,
        }

        # Mock prodcut_map
        mock_prodcut_map.get.return_value = "ProductName"

        # Mock to_hex and to_hex_without_head
        mock_to_hex_without_head.side_effect = lambda val, length: f"{val:0{length * 2}X}"
        mock_to_hex.side_effect = lambda val, length: f"0x{val:0{length * 2}X}"

        # Mock logger
        logger = MagicMock()

        res, dusn = test_steps.detect_dut(connections, logger, limit=5)
        self.assertEqual(res["platform_code"], 0x01)
        self.assertEqual(dusn, "0x04050607")


#
#
#
# if __name__ == '__main__':
#     unittest.main()
