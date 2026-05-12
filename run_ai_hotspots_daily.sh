#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"

mkdir -p "${LOG_DIR}"
cd "${SCRIPT_DIR}"

python3 "${SCRIPT_DIR}/ai_hotspots_daily.py" "$@" >>"${LOG_DIR}/ai_hotspots_daily.log" 2>&1
