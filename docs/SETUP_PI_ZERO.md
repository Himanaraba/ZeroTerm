# Setup: Raspberry Pi Zero 2 W (Kali Lite)

This guide targets real hardware: Raspberry Pi Zero 2 W + Kali Linux Lite + systemd.
All commands run on the Pi unless stated otherwise.

## 0) Requirements
- Raspberry Pi Zero 2 W (WH is fine)
- Kali Linux Lite image
- Network access for initial setup
- Optional: Waveshare 2.13-inch e-Paper, PiSugar battery, external Wi-Fi adapter

## 1) Flash and headless boot
- Download the Kali Linux ARM image for Raspberry Pi Zero 2 W.
- Flash it to a microSD card.
- On the boot partition:
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

## 2) First boot
- Power on the Pi and connect over SSH.
- Change default passwords and update packages.

## 3) Install dependencies
```
sudo apt update
sudo apt install -y python3 git tmux
```

Optional (e-Paper status display):

```
sudo apt install -y python3-pil python3-spidev python3-rpi.gpio
```

## 4) Install ZeroTerm
Minimal install:
```
curl -fsSL https://raw.githubusercontent.com/Himanaraba/ZeroTerm/main/scripts/quick_install.sh | sudo bash
```

Full install (e-Paper + RTL8821AU):
```
curl -fsSL https://raw.githubusercontent.com/Himanaraba/ZeroTerm/main/scripts/full_install.sh | sudo bash
```

Optional flags:
```
curl -fsSL https://raw.githubusercontent.com/Himanaraba/ZeroTerm/main/scripts/quick_install.sh | sudo ZEROTERM_ENABLE_EPAPER=1 bash
curl -fsSL https://raw.githubusercontent.com/Himanaraba/ZeroTerm/main/scripts/quick_install.sh | sudo ZEROTERM_ENABLE_RTL8821AU=1 bash
```

Manual install (clone to /opt and run the installer):

```
sudo mkdir -p /opt/zeroterm
sudo git clone <your-repo-url> /opt/zeroterm
sudo bash /opt/zeroterm/scripts/install_pi_zero.sh
```

Quick bootstrap (deps + install + optional e-Paper):

```
sudo ZEROTERM_ENABLE_EPAPER=1 bash /opt/zeroterm/scripts/bootstrap_pi_zero.sh
```

## 5) Configure environment
```
sudo mkdir -p /etc/zeroterm
sudo cp /opt/zeroterm/config/zeroterm.env /etc/zeroterm/zeroterm.env
sudo nano /etc/zeroterm/zeroterm.env
```

See docs/CONFIG_EXAMPLES.md for ready-to-use settings.

Optional (tmux session on connect):
```
ZEROTERM_SHELL_CMD=tmux new -A -s zeroterm
```

If you use Waveshare 2.13, set:
```
ZEROTERM_EPAPER_LIB=/opt/zeroterm/third_party/e-Paper/RaspberryPi_JetsonNano/python/lib
ZEROTERM_EPAPER_MODEL=epd2in13_V3
```

## 6) Enable services
The installer already copies and enables systemd units. For manual setup:

```
sudo cp /opt/zeroterm/systemd/zeroterm.service /etc/systemd/system/zeroterm.service
sudo cp /opt/zeroterm/systemd/zeroterm-status.service /etc/systemd/system/zeroterm-status.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm.service
sudo systemctl enable --now zeroterm-status.service
```

Restart after config changes:
```
sudo systemctl restart zeroterm.service
sudo systemctl restart zeroterm-status.service
```

## 7) Access from iPad
- Connect the iPad to the Pi management Wi-Fi network.
- Open `http://<pi-ip>:<port>/` in Safari.

## Usage
Status API:
- `GET /api/status`
- `POST /api/power` with `{"profile":"eco"}`

CLI presets:
```
sudo zeroterm-power eco
sudo zeroterm-power balanced
sudo zeroterm-power performance
sudo zeroterm-power default
```

Monitor mode helper:
```
sudo zeroterm-monitor on
sudo zeroterm-monitor off
sudo zeroterm-monitor status
```
Interface selection:
```
ZEROTERM_MONITOR_IFACE=wlan0
```

Web UI buttons:
- MON ON/OFF sends zeroterm-monitor (or ip/iw fallback).
- WIFITE/HCXDUMP/BETTERCAP buttons type commands into the PTY.

## Optional: e-Paper status display
- Enable SPI (raspi-config or boot config) and reboot.
- Install Waveshare helper (if needed):
```
sudo bash /opt/zeroterm/scripts/install_waveshare_epd.sh
```

Quick output test (no hardware):
```
ZEROTERM_EPAPER_DRIVER=file \
ZEROTERM_EPAPER_OUTPUT=/tmp/zeroterm_epaper.png \
python3 /opt/zeroterm/scripts/render_status_sample.py --live
```

## Optional: Offline install bundle
Build the bundle on an online Kali machine with the same architecture:

```
sudo ZEROTERM_OFFLINE_INCLUDE_EPAPER=1 ZEROTERM_OFFLINE_INCLUDE_RTL8821AU=1 \
  bash /opt/zeroterm/scripts/build_offline_bundle.sh
```

Install on the Pi:
```
sudo bash /opt/zeroterm/scripts/install_offline_bundle.sh /path/to/zeroterm-offline-*.tar.gz
```

## Optional: RTL8821AU monitor mode
Run the installer + verification script:

```
sudo bash /opt/zeroterm/scripts/rtl8821au_setup.sh
```

Enable the one-shot systemd unit (runs at boot):
```
sudo cp /opt/zeroterm/systemd/zeroterm-rtl8821au.service /etc/systemd/system/zeroterm-rtl8821au.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm-rtl8821au.service
```

If your adapter enumerates as wlan1, set:
```
ZEROTERM_RTL8821AU_IFACE=wlan1 sudo bash /opt/zeroterm/scripts/rtl8821au_setup.sh
```

## Troubleshooting
- Battery shows `--`: set `ZEROTERM_BATTERY_CMD` or `ZEROTERM_BATTERY_PATH`.
- Web UI not reachable: confirm `zeroterm.service` and the port in `zeroterm.env`.
- Preset change not applied: check `ZEROTERM_ENV_PATH` and `zeroterm-status.service` logs.
- e-Paper blank: confirm SPI is enabled and the Waveshare library path is correct.
- Wi-Fi SSID missing: set `ZEROTERM_STATUS_IFACE` or enable auto-selection.

## Notes
- Built-in Wi-Fi is for management and web access.
- Use an external USB Wi-Fi adapter for monitoring or experiments.
- No command filtering or sandboxing is applied.
- The systemd unit runs as root by default to avoid command restrictions.
