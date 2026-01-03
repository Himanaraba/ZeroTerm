# Config Examples

All samples are .env-style key=value lines.

## Minimal server
ZEROTERM_BIND=0.0.0.0
ZEROTERM_PORT=8080
ZEROTERM_SHELL=/bin/bash

## Status + e-Paper (Waveshare)
ZEROTERM_STATUS_IFACE=wlan0
ZEROTERM_EPAPER_LIB=/opt/zeroterm/third_party/e-Paper/RaspberryPi_JetsonNano/python/lib
ZEROTERM_EPAPER_MODEL=epd2in13_V3

## e-Paper file output (no hardware)
ZEROTERM_EPAPER_DRIVER=file
ZEROTERM_EPAPER_OUTPUT=/var/lib/zeroterm/epaper.png

## Battery sources
ZEROTERM_BATTERY_CMD=pisugar-power -c
# or
ZEROTERM_BATTERY_PATH=/sys/class/power_supply

## Power presets
ZEROTERM_STATUS_PROFILE=eco
ZEROTERM_STATUS_LOW_BATTERY=20
ZEROTERM_STATUS_LOW_BATTERY_INTERVAL=120
ZEROTERM_STATUS_NIGHT_START=23
ZEROTERM_STATUS_NIGHT_END=6
ZEROTERM_STATUS_NIGHT_INTERVAL=300

## Update checks (optional)
ZEROTERM_UPDATE_CHECK=1
ZEROTERM_UPDATE_FETCH=0
ZEROTERM_UPDATE_PATH=/opt/zeroterm
ZEROTERM_UPDATE_REMOTE=origin
ZEROTERM_UPDATE_BRANCH=main

## RTL8821AU
ZEROTERM_RTL8821AU_IFACE=wlan1
