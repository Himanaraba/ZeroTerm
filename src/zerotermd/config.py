from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Config:
    bind: str
    port: int
    shell: str
    term: str
    cwd: str | None
    log_level: str
    static_dir: Path


def _env_value(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def load_config() -> Config:
    root_dir = Path(__file__).resolve().parents[2]
    static_dir = Path(_env_value("ZEROTERM_STATIC_DIR", str(root_dir / "web"))).resolve()

    bind = _env_value("ZEROTERM_BIND", "0.0.0.0")
    port_value = _env_value("ZEROTERM_PORT", "8080")
    try:
        port = int(port_value)
    except ValueError:
        port = 8080
    shell = _env_value("ZEROTERM_SHELL", "/bin/bash")
    term = _env_value("ZEROTERM_TERM", "linux")
    cwd = os.environ.get("ZEROTERM_CWD")
    if cwd == "":
        cwd = None
    log_level = _env_value("ZEROTERM_LOG_LEVEL", "info").lower()

    return Config(
        bind=bind,
        port=port,
        shell=shell,
        term=term,
        cwd=cwd,
        log_level=log_level,
        static_dir=static_dir,
    )
