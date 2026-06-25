#!/usr/bin/env python3
"""Render results/summary.json into a static site/index.html."""
import argparse
import html
import json
from pathlib import Path


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def render(summary: dict, title: str = "skill", selection: dict | None = None) -> str:
    t = html.escape(title)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{t} benchmark</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "th,td{border:1px solid #ccc;padding:.4rem .6rem;text-align:right}"
        "th:first-child,td:first-child{text-align:left}"
        ".neg{color:#b00}.pos{color:#070}.muted{color:#555;font-size:.9rem}</style>"
        "</head><body>",
        f"<h1>{t} &mdash; SkillsBench benchmark</h1>",
        f"<p>Unprompted model vs. the same model with the <code>{t}</code> skill "
        "injected. Negative lift means the skill made the model perform "
        "<em>worse</em>.</p>",
    ]
    if selection and selection.get("selections"):
        parts.append("<h2>Benchmark selection (Codex)</h2>")
        if selection.get("note"):
            parts.append(f"<p class='muted'>{html.escape(selection['note'])}</p>")
        parts.append("<ul>")
        for s in selection["selections"]:
            star = " <strong>(recommended)</strong>" if s.get("recommended") else ""
            parts.append(
                f"<li><code>{html.escape(str(s.get('env')))}</code> "
                f"(fit {s.get('fit_score')}){star}: "
                f"{html.escape(str(s.get('reason','')))}</li>"
            )
        parts.append("</ul>")
    for model, data in summary["models"].items():
        parts.append(f"<h2>{html.escape(model)}</h2>")
        parts.append("<table><thead><tr><th>Benchmark</th><th>Baseline</th>"
                     "<th>With skill</th><th>Lift (pp)</th><th>Regressions</th>"
                     "</tr></thead><tbody>")
        for task, t in data["tasks"].items():
            lift = t["lift_pp"]
            cls = "neg" if lift < 0 else ("pos" if lift > 0 else "")
            parts.append(
                f"<tr><td>{html.escape(task)}</td>"
                f"<td>{pct(t['no_skill']['pass_rate'])}</td>"
                f"<td>{pct(t['with_skill']['pass_rate'])}</td>"
                f"<td class='{cls}'>{lift:+.1f}</td>"
                f"<td>{t['regressions']}</td></tr>"
            )
        o = data["overall"]
        lift = o["lift_pp"]
        cls = "neg" if lift < 0 else ("pos" if lift > 0 else "")
        parts.append(
            f"<tr><td><strong>Overall</strong></td>"
            f"<td>{pct(o['no_skill_pass_rate'])}</td>"
            f"<td>{pct(o['with_skill_pass_rate'])}</td>"
            f"<td class='{cls}'>{lift:+.1f}</td>"
            f"<td>{o['regressions']}</td></tr>"
        )
        parts.append("</tbody></table>")
    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/summary.json")
    ap.add_argument("--out", default="site")
    ap.add_argument("--title", default="make-no-mistakes")
    ap.add_argument("--selection", default=None,
                    help="optional selection.json to render Codex's rationale")
    args = ap.parse_args()
    summary = json.loads(Path(args.summary).read_text())
    selection = json.loads(Path(args.selection).read_text()) if args.selection else None
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render(summary, title=args.title, selection=selection))
    print(f"wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
