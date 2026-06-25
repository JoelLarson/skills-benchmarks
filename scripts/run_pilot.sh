#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/config.sh

SKILLS_DIR="skills"

newest_reward() {
  # Print the most recently modified reward.txt matching the configured glob.
  shopt -s globstar nullglob
  local newest="" f
  for f in $BENCH_REWARD_GLOB; do
    [[ -z "$newest" || "$f" -nt "$newest" ]] && newest="$f"
  done
  printf '%s' "$newest"
}

run_one() {
  local model="$1" task="$2" cond="$3" trial="$4"
  local extra=()
  if [[ "$cond" == "with_skill" ]]; then
    extra=(--skill-mode with-skill --skills-dir "$SKILLS_DIR")
  else
    extra=(--skill-mode no-skill)
  fi

  echo ">> $model | $task | $cond | trial $trial"
  bench eval run --tasks-dir "tasks/$task" --agent claude-agent-acp \
    --model "$model" --sandbox docker "${extra[@]}"

  local src dest
  src="$(newest_reward)"
  if [[ -z "$src" ]]; then
    echo "ERROR: no reward.txt found via glob '$BENCH_REWARD_GLOB'" >&2
    exit 1
  fi
  dest="results/raw/$model/$task/$cond/trial-$trial"
  mkdir -p "$dest"
  cp "$src" "$dest/reward.txt"
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
