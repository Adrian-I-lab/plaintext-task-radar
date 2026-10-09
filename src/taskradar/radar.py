"""Build the radar from parsed notes, following "Radar definitions" in docs/FORMAT.md."""

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .model import Project, to_date

CLOSED = ("done", "dropped")


@dataclass
class Item:
    path: Path
    line: int
    text: str
    due: date | None
    days: int
    kind: str = "task"


@dataclass
class Issue:
    path: Path
    check: str
    detail: str


@dataclass
class Report:
    today: date
    horizon: int
    stale_days: int
    overdue: list[Item] = field(default_factory=list)
    due_soon: list[Item] = field(default_factory=list)
    stale: list[Item] = field(default_factory=list)
    project_issues: list[Issue] = field(default_factory=list)

    def totals(self) -> dict[str, int]:
        return {"overdue": len(self.overdue), "due_soon": len(self.due_soon),
                "stale": len(self.stale), "project_issues": len(self.project_issues)}


def git_date(path: Path) -> date | None:
    """Date of the file's last commit, or None outside a repository."""
    try:
        done = subprocess.run(["git", "log", "-1", "--format=%cs", "--", path.name],
                              cwd=path.parent, capture_output=True, text=True, timeout=5)
        return to_date(done.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def last_touched(project: Project) -> date | None:
    """Frontmatter "updated", else the last git commit date, else the modification time."""
    found = to_date(project.meta.get("updated")) or git_date(project.path)
    if found is None and project.path.exists():
        found = date.fromtimestamp(project.path.stat().st_mtime)
    return found


def build(projects: Iterable[Project], today: date, horizon: int = 7,
          stale_days: int = 21) -> Report:
    report = Report(today, horizon, stale_days)
    for project in projects:
        path, live, active = project.path, project.live_tasks, project.status == "active"
        dated = [(t.line, t.text, t.due, "task") for t in live if t.due]
        deadline = project.deadline
        if active and deadline and all(t.due != deadline for t in live):
            title = project.meta.get("title") or path.stem
            dated.append((0, f"Project deadline: {title}", deadline, "deadline"))
        for line, text, due, kind in dated:
            delta = (due - today).days
            if delta < 0:
                report.overdue.append(Item(path, line, text, due, -delta, kind))
            elif delta <= horizon:
                report.due_soon.append(Item(path, line, text, due, delta, kind))
        undated = [t for t in live if t.due is None]
        touched = last_touched(project) if active and undated else None
        if touched and (today - touched).days > stale_days:
            age = (today - touched).days
            report.stale.extend(Item(path, t.line, t.text, None, age) for t in undated)
        if active and not live:
            report.project_issues.append(Issue(path, "no-live-tasks", "active project with no "
                                               "open or in-progress task"))
        if active and deadline and deadline < today:
            report.project_issues.append(Issue(path, "deadline-passed",
                                               f"deadline {deadline} has passed"))
        if project.status in CLOSED and live:
            report.project_issues.append(Issue(
                path, "live-tasks-in-closed-project",
                f"status {project.status} but {len(live)} live task(s)"))
    report.overdue.sort(key=lambda i: (i.due, str(i.path), i.line))
    report.due_soon.sort(key=lambda i: (i.due, str(i.path), i.line))
    report.stale.sort(key=lambda i: (-i.days, str(i.path), i.line))
    report.project_issues.sort(key=lambda i: (str(i.path), i.check))
    return report
