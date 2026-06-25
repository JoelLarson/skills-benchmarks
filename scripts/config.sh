#!/bin/bash
# Agent under test (the "prompt runner"). codex-acp = OpenAI Codex via ACP,
# authenticated with OPENAI_API_KEY or a Codex subscription login (~/.codex/auth.json).
# This keeps task-solving off the Anthropic API. See `bench agent list`.
# Override at run time, e.g. `AGENT=oracle bash scripts/run_pilot.sh` for a keyless
# smoke test of the pipeline.
AGENT="${AGENT:-codex-acp}"

# Models to evaluate. "default" omits --model so Codex uses its configured model.
# Replace with explicit OpenAI/Codex model ids to compare (e.g. "gpt-5-codex"),
# one entry per model. Each becomes a directory under results/raw/.
if [[ -z "${MODELS+x}" ]]; then MODELS=("default"); fi

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
