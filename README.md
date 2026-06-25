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

## Publishing
GitHub Pages is served via Actions. In repo Settings → Pages, set Source to
"GitHub Actions". The site rebuilds from `results/summary.json` on every push to
`main`.
