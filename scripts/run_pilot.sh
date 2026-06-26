#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh
source scripts/lib_run.sh

# Use Podman via a docker->podman shim (bench has no --sandbox podman).
if [[ "${USE_PODMAN:-0}" == "1" ]]; then
  command -v podman >/dev/null || { echo "USE_PODMAN=1 but podman not found" >&2; exit 1; }
  export PATH="$(pwd)/scripts/podman:$PATH"
  export PODMAN_SOCKET DOCKER_HOST="unix://${PODMAN_SOCKET}"
fi

SKILLS_DIR="skills"

# strip YAML frontmatter (first ---...--- block); print the body
strip_frontmatter() { awk 'BEGIN{f=0} /^---[[:space:]]*$/{f++; next} f>=2{print}' "$1"; }

SKILL_BODY=""
if [[ "${FORCE_INJECT:-0}" == "1" ]]; then
  SMD="$(find "$SKILLS_DIR" -name SKILL.md | head -1)"
  SKILL_BODY="$(strip_frontmatter "$SMD")"
  [[ -n "$SKILL_BODY" ]] || SKILL_BODY="$(cat "$SMD")"
  echo "Force-inject ON: appending the skill directive to every with_skill prompt."
fi

run_one() {
  local model="$1" task="$2" cond="$3" trial="$4"

  local dest="results/raw/$model/$task/$cond/trial-$trial"
  if [[ "${RESUME:-1}" == "1" && -f "$dest/reward.txt" ]]; then
    echo "== skip (already done): $model | $task | $cond | trial $trial"
    return 0
  fi

  local extra=() prompt_args=()
  if [[ "$cond" == "with_skill" ]]; then
    if [[ "${FORCE_INJECT:-0}" == "1" ]]; then
      # Only difference from baseline is the appended directive (native skill
      # injection won't activate a trigger-less skill on Codex).
      extra=(--skill-mode no-skill)
      prompt_args=(--prompt "$(strip_frontmatter "tasks/$task/task.md")"$'\n\n'"$SKILL_BODY")
    else
      extra=(--skill-mode with-skill --skills-dir "$SKILLS_DIR")
    fi
  else
    extra=(--skill-mode no-skill)
  fi

  local model_args=()
  [[ "$model" != "default" ]] && model_args=(--model "$model")
  [[ -n "${REASONING_EFFORT:-}" ]] && model_args+=(--reasoning-effort "$REASONING_EFFORT")

  # Retry loop: on a quota/usage block (no reward produced), wait until the reset
  # window and retry the same cell, so a long run survives quota exhaustion.
  local waits=0
  while true; do
    local jobsdir="jobs/$model/$task/$cond/trial-$trial"; rm -rf "$jobsdir"; mkdir -p "$jobsdir"
    local log="$jobsdir/run.log"

    echo ">> $AGENT | $model | $task | $cond | trial $trial"
    bench eval run --tasks-dir "tasks/$task" --agent "$AGENT" \
      "${model_args[@]}" --sandbox docker "${extra[@]}" "${prompt_args[@]}" \
      --jobs-dir "$jobsdir" 2>&1 | tee "$log" || true

    local src timing
    src="$(find "$jobsdir" -name reward.txt | head -1)"
    if [[ -n "$src" ]]; then
      mkdir -p "$dest"; cp "$src" "$dest/reward.txt"
      timing="$(find "$jobsdir" -name timing.json | head -1)"
      [[ -n "$timing" ]] && cp "$timing" "$dest/timing.json" || true
      return 0
    fi

    if quota_blocked "$log"; then
      waits=$((waits + 1))
      if (( waits > MAX_QUOTA_WAITS )); then
        echo "!! gave up on $task/$cond/trial-$trial after $((waits - 1)) quota waits" >&2
        return 1
      fi
      local secs; secs="$(quota_wait_secs "$log")"
      echo "== quota exhausted; sleeping ${secs}s until reset, then retry [$task/$cond/trial-$trial, $waits/$MAX_QUOTA_WAITS]"
      sleep "$secs"
      continue
    fi

    echo "!! no reward and not quota-blocked: $task/$cond/trial-$trial — skipping" >&2
    return 1
  done
}

for model in "${MODELS[@]}"; do
  for task in "${TASKS[@]}"; do
    for cond in "${CONDS[@]}"; do
      for trial in $(seq 1 "$TRIALS"); do
        run_one "$model" "$task" "$cond" "$trial" || true
      done
    done
  done
done

echo "Done. Raw rewards under results/raw/. Re-run to resume any skipped cells."
echo "Next: uv run python scripts/aggregate.py"
