from __future__ import annotations

import logging
import time
from datetime import datetime

from .config import load_config
from .display import create_display
from .drivers.base import DisplayError
from .drivers.file import FileDisplay
from .drivers.null import NullDisplay
from .metrics import find_external_wifi, read_battery, read_service_state, read_system, read_wifi, select_wifi_iface
from .render import RenderConfig, render_status

logger = logging.getLogger(__name__)


def _format_status(service_state: str | None) -> str:
    if service_state == "active":
        return "RUNNING"
    if service_state in {"inactive", "failed"}:
        return "DOWN"
    return "READY"


def _format_wifi(wifi_state: str | None) -> str:
    if wifi_state is None:
        return "UNKNOWN"
    return wifi_state.upper()


def _format_battery(percent: int | None, status: str | None) -> str:
    if percent is None:
        return "--"
    if status:
        return f"{percent}% {status.upper()}"
    return f"{percent}%"


def _is_night(now: datetime, start: int, end: int) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= now.hour < end
    return now.hour >= start or now.hour < end


def _select_interval(config, battery_percent: int | None) -> int:
    interval = config.interval
    now = datetime.now()
    if config.night_interval > 0 and _is_night(now, config.night_start, config.night_end):
        interval = max(interval, config.night_interval)
    if (
        battery_percent is not None
        and config.low_battery_threshold > 0
        and config.low_battery_interval > 0
        and battery_percent <= config.low_battery_threshold
    ):
        interval = max(interval, config.low_battery_interval)
    return interval


def build_payload(service_state: str | None, wifi, battery) -> tuple[str, str, str, str]:
    status = _format_status(service_state)
    ip = wifi.ip or "--"
    wifi_state = _format_wifi(wifi.state)
    wifi_text = wifi_state
    if wifi.ssid:
        wifi_text = f"{wifi_text} {wifi.ssid}"
    battery_text = _format_battery(battery.percent, battery.status)
    return status, ip, wifi_text, battery_text


def main() -> None:
    config = load_config()
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    display = create_display(config)
    try:
        display.init()
    except DisplayError as exc:
        logger.error("Display init failed: %s", exc)
        if config.epaper_output:
            display = FileDisplay(
                config.epaper_width,
                config.epaper_height,
                config.epaper_output,
            )
            display.init()
        else:
            display = NullDisplay(config.epaper_width, config.epaper_height)

    width = display.width or config.epaper_width
    height = display.height or config.epaper_height
    render_config = RenderConfig(
        width=width,
        height=height,
        rotate=config.epaper_rotate,
        font_path=config.font_path,
        font_size=config.font_size,
    )

    last_payload = None
    next_render_attempt = 0.0
    render_failures = 0
    last_wifi = None
    last_wifi_at = 0.0
    last_service = None
    last_service_at = 0.0
    last_system = None
    last_system_at = 0.0

    while True:
        interval = config.interval
        payload = None
        try:
            now = time.monotonic()
            iface = select_wifi_iface(config.iface, config.iface_auto)
            if (
                config.wifi_interval > 0
                and last_wifi is not None
                and now - last_wifi_at < config.wifi_interval
                and last_wifi.iface == iface
            ):
                wifi = last_wifi
            else:
                wifi = read_wifi(iface, read_ssid=config.wifi_ssid)
                last_wifi = wifi
                last_wifi_at = now

            if (
                config.service_interval > 0
                and last_service is not None
                and now - last_service_at < config.service_interval
            ):
                service = last_service
            else:
                service = read_service_state(config.service_name)
                last_service = service
                last_service_at = now

            battery = read_battery(config.battery_path, config.battery_cmd)

            if (
                config.metrics_interval > 0
                and last_system is not None
                and now - last_system_at < config.metrics_interval
            ):
                system = last_system
            else:
                system = read_system()
                last_system = system
                last_system_at = now
            status, ip, wifi_text, battery_text = build_payload(service.state, wifi, battery)
            external_iface = find_external_wifi(iface)
            temp_text = system.temp or "--"
            load_text = system.load or "--"
            uptime_text = system.uptime or "--"
            mem_text = f"{system.mem_percent}%" if system.mem_percent is not None else "--"
            cpu_text = f"{system.cpu_percent}%" if system.cpu_percent is not None else "--"
            interval = _select_interval(config, battery.percent)
            payload = "\n".join(
                [
                    status,
                    ip,
                    wifi_text,
                    battery_text,
                    external_iface or "--",
                    temp_text,
                    load_text,
                    uptime_text,
                    mem_text,
                    cpu_text,
                ]
            )
            now = time.monotonic()
            if payload != last_payload and now >= next_render_attempt:
                try:
                    image = render_status(
                        status=status,
                        ip=ip,
                        wifi=wifi_text,
                        battery=battery_text,
                        adapter=external_iface,
                        temp=temp_text,
                        load=load_text,
                        uptime=uptime_text,
                        mem=mem_text,
                        cpu=cpu_text,
                        battery_percent=battery.percent,
                        updated=None,
                        config=render_config,
                    )
                except RuntimeError as exc:
                    render_failures += 1
                    backoff = min(60, max(interval, 5) * render_failures)
                    next_render_attempt = now + backoff
                    logger.error("Render failed (backoff %ss): %s", backoff, exc)
                    continue
                render_failures = 0
                next_render_attempt = 0.0
                try:
                    display.show(image)
                except DisplayError as exc:
                    logger.error("Display update failed: %s", exc)
                    try:
                        display.init()
                    except DisplayError as init_exc:
                        logger.error("Display re-init failed: %s", init_exc)
                last_payload = payload
        except Exception:
            logger.exception("Status update failed")
        if payload is not None and config.idle_interval > 0 and last_payload == payload:
            interval = max(interval, config.idle_interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
