from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from zerotermd import server


class TestServerHelpers(unittest.TestCase):
    def test_sanitize_session_id(self) -> None:
        self.assertEqual(server._sanitize_session_id("abc-123_DEF"), "abc-123_DEF")
        self.assertIsNone(server._sanitize_session_id("bad id"))
        self.assertIsNone(server._sanitize_session_id("bad!"))
        self.assertIsNone(server._sanitize_session_id(""))
        self.assertIsNone(server._sanitize_session_id("a" * 65))

    def test_extract_session_id(self) -> None:
        self.assertEqual(server._extract_session_id("/ws?session=abc123"), "abc123")
        self.assertIsNone(server._extract_session_id("/wrong?session=abc123"))

    def test_make_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SimpleNamespace(session_log_dir=Path(temp_dir))
            with mock.patch("zerotermd.server.time.strftime", return_value="20200101-000000"):
                path = server._make_log_path(config, "sess", 42)
        self.assertIsNotNone(path)
        self.assertIn("zeroterm-session-20200101-000000-sess-42.log", str(path))
