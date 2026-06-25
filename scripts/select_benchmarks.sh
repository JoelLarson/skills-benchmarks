#!/usr/bin/env bash
# Ask Codex which harbor benchmarks fit a skill. Writes a schema-validated JSON to <out>.
# Uses the host `codex` CLI (your codex login), not bench — pure reasoning, no sandbox tools.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

SKILLS_DIR="${1:?usage: select_benchmarks.sh <skills-dir> <out.json>}"
OUT="${2:?usage: select_benchmarks.sh <skills-dir> <out.json>}"

SKILL_MD="$(find "$SKILLS_DIR" -name SKILL.md | head -1)"
[[ -f "$SKILL_MD" ]] || { echo "select_benchmarks: no SKILL.md under $SKILLS_DIR" >&2; exit 1; }

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

echo "select_benchmarks: fetching harbor catalog..." >&2
bench hub list --provider harbor --limit 500 --json > "$WORK/catalog_full.json" 2>/dev/null

# Condense: keep name, task count, description (drop the big per-task lists).
python3 - "$WORK/catalog_full.json" > "$WORK/catalog.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
envs = data if isinstance(data, list) else data.get("environments", data.get("results", []))
out = []
for e in envs:
    tasks = e.get("tasks")
    n = len(tasks) if isinstance(tasks, list) else e.get("task_count", e.get("tasks", 0))
    out.append({"name": e.get("name"), "tasks": n, "description": (e.get("description") or "")[:200]})
json.dump(out, sys.stdout)
PY

cat > "$WORK/schema.json" <<'JSON'
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "software_related": {"type": "boolean"},
    "note": {"type": "string"},
    "selections": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "properties": {
          "env": {"type": "string"},
          "reason": {"type": "string"},
          "fit_score": {"type": "number"},
          "recommended": {"type": "boolean"}
        },
        "required": ["env", "reason", "fit_score", "recommended"]
      }
    }
  },
  "required": ["software_related", "note", "selections"]
}
JSON

PROMPT="You are selecting benchmarks to measure whether an agent SKILL helps or HURTS a coding model.

SKILL UNDER TEST (SKILL.md):
---
$(cat "$SKILL_MD")
---

AVAILABLE BENCHMARKS (harbor registry; name, task count, description) as JSON:
$(cat "$WORK/catalog.json")

Pick the benchmarks (by exact 'name') most likely to REVEAL the skill's effect — whether it
improves OR regresses the model. Prefer deterministic, verifiable, error-prone CODING benchmarks
where the skill's behavior plausibly changes pass-rate. Set fit_score 0..1. Mark up to 3 as
recommended=true. If the skill is NOT about software/coding, set software_related=false, leave
selections empty, and explain in note. Only use 'env' names that appear in the list above."

echo "select_benchmarks: asking Codex (gpt-5.5) to choose..." >&2
codex exec --output-schema "$WORK/schema.json" --output-last-message "$WORK/out.json" \
  "$PROMPT" >/dev/null 2>"$WORK/codex.err" || {
    echo "select_benchmarks: codex exec failed:" >&2; cat "$WORK/codex.err" >&2; exit 1; }

# Validate JSON before saving.
python3 -c "import json,sys; json.load(open('$WORK/out.json'))" 2>/dev/null || {
  echo "select_benchmarks: codex output was not valid JSON. Raw:" >&2
  cat "$WORK/out.json" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"
cp "$WORK/out.json" "$OUT"
echo "select_benchmarks: wrote $OUT" >&2
