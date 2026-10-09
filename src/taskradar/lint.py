"""Check notes against lint rules L001 to L006 from docs/FORMAT.md."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .model import MARKERS, Project

FIXES = {"/": "~", "X": "x"}
WARNINGS = frozenset({"L005"})


@dataclass(frozen=True, order=True)
class Finding:
    path: Path
    line: int
    rule: str
    message: str
    fix: str = ""

    @property
    def severity(self) -> str:
        return "warning" if self.rule in WARNINGS else "error"


def lint_project(project: Project) -> list[Finding]:
    path, found = project.path, []
    for error in project.meta_errors:
        line = project.meta_lines.get(error.split(":")[0], 1)
        found.append(Finding(path, line, "L006", f"frontmatter: {error}"))
    for task in project.tasks:
        if task.marker not in MARKERS:
            fix = f"use [{FIXES[task.marker]}]" if task.marker in FIXES else ""
            message = f"[{task.marker}] is not one of the six markers"
            found.append(Finding(path, task.line, "L001", message, fix))
        for raw in task.bad_dates:
            message = f"'{raw}' is not a YYYY-MM-DD date"
            found.append(Finding(path, task.line, "L002", message, "write the date as YYYY-MM-DD"))
        if task.marker == "d" and task.delegate is None:
            found.append(Finding(path, task.line, "L004", "delegated task names nobody",
                                 "add @name"))
        if not task.in_tasks_section:
            found.append(Finding(path, task.line, "L005", "task line outside '## Tasks'",
                                 "move it under '## Tasks'"))
    for line in project.near_misses:
        found.append(Finding(path, line, "L003", "no space after the bullet, so this is not a task",
                             "put a space between the bullet and '['"))
    return sorted(found)


def lint(projects: Iterable[Project]) -> list[Finding]:
    """All findings, ordered by path, then line, then rule."""
    return sorted(f for project in projects for f in lint_project(project))


def counts(findings: Iterable[Finding]) -> Counter[str]:
    return Counter(f.rule for f in findings)


def format_finding(finding: Finding, root: Path) -> str:
    where = finding.path.relative_to(root) if finding.path.is_relative_to(root) else finding.path
    fix = f" (fix: {finding.fix})" if finding.fix else ""
    return f"{where.as_posix()}:{finding.line}: {finding.rule} {finding.severity}: " \
           f"{finding.message}{fix}"
