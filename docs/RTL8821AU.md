# RTL8821AU Monitor Mode

ZeroTerm can install the aircrack-ng rtl8812au driver, switch the adapter
to monitor mode, and verify injection. This is done via a one-shot script
and a systemd unit.

## Manual run
```
sudo bash scripts/rtl8821au_setup.sh
```

## systemd unit
```
sudo cp /opt/zeroterm/systemd/zeroterm-rtl8821au.service /etc/systemd/system/zeroterm-rtl8821au.service
sudo systemctl daemon-reload
sudo systemctl enable --now zeroterm-rtl8821au.service
```

## Outputs
- Status file: /var/lib/zeroterm/rtl8821au.status
- Log file: /var/log/zeroterm/rtl8821au.log

## Environment overrides
- ZEROTERM_RTL8821AU_IFACE (default: wlan0)
- ZEROTERM_RTL8821AU_REPO (default: https://github.com/aircrack-ng/rtl8812au.git)
- ZEROTERM_RTL8821AU_SRC_DIR (default: /usr/src/rtl8812au)
- ZEROTERM_RTL8821AU_STATUS_FILE (default: /var/lib/zeroterm/rtl8821au.status)
- ZEROTERM_RTL8821AU_LOG_FILE (default: /var/log/zeroterm/rtl8821au.log)
- ZEROTERM_RTL8821AU_REQUIRE_INJECTION (default: 0)
