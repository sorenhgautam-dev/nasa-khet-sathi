"""Two judge-facing additions (owner, 2026-11-15 evening): every language in one list (a globe with the count in the top bar
opens it; each language in its own script, with who wrote it and whether a native speaker has checked it), and "Our data,
explained" first on How we know (how to read the numbers, every source, the raw files every screen reads, the public code,
the languages), reached from Home's one judges' link. Every word is in every language; every linked file exists."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
APP = (SITE / "js" / "app.js").read_text()
HOW = (SITE / "js" / "how.js").read_text()
WORDS = json.loads((SITE / "data" / "words.json").read_text())
NEW = ["lang_title", "lang_count", "lang_tap", "lang_source", "lang_review", "lang_draft", "data_title", "data_lead",
       "data_read_h", "data_read_1", "data_read_2", "data_read_3", "data_read_4", "data_read_5", "data_list_h",
       "data_list_note", "data_files_h", "data_files_lead", "file_field", "file_behind", "file_story", "file_words",
       "file_index", "file_version", "data_code", "more_crops"]


def test_every_new_word_is_in_every_language():
    langs = [x["code"] for x in WORDS["languages"]]
    farm = WORDS["shared"]["farm"]
    for key in NEW:
        assert all(farm[key].get(lang) for lang in langs), key
        assert farm[key]["ne_review"] == "needs native-speaker review", key
    assert all("{count}" in farm["lang_count"][lang] for lang in langs)


def test_the_top_bar_opens_one_list_of_every_language():
    assert "<select" not in APP and "h('select'" not in APP                   # the hidden '···' menu is gone
    assert "class: 'globe'" in APP and "onclick: openLangs" in APP
    body = APP[APP.index("function langList("):APP.index("function openLangs(")]
    for key in ("farm.lang_source", "farm.lang_draft", "farm.lang_review"):
        assert key in body                                                  # who wrote it, and its review state


def test_data_guide_comes_first_and_every_linked_file_exists():
    assert "mine.unshift(dataGuide(F));" in HOW and "addToc('data'" in HOW
    assert APP.count("class: 'judges', href: '#/how'") == 1                    # Home keeps one small judges' link
    files = re.findall(r"\['(data/[a-z]+\.json)'", HOW)
    assert len(files) == 5 and all((SITE / f).exists() for f in files), files
    for f in json.loads((SITE / "data" / "index.json").read_text())["fields"]:
        assert (SITE / "data" / "fields" / f"{f['id']}.json").exists()       # 'This field' opens the field's own file


def test_pea_and_cabbage_are_named_on_both_next_screens_never_scored():
    assert APP.count("moreCrops(), tags, advisorNote(monthsNote())") == 2       # Next 3 and Next 6 months, under More
    assert "pea" not in json.loads((REPO / "config" / "crops.json").read_text())["crops"]   # not in the twin's crops
