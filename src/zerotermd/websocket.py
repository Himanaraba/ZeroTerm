from __future__ import annotations

import base64
import hashlib
import struct

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


def build_accept_key(client_key: str) -> str:
    raw = (client_key + GUID).encode("ascii")
    digest = hashlib.sha1(raw).digest()
    return base64.b64encode(digest).decode("ascii")


def build_frame(opcode: int, payload: bytes) -> bytes:
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length < 65536:
        header.append(126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127)
        header.extend(struct.pack("!Q", length))
    return bytes(header) + payload


def build_text_frame(text: str) -> bytes:
    return build_frame(OPCODE_TEXT, text.encode("utf-8"))


def build_binary_frame(payload: bytes) -> bytes:
    return build_frame(OPCODE_BINARY, payload)


def build_pong_frame(payload: bytes) -> bytes:
    return build_frame(OPCODE_PONG, payload)


def build_close_frame() -> bytes:
    return build_frame(OPCODE_CLOSE, b"")


class WebSocketBuffer:
    def __init__(self, max_size: int = 2_000_000) -> None:
        self._buffer = bytearray()
        self._partial_opcode: int | None = None
        self._partial_payload = bytearray()
        self._max_size = max_size

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        self._buffer.extend(data)
        if len(self._buffer) > self._max_size:
            raise ValueError("WebSocket buffer exceeded limit")
        messages: list[tuple[int, bytes]] = []
        while True:
            frame = self._next_frame()
            if frame is None:
                break
            fin, opcode, payload = frame
            if opcode == OPCODE_CONTINUATION:
                if self._partial_opcode is None:
                    continue
                self._partial_payload.extend(payload)
                if fin:
                    messages.append((self._partial_opcode, bytes(self._partial_payload)))
                    self._partial_opcode = None
                    self._partial_payload = bytearray()
                continue

            if fin:
                messages.append((opcode, payload))
            else:
                self._partial_opcode = opcode
                self._partial_payload = bytearray(payload)
        return messages

    def _next_frame(self) -> tuple[bool, int, bytes] | None:
        if len(self._buffer) < 2:
            return None
        b1 = self._buffer[0]
        b2 = self._buffer[1]
        fin = bool(b1 & 0x80)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        index = 2

        if length == 126:
            if len(self._buffer) < index + 2:
                return None
            length = struct.unpack("!H", self._buffer[index : index + 2])[0]
            index += 2
        elif length == 127:
            if len(self._buffer) < index + 8:
                return None
            length = struct.unpack("!Q", self._buffer[index : index + 8])[0]
            index += 8

        mask_key = b""
        if masked:
            if len(self._buffer) < index + 4:
                return None
            mask_key = bytes(self._buffer[index : index + 4])
            index += 4

        if len(self._buffer) < index + length:
            return None

        payload = bytes(self._buffer[index : index + length])
        del self._buffer[: index + length]

        if masked:
            payload = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))

        return fin, opcode, payload
