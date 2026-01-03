from __future__ import annotations

import unittest

from zerotermd.websocket import OPCODE_BINARY, OPCODE_TEXT, WebSocketBuffer, build_frame


def _make_masked_frame(opcode: int, payload: bytes, mask: bytes) -> bytes:
    if len(mask) != 4:
        raise ValueError("mask must be 4 bytes")
    header = bytearray()
    header.append(0x80 | (opcode & 0x0F))
    header.append(0x80 | len(payload))
    header.extend(mask)
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
    return bytes(header) + masked


class TestWebSocketBuffer(unittest.TestCase):
    def test_unmasked_frame(self) -> None:
        payload = b"hello"
        frame = build_frame(OPCODE_BINARY, payload)
        buffer = WebSocketBuffer()
        messages = buffer.feed(frame)
        self.assertEqual(messages, [(OPCODE_BINARY, payload)])

    def test_masked_frame(self) -> None:
        payload = b"world"
        mask = b"\x01\x02\x03\x04"
        frame = _make_masked_frame(OPCODE_TEXT, payload, mask)
        buffer = WebSocketBuffer()
        messages = buffer.feed(frame)
        self.assertEqual(messages, [(OPCODE_TEXT, payload)])
