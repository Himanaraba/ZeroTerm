#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="${ZEROTERM_OFFLINE_OUT_DIR:-${ROOT_DIR}/dist/zeroterm-offline-${STAMP}}"
PKG_DIR="${OUT_DIR}/packages"
REPO_DIR="${OUT_DIR}/repo"

INCLUDE_EPAPER="${ZEROTERM_OFFLINE_INCLUDE_EPAPER:-0}"
INCLUDE_RTL="${ZEROTERM_OFFLINE_INCLUDE_RTL8821AU:-0}"
INCLUDE_WAVESHARE="${ZEROTERM_OFFLINE_INCLUDE_WAVESHARE:-0}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

mkdir -p "${PKG_DIR}" "${REPO_DIR}"

packages=(python3 git)
if [[ "${INCLUDE_EPAPER}" == "1" ]]; then
  packages+=(python3-pil python3-spidev python3-rpi.gpio)
fi
if [[ "${INCLUDE_RTL}" == "1" ]]; then
  packages+=(dkms build-essential "linux-headers-$(uname -r)" iw wireless-tools aircrack-ng)
fi

echo "Downloading packages: ${packages[*]}"
apt-get update
apt-get install -y --download-only "${packages[@]}"

cp -a /var/cache/apt/archives/*.deb "${PKG_DIR}/" || true
rm -f "${PKG_DIR}"/*dbgsym*.deb

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude '.git' --exclude '.venv' --exclude 'dist' "${ROOT_DIR}/" "${REPO_DIR}/"
else
  cp -a "${ROOT_DIR}/." "${REPO_DIR}/"
  rm -rf "${REPO_DIR}/.git" "${REPO_DIR}/.venv" "${REPO_DIR}/dist"
fi

if [[ "${INCLUDE_WAVESHARE}" == "1" ]]; then
  if [[ -d "${ROOT_DIR}/third_party/e-Paper" ]]; then
    mkdir -p "${REPO_DIR}/third_party"
    cp -a "${ROOT_DIR}/third_party/e-Paper" "${REPO_DIR}/third_party/"
  else
    echo "Waveshare repo not found at ${ROOT_DIR}/third_party/e-Paper" >&2
  fi
fi

cat > "${OUT_DIR}/manifest.txt" <<EOF
created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
include_epaper=${INCLUDE_EPAPER}
include_rtl8821au=${INCLUDE_RTL}
include_waveshare=${INCLUDE_WAVESHARE}
packages=${packages[*]}
EOF

tar -czf "${OUT_DIR}.tar.gz" -C "$(dirname "${OUT_DIR}")" "$(basename "${OUT_DIR}")"

echo "Bundle created: ${OUT_DIR}.tar.gz"
