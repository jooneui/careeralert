#!/bin/zsh
set -euo pipefail

VAULT_DIR="/Users/jooneuihong/Library/CloudStorage/OneDrive-UCIrvine/06 Obisidian/05 Career"
SCAN_DATE="$(date +%Y-%m-%d)"
SCAN_STARTED="$(date +%s)"
PROMPT_FILE="$VAULT_DIR/automation/econ-news-scan-prompt.md"
DIGEST_FILE="$VAULT_DIR/automation/econ-news-digests/$SCAN_DATE.md"
LOG_FILE="$VAULT_DIR/automation/logs/econ-news-$SCAN_DATE.log"
CLAUDE_BIN="/Users/jooneuihong/.local/bin/claude"

mkdir -p "$VAULT_DIR/automation/econ-news-digests"
cd "$VAULT_DIR"

"$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
  --model claude-sonnet-5 \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "WebSearch WebFetch Read Write Edit Glob Grep" \
  --no-session-persistence \
  >> "$LOG_FILE" 2>&1

if [[ ! -s "$DIGEST_FILE" ]] || (( $(stat -f %m "$DIGEST_FILE") < SCAN_STARTED )); then
  print -r -- "ERROR: Economy scan returned success without writing a fresh digest for $SCAN_DATE" >> "$LOG_FILE"
  exit 1
fi

print -r -- "Economy digest ready: $DIGEST_FILE" >> "$LOG_FILE"
