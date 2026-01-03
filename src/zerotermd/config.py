from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shlex


@dataclass(frozen=True)
class Config:
    bind: str
    port: int
    shell: str
    shell_cmd: list[str] | None
    term: str
    cwd: str | None
    log_level: str
    static_dir: Path
    env_path: Path
    session_log_dir: Path | None
    session_resume: bool
    session_ttl: int


def _env_value(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    root_dir = Path(__file__).resolve().parents[2]
    static_dir = Path(_env_value("ZEROTERM_STATIC_DIR", str(root_dir / "web"))).resolve()
    env_path = Path(_env_value("ZEROTERM_ENV_PATH", "/etc/zeroterm/zeroterm.env")).expanduser().resolve()

    bind = _env_value("ZEROTERM_BIND", "0.0.0.0")
    port_value = _env_value("ZEROTERM_PORT", "8080")
    try:
        port = int(port_value)
    except ValueError:
        port = 8080
    shell = _env_value("ZEROTERM_SHELL", "/bin/bash")
    shell_cmd_value = os.environ.get("ZEROTERM_SHELL_CMD", "")
    shell_cmd = None
    if shell_cmd_value:
        try:
            shell_cmd = shlex.split(shell_cmd_value)
        except ValueError:
            shell_cmd = None
    if shell_cmd == []:
        shell_cmd = None
    term = _env_value("ZEROTERM_TERM", "linux")
    cwd = os.environ.get("ZEROTERM_CWD")
    if cwd == "":
        cwd = None
    log_level = _env_value("ZEROTERM_LOG_LEVEL", "info").lower()

    session_log_dir_value = _env_value("ZEROTERM_SESSION_LOG_DIR", "")
    session_log_dir = (
        Path(session_log_dir_value).expanduser().resolve()
        if session_log_dir_value
        else None
    )
    session_resume = _env_bool("ZEROTERM_SESSION_RESUME", True)
    session_ttl = max(0, _env_int("ZEROTERM_SESSION_TTL", 60))

    return Config(
        bind=bind,
        port=port,
        shell=shell,
        shell_cmd=shell_cmd,
        term=term,
        cwd=cwd,
        log_level=log_level,
        static_dir=static_dir,
        env_path=env_path,
        session_log_dir=session_log_dir,
        session_resume=session_resume,
        session_ttl=session_ttl,
    )
