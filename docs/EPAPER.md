# e-Paper Status Display

ZeroTerm can render a small status summary to a 2.13-inch e-Paper display.
This display is intentionally limited to a compact system/health overview.

## Displayed Items

- System state (READY / RUNNING / DOWN)
- IP address (management interface)
- Wi-Fi state and SSID (if available)
- Battery percentage (and charge state when available)
- Uptime, temperature, load, CPU, and memory (lightweight health summary)
- A small status face to mirror the device mood

## Layout

- Top bar with IP, Wi-Fi state, battery, and uptime.
- Left panel with status face and battery bar.
- Right panel with status message and MEM/CPU/TMP metrics.
- Footer bar with Wi-Fi SSID and load.

## Requirements (Waveshare 2.13)

- SPI enabled
- Python packages: python3-pil, python3-spidev, python3-rpi.gpio
- waveshare_epd library available in PYTHONPATH

Example install (Kali):

```
sudo apt install -y python3-pil python3-spidev python3-rpi.gpio
```

Then place the Waveshare Python library somewhere like:

```
/opt/zeroterm/third_party/e-Paper/RaspberryPi_JetsonNano/python/lib
```

Optional helper:

```
sudo bash scripts/install_waveshare_epd.sh
```

Set:

```
ZEROTERM_EPAPER_LIB=/opt/zeroterm/third_party/e-Paper/RaspberryPi_JetsonNano/python/lib
ZEROTERM_EPAPER_MODEL=epd2in13_V3
```

Battery sources can be configured via:

```
ZEROTERM_BATTERY_CMD=pisugar-power -c
ZEROTERM_BATTERY_PATH=/sys/class/power_supply
```

## SPI Enablement

- Enable SPI in raspi-config or by editing boot config.
- Reboot after enabling SPI.

## Test Output Without Hardware

Set:

```
ZEROTERM_EPAPER_DRIVER=file
ZEROTERM_EPAPER_OUTPUT=/var/lib/zeroterm/epaper.png
```

This writes the status image to a PNG file for verification.

## Notes

- Refresh is throttled to avoid unnecessary e-Paper updates.
- The display is not used as a terminal screen.
