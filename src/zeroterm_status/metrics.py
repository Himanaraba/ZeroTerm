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


@dataclass(frozen=True)
class SystemInfo:
    uptime: str | None
    load: str | None
    temp: str | None
    mem_percent: int | None
    cpu_percent: int | None


_CPU_SAMPLE: tuple[int, int] | None = None
_COMMAND_TIMEOUT = 3.0


def _run_command(args: list[str]) -> str | None:
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=_COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
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


def list_wifi_ifaces() -> list[str]:
    root = Path("/sys/class/net")
    if not root.exists():
        return []
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and entry.name.startswith("wlan")
    )


def select_wifi_iface(preferred: str, auto: bool) -> str:
    if preferred and _iface_exists(preferred):
        return preferred
    if not auto:
        return preferred
    for iface in list_wifi_ifaces():
        if _iface_exists(iface):
            return iface
    return preferred


def find_external_wifi(primary_iface: str | None) -> str | None:
    ifaces = list_wifi_ifaces()
    if not ifaces:
        return None
    if primary_iface and primary_iface in ifaces:
        extras = [iface for iface in ifaces if iface != primary_iface]
        return extras[0] if extras else None
    if len(ifaces) > 1:
        return ifaces[0]
    return None


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


def read_wifi(iface: str, read_ssid: bool = True) -> WifiInfo:
    if not iface:
        return WifiInfo(iface=iface, state=None, ssid=None, ip=None)
    if not _iface_exists(iface):
        return WifiInfo(iface=iface, state="missing", ssid=None, ip=None)
    state = _read_operstate(iface)
    ssid = _read_ssid(iface) if read_ssid else None
    ip = get_ip_address(iface)
    return WifiInfo(iface=iface, state=state, ssid=ssid, ip=ip)


def read_service_state(name: str) -> ServiceInfo:
    if not name:
        return ServiceInfo(name=name, state=None)
    if shutil.which("systemctl") is None:
        return ServiceInfo(name=name, state=None)
    output = _run_command(["systemctl", "is-active", name])
    return ServiceInfo(name=name, state=output)


def _format_uptime(seconds: float) -> str:
    minutes = int(seconds // 60)
    days, rem = divmod(minutes, 24 * 60)
    hours, minutes = divmod(rem, 60)
    if days > 0:
        return f"{days}d{hours}h"
    if hours > 0:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def _read_file_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None


def read_uptime() -> str | None:
    text = _read_file_text(Path("/proc/uptime"))
    if not text:
        return None
    try:
        seconds = float(text.split()[0])
    except (ValueError, IndexError):
        return None
    return _format_uptime(seconds)


def read_load() -> str | None:
    text = _read_file_text(Path("/proc/loadavg"))
    if not text:
        return None
    try:
        load_value = float(text.split()[0])
    except (ValueError, IndexError):
        return None
    return f"{load_value:.2f}"


def _parse_temp_value(raw: str) -> str | None:
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    if value > 1000:
        value = int(round(value / 1000))
    if value < -20 or value > 150:
        return None
    return f"{value}C"


def read_temperature() -> str | None:
    root = Path("/sys/class/thermal")
    if not root.exists():
        return None
    for path in sorted(root.glob("thermal_zone*/temp")):
        text = _read_file_text(path)
        if not text:
            continue
        parsed = _parse_temp_value(text)
        if parsed:
            return parsed
    return None


def read_memory_percent() -> int | None:
    text = _read_file_text(Path("/proc/meminfo"))
    if not text:
        return None
    total = None
    available = None
    free = None
    buffers = None
    cached = None
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            total = _parse_kib(line)
        elif line.startswith("MemAvailable:"):
            available = _parse_kib(line)
        elif line.startswith("MemFree:"):
            free = _parse_kib(line)
        elif line.startswith("Buffers:"):
            buffers = _parse_kib(line)
        elif line.startswith("Cached:"):
            cached = _parse_kib(line)
    if total is None or total <= 0:
        return None
    if available is None:
        if free is None:
            return None
        buffers = buffers or 0
        cached = cached or 0
        available = free + buffers + cached
    used = max(0, total - available)
    percent = int(round(used * 100 / total))
    return max(0, min(100, percent))


def _parse_kib(line: str) -> int | None:
    match = re.search(r"(\d+)", line)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def read_cpu_percent() -> int | None:
    global _CPU_SAMPLE
    text = _read_file_text(Path("/proc/stat"))
    if not text:
        return None
    line = text.splitlines()[0] if text else ""
    parts = line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return None
    try:
        values = [int(value) for value in parts[1:]]
    except ValueError:
        return None
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    if total <= 0:
        return None
    if _CPU_SAMPLE is None:
        _CPU_SAMPLE = (total, idle)
        return None
    delta_total = total - _CPU_SAMPLE[0]
    delta_idle = idle - _CPU_SAMPLE[1]
    _CPU_SAMPLE = (total, idle)
    if delta_total <= 0:
        return None
    usage = int(round((delta_total - delta_idle) * 100 / delta_total))
    return max(0, min(100, usage))


def read_system() -> SystemInfo:
    return SystemInfo(
        uptime=read_uptime(),
        load=read_load(),
        temp=read_temperature(),
        mem_percent=read_memory_percent(),
        cpu_percent=read_cpu_percent(),
    )
