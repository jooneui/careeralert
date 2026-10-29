#!/bin/zsh
set -euo pipefail

VAULT_DIR="/Users/jooneuihong/Library/CloudStorage/OneDrive-UCIrvine/06 Obisidian/05 Career"
SCAN_DATE="$(date +%Y-%m-%d)"
SCAN_STARTED="$(date +%s)"
LOG_FILE="$VAULT_DIR/automation/logs/$SCAN_DATE.log"
PROMPT_FILE="$VAULT_DIR/automation/daily-scan-prompt.md"
DIGEST_FILE="$VAULT_DIR/automation/digests/$SCAN_DATE.md"
CLAUDE_BIN="/Users/jooneuihong/.local/bin/claude"

cd "$VAULT_DIR"

"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
  --model claude-sonnet-5 \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "WebSearch WebFetch Read Write Edit Glob Grep" \
  --no-session-persistence \
  >> "$LOG_FILE" 2>&1 || SCAN_STATUS=$?

SCAN_STATUS=${SCAN_STATUS:-0}
if [[ $SCAN_STATUS -ne 0 ]]; then
  echo "ERROR: scan exited $SCAN_STATUS; dashboard was not rebuilt" >> "$LOG_FILE"
  exit $SCAN_STATUS
fi

# A successful scan must leave a dated digest, including when it found nothing.
if [[ ! -s "$DIGEST_FILE" ]] || (( $(stat -f %m "$DIGEST_FILE") < SCAN_STARTED )); then
  echo "ERROR: scan returned success without writing a fresh digest for $SCAN_DATE" >> "$LOG_FILE"
  exit 1
fi

# The other feeds run independently: a failure keeps that feed's last digest
# visible and is named in the notification, but never discards the career scan.
FAILED=()
run_feed() {
  local name="$1"; shift
  "$@" >> "$LOG_FILE" 2>&1 || {
    echo "WARNING: $name exited $?; showing its last successful data" >> "$LOG_FILE"
    FAILED+=("$name")
  }
}
run_feed "AI Watch" /bin/zsh "$VAULT_DIR/automation/run-ai-watch.sh"
run_feed "Transportation News" /bin/zsh "$VAULT_DIR/automation/run-transport-news.sh"
run_feed "Economy indicators" /usr/bin/python3 "$VAULT_DIR/automation/econ_indicators.py" fetch
run_feed "Economy news" /bin/zsh "$VAULT_DIR/automation/run-econ-news.sh"

# Rebuild the browsable HTML dashboard from all digests (deterministic, no network).
/usr/bin/python3 "$VAULT_DIR/automation/build-digest-html.py" >> "$LOG_FILE" 2>&1

# Send one daily completion notification, including days with no new items.
if (( ${#FAILED} == 0 )); then
  NOTICE="All scans complete; open Career Alerts for results"
else
  NOTICE="Career scan complete; needs attention: ${(j:, :)FAILED}"
fi
/usr/bin/osascript -e "display notification \"$NOTICE\" with title \"Career Alerts\"" >> "$LOG_FILE" 2>&1 || echo "WARNING: notification could not be sent" >> "$LOG_FILE"
