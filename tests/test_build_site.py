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
    assert "claude-sonnet-4-6" in html
    assert "arithmetic-trap" in html
    assert "-33.3" in html
    assert "Regressions" in html
    assert "make-no-mistakes" in html
