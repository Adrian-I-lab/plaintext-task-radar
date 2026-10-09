"""Read Markdown project notes into Project and Task objects. Never raises on bad content."""

import re
from collections.abc import Iterator
from pathlib import Path

import yaml

from .model import PRIORITIES, STATUSES, Project, Task, to_date

TASK_RE = re.compile(r"^(?P<indent>[ \t]*)[-*][ \t]+\[(?P<marker>.)\](?:[ \t]+(?P<text>.*))?$")
NEAR_MISS_RE = re.compile(r"^[ \t]*[-*]\[[ ~xX\-/>d]\]")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t#]*$")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
DATE_RE = re.compile(r"(📅|✅|due:)[ \t]*(\S*)")
DELEGATE_RE = re.compile(r"(?:^|\s)@([A-Za-z][\w.-]*)")
REQUIRED = ("title", "status", "priority")
PRIORITY_SIGNS = {"⏫": "high", "🔼": "medium", "🔽": "low"}


def check_meta(meta: dict) -> list[str]:
    errors = [f"missing required key '{k}'" for k in REQUIRED if k not in meta]
    if "status" in meta and meta["status"] not in STATUSES:
        errors.append(f"status: '{meta['status']}' is not one of {', '.join(STATUSES)}")
    if "priority" in meta and meta["priority"] not in PRIORITIES:
        errors.append(f"priority: '{meta['priority']}' is not one of {', '.join(PRIORITIES)}")
    for key in ("deadline", "updated"):
        if meta.get(key) is not None and to_date(meta[key]) is None:
            errors.append(f"{key}: '{meta[key]}' is not a YYYY-MM-DD date")
    return errors


def read_frontmatter(lines: list[str]) -> tuple[dict, list[str], int]:
    """Return (meta, errors, index of the first body line)."""
    if not lines or lines[0].strip() != "---":
        return {}, ["no frontmatter block"], 0
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            try:
                meta = yaml.safe_load("\n".join(lines[1:end])) or {}
            except yaml.YAMLError:
                return {}, ["frontmatter is not valid YAML"], end + 1
            if not isinstance(meta, dict):
                return {}, ["frontmatter is not a mapping"], end + 1
            return meta, check_meta(meta), end + 1
    return {}, ["frontmatter block is never closed"], 0


def parse_task(path: Path, number: int, match: re.Match[str], in_tasks: bool) -> Task:
    raw = match.group("text") or ""
    task = Task(path, number, len(match.group("indent").expandtabs(4)), match.group("marker"), raw,
                in_tasks_section=in_tasks)
    for sign, value in DATE_RE.findall(raw):
        parsed = to_date(value)
        if parsed is None:
            task.bad_dates.append(f"{sign} {value}".strip())
        elif sign == "✅":
            task.done = task.done or parsed
        else:
            task.due = task.due or parsed
    task.priority = next((p for s, p in PRIORITY_SIGNS.items() if s in raw), None)
    delegate = DELEGATE_RE.search(raw)
    task.delegate = delegate.group(1) if delegate else None
    task.text = " ".join(re.sub("[⏫🔼🔽]", "", DATE_RE.sub("", raw)).split())
    return task


def parse_text(path: Path, content: str) -> Project:
    lines = content.splitlines()
    meta, errors, start = read_frontmatter(lines)
    project = Project(path, meta, [], errors)
    project.meta_lines = {ln.split(":")[0]: i + 1 for i, ln in enumerate(lines[:start])}
    fence: str | None = None
    in_tasks = False
    for index in range(start, len(lines)):
        line, number = lines[index], index + 1
        opener = FENCE_RE.match(line)
        if fence is not None:
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                fence = None
            continue
        if opener:
            fence = opener.group(1)
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2).strip().lower()
            if level <= 2:
                in_tasks = level == 2 and title == "tasks"
            continue
        match = TASK_RE.match(line)
        if match:
            project.tasks.append(parse_task(path, number, match, in_tasks))
        elif NEAR_MISS_RE.match(line):
            project.near_misses.append(number)
    return project


def parse_note(path: Path) -> Project:
    return parse_text(path, path.read_text(encoding="utf-8", errors="replace"))


def is_note(path: Path, root: Path) -> bool:
    """Skip hidden folders and all-capitals documentation files such as README.md."""
    hidden = any(part.startswith(".") for part in path.relative_to(root).parts)
    return not hidden and not (path.stem == path.stem.upper() and path.stem.lower() != path.stem)


def iter_notes(root: Path) -> Iterator[Project]:
    """Yield every note under root (or root itself if it is a file), sorted by path."""
    if root.is_file():
        yield parse_note(root)
        return
    for path in sorted(root.rglob("*.md")):
        if path.is_file() and is_note(path, root):
            yield parse_note(path)
