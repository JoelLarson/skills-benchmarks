# skill-benchmarks

Benchmarks the `make-no-mistakes` skill with [SkillsBench](https://github.com/benchflow-ai/skillsbench),
comparing an unprompted model against the same model with the skill injected.

## Prereqs
- **Podman** with its Docker-API socket active
  (`systemctl --user enable --now podman.socket`). bench has no `--sandbox podman`,
  so a `docker`→`podman` shim (`scripts/podman/`) is used; `USE_PODMAN=1` is the
  default. Set `USE_PODMAN=0` in `scripts/config.sh` to use real Docker instead.
- **Compose v2** binary (bench uses `docker compose ... up --wait`):
  `curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o ~/.local/bin/docker-compose && chmod +x ~/.local/bin/docker-compose`
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- The agent under test is **Codex** (`codex-acp`): either `OPENAI_API_KEY` or a
  Codex subscription login (`~/.codex/auth.json` via `codex login`). No Anthropic
  key is needed for runs.

Verify the backend: `bash scripts/podman-setup.sh`

## Setup
```bash
git submodule update --init --recursive
uv tool install "benchflow>=0.6.2,<0.7"
(cd skillsbench && uv sync --locked)
uv sync
```

## Evaluate any skill end-to-end
One command fetches a skill, has Codex propose fitting benchmarks (you confirm),
prints a cost/time estimate, runs no-skill vs with-skill on small slices, and
writes a consolidated report:
```bash
bash scripts/eval_skill.sh <skill-source>           # git repo / gist URL / local dir / .skill
# options: --benchmarks a,b  --tasks-per-bench N  --trials T  --model M  --yes
```
- Codex (your `codex login`) picks benchmarks from the harbor registry based on the
  skill's `SKILL.md`; you approve/edit before anything runs.
- Skip selection with `--benchmarks humanevalfix,quixbugs`; skip all prompts with `--yes`.
- `--force-inject`: for **global-directive** skills that Codex won't auto-activate
  (e.g. `make-no-mistakes`), append the skill's body to every `with_skill` task
  prompt so its guidance is always applied. The `no_skill` baseline is unchanged,
  so the only difference between conditions is the injected directive. Without this,
  Codex only loads a skill when a `$name` mention or command-pattern triggers it, so
  a passive skill shows no effect.
- Report lands at `results/<skill>/site/index.html` (per-benchmark pass-rate, Skill
  Lift, regressions, plus Codex's selection rationale).

### Long runs that survive quota exhaustion
Runs are **per-task, resumable, and quota-resilient** (both `eval_skill.sh` and
`run_pilot.sh`). When Codex hits its usage limit, the current cell waits until the
reset window (parsed from Codex's "try again at H:MM", else `QUOTA_FALLBACK_WAIT`)
and retries — rather than failing every remaining cell. Knobs (env vars):
- `RESUME=1` (default) — skip cells whose `reward.txt` already exists; just re-run
  the same command to continue a run that was interrupted or partially completed.
- `MAX_QUOTA_WAITS=48` — give up on a cell after this many consecutive quota waits.
- `QUOTA_FALLBACK_WAIT=1800` — seconds to wait when no reset time is in the log.

For a multi-hour benchmark, run it detached so it keeps sleeping/retrying across
quota windows:
```bash
nohup bash scripts/eval_skill.sh skills/make-no-mistakes \
  --benchmarks swebench-verified --tasks-per-bench 10 --trials 3 --force-inject --yes \
  > eval.log 2>&1 &
tail -f eval.log     # watch progress; re-run the same command anytime to resume
```

Example (tiny smoke, no prompts):
```bash
bash scripts/eval_skill.sh skills/make-no-mistakes \
  --benchmarks humanevalfix --tasks-per-bench 2 --trials 1 --yes
```

## Run the fixed three-task pilot
The three local tasks are the cheapest, most controlled testbed (tiny image, one
short Codex call each) and `arithmetic-trap` already fails at baseline — ideal for
proving a precision skill without burning quota. Force-inject works here too:
```bash
FORCE_INJECT=1 bash scripts/run_pilot.sh        # appends the skill directive to with_skill prompts
# focus the cheapest high-signal task:
FORCE_INJECT=1 TASKS=arithmetic-trap TRIALS=3 bash scripts/run_pilot.sh
```

```bash
bash scripts/run_pilot.sh          # local, uses Docker + API key
uv run python scripts/aggregate.py # -> results/summary.json
uv run python scripts/build_site.py # -> site/index.html (preview locally)
```

Push to `main`; GitHub Actions renders `results/summary.json` into the published site.

## Publishing
GitHub Pages is served via Actions. In repo Settings → Pages, set Source to
"GitHub Actions". The site rebuilds from `results/summary.json` on every push to
`main`.
