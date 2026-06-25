#!/bin/bash
# Quota-resilient run helpers. Source AFTER scripts/config.sh.
#
# Lets a long benchmark survive Codex usage-limit exhaustion: when a run produces
# no reward and the log shows a usage/quota block, the caller waits until the
# reset window and retries — instead of losing every remaining cell.

: "${QUOTA_FALLBACK_WAIT:=1800}"   # seconds to wait when no reset time is parseable
: "${MAX_QUOTA_WAITS:=48}"          # max consecutive quota waits per cell (~24h @ 30m)
: "${RESUME:=1}"                    # skip cells whose reward.txt already exists (resumable)

_LIB_RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# True when a run log indicates a quota/usage block (codex surfaces it as a usage
# message or an auth-style ACP error when the account is out of credits).
quota_blocked() {  # <logfile>
  grep -qiE "usage limit|hit your (usage|limit)|reached your|Authentication required|ACP error -32000|rate limit|\\b429\\b|too many requests" "$1"
}

# Seconds to sleep before retrying after a quota block (parsed from the log, else fallback).
quota_wait_secs() {  # <logfile>
  python3 "$_LIB_RUN_DIR/quota_sleep.py" "$QUOTA_FALLBACK_WAIT" < "$1"
}
