#!/usr/bin/env python3
"""Read a harbor catalog JSON (stdin) and print the run spec for one benchmark.

Output (shell-eval-able):
  REPO=<org/repo>
  REF=<commit>
  SRCPATH=<subpath containing task packages>
  TASKS=<space-separated first-N task names>
"""
import json
import os
import sys

bench = sys.argv[1]
n = int(sys.argv[2])
data = json.load(sys.stdin)
envs = data if isinstance(data, list) else data.get("environments", data.get("results", []))
match = [e for e in envs if e.get("name") == bench]
if not match:
    sys.exit(f"bench_spec: env not found: {bench}")
tasks = match[0].get("tasks") or []
if not tasks:
    sys.exit(f"bench_spec: no tasks listed for {bench}")
t0 = tasks[0]
repo = t0.get("git_url", "").replace("https://github.com/", "").removesuffix(".git")
ref = t0.get("git_commit_id", "")
srcpath = os.path.dirname(t0.get("path", ""))
names = [t.get("name") for t in tasks[:n] if t.get("name")]
print(f"REPO={repo}")
print(f"REF={ref}")
print(f"SRCPATH={srcpath}")
print(f"TASKS={' '.join(names)}")
