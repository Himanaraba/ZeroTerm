# ZeroTerm

ZeroTerm is a fully headless, ultra-lightweight Kali Linux terminal system
for Raspberry Pi Zero 2 W. It exposes a real PTY over the web so an iPad
(Safari) acts as the keyboard and screen.

No display, keyboard, desktop environment, or heavy framework is used.

---

## Motivation

Modern security tools and Linux systems are increasingly tied to
graphical interfaces, large frameworks, and powerful hardware.

ZeroTerm was created with a different philosophy:

- Treat Kali Linux as a service OS, not a desktop OS
- Eliminate unnecessary layers (GUI, window managers, VNC)
- Use the web only as a transport layer, not an application platform
- Make a portable, battery-powered Linux security node
- Operate through a real CUI, not abstractions

The result is a system that behaves like a true Linux terminal on the network.

---

## Core Concept

"The web interface is a terminal cable."

ZeroTerm does not:
- Convert CUI tools into web apps
- Wrap commands in JSON or REST APIs
- Restrict available Linux commands
- Provide a sandboxed or limited shell

Instead:
- Tools run on a real PTY
- Input/output is forwarded as raw bytes
- The experience is equivalent to SSH, but browser-based
- CUI tools remain unmodified

---

## Design Goals

- Fully headless operation (no HDMI, keyboard, mouse)
- 100% CUI-based Kali Linux environment
- Web-based terminal access (Safari-compatible, no apps)
- Extremely lightweight for Pi Zero 2 W constraints
- Portable and battery-powered
- Clear separation of roles: Web = transport, Linux = execution, CUI = interface

---

## What ZeroTerm Is

- A real Linux TTY over the web
- A headless Kali Linux node
- A platform for security research and experimentation
- A system where standard Linux commands work normally

Examples of supported usage:
- apt install, apt build-dep
- Kernel module and driver builds
- ip, iw, rfkill, lsusb
- Compilation with make
- Native Kali CUI tools (wifite, aircrack-ng, etc.)

There is no artificial restriction layer.

---

## What ZeroTerm Is Not

- A GUI or desktop replacement
- A web-based command launcher
- A restricted shell
- A REST/JSON API service
- A browser-based IDE

---

## Hardware Target

- Raspberry Pi Zero 2 W (WH is fine)
- Kali Linux (Lite)
- External USB Wi-Fi adapter for monitoring/experimentation
- Built-in Wi-Fi for management and web access
- PiSugar2 battery module
- 2.13-inch ePaper display for status only

The hardware limits are part of the design.

---

## Operating Model

- Boots directly into a service-based state
- No interactive login required
- Core components run as systemd services
- Always reachable over the web once powered

---

## ePaper Philosophy

The ePaper display is not a terminal. It shows:
- System state (READY / RUNNING / DOWN)
- IP address for web access
- Wi-Fi status (and SSID when available)
- Battery level (and charge state when available)
- Uptime, temperature, load, CPU, and memory (lightweight health summary)
- A small status face for quick visual state checks

It does not show logs or TTY output.

---

## Software Stack (High Level)

- Kali Linux Lite
- No X / Wayland / desktop environment
- Minimal HTML + JavaScript
- PTY backend with WebSocket transport
- systemd-managed services

---

## Security & Usage

ZeroTerm provides a terminal, not intent. Use it for education and research,
and follow local laws and network policies. See docs/SECURITY.md.

---

## Project Status

This repository represents the foundation and architecture of ZeroTerm.
Implementation is intentionally incremental, focusing on:
- Correctness
- Simplicity
- Transparency

---

## Implementation (Baseline)

This repository includes a minimal, framework-free baseline:

- Python 3 standard library PTY-over-WebSocket service
- Minimal HTML/CSS/JS terminal client
- systemd units for terminal + e-Paper status
- Environment-based configuration

---

## Documentation

- docs/ARCHITECTURE.md
- docs/SETUP_PI_ZERO.md
- docs/SECURITY.md
- docs/EPAPER.md
- docs/CONFIGURATION.md
- docs/PROTOCOL.md
- docs/CLIENT.md

---

## License

MIT License

---

## One-Line Summary

ZeroTerm turns a Raspberry Pi Zero 2 W into a fully headless Kali Linux node,
controlled entirely via a real web-based TTY from an iPad - nothing more,
nothing less.
