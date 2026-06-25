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


def summarize(results_dir: Path) -> dict:
    raw = results_dir / "raw"
    models = {}
    for model_dir in sorted(p for p in raw.glob("*") if p.is_dir()):
        tasks = {}
        ns_p = ns_t = ws_p = ws_t = regr = 0
        for task_dir in sorted(p for p in model_dir.glob("*") if p.is_dir()):
            ns = tally(task_dir / "no_skill")
            ws = tally(task_dir / "with_skill")
            regressions = max(0, ns["passes"] - ws["passes"])
            tasks[task_dir.name] = {
                "no_skill": ns,
                "with_skill": ws,
                "lift_pp": round((ws["pass_rate"] - ns["pass_rate"]) * 100, 1),
                "regressions": regressions,
            }
            ns_p += ns["passes"]; ns_t += ns["trials"]
            ws_p += ws["passes"]; ws_t += ws["trials"]
            regr += regressions
        ns_rate = round(ns_p / ns_t, 4) if ns_t else 0.0
        ws_rate = round(ws_p / ws_t, 4) if ws_t else 0.0
        models[model_dir.name] = {
            "tasks": tasks,
            "overall": {
                "no_skill_pass_rate": ns_rate,
                "with_skill_pass_rate": ws_rate,
                "lift_pp": round((ws_rate - ns_rate) * 100, 1),
                "regressions": regr,
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
