# Skill Evaluator — Implementation Plan

**Goal:** One command, `bash scripts/eval_skill.sh <skill-source>`, that fetches a skill,
has Codex propose fitting benchmarks (you confirm), prints a cost/time estimate, runs
no-skill vs with-skill on small slices, and produces a consolidated report.

**Reuses:** Podman shim, Codex OAuth wiring, `bench eval run`, `aggregate.py`, `build_site.py`.

## Grounded facts
- Run a benchmark slice: `bench eval run --source-env harbor/<env> --include <task> [...]`
  (`--include` repeatable; task names come from `bench hub list --provider harbor --json`).
- Selection model: `codex exec --output-schema <schema.json> --output-last-message <out> "<prompt>"`
  returns a schema-validated JSON final message.
- Skill-mode flags (`--skill-mode`, `--skills-dir`) apply to harbor envs.

## Data model
`results/<skill>/raw/<model>/<benchmark>/<condition>/trial-<n>/<subtask>/reward.txt`
- Generalizes the existing layout by adding a `<subtask>` level. `aggregate.py` is changed
  to count **all** `reward.txt` under a condition dir recursively (works for both the old
  one-reward layout and the new sub-task layout).

## Tasks

### Task 1: Generalize `aggregate.py` to recurse for rewards
- Modify `tally()` to use `cond_dir.rglob("reward.txt")` (count passes/total over all found).
- Existing test stays green (old layout: `cond/trial-n/reward.txt`).
- Add `tests/test_aggregate_subtasks.py`: build `cond/trial-1/sub-a/reward.txt`=1,
  `sub-b/reward.txt`=0 → passes=1, trials=2, pass_rate=0.5.
- Run `uv run pytest -q`; commit.

### Task 2: `scripts/fetch_skill.sh <source> [--name X]`
- Detect source:
  - `*.git` or `github.com/<o>/<r>` (no file) → `git clone --depth 1` to a temp, find first
    `SKILL.md` (prefer `skills/*/SKILL.md`, else root, else any).
  - `gist.github.com/<u>/<id>` → fetch `https://gist.githubusercontent.com/<u>/<id>/raw`.
  - other `http(s)://...` → `curl` the raw file.
  - local dir → copy; `*.skill`/`*.zip` → `unzip`.
- Normalize into `skills-eval/<name>/SKILL.md` (+ any `references/`,`scripts/` if a dir/repo).
- Print the resolved skill dir path (stdout, last line) for the orchestrator to capture.
- Verify with a local-dir case and a git/gist case; commit.

### Task 3: `scripts/select_benchmarks.sh <skill-dir> <out.json>`
- Build catalog: `bench hub list --provider harbor --json` → condense to `{name,tasks,description}`
  (drop task lists) via python.
- Write a JSON schema (selections[]{env,reason,fit_score 0-1,recommended bool}, software_related bool, note).
- Prompt = SKILL.md + condensed catalog + instructions ("pick benchmarks that would reveal whether
  this skill helps OR hurts; prefer deterministic, error-prone, verifiable coding benchmarks; if the
  skill is not about software, set software_related=false").
- `codex exec --output-schema schema.json --output-last-message <out.json> "<prompt>"` (uses Codex OAuth
  via config.sh env). Validate JSON; on failure, save raw output and exit non-zero with a message.
- Commit.

### Task 4: `scripts/estimate.py <selection.json> --tasks-per-bench N --trials T`
- runs = chosen_benchmarks × N × T × 2 (conditions).
- Per-benchmark avg minutes from a small lookup (function-level≈2, swe/agentic≈8, default≈3),
  matched by name substring (swe/lancer/contest/terminal → heavy).
- Print a table: per-benchmark runs + est minutes, and totals. No $ (Codex is subscription/quota);
  report estimated agent-runs and wall-clock, plus token totals after the run.
- Commit.

### Task 5: `scripts/eval_skill.sh <source>` orchestrator
Flags: `--benchmarks a,b` (skip selection), `--tasks-per-bench 10`, `--trials 3`, `--yes` (no prompts),
`--model gpt-5.5`.
1. `fetch_skill.sh` → SKILL_DIR.
2. `select_benchmarks.sh` → `results/<skill>/selection.json`; if `software_related=false`, print the
   note and exit 0 (report "not a software skill — no benchmarks run").
3. Print ranked proposal; unless `--yes`, ask which to run (default = `recommended` ones, max 3).
4. `estimate.py` → print estimate; unless `--yes`, confirm before stage 3.
5. For each benchmark: read its task names from catalog JSON, take first N via `--include`; run
   `no_skill` + `with_skill` × trials with `--agent codex-acp --model <model> --sandbox docker`
   (Podman env from config.sh); copy each sub-task `reward.txt` + `timing.json` into the data-model path.
6. `aggregate.py --results-dir results/<skill>` → `summary.json`.
7. `build_site.py` (skill-aware title + selection rationale) → `results/<skill>/site/index.html`.
- Reuse config.sh for AGENT/Podman/Codex-OAuth; `set -euo pipefail`.

### Task 6: `build_site.py` — skill-aware report
- Accept `--title` and optional `--selection <selection.json>` to render Codex's rationale + caveats.
- Relabel the table column "Task" → "Benchmark". Keep existing test green (column text change only in
  a new heading; update assertion or keep "Regressions"/model/lift assertions).
- Add `tests/` assertion for rationale rendering when `--selection` given.
- Commit.

### Task 7: End-to-end smoke (cheap)
- `bash scripts/eval_skill.sh skills/make-no-mistakes --benchmarks humanevalfix --tasks-per-bench 2 --trials 1`
  (skip Codex selection via `--benchmarks`; tiny slice) → confirm results + site render.
- Then a real selection smoke: `select_benchmarks.sh skills/make-no-mistakes /tmp/sel.json` and eyeball.
- Document usage in README + `docs/REMAINING.md`.

## Risks / handling
- **Codex JSON parse**: `--output-schema` enforces shape; on parse failure save raw + manual `--benchmarks`.
- **Cost**: estimate + confirm gate (Task 4/5); small-slice defaults; heavy-env minutes flagged.
- **Big image pulls**: first run per benchmark slow — noted in progress output.
- **Non-software skills**: selector returns `software_related=false` → report + stop.
- **`--include` task names**: pulled from catalog JSON; if an env names tasks differently, fall back to
  `--source-env-num-examples`/first-N (handled in run step).
