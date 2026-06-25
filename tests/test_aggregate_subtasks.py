import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_reward(base, model, bench, cond, trial, subtask, value):
    d = base / "raw" / model / bench / cond / f"trial-{trial}" / subtask
    d.mkdir(parents=True, exist_ok=True)
    (d / "reward.txt").write_text(f"{value}\n")


def test_aggregate_counts_subtask_rewards(tmp_path):
    m, b = "gpt-5.5", "humanevalfix"
    # one trial, two sub-tasks: one pass, one fail -> passes=1, trials=2, rate=0.5
    write_reward(tmp_path, m, b, "no_skill", 1, "python-0", 1)
    write_reward(tmp_path, m, b, "no_skill", 1, "python-1", 0)
    write_reward(tmp_path, m, b, "with_skill", 1, "python-0", 1)
    write_reward(tmp_path, m, b, "with_skill", 1, "python-1", 1)

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "aggregate.py"),
         "--results-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    summary = json.loads((tmp_path / "summary.json").read_text())
    bench = summary["models"][m]["tasks"][b]
    assert bench["no_skill"] == {"passes": 1, "trials": 2, "pass_rate": 0.5}
    assert bench["with_skill"] == {"passes": 2, "trials": 2, "pass_rate": 1.0}
    assert bench["lift_pp"] == 50.0
