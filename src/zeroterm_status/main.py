from __future__ import annotations

import logging
import time

from .config import load_config
from .display import create_display
from .drivers.base import DisplayError
from .drivers.file import FileDisplay
from .drivers.null import NullDisplay
from .metrics import read_battery, read_service_state, read_wifi
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
    render_failed = False

    while True:
        try:
            wifi = read_wifi(config.iface)
            battery = read_battery(config.battery_path, config.battery_cmd)
            service = read_service_state(config.service_name)
            status, ip, wifi_text, battery_text = build_payload(service.state, wifi, battery)
            payload = "\n".join([status, ip, wifi_text, battery_text])
            if payload != last_payload and not render_failed:
                try:
                    image = render_status(
                        status=status,
                        ip=ip,
                        wifi=wifi_text,
                        battery=battery_text,
                        updated=None,
                        config=render_config,
                    )
                except RuntimeError as exc:
                    logger.error("Render failed: %s", exc)
                    render_failed = True
                    continue
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
        time.sleep(config.interval)


if __name__ == "__main__":
    main()
