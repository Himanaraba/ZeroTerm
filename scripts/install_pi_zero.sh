#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${ZEROTERM_TARGET:-/opt/zeroterm}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"
if command -v rsync >/dev/null 2>&1; then
  rsync -a "${ROOT_DIR}/" "${TARGET_DIR}/"
else
  cp -a "${ROOT_DIR}/." "${TARGET_DIR}/"
fi

mkdir -p /etc/zeroterm
cp "${TARGET_DIR}/config/zeroterm.env" /etc/zeroterm/zeroterm.env

cp "${TARGET_DIR}/systemd/zeroterm.service" /etc/systemd/system/zeroterm.service
cp "${TARGET_DIR}/systemd/zeroterm-status.service" /etc/systemd/system/zeroterm-status.service

systemctl daemon-reload
systemctl enable --now zeroterm.service
systemctl enable --now zeroterm-status.service

echo "ZeroTerm installed to ${TARGET_DIR}"