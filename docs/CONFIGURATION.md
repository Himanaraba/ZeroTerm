# Configuration

ZeroTerm is configured entirely through environment variables. The systemd unit
loads /etc/zeroterm/zeroterm.env so you can change defaults without editing code.

## Variables

- ZEROTERM_BIND (default: 0.0.0.0)
  Address to bind the HTTP/WebSocket server.

- ZEROTERM_PORT (default: 8080)
  Port for the HTTP/WebSocket server.

- ZEROTERM_SHELL (default: /bin/bash)
  Shell to launch inside the PTY.

- ZEROTERM_TERM (default: linux)
  TERM value exported to the shell session.

- ZEROTERM_CWD (default: empty)
  Optional working directory for the shell. Empty means the user home.

- ZEROTERM_LOG_LEVEL (default: info)
  Logging verbosity (debug, info, warning, error).

- ZEROTERM_STATIC_DIR (default: /opt/zeroterm/web)
  Directory that serves static assets for the web client.

## Status / e-Paper Variables

- ZEROTERM_STATUS_INTERVAL (default: 30)
  Refresh interval in seconds for the e-Paper status display.

- ZEROTERM_STATUS_IFACE (default: wlan0)
  Network interface to display IP/Wi-Fi status from.

- ZEROTERM_STATUS_SERVICE (default: zeroterm.service)
  systemd service name used to decide READY/RUNNING state.

- ZEROTERM_EPAPER_DRIVER (default: waveshare)
  Display backend: waveshare, file, or null.

- ZEROTERM_EPAPER_MODEL (default: epd2in13_V3)
  Waveshare Python module name to load.

- ZEROTERM_EPAPER_LIB (default: empty)
  Optional path to the waveshare_epd library.

- ZEROTERM_EPAPER_OUTPUT (default: /var/lib/zeroterm/epaper.png)
  Output path when ZEROTERM_EPAPER_DRIVER=file.

- ZEROTERM_EPAPER_FONT_PATH (default: empty)
  Optional TTF font path for e-Paper text rendering.

- ZEROTERM_EPAPER_FONT_SIZE (default: 14)
  Font size for e-Paper rendering.

- ZEROTERM_EPAPER_WIDTH / ZEROTERM_EPAPER_HEIGHT (default: 250x122)
  Display size override in pixels.

- ZEROTERM_EPAPER_ROTATE (default: 0)
  Rotation (0/90/180/270).

- ZEROTERM_BATTERY_CMD (default: empty)
  Optional command that prints battery percent.

- ZEROTERM_BATTERY_PATH (default: /sys/class/power_supply)
  Optional path to battery capacity files.
