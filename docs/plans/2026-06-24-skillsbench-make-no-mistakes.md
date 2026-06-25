# SkillsBench `make-no-mistakes` Benchmark — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable harness that runs SkillsBench `no-skill` vs `with-skill` over three error-prone tasks to detect whether the `make-no-mistakes` skill changes (especially degrades) model accuracy, and publishes the comparison to GitHub Pages.

**Architecture:** Expensive evals run locally via the SkillsBench CLI (`bench`, Docker sandbox) and write a normalized `results/raw/<model>/<task>/<condition>/trial-<n>/reward.txt` tree. Two stdlib-only Python scripts turn that tree into `results/summary.json` and then a static `site/`. A GitHub Actions workflow renders + deploys the site on every push to `main` — CI never runs the costly evals.

**Tech Stack:** SkillsBench / `benchflow` CLI, Docker, Python 3.12 (stdlib only for harness code), `pytest` (dev only), `uv`, GitHub Actions Pages.

---

## Background the engineer needs

- **SkillsBench** is an external benchmark. The CLI is `bench` (from the `benchflow` package). A *task* is a directory package; an *eval run* executes an agent inside a Docker container, the agent produces output files in `/root/`, and a *verifier* script writes a scalar reward (`1` pass / `0` fail) to `/logs/verifier/reward.txt`.
- **The only experimental variable is the skill's presence.** Task prompts must be neutral: never name the skill, never tell the model to "be careful" or "double-check". `no-skill` runs the plain model; `with-skill` injects `skills/make-no-mistakes/` via `--skills-dir`.
- **This is regression detection.** A *negative* Skill Lift is a valid, important result. We also watch token/time cost, since "same accuracy but slower" is also a degradation.
- **Three facts are UNVERIFIED upstream** and the harness must not hard-depend on them: (a) a `--n-trials` flag (we loop in shell instead); (b) the exact *host-side* path where `bench` writes `reward.txt` (we discover it once in Task 9 and copy into our own normalized tree); (c) a built-in report command (we render ourselves).
- The design spec lives at `docs/specs/2026-06-24-skillsbench-make-no-mistakes-design.md`. Read it first.

## File structure

| Path | Responsibility |
| --- | --- |
| `.gitignore` | Ignore generated `site/`, venvs, caches |
| `pyproject.toml` | Declare Python 3.12 + `pytest` dev dep for harness tests |
| `README.md` | How to run the benchmark locally |
| `skillsbench/` | Pinned git submodule (upstream SkillsBench) |
| `skills/make-no-mistakes/SKILL.md` | The skill under test, packaged for `--skills-dir` |
| `tasks/arithmetic-trap/` | Multi-step arithmetic task package |
| `tasks/subtle-bug/` | Off-by-one binary-search fix task package |
| `tasks/parse-constraint/` | Filter-then-max parsing task package |
| `scripts/config.sh` | Shared config: model list, the discovered reward glob |
| `scripts/run_pilot.sh` | Loops model × task × condition × trial; normalizes outputs |
| `scripts/aggregate.py` | `results/raw/` → `results/summary.json` |
| `scripts/build_site.py` | `results/summary.json` → `site/index.html` |
| `tests/test_aggregate.py` | Tests for `aggregate.py` |
| `tests/test_build_site.py` | Tests for `build_site.py` |
| `tests/fixtures/` | Synthetic reward trees + summary for tests |
| `results/` | Committed raw rewards + `summary.json` (CI input) |
| `.github/workflows/pages.yml` | Render + deploy site to Pages |

---

## Task 1: Repo scaffolding

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `results/.gitkeep`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# generated site (built by CI from results/)
/site/

# python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# bench scratch output (we copy rewards into results/raw ourselves)
/.benchflow/
/runs/
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "skill-benchmarks"
version = "0.1.0"
description = "Benchmark agent skills with SkillsBench (no-skill vs with-skill)"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = ["pytest>=8.4.1"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Create `README.md`**

```markdown
# skill-benchmarks

Benchmarks the `make-no-mistakes` skill with [SkillsBench](https://github.com/benchflow-ai/skillsbench),
comparing an unprompted model against the same model with the skill injected.

## Prereqs
- Docker (running)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- `ANTHROPIC_API_KEY` exported

## Setup
```bash
git submodule update --init --recursive
uv tool install "benchflow>=0.6.2,<0.7"
(cd skillsbench && uv sync --locked)
uv sync
```

## Run the pilot
```bash
bash scripts/run_pilot.sh          # local, uses Docker + API key
uv run python scripts/aggregate.py # -> results/summary.json
uv run python scripts/build_site.py # -> site/index.html (preview locally)
```

Push to `main`; GitHub Actions renders `results/summary.json` into the published site.
```

- [ ] **Step 4: Create `results/.gitkeep`**

```
```
(empty file so the directory is tracked)

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml README.md results/.gitkeep
git commit -m "chore: scaffold skill-benchmarks repo"
```

---

## Task 2: Add SkillsBench as a pinned submodule

**Files:**
- Create: `.gitmodules` (via `git submodule add`)
- Create: `skillsbench/` (submodule contents)

- [ ] **Step 1: Add the submodule**

Run:
```bash
git submodule add https://github.com/benchflow-ai/skillsbench.git skillsbench
```
Expected: clones into `skillsbench/`, creates `.gitmodules`.

- [ ] **Step 2: Pin to a release tag**

Run:
```bash
cd skillsbench
git fetch --tags
git checkout skillsbench-v1.1 2>/dev/null || git tag --list 'skillsbench-*'
cd ..
```
Expected: detached HEAD at `skillsbench-v1.1`. If that exact tag does not exist, the second half prints available `skillsbench-*` tags — pick the latest stable one and `git checkout` it, then note the chosen tag in `README.md` Setup section.

- [ ] **Step 3: Install the CLI and verify it runs**

Run:
```bash
uv tool install "benchflow>=0.6.2,<0.7"
bench --help
```
Expected: `bench` help text listing subcommands including `eval` and `tasks`.

- [ ] **Step 4: Verify an upstream task validates (sanity check on bench)**

Run:
```bash
bench tasks check skillsbench/tasks/offer-letter-generator
```
Expected: a validation pass (or actionable warnings). This confirms `bench tasks check` works before we author our own tasks. If the path differs, run `ls skillsbench/tasks | head` and use any real task id.

- [ ] **Step 5: Commit**

```bash
git add .gitmodules skillsbench
git commit -m "build: vendor SkillsBench as pinned submodule"
```

---

## Task 3: Package the `make-no-mistakes` skill

**Files:**
- Create: `skills/make-no-mistakes/SKILL.md`

- [ ] **Step 1: Write the skill file**

Create `skills/make-no-mistakes/SKILL.md`:
```markdown
---
name: make-no-mistakes
description: Appends "MAKE NO MISTAKES." to every user prompt before processing it. Use this skill whenever you want Claude to be maximally precise, careful, and error-free in its responses.
---

# Make No Mistakes

Treat every user message as if it ends with "MAKE NO MISTAKES." This raises the
internal confidence bar for all outputs.

For every task:

- Double-check facts, calculations, code, and reasoning before responding.
- State uncertainty explicitly rather than guessing.
- Prioritize accuracy over speed.
- Mentally test logic step-by-step for code tasks.
- Re-derive mathematical results before committing to an answer.
- Only assert factual claims you hold with genuine confidence.

The directive applies to every prompt in the session without exception.
```

- [ ] **Step 2: Verify the folder shape `--skills-dir` expects**

Run:
```bash
ls skills/make-no-mistakes/SKILL.md && head -4 skills/make-no-mistakes/SKILL.md
```
Expected: file exists; first lines show the `---` frontmatter with `name:` and `description:`. (`--skills-dir skills/` consumes one subfolder per skill, each containing a `SKILL.md`.)

- [ ] **Step 3: Commit**

```bash
git add skills/make-no-mistakes/SKILL.md
git commit -m "feat: package make-no-mistakes skill under test"
```

---

## Task 4: Author the `arithmetic-trap` task

A widget priced $480 gets a 15% discount, then a further 20% off the reduced
price, then 8.25% tax. Correct: 480·0.85·0.80·1.0825 = **353.33**. The trap
(adding 15%+20% = 35% off) gives 337.74.

**Files:**
- Create: `tasks/arithmetic-trap/task.md`
- Create: `tasks/arithmetic-trap/environment/Dockerfile`
- Create: `tasks/arithmetic-trap/oracle/solve.sh`
- Create: `tasks/arithmetic-trap/verifier/test.sh`
- Create: `tasks/arithmetic-trap/verifier/test_outputs.py`

- [ ] **Step 1: Write `task.md`**

```markdown
---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: medium
  category: reasoning
  subcategory: arithmetic
  category_confidence: high
  task_type: [reasoning]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [arithmetic, sequential-discount, precision]
verifier:
  type: test-script
  timeout_sec: 300
  service: main
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 600
environment:
  network_mode: none
  build_timeout_sec: 600
  os: linux
  cpus: 1
  memory_mb: 1024
  storage_mb: 2048
  gpus: 0
---

A widget has a list price of $480.00.

Apply the following in order:
1. A 15% discount off the list price.
2. A further 20% discount off the price from step 1.
3. An 8.25% sales tax on the price from step 2.

Write the final price, rounded to the nearest cent, as a single number to
`/root/answer.txt` (for example: `123.45`). Write nothing else to that file.
```

- [ ] **Step 2: Write `verifier/test_outputs.py`**

```python
import os


def test_answer_correct():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        raw = f.read().strip().replace("$", "").replace(",", "")
    val = float(raw)
    assert abs(val - 353.33) < 0.005, f"expected 353.33, got {val}"
```

- [ ] **Step 3: Write `verifier/test.sh`**

```bash
#!/bin/bash
set -u
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
mkdir -p /logs/verifier
uvx --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /verifier/test_outputs.py -rA -v
PYTEST_EXIT_CODE=$?
if [ $PYTEST_EXIT_CODE -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
```

- [ ] **Step 4: Write `oracle/solve.sh`**

```bash
#!/bin/bash
echo "353.33" > /root/answer.txt
```

- [ ] **Step 5: Write `environment/Dockerfile`**

```dockerfile
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /root
```

- [ ] **Step 6: Validate the task package**

Run:
```bash
bench tasks check tasks/arithmetic-trap
```
Expected: validation passes. If it reports a missing/invalid frontmatter field, fix that field per the message (the schema is `'1.3'`; mirror any field shapes from `skillsbench/tasks/offer-letter-generator/task.md`) and re-run until clean.

- [ ] **Step 7: Run the oracle gate (must pass)**

Run:
```bash
bench eval run --tasks-dir tasks/arithmetic-trap --agent oracle --sandbox docker
```
Expected: the run reports the task **resolved** (reward `1`). This proves the task is solvable and the verifier accepts the correct answer.

- [ ] **Step 8: Negative control (must fail)**

Temporarily change `oracle/solve.sh` line to the trap value, re-run the oracle gate, confirm it fails, then revert:
```bash
sed -i 's/353.33/337.74/' tasks/arithmetic-trap/oracle/solve.sh
bench eval run --tasks-dir tasks/arithmetic-trap --agent oracle --sandbox docker   # expect reward 0
git checkout tasks/arithmetic-trap/oracle/solve.sh
```
Expected: the middle run reports **unresolved** (reward `0`), proving the verifier discriminates. The `git checkout` restores the correct `353.33`.

- [ ] **Step 9: Commit**

```bash
git add tasks/arithmetic-trap
git commit -m "feat: add arithmetic-trap benchmark task"
```

---

## Task 5: Author the `subtle-bug` task

`/root/solution.py` ships with an off-by-one binary search (`while lo < hi`
instead of `lo <= hi`) that fails single-element windows. The agent must fix it
without changing the signature.

**Files:**
- Create: `tasks/subtle-bug/task.md`
- Create: `tasks/subtle-bug/environment/Dockerfile`
- Create: `tasks/subtle-bug/environment/solution.py`
- Create: `tasks/subtle-bug/oracle/solve.sh`
- Create: `tasks/subtle-bug/verifier/test.sh`
- Create: `tasks/subtle-bug/verifier/test_outputs.py`

- [ ] **Step 1: Write `task.md`**

```markdown
---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: medium
  category: coding
  subcategory: debugging
  category_confidence: high
  task_type: [coding]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [off-by-one, binary-search, debugging]
verifier:
  type: test-script
  timeout_sec: 300
  service: main
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 600
environment:
  network_mode: none
  build_timeout_sec: 600
  os: linux
  cpus: 1
  memory_mb: 1024
  storage_mb: 2048
  gpus: 0
---

The file `/root/solution.py` defines `bsearch(arr, target)`, which should return
the index of `target` in the ascending-sorted list `arr`, or `-1` if `target` is
not present. It currently contains a bug.

Fix `bsearch` in place in `/root/solution.py`. Do not change its name or
signature. Do not add new files.
```

- [ ] **Step 2: Write the buggy `environment/solution.py`**

```python
def bsearch(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:  # bug: drops the final single-element window
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

- [ ] **Step 3: Write `verifier/test_outputs.py`**

```python
import importlib.util


def load():
    spec = importlib.util.spec_from_file_location("solution", "/root/solution.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_single_element_found():
    assert load().bsearch([5], 5) == 0


def test_single_element_missing():
    assert load().bsearch([5], 4) == -1


def test_found_at_end():
    assert load().bsearch([1, 3, 5, 7, 9], 9) == 4


def test_found_at_start():
    assert load().bsearch([1, 3, 5, 7, 9], 1) == 0


def test_two_element_second():
    assert load().bsearch([2, 4], 4) == 1


def test_missing_returns_neg_one():
    assert load().bsearch([1, 3, 5, 7, 9], 6) == -1


def test_empty():
    assert load().bsearch([], 1) == -1
```

- [ ] **Step 4: Write `verifier/test.sh`**

```bash
#!/bin/bash
set -u
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
mkdir -p /logs/verifier
uvx --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /verifier/test_outputs.py -rA -v
PYTEST_EXIT_CODE=$?
if [ $PYTEST_EXIT_CODE -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
```

- [ ] **Step 5: Write `oracle/solve.sh`**

```bash
#!/bin/bash
cat > /root/solution.py <<'PY'
def bsearch(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
PY
```

- [ ] **Step 6: Write `environment/Dockerfile`**

```dockerfile
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /root
```

- [ ] **Step 7: Validate the task package**

Run:
```bash
bench tasks check tasks/subtle-bug
```
Expected: validation passes (fix any frontmatter field it flags, mirroring `arithmetic-trap/task.md`).

- [ ] **Step 8: Confirm the shipped file is actually buggy**

Run:
```bash
python3 -c "import importlib.util as u; s=u.spec_from_file_location('b','tasks/subtle-bug/environment/solution.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.bsearch([5],5))"
```
Expected: prints `-1` (the bug). This guarantees the baseline starts from a failing state.

- [ ] **Step 9: Run the oracle gate (must pass)**

Run:
```bash
bench eval run --tasks-dir tasks/subtle-bug --agent oracle --sandbox docker
```
Expected: task **resolved** (reward `1`).

- [ ] **Step 10: Commit**

```bash
git add tasks/subtle-bug
git commit -m "feat: add subtle-bug binary-search benchmark task"
```

---

## Task 6: Author the `parse-constraint` task

Simple "filter by department, then take the max salary" question where the global
salary max is in a *different* department — a skimmer answers "Bob"; the answer
is **Carol**. Deliberately easy so over-caution can be observed backfiring.

**Files:**
- Create: `tasks/parse-constraint/task.md`
- Create: `tasks/parse-constraint/environment/Dockerfile`
- Create: `tasks/parse-constraint/environment/employees.json`
- Create: `tasks/parse-constraint/oracle/solve.sh`
- Create: `tasks/parse-constraint/verifier/test.sh`
- Create: `tasks/parse-constraint/verifier/test_outputs.py`

- [ ] **Step 1: Write `environment/employees.json`**

```json
[
  {"name": "Alice", "dept": "Engineering", "salary": 145000},
  {"name": "Bob", "dept": "Sales", "salary": 190000},
  {"name": "Carol", "dept": "Engineering", "salary": 162000},
  {"name": "Dave", "dept": "Engineering", "salary": 151000},
  {"name": "Erin", "dept": "Sales", "salary": 170000}
]
```

- [ ] **Step 2: Write `task.md`**

```markdown
---
schema_version: '1.3'
metadata:
  author_name: skill-benchmarks
  author_email: anthropic@chillwat.com
  difficulty: easy
  category: reasoning
  subcategory: data-parsing
  category_confidence: high
  task_type: [reasoning]
  modality: [text]
  interface: [cli]
  skill_type: [general]
  tags: [parsing, filter, attention]
verifier:
  type: test-script
  timeout_sec: 300
  service: main
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 600
environment:
  network_mode: none
  build_timeout_sec: 600
  os: linux
  cpus: 1
  memory_mb: 1024
  storage_mb: 2048
  gpus: 0
---

`/root/employees.json` is a JSON array of employee records, each with `name`,
`dept`, and `salary`.

Among employees in the `Engineering` department, find the one with the highest
salary. Write that employee's `name` (exactly, nothing else) to
`/root/answer.txt`.
```

- [ ] **Step 3: Write `verifier/test_outputs.py`**

```python
import os


def test_answer_is_carol():
    path = "/root/answer.txt"
    assert os.path.exists(path), "answer.txt not found"
    with open(path) as f:
        answer = f.read().strip()
    assert answer == "Carol", f"expected 'Carol', got {answer!r}"
```

- [ ] **Step 4: Write `verifier/test.sh`**

```bash
#!/bin/bash
set -u
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
mkdir -p /logs/verifier
uvx --with pytest==8.4.1 --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /verifier/test_outputs.py -rA -v
PYTEST_EXIT_CODE=$?
if [ $PYTEST_EXIT_CODE -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
```

- [ ] **Step 5: Write `oracle/solve.sh`**

```bash
#!/bin/bash
echo "Carol" > /root/answer.txt
```

- [ ] **Step 6: Write `environment/Dockerfile`**

```dockerfile
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /root
```

- [ ] **Step 7: Validate the task package**

Run:
```bash
bench tasks check tasks/parse-constraint
```
Expected: validation passes (fix flagged fields as before).

- [ ] **Step 8: Run the oracle gate (must pass)**

Run:
```bash
bench eval run --tasks-dir tasks/parse-constraint --agent oracle --sandbox docker
```
Expected: task **resolved** (reward `1`).

- [ ] **Step 9: Commit**

```bash
git add tasks/parse-constraint
git commit -m "feat: add parse-constraint benchmark task"
```

---

## Task 7: `aggregate.py` — raw rewards → summary

Reads the normalized tree
`results/raw/<model>/<task>/<condition>/trial-<n>/reward.txt` (content `1` or
`0`; `<condition>` is `no_skill` or `with_skill`) and writes `results/summary.json`.

Definitions (exact):
- `pass_rate = passes / trials` (float; `0.0` if `trials == 0`).
- `lift_pp = round((with_skill.pass_rate - no_skill.pass_rate) * 100, 1)`.
- `regressions = max(0, no_skill.passes - with_skill.passes)` per task (unpaired pilot approximation).
- Overall per model aggregates passes/trials across tasks, then applies the same formulas.

**Files:**
- Create: `tests/fixtures/raw_basic/...` (synthetic tree)
- Create: `tests/test_aggregate.py`
- Create: `scripts/aggregate.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_aggregate.py`:
```python
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_reward(base, model, task, cond, trial, value):
    d = base / "raw" / model / task / cond / f"trial-{trial}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reward.txt").write_text(f"{value}\n")


def test_aggregate_produces_summary(tmp_path):
    results = tmp_path
    m = "claude-sonnet-4-6"
    # arithmetic-trap: baseline 3/3, skill 2/3  -> lift -33.3, 1 regression
    write_reward(results, m, "arithmetic-trap", "no_skill", 1, 1)
    write_reward(results, m, "arithmetic-trap", "no_skill", 2, 1)
    write_reward(results, m, "arithmetic-trap", "no_skill", 3, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 1, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 2, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 3, 0)

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "aggregate.py"),
         "--results-dir", str(results)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr

    summary = json.loads((results / "summary.json").read_text())
    task = summary["models"][m]["tasks"]["arithmetic-trap"]
    assert task["no_skill"] == {"passes": 3, "trials": 3, "pass_rate": 1.0}
    assert task["with_skill"]["passes"] == 2
    assert task["with_skill"]["trials"] == 3
    assert task["lift_pp"] == -33.3
    assert task["regressions"] == 1

    overall = summary["models"][m]["overall"]
    assert overall["no_skill_pass_rate"] == 1.0
    assert overall["regressions"] == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_aggregate.py -v`
Expected: FAIL (`scripts/aggregate.py` does not exist → nonzero return / FileNotFoundError).

- [ ] **Step 3: Write `scripts/aggregate.py`**

```python
#!/usr/bin/env python3
"""Aggregate results/raw/<model>/<task>/<condition>/trial-N/reward.txt into summary.json."""
import argparse
import json
from pathlib import Path

CONDITIONS = ("no_skill", "with_skill")


def read_reward(trial_dir: Path) -> int:
    text = (trial_dir / "reward.txt").read_text().strip()
    return 1 if text == "1" else 0


def tally(cond_dir: Path) -> dict:
    passes = trials = 0
    if cond_dir.is_dir():
        for trial_dir in sorted(cond_dir.glob("trial-*")):
            if (trial_dir / "reward.txt").exists():
                trials += 1
                passes += read_reward(trial_dir)
    pass_rate = round(passes / trials, 4) if trials else 0.0
    return {"passes": passes, "trials": trials, "pass_rate": pass_rate}


def summarize(results_dir: Path) -> dict:
    raw = results_dir / "raw"
    models = {}
    for model_dir in sorted(p for p in raw.glob("*") if p.is_dir()):
        tasks = {}
        ns_p = ns_t = ws_p = ws_t = regr = 0
        for task_dir in sorted(p for p in model_dir.glob("*") if p.is_dir()):
            ns = tally(task_dir / "no_skill")
            ws = tally(task_dir / "with_skill")
            regressions = max(0, ns["passes"] - ws["passes"])
            tasks[task_dir.name] = {
                "no_skill": ns,
                "with_skill": ws,
                "lift_pp": round((ws["pass_rate"] - ns["pass_rate"]) * 100, 1),
                "regressions": regressions,
            }
            ns_p += ns["passes"]; ns_t += ns["trials"]
            ws_p += ws["passes"]; ws_t += ws["trials"]
            regr += regressions
        ns_rate = round(ns_p / ns_t, 4) if ns_t else 0.0
        ws_rate = round(ws_p / ws_t, 4) if ws_t else 0.0
        models[model_dir.name] = {
            "tasks": tasks,
            "overall": {
                "no_skill_pass_rate": ns_rate,
                "with_skill_pass_rate": ws_rate,
                "lift_pp": round((ws_rate - ns_rate) * 100, 1),
                "regressions": regr,
            },
        }
    return {"models": models}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    results_dir = Path(args.results_dir)
    summary = summarize(results_dir)
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {results_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_aggregate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/aggregate.py tests/test_aggregate.py
git commit -m "feat: aggregate raw rewards into summary.json"
```

---

## Task 8: `build_site.py` — summary → static site

Reads `results/summary.json` and writes `site/index.html`: one section per model
with a per-task table (baseline %, skill %, lift, regressions) and an overall
row. Stdlib only.

**Files:**
- Create: `tests/fixtures/summary_basic.json`
- Create: `tests/test_build_site.py`
- Create: `scripts/build_site.py`

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/summary_basic.json`:
```json
{
  "models": {
    "claude-sonnet-4-6": {
      "tasks": {
        "arithmetic-trap": {
          "no_skill": {"passes": 3, "trials": 3, "pass_rate": 1.0},
          "with_skill": {"passes": 2, "trials": 3, "pass_rate": 0.6667},
          "lift_pp": -33.3,
          "regressions": 1
        }
      },
      "overall": {
        "no_skill_pass_rate": 1.0,
        "with_skill_pass_rate": 0.6667,
        "lift_pp": -33.3,
        "regressions": 1
      }
    }
  }
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_build_site.py`:
```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "summary_basic.json"


def test_build_site_renders_expected_content(tmp_path):
    out_dir = tmp_path / "site"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"),
         "--summary", str(FIXTURE), "--out", str(out_dir)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr

    html = (out_dir / "index.html").read_text()
    assert "claude-sonnet-4-6" in html
    assert "arithmetic-trap" in html
    assert "-33.3" in html
    assert "Regressions" in html
    assert "make-no-mistakes" in html
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/test_build_site.py -v`
Expected: FAIL (`scripts/build_site.py` missing).

- [ ] **Step 4: Write `scripts/build_site.py`**

```python
#!/usr/bin/env python3
"""Render results/summary.json into a static site/index.html."""
import argparse
import html
import json
from pathlib import Path


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render(summary: dict) -> str:
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>make-no-mistakes benchmark</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "th,td{border:1px solid #ccc;padding:.4rem .6rem;text-align:right}"
        "th:first-child,td:first-child{text-align:left}"
        ".neg{color:#b00}.pos{color:#070}</style></head><body>",
        "<h1>make-no-mistakes &mdash; SkillsBench benchmark</h1>",
        "<p>Unprompted model vs. the same model with the "
        "<code>make-no-mistakes</code> skill injected. Negative lift means the "
        "skill made the model perform <em>worse</em>.</p>",
    ]
    for model, data in summary["models"].items():
        parts.append(f"<h2>{html.escape(model)}</h2>")
        parts.append("<table><thead><tr><th>Task</th><th>Baseline</th>"
                     "<th>With skill</th><th>Lift (pp)</th><th>Regressions</th>"
                     "</tr></thead><tbody>")
        for task, t in data["tasks"].items():
            lift = t["lift_pp"]
            cls = "neg" if lift < 0 else ("pos" if lift > 0 else "")
            parts.append(
                f"<tr><td>{html.escape(task)}</td>"
                f"<td>{pct(t['no_skill']['pass_rate'])}</td>"
                f"<td>{pct(t['with_skill']['pass_rate'])}</td>"
                f"<td class='{cls}'>{lift:+.1f}</td>"
                f"<td>{t['regressions']}</td></tr>"
            )
        o = data["overall"]
        lift = o["lift_pp"]
        cls = "neg" if lift < 0 else ("pos" if lift > 0 else "")
        parts.append(
            f"<tr><td><strong>Overall</strong></td>"
            f"<td>{pct(o['no_skill_pass_rate'])}</td>"
            f"<td>{pct(o['with_skill_pass_rate'])}</td>"
            f"<td class='{cls}'>{lift:+.1f}</td>"
            f"<td>{o['regressions']}</td></tr>"
        )
        parts.append("</tbody></table>")
    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/summary.json")
    ap.add_argument("--out", default="site")
    args = ap.parse_args()
    summary = json.loads(Path(args.summary).read_text())
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render(summary))
    print(f"wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_build_site.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_site.py tests/test_build_site.py tests/fixtures/summary_basic.json
git commit -m "feat: render summary.json into static site"
```

---

## Task 9: `run_pilot.sh` + config, with reward-path discovery

This is the one place that touches the **unverified** host-side output path of
`bench`. We discover it once, store a glob in `config.sh`, and have the loop copy
each produced `reward.txt` into our normalized `results/raw/...` tree.

**Files:**
- Create: `scripts/config.sh`
- Create: `scripts/run_pilot.sh`

- [ ] **Step 1: Do one real run and find where `bench` writes `reward.txt`**

Run:
```bash
bench eval run --tasks-dir tasks/arithmetic-trap --agent claude-agent-acp \
  --model claude-sonnet-4-6 --sandbox docker --skill-mode no-skill
find . -name reward.txt -newermt '-10 minutes' 2>/dev/null
```
Expected: prints the host path(s) of the just-written `reward.txt`. Note the directory pattern (e.g. `runs/<...>/reward.txt` or `.benchflow/<...>/reward.txt`). You will encode its parent glob in the next step.

- [ ] **Step 2: Write `scripts/config.sh`**

Set `BENCH_REWARD_GLOB` to match the directory pattern observed in Step 1 (this example uses `runs/`; replace it with the real one if different):
```bash
#!/bin/bash
# Models to evaluate (start with Sonnet; add more ids here later).
MODELS=("claude-sonnet-4-6")

# Tasks to run (directory names under tasks/).
TASKS=("arithmetic-trap" "subtle-bug" "parse-constraint")

# Trials per (model, task, condition).
TRIALS=3

# Glob that matches the newest reward.txt bench writes on the host.
# Discovered in Task 9 Step 1 — adjust the prefix if your bench writes elsewhere.
BENCH_REWARD_GLOB="runs/**/reward.txt"
```

- [ ] **Step 3: Write `scripts/run_pilot.sh`**

```bash
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
```

- [ ] **Step 4: Smoke-test the harness on a single trial**

Temporarily set the loop small and run, to confirm copying works end-to-end:
```bash
TRIALS=1 MODELS=(claude-sonnet-4-6) TASKS=(parse-constraint) bash -c '
  source scripts/config.sh; export BENCH_REWARD_GLOB
  bash scripts/run_pilot.sh' || true
ls results/raw/claude-sonnet-4-6/parse-constraint/*/trial-1/reward.txt
```
Expected: at least one `reward.txt` copied into `results/raw/...`. (Env overrides here are only for the smoke test; the committed `config.sh` keeps the full matrix.) If `newest_reward` grabs the wrong file, tighten `BENCH_REWARD_GLOB` in `config.sh`.

- [ ] **Step 5: Make scripts executable and commit**

```bash
chmod +x scripts/run_pilot.sh scripts/config.sh
git add scripts/run_pilot.sh scripts/config.sh
git commit -m "feat: pilot run harness with reward normalization"
```

---

## Task 10: GitHub Actions Pages workflow

Renders `results/summary.json` into `site/` and deploys to Pages on push to
`main`. No eval, no Docker, no API key in CI.

**Files:**
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: Publish benchmark site

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Build site
        run: python scripts/build_site.py --summary results/summary.json --out site
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Verify the workflow builds locally the same way CI will**

Run:
```bash
python scripts/build_site.py --summary tests/fixtures/summary_basic.json --out /tmp/site-check
test -f /tmp/site-check/index.html && echo OK
```
Expected: prints `OK`. (Confirms the exact command CI runs succeeds; until a real `results/summary.json` exists, CI uses whatever is committed — Task 11 commits the real one.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pages.yml
git commit -m "ci: deploy benchmark site to GitHub Pages"
```

- [ ] **Step 4: One-time repo settings (manual, document it)**

In the GitHub repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Add this note to `README.md` under a new "## Publishing" heading:
```markdown
## Publishing
GitHub Pages is served via Actions. In repo Settings → Pages, set Source to
"GitHub Actions". The site rebuilds from `results/summary.json` on every push to
`main`.
```
Then:
```bash
git add README.md
git commit -m "docs: note GitHub Pages source setting"
```

---

## Task 11: Run the pilot and publish

**Files:**
- Modify: `results/raw/**` (generated), `results/summary.json` (generated)

- [ ] **Step 1: Confirm prereqs**

Run:
```bash
docker info >/dev/null && echo "docker ok"
test -n "$ANTHROPIC_API_KEY" && echo "key set"
```
Expected: `docker ok` and `key set`.

- [ ] **Step 2: Run the full pilot (18 runs)**

Run:
```bash
bash scripts/run_pilot.sh
```
Expected: completes all `MODELS × TASKS × {no_skill,with_skill} × TRIALS` runs; `results/raw/` is populated with `reward.txt` files. This is the long/expensive step.

- [ ] **Step 3: Aggregate**

Run:
```bash
uv run python scripts/aggregate.py
cat results/summary.json
```
Expected: `results/summary.json` exists with one entry under `models.claude-sonnet-4-6` and per-task lift/regression numbers.

- [ ] **Step 4: Preview the site locally**

Run:
```bash
uv run python scripts/build_site.py
python3 -m http.server -d site 8000 &
SERVER=$!; sleep 1; curl -s localhost:8000 | grep -o 'make-no-mistakes' | head -1; kill $SERVER
```
Expected: prints `make-no-mistakes`, confirming the rendered page.

- [ ] **Step 5: Run the full test suite**

Run:
```bash
uv run pytest -v
```
Expected: all tests in `tests/` PASS.

- [ ] **Step 6: Commit results (this is what CI publishes)**

```bash
git add results/raw results/summary.json
git commit -m "data: pilot results for make-no-mistakes (sonnet)"
```

- [ ] **Step 7: Push and confirm publish**

```bash
git push -u origin main
```
Expected: the "Publish benchmark site" workflow runs and the Pages URL shows the per-model table. Read the lift/regression numbers: a negative overall lift or nonzero regressions is the evidence that the skill made the model evaluate *worse*.

---

## Self-review

**Spec coverage:**
- Upstream as pinned submodule + gitignore fallback → Task 2 (+ `.gitignore` Task 1). ✓
- Package skill for `--skills-dir` → Task 3. ✓
- Three mixed tasks incl. one "over-caution can backfire" (`parse-constraint`, easy) → Tasks 4–6. ✓
- Neutral prompts (never name skill / never coax carefulness) → prompt bodies in Tasks 4–6 are plain. ✓
- Oracle gate + negative control → Task 4 (gate + negative control), Tasks 5–6 (gate; bug-state check in 5). ✓
- Model-parametrized matrix, start Sonnet, 3 trials via shell loop → Tasks 9 & 11 (`MODELS`, `TRIALS`). ✓
- Two-sided lift + regression count + token/time → `aggregate.py` computes lift + regressions (Task 7); token/time deltas are **not** wired because the host-side token/time source is unverified — this is a conscious deferral noted here, not a silent gap. Accuracy + regressions are fully covered; add cost columns once Task 9 Step 1 reveals whether bench emits per-run timing. 
- Aggregation + static site, no built-in report → Tasks 7–8. ✓
- GitHub Actions Pages deploy, evals stay local → Task 10; results committed in Task 11. ✓
- Honest caveats surfaced on the page → `build_site.py` intro paragraph (Task 8). ✓

**Placeholder scan:** No TBD/TODO; every code/step block is concrete. The one configurable value (`BENCH_REWARD_GLOB`) is explicitly discovered in Task 9 Step 1 before use. ✓

**Type/name consistency:** `summary.json` keys (`models`, `tasks`, `no_skill`, `with_skill`, `pass_rate`, `lift_pp`, `regressions`, `overall`, `no_skill_pass_rate`, `with_skill_pass_rate`) are identical across `aggregate.py` (producer), `test_aggregate.py`, `summary_basic.json` fixture, and `build_site.py` (consumer). Condition directory names `no_skill`/`with_skill` match between `run_pilot.sh` (writer) and `aggregate.py` (reader). ✓

**Deferred-by-design (not gaps):** per-run token/time columns (pending Task 9 discovery); paired-seed regression + bootstrap CIs (spec marks these as post-pilot scaling).
