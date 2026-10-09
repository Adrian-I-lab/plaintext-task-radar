import re
from datetime import date
from pathlib import Path

from taskradar.cli import main
from taskradar.html import render
from taskradar.parse import iter_notes, parse_text
from taskradar.radar import build

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo-vault"
HEAD = "---\ntitle: T\nstatus: active\npriority: low\nupdated: 2026-10-13\n---\n## Tasks\n"


def demo_html() -> str:
    return render(build(iter_notes(DEMO), date(2026, 10, 14)), DEMO)


def test_note_text_is_escaped():
    project = parse_text(Path("n.md"), HEAD + "- [ ] <script>alert(1)</script> 📅 2026-10-13\n")
    html = render(build([project], date(2026, 10, 14)), Path("."))
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_no_external_urls_or_scripts():
    html = demo_html()
    assert "http://" not in html and "https://" not in html
    assert "<script" not in html.lower() and "@import" not in html


def test_header_totals_equal_report_totals():
    report = build(iter_notes(DEMO), date(2026, 10, 14))
    html = render(report, DEMO)
    shown = dict(re.findall(r'data-total="(\w+)"><b>(\d+)</b>', html))
    assert {k: int(v) for k, v in shown.items()} == report.totals()


def test_dark_mode_and_phone_width_support():
    html = demo_html()
    assert "prefers-color-scheme: dark" in html
    assert 'name="viewport"' in html and "overflow-x: auto" in html


def test_cli_writes_the_file(tmp_path, capsys):
    out = tmp_path / "out" / "report.html"
    assert main(["radar", str(DEMO), "--today", "2026-10-14", "--html", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == demo_html()
    assert capsys.readouterr().out.startswith("Radar for 2026-10-14")
