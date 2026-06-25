# Remaining work (run in an environment with Docker + API key)

The offline build is done: scaffolding, the `make-no-mistakes` skill, three task
packages (`arithmetic-trap`, `subtle-bug`, `parse-constraint`), the
`aggregate.py` + `build_site.py` harness (both tested), the GitHub Pages workflow,
and the `run_pilot.sh`/`config.sh` scripts. The steps below are the parts that
need **Docker running**, **`ANTHROPIC_API_KEY` exported**, and the **`bench` CLI**
— deferred because the authoring session had none of them.

Full detail per step lives in
`docs/plans/2026-06-24-skillsbench-make-no-mistakes.md` (Tasks 2, 4–6 gates, 9, 11).

## Prereqs
```bash
docker info >/dev/null && echo "docker ok"
test -n "$ANTHROPIC_API_KEY" && echo "key set"
```

## 1. Vendor SkillsBench + install the CLI (Task 2)
```bash
git submodule add https://github.com/benchflow-ai/skillsbench.git skillsbench
cd skillsbench && git fetch --tags
git checkout skillsbench-v1.1 2>/dev/null || git tag --list 'skillsbench-*'   # pick latest stable if v1.1 absent
cd ..
uv tool install "benchflow>=0.6.2,<0.7"
bench --help
git add .gitmodules skillsbench && git commit -m "build: vendor SkillsBench as pinned submodule"
```
**Watch-out:** confirm the actual tag name (`skillsbench-v1.1` is assumed, unverified).

## 2. Validate tasks + oracle gate + negative control (Tasks 4–6)
Each task must validate and its oracle must resolve (reward 1):
```bash
for t in arithmetic-trap subtle-bug parse-constraint; do
  bench tasks check tasks/$t
  bench eval run --tasks-dir tasks/$t --agent oracle --sandbox docker   # expect: resolved / reward 1
done
```
Negative control (verifier must reject a wrong answer):
```bash
sed -i 's/353.33/337.74/' tasks/arithmetic-trap/oracle/solve.sh
bench eval run --tasks-dir tasks/arithmetic-trap --agent oracle --sandbox docker   # expect: reward 0
git checkout tasks/arithmetic-trap/oracle/solve.sh
```
If `bench tasks check` flags a frontmatter field, mirror the shape from
`skillsbench/tasks/offer-letter-generator/task.md` and re-run.

## 3. Discover the reward path, then wire config (Task 9 Step 1)
The one value that couldn't be verified from docs: where `bench` writes
`reward.txt` on the host.
```bash
bench eval run --tasks-dir tasks/arithmetic-trap --agent claude-agent-acp \
  --model claude-sonnet-4-6 --sandbox docker --skill-mode no-skill
find . -name reward.txt -newermt '-10 minutes'
```
Set `BENCH_REWARD_GLOB` in `scripts/config.sh` to match that directory pattern
(default assumes `runs/**/reward.txt`).

## 4. Run the pilot, aggregate, publish (Task 11)
```bash
bash scripts/run_pilot.sh                  # 3 tasks x 2 conditions x 3 trials = 18 runs
uv run python scripts/aggregate.py         # -> results/summary.json
uv run python scripts/build_site.py        # -> site/index.html (local preview)
uv run pytest -q                           # all green
git add results/raw results/summary.json
git commit -m "data: pilot results for make-no-mistakes (sonnet)"
git push -u origin main
```
Then in the GitHub repo: **Settings → Pages → Source: GitHub Actions**. The
"Publish benchmark site" workflow renders the per-model table.

## Reading the result
This is **regression detection**: a *negative* overall lift or a nonzero
regression count is the evidence that `make-no-mistakes` made the model evaluate
*worse*. `parse-constraint` (deliberately easy) is the task most likely to expose
over-caution backfiring. To add models, append ids to `MODELS` in
`scripts/config.sh` and re-run.
