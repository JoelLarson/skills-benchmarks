#!/usr/bin/env bash
# Offline verification that run_pilot.sh survives a quota block: stub `bench` so the
# first attempt of each cell reports a usage-limit (no reward) and the next succeeds.
# Proves the wait→retry loop and RESUME skip, using the real script + lib_run.sh.
# No Codex, no quota, no Docker.
set -euo pipefail
cd "$(dirname "$0")/.."

TMP="$(mktemp -d)"; BIN="$TMP/bin"; STATE="$TMP/state"; mkdir -p "$BIN" "$STATE"
trap 'rm -rf "$TMP" results/raw jobs' EXIT

# Fake bench: 1st call per --jobs-dir => usage-limit (no reward, no reset time so the
# fallback wait applies); 2nd+ call => write a reward, simulating quota having reset.
cat > "$BIN/bench" <<EOF
#!/usr/bin/env bash
jd=""; prev=""
for a in "\$@"; do [ "\$prev" = "--jobs-dir" ] && jd="\$a"; prev="\$a"; done
key="\$(echo "\$jd" | tr '/' '_')"; m="$STATE/\$key"
n=\$(cat "\$m" 2>/dev/null || echo 0); n=\$((n+1)); echo "\$n" > "\$m"
if [ "\$n" -lt 2 ]; then
  echo "ERROR: You've hit your usage limit. Upgrade or purchase more credits."
  exit 0
fi
mkdir -p "\$jd/rollout/verifier"; echo 1 > "\$jd/rollout/verifier/reward.txt"
echo "Rewards: {'reward': 1.0}"
EOF
chmod +x "$BIN/bench"

rm -rf results/raw jobs
common=(env "PATH=$BIN:$PATH" USE_PODMAN=0 AGENT=oracle MODELS=default
        TASKS=arithmetic-trap TRIALS=1 QUOTA_FALLBACK_WAIT=2 MAX_QUOTA_WAITS=3 RESUME=1)

echo "=== Run 1: expect a quota wait+retry, then a reward ==="
out1="$("${common[@]}" bash scripts/run_pilot.sh 2>&1)"; echo "$out1" | grep -E 'quota exhausted|>>|skip' || true

pass=1
echo "$out1" | grep -q "quota exhausted; sleeping" || { echo "FAIL: no quota wait happened"; pass=0; }
[ -f results/raw/default/arithmetic-trap/no_skill/trial-1/reward.txt ] || { echo "FAIL: no reward after retry"; pass=0; }

echo "=== Run 2: expect RESUME to skip the completed cells ==="
out2="$("${common[@]}" bash scripts/run_pilot.sh 2>&1)"; echo "$out2" | grep -E 'skip|>>' || true
echo "$out2" | grep -q "skip (already done)" || { echo "FAIL: RESUME did not skip"; pass=0; }
echo "$out2" | grep -q "^>> " && { echo "FAIL: re-ran a completed cell"; pass=0; }

echo "============================================"
if [ "$pass" = 1 ]; then echo "PASS: quota wait+retry and RESUME both work"; else echo "FAILED"; exit 1; fi
