#!/usr/bin/env python3
"""Print a cost/time estimate for a skill-evaluation run, before stage 3 executes.

Codex auth is subscription/quota-based (not per-$), so we estimate in agent-runs and
wall-clock minutes. Actual token totals are reported after the run from timing.json.
"""
import argparse

# Rough per-run wall-clock minutes by benchmark family (one agent rollout on one task).
HEAVY = ("swe", "lancer", "contest", "terminal", "cooper", "compile", "vmax",
         "multilingual", "researchcode", "ml-dev", "otel", "ade-bench")
LIGHT = ("humaneval", "livecode", "evoeval", "bigcode", "ds-1000", "quix",
         "aider", "usaco", "autocode", "codepde", "dabstep")


def per_run_minutes(name: str) -> float:
    n = name.lower()
    if any(h in n for h in HEAVY):
        return 8.0
    if any(l in n for l in LIGHT):
        return 2.0
    return 3.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("benchmarks", nargs="+")
    ap.add_argument("--tasks-per-bench", type=int, default=10)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--concurrency", type=int, default=1,
                    help="parallel agent runs (divides wall-clock)")
    args = ap.parse_args()

    rows, total_runs, total_min = [], 0, 0.0
    for b in args.benchmarks:
        runs = args.tasks_per_bench * args.trials * 2  # no_skill + with_skill
        mins = runs * per_run_minutes(b)
        rows.append((b, runs, per_run_minutes(b), mins))
        total_runs += runs
        total_min += mins

    wall = total_min / max(1, args.concurrency)
    w = max(len(b) for b, *_ in rows) if rows else 10

    print(f"\nEstimate — {args.tasks_per_bench} tasks x {args.trials} trials x 2 conditions"
          f" per benchmark (concurrency={args.concurrency})\n")
    print(f"  {'benchmark'.ljust(w)}  {'runs':>5}  {'min/run':>7}  {'est min':>8}")
    print(f"  {'-'*w}  {'-'*5}  {'-'*7}  {'-'*8}")
    for b, runs, mpr, mins in rows:
        print(f"  {b.ljust(w)}  {runs:>5}  {mpr:>7.1f}  {mins:>8.0f}")
    print(f"  {'-'*w}  {'-'*5}  {'-'*7}  {'-'*8}")
    print(f"  {'TOTAL'.ljust(w)}  {total_runs:>5}  {'':>7}  {total_min:>8.0f}")
    print(f"\n  agent runs: {total_runs}   serial: ~{total_min/60:.1f}h"
          f"   at concurrency {args.concurrency}: ~{wall/60:.1f}h")
    print("  cost: Codex subscription/quota (no per-$); token totals reported after the run.\n")


if __name__ == "__main__":
    main()
