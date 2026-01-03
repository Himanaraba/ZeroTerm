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
7. Browser polls /api/status for battery and power telemetry.
8. Power preset changes are sent to /api/power and applied via zeroterm-status.

## Components
- zerotermd: Python standard library server (HTTP, WebSocket, PTY, status API).
- Web client: minimal HTML/CSS/JS with a tiny VT subset.
- systemd unit: runs zerotermd at boot.
- zeroterm-status: e-Paper status renderer (status/IP/Wi-Fi/battery/uptime/temp/load/mem/cpu).
- Environment config: /etc/zeroterm/zeroterm.env.

## Protocol

ZeroTerm uses a single HTTP/WebSocket endpoint. The WebSocket link is a direct
byte pipe to the PTY with only minimal control messages.

- URL: ws://<host>:<port>/ws
- Binary frames: raw PTY bytes (both directions)
- Text frames: control messages in JSON

HTTP endpoints:
- GET /api/status: battery percent, power state, and active power profile.
- POST /api/power: update ZEROTERM_STATUS_PROFILE and restart zeroterm-status.

Resize control message (client -> server):

```
{"type":"resize","cols":80,"rows":24}
```

Notes:
- Commands are never filtered or translated.
- The browser is a transport cable for the TTY.

## Web Client Behavior

The client is intentionally minimal and framework-free. It renders a small
VT100-style subset to keep the transport thin and predictable.

Supported controls:
- Carriage return, line feed, backspace, tab
- Cursor movement: CSI A/B/C/D/E/F/G/H/f and CSI d
- Erase: CSI J and CSI K
- Insert/delete: CSI @ (ICH), CSI P (DCH), CSI X (ECH)
- Line insert/delete: CSI L/CSI M (IL/DL)
- Scroll region: CSI r (top/bottom), CSI S/CSI T
- Index: ESC D, reverse index: ESC M
- Cursor save/restore: ESC 7/ESC 8 and CSI s/u
- Private modes: ?25h/?25l (cursor) and ?1049h/?1049l (alt screen)
- SGR colors: 30-37/90-97 (foreground), 40-47/100-107 (background)
- SGR extended colors: 38/48;5;n (256-color) and 38/48;2;r;g;b (truecolor)
- SGR attributes: 1 (bold), 7 (inverse), 22/27/39/49 (reset)

Not implemented:
- Other SGR attributes (underline, italic, blink, strike)
- Advanced DEC modes beyond the subset above

Behavior notes:
- The client always forwards raw input bytes to the PTY.
- Full-screen TUI apps work for basic navigation; complex rendering may be limited.
- Touch devices show a small key bar (ESC/TAB/CTRL+C/CTRL+D/arrows).
- Rendering updates only touch dirty rows to keep the browser fast on low-power devices.

## Design Constraints
- No GUI and no frontend frameworks
- No command restrictions or sandboxing
- Raspberry Pi Zero 2 W + Kali Linux Lite + systemd
- Web is a terminal cable, not an application platform
