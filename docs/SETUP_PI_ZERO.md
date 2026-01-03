# Setup: Raspberry Pi Zero 2 W (Kali Lite)

This guide assumes a headless Kali Linux Lite image on Raspberry Pi Zero 2 W
and systemd as the init system. All steps are manual on the device.

## 1) Flash the OS
- Download the Kali Linux ARM image for Raspberry Pi Zero 2 W.
- Flash it to a microSD card.

## 2) Headless bootstrap (no HDMI)
On the boot partition:
- Create an empty file named `ssh` to enable SSH on first boot.
- Create `wpa_supplicant.conf` with your Wi-Fi credentials.

Example `wpa_supplicant.conf`:
```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
  ssid="YOUR_SSID"
  psk="YOUR_PASSWORD"
  key_mgmt=WPA-PSK
}
```

## 3) First boot
- Power on the Pi and connect over SSH.
- Change default passwords and update packages.

## 4) Install dependencies
```
sudo apt update
sudo apt install -y python3 git
```

Optional (e-Paper status display):

```
sudo apt install -y python3-pil python3-spidev python3-rpi.gpio
```

Enable SPI for the e-Paper display (raspi-config or boot config), then reboot.

Quick bootstrap (installs deps + enables services):

```
sudo ZEROTERM_ENABLE_EPAPER=1 bash scripts/bootstrap_pi_zero.sh
```

Optional (Waveshare library helper):

```
sudo bash scripts/install_waveshare_epd.sh
```

## 5) Deploy the repo
```
sudo mkdir -p /opt/zeroterm
sudo git clone <your-repo-url> /opt/zeroterm
```

Quick install (from repo root):

```
sudo bash scripts/install_pi_zero.sh
```

## 6) Optional: RTL8821AU monitor mode

Run the installer + verification script:

```
sudo bash scripts/rtl8821au_setup.sh
```

Enable the one-shot systemd unit (runs at boot):

```
sudo cp /opt/zeroterm/systemd/zeroterm-rtl8821au.service /etc/systemd/system/zeroterm-rtl8821au.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm-rtl8821au.service
```

If your adapter enumerates as wlan1, set:

```
sudo ZEROTERM_RTL8821AU_IFACE=wlan1 bash scripts/rtl8821au_setup.sh
```

## 7) Decide runtime user

ZeroTerm assumes a full-power shell. Running as root preserves unrestricted
command access (default). If you choose a dedicated user, some commands will
be unavailable and that conflicts with the project goals.

## 8) Configure environment
```
sudo mkdir -p /etc/zeroterm
sudo cp /opt/zeroterm/config/zeroterm.env /etc/zeroterm/zeroterm.env
sudo nano /etc/zeroterm/zeroterm.env
```

If you use a Waveshare 2.13 display, set:

```
ZEROTERM_EPAPER_LIB=/opt/zeroterm/third_party/e-Paper/RaspberryPi_JetsonNano/python/lib
ZEROTERM_EPAPER_MODEL=epd2in13_V3
```

## 9) Install and enable systemd service
```
sudo cp /opt/zeroterm/systemd/zeroterm.service /etc/systemd/system/zeroterm.service
sudo cp /opt/zeroterm/systemd/zeroterm-status.service /etc/systemd/system/zeroterm-status.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm.service
sudo systemctl enable --now zeroterm-status.service
```

## 10) Access from iPad
- Connect the iPad to the Pi management Wi-Fi network.
- Open `http://<pi-ip>:<port>/` in Safari.

## Notes
- Built-in Wi-Fi is for management/web access.
- Use an external USB Wi-Fi adapter for monitoring or experiments.
- The web UI is intentionally minimal and uses no frontend framework.
- No command filtering or sandboxing is applied.
- The systemd unit runs as root by default to avoid command restrictions.
- Use network-level controls if you need access restrictions.

## Optional: e-Paper status display

Displayed items:
- System state (READY / RUNNING / DOWN)
- IP address (management interface)
- Wi-Fi state and SSID (if available)
- External Wi-Fi adapter (if detected)
- Battery percentage (and charge state when available)
- Uptime, temperature, load, CPU, and memory (lightweight health summary)
- A small status face to mirror the device mood

Layout:
- Top bar with IP, Wi-Fi state, battery, and uptime.
- Left panel with status face and battery bar.
- Right panel with status message and MEM/CPU/TMP metrics.
- Footer bar with Wi-Fi SSID and load.

Requirements (Waveshare 2.13):
- SPI enabled
- Python packages: python3-pil, python3-spidev, python3-rpi.gpio
- waveshare_epd library available in PYTHONPATH

Battery sources can be configured via:
```
ZEROTERM_BATTERY_CMD=pisugar-power -c
ZEROTERM_BATTERY_PATH=/sys/class/power_supply
```

Test output without hardware:

```
ZEROTERM_EPAPER_DRIVER=file
ZEROTERM_EPAPER_OUTPUT=/var/lib/zeroterm/epaper.png
```

Quick checks (no hardware):

1) Install Pillow (if missing):
```
python3 -m pip install Pillow
```

2) Render a sample PNG:
```
python3 scripts/render_status_sample.py --output /tmp/zeroterm_epaper.png
```

3) Render with live metrics (optional):
```
python3 scripts/render_status_sample.py --live
```

## Configuration reference

Core:
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
- ZEROTERM_SESSION_LOG_DIR (default: empty)
  Optional directory for PTY session logs.
- ZEROTERM_SESSION_RESUME (default: 1)
  Reuse PTY sessions across WebSocket reconnects.
- ZEROTERM_SESSION_TTL (default: 60)
  Seconds to keep a detached PTY session alive.

Status / e-Paper:
- ZEROTERM_STATUS_PROFILE (default: empty)
  Power preset for status updates (eco, balanced, performance).
- ZEROTERM_STATUS_INTERVAL (default: 30)
  Refresh interval in seconds for the e-Paper status display.
- ZEROTERM_STATUS_IFACE (default: wlan0)
  Network interface to display IP/Wi-Fi status from.
- ZEROTERM_STATUS_IFACE_AUTO (default: 0)
  Auto-select a wlan interface when the preferred one is missing.
- ZEROTERM_STATUS_SERVICE (default: zeroterm.service)
  systemd service name used to decide READY/RUNNING state.
- ZEROTERM_STATUS_NIGHT_START (default: 22)
  Night schedule start hour (0-23).
- ZEROTERM_STATUS_NIGHT_END (default: 6)
  Night schedule end hour (0-23).
- ZEROTERM_STATUS_NIGHT_INTERVAL (default: 0)
  If set, uses a slower update interval at night.
- ZEROTERM_STATUS_LOW_BATTERY (default: 0)
  Battery percent threshold for low-power updates.
- ZEROTERM_STATUS_LOW_BATTERY_INTERVAL (default: 0)
  If set, uses a slower update interval when below the threshold.
- ZEROTERM_STATUS_WIFI_INTERVAL (default: 0)
  If set, caches Wi-Fi info for this many seconds.
- ZEROTERM_STATUS_SERVICE_INTERVAL (default: 0)
  If set, caches service state for this many seconds.
- ZEROTERM_STATUS_METRICS_INTERVAL (default: 0)
  If set, caches system metrics for this many seconds.
- ZEROTERM_STATUS_IDLE_INTERVAL (default: 0)
  If set, sleeps longer when the payload is unchanged.
- ZEROTERM_STATUS_WIFI_SSID (default: 1)
  When 0, skip SSID reads to reduce work.
- ZEROTERM_BATTERY_LOG_PATH (default: empty)
  Optional CSV path for battery history logging.
- ZEROTERM_BATTERY_LOG_INTERVAL (default: 0)
  Interval in seconds for battery log entries.
- ZEROTERM_POWER_LOG_PATH (default: empty)
  Optional log file for power state events.

Update checks:
- ZEROTERM_UPDATE_CHECK (default: 0)
  Enable update availability checks.
- ZEROTERM_UPDATE_INTERVAL (default: 3600)
  Update check interval in seconds.
- ZEROTERM_UPDATE_PATH (default: /opt/zeroterm)
  Repo path to check for updates.
- ZEROTERM_UPDATE_REMOTE (default: origin)
  Git remote to compare against.
- ZEROTERM_UPDATE_BRANCH (default: main)
  Git branch to compare against.
- ZEROTERM_UPDATE_FETCH (default: 0)
  When 1, fetch remote refs before comparing.
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

RTL8821AU:
- ZEROTERM_RTL8821AU_IFACE (default: wlan0)
  Wi-Fi interface to switch into monitor mode.
- ZEROTERM_RTL8821AU_REPO (default: https://github.com/aircrack-ng/rtl8812au.git)
  Driver repository to clone into /usr/src.
- ZEROTERM_RTL8821AU_SRC_DIR (default: /usr/src/rtl8812au)
  Working directory for the driver build.
- ZEROTERM_RTL8821AU_STATUS_FILE (default: /var/lib/zeroterm/rtl8821au.status)
  Status output file written by the setup/check script.
- ZEROTERM_RTL8821AU_LOG_FILE (default: /var/log/zeroterm/rtl8821au.log)
  Log file for the setup/check script.
- ZEROTERM_RTL8821AU_REQUIRE_INJECTION (default: 0)
  When set to 1, the script fails if injection is not verified.
