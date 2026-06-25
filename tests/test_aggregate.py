import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_reward(base, model, task, cond, trial, value):
    d = base / "raw" / model / task / cond / f"trial-{trial}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reward.txt").write_text(f"{value}\n")


def test_aggregate_produces_summary(tmp_path):
    results = tmp_path
    m = "claude-sonnet-4-6"
    # arithmetic-trap: baseline 3/3, skill 2/3  -> lift -33.3, 1 regression
    write_reward(results, m, "arithmetic-trap", "no_skill", 1, 1)
    write_reward(results, m, "arithmetic-trap", "no_skill", 2, 1)
    write_reward(results, m, "arithmetic-trap", "no_skill", 3, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 1, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 2, 1)
    write_reward(results, m, "arithmetic-trap", "with_skill", 3, 0)

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "aggregate.py"),
         "--results-dir", str(results)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr

    summary = json.loads((results / "summary.json").read_text())
    task = summary["models"][m]["tasks"]["arithmetic-trap"]
    assert task["no_skill"] == {"passes": 3, "trials": 3, "pass_rate": 1.0}
    assert task["with_skill"]["passes"] == 2
    assert task["with_skill"]["trials"] == 3
    assert task["lift_pp"] == -33.3
    assert task["regressions"] == 1

    overall = summary["models"][m]["overall"]
    assert overall["no_skill_pass_rate"] == 1.0
    assert overall["regressions"] == 1
