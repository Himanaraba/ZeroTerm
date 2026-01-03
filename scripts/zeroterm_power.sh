#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo)" >&2
  exit 1
fi

PROFILE="${1:-}"
if [[ -z "${PROFILE}" ]]; then
  echo "Usage: $0 <eco|balanced|performance|default>" >&2
  exit 1
fi

case "${PROFILE}" in
  eco|balanced|performance)
    ;;
  default|none|off)
    PROFILE=""
    ;;
  *)
    echo "Unknown profile: ${PROFILE}" >&2
    exit 1
    ;;
esac

ENV_FILE="${ZEROTERM_ENV_PATH:-/etc/zeroterm/zeroterm.env}"

python3 - "${ENV_FILE}" "${PROFILE}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
value = sys.argv[2]
key = "ZEROTERM_STATUS_PROFILE"

try:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
except FileNotFoundError:
    lines = []

updated = False
new_lines = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith("#") or "=" not in stripped:
        new_lines.append(line)
        continue
    candidate = stripped
    if candidate.startswith("export "):
        candidate = candidate[7:].lstrip()
    name = candidate.split("=", 1)[0].strip()
    if name != key:
        new_lines.append(line)
        continue
    new_lines.append(f"{key}={value}\n")
    updated = True

if not updated:
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] = new_lines[-1] + "\n"
    new_lines.append(f"{key}={value}\n")

path.parent.mkdir(parents=True, exist_ok=True)
tmp_path = path.with_suffix(path.suffix + ".tmp")
tmp_path.write_text("".join(new_lines), encoding="utf-8")
tmp_path.replace(path)
PY

if command -v systemctl >/dev/null 2>&1; then
  systemctl restart zeroterm-status.service || true
fi

if [[ -n "${PROFILE}" ]]; then
  echo "Power profile set to ${PROFILE}"
else
  echo "Power profile reset to default"
fi
