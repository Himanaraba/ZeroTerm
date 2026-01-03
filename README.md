# ZeroTerm

Headless Kali PTY over Web for Raspberry Pi Zero 2 W.
Version: v1

ZeroTerm turns a Pi Zero 2 W into a real Kali Linux TTY that you drive from Safari.
No GUI, no desktop, no framework. The web is just a terminal cable.

## Overview
- Real PTY over WebSocket with zero command filtering
- Minimal web terminal (ANSI colors + basic VT controls)
- Optional e-Paper status display for battery and health
- Status API + power presets for telemetry and tuning
- systemd-first, boot-and-go operation

## Core Idea
"The web interface is a terminal cable."

ZeroTerm does not wrap commands, limit features, or replace the CLI.
It forwards raw bytes to a real PTY, so the experience matches SSH.

## What You Get
- Full Kali Linux CLI in a browser
- Framework-free HTML/CSS/JS terminal UI
- e-Paper renderer for battery, Wi-Fi, and system health
- Optional offline install bundle
- Windows mock UI for layout checks

## Hardware / OS
- Raspberry Pi Zero 2 W (WH is fine)
- Kali Linux Lite + systemd
- Built-in Wi-Fi for management, optional external adapter for experiments
- Optional PiSugar battery + Waveshare 2.13-inch e-Paper

## Quick Start
- Follow docs/SETUP_PI_ZERO.md for the real device.
- For UI preview on Windows: `python test\app.py`.

## Status API & Power Presets
- GET `/api/status` for battery percent, power state, and active profile.
- POST `/api/power` with `{"profile":"eco"}` to change presets.
- CLI helper: `sudo zeroterm-power eco` / `balanced` / `performance` / `default`.

## Implementation (Baseline)
- Python 3 standard library PTY-over-WebSocket server
- Minimal web terminal client (no frontend framework)
- systemd units for terminal + e-Paper status
- Environment-based configuration

## Documentation
- docs/ARCHITECTURE.md - system flow, protocol, and renderer behavior
- docs/SETUP_PI_ZERO.md - installation and runtime setup
- docs/CONFIG_EXAMPLES.md - ready-to-use config samples
- docs/SECURITY.md - operational notes

## License
MIT License
