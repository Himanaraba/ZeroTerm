from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from zeroterm_status import metrics


class TestMetricsHelpers(unittest.TestCase):
    def test_parse_percent(self) -> None:
        self.assertEqual(metrics._parse_percent("55"), 55)
        self.assertEqual(metrics._parse_percent("bat=99%"), 99)
        self.assertIsNone(metrics._parse_percent("nope"))
        self.assertIsNone(metrics._parse_percent("999"))

    def test_parse_kib(self) -> None:
        self.assertEqual(metrics._parse_kib("MemTotal: 12345 kB"), 12345)
        self.assertIsNone(metrics._parse_kib("MemTotal:"))

    def test_parse_temp_value(self) -> None:
        self.assertEqual(metrics._parse_temp_value("42000"), "42C")
        self.assertEqual(metrics._parse_temp_value("42"), "42C")
        self.assertIsNone(metrics._parse_temp_value("999999"))

    def test_format_uptime(self) -> None:
        self.assertEqual(metrics._format_uptime(60), "1m")
        self.assertEqual(metrics._format_uptime(3600), "1h0m")
        self.assertEqual(metrics._format_uptime(90000), "1d1h")

    def test_read_battery_from_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "BAT0"
            root.mkdir(parents=True, exist_ok=True)
            (root / "capacity").write_text("55\n", encoding="utf-8")
            (root / "type").write_text("Battery\n", encoding="utf-8")
            (root / "status").write_text("Charging\n", encoding="utf-8")
            info = metrics.read_battery(temp_dir, None)
        self.assertEqual(info.percent, 55)
        self.assertEqual(info.status, "Charging")

    def test_read_battery_cmd_missing(self) -> None:
        info = metrics.read_battery(None, "missing-command --foo")
        self.assertIsNone(info.percent)
        self.assertIsNone(info.status)

    def test_select_wifi_iface_auto(self) -> None:
        def exists_side_effect(name: str) -> bool:
            return name == "wlan1"

        with mock.patch("zeroterm_status.metrics._iface_exists", side_effect=exists_side_effect):
            with mock.patch("zeroterm_status.metrics.list_wifi_ifaces", return_value=["wlan1"]):
                iface = metrics.select_wifi_iface("wlan0", True)
        self.assertEqual(iface, "wlan1")

    def test_find_external_wifi(self) -> None:
        with mock.patch("zeroterm_status.metrics.list_wifi_ifaces", return_value=["wlan0", "wlan1"]):
            self.assertEqual(metrics.find_external_wifi("wlan0"), "wlan1")

    def test_read_wifi_missing(self) -> None:
        with mock.patch("zeroterm_status.metrics._iface_exists", return_value=False):
            info = metrics.read_wifi("wlan9")
        self.assertEqual(info.state, "missing")

    def test_read_wifi_with_data(self) -> None:
        with mock.patch("zeroterm_status.metrics._iface_exists", return_value=True):
            with mock.patch("zeroterm_status.metrics._read_operstate", return_value="up"):
                with mock.patch("zeroterm_status.metrics._read_ssid", return_value="TEST"):
                    with mock.patch("zeroterm_status.metrics.get_ip_address", return_value="10.0.0.5"):
                        with mock.patch(
                            "zeroterm_status.metrics._read_wifi_mode_channel",
                            return_value=("managed", "11"),
                        ):
                            with mock.patch(
                                "zeroterm_status.metrics._read_packet_count",
                                return_value=1234,
                            ):
                                info = metrics.read_wifi("wlan0")
        self.assertEqual(info.state, "up")
        self.assertEqual(info.ssid, "TEST")
        self.assertEqual(info.ip, "10.0.0.5")
        self.assertEqual(info.mode, "managed")
        self.assertEqual(info.channel, "11")
        self.assertEqual(info.packets, 1234)

    def test_read_time_sync_yes(self) -> None:
        with mock.patch("zeroterm_status.metrics.shutil.which", return_value="/bin/timedatectl"):
            with mock.patch("zeroterm_status.metrics._run_command", return_value="yes"):
                self.assertTrue(metrics.read_time_sync())

    def test_read_time_sync_no(self) -> None:
        with mock.patch("zeroterm_status.metrics.shutil.which", return_value="/bin/timedatectl"):
            with mock.patch("zeroterm_status.metrics._run_command", return_value="no"):
                self.assertFalse(metrics.read_time_sync())

    def test_read_update_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("zeroterm_status.metrics.shutil.which", return_value="/bin/git"):
                with mock.patch("zeroterm_status.metrics._run_command", return_value="2"):
                    self.assertTrue(
                        metrics.read_update_available(temp_dir, "origin", "main", fetch=False)
                    )
