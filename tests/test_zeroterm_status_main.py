from __future__ import annotations

import unittest
from unittest import mock
from datetime import datetime as real_datetime

from zeroterm_status import main


class FixedLateNight:
    @staticmethod
    def now():
        return real_datetime(2024, 1, 1, 23, 30)


class TestStatusMainHelpers(unittest.TestCase):
    def test_is_night_wrap(self) -> None:
        late = real_datetime(2024, 1, 1, 23, 0)
        early = real_datetime(2024, 1, 2, 5, 0)
        day = real_datetime(2024, 1, 1, 12, 0)
        self.assertTrue(main._is_night(late, 22, 6))
        self.assertTrue(main._is_night(early, 22, 6))
        self.assertFalse(main._is_night(day, 22, 6))

    def test_select_interval_prefers_night_and_low_battery(self) -> None:
        config = type(
            "Cfg",
            (),
            {
                "interval": 10,
                "night_start": 22,
                "night_end": 6,
                "night_interval": 60,
                "low_battery_threshold": 20,
                "low_battery_interval": 120,
            },
        )()
        with mock.patch("zeroterm_status.main.datetime", FixedLateNight):
            interval = main._select_interval(config, 15)
        self.assertEqual(interval, 120)

    def test_format_power_state(self) -> None:
        self.assertEqual(main._format_power_state("Charging"), "CHG")
        self.assertEqual(main._format_power_state("Discharging"), "DIS")
        self.assertEqual(main._format_power_state("Full"), "FULL")
        self.assertEqual(main._format_power_state("Unknown"), "UNK")
