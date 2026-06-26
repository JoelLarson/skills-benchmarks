#!/usr/bin/env python3
"""Render results/summary.json into a static site/index.html."""
import argparse
import html
import json
from pathlib import Path


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def toks(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(int(n))


def dur(s: float) -> str:
    return f"{s/60:.1f} min" if s >= 60 else f"{s:.0f} s"


def signed_pct(base: float, other: float) -> str:
    if not base:
        return "n/a"
    return f"{(other - base) / base * 100:+.0f}%"


def cost_table(model_data: dict) -> list[str]:
    """Render the token + wall-clock cost comparison, plus the skill's overhead.
    Returns [] when no cost data was captured (older summaries / fixtures)."""
    o = model_data.get("overall", {}).get("cost")
    if not o:
        return []
    ns, ws = o["no_skill"], o["with_skill"]
    if ns.get("runs", 0) == 0 and ws.get("runs", 0) == 0:
        return []
    rows = [
        ("Baseline (no skill)", ns),
        ("With skill", ws),
    ]
    def avg(c):
        return c["wall_time_s"] / c["runs"] if c.get("runs") else 0.0

    parts = ["<h3>Cost — tokens &amp; time</h3>",
             "<table><thead><tr><th>Condition</th><th>Runs</th>"
             "<th>Output tokens</th><th>Total tokens</th>"
             "<th>Wall time (total)</th><th>Avg / run</th></tr></thead><tbody>"]
    for label, c in rows:
        parts.append(
            f"<tr><td>{label}</td><td>{c['runs']}</td>"
            f"<td>{toks(c['output_tokens'])}</td>"
            f"<td>{toks(c['total_tokens'])}</td>"
            f"<td>{dur(c['wall_time_s'])}</td>"
            f"<td>{dur(avg(c))}</td></tr>"
        )
    # Overhead row: how much more the skill costs (positive = skill costs more).
    parts.append(
        "<tr><td><strong>Skill overhead</strong></td><td>&mdash;</td>"
        f"<td class='muted'>{signed_pct(ns['output_tokens'], ws['output_tokens'])}</td>"
        f"<td class='muted'>{signed_pct(ns['total_tokens'], ws['total_tokens'])}</td>"
        f"<td class='muted'>{signed_pct(ns['wall_time_s'], ws['wall_time_s'])}</td>"
        f"<td class='muted'>{signed_pct(avg(ns), avg(ws))}</td></tr>"
    )
    parts.append("</tbody></table>")
    parts.append(
        "<p class='muted'>Wall time is the full per-run cell (container build + "
        "agent + verifier); the agent's own execution time is not separately "
        "metered by the harness. Token totals include cache reads. No USD cost is "
        "shown because Codex is subscription-billed (no per-token price). Positive "
        "overhead means the skill spent more.</p>"
    )
    return parts


def task_description(tasks_dir: Path, task: str) -> str | None:
    """The task's prompt (task.md body, frontmatter stripped), if available."""
    md = tasks_dir / task / "task.md"
    if not md.is_file():
        return None
    lines, body, seps = md.read_text().splitlines(), [], 0
    for ln in lines:
        if ln.strip() == "---":
            seps += 1
            continue
        if seps >= 2:
            body.append(ln)
    text = "\n".join(body).strip() if seps >= 2 else md.read_text().strip()
    return text or None


def eval_logs(results_dir: Path, model: str, task: str) -> list[tuple[str, str, str]]:
    """(condition, trial, log-text) for every cell with a captured verifier.log."""
    rows = []
    base = results_dir / "raw" / model / task
    for cond in ("no_skill", "with_skill"):
        for log in sorted((base / cond).glob("trial-*/verifier.log")) if (base / cond).is_dir() else []:
            rows.append((cond, log.parent.name, log.read_text()))
    return rows


def details_section(summary_model: dict, model: str, tasks_dir: Path,
                    results_dir: Path) -> list[str]:
    """Per-benchmark collapsible: what the benchmark does + its evaluation logs."""
    out = []
    for task in summary_model["tasks"]:
        desc = task_description(tasks_dir, task)
        logs = eval_logs(results_dir, model, task)
        if not desc and not logs:
            continue
        out.append(f"<details><summary><strong>{html.escape(task)}</strong> "
                   "&mdash; description &amp; evaluation logs</summary>")
        if desc:
            out.append("<h4>What this benchmark does</h4>")
            out.append(f"<pre class='desc'>{html.escape(desc)}</pre>")
        if logs:
            out.append("<h4>Evaluation logs (verifier output per trial)</h4>")
            for cond, trial, text in logs:
                out.append(f"<details><summary>{cond} / {html.escape(trial)}</summary>"
                           f"<pre class='log'>{html.escape(text)}</pre></details>")
        out.append("</details>")
    return out


def render(summary: dict, title: str = "skill", selection: dict | None = None,
           tasks_dir: Path = Path("tasks"),
           results_dir: Path = Path("results")) -> str:
    t = html.escape(title)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{t} benchmark</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%;margin:1rem 0}"
        "th,td{border:1px solid #ccc;padding:.4rem .6rem;text-align:right}"
        "th:first-child,td:first-child{text-align:left}"
        ".neg{color:#b00}.pos{color:#070}.muted{color:#555;font-size:.9rem}"
        "details{margin:.4rem 0}summary{cursor:pointer}"
        "pre.desc,pre.log{white-space:pre-wrap;background:#f6f6f6;border:1px solid #ddd;"
        "padding:.6rem;border-radius:4px;font-size:.85rem;overflow-x:auto}</style>"
        "</head><body>",
        f"<h1>{t} &mdash; SkillsBench benchmark</h1>",
        f"<p>Unprompted model vs. the same model with the <code>{t}</code> skill "
        "injected. Each model section reports <strong>improvement/degradation</strong> "
        "(pass-rate lift and regressions) and the skill's <strong>token and time "
        "cost</strong>. Negative lift means the skill made the model perform "
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
        parts.extend(cost_table(data))
        details = details_section(data, model, tasks_dir, results_dir)
        if details:
            parts.append("<h3>Benchmark details &amp; evaluation logs</h3>")
            parts.extend(details)
    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default="results/summary.json")
    ap.add_argument("--out", default="site")
    ap.add_argument("--title", default="make-no-mistakes")
    ap.add_argument("--selection", default=None,
                    help="optional selection.json to render Codex's rationale")
    ap.add_argument("--tasks-dir", default="tasks",
                    help="local task dirs, for benchmark descriptions (task.md)")
    ap.add_argument("--results-dir", default="results",
                    help="results dir, for per-trial evaluation logs (verifier.log)")
    args = ap.parse_args()
    summary = json.loads(Path(args.summary).read_text())
    selection = json.loads(Path(args.selection).read_text()) if args.selection else None
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render(
        summary, title=args.title, selection=selection,
        tasks_dir=Path(args.tasks_dir), results_dir=Path(args.results_dir)))
    print(f"wrote {out_dir / 'index.html'}")


if __name__ == "__main__":
    main()
