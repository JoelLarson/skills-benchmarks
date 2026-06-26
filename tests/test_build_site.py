import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "summary_basic.json"


def test_build_site_renders_expected_content(tmp_path):
    out_dir = tmp_path / "site"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"),
         "--summary", str(FIXTURE), "--out", str(out_dir)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr

    html = (out_dir / "index.html").read_text()
    assert "default" in html
    assert "arithmetic-trap" in html
    assert "-33.3" in html
    assert "Regressions" in html
    assert "make-no-mistakes" in html


def _summary_with_cost():
    return {"models": {"gpt-5.5": {
        "tasks": {"arithmetic-trap": {
            "no_skill": {"passes": 0, "trials": 1, "pass_rate": 0.0},
            "with_skill": {"passes": 1, "trials": 1, "pass_rate": 1.0},
            "lift_pp": 100.0, "regressions": 0,
            "cost": {
                "no_skill": {"runs": 1, "input_tokens": 500, "output_tokens": 20,
                             "cache_read_tokens": 0, "total_tokens": 520,
                             "agent_time_s": 30.0, "wall_time_s": 60.0},
                "with_skill": {"runs": 1, "input_tokens": 800, "output_tokens": 40,
                               "cache_read_tokens": 0, "total_tokens": 840,
                               "agent_time_s": 30.0, "wall_time_s": 66.0}}}},
        "overall": {"no_skill_pass_rate": 0.0, "with_skill_pass_rate": 1.0,
                    "lift_pp": 100.0, "regressions": 0,
                    "cost": {
                        "no_skill": {"runs": 1, "input_tokens": 500, "output_tokens": 20,
                                     "cache_read_tokens": 0, "total_tokens": 520,
                                     "agent_time_s": 30.0, "wall_time_s": 60.0},
                        "with_skill": {"runs": 1, "input_tokens": 800, "output_tokens": 40,
                                       "cache_read_tokens": 0, "total_tokens": 840,
                                       "agent_time_s": 30.0, "wall_time_s": 66.0}}}}}}


def test_build_site_renders_cost_description_and_logs(tmp_path):
    import json
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps(_summary_with_cost()))

    # a local task description and a captured evaluation log
    (tmp_path / "tasks" / "arithmetic-trap").mkdir(parents=True)
    (tmp_path / "tasks" / "arithmetic-trap" / "task.md").write_text(
        "---\nmeta: x\n---\nApply a 15% discount then 20% then tax.\n")
    cell = tmp_path / "results" / "raw" / "gpt-5.5" / "arithmetic-trap" / "no_skill" / "trial-1"
    cell.mkdir(parents=True)
    (cell / "verifier.log").write_text("AssertionError: expected 353.33, got 359.04")

    out_dir = tmp_path / "site"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"),
         "--summary", str(summary), "--out", str(out_dir),
         "--tasks-dir", str(tmp_path / "tasks"),
         "--results-dir", str(tmp_path / "results")],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    html = (out_dir / "index.html").read_text()
    assert "Cost &mdash; tokens" in html or "Cost" in html
    assert "Output tokens" in html
    assert "+100%" in html                       # output-token overhead (20 -> 40)
    assert "Apply a 15% discount" in html        # benchmark description
    assert "expected 353.33, got 359.04" in html  # evaluation log
    assert "Wall time" in html
