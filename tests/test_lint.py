import re
from pathlib import Path

from taskradar.lint import counts, format_finding, lint, lint_project
from taskradar.parse import iter_notes, parse_text

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
HEAD = "---\ntitle: T\nstatus: active\npriority: low\n---\n## Tasks\n"


def rules(body: str, head: str = HEAD) -> list[str]:
    return [f.rule for f in lint_project(parse_text(Path("n.md"), head + body))]


def expected_counts() -> dict[str, int]:
    text = (DEMO / "EXPECTED.md").read_text(encoding="utf-8")
    return {m[0]: int(m[1]) for m in re.findall(r"^\| (L00\d) \| (\d+) \|$", text, re.M)}


def test_clean_note_has_no_findings():
    assert rules("- [ ] a 📅 2026-10-20\n- [d] b @sam\n- [x] c ✅ 2026-10-01\n") == []


def test_l001_unknown_marker_with_fix_hints():
    found = lint_project(parse_text(Path("n.md"), HEAD + "- [/] a\n- [X] b\n- [?] c\n"))
    assert [f.fix for f in found] == ["use [~]", "use [x]", ""]
    assert {f.rule for f in found} == {"L001"}
    assert "not one of the six markers" in found[2].message


def test_l001_fenced_negative_control_and_positive_twin():
    assert rules("```\n- [/] example\n```\n") == []
    assert rules("- [/] example\n") == ["L001"]


def test_backticks_and_table_cells_are_never_findings():
    assert rules("Use `- [/]` for nothing.\n| - [/] | cell |\n") == []


def test_l002_malformed_due_and_done_dates():
    assert rules("- [ ] a 📅 29 Sep\n- [x] b ✅ 2026-13-01\n- [ ] c due:soon\n") == ["L002"] * 3


def test_l003_no_space_after_bullet():
    assert rules("-[ ] a\n*[x] b\n  -[~] c\n") == ["L003"] * 3


def test_l003_footnote_negative_control_and_positive_twin():
    assert rules("*[1] Reference to a source\n") == []
    assert rules("*[x] Reference to a source\n") == ["L003"]


def test_l004_delegated_without_name():
    assert rules("- [d] Collect keys\n") == ["L004"]
    assert rules("- [d] Collect keys @sam\n") == []
    assert rules("- [d] Mail it to sam@example.org\n") == ["L004"]


def test_l005_task_outside_tasks_section():
    head = "---\ntitle: T\nstatus: active\npriority: low\n---\n"
    assert rules("- [ ] early\n## Tasks\n- [ ] fine\n## Log\n- [ ] late\n", head) == ["L005"] * 2


def test_l006_frontmatter_problems_point_at_the_key():
    head = "---\ntitle: T\nstatus: on-hold\npriority: urgent\n---\n## Tasks\n"
    found = lint_project(parse_text(Path("n.md"), head))
    assert [(f.rule, f.line) for f in found] == [("L006", 3), ("L006", 4)]
    assert rules("## Tasks\n- [ ] a\n", head="") == ["L006"]


def test_order_is_path_then_line_then_rule():
    found = lint_project(parse_text(Path("n.md"), "- [/] a 📅 29 Sep\n"))
    assert [(f.line, f.rule) for f in found] == [(1, "L001"), (1, "L002"), (1, "L005"), (1, "L006")]


def test_format_finding_is_relative_and_includes_fix():
    finding = lint_project(parse_text(DEMO / "x.md", HEAD + "- [/] a\n"))[0]
    expected = "x.md:7: L001 error: [/] is not one of the six markers (fix: use [~])"
    assert format_finding(finding, DEMO) == expected


def test_demo_vault_golden_counts():
    found = lint(iter_notes(DEMO))
    assert dict(counts(found)) == expected_counts()
    assert sum(f.severity == "error" for f in found) == 6
    assert sum(f.severity == "warning" for f in found) == 1
    assert [(f.path.name, f.line, f.rule) for f in found] == [
        ("bike-repair.md", 15, "L001"),
        ("book-club.md", 11, "L005"),
        ("book-club.md", 16, "L004"),
        ("book-club.md", 17, "L001"),
        ("conference-talk.md", 15, "L002"),
        ("conference-talk.md", 16, "L003"),
        ("tidy-csv-library.md", 3, "L006"),
    ]
