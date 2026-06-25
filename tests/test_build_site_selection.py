import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "summary_basic.json"


def test_build_site_renders_selection_and_title(tmp_path):
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({
        "software_related": True,
        "note": "precision skill best probed by deterministic repair tasks",
        "selections": [
            {"env": "humanevalfix", "reason": "deterministic python repair",
             "fit_score": 0.9, "recommended": True},
        ],
    }))
    out_dir = tmp_path / "site"
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_site.py"),
         "--summary", str(FIXTURE), "--out", str(out_dir),
         "--title", "my-skill", "--selection", str(sel)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    html = (out_dir / "index.html").read_text()
    assert "my-skill" in html
    assert "Benchmark selection (Codex)" in html
    assert "humanevalfix" in html
    assert "deterministic python repair" in html
    assert "<th>Benchmark</th>" in html
