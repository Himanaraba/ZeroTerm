#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
iface="${2:-${ZEROTERM_MONITOR_IFACE:-wlan0}}"

if [[ -z "${action}" || -z "${iface}" ]]; then
  echo "Usage: zeroterm-monitor <on|off|status> [iface]" >&2
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

if ! command -v iw >/dev/null 2>&1; then
  echo "iw not found" >&2
  exit 1
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "ip not found" >&2
  exit 1
fi

mode_from_iw() {
  iw dev "${iface}" info 2>/dev/null | awk '/type/ {print $2; exit}'
}

case "${action}" in
  on)
    ip link set "${iface}" down
    iw dev "${iface}" set type monitor
    ip link set "${iface}" up
    echo "monitor on (${iface})"
    ;;
  off)
    ip link set "${iface}" down
    iw dev "${iface}" set type managed
    ip link set "${iface}" up
    echo "monitor off (${iface})"
    ;;
  status)
    mode="$(mode_from_iw)"
    if [[ -z "${mode}" ]]; then
      echo "monitor status: unknown (${iface})"
      exit 1
    fi
    echo "monitor status: ${mode} (${iface})"
    ;;
  *)
    echo "Usage: zeroterm-monitor <on|off|status> [iface]" >&2
    exit 1
    ;;
esac
