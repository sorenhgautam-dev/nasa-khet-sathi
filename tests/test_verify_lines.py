"""Owner, 2026-11-15: every row of the compliance table says in one plain line what would verify it (English in
rules.yaml verification.outputs.<id>.verify_by, Nepali drafts in build_story.VERIFY_BY_NE); the monsoon-shift sentence is
sourced to DHM alone and scored by its own row; How we know shows "How each answer becomes verified"."""
import json
from pathlib import Path

from pipeline.export import build_story as bs
from pipeline.fetch.rules import load_rules

ROOT = Path(__file__).resolve().parents[1]
OUTS = load_rules()["verification"]["outputs"]


def test_every_row_has_a_plain_line_and_its_nepali():
    for k, o in OUTS.items():
        assert o.get("verify_by"), k
        assert o["verify_by"] == "-" or bs.VERIFY_BY_NE.get(k), k
        assert k in bs.COMPLIANCE, k


def test_the_line_is_shown_only_while_a_row_is_not_verified():
    row = {"status": "ESTIMATE", "verify_by": OUTS["soil_month_words"]["verify_by"]}
    vb = bs.verify_by("soil_month_words", row)
    assert vb["en"].endswith(OUTS["soil_month_words"]["verify_by"]) and vb["ne"]
    assert bs.verify_by("soil_month_words", {**row, "status": "VERIFIED"}) is None


def test_how_each_answer_becomes_verified_counts_the_rows():
    rows = [{"status": "VERIFIED"}, {"status": "ESTIMATE"}, {"status": "ESTIMATE"}, {"status": "NOT YET VERIFIABLE"}]
    vh = bs.verify_how(rows, {"pct": 92, "nmin": 10})
    assert any("Today: 1 verified, 2 estimates, 1 not yet checkable." == t["en"] for t in vh["lines"])
    assert all(t["en"] and t["ne"] for t in vh["lines"] + [vh["title"]])


def test_the_shift_sentence_is_sourced_to_dhm_and_scored():
    lab = load_rules()["labels"]["outputs"]["monsoon_shift"]
    assert lab["inputs"] == ["dhm_onset"] and lab["also"] == [] and lab["scorecard"] == ["monsoon_shift"]


def test_how_we_know_renders_the_line_and_the_section():
    how = (ROOT / "site/js/how.js").read_text()
    assert "r.verify_by" in how and "st.verify_how" in how
