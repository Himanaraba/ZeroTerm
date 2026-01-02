# Setup (Kali Linux Lite on Raspberry Pi Zero 2 W)

This setup assumes a headless Pi running Kali Linux (Lite) with systemd.
All steps are manual on the device; no installer is provided.

## 1) Install prerequisites

- python3 (standard library only)
- systemd (already present on Kali Lite)

Optional (e-Paper status display):
- python3-pil
- python3-spidev
- python3-rpi.gpio

Enable SPI if you use an e-Paper display.

Optional (Waveshare library helper):

```
sudo bash scripts/install_waveshare_epd.sh
```

## 2) Decide runtime user

ZeroTerm assumes a full-power shell. Running as root preserves unrestricted
command access (default). If you choose a dedicated user, some commands will
be unavailable and that conflicts with the project goals.

## 3) Place the repo

```
sudo mkdir -p /opt/zeroterm
sudo rsync -a ./ /opt/zeroterm/
```

Quick install (from repo root):

```
sudo bash scripts/install_pi_zero.sh
```

## 4) Configure environment

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

## 5) Install the systemd unit

```
sudo cp /opt/zeroterm/systemd/zeroterm.service /etc/systemd/system/zeroterm.service
sudo cp /opt/zeroterm/systemd/zeroterm-status.service /etc/systemd/system/zeroterm-status.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm.service
sudo systemctl enable --now zeroterm-status.service
```

## 6) Access from the iPad

Open Safari and connect to:

```
http://<pi-ip>:<port>/
```

## Notes

- The web UI is intentionally minimal and uses no frontend framework.
- No command filtering or sandboxing is applied.
- The systemd unit runs as root by default to avoid command restrictions.
- Use network-level controls if you need access restrictions.
