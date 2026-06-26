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

# Copy the verifier's stdout (expected-vs-got, pass/fail) into the cell as the
# human-readable evaluation log shown in the report. No-op if not found.
capture_log() {  # <jobsdir> <dest_dir>
  local v; v="$(find "$1" -name test-stdout.txt 2>/dev/null | head -1)"
  [[ -n "$v" ]] || return 1
  cp "$v" "$2/verifier.log" 2>/dev/null || return 1
}

# Extract token usage from a cell's bench result.json into a compact usage.json
# (token cost for the report). No-op if no result.json or no agent_result usage.
extract_usage() {  # <jobsdir> <out_usage_json>
  local res; res="$(find "$1" -name result.json | head -1)"
  [[ -n "$res" ]] || return 1
  python3 - "$res" "$2" <<'PY' || return 1
import json, sys
src, out = sys.argv[1], sys.argv[2]
try:
    a = (json.load(open(src)) or {}).get("agent_result") or {}
except (OSError, ValueError):
    sys.exit(1)
keys = {"input_tokens": "n_input_tokens", "output_tokens": "n_output_tokens",
        "cache_read_tokens": "n_cache_read_tokens", "total_tokens": "total_tokens"}
u = {k: (a.get(v) or 0) for k, v in keys.items()}
if not any(u.values()):
    sys.exit(1)
json.dump(u, open(out, "w"))
PY
}
