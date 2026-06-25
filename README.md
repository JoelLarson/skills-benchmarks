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

## Run the pilot
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
