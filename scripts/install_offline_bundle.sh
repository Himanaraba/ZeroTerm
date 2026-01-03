#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

BUNDLE_PATH="${1:-}"
if [[ -z "${BUNDLE_PATH}" ]]; then
  echo "Usage: $0 <bundle-dir-or-tar.gz>" >&2
  exit 1
fi

WORK_DIR=""
BUNDLE_DIR=""

if [[ -f "${BUNDLE_PATH}" ]]; then
  WORK_DIR="$(mktemp -d)"
  tar -xzf "${BUNDLE_PATH}" -C "${WORK_DIR}"
  BUNDLE_DIR="$(find "${WORK_DIR}" -maxdepth 1 -type d -name 'zeroterm-offline-*' | head -n 1)"
elif [[ -d "${BUNDLE_PATH}" ]]; then
  BUNDLE_DIR="${BUNDLE_PATH}"
else
  echo "Bundle not found: ${BUNDLE_PATH}" >&2
  exit 1
fi

if [[ -z "${BUNDLE_DIR}" ]]; then
  echo "Bundle directory not found inside archive" >&2
  exit 1
fi

PKG_DIR="${BUNDLE_DIR}/packages"
REPO_DIR="${BUNDLE_DIR}/repo"

if [[ ! -d "${PKG_DIR}" || ! -d "${REPO_DIR}" ]]; then
  echo "Invalid bundle structure: ${BUNDLE_DIR}" >&2
  exit 1
fi

mkdir -p /var/cache/apt/archives
cp -a "${PKG_DIR}"/*.deb /var/cache/apt/archives/ || true

dpkg -i "${PKG_DIR}"/*.deb || true
apt-get -y -f install --no-download
dpkg -i "${PKG_DIR}"/*.deb

if [[ -x "${REPO_DIR}/scripts/install_pi_zero.sh" ]]; then
  ZEROTERM_TARGET=/opt/zeroterm bash "${REPO_DIR}/scripts/install_pi_zero.sh"
else
  echo "install_pi_zero.sh not found in bundle repo" >&2
  exit 1
fi

if [[ -n "${WORK_DIR}" ]]; then
  rm -rf "${WORK_DIR}"
fi

echo "Offline install complete."
