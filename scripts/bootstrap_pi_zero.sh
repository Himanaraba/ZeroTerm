#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENABLE_EPAPER="${ZEROTERM_ENABLE_EPAPER:-0}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

apt update
apt install -y python3 git tmux

if [[ "${ENABLE_EPAPER}" == "1" ]]; then
  apt install -y python3-pil python3-spidev python3-rpi.gpio
  if [[ -x "${ROOT_DIR}/scripts/install_waveshare_epd.sh" ]]; then
    "${ROOT_DIR}/scripts/install_waveshare_epd.sh"
  fi
fi

"${ROOT_DIR}/scripts/install_pi_zero.sh"
