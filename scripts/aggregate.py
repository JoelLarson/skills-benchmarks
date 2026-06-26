#!/usr/bin/env python3
"""Aggregate results/raw/<model>/<task>/<condition>/trial-N/reward.txt into summary.json."""
import argparse
import json
from pathlib import Path

CONDITIONS = ("no_skill", "with_skill")


def read_reward(trial_dir: Path) -> int:
    text = (trial_dir / "reward.txt").read_text().strip()
    return 1 if text == "1" else 0


def tally(cond_dir: Path) -> dict:
    # Count every reward.txt under the condition dir, at any depth. This supports
    # both the simple layout (cond/trial-N/reward.txt — one reward per trial) and
    # the benchmark layout (cond/trial-N/<subtask>/reward.txt — many per trial).
    passes = trials = 0
    if cond_dir.is_dir():
        for reward_file in sorted(cond_dir.rglob("reward.txt")):
            trials += 1
            passes += read_reward(reward_file.parent)
    pass_rate = round(passes / trials, 4) if trials else 0.0
    return {"passes": passes, "trials": trials, "pass_rate": pass_rate}


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def cost(cond_dir: Path) -> dict:
    """Sum token usage (usage.json) and wall-clock time (timing.json) across all
    runs under a condition dir. Both files are optional, so a run that captured
    no cost data yields zeros — keeping older summaries and tests valid."""
    agg = {"runs": 0, "input_tokens": 0, "output_tokens": 0,
           "cache_read_tokens": 0, "total_tokens": 0,
           "agent_time_s": 0.0, "wall_time_s": 0.0}
    if not cond_dir.is_dir():
        return agg
    for u in sorted(cond_dir.rglob("usage.json")):
        d = _load(u)
        agg["runs"] += 1
        for k in ("input_tokens", "output_tokens", "cache_read_tokens", "total_tokens"):
            agg[k] += int(d.get(k) or 0)
    for tm in sorted(cond_dir.rglob("timing.json")):
        d = _load(tm)
        agg["agent_time_s"] += float(d.get("agent_execution") or 0.0)
        agg["wall_time_s"] += float(d.get("total") or 0.0)
    agg["agent_time_s"] = round(agg["agent_time_s"], 1)
    agg["wall_time_s"] = round(agg["wall_time_s"], 1)
    return agg


def _sum_cost(a: dict, b: dict) -> dict:
    return {k: round(a[k] + b[k], 1) if isinstance(a[k], float) else a[k] + b[k]
            for k in a}


def summarize(results_dir: Path) -> dict:
    raw = results_dir / "raw"
    models = {}
    for model_dir in sorted(p for p in raw.glob("*") if p.is_dir()):
        tasks = {}
        ns_p = ns_t = ws_p = ws_t = regr = 0
        ns_cost_tot = cost(Path("/nonexistent"))  # zero-initialized accumulator
        ws_cost_tot = cost(Path("/nonexistent"))
        for task_dir in sorted(p for p in model_dir.glob("*") if p.is_dir()):
            ns = tally(task_dir / "no_skill")
            ws = tally(task_dir / "with_skill")
            ns_cost = cost(task_dir / "no_skill")
            ws_cost = cost(task_dir / "with_skill")
            regressions = max(0, ns["passes"] - ws["passes"])
            tasks[task_dir.name] = {
                "no_skill": ns,
                "with_skill": ws,
                "lift_pp": round((ws["pass_rate"] - ns["pass_rate"]) * 100, 1),
                "regressions": regressions,
                "cost": {"no_skill": ns_cost, "with_skill": ws_cost},
            }
            ns_p += ns["passes"]; ns_t += ns["trials"]
            ws_p += ws["passes"]; ws_t += ws["trials"]
            regr += regressions
            ns_cost_tot = _sum_cost(ns_cost_tot, ns_cost)
            ws_cost_tot = _sum_cost(ws_cost_tot, ws_cost)
        ns_rate = round(ns_p / ns_t, 4) if ns_t else 0.0
        ws_rate = round(ws_p / ws_t, 4) if ws_t else 0.0
        models[model_dir.name] = {
            "tasks": tasks,
            "overall": {
                "no_skill_pass_rate": ns_rate,
                "with_skill_pass_rate": ws_rate,
                "lift_pp": round((ws_rate - ns_rate) * 100, 1),
                "regressions": regr,
                "cost": {"no_skill": ns_cost_tot, "with_skill": ws_cost_tot},
            },
        }
    return {"models": models}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", default="results")
    args = ap.parse_args()
    results_dir = Path(args.results_dir)
    summary = summarize(results_dir)
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {results_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
