from __future__ import annotations

import json
import logging
import os
import socket
import threading

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
        request = read_http_request(conn)
        if request is None:
            return

        if request.method != "GET":
            _send_text(conn, 405, b"Method Not Allowed")
            return

        if _is_websocket_request(request.headers):
            if not _websocket_handshake(conn, request.headers):
                _send_text(conn, 400, b"Bad Request")
                return
            logger.info("WebSocket connected from %s:%s", addr[0], addr[1])
            _run_ws_session(conn, config)
            return

        serve_static(conn, request.target, config.static_dir)


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


def _is_websocket_request(headers: dict[str, str]) -> bool:
    upgrade = headers.get("upgrade", "").lower() == "websocket"
    connection = headers.get("connection", "").lower()
    has_upgrade = "upgrade" in connection
    return upgrade and has_upgrade


def _websocket_handshake(conn: socket.socket, headers: dict[str, str]) -> bool:
    key = headers.get("sec-websocket-key")
    if not key:
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


def _run_ws_session(conn: socket.socket, config: Config) -> None:
    pid, master_fd = spawn_pty(config.shell, config.term, config.cwd)
    resize_pty(master_fd, pid, 24, 80)
    ws_buffer = WebSocketBuffer()
    stop_event = threading.Event()

    def ws_to_pty() -> None:
        try:
            while not stop_event.is_set():
                data = conn.recv(4096)
                if not data:
                    break
                for opcode, payload in ws_buffer.feed(data):
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
                data = os.read(master_fd, 4096)
                if not data:
                    break
                conn.sendall(build_binary_frame(data))
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
    try:
        os.close(master_fd)
    except OSError:
        pass
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass


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
