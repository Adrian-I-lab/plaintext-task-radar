from datetime import date
from pathlib import Path

from taskradar.parse import iter_notes, parse_note, parse_text

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
HEAD = "---\ntitle: T\nstatus: active\npriority: low\n---\n"


def parse(body: str, head: str = HEAD):
    return parse_text(Path("note.md"), head + body)


def test_basic_task_fields():
    p = parse("## Tasks\n- [ ] Ring the plumber 📅 2026-10-20 ⏫ @sam\n")
    (t,) = p.tasks
    assert (t.line, t.marker, t.due) == (7, " ", date(2026, 10, 20))
    assert (t.priority, t.delegate) == ("high", "sam")
    assert t.text == "Ring the plumber @sam"
    assert t.live and t.in_tasks_section


def test_six_markers_and_liveness():
    body = "## Tasks\n" + "".join(f"- [{m}] item\n" for m in " ~x->d")
    assert [t.live for t in parse(body).tasks] == [True, True, False, False, False, False]


def test_indented_subtask_is_a_task():
    p = parse("## Tasks\n- [ ] parent\n    - [ ] child 📅 2026-10-13\n\t* [~] tabbed\n")
    assert [t.indent for t in p.tasks] == [0, 4, 4]
    assert p.tasks[1].due == date(2026, 10, 13)


def test_ascii_due_alias():
    (t,) = parse("- [ ] Mend the gate due:2026-10-16\n").tasks
    assert t.due == date(2026, 10, 16) and t.text == "Mend the gate"


def test_done_date_is_not_a_due_date():
    (t,) = parse("- [x] Sweep 📅 2026-10-01 ✅ 2026-09-30\n").tasks
    assert t.due == date(2026, 10, 1) and t.done == date(2026, 9, 30)


def test_bad_date_never_crashes_and_is_recorded():
    (t,) = parse("- [ ] Book the hall 📅 29 Sep\n").tasks
    assert t.due is None and t.bad_dates == ["📅 29"]


def test_impossible_calendar_date_is_bad():
    (t,) = parse("- [ ] Leap 📅 2026-02-30\n").tasks
    assert t.due is None and t.bad_dates == ["📅 2026-02-30"]


def test_fenced_block_is_skipped():
    p = parse("## Tasks\n```markdown\n- [/] example\n-[ ] near\n```\n- [ ] real\n")
    assert [t.text for t in p.tasks] == ["real"] and p.near_misses == []


def test_tilde_fence_and_longer_closer():
    p = parse("~~~\n- [ ] hidden\n~~~~\n- [ ] shown\n")
    assert [t.text for t in p.tasks] == ["shown"]


def test_unclosed_fence_hides_the_rest():
    assert parse("```\n- [ ] hidden\n").tasks == []


def test_tasks_section_tracking():
    p = parse("- [ ] above\n## Tasks\n- [ ] in\n### Sub\n- [ ] still in\n## Log\n- [ ] after\n")
    assert [t.in_tasks_section for t in p.tasks] == [False, True, True, False]


def test_near_miss_lines_are_recorded_not_tasks():
    p = parse("-[ ] no space\n*[x] also\n*[1] Footnote text\n")
    assert p.tasks == [] and p.near_misses == [6, 7]


def test_table_cell_and_backticks_are_not_tasks():
    assert parse("| - [/] cell |\n`- [ ] code`\nText - [ ] inline\n").tasks == []


def test_frontmatter_errors():
    assert parse("x\n", head="").meta_errors == ["no frontmatter block"]
    broken = parse("x\n", head="---\ntitle: [\n---\n")
    assert broken.meta_errors == ["frontmatter is not valid YAML"]
    bad = parse("x\n", head="---\ntitle: T\nstatus: on-hold\npriority: low\nupdated: 14/10\n---\n")
    assert bad.status is None
    assert [e.split()[0] for e in bad.meta_errors] == ["status", "updated"]


def test_frontmatter_dates_parse():
    head = "---\ntitle: T\nstatus: done\npriority: high\ndeadline: 2026-10-07\n---\n"
    p = parse("x\n", head=head)
    assert p.meta_errors == [] and p.deadline == date(2026, 10, 7) and p.status == "done"


def test_unknown_marker_is_kept_but_not_live():
    (t,) = parse("- [/] Re-tape\n").tasks
    assert t.marker == "/" and not t.live


def test_text_mentioning_readme_is_still_a_task(tmp_path):
    (tmp_path / "README.md").write_text("# docs\n")
    (tmp_path / "a.md").write_text(HEAD + "- [ ] Update README and CLAUDE notes\n")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "b.md").write_text(HEAD + "- [ ] hidden\n")
    projects = list(iter_notes(tmp_path))
    assert [p.path.name for p in projects] == ["a.md"]
    assert projects[0].tasks[0].text == "Update README and CLAUDE notes"


def test_demo_vault_parses():
    projects = list(iter_notes(DEMO))
    assert len(projects) == 8
    garden = parse_note(DEMO / "community-garden.md")
    assert sum(t.indent > 0 for t in garden.tasks) == 1
    assert garden.meta["owner"] == "Mara Quill"
