from __future__ import annotations

import os
import sys
import types
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

if os.name == "nt":
    if "fcntl" not in sys.modules:
        fcntl_stub = types.ModuleType("fcntl")
        fcntl_stub.ioctl = lambda *args, **kwargs: b""
        sys.modules["fcntl"] = fcntl_stub
    if "pty" not in sys.modules:
        pty_stub = types.ModuleType("pty")

        def _unsupported(*args, **kwargs):
            raise NotImplementedError("pty is not available on Windows")

        pty_stub.fork = _unsupported
        sys.modules["pty"] = pty_stub
    if "termios" not in sys.modules:
        termios_stub = types.ModuleType("termios")
        termios_stub.TIOCSWINSZ = 0x5414
        sys.modules["termios"] = termios_stub
