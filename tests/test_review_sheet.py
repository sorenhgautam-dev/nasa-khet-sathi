"""pipeline/words/review_sheet.py: the Nepali review spreadsheet (write, read back, apply)."""
import json
import shutil

import pytest

from pipeline.words import review_sheet as rs
from pipeline.words.texts import is_review_mark

HEADER = ["id", "where it appears in the app", "English", "Nepali", "Correct? (yes/no)", "Corrected Nepali", "Comment"]


def test_rows_put_screens_first_then_plans_then_glossary():
    rows = rs.rows()
    order = [r["where"].split(".")[0] for r in rows]
    assert order == sorted(order), "sections must not interleave"
    first = {o: i for i, o in reversed(list(enumerate(order)))}
    assert first["1"] < first["2"] < first["3"]
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert "screens.what_to_grow.texts.next_h2_6" in ids and any(i.startswith("tabs.") for i in ids)
    assert any(i.startswith("glossary.") for i in ids) and any(i.startswith("crop_explainers.") for i in ids)
    assert all(r["en"] and r["ne"] for r in rows)


def test_xlsx_round_trip_keeps_every_cell(tmp_path):
    rows = [{"id": "a.b", "where": "1. Screen", "en": "Rain & <sun>", "ne": "वर्षा", "ok": "", "fix": "", "note": ""},
            {"id": "c", "where": "2. Plans", "en": "x", "ne": "य", "ok": "yes", "fix": "", "note": "fine"}]
    p = tmp_path / "s.xlsx"
    rs.write_xlsx(rows, p)
    got = rs.read_xlsx(p)
    assert got[0] == dict(zip(HEADER, ["a.b", "1. Screen", "Rain & <sun>", "वर्षा", "", "", ""]))
    assert got[1]["Correct? (yes/no)"] == "yes" and got[1]["Comment"] == "fine"


def _copy_words(tmp_path):
    d = tmp_path / "words"
    shutil.copytree(rs.HERE, d, ignore=shutil.ignore_patterns("__pycache__", "drafts", "*.py", "*.md"))
    return d


def test_apply_marks_correct_and_replaces_corrected(tmp_path):
    d = _copy_words(tmp_path)
    sheet = [dict(zip(HEADER, ["screens.what_to_grow.texts.next_h2_6", "", "6 months", "६ महिना", "yes", "", ""])),
             dict(zip(HEADER, ["screens.what_to_grow.texts.next_h2", "", "3 months", "३ महिना", "no", "तीन महिना", ""])),
             dict(zip(HEADER, ["glossary.ndvi.say", "", "x", "y", "", "", ""]))]       # not answered: untouched
    out = rs.apply_review(sheet, "Test Reviewer", "2026-11-15", words_dir=d)
    assert out["marked"] == 1 and out["corrected"] == 1 and out["unanswered"] == 1
    s = json.loads((d / "screens.json").read_text())
    node = {t["id"]: t for sc in s["screens"] if sc["id"] == "what_to_grow" for t in sc["texts"]}
    assert node["next_h2"]["ne"] == "तीन महिना" and node["next_h2_6"]["ne"] == "६ महिना"
    assert node["next_h2"]["ne_review"] == "reviewed by Test Reviewer, 2026-11-15"
    assert is_review_mark(node["next_h2_6"]["ne_review"])


def test_apply_refuses_a_correction_that_drops_a_placeholder(tmp_path):
    d = _copy_words(tmp_path)
    sheet = [dict(zip(HEADER, ["screens.last_years.title", "", "", "", "no", "पछिल्ला वर्ष", ""]))]
    with pytest.raises(ValueError, match="year_count"):
        rs.apply_review(sheet, "Test Reviewer", "2026-11-15", words_dir=d)


def test_unchanged_files_are_written_back_byte_for_byte(tmp_path):
    d = _copy_words(tmp_path)
    before = {f: (d / f"{f}.json").read_bytes() for f in rs.FILES}
    rs.apply_review([], "Test Reviewer", "2026-11-15", words_dir=d)
    assert {f: (d / f"{f}.json").read_bytes() for f in rs.FILES} == before
