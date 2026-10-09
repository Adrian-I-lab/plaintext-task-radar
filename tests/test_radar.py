import json
import os
import re
from datetime import date
from pathlib import Path

import pytest

from taskradar.cli import main
from taskradar.parse import iter_notes, parse_text
from taskradar.radar import build, last_touched

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "examples" / "demo-vault"
GOLDEN = ROOT / "tests" / "golden" / "demo-radar.txt"
TODAY = date(2026, 10, 14)


def note(body: str, status: str = "active", extra: str = "updated: 2026-10-13\n"):
    head = f"---\ntitle: T\nstatus: {status}\npriority: low\n{extra}---\n## Tasks\n"
    return parse_text(Path("n.md"), head + body)


def radar(*projects, horizon: int = 7):
    return build(projects, TODAY, horizon=horizon)


def test_boundaries_today_seven_and_eight_days():
    r = radar(note("- [ ] a 📅 2026-10-14\n- [ ] b 📅 2026-10-21\n- [ ] c 📅 2026-10-22\n"))
    assert [(i.text, i.days) for i in r.due_soon] == [("a", 0), ("b", 7)]
    assert r.overdue == []


def test_horizon_six_drops_the_seven_day_task():
    r = radar(note("- [ ] b 📅 2026-10-21\n"), horizon=6)
    assert r.due_soon == []


def test_in_progress_and_indented_tasks_can_be_overdue():
    r = radar(note("- [~] a 📅 2026-10-12\n- [ ] p\n    - [ ] b 📅 2026-10-13\n"))
    assert [(i.text, i.days) for i in r.overdue] == [("a", 2), ("b", 1)]


def test_closed_markers_never_reach_the_radar():
    body = "".join(f"- [{m}] t 📅 2026-10-01\n" for m in "x->d") + "- [/] u 📅 2026-10-01\n"
    r = radar(note(body + "- [ ] live\n"))
    assert r.overdue == [] and r.due_soon == []


def test_task_text_mentioning_readme_is_counted():
    r = radar(note("- [ ] Update README and CLAUDE notes 📅 2026-10-15\n"))
    assert [i.text for i in r.due_soon] == ["Update README and CLAUDE notes"]


def test_stale_needs_an_old_active_note_and_an_undated_live_task():
    old = "updated: 2026-09-01\n"
    assert [i.days for i in radar(note("- [ ] a\n", extra=old)).stale] == [43]
    assert radar(note("- [ ] a 📅 2026-12-01\n", extra=old)).stale == []
    assert radar(note("- [ ] a\n", status="paused", extra=old)).stale == []
    assert radar(note("- [ ] a\n")).stale == []


def test_stale_limit_is_strictly_more_than_the_limit():
    assert radar(note("- [ ] a\n", extra="updated: 2026-09-23\n")).stale == []
    assert len(radar(note("- [ ] a\n", extra="updated: 2026-09-22\n")).stale) == 1


def test_stale_age_falls_back_to_modification_time(tmp_path):
    path = tmp_path / "n.md"
    path.write_text("---\ntitle: T\nstatus: active\npriority: low\n---\n## Tasks\n- [ ] a\n")
    stamp = 1788000000  # 2026-08-29 in UTC
    os.utime(path, (stamp, stamp))
    (project,) = iter_notes(tmp_path)
    assert last_touched(project) == date.fromtimestamp(stamp)
    assert len(build([project], TODAY).stale) == 1


def test_project_deadline_listed_only_without_a_matching_task():
    extra = "updated: 2026-10-13\ndeadline: 2026-10-16\n"
    assert [i.kind for i in radar(note("- [ ] a\n", extra=extra)).due_soon] == ["deadline"]
    matched = radar(note("- [ ] a 📅 2026-10-16\n", extra=extra))
    assert [i.kind for i in matched.due_soon] == ["task"]


def test_project_checks():
    r = radar(note("- [x] a\n"), note("- [ ] b\n", status="done"),
              note("- [ ] c\n", extra="deadline: 2026-10-01\nupdated: 2026-10-13\n"))
    assert sorted(i.check for i in r.project_issues) == [
        "deadline-passed", "live-tasks-in-closed-project", "no-live-tasks"]


def expected_totals() -> dict[str, int]:
    text = (DEMO / "EXPECTED.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (.+?) \| (\d+) \|$", text, re.M))
    issues = sum(int(v) for k, v in rows.items() if k.startswith("Project issue"))
    return {"overdue": int(rows["Overdue"]), "due_soon": int(rows["Due soon"]),
            "stale": int(rows["Stale"]), "project_issues": issues}


def test_demo_totals_match_expected():
    report = build(iter_notes(DEMO), TODAY)
    assert report.totals() == expected_totals()


def test_golden_text_output(capsys):
    assert main(["radar", str(DEMO), "--today", "2026-10-14"]) == 0
    assert capsys.readouterr().out == GOLDEN.read_text(encoding="utf-8")


def test_json_output_schema(capsys):
    main(["radar", str(DEMO), "--today", "2026-10-14", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["schema_version"] == 1 and data["totals"] == expected_totals()
    assert data["overdue"][0] == {"path": "conference-talk.md", "line": 0, "kind": "deadline",
                                  "text": "Project deadline: Conference talk",
                                  "due": "2026-10-07", "days": 7}


def test_exit_codes(capsys):
    assert main(["radar", str(DEMO), "--today", "2026-10-14", "--fail-on-overdue"]) == 2
    assert main(["radar", str(DEMO), "--today", "2026-01-01", "--fail-on-overdue"]) == 0
    assert main(["lint", str(DEMO)]) == 1
    assert main(["lint", str(DEMO / "half-marathon.md")]) == 0
    with pytest.raises(SystemExit):
        main(["radar", str(DEMO / "missing")])
