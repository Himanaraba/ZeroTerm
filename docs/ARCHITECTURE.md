# Architecture

## Overview
ZeroTerm is a headless Kali terminal over Web. The browser is a transport cable.
A real PTY is spawned on the Pi and raw bytes flow both directions.

## Components
- zerotermd: HTTP + WebSocket server, PTY bridge, status/power API
- Web client: framework-free terminal renderer (ANSI + small VT subset)
- zeroterm-status: e-Paper renderer + power profile handler
- systemd units: zeroterm.service, zeroterm-status.service

## Data Flow
1. Browser loads static HTML/CSS/JS from zerotermd.
2. Browser opens a WebSocket to /ws.
3. zerotermd spawns a PTY and login shell.
4. PTY output streams to the browser as binary frames.
5. Browser input streams to the PTY as binary frames.
6. Resize events are sent as JSON control messages.
7. Browser polls /api/status for battery, power, and Wi-Fi telemetry.
8. Power preset changes are sent to /api/power and applied by zeroterm-status.

## Protocol
- WebSocket binary frames: raw PTY bytes
- WebSocket text frames: JSON control messages
- HTTP endpoints: /api/status and /api/power
  - /api/status returns battery + Wi-Fi (iface/state/mode/ssid/channel/packets).

Resize control message (client -> server):

```
{"type":"resize","cols":80,"rows":24}
```

Notes:
- Commands are never filtered or translated.
- The browser is a transport cable for the TTY.

## Web Terminal Rendering
The client intentionally stays small to keep the transport predictable.

Supported behavior:
- ANSI SGR 16/256/truecolor
- Cursor movement, insert/delete, erase, scroll region
- Alt screen, cursor show/hide

Not implemented:
- Advanced DEC modes beyond the subset above
- Additional SGR attributes (underline/italic/blink/strike)

UI notes:
- Tool/monitor buttons simply send commands into the PTY.

## Status / e-Paper Rendering
- zeroterm-status reads system metrics and renders the 2.13-inch layout.
- Drivers: waveshare (real device), file (PNG output), null (disabled).
- Face/mood reflects RUNNING/READY/DOWN and low battery.

## Constraints
- No GUI or frontend frameworks
- No command filtering or sandboxing
- Raspberry Pi Zero 2 W + Kali + systemd
- Web is a terminal cable, not an app layer
