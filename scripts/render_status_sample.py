#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from zeroterm_status.config import load_config
from zeroterm_status.render import RenderConfig, render_status


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


def _build_live_payload(config):
    from zeroterm_status.metrics import (
        find_external_wifi,
        read_battery,
        read_service_state,
        read_system,
        read_wifi,
        select_wifi_iface,
    )

    iface = select_wifi_iface(config.iface, config.iface_auto)
    wifi = read_wifi(iface, read_ssid=config.wifi_ssid)
    battery = read_battery(config.battery_path, config.battery_cmd)
    system = read_system()
    service = read_service_state(config.service_name)
    external_iface = find_external_wifi(iface)

    status = _format_status(service.state)
    ip = wifi.ip or "--"
    wifi_state = _format_wifi(wifi.state)
    wifi_text = wifi_state
    if wifi.ssid:
        wifi_text = f"{wifi_text} {wifi.ssid}"
    battery_text = _format_battery(battery.percent, battery.status)

    temp_text = system.temp or "--"
    load_text = system.load or "--"
    uptime_text = system.uptime or "--"
    mem_text = f"{system.mem_percent}%" if system.mem_percent is not None else "--"
    cpu_text = f"{system.cpu_percent}%" if system.cpu_percent is not None else "--"

    return (
        status,
        ip,
        wifi_text,
        battery_text,
        external_iface,
        "CHG" if battery.status and "charg" in battery.status.lower() else None,
        None,
        temp_text,
        load_text,
        uptime_text,
        mem_text,
        cpu_text,
        battery.percent,
        wifi.channel,
        wifi.packets,
    )


def _build_sample_payload():
    return (
        "RUNNING",
        "10.0.0.12",
        "UP ZEROTERM-LAB",
        "67% CHARGING",
        "wlan1",
        "CHG",
        "UPD",
        "44C",
        "0.42",
        "3h12m",
        "58%",
        "12%",
        67,
        "11",
        12458,
    )


def _resolve_output(path_arg: str | None) -> Path:
    if path_arg:
        return Path(path_arg).expanduser().resolve()
    return Path(tempfile.gettempdir()) / "zeroterm_epaper_sample.png"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a ZeroTerm e-paper status PNG without hardware."
    )
    parser.add_argument(
        "--output",
        help="Output PNG path (default: OS temp directory).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live system metrics when available.",
    )
    args = parser.parse_args()

    config = load_config()
    render_config = RenderConfig(
        width=config.epaper_width,
        height=config.epaper_height,
        rotate=config.epaper_rotate,
        font_path=config.font_path,
        font_size=config.font_size,
    )

    if args.live:
        payload = _build_live_payload(config)
    else:
        payload = _build_sample_payload()

    output_path = _resolve_output(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        image = render_status(
            status=payload[0],
            ip=payload[1],
            wifi=payload[2],
            battery=payload[3],
            adapter=payload[4],
            power=payload[5],
            alert=payload[6],
            temp=payload[7],
            load=payload[8],
            uptime=payload[9],
            mem=payload[10],
            cpu=payload[11],
            battery_percent=payload[12],
            updated=None,
            config=render_config,
            wifi_channel=payload[13],
            wifi_packets=payload[14],
        )
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        print("[hint] Install Pillow: python3 -m pip install Pillow", file=sys.stderr)
        return 1

    image.save(output_path, format="PNG")
    print(f"[ok] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
