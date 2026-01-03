from __future__ import annotations

import unittest

from zeroterm_status.render import (
    RenderConfig,
    _battery_short,
    _pick_face,
    _short_wifi_state,
    _status_message,
    render_lines,
    render_status,
)


class TestRenderHelpers(unittest.TestCase):
    def test_short_wifi_state(self) -> None:
        self.assertEqual(_short_wifi_state("up"), "UP")
        self.assertEqual(_short_wifi_state("down"), "DN")
        self.assertEqual(_short_wifi_state(None), "UNK")

    def test_battery_short(self) -> None:
        self.assertEqual(_battery_short(50, "charging"), "50%C")
        self.assertEqual(_battery_short(100, "full"), "100%F")
        self.assertEqual(_battery_short(None, ""), "--")

    def test_status_message(self) -> None:
        self.assertEqual(_status_message("running"), "SESSION LIVE")
        self.assertEqual(_status_message("ready"), "WAITING FOR INPUT")
        self.assertEqual(_status_message("failed"), "SERVICE DOWN")

    def test_pick_face(self) -> None:
        self.assertEqual(_pick_face("running", 90), "(^_^)")
        self.assertEqual(_pick_face("ready", 90), "(^_~)")
        self.assertEqual(_pick_face("down", 90), "(x_x)")
        self.assertEqual(_pick_face("running", 10), "(T_T)")


class TestRenderOutput(unittest.TestCase):
    def test_render_lines(self) -> None:
        config = RenderConfig(width=250, height=122, rotate=0, font_path=None, font_size=14)
        try:
            image = render_lines(["HELLO", "WORLD"], config)
        except RuntimeError:
            self.skipTest("Pillow not available")
        self.assertEqual(image.size, (250, 122))

    def test_render_status(self) -> None:
        config = RenderConfig(width=250, height=122, rotate=0, font_path=None, font_size=14)
        try:
            image = render_status(
                status="RUNNING",
                ip="10.0.0.5",
                wifi="UP TEST",
                battery="55% CHARGING",
                adapter="wlan1",
                power="CHG",
                alert="UPD",
                temp="42C",
                load="0.42",
                uptime="1h2m",
                mem="50%",
                cpu="20%",
                battery_percent=55,
                updated=None,
                config=config,
            )
        except RuntimeError:
            self.skipTest("Pillow not available")
        self.assertEqual(image.size, (250, 122))
