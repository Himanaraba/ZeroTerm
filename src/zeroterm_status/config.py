from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class StatusConfig:
    interval: int
    iface: str
    iface_auto: bool
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
    night_start: int
    night_end: int
    night_interval: int
    low_battery_threshold: int
    low_battery_interval: int
    wifi_interval: int
    service_interval: int
    metrics_interval: int
    idle_interval: int
    wifi_ssid: bool
    battery_log_path: str | None
    battery_log_interval: int
    power_log_path: str | None
    update_check: bool
    update_interval: int
    update_path: str | None
    update_remote: str
    update_branch: str
    update_fetch: bool


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


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_path(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return value


def load_config() -> StatusConfig:
    profile = _env("ZEROTERM_STATUS_PROFILE", "").strip().lower()
    interval = max(5, _env_int("ZEROTERM_STATUS_INTERVAL", 30))
    iface = _env("ZEROTERM_STATUS_IFACE", "wlan0")
    iface_auto = _env_bool("ZEROTERM_STATUS_IFACE_AUTO", False)
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

    night_start = _env_int("ZEROTERM_STATUS_NIGHT_START", 22)
    if night_start < 0 or night_start > 23:
        night_start = 22
    night_end = _env_int("ZEROTERM_STATUS_NIGHT_END", 6)
    if night_end < 0 or night_end > 23:
        night_end = 6
    night_interval = max(0, _env_int("ZEROTERM_STATUS_NIGHT_INTERVAL", 0))
    low_battery_threshold = max(0, min(100, _env_int("ZEROTERM_STATUS_LOW_BATTERY", 0)))
    low_battery_interval = max(0, _env_int("ZEROTERM_STATUS_LOW_BATTERY_INTERVAL", 0))
    wifi_interval = max(0, _env_int("ZEROTERM_STATUS_WIFI_INTERVAL", 0))
    service_interval = max(0, _env_int("ZEROTERM_STATUS_SERVICE_INTERVAL", 0))
    metrics_interval = max(0, _env_int("ZEROTERM_STATUS_METRICS_INTERVAL", 0))
    idle_interval = max(0, _env_int("ZEROTERM_STATUS_IDLE_INTERVAL", 0))
    wifi_ssid = _env_bool("ZEROTERM_STATUS_WIFI_SSID", True)

    battery_log_path = _env_path("ZEROTERM_BATTERY_LOG_PATH")
    battery_log_interval = max(0, _env_int("ZEROTERM_BATTERY_LOG_INTERVAL", 0))
    power_log_path = _env_path("ZEROTERM_POWER_LOG_PATH")
    update_check = _env_bool("ZEROTERM_UPDATE_CHECK", False)
    update_interval = max(0, _env_int("ZEROTERM_UPDATE_INTERVAL", 3600))
    update_path = _env_path("ZEROTERM_UPDATE_PATH") or "/opt/zeroterm"
    update_remote = _env("ZEROTERM_UPDATE_REMOTE", "origin")
    update_branch = _env("ZEROTERM_UPDATE_BRANCH", "main")
    update_fetch = _env_bool("ZEROTERM_UPDATE_FETCH", False)

    profile_map = {
        "eco": {
            "interval": 60,
            "wifi_interval": 120,
            "service_interval": 60,
            "metrics_interval": 300,
            "idle_interval": 180,
            "wifi_ssid": False,
            "night_interval": 300,
            "low_battery_threshold": 30,
            "low_battery_interval": 300,
        },
        "balanced": {
            "interval": 30,
            "wifi_interval": 30,
            "service_interval": 30,
            "metrics_interval": 60,
            "idle_interval": 60,
            "wifi_ssid": True,
        },
        "performance": {
            "interval": 10,
            "wifi_interval": 10,
            "service_interval": 10,
            "metrics_interval": 10,
            "idle_interval": 0,
            "wifi_ssid": True,
        },
    }

    if profile in profile_map:
        preset = profile_map[profile]
        if "ZEROTERM_STATUS_INTERVAL" not in os.environ:
            interval = max(5, preset.get("interval", interval))
        if "ZEROTERM_STATUS_WIFI_INTERVAL" not in os.environ:
            wifi_interval = max(0, preset.get("wifi_interval", wifi_interval))
        if "ZEROTERM_STATUS_SERVICE_INTERVAL" not in os.environ:
            service_interval = max(0, preset.get("service_interval", service_interval))
        if "ZEROTERM_STATUS_METRICS_INTERVAL" not in os.environ:
            metrics_interval = max(0, preset.get("metrics_interval", metrics_interval))
        if "ZEROTERM_STATUS_IDLE_INTERVAL" not in os.environ:
            idle_interval = max(0, preset.get("idle_interval", idle_interval))
        if "ZEROTERM_STATUS_WIFI_SSID" not in os.environ:
            wifi_ssid = bool(preset.get("wifi_ssid", wifi_ssid))
        if "ZEROTERM_STATUS_NIGHT_INTERVAL" not in os.environ:
            night_interval = max(0, preset.get("night_interval", night_interval))
        if "ZEROTERM_STATUS_LOW_BATTERY" not in os.environ:
            low_battery_threshold = max(
                0,
                min(100, preset.get("low_battery_threshold", low_battery_threshold)),
            )
        if "ZEROTERM_STATUS_LOW_BATTERY_INTERVAL" not in os.environ:
            low_battery_interval = max(
                0,
                preset.get("low_battery_interval", low_battery_interval),
            )

    return StatusConfig(
        interval=interval,
        iface=iface,
        iface_auto=iface_auto,
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
        night_start=night_start,
        night_end=night_end,
        night_interval=night_interval,
        low_battery_threshold=low_battery_threshold,
        low_battery_interval=low_battery_interval,
        wifi_interval=wifi_interval,
        service_interval=service_interval,
        metrics_interval=metrics_interval,
        idle_interval=idle_interval,
        wifi_ssid=wifi_ssid,
        battery_log_path=battery_log_path,
        battery_log_interval=battery_log_interval,
        power_log_path=power_log_path,
        update_check=update_check,
        update_interval=update_interval,
        update_path=update_path,
        update_remote=update_remote,
        update_branch=update_branch,
        update_fetch=update_fetch,
    )
