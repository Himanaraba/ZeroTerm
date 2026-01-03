#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ZEROTERM_REPO:-https://github.com/Himanaraba/ZeroTerm.git}"
BRANCH="${ZEROTERM_BRANCH:-main}"
TARGET_DIR="${ZEROTERM_TARGET:-/opt/zeroterm}"
ENABLE_EPAPER="${ZEROTERM_ENABLE_EPAPER:-0}"
ENABLE_RTL8821AU="${ZEROTERM_ENABLE_RTL8821AU:-0}"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git python3
fi

if [[ -d "${TARGET_DIR}/.git" ]]; then
  git -C "${TARGET_DIR}" fetch --all
  git -C "${TARGET_DIR}" checkout "${BRANCH}"
  git -C "${TARGET_DIR}" pull --ff-only
elif [[ -d "${TARGET_DIR}" && -n "$(ls -A "${TARGET_DIR}")" ]]; then
  echo "Target dir is not empty: ${TARGET_DIR}" >&2
  exit 1
else
  git clone --branch "${BRANCH}" "${REPO_URL}" "${TARGET_DIR}"
fi

ZEROTERM_ENABLE_EPAPER="${ENABLE_EPAPER}" bash "${TARGET_DIR}/scripts/bootstrap_pi_zero.sh"

if [[ "${ENABLE_RTL8821AU}" == "1" ]]; then
  bash "${TARGET_DIR}/scripts/rtl8821au_setup.sh"
fi

echo "ZeroTerm quick install complete."
