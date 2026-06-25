# Remaining work (Podman flow)

The harness is built and **validated on Podman end-to-end** with the keyless
`oracle` agent: all three tasks pass their oracle gate, the negative control
fails as it should, and `run_pilot.sh → aggregate.py → build_site.py` produces a
site. The only unproven piece is the real **`codex-acp`** agent, which needs your
OpenAI/Codex auth.

Full design detail: `docs/plans/2026-06-24-skillsbench-make-no-mistakes.md`.

## Prereqs (one time)
- **Podman** running and the **Docker-API socket** active:
  `systemctl --user enable --now podman.socket`
- **Compose v2** binary (bench uses `docker compose ... up --wait`; `podman-compose`
  is unreliable for this). Install without sudo:
  ```bash
  mkdir -p ~/.local/bin
  curl -fsSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o ~/.local/bin/docker-compose && chmod +x ~/.local/bin/docker-compose
  ```
- **bench**: `uv tool install "benchflow>=0.6.2,<0.7"` (you have 0.6.3).
- **Codex auth** for the real runs: `codex login` (→ `~/.codex/auth.json`) or
  `export OPENAI_API_KEY=...`. Verify: `bench agent show codex-acp`.

Run the preflight to check all of the above:
```bash
bash scripts/podman-setup.sh
```

How Podman is wired: bench has no `--sandbox podman`, so `scripts/podman/docker`
is a `docker`→`podman` shim (routing `docker compose` to Compose v2 against the
Podman socket). `run_pilot.sh` and `scripts/bench-podman.sh` put it on `PATH`
automatically when `USE_PODMAN=1` (the default in `scripts/config.sh`). For ad-hoc
bench commands use the wrapper:
```bash
scripts/bench-podman.sh eval run --tasks-dir tasks/arithmetic-trap --agent oracle --sandbox docker
```

## 1. Vendor SkillsBench — DONE
Submodule already added.

## 2. Tasks validated on Podman — DONE
Oracle gates pass (reward 1) for all three tasks; arithmetic-trap negative control
fails (reward 0). To re-check:
```bash
for t in arithmetic-trap subtle-bug parse-constraint; do
  scripts/bench-podman.sh eval run --tasks-dir tasks/$t --agent oracle --sandbox docker --jobs-dir jobs-check/$t
done
rm -rf jobs-check
```

## 3. Reward path — RESOLVED
bench writes `jobs/<timestamp>/<task>__<hash>/verifier/reward.txt`. `run_pilot.sh`
gives each trial its own `--jobs-dir` (independent runs; bench otherwise *resumes*
/ skips an already-completed task) and copies the reward to
`results/raw/<model>/<task>/<condition>/trial-<n>/reward.txt`.

## 4. Run the pilot (needs Codex auth)
```bash
bash scripts/podman-setup.sh          # confirm green
bash scripts/run_pilot.sh             # codex-acp, 3 tasks × 2 conditions × 3 trials = 18 runs
uv run python scripts/aggregate.py    # → results/summary.json
uv run python scripts/build_site.py   # → site/index.html (preview locally)
uv run pytest -q                      # harness tests stay green
git add results/raw results/summary.json && git commit -m "data: pilot results"
git push -u origin main               # then Settings → Pages → Source: GitHub Actions
```
Smoke-test the pipeline first without Codex auth:
`AGENT=oracle TRIALS=1 bash scripts/run_pilot.sh` (everything passes; lift 0).

## Reading the result
Regression detection: a **negative overall lift** or **nonzero regression count**
is the evidence that `make-no-mistakes` made Codex *worse*. `parse-constraint`
(deliberately easy) is the task most likely to expose over-caution backfiring. Add
models by listing ids in `MODELS` in `scripts/config.sh` and re-running.

Bonus: each trial also captures `timing.json` (tokens/time) into its `results/raw`
dir — available to wire into the report later.
