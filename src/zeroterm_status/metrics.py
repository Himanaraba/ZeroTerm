from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fcntl
import re
import shutil
import shlex
import socket
import struct
import subprocess


@dataclass(frozen=True)
class BatteryInfo:
    percent: int | None
    status: str | None


@dataclass(frozen=True)
class WifiInfo:
    iface: str
    state: str | None
    ssid: str | None
    ip: str | None


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    state: str | None


def _run_command(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except OSError:
        return None
    output = result.stdout.strip()
    return output if output else None


def _parse_percent(text: str) -> int | None:
    match = re.search(r"(\d{1,3})", text)
    if not match:
        return None
    value = int(match.group(1))
    if value < 0 or value > 100:
        return None
    return value


def read_battery(battery_path: str | None, battery_cmd: str | None) -> BatteryInfo:
    if battery_cmd:
        cmd = shlex.split(battery_cmd)
        if not cmd or shutil.which(cmd[0]) is None:
            return BatteryInfo(percent=None, status=None)
        output = _run_command(cmd)
        if output:
            return BatteryInfo(percent=_parse_percent(output), status=None)

    search_root = Path(battery_path) if battery_path else Path("/sys/class/power_supply")
    if not search_root.exists():
        return BatteryInfo(percent=None, status=None)

    for entry in search_root.iterdir():
        capacity = entry / "capacity"
        power_type = entry / "type"
        status_file = entry / "status"
        if not capacity.exists():
            continue
        if power_type.exists():
            type_value = power_type.read_text(encoding="utf-8", errors="ignore").strip().lower()
            if type_value and type_value != "battery":
                continue
        try:
            percent_text = capacity.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        percent = _parse_percent(percent_text)
        status = None
        if status_file.exists():
            try:
                status = status_file.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                status = None
        return BatteryInfo(percent=percent, status=status)

    return BatteryInfo(percent=None, status=None)


def _iface_exists(iface: str) -> bool:
    return (Path("/sys/class/net") / iface).exists()


def get_ip_address(iface: str) -> str | None:
    if not iface:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        iface_bytes = iface.encode("utf-8")[:15]
        request = struct.pack("256s", iface_bytes)
        response = fcntl.ioctl(sock.fileno(), 0x8915, request)
        return socket.inet_ntoa(response[20:24])
    except OSError:
        return None
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _read_operstate(iface: str) -> str | None:
    path = Path("/sys/class/net") / iface / "operstate"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None


def _read_ssid(iface: str) -> str | None:
    if shutil.which("iwgetid") is None:
        return None
    output = _run_command(["iwgetid", iface, "-r"])
    return output


def read_wifi(iface: str) -> WifiInfo:
    if not iface:
        return WifiInfo(iface=iface, state=None, ssid=None, ip=None)
    if not _iface_exists(iface):
        return WifiInfo(iface=iface, state="missing", ssid=None, ip=None)
    state = _read_operstate(iface)
    ssid = _read_ssid(iface)
    ip = get_ip_address(iface)
    return WifiInfo(iface=iface, state=state, ssid=ssid, ip=ip)


def read_service_state(name: str) -> ServiceInfo:
    if not name:
        return ServiceInfo(name=name, state=None)
    if shutil.which("systemctl") is None:
        return ServiceInfo(name=name, state=None)
    output = _run_command(["systemctl", "is-active", name])
    return ServiceInfo(name=name, state=output)
