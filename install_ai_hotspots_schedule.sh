#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${SCRIPT_DIR}/run_ai_hotspots_daily.sh"
CRON_LINE="0 9 * * * ${RUNNER}"

chmod +x "${SCRIPT_DIR}/ai_hotspots_daily.py" "${RUNNER}"

if command -v crontab >/dev/null 2>&1; then
  tmp_file="$(mktemp)"
  crontab -l 2>/dev/null | grep -vF "${RUNNER}" >"${tmp_file}" || true
  echo "${CRON_LINE}" >>"${tmp_file}"
  crontab "${tmp_file}"
  rm -f "${tmp_file}"
  echo "Installed cron job: ${CRON_LINE}"
  exit 0
fi

if command -v systemctl >/dev/null 2>&1; then
  USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
  mkdir -p "${USER_SYSTEMD_DIR}"

  cat >"${USER_SYSTEMD_DIR}/ai-hotspots-daily.service" <<EOF_SERVICE
[Unit]
Description=Generate daily AI hotspots report

[Service]
Type=oneshot
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${RUNNER}
EOF_SERVICE

  cat >"${USER_SYSTEMD_DIR}/ai-hotspots-daily.timer" <<EOF_TIMER
[Unit]
Description=Run AI hotspots report every day at 09:00

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF_TIMER

  systemctl --user daemon-reload
  systemctl --user enable --now ai-hotspots-daily.timer
  echo "Installed systemd user timer: ai-hotspots-daily.timer"
  exit 0
fi

cat <<EOF_MANUAL
No crontab or systemctl command was found.

Manual schedule command:
${CRON_LINE}

You can still run the task now with:
${RUNNER}
EOF_MANUAL
