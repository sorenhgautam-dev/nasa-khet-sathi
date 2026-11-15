"""The fog on the step soil test (owner, 2026-11-15: space guesses, the ground checks): every word it asks for is in
site/data/words.json in English and Nepali, How we know can read the same numbers, and the long scrolling page is off the
site (the owner chose the click-through version)."""
import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
APP, HOW = (SITE / "js" / "app.js").read_text(), (SITE / "js" / "how.js").read_text()
WORDS = json.loads((SITE / "data" / "words.json").read_text())


def test_every_fog_word_used_is_published_in_english_and_nepali():
    used = set(re.findall(r"T\('fog\.([a-z0-9_]+)'", APP + HOW))
    have = WORDS["shared"]["fog"]
    assert used and not used - set(have), sorted(used - set(have))
    for k in used:
        assert have[k]["en"].strip() and have[k]["ne"].strip(), k
    assert any(g["id"] == "kalman_update" for g in WORDS["glossary"])


def test_how_we_know_reads_the_numbers_the_soil_screen_draws():
    assert "sureOf: sureOf" in APP and "K.sureOf(" in HOW
    assert "fogParts(box, F)" in APP


def test_the_long_page_is_off_the_site():
    assert not (SITE / "js" / "story.js").exists() and not (SITE / "css" / "story.css").exists()
    assert "SCREENS.story" not in APP and "FLOW" not in APP
    assert "SCREENS.home = function" in APP   # the click-through Home is the first screen
