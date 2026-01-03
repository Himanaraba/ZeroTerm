#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

IFACE="${ZEROTERM_RTL8821AU_IFACE:-wlan0}"
REPO="${ZEROTERM_RTL8821AU_REPO:-https://github.com/aircrack-ng/rtl8812au.git}"
SRC_DIR="${ZEROTERM_RTL8821AU_SRC_DIR:-/usr/src/rtl8812au}"
STATUS_DIR="${ZEROTERM_RTL8821AU_STATUS_DIR:-/var/lib/zeroterm}"
STATUS_FILE="${ZEROTERM_RTL8821AU_STATUS_FILE:-${STATUS_DIR}/rtl8821au.status}"
LOG_DIR="${ZEROTERM_RTL8821AU_LOG_DIR:-/var/log/zeroterm}"
LOG_FILE="${ZEROTERM_RTL8821AU_LOG_FILE:-${LOG_DIR}/rtl8821au.log}"
REQUIRE_INJECTION="${ZEROTERM_RTL8821AU_REQUIRE_INJECTION:-0}"

mkdir -p "${STATUS_DIR}" "${LOG_DIR}"
touch "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "[rtl8821au] start ${timestamp}"
echo "[rtl8821au] iface=${IFACE}"

echo "[rtl8821au] purge legacy drivers"
apt purge -y realtek-rtl88xxau-dkms rtl8821au-dkms || true

echo "[rtl8821au] install build dependencies"
apt update
apt install -y git dkms build-essential "linux-headers-$(uname -r)" iw wireless-tools aircrack-ng

echo "[rtl8821au] clone aircrack-ng driver"
rm -rf "${SRC_DIR}"
git clone --depth 1 "${REPO}" "${SRC_DIR}"

echo "[rtl8821au] install DKMS module"
cd "${SRC_DIR}"
make dkms_install

driver_loaded="no"
echo "[rtl8821au] reload module"
modprobe -r 8821au 2>/dev/null || true
if modprobe 8821au; then
  driver_loaded="yes"
fi

iface_state="missing"
monitor_state="fail"
if iw dev | grep -q "Interface ${IFACE}"; then
  iface_state="present"
  echo "[rtl8821au] switch ${IFACE} to monitor mode"
  ip link set "${IFACE}" down
  iw dev "${IFACE}" set type monitor
  ip link set "${IFACE}" up
  iw dev "${IFACE}" info || true
  iwconfig "${IFACE}" || true
  if iw dev "${IFACE}" info | grep -q "type monitor"; then
    monitor_state="ok"
  fi
else
  echo "[rtl8821au] interface ${IFACE} not found"
fi

injection_state="skip"
if command -v aireplay-ng >/dev/null 2>&1; then
  if [[ "${monitor_state}" == "ok" ]]; then
    echo "[rtl8821au] injection test"
    if command -v timeout >/dev/null 2>&1; then
      injection_output="$(timeout 20s aireplay-ng -9 "${IFACE}" 2>&1 || true)"
    else
      injection_output="$(aireplay-ng -9 "${IFACE}" 2>&1 || true)"
    fi
    echo "${injection_output}"
    if echo "${injection_output}" | grep -q "Injection is working"; then
      injection_state="ok"
    else
      injection_state="fail"
    fi
  fi
fi

cat > "${STATUS_FILE}" <<EOF
timestamp=${timestamp}
iface=${IFACE}
driver_loaded=${driver_loaded}
iface_state=${iface_state}
monitor_state=${monitor_state}
injection_state=${injection_state}
EOF

echo "[rtl8821au] status written to ${STATUS_FILE}"

if [[ "${monitor_state}" != "ok" ]]; then
  exit 1
fi

if [[ "${REQUIRE_INJECTION}" == "1" && "${injection_state}" != "ok" ]]; then
  exit 1
fi
