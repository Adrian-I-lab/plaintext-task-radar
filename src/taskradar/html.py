"""Render a report as one self-contained HTML file: inline CSS, no scripts, no external links."""

from html import escape
from pathlib import Path

from .radar import Item, Report, where

CSS = """
:root { color-scheme: light dark; --bg: #fbfaf7; --fg: #1d1d1b; --muted: #66655f;
  --line: #e2e0da; --late: #a1271e; --soon: #7a5200; --stale: #3d5a80; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161614; --fg: #ecebe6; --muted: #a3a29b; --line: #34332f;
    --late: #f2b8b5; --soon: #f0c674; --stale: #a9c4e8; } }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 60rem; padding: 1rem; background: var(--bg); color: var(--fg);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
h1 { font-size: 1.35rem; margin: 0 0 .25rem; }
h2 { font-size: 1.05rem; margin: 1.5rem 0 .5rem; }
p.meta { color: var(--muted); margin: 0; }
ul.totals { display: flex; flex-wrap: wrap; gap: .5rem; padding: 0; margin: 1rem 0;
  list-style: none; }
ul.totals li { border: 1px solid var(--line); border-radius: .4rem; padding: .3rem .65rem; }
ul.totals b { font-variant-numeric: tabular-nums; }
.overdue b, .overdue h2 { color: var(--late); }
.due_soon b, .due_soon h2 { color: var(--soon); }
.stale b, .stale h2 { color: var(--stale); }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .35rem .5rem; border-bottom: 1px solid var(--line);
  vertical-align: top; }
th { color: var(--muted); font-size: .8rem; font-weight: 600; }
td.nowrap { white-space: nowrap; font-variant-numeric: tabular-nums; }
span.where { display: block; color: var(--muted); font-size: .8rem; overflow-wrap: anywhere; }
p.none { color: var(--muted); }
"""
LABELS = {"overdue": "Overdue", "due_soon": "Due soon", "stale": "Stale",
          "project_issues": "Project issues"}


def table(heads: list[str], rows: list[tuple[str, str, list[str]]]) -> str:
    """Rows are (main text, note location, extra cells). The location sits under the text."""
    if not rows:
        return '<p class="none">None.</p>'
    head = "".join(f"<th>{escape(h)}</th>" for h in heads)
    body = "".join(f'<tr><td>{escape(text)}<span class="where">{escape(loc)}</span></td>'
                   + "".join(f'<td class="nowrap">{escape(c)}</td>' for c in cells) + "</tr>"
                   for text, loc, cells in rows)
    return f'<div class="scroll"><table><tr>{head}</tr>{body}</table></div>'


def item_rows(items: list[Item], root: Path) -> list[tuple[str, str, list[str]]]:
    return [(i.text, where(i.path, i.line, root),
             [str(i.due or "-"), f"{i.days} day" + ("" if i.days == 1 else "s")]) for i in items]


def render(report: Report, root: Path) -> str:
    totals = report.totals()
    sections = {
        "overdue": table(["Task", "Due", "Late"], item_rows(report.overdue, root)),
        "due_soon": table(["Task", "Due", "In"], item_rows(report.due_soon, root)),
        "stale": table(["Task", "Due", "Age"], item_rows(report.stale, root)),
        "project_issues": table(["Issue", "Check"], [
            (i.detail, where(i.path, 0, root), [i.check]) for i in report.project_issues]),
    }
    chips = "".join(f'<li class="{k}" data-total="{k}"><b>{totals[k]}</b> {escape(LABELS[k])}</li>'
                    for k in LABELS)
    parts = "".join(f'<section class="{k}"><h2>{escape(LABELS[k])} ({totals[k]})</h2>{html}'
                    "</section>" for k, html in sections.items())
    meta = (f"Reference date {report.today}. Due soon means within {report.horizon} days. "
            f"Stale means undated and untouched for more than {report.stale_days} days.")
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>Task radar {report.today}</title><style>{CSS}</style></head><body>"
            f"<h1>Task radar</h1><p class=\"meta\">{escape(meta)}</p>"
            f'<ul class="totals">{chips}</ul>{parts}</body></html>\n')
