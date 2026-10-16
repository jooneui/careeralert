#!/bin/zsh
# Keep this file installed outside OneDrive so launchd can always start it.
set -u

VAULT_DIR="/Users/jooneuihong/Library/CloudStorage/OneDrive-UCIrvine/06 Obisidian/05 Career"
SCAN_SCRIPT="/Users/jooneuihong/Library/Application Support/CareerAlerts/run-daily-scan.sh"
PROMPT_FILE="$VAULT_DIR/automation/daily-scan-prompt.md"
LOG_DIR="/Users/jooneuihong/Library/Logs/CareerAlerts"
RUN_LOG="$LOG_DIR/runner.log"

mkdir -p "$LOG_DIR"
print -r -- "$(date '+%Y-%m-%d %H:%M:%S') Starting scheduled scan" >> "$RUN_LOG"

# OneDrive may be unavailable briefly after login or wake. Keep the executable
# script local and wait until its vault input can actually be opened.
for (( attempt = 1; attempt <= 20; attempt++ )); do
  if probe_error="$(/bin/cat "$PROMPT_FILE" 2>&1 > /dev/null)"; then
    /bin/zsh "$SCAN_SCRIPT" >> "$RUN_LOG" 2>&1
    scan_exit_code=$?
    if (( scan_exit_code != 126 && scan_exit_code != 127 )); then
      print -r -- "$(date '+%Y-%m-%d %H:%M:%S') Scan exited $scan_exit_code" >> "$RUN_LOG"
      if (( scan_exit_code != 0 )); then
        /usr/bin/osascript -e 'display notification "Daily scan failed; check the Career Alerts log" with title "Career Alerts"' >> "$RUN_LOG" 2>&1 || true
      fi
      exit "$scan_exit_code"
    fi
  elif [[ "$probe_error" == *"Operation not permitted"* ]]; then
    print -r -- "$(date '+%Y-%m-%d %H:%M:%S') macOS denied /bin/zsh access to OneDrive: $probe_error" >> "$RUN_LOG"
    /usr/bin/osascript -e 'display notification "Allow zsh access to OneDrive in macOS Privacy settings" with title "Career Alerts"' >> "$RUN_LOG" 2>&1 || true
    exit 1
  fi
  print -r -- "$(date '+%Y-%m-%d %H:%M:%S') Vault input unavailable (attempt $attempt/20): $probe_error" >> "$RUN_LOG"
  sleep 30
done

print -r -- "$(date '+%Y-%m-%d %H:%M:%S') Scan script remained unavailable" >> "$RUN_LOG"
/usr/bin/osascript -e 'display notification "Daily scan could not open its files; check the Career Alerts log" with title "Career Alerts"' >> "$RUN_LOG" 2>&1 || true
exit 127
