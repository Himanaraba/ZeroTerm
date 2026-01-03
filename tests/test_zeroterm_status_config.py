from __future__ import annotations

import unittest

from tests.helpers import temp_env
from zeroterm_status.config import load_config


class TestStatusConfig(unittest.TestCase):
    def test_status_config_overrides(self) -> None:
        with temp_env(
            {
                "ZEROTERM_STATUS_INTERVAL": "15",
                "ZEROTERM_STATUS_IFACE": "wlan1",
                "ZEROTERM_STATUS_IFACE_AUTO": "1",
                "ZEROTERM_STATUS_NIGHT_START": "23",
                "ZEROTERM_STATUS_NIGHT_END": "5",
                "ZEROTERM_STATUS_NIGHT_INTERVAL": "120",
                "ZEROTERM_STATUS_LOW_BATTERY": "25",
                "ZEROTERM_STATUS_LOW_BATTERY_INTERVAL": "180",
                "ZEROTERM_STATUS_WIFI_INTERVAL": "20",
                "ZEROTERM_STATUS_SERVICE_INTERVAL": "30",
                "ZEROTERM_STATUS_METRICS_INTERVAL": "45",
                "ZEROTERM_STATUS_IDLE_INTERVAL": "90",
                "ZEROTERM_STATUS_WIFI_SSID": "0",
            }
        ):
            config = load_config()
        self.assertEqual(config.interval, 15)
        self.assertEqual(config.iface, "wlan1")
        self.assertTrue(config.iface_auto)
        self.assertEqual(config.night_start, 23)
        self.assertEqual(config.night_end, 5)
        self.assertEqual(config.night_interval, 120)
        self.assertEqual(config.low_battery_threshold, 25)
        self.assertEqual(config.low_battery_interval, 180)
        self.assertEqual(config.wifi_interval, 20)
        self.assertEqual(config.service_interval, 30)
        self.assertEqual(config.metrics_interval, 45)
        self.assertEqual(config.idle_interval, 90)
        self.assertFalse(config.wifi_ssid)

    def test_clamping(self) -> None:
        with temp_env(
            {
                "ZEROTERM_STATUS_NIGHT_START": "44",
                "ZEROTERM_STATUS_NIGHT_END": "-1",
                "ZEROTERM_STATUS_LOW_BATTERY": "999",
            }
        ):
            config = load_config()
        self.assertEqual(config.night_start, 22)
        self.assertEqual(config.night_end, 6)
        self.assertEqual(config.low_battery_threshold, 100)
