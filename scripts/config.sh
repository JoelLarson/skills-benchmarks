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
