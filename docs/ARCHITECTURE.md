# Architecture

## Overview
ZeroTerm is a headless Kali Linux terminal system. The web UI is only a
transport layer. The shell runs on a real PTY and all input/output is
forwarded without filtering or sandboxing.

## Data Flow
1. Browser loads static HTML/CSS/JS from zerotermd.
2. Browser opens a WebSocket to /ws.
3. zerotermd spawns a PTY and launches the login shell.
4. PTY output is streamed to the browser as binary frames.
5. Browser input is streamed to the PTY as binary frames.
6. Resize events are sent as JSON control messages.

## Components
- zerotermd: Python standard library server (HTTP, WebSocket, PTY).
- Web client: minimal HTML/CSS/JS with a tiny VT subset.
- systemd unit: runs zerotermd at boot.
- zeroterm-status: e-Paper status renderer (status/IP/Wi-Fi/battery/uptime/temp/load).
- Environment config: /etc/zeroterm/zeroterm.env.

## Protocol Summary
- WebSocket endpoint: /ws
- Binary frames carry raw PTY bytes in both directions.
- Text frames carry JSON control messages (resize only).
- See docs/PROTOCOL.md for details.

## Design Constraints
- No GUI and no frontend frameworks
- No command restrictions or sandboxing
- Raspberry Pi Zero 2 W + Kali Linux Lite + systemd
- Web is a terminal cable, not an application platform
