from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zerotermd import http_utils


class TestHttpUtils(unittest.TestCase):
    def test_resolve_path_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            index = base / "index.html"
            index.write_text("ok", encoding="utf-8")
            resolved = http_utils._resolve_path("/", base)
            self.assertEqual(resolved, index)

    def test_resolve_path_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            resolved = http_utils._resolve_path("/../../etc/passwd", base)
            self.assertIsNone(resolved)
