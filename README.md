# ZeroTerm

ZeroTerm is a **fully headless, ultra-lightweight Kali Linux terminal system**
designed specifically for the **Raspberry Pi Zero 2 W**.

It provides **direct, unrestricted TTY access** to native Kali Linux
command-line tools and standard Linux commands through a **minimal web interface**,
operated entirely from an **iPad (Safari)**.

No display, keyboard, desktop environment, or heavy frameworks are used.

---

## Motivation

Modern security tools and Linux systems are increasingly tied to
graphical interfaces, large frameworks, and powerful hardware.

ZeroTerm was created with a different philosophy:

- Treat Kali Linux as a **service OS**, not a desktop OS
- Eliminate all unnecessary layers (GUI, window managers, VNC, etc.)
- Use the web **only as a transport layer**, not as an application platform
- Make a portable, battery-powered Linux security node
- Operate everything through **real CUI**, not abstractions

The result is a system that behaves like a **true Linux terminal on the network**.

---

## Core Concept

> **“The web interface is used as a terminal cable.”**

ZeroTerm does **not**:
- Convert CUI tools into web applications
- Wrap commands in JSON or REST APIs
- Restrict available Linux commands
- Provide a sandboxed or limited shell

Instead:

- Tools run on a **real PTY**
- Input/output is forwarded over the web
- The experience is equivalent to SSH, but browser-based
- CUI tools remain completely unmodified

---

## Design Goals

- Fully headless operation  
  (no HDMI, no keyboard, no mouse)

- 100% CUI-based Kali Linux environment

- Web-based terminal access  
  (Safari-compatible, no apps required)

- Extremely lightweight  
  (designed for Raspberry Pi Zero 2 W constraints)

- Portable and battery-powered

- Explicit separation of roles:
  - Web = transport
  - Linux = execution
  - CUI = interface

---

## What ZeroTerm Is

- A **real Linux TTY over the web**
- A headless Kali Linux node
- A platform for security research and experimentation
- A system where **standard Linux commands work normally**

Examples of supported usage:
- `apt install`, `apt build-dep`
- Kernel module and driver builds
- `ip`, `iw`, `rfkill`, `lsusb`
- Compilation with `make`
- Native Kali CUI tools (e.g. wifite, aircrack-ng, etc.)

There is **no artificial restriction layer**.

---

## What ZeroTerm Is NOT

- Not a GUI
- Not a web-based command launcher
- Not a restricted shell
- Not a desktop replacement
- Not a REST/JSON API service
- Not a browser-based IDE

If you want a graphical desktop or rich UI, this project is not for you.

---

## Hardware Target

ZeroTerm is designed around the following **fixed hardware assumptions**:

- **Raspberry Pi Zero 2 WH**
- **Kali Linux (Lite)**
- **External USB Wi-Fi adapter**  
  (used for monitoring / research / experimentation)
- **Built-in Wi-Fi**  
  (used exclusively for management and web access)
- **PiSugar2 battery module**
- **2.13" ePaper display** for persistent status information

The hardware limitations are not a drawback — they are part of the design.

---

## Operating Model

- The device boots directly into a **service-based state**
- No interactive login is required
- Core components run as `systemd` services
- The system is always reachable over the web once powered

The iPad acts as:
- Keyboard
- Monitor
- Control console

The Raspberry Pi acts as:
- Execution node
- Network interface
- Power-efficient compute unit

---

## ePaper Usage Philosophy

The ePaper display is **not** a terminal.

It is intentionally limited to:
- System state (READY / RUNNING)
- IP address for web access
- Battery level
- Wi-Fi status

It does **not**:
- Display logs
- Scroll text
- Mirror the TTY output

This preserves battery life and aligns with the
“headless-first” design philosophy.

---

## Software Stack Overview

- Kali Linux (Lite)
- No X / Wayland / Desktop Environment
- No GUI libraries
- No frontend frameworks
- Minimal HTML + JavaScript
- PTY-based terminal backend
- WebSocket or equivalent bidirectional transport
- systemd-managed services

Every layer is intentionally minimal.

---

## Security & Usage Notice

This project is intended for:
- Educational purposes
- Security research
- Controlled experimentation

Users are responsible for complying with:
- Local laws
- Network policies
- Ethical guidelines

ZeroTerm provides a **terminal**, not intent.

---

## Why ZeroTerm Exists

Because sometimes you don’t want:
- A laptop
- A screen
- A heavy OS
- A complicated UI

You just want:
- A real Linux shell
- On small hardware
- Accessible anywhere
- Without compromises

---

## Project Status

This repository represents the **foundation and architecture**
of ZeroTerm.

Implementation is intentionally incremental, focusing first on:
- Correctness
- Simplicity
- Transparency

---

## License

MIT License

---

## One-Line Summary

**ZeroTerm turns a Raspberry Pi Zero 2 W into a fully headless Kali Linux node,
controlled entirely via a real web-based TTY from an iPad — nothing more,
nothing less.**
