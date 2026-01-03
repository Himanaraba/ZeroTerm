from __future__ import annotations

import json
import logging
import os
import select
import shutil
import signal
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .config import Config
from .http_utils import read_http_request, send_response, serve_static
from .pty_session import resize_pty, spawn_pty
from .websocket import (
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_PING,
    OPCODE_TEXT,
    WebSocketBuffer,
    build_accept_key,
    build_binary_frame,
    build_close_frame,
    build_pong_frame,
)
logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    pid: int
    master_fd: int
    session_id: str | None
    persistent: bool
    log_path: Path | None


@dataclass
class StoredSession:
    pid: int
    master_fd: int
    attached: bool
    last_detach: float
    log_path: Path | None


_SESSIONS: dict[str, StoredSession] = {}
_SESSIONS_LOCK = threading.Lock()
_ENV_CACHE: dict[str, object] = {
    "path": None,
    "mtime": None,
    "data": {},
}
_ENV_CACHE_LOCK = threading.Lock()


def run_server(config: Config) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((config.bind, config.port))
        server.listen(32)
        logger.info("ZeroTerm listening on %s:%s", config.bind, config.port)
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=_handle_client,
                args=(conn, addr, config),
                daemon=True,
            )
            thread.start()


def _handle_client(conn: socket.socket, addr: tuple[str, int], config: Config) -> None:
    with conn:
        try:
            conn.settimeout(5.0)
            request = read_http_request(conn)
            conn.settimeout(None)
            if request is None:
                return

            if _is_websocket_request(request.headers):
                if request.method != "GET":
                    _send_text(conn, 405, b"Method Not Allowed")
                    return
                if not _is_ws_path(request.target):
                    _send_text(conn, 404, b"Not Found")
                    return
                session_id = _extract_session_id(request.target)
                if config.session_resume and session_id:
                    _prune_sessions(config.session_ttl)
                    if _session_is_attached(session_id):
                        _send_text(conn, 409, b"Session Busy")
                        return
                if not _websocket_handshake(conn, request.headers):
                    _send_text(conn, 400, b"Bad Request")
                    return
                logger.info("WebSocket connected from %s:%s", addr[0], addr[1])
                _run_ws_session(conn, config, session_id)
                return

            if _is_status_path(request.target):
                if request.method != "GET":
                    _send_text(conn, 405, b"Method Not Allowed")
                    return
                _handle_status_request(conn, config)
                return

            if _is_power_path(request.target):
                if request.method != "POST":
                    _send_text(conn, 405, b"Method Not Allowed")
                    return
                _handle_power_request(conn, config, request.body)
                return

            if request.method != "GET":
                _send_text(conn, 405, b"Method Not Allowed")
                return

            serve_static(conn, request.target, config.static_dir)
        except Exception:
            logger.exception("Client handling failed for %s:%s", addr[0], addr[1])


def _send_text(conn: socket.socket, status: int, body: bytes) -> None:
    send_response(
        conn,
        status,
        {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Length": str(len(body)),
        },
        body,
    )


def _send_json(conn: socket.socket, status: int, payload: dict[str, object]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    send_response(
        conn,
        status,
        {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
        },
        body,
    )


def _is_websocket_request(headers: dict[str, str]) -> bool:
    upgrade = headers.get("upgrade", "").lower() == "websocket"
    connection = headers.get("connection", "").lower()
    has_upgrade = "upgrade" in connection
    return upgrade and has_upgrade


def _is_ws_path(target: str) -> bool:
    return urlsplit(target).path == "/ws"


def _is_status_path(target: str) -> bool:
    return urlsplit(target).path == "/api/status"


def _is_power_path(target: str) -> bool:
    return urlsplit(target).path == "/api/power"


def _extract_session_id(target: str) -> str | None:
    parsed = urlsplit(target)
    if parsed.path != "/ws":
        return None
    params = parse_qs(parsed.query)
    raw = params.get("session", [None])[0]
    return _sanitize_session_id(raw)


def _sanitize_session_id(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not (1 <= len(value) <= 64):
        return None
    for char in value:
        if not (char.isalnum() or char in {"-", "_"}):
            return None
    return value


def _parse_env_text(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            data[key] = value
    return data


def _load_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    with _ENV_CACHE_LOCK:
        cached_path = _ENV_CACHE.get("path")
        cached_mtime = _ENV_CACHE.get("mtime")
        cached_data = _ENV_CACHE.get("data")
        if cached_path == path and cached_mtime == mtime and isinstance(cached_data, dict):
            return dict(cached_data)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    data = _parse_env_text(text)
    with _ENV_CACHE_LOCK:
        _ENV_CACHE["path"] = path
        _ENV_CACHE["mtime"] = mtime
        _ENV_CACHE["data"] = dict(data)
    return data


def _get_env_value(env_data: dict[str, str], key: str, default: str | None = None) -> str | None:
    value = env_data.get(key)
    if value is None or value == "":
        value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


def _get_env_bool(env_data: dict[str, str], key: str, default: bool) -> bool:
    value = _get_env_value(env_data, key, None)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _update_env_file(path: Path | None, key: str, value: str) -> bool:
    if path is None:
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    except FileNotFoundError:
        lines = []
    except OSError:
        return False

    updated = False
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        candidate = stripped
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        key_name = candidate.split("=", 1)[0].strip()
        if key_name != key:
            new_lines.append(line)
            continue
        new_lines.append(f"{key}={value}\n")
        updated = True
    if not updated:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] = new_lines[-1] + "\n"
        new_lines.append(f"{key}={value}\n")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text("".join(new_lines), encoding="utf-8")
        tmp_path.replace(path)
    except OSError:
        return False
    with _ENV_CACHE_LOCK:
        _ENV_CACHE["path"] = None
        _ENV_CACHE["mtime"] = None
        _ENV_CACHE["data"] = {}
    return True


def _format_power_state(status: str | None) -> str | None:
    if not status:
        return None
    value = status.strip().lower()
    if "discharg" in value:
        return "DIS"
    if "charg" in value:
        return "CHG"
    if "full" in value:
        return "FULL"
    if "not charging" in value:
        return "IDLE"
    if "unknown" in value:
        return "UNK"
    return value[:4].upper()


def _restart_status_service() -> bool:
    if shutil.which("systemctl") is None:
        return False
    try:
        result = subprocess.run(
            ["systemctl", "restart", "zeroterm-status.service"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _read_battery_snapshot(battery_path: str | None, battery_cmd: str | None) -> tuple[int | None, str | None]:
    try:
        from zeroterm_status.metrics import read_battery
    except Exception:
        return None, None
    info = read_battery(battery_path, battery_cmd)
    return info.percent, info.status


def _handle_status_request(conn: socket.socket, config: Config) -> None:
    env_data = _load_env_file(config.env_path)
    battery_path = _get_env_value(env_data, "ZEROTERM_BATTERY_PATH")
    battery_cmd = _get_env_value(env_data, "ZEROTERM_BATTERY_CMD")
    profile = _get_env_value(env_data, "ZEROTERM_STATUS_PROFILE")
    wifi_iface = _get_env_value(env_data, "ZEROTERM_STATUS_IFACE", "wlan0") or "wlan0"
    wifi_auto = _get_env_bool(env_data, "ZEROTERM_STATUS_IFACE_AUTO", False)
    wifi_ssid = _get_env_bool(env_data, "ZEROTERM_STATUS_WIFI_SSID", True)

    battery_percent, battery_status = _read_battery_snapshot(battery_path, battery_cmd)
    power_state = _format_power_state(battery_status)
    wifi_payload: dict[str, object] = {
        "wifi_iface": wifi_iface,
        "wifi_state": None,
        "wifi_ssid": None,
        "wifi_mode": None,
        "wifi_channel": None,
        "wifi_packets": None,
        "wifi_ip": None,
    }
    try:
        from zeroterm_status.metrics import read_wifi, select_wifi_iface

        selected_iface = select_wifi_iface(wifi_iface, wifi_auto)
        wifi = read_wifi(selected_iface, read_ssid=wifi_ssid)
        wifi_payload = {
            "wifi_iface": wifi.iface,
            "wifi_state": wifi.state,
            "wifi_ssid": wifi.ssid,
            "wifi_mode": wifi.mode,
            "wifi_channel": wifi.channel,
            "wifi_packets": wifi.packets,
            "wifi_ip": wifi.ip,
        }
    except Exception:
        pass
    payload = {
        "battery_percent": battery_percent,
        "battery_status": battery_status,
        "power_state": power_state,
        "profile": profile or None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    payload.update(wifi_payload)
    _send_json(conn, 200, payload)


def _normalize_profile(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"default", "none", "off"}:
        return ""
    if normalized in {"eco", "balanced", "performance"}:
        return normalized
    return None


def _handle_power_request(conn: socket.socket, config: Config, body: bytes) -> None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        _send_json(conn, 400, {"ok": False, "error": "invalid json"})
        return
    profile = _normalize_profile(payload.get("profile") if isinstance(payload, dict) else None)
    if profile is None:
        _send_json(conn, 400, {"ok": False, "error": "invalid profile"})
        return
    if not _update_env_file(config.env_path, "ZEROTERM_STATUS_PROFILE", profile):
        _send_json(conn, 500, {"ok": False, "error": "failed to update env"})
        return
    restarted = _restart_status_service()
    _send_json(
        conn,
        200,
        {
            "ok": True,
            "profile": profile or None,
            "restarted": restarted,
        },
    )


def _websocket_handshake(conn: socket.socket, headers: dict[str, str]) -> bool:
    key = headers.get("sec-websocket-key")
    if not key:
        return False
    version = headers.get("sec-websocket-version")
    if version and version != "13":
        return False
    accept = build_accept_key(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    conn.sendall(response.encode("ascii"))
    return True


def _run_ws_session(conn: socket.socket, config: Config, session_id: str | None) -> None:
    session = _attach_or_create_session(session_id, config)
    if session is None:
        conn.sendall(build_close_frame())
        return
    pid = session.pid
    master_fd = session.master_fd
    resize_pty(master_fd, pid, 24, 80)
    log_handle = _open_session_log(session)
    ws_buffer = WebSocketBuffer()
    stop_event = threading.Event()

    def ws_to_pty() -> None:
        try:
            while not stop_event.is_set():
                data = conn.recv(4096)
                if not data:
                    break
                try:
                    messages = ws_buffer.feed(data)
                except ValueError as exc:
                    logger.warning("WebSocket buffer error: %s", exc)
                    conn.sendall(build_close_frame())
                    stop_event.set()
                    break
                for opcode, payload in messages:
                    if opcode == OPCODE_BINARY:
                        os.write(master_fd, payload)
                    elif opcode == OPCODE_TEXT:
                        _handle_text_message(payload, master_fd, pid)
                    elif opcode == OPCODE_PING:
                        conn.sendall(build_pong_frame(payload))
                    elif opcode == OPCODE_CLOSE:
                        conn.sendall(build_close_frame())
                        stop_event.set()
                        break
        except OSError:
            pass
        finally:
            stop_event.set()

    def pty_to_ws() -> None:
        try:
            while not stop_event.is_set():
                ready, _, _ = select.select([master_fd], [], [], 0.5)
                if not ready:
                    continue
                data = os.read(master_fd, 4096)
                if not data:
                    break
                conn.sendall(build_binary_frame(data))
                if log_handle:
                    log_handle.write(data)
        except OSError:
            pass
        finally:
            stop_event.set()

    thread_in = threading.Thread(target=ws_to_pty, daemon=True)
    thread_out = threading.Thread(target=pty_to_ws, daemon=True)
    thread_in.start()
    thread_out.start()
    thread_in.join()
    thread_out.join()

    stop_event.set()
    if log_handle:
        try:
            log_handle.close()
        except OSError:
            pass
    _finalize_session(session)


def _session_is_attached(session_id: str) -> bool:
    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
        return bool(session and session.attached)


def _prune_sessions(ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    now = time.monotonic()
    expired: list[tuple[str, StoredSession]] = []
    with _SESSIONS_LOCK:
        for session_id, session in list(_SESSIONS.items()):
            if session.attached:
                continue
            if now - session.last_detach >= ttl_seconds:
                expired.append((session_id, session))
                del _SESSIONS[session_id]
    for _, session in expired:
        _cleanup_pty(session.pid, session.master_fd)


def _attach_or_create_session(session_id: str | None, config: Config) -> SessionContext | None:
    if not config.session_resume or not session_id:
        pid, master_fd = spawn_pty(config.shell, config.term, config.cwd, config.shell_cmd)
        return SessionContext(
            pid=pid,
            master_fd=master_fd,
            session_id=None,
            persistent=False,
            log_path=_make_log_path(config, None, pid),
        )

    with _SESSIONS_LOCK:
        session = _SESSIONS.get(session_id)
        if session and session.attached:
            return None
        if session:
            session.attached = True
            session.last_detach = 0.0
            return SessionContext(
                pid=session.pid,
                master_fd=session.master_fd,
                session_id=session_id,
                persistent=True,
                log_path=session.log_path,
            )

    pid, master_fd = spawn_pty(config.shell, config.term, config.cwd, config.shell_cmd)
    log_path = _make_log_path(config, session_id, pid)
    new_session = StoredSession(
        pid=pid,
        master_fd=master_fd,
        attached=True,
        last_detach=0.0,
        log_path=log_path,
    )
    with _SESSIONS_LOCK:
        existing = _SESSIONS.get(session_id)
        if existing and existing.attached:
            _cleanup_pty(pid, master_fd)
            return None
        if existing and not existing.attached:
            _cleanup_pty(pid, master_fd)
            existing.attached = True
            existing.last_detach = 0.0
            return SessionContext(
                pid=existing.pid,
                master_fd=existing.master_fd,
                session_id=session_id,
                persistent=True,
                log_path=existing.log_path,
            )
        _SESSIONS[session_id] = new_session
    return SessionContext(
        pid=pid,
        master_fd=master_fd,
        session_id=session_id,
        persistent=True,
        log_path=log_path,
    )


def _make_log_path(config: Config, session_id: str | None, pid: int) -> Path | None:
    if not config.session_log_dir:
        return None
    session_tag = session_id or "anonymous"
    safe_tag = session_tag[:32]
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    filename = f"zeroterm-session-{timestamp}-{safe_tag}-{pid}.log"
    return config.session_log_dir / filename


def _open_session_log(session: SessionContext):
    if session.log_path is None:
        return None
    try:
        session.log_path.parent.mkdir(parents=True, exist_ok=True)
        return open(session.log_path, "ab", buffering=0)
    except OSError:
        logger.warning("Failed to open session log %s", session.log_path)
        return None


def _finalize_session(session: SessionContext) -> None:
    if not session.persistent or not session.session_id:
        _cleanup_pty(session.pid, session.master_fd)
        return
    if not _is_child_alive(session.pid):
        _cleanup_pty(session.pid, session.master_fd)
        with _SESSIONS_LOCK:
            _SESSIONS.pop(session.session_id, None)
        return
    with _SESSIONS_LOCK:
        stored = _SESSIONS.get(session.session_id)
        if stored:
            stored.attached = False
            stored.last_detach = time.monotonic()


def _is_child_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return False
    return waited == 0


def _cleanup_pty(pid: int, master_fd: int) -> None:
    try:
        os.close(master_fd)
    except OSError:
        pass
    if pid <= 0:
        return
    if _wait_for_child(pid, 0.1):
        return
    for sig in (signal.SIGHUP, signal.SIGTERM):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        if _wait_for_child(pid, 0.5):
            return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    _wait_for_child(pid, 0.5)


def _wait_for_child(pid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            waited, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return True
        if waited == pid:
            return True
        time.sleep(0.05)
    return False


def _handle_text_message(payload: bytes, master_fd: int, pid: int) -> None:
    try:
        message = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if message.get("type") != "resize":
        return

    try:
        cols = int(message.get("cols", 0))
        rows = int(message.get("rows", 0))
    except (TypeError, ValueError):
        return

    resize_pty(master_fd, pid, rows, cols)
