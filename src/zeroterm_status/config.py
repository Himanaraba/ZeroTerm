from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class StatusConfig:
    interval: int
    iface: str
    service_name: str
    epaper_driver: str
    epaper_model: str
    epaper_rotate: int
    epaper_width: int
    epaper_height: int
    epaper_lib: str | None
    epaper_output: str | None
    font_path: str | None
    font_size: int
    battery_path: str | None
    battery_cmd: str | None
    log_level: str


def _env(name: str, default: str) -> str:
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


def _env_path(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return value


def load_config() -> StatusConfig:
    interval = max(5, _env_int("ZEROTERM_STATUS_INTERVAL", 30))
    iface = _env("ZEROTERM_STATUS_IFACE", "wlan0")
    service_name = _env("ZEROTERM_STATUS_SERVICE", "zeroterm.service")

    epaper_driver = _env("ZEROTERM_EPAPER_DRIVER", "waveshare")
    epaper_model = _env("ZEROTERM_EPAPER_MODEL", "epd2in13_V3")
    epaper_rotate = _env_int("ZEROTERM_EPAPER_ROTATE", 0)
    if epaper_rotate not in {0, 90, 180, 270}:
        epaper_rotate = 0
    epaper_width = _env_int("ZEROTERM_EPAPER_WIDTH", 250)
    epaper_height = _env_int("ZEROTERM_EPAPER_HEIGHT", 122)
    epaper_lib = _env_path("ZEROTERM_EPAPER_LIB")
    epaper_output = _env_path("ZEROTERM_EPAPER_OUTPUT")

    font_path = _env_path("ZEROTERM_EPAPER_FONT_PATH")
    font_size = _env_int("ZEROTERM_EPAPER_FONT_SIZE", 14)

    battery_path = _env_path("ZEROTERM_BATTERY_PATH")
    battery_cmd = _env_path("ZEROTERM_BATTERY_CMD")

    log_level = _env("ZEROTERM_LOG_LEVEL", "info").lower()

    return StatusConfig(
        interval=interval,
        iface=iface,
        service_name=service_name,
        epaper_driver=epaper_driver,
        epaper_model=epaper_model,
        epaper_rotate=epaper_rotate,
        epaper_width=epaper_width,
        epaper_height=epaper_height,
        epaper_lib=epaper_lib,
        epaper_output=epaper_output,
        font_path=font_path,
        font_size=font_size,
        battery_path=battery_path,
        battery_cmd=battery_cmd,
        log_level=log_level,
    )
