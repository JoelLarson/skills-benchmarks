#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh

# Use Podman via a docker->podman shim (bench has no --sandbox podman).
if [[ "${USE_PODMAN:-0}" == "1" ]]; then
  command -v podman >/dev/null || { echo "USE_PODMAN=1 but podman not found" >&2; exit 1; }
  export PATH="$(pwd)/scripts/podman:$PATH"
  export PODMAN_SOCKET DOCKER_HOST="unix://${PODMAN_SOCKET}"
fi

SKILLS_DIR="skills"

run_one() {
  local model="$1" task="$2" cond="$3" trial="$4"

  local extra=()
  if [[ "$cond" == "with_skill" ]]; then
    extra=(--skill-mode with-skill --skills-dir "$SKILLS_DIR")
  else
    extra=(--skill-mode no-skill)
  fi

  local model_args=()
  [[ "$model" != "default" ]] && model_args=(--model "$model")
  [[ -n "${REASONING_EFFORT:-}" ]] && model_args+=(--reasoning-effort "$REASONING_EFFORT")

  # A unique, fresh jobs dir per trial guarantees an independent run (bench resumes
  # — i.e. skips — tasks already present in a jobs dir) and a deterministic reward path.
  local jobsdir="jobs/$model/$task/$cond/trial-$trial"
  rm -rf "$jobsdir"

  echo ">> $AGENT | $model | $task | $cond | trial $trial"
  bench eval run --tasks-dir "tasks/$task" --agent "$AGENT" \
    "${model_args[@]}" --sandbox docker "${extra[@]}" --jobs-dir "$jobsdir"

  local src dest timing
  src="$(find "$jobsdir" -name reward.txt | head -1)"
  if [[ -z "$src" ]]; then
    echo "ERROR: no reward.txt under $jobsdir" >&2
    exit 1
  fi
  dest="results/raw/$model/$task/$cond/trial-$trial"
  mkdir -p "$dest"
  cp "$src" "$dest/reward.txt"

  # Capture timing/token data if bench wrote it (optional; aggregate may use later).
  timing="$(find "$jobsdir" -name timing.json | head -1)"
  [[ -n "$timing" ]] && cp "$timing" "$dest/timing.json" || true
}

for model in "${MODELS[@]}"; do
  for task in "${TASKS[@]}"; do
    for cond in no_skill with_skill; do
      for trial in $(seq 1 "$TRIALS"); do
        run_one "$model" "$task" "$cond" "$trial"
      done
    done
  done
done

echo "Done. Raw rewards under results/raw/. Next: uv run python scripts/aggregate.py"
