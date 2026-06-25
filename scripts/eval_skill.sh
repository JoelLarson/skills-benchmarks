#!/usr/bin/env bash
# End-to-end skill evaluator:
#   fetch skill -> Codex proposes benchmarks (you confirm) -> cost/time estimate
#   -> run no-skill vs with-skill on slices (codex-acp on Podman) -> consolidated report.
#
# Usage:
#   scripts/eval_skill.sh <skill-source> [--benchmarks a,b] [--tasks-per-bench N]
#                         [--trials T] [--model M] [--name NAME] [--yes]
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

SOURCE=""; BENCHMARKS=""; TPB=10; TRIALS=3; YES=0; MODEL="gpt-5.5"; NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmarks) BENCHMARKS="$2"; shift 2;;
    --tasks-per-bench) TPB="$2"; shift 2;;
    --trials) TRIALS="$2"; shift 2;;
    --model) MODEL="$2"; shift 2;;
    --name) NAME="$2"; shift 2;;
    --yes) YES=1; shift;;
    -*) echo "unknown flag: $1" >&2; exit 1;;
    *) SOURCE="$1"; shift;;
  esac
done
[[ -n "$SOURCE" ]] || { echo "usage: eval_skill.sh <skill-source> [--benchmarks a,b] [--tasks-per-bench N] [--trials T] [--model M] [--yes]" >&2; exit 1; }

# 1. Fetch skill -------------------------------------------------------------
SKILLS_DIR="$(bash scripts/fetch_skill.sh "$SOURCE" ${NAME:+"$NAME"} | tail -1)"
SKILL_NAME="$(basename "$SKILLS_DIR")"
RES="results/$SKILL_NAME"
mkdir -p "$RES"
echo "Skill: $SKILL_NAME   (skills-dir: $SKILLS_DIR)"

# 2. Select benchmarks -------------------------------------------------------
if [[ -z "$BENCHMARKS" ]]; then
  bash scripts/select_benchmarks.sh "$SKILLS_DIR" "$RES/selection.json"
  if [[ "$(python3 -c "import json;print(json.load(open('$RES/selection.json'))['software_related'])")" != "True" ]]; then
    echo "Selector: this skill is not software-related — no benchmarks to run."
    python3 -c "import json;print('Note:', json.load(open('$RES/selection.json'))['note'])"
    exit 0
  fi
  python3 - "$RES/selection.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("\nProposed benchmarks:")
for s in d["selections"]:
    rec = "*" if s.get("recommended") else " "
    print(f"  [{rec}] {s['env']:<26} fit={s['fit_score']:.2f}  {s['reason'][:88]}")
print("  (* = recommended)")
PY
  CHOSEN="$(python3 -c "import json;d=json.load(open('$RES/selection.json'));print(','.join([s['env'] for s in d['selections'] if s['recommended']][:3]))")"
  if [[ "$YES" != "1" ]]; then
    read -rp "Benchmarks to run [$CHOSEN]: " ans || true
    [[ -n "${ans:-}" ]] && CHOSEN="$ans"
  fi
else
  CHOSEN="$BENCHMARKS"
fi
IFS=',' read -ra BENCH_ARR <<< "$CHOSEN"
[[ ${#BENCH_ARR[@]} -gt 0 ]] || { echo "No benchmarks selected." >&2; exit 1; }
echo "Will run: ${BENCH_ARR[*]}"

# 3. Estimate + confirm ------------------------------------------------------
python3 scripts/estimate.py "${BENCH_ARR[@]}" --tasks-per-bench "$TPB" --trials "$TRIALS"
if [[ "$YES" != "1" ]]; then
  read -rp "Proceed with these runs? [y/N]: " go || true
  [[ "${go:-}" == "y" || "${go:-}" == "Y" ]] || { echo "Aborted before running."; exit 0; }
fi

# 4. Run no_skill vs with_skill ---------------------------------------------
for bench in "${BENCH_ARR[@]}"; do
  spec="$(bench hub list --provider harbor --search "$bench" --limit 10 --json 2>/dev/null \
          | python3 scripts/bench_spec.py "$bench" "$TPB")" || {
    echo "WARN: could not resolve $bench; skipping" >&2; continue; }
  eval "$spec"   # sets REPO REF SRCPATH TASKS
  read -ra TASK_ARR <<< "$TASKS"
  [[ ${#TASK_ARR[@]} -gt 0 ]] || { echo "WARN: no tasks for $bench; skipping" >&2; continue; }
  inc=(); for t in "${TASK_ARR[@]}"; do inc+=(--include "$t"); done

  for cond in no_skill with_skill; do
    skillargs=(--skill-mode no-skill)
    [[ "$cond" == "with_skill" ]] && skillargs=(--skill-mode with-skill --skills-dir "$SKILLS_DIR")
    for trial in $(seq 1 "$TRIALS"); do
      jd="jobs/$SKILL_NAME/$bench/$cond/trial-$trial"; rm -rf "$jd"
      echo ">> $bench | $cond | trial $trial (${#TASK_ARR[@]} tasks)"
      scripts/bench-podman.sh eval run --source-repo "$REPO" --source-ref "$REF" \
        --source-path "$SRCPATH" "${inc[@]}" --agent codex-acp --model "$MODEL" \
        --sandbox docker "${skillargs[@]}" --jobs-dir "$jd" || true
      # normalize each sub-task reward into the results tree
      while IFS= read -r rf; do
        sub="$(basename "$(dirname "$(dirname "$rf")")")"
        dest="$RES/raw/$MODEL/$bench/$cond/trial-$trial/$sub"; mkdir -p "$dest"
        cp "$rf" "$dest/reward.txt"
      done < <(find "$jd" -name reward.txt 2>/dev/null)
    done
  done
done

# 5. Aggregate + report ------------------------------------------------------
uv run python scripts/aggregate.py --results-dir "$RES"
sel_arg=(); [[ -f "$RES/selection.json" ]] && sel_arg=(--selection "$RES/selection.json")
uv run python scripts/build_site.py --summary "$RES/summary.json" --out "$RES/site" \
  --title "$SKILL_NAME" "${sel_arg[@]}"

echo ""
echo "Done. Report: $RES/site/index.html   Summary: $RES/summary.json"
