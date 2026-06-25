#!/bin/bash
# Agent under test (the "prompt runner"). codex-acp = OpenAI Codex via ACP,
# authenticated with OPENAI_API_KEY or a Codex subscription login (~/.codex/auth.json).
# This keeps task-solving off the Anthropic API. See `bench agent list`.
AGENT="codex-acp"

# Models to evaluate. "default" omits --model so Codex uses its configured model.
# Replace with explicit OpenAI/Codex model ids to compare (e.g. "gpt-5-codex"),
# one entry per model. Each becomes a directory under results/raw/.
MODELS=("default")

# Tasks to run (directory names under tasks/).
TASKS=("arithmetic-trap" "subtle-bug" "parse-constraint")

# Trials per (model, task, condition).
TRIALS=3

# Glob that matches the newest reward.txt bench writes on the host.
# Discovered in Task 9 Step 1 — adjust the prefix if your bench writes elsewhere.
BENCH_REWARD_GLOB="runs/**/reward.txt"
