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
    m = "default"
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


def test_aggregate_collects_token_and_time_cost(tmp_path):
    m = "gpt-5.5"
    write_reward(tmp_path, m, "arithmetic-trap", "with_skill", 1, 1)
    cell = tmp_path / "raw" / m / "arithmetic-trap" / "with_skill" / "trial-1"
    (cell / "usage.json").write_text(json.dumps(
        {"input_tokens": 500, "output_tokens": 20,
         "cache_read_tokens": 25000, "total_tokens": 25520}))
    (cell / "timing.json").write_text(json.dumps(
        {"agent_execution": 30.0, "total": 62.2}))

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "aggregate.py"),
         "--results-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    summary = json.loads((tmp_path / "summary.json").read_text())
    ws = summary["models"][m]["tasks"]["arithmetic-trap"]["cost"]["with_skill"]
    assert ws["runs"] == 1
    assert ws["output_tokens"] == 20
    assert ws["total_tokens"] == 25520
    assert ws["wall_time_s"] == 62.2
    # condition tallies stay exactly three keys (no cost leakage)
    assert set(summary["models"][m]["tasks"]["arithmetic-trap"]["with_skill"]) == {
        "passes", "trials", "pass_rate"}
    assert summary["models"][m]["overall"]["cost"]["with_skill"]["output_tokens"] == 20
