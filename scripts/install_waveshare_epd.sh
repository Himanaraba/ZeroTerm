#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${ZEROTERM_EPAPER_REPO:-/opt/zeroterm/third_party/e-Paper}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

if [[ -d "${TARGET_DIR}" ]]; then
  echo "Waveshare e-Paper repo already exists at ${TARGET_DIR}"
else
  git clone https://github.com/waveshare/e-Paper "${TARGET_DIR}"
fi

echo "Set ZEROTERM_EPAPER_LIB=${TARGET_DIR}/RaspberryPi_JetsonNano/python/lib"