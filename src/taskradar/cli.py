"""Command line: `taskradar radar` and `taskradar lint`."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .lint import format_finding, lint
from .parse import iter_notes
from .radar import Item, Report, build


def where(path: Path, line: int, root: Path) -> str:
    rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    return f"{rel}:{line}" if line else rel


def when(item: Item, late: bool) -> str:
    unit = "day" if item.days == 1 else "days"
    if late:
        return f"{item.days} {unit} late"
    return "due today" if item.days == 0 else f"in {item.days} {unit}"


def render_text(report: Report, root: Path) -> str:
    t = report.totals()
    out = [f"Radar for {report.today} (horizon {report.horizon} days, "
           f"stale after {report.stale_days} days)",
           f"Totals: {t['overdue']} overdue, {t['due_soon']} due soon, {t['stale']} stale, "
           f"{t['project_issues']} project issues"]
    for title, items, late in (("Overdue", report.overdue, True),
                               ("Due soon", report.due_soon, False)):
        out += ["", f"{title} ({len(items)})"]
        out += [f"  {i.due}  {when(i, late):<12}  {where(i.path, i.line, root)}  {i.text}"
                for i in items] or ["  none"]
    out += ["", f"Stale ({len(report.stale)})"]
    out += [f"  {i.days} days since update  {where(i.path, i.line, root)}  {i.text}"
            for i in report.stale] or ["  none"]
    out += ["", f"Project issues ({len(report.project_issues)})"]
    out += [f"  {where(i.path, 0, root)}  {i.check}: {i.detail}"
            for i in report.project_issues] or ["  none"]
    return "\n".join(out) + "\n"


def render_json(report: Report, root: Path) -> str:
    def item(i: Item) -> dict:
        return {"path": where(i.path, 0, root), "line": i.line, "text": i.text,
                "due": i.due.isoformat() if i.due else None, "days": i.days, "kind": i.kind}
    data = {"schema_version": 1, "today": report.today.isoformat(), "horizon": report.horizon,
            "stale_days": report.stale_days, "totals": report.totals(),
            "overdue": [item(i) for i in report.overdue],
            "due_soon": [item(i) for i in report.due_soon],
            "stale": [item(i) for i in report.stale],
            "project_issues": [{"path": where(i.path, 0, root), "check": i.check,
                                "detail": i.detail} for i in report.project_issues]}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskradar", description="Overdue, due-soon, and "
                                     "stale tasks from a folder of Markdown notes.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    radar = sub.add_parser("radar", help="report overdue, due soon, and stale tasks")
    radar.add_argument("root", type=Path, help="folder of notes, or one note")
    radar.add_argument("--today", type=date.fromisoformat, metavar="YYYY-MM-DD",
                       help="reference date (default: the real today)")
    radar.add_argument("--horizon", type=int, default=7, help="due soon window in days")
    radar.add_argument("--stale-days", type=int, default=21, help="age limit for undated tasks")
    radar.add_argument("--json", action="store_true", help="print JSON instead of text")
    radar.add_argument("--fail-on-overdue", action="store_true", help="exit 2 if anything is late")
    lint_cmd = sub.add_parser("lint", help="check notes against the format rules")
    lint_cmd.add_argument("root", type=Path, help="folder of notes, or one note")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if not args.root.exists():
        parser.error(f"{args.root} does not exist")
    projects = list(iter_notes(args.root))
    if args.command == "lint":
        findings = lint(projects)
        errors = sum(f.severity == "error" for f in findings)
        for finding in findings:
            print(format_finding(finding, args.root))
        print(f"{len(findings)} finding(s): {errors} error(s), {len(findings) - errors} warning(s)")
        return 1 if errors else 0
    report = build(projects, args.today or date.today(), args.horizon, args.stale_days)
    print(render_json(report, args.root) if args.json else render_text(report, args.root), end="")
    return 2 if args.fail_on_overdue and report.overdue else 0


if __name__ == "__main__":
    sys.exit(main())
