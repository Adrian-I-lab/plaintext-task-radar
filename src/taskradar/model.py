"""Data types shared by the parser, the linter, and the radar."""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

MARKERS = {" ": "open", "~": "in progress", "x": "done",
           "-": "cancelled", ">": "migrated", "d": "delegated"}
LIVE = frozenset({" ", "~"})
STATUSES = ("active", "paused", "done", "dropped")
PRIORITIES = ("high", "medium", "low")


def to_date(value: Any) -> date | None:
    """Return a date for a real YYYY-MM-DD value (string or YAML date), else None."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else None
    except ValueError:
        return None


@dataclass
class Task:
    file: Path
    line: int
    indent: int
    marker: str
    text: str
    due: date | None = None
    done: date | None = None
    priority: str | None = None
    delegate: str | None = None
    in_tasks_section: bool = True
    bad_dates: list[str] = field(default_factory=list)

    @property
    def live(self) -> bool:
        return self.marker in LIVE


@dataclass
class Project:
    path: Path
    meta: dict[str, Any]
    tasks: list[Task]
    meta_errors: list[str]
    near_misses: list[int] = field(default_factory=list)

    @property
    def status(self) -> str | None:
        value = self.meta.get("status")
        return value if value in STATUSES else None

    @property
    def deadline(self) -> date | None:
        return to_date(self.meta.get("deadline"))

    @property
    def live_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.live]
