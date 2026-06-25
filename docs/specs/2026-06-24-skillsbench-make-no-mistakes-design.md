# Benchmarking `make-no-mistakes` with SkillsBench

**Date:** 2026-06-24
**Status:** Approved design — ready for implementation planning

## Summary

A repeatable harness that measures whether the `make-no-mistakes` agent skill
changes model accuracy — **specifically watching for whether it makes the model
perform _worse_** — by running SkillsBench's `no-skill` vs `with-skill`
conditions over a small set of error-prone, deterministically-checkable tasks,
across one or more models, and publishing the comparison via GitHub Pages.

The skill under test (`make-no-mistakes`,
<https://gist.github.com/pashov/36122682738b10a4b90a9736b6674dc2>) is a
general-purpose "be careful / double-check everything" precision nudge. It is
domain-agnostic, so the benchmark uses a **mixed spread** of task types rather
than one domain.

## Hypothesis & framing

This is a **regression-detection** study, not a "prove the skill helps" study.

- The only variable is the **presence of the skill**. Both conditions use the
  same neutral task prompt with no extra user instructions: an *unprompted
  model* vs *the same unprompted model with the skill auto-injected*.
- Skill Lift is treated as **two-sided**. A negative delta is a first-class,
  reportable result.
- Tasks are selected for being *generally error-prone*, **not** cherry-picked to
  favor the skill — cherry-picking would bias toward a positive finding and
  defeat the purpose.
- "Worse" includes more than accuracy: a run that keeps the same pass rate but
  costs more tokens / time (from over-caution / overthinking) is also a
  degradation, so cost/tokens/wall-clock are captured and reported.

## Tool choice

Reuse **SkillsBench** (`github.com/benchflow-ai/skillsbench`). Its
`--skill-mode no-skill | with-skill` + `--skills-dir` design is purpose-built for
the base-vs-base+skill comparison, with deterministic verifiers in a Docker
sandbox. ProgramBench was rejected (poor fit for a general precision skill); the
already-installed `skill-creator` eval loop was rejected in favor of
SkillsBench's deterministic, reproducible verifiers.

## Architecture

### Components

1. **Upstream SkillsBench** — added as a **pinned git submodule** (e.g. tag
   `skillsbench-v1.1`) under `skillsbench/`, with a `.gitignore` fallback if
   vendoring is undesired. Installed with
   `uv tool install "benchflow>=0.6.2,<0.7"` + `uv sync --locked`.
   Prereqs: Python 3.12+, Docker, `ANTHROPIC_API_KEY` (later other provider keys
   as more models are added).

2. **Packaged skill** — the gist converted to a SkillsBench-consumable folder
   `skills/make-no-mistakes/SKILL.md` (frontmatter `name` + `description`, then
   body). This folder is what `--skills-dir skills/` injects in `with-skill`
   mode.

3. **Three tasks (mixed spread)** — each a full SkillsBench task package under
   `tasks/`:
   - **`arithmetic-trap`** — multi-step arithmetic / unit conversion with a trap
     where careless order-of-operations yields a plausible-but-wrong number;
     verifier checks the exact value.
   - **`subtle-bug`** — small program with an off-by-one / boundary bug to fix; a
     hidden `pytest` edge-case suite is the verifier.
   - **`parse-constraint`** — parse structured input and answer a constraint
     question where skimming yields a wrong-but-plausible answer; exact-match
     verifier. This task is deliberately *simple enough that over-caution could
     backfire*, giving the study a chance to observe degradation.

   Each package mirrors the verified upstream layout:
   ```
   tasks/<id>/
     task.md                  # schema_version 1.3; metadata/verifier/agent/environment
                              # frontmatter; prompt is NEUTRAL — never names the skill,
                              # never coaxes carefulness/precision
     environment/Dockerfile   # FROM ubuntu:24.04 + minimal deps
     environment/<inputs>     # bundled input files, if any
     oracle/solve.sh          # reference solution (must pass the verifier)
     verifier/test.sh         # runs pytest -> writes 1/0 to /logs/verifier/reward.txt
     verifier/test_outputs.py # the assertions
   ```
   Difficulty is tuned to the **medium-hard, mistake-prone** band to avoid a
   ceiling (baseline already 100%) or floor (both conditions fail). Difficulty is
   adjusted after the oracle gate and the first baseline run.

4. **Run harness** — `scripts/run_pilot.sh`, parametrized over
   **model × condition × trial**:
   - Models: a list, starting with `claude-sonnet-4-6`; more added later.
   - Conditions: `no-skill`, `with-skill`.
   - Trials: 3 (a `--n-trials` upstream flag is **unverified**, so trials are
     driven by a shell loop).
   ```
   bench eval run --tasks-dir tasks/<id> --agent claude-agent-acp \
     --model <model> --sandbox docker --skill-mode no-skill
   bench eval run --tasks-dir tasks/<id> --agent claude-agent-acp \
     --model <model> --sandbox docker --skill-mode with-skill --skills-dir skills/
   ```
   Pilot size: 3 tasks × 2 conditions × 3 trials × 1 model = **18 runs**.

5. **Aggregation** — `scripts/aggregate.py` reads each run's scalar reward from
   `/logs/verifier/reward.txt` plus available timing/token data, and writes
   `results/*.json` (raw + aggregated). No built-in upstream report command was
   verified, so reporting is ours.

6. **Site builder** — `scripts/build_site.py` renders `results/*.json` into a
   static `site/` (per-model breakdown, per-task pass rates, Skill Lift,
   regression count, cost/time deltas).

7. **Publishing** — `.github/workflows/pages.yml` renders `results/*.json` into
   `site/` and deploys to **GitHub Pages via GitHub Actions** on push to `main`.
   The expensive eval runs are **never** in CI — only the cheap render+deploy.

### Data flow

```
gist ─► skills/make-no-mistakes/SKILL.md ─┐
                                          ├─► bench eval run (local, Docker)
tasks/<id>/ ──────────────────────────────┘        │
                                                    ▼
                                  /logs/verifier/reward.txt (+ timing/tokens)
                                                    │  scripts/aggregate.py
                                                    ▼
                                          results/*.json (committed)
                                                    │  CI: scripts/build_site.py
                                                    ▼
                                          site/  ──► GitHub Pages
```

## Metrics (reported per model)

| Metric | Definition |
| --- | --- |
| Pass rate (per condition) | passed trials ÷ total trials, per task and overall |
| Skill Lift (Δ, pp) | with-skill pass rate − no-skill pass rate (two-sided) |
| Regression count | task-trials the baseline passed but the skill failed |
| Token delta | median tokens with-skill − no-skill |
| Time delta | median wall-clock with-skill − no-skill |

## Testing

- **Oracle gate** — `bench eval run --agent oracle --sandbox docker` per task
  must pass before any measurement, proving the task is solvable and its verifier
  correct.
- **Negative control** — a deliberately-wrong solution must score 0, proving the
  verifier actually discriminates.
- **Aggregation dry-run** — `aggregate.py` and `build_site.py` validated against
  synthetic `reward.txt` / results fixtures before real runs.

## Validity caveats (reported alongside results)

- `make-no-mistakes` is a generic "be careful" nudge; lift measures whether *this
  careful-mode skill* helps/hurts on error-prone tasks — not that it beats any
  other instruction.
- Upstream docs imply but do not explicitly state the skill is *fully* absent
  from context in `no-skill` mode (**unverified**); we trust the injection model
  and sanity-check behavior.
- A 3×3 pilot yields wide confidence intervals; results are **directional**.
  Scale up (more tasks/trials/models) if a signal appears.
- A `--n-trials` flag and a built-in report/leaderboard command are both
  **unverified** upstream; the harness does not depend on either.

## Out of scope (YAGNI)

- ProgramBench integration.
- The full 87-task SkillsBench suite (we author our own small task set).
- Statistical machinery beyond simple pass rates + paired deltas for the pilot
  (bootstrap CIs / McNemar can come later if the pilot warrants scaling).
```

