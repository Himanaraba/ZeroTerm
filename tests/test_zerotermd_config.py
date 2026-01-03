from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import temp_env
from zerotermd.config import load_config


class TestZerotermdConfig(unittest.TestCase):
    def test_load_config_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with temp_env(
                {
                    "ZEROTERM_BIND": "127.0.0.1",
                    "ZEROTERM_PORT": "9001",
                    "ZEROTERM_SHELL": "/bin/zsh",
                    "ZEROTERM_SHELL_CMD": "tmux new -A -s zeroterm",
                    "ZEROTERM_TERM": "xterm-256color",
                    "ZEROTERM_CWD": "/tmp",
                    "ZEROTERM_LOG_LEVEL": "debug",
                    "ZEROTERM_STATIC_DIR": temp_dir,
                    "ZEROTERM_SESSION_LOG_DIR": temp_dir,
                    "ZEROTERM_SESSION_RESUME": "0",
                    "ZEROTERM_SESSION_TTL": "120",
                }
            ):
                config = load_config()
            self.assertEqual(config.bind, "127.0.0.1")
            self.assertEqual(config.port, 9001)
            self.assertEqual(config.shell, "/bin/zsh")
            self.assertEqual(config.shell_cmd, ["tmux", "new", "-A", "-s", "zeroterm"])
            self.assertEqual(config.term, "xterm-256color")
            self.assertEqual(config.cwd, "/tmp")
            self.assertEqual(config.log_level, "debug")
            self.assertEqual(config.static_dir, Path(temp_dir).resolve())
            self.assertEqual(config.session_log_dir, Path(temp_dir).resolve())
            self.assertFalse(config.session_resume)
            self.assertEqual(config.session_ttl, 120)

    def test_invalid_port_falls_back(self) -> None:
        with temp_env({"ZEROTERM_PORT": "not-a-number"}):
            config = load_config()
        self.assertEqual(config.port, 8080)
