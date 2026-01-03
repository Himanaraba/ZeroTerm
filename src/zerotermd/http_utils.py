from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


HTTP_REASONS = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    500: "Internal Server Error",
    101: "Switching Protocols",
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".woff2": "font/woff2",
}


@dataclass
class HttpRequest:
    method: str
    target: str
    version: str
    headers: dict[str, str]
    body: bytes


def read_http_request(
    conn,
    max_bytes: int = 65536,
    max_body_bytes: int = 65536,
) -> HttpRequest | None:
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        data.extend(chunk)
        if len(data) > max_bytes:
            return None

    header_bytes, rest = bytes(data).split(b"\r\n\r\n", 1)
    try:
        header_text = header_bytes.decode("iso-8859-1")
        lines = header_text.split("\r\n")
        method, target, version = lines[0].split(" ")
    except ValueError:
        return None

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    body = rest
    content_length = headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
        except ValueError:
            length = 0
        if length > max_body_bytes:
            return None
        while len(body) < length:
            chunk = conn.recv(min(4096, length - len(body)))
            if not chunk:
                break
            body += chunk
    return HttpRequest(method=method, target=target, version=version, headers=headers, body=body)


def send_response(conn, status: int, headers: dict[str, str] | None, body: bytes) -> None:
    reason = HTTP_REASONS.get(status, "")
    lines = [f"HTTP/1.1 {status} {reason}"]
    if headers:
        for name, value in headers.items():
            lines.append(f"{name}: {value}")
    lines.append("")
    lines.append("")
    payload = "\r\n".join(lines).encode("ascii") + body
    conn.sendall(payload)


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def _resolve_path(target: str, static_dir: Path) -> Path | None:
    path = urlsplit(target).path
    if path == "/":
        path = "/index.html"
    resolved = (static_dir / path.lstrip("/")).resolve()
    if not _is_within(static_dir, resolved):
        return None
    return resolved


def serve_static(conn, target: str, static_dir: Path) -> None:
    resolved = _resolve_path(target, static_dir)
    if resolved is None or not resolved.is_file():
        body = b"Not Found"
        send_response(
            conn,
            404,
            {
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Length": str(len(body)),
            },
            body,
        )
        return

    try:
        body = resolved.read_bytes()
    except OSError:
        body = b"Internal Server Error"
        send_response(
            conn,
            500,
            {
                "Content-Type": "text/plain; charset=utf-8",
                "Content-Length": str(len(body)),
            },
            body,
        )
        return

    content_type = CONTENT_TYPES.get(resolved.suffix.lower(), "application/octet-stream")
    send_response(
        conn,
        200,
        {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Cache-Control": "no-store",
        },
        body,
    )
