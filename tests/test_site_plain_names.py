"""C (owner, 2026-11-15): plain names. No farmer screen (home, photo, parts, soil, choose, today, next, weather, trial)
says "Field Twin" or "replay"; "Field Twin" appears once, in brackets, in How we know's explanation."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = json.loads((ROOT / "pipeline" / "words" / "screens.json").read_text())
# the words groups those screens read (the Replay, Your plan and 2040 screens and How we know are not farmer screens)
FARMER_SCREENS = ["home", "where", "from_space", "parts", "each_part", "check_soil", "what_to_grow"]
FARMER_SHARED = ["weather"]
BANNED = re.compile(r"twin|replay", re.I)


def _texts(x):
    if isinstance(x, dict):
        if isinstance(x.get("en"), str):
            yield x.get("id", ""), x["en"]
        for v in x.values():
            yield from _texts(v)
    elif isinstance(x, list):
        for v in x:
            yield from _texts(v)


def test_no_farmer_screen_word_says_field_twin_or_replay():
    groups = [s for s in WORDS["screens"] if s["id"] in FARMER_SCREENS] + [WORDS["shared"][g] for g in FARMER_SHARED]
    assert len(groups) == len(FARMER_SCREENS) + len(FARMER_SHARED)
    bad = [(i, t) for g in groups for i, t in _texts(g) if BANNED.search(t)]
    assert not bad, bad


def test_field_twin_is_named_once_in_brackets_in_how_we_know():
    # the name is the glossary's own term (science words live only there), put in brackets in How we know's three pictures
    assert not [t for _, t in _texts(WORDS) if "field twin" in t.lower()]
    how = (ROOT / "site" / "js" / "how.js").read_text()
    pics = how[how.index("  function twinPics"):how.index("  function animBox")]
    assert how.count("'field_twin'") == 1 and "'field_twin'" in pics and "'(' + name + ')'" in pics


def test_the_flow_line_says_what_happens_in_plain_words():
    behind = json.loads((ROOT / "site" / "data" / "behind.json").read_text())
    n = len(json.loads((ROOT / "site" / "data" / "fields" / f"{behind['field']}.json").read_text())["replay"]["current"])
    assert [f["en"] for f in behind["flow"]] == ["NASA data", "A copy of your field", f"Tested in {n} past years", "Your answers"]
    assert not [c["id"] for c in behind["cards"] if BANNED.search(c["say"]["en"])]
