#!/bin/bash
# Agent under test (the "prompt runner"). codex-acp = OpenAI Codex via ACP,
# authenticated with OPENAI_API_KEY or a Codex subscription login (~/.codex/auth.json).
# This keeps task-solving off the Anthropic API. See `bench agent list`.
# Override at run time, e.g. `AGENT=oracle bash scripts/run_pilot.sh` for a keyless
# smoke test of the pipeline.
AGENT="${AGENT:-codex-acp}"

# codex-acp authenticates with your `codex login` OAuth (ChatGPT/Codex subscription),
# NOT an API key. bench writes the container's ~/.codex/auth.json from CODEX_AUTH_JSON,
# and only takes the subscription path when OPENAI_API_KEY is UNSET. So for codex-acp:
# load the OAuth json from the host and drop any OPENAI_API_KEY from the environment.
if [[ "$AGENT" == "codex-acp" ]]; then
  if [[ -z "${CODEX_AUTH_JSON:-}" && -f "$HOME/.codex/auth.json" ]]; then
    export CODEX_AUTH_JSON="$(cat "$HOME/.codex/auth.json")"
  fi
  unset OPENAI_API_KEY 2>/dev/null || true
fi

# Models to evaluate (the --model passed to codex-acp). codex-acp has no default,
# so a real id is required. List several ids to compare; each becomes a directory
# under results/raw/. ("default" is a special label that omits --model — only valid
# for agents like `oracle` that don't need one.)
if [[ -z "${MODELS+x}" ]]; then MODELS=("gpt-5.5"); fi

# Reasoning/thinking effort, passed as --reasoning-effort to agents that expose it.
# IMPORTANT: codex-acp does NOT accept this flag (it errors). Leave empty for codex
# — bench already maps a bare codex model to its 'medium'-effort session id by
# default. Only set this for agents that declare an ACP effort option.
: "${REASONING_EFFORT:=}"

# Tasks to run (directory names under tasks/).
if [[ -z "${TASKS+x}" ]]; then TASKS=("arithmetic-trap" "subtle-bug" "parse-constraint"); fi

# Trials per (model, task, condition).
: "${TRIALS:=3}"

# Container backend. bench has no --sandbox podman, so with USE_PODMAN=1 we put a
# docker->podman shim (scripts/podman/) on PATH and point Compose v2 at the Podman
# API socket; bench's --sandbox docker then transparently uses Podman.
# Set USE_PODMAN=0 to use real Docker. Run scripts/podman-setup.sh once first.
: "${USE_PODMAN:=1}"
: "${PODMAN_SOCKET:=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
