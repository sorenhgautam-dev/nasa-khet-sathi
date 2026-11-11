"""Fetch modules append their source to CREDITS.md (CLAUDE.md "Data sources", item 4), once."""
from pipeline.fetch.credits import HEADING, ensure_credit


def test_adds_a_line_only_once(tmp_path):
    p = tmp_path / "CREDITS.md"
    p.write_text("# CREDITS\n")
    ensure_credit(p, "- NASA POWER daily, demo")
    ensure_credit(p, "- NASA POWER daily, demo")
    assert p.read_text().count("- NASA POWER daily, demo") == 1


def test_puts_lines_under_one_heading(tmp_path):
    p = tmp_path / "CREDITS.md"
    p.write_text("# CREDITS\n")
    ensure_credit(p, "- a")
    ensure_credit(p, "- b")
    text = p.read_text()
    assert text.count(HEADING) == 1 and text.index(HEADING) < text.index("- a") < text.index("- b")
