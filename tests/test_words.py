"""pipeline/words/: the plain words (SI component 3, text only).

Checks the rules in CLAUDE.md "Site rules" and the parallel-session brief:
every text has English and Nepali (each Nepali text marked "needs native-speaker review" or
"reviewed by <name>, <date>"), screen sentences have
eight words or fewer, every placeholder is one the pipeline provides, and no science word appears
outside the glossary.
"""
import json
import re
from pathlib import Path

import pytest

from pipeline.words import texts
from pipeline.words.texts import (
    NE_REVIEW, PlaceholderError, fill, is_review_mark, iter_text_nodes, load, placeholders, render_tab,
    science_hits, sentences, word_count,
)

REPO = Path(__file__).resolve().parents[1]
CROPS = json.loads((REPO / "config" / "crops.json").read_text())["crops"]

SCREEN_IDS = ["home", "where", "from_space", "parts", "each_part", "check_soil",
              "last_years", "what_to_grow", "field_future", "your_plan"]
REQUIRED_TERMS = ["evapotranspiration", "soil_moisture_anomaly", "ndvi", "frost_risk",
                  "water_balance", "monsoon_onset", "bare_days", "crop_rotation", "cover_crop"]
TABS = ["why", "evidence", "benefits", "unknown", "check"]
EXPLAINERS = ["nitrogen_fixing", "cover", "deep_rooting", "drought_tolerant"]
PUBLISHERS = {"FAO", "CGIAR", "ICRISAT", "ICARDA", "CIMMYT", "IRRI", "CIP",
              "Alliance Bioversity-CIAT", "IWMI", "ILRI", "NARC"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def farmer_nodes():
    """Every text a farmer reads on the screens: screens, tabs, tips, crop explainers."""
    for name in ("screens", "tabs", "crop_explainers"):
        for path, node in iter_text_nodes(load(name)):
            yield f"{name}:{path}", node


def all_nodes():
    for name in texts.WORD_FILES:
        for path, node in iter_text_nodes(load(name)):
            yield f"{name}:{path}", node


# ---------- helpers (worked examples) ----------

def test_sentences_split_on_full_stops_and_the_danda():
    assert sentences("Tap a part. Then wait!", "en") == ["Tap a part.", "Then wait!"]
    assert sentences("हरेक भाग कस्तो छ? राम्रो छ।", "ne") == ["हरेक भाग कस्तो छ?", "राम्रो छ।"]


def test_word_count_counts_a_placeholder_as_one_word():
    assert word_count("No crop on {bare_days} days each year.") == 7
    assert word_count("Harvest: {future_low} to {future_high} out of 100.") == 7
    assert word_count("हरेक वर्ष {bare_days} दिन खेतमा बाली हुँदैन।") == 7


def test_placeholders_are_found_with_suffixes_attached():
    assert placeholders("{legume_crop}ले माटोमा मल थप्छ।") == {"legume_crop"}
    assert placeholders("Since {year_first}, the rains start {shift_days_abs} days earlier.") == {
        "year_first", "shift_days_abs"}


def test_science_hits_finds_whole_words_and_phrases_only():
    words = {"en": ["yield", "cover crop", "data"], "ne": ["भू-उपग्रह"]}
    assert science_hits("The yield fell.", "en", words) == ["yield"]
    assert science_hits("Grow a cover-crop now.", "en", words) == ["cover crop"]
    assert science_hits("We update it.", "en", words) == []          # 'data' is not inside 'update'
    assert science_hits("Words in {dataset} are skipped.", "en", {"en": ["dataset"], "ne": []}) == []
    assert science_hits("भू-उपग्रहबाट हेरियो।", "ne", words) == ["भू-उपग्रह"]


def test_fill_uses_devanagari_digits_in_nepali_and_fails_on_a_missing_value():
    node = {"en": "No crop on {bare_days} days each year.",
            "ne": "हरेक वर्ष {bare_days} दिन खेतमा बाली हुँदैन।"}
    assert fill(node, {"bare_days": 110}, "en") == "No crop on 110 days each year."
    assert fill(node, {"bare_days": 110}, "ne") == "हरेक वर्ष ११० दिन खेतमा बाली हुँदैन।"
    with pytest.raises(PlaceholderError, match="bare_days"):
        fill(node, {}, "en")


def test_fill_translates_names_per_language():
    node = {"en": "Ask if {legume_crop} grows well here.", "ne": "यहाँ {legume_crop} राम्रो हुन्छ कि सोध्नुहोस्।"}
    value = {"en": "lentil", "ne": "मसुर"}
    assert fill(node, {"legume_crop": value}, "ne") == "यहाँ मसुर राम्रो हुन्छ कि सोध्नुहोस्।"


def test_render_tab_picks_sentences_by_condition_and_falls_back():
    tab = [
        {"id": "a", "when": ["always"], "en": "One.", "ne": "एक।"},
        {"id": "b", "when": ["has_legume"], "en": "Two {legume_crop}.", "ne": "दुई {legume_crop}।"},
        {"id": "c", "when": ["fallback"], "en": "None.", "ne": "छैन।"},
    ]
    assert render_tab(tab, set(), {}, "en") == "One."
    assert render_tab(tab, {"has_legume"}, {"legume_crop": {"en": "lentil", "ne": "मसुर"}}, "en") == "One. Two lentil."
    assert render_tab(tab[1:], set(), {}, "en") == "None."


def test_render_tab_repeats_a_line_for_each_source():
    tab = [{"id": "s", "when": ["always"], "repeat": "sources",
            "en": "{source_name}: {source_years}.", "ne": "{source_name}: {source_years}।"}]
    values = {"sources": [{"source_name": "GPM IMERG", "source_years": "2001-2025"},
                          {"source_name": "NASA POWER", "source_years": "2001-2025"}]}
    assert render_tab(tab, set(), values, "en") == "GPM IMERG: 2001-2025. NASA POWER: 2001-2025."


# ---------- every text: English and Nepali ----------

def test_word_files_load():
    for name in texts.WORD_FILES:
        assert load(name)


def test_review_mark_is_needs_review_or_a_real_name_and_date():
    assert is_review_mark(NE_REVIEW)
    assert is_review_mark("reviewed by Asha Rai, 2026-11-12")
    assert is_review_mark("reviewed by आशा राई, 2026-11-12")
    for bad in ("reviewed by [your full name], 2026-11-12",   # a template left unfilled
                "reviewed by [your name], 2026-11-12",
                "reviewed by , 2026-11-12", "reviewed by  , 2026-11-12",
                "reviewed by Asha Rai", "reviewed by Asha Rai, 2026-13-40", "reviewed by Asha Rai, 12-11-2026",
                "reviewed", "", None):
        assert not is_review_mark(bad), bad


def test_every_text_has_english_and_nepali_marked_for_review():
    nodes = list(all_nodes())
    assert len(nodes) > 100
    for where, node in nodes:
        assert str(node.get("en", "")).strip(), f"{where}: no English"
        ne = str(node.get("ne", "")).strip()
        assert ne, f"{where}: no Nepali"
        assert DEVANAGARI.search(ne), f"{where}: Nepali is not in Devanagari: {ne!r}"
        assert is_review_mark(node.get("ne_review")), (
            f"{where}: ne_review must be '{NE_REVIEW}' or 'reviewed by <name>, <YYYY-MM-DD>', "
            f"not {node.get('ne_review')!r}")


def test_nepali_uses_devanagari_digits_and_the_danda():
    for where, node in all_nodes():
        static = re.sub(r"\{[a-z0-9_]+\}", "", node["ne"])
        assert not re.search(r"[0-9]", static), f"{where}: ASCII digit in Nepali: {node['ne']!r}"
        assert "." not in static, f"{where}: full stop in Nepali (use the danda): {node['ne']!r}"


def test_no_text_node_is_missing_its_english_twin():
    def walk(obj, path=""):
        if isinstance(obj, dict):
            if "ne" in obj:
                assert "en" in obj, f"{path}: Nepali without English"
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
    for name in texts.WORD_FILES:
        walk(load(name), name)


# ---------- screens: eight words, ten screens ----------

def test_the_ten_screens_are_there_in_order():
    screens = load("screens")["screens"]
    assert [s["id"] for s in screens] == SCREEN_IDS
    for s in screens:
        assert s["title"]["en"] and s["texts"], s["id"]


@pytest.mark.parametrize("lang", ["en", "ne"])
def test_no_farmer_sentence_has_more_than_eight_words(lang):
    long = [(w, s, word_count(s)) for w, node in farmer_nodes()
            for s in sentences(node[lang], lang) if word_count(s) > texts.MAX_WORDS_SCREEN]
    assert not long, "\n".join(f"{w}: {n} words: {s}" for w, s, n in long)


def test_every_screen_glossary_link_exists():
    ids = {t["id"] for t in load("glossary")["terms"]}
    for s in load("screens")["screens"]:
        for g in s.get("glossary", []):
            assert g in ids, f"screen {s['id']} links unknown glossary term {g}"


# ---------- placeholders and conditions: only what the pipeline provides ----------

def test_every_placeholder_is_in_the_registry():
    known = set(load("fill_registry")["placeholders"])
    for where, node in all_nodes():
        for lang in ("en", "ne"):
            unknown = placeholders(node[lang]) - known
            assert not unknown, f"{where} ({lang}): unknown placeholder(s) {sorted(unknown)}"


def test_english_and_nepali_use_the_same_placeholders():
    for where, node in all_nodes():
        assert placeholders(node["en"]) == placeholders(node["ne"]), where


def test_every_registry_placeholder_is_used():
    used = set()
    for _, node in all_nodes():
        used |= placeholders(node["en"])
    stale = set(load("fill_registry")["placeholders"]) - used
    assert not stale, f"registry entries no text uses: {sorted(stale)}"


def test_every_registry_entry_points_at_something_that_exists():
    """Each placeholder and condition names where its value comes from: a path in the output
    contract (pipeline/export/schema.json), a key in config/crops.json or the field YAML, or a
    word list in pipeline/words. Every one of those paths must resolve."""
    reg = load("fill_registry")
    for kind in ("placeholders", "conditions"):
        for name, entry in reg[kind].items():
            assert entry.get("from"), f"{kind}.{name}: no 'from'"
            assert str(entry.get("how", "")).strip(), f"{kind}.{name}: no 'how'"
            for ref in entry["from"]:
                assert texts.resolve_ref(ref), f"{kind}.{name}: '{ref}' does not resolve"


def test_resolve_ref_rejects_paths_that_do_not_exist():
    assert texts.resolve_ref("contract:diary.bare_days")
    assert texts.resolve_ref("contract:replay.*[].irrigated.harvest")
    assert texts.resolve_ref("crops:*.legume")
    assert texts.resolve_ref("field:water_source")
    assert texts.resolve_ref("words:screens.shared.crop_names")
    assert texts.resolve_ref("code:pipeline/twin/soil_water.py:run_bucket")
    assert not texts.resolve_ref("contract:diary.bare_weeks")
    assert not texts.resolve_ref("crops:*.colour")
    assert not texts.resolve_ref("field:soil_colour")
    assert not texts.resolve_ref("code:pipeline/twin/soil_water.py:no_such_function")
    assert not texts.resolve_ref("code:pipeline/twin/no_such_file.py:run_bucket")
    assert not texts.resolve_ref("nowhere:x")


def test_every_condition_used_is_in_the_registry():
    known = set(load("fill_registry")["conditions"]) | {"always", "fallback"}
    def check(node, where):
        for c in node.get("when", []):
            assert c in known, f"{where}: unknown condition {c}"
    for where, node in all_nodes():
        check(node, where)


def test_every_condition_has_plain_words_for_the_reviewer():
    for name, entry in load("fill_registry")["conditions"].items():
        assert str(entry.get("plain", "")).strip(), name


# ---------- science words stay in the glossary ----------

def test_no_science_word_outside_the_glossary():
    words = texts.science_words()
    assert "yield" in words["en"] and "evapotranspiration" in words["en"]
    hits = [(w, lang, h) for w, node in farmer_nodes() for lang in ("en", "ne")
            for h in science_hits(node[lang], lang, words)]
    assert not hits, "\n".join(f"{w} ({lang}): {h}" for w, lang, h in hits)


def test_glossary_has_the_required_terms_one_short_sentence_each():
    terms = {t["id"]: t for t in load("glossary")["terms"]}
    for t in REQUIRED_TERMS:
        assert t in terms, f"glossary lacks {t}"
    for tid, t in terms.items():
        for lang in ("en", "ne"):
            said = sentences(t["say"][lang], lang)
            assert len(said) == 1, f"{tid} ({lang}): {len(said)} sentences"
            assert word_count(said[0]) <= texts.MAX_WORDS_GLOSSARY, f"{tid} ({lang}): too long"


# ---------- crop explainers ----------

def test_crop_explainers_cover_the_four_kinds_with_local_examples():
    ex = load("crop_explainers")["explainers"]
    glossary = {t["id"] for t in load("glossary")["terms"]}
    assert set(EXPLAINERS) <= set(ex)
    for key, e in ex.items():
        assert e["glossary_term"] in glossary, key
        assert e["examples"], f"{key}: no local example"
        for crop in e["examples"]:
            assert crop in CROPS, f"{key}: {crop} is not in config/crops.json"
        assert e["claims"], f"{key}: no claims"


def test_every_crop_explainer_claim_has_an_opened_source():
    for key, e in load("crop_explainers")["explainers"].items():
        for i, claim in enumerate(e["claims"]):
            src = claim.get("source") or {}
            where = f"{key}.claims[{i}]"
            assert src.get("publisher") in PUBLISHERS, f"{where}: publisher {src.get('publisher')!r}"
            assert str(src.get("url", "")).startswith("https://"), f"{where}: no https url"
            assert str(src.get("quote", "")).strip(), f"{where}: no quote"
            assert str(src.get("title", "")).strip(), f"{where}: no title"
            assert "TODO" not in json.dumps(src), f"{where}: unfinished source"


def test_lentil_is_the_nitrogen_example_because_crops_json_says_legume():
    ex = load("crop_explainers")["explainers"]["nitrogen_fixing"]
    for crop in ex["examples"]:
        assert CROPS[crop]["legume"] is True


def test_deep_rooting_examples_are_deeper_than_the_shallow_ones():
    ex = load("crop_explainers")["explainers"]["deep_rooting"]
    shallow = [c for c in CROPS.values() if c.get("zr_m")]
    least = min(c["zr_m"] for c in shallow)
    for crop in ex["examples"]:
        assert CROPS[crop]["zr_m"] is not None and CROPS[crop]["zr_m"] > least


# ---------- five tabs ----------

def test_every_tab_has_templates_and_never_comes_out_empty():
    tabs = load("tabs")["tabs"]
    assert list(tabs) == TABS
    for tab, lines in tabs.items():
        assert lines, tab
        assert any(set(l["when"]) & {"always", "fallback"} for l in lines), f"{tab} can come out empty"


def test_each_plan_kind_has_its_own_why():
    whens = [set(l["when"]) for l in load("tabs")["tabs"]["why"]]
    for kind in ("plan_is_current", "plan_is_cover_gap", "plan_is_follow_shift"):
        assert any(kind in w for w in whens), kind


def test_a_rendered_tab_is_never_empty_for_any_plan_kind():
    tabs = load("tabs")["tabs"]
    reg = load("fill_registry")["placeholders"]
    sample = {name: entry["example"] for name, entry in reg.items()}
    sample["sources"] = [{k: reg[k]["example"] for k in reg if k.startswith("source_")}]
    for kind in ("plan_is_current", "plan_is_cover_gap", "plan_is_follow_shift"):
        for tab, lines in tabs.items():
            for lang in ("en", "ne"):
                assert render_tab(lines, {kind}, sample, lang).strip(), (kind, tab, lang)


# ---------- preview ----------

def test_preview_md_is_up_to_date():
    from pipeline.words import preview
    path = REPO / "pipeline" / "words" / "PREVIEW.md"
    assert path.exists(), "run: .venv/bin/python -m pipeline.words.preview"
    assert path.read_text() == preview.render(), "PREVIEW.md is stale: run .venv/bin/python -m pipeline.words.preview"


def test_preview_status_line_counts_each_review_mark():
    from pipeline.words import preview
    todo = {"ne_review": NE_REVIEW}
    done = {"ne_review": "reviewed by Asha Rai, 2026-11-12"}
    assert preview.status_line([todo, todo]) == "*Nepali: needs native-speaker review.*"
    assert preview.status_line([done]) == "*Nepali: reviewed by Asha Rai, 2026-11-12.*"
    assert preview.status_line([todo, done, done]) == (
        "*Nepali: 2 reviewed by Asha Rai, 2026-11-12; 1 needs native-speaker review.*")


def test_preview_header_gives_each_word_file_its_review_status():
    from pipeline.words import preview
    md = preview.render()
    for name in texts.WORD_FILES:
        nodes = [n for _, n in iter_text_nodes(load(name))]
        line = f"({name}.json, {len(nodes)} texts): {preview.review_status(nodes)}."
        assert line in md, f"PREVIEW.md header lacks: {line}"


def test_preview_lists_every_text():
    from pipeline.words import preview
    md = preview.render()
    for where, node in all_nodes():
        assert preview.cell(node["en"]) in md, f"{where}: English missing from preview"
        assert preview.cell(node["ne"]) in md, f"{where}: Nepali missing from preview"
    assert "```" not in md, "PREVIEW.md must hold words only, no code"


# ---------- owner's decisions on the words, 2026-11-12 ----------

# Choice 7: in Nepali, each month is the Bikram Sambat month that begins in it (about mid-month), with
# the approximate Gregorian months beside it, e.g. बैशाख (Apr–May); a note says they don't line up exactly.
BS_BEGINNING_IN = {"Jan": "माघ", "Feb": "फागुन", "Mar": "चैत", "Apr": "बैशाख", "May": "जेठ", "Jun": "असार",
                   "Jul": "साउन", "Aug": "भदौ", "Sep": "असोज", "Oct": "कात्तिक", "Nov": "मंसिर", "Dec": "पुस"}
MONTH_PLACEHOLDERS = {"month", "sow_month", "harvest_month"}


def _screen(sid):
    return next(s for s in load("screens")["screens"] if s["id"] == sid)


def test_nepali_months_are_bikram_sambat_first_with_the_gregorian_months_beside():
    months = load("screens")["shared"]["months"]
    keys = list(BS_BEGINNING_IN)
    assert list(months) == keys
    for i, key in enumerate(keys):
        assert months[key]["ne"] == f"{BS_BEGINNING_IN[key]} ({key}–{keys[(i + 1) % 12]})"
    assert months["Apr"]["ne"] == "बैशाख (Apr–May)"          # the owner's own example
    assert months["Apr"]["en"] == "April"                     # English stays Gregorian


def test_every_screen_that_names_a_month_says_the_months_do_not_line_up():
    tab_month = any(placeholders(n["en"]) & MONTH_PLACEHOLDERS for _, n in iter_text_nodes(load("tabs")))
    needs = {"from_space"}                                     # the twelve-month calendar
    for s in load("screens")["screens"]:
        if any(placeholders(t["en"]) & MONTH_PLACEHOLDERS for t in s["texts"]):
            needs.add(s["id"])
    if tab_month:
        needs.add("what_to_grow")                              # tips name a month
    for sid in needs:
        note = [t for t in _screen(sid)["texts"] if t["id"] == "months_note"]
        assert note, f"{sid}: no months_note"
        assert "ठ्याक्कै" in note[0]["ne"] and "exactly" in note[0]["en"]


def test_month_examples_in_the_registry_use_the_nepali_month_words():
    months = load("screens")["shared"]["months"]
    nepali = {m["ne"] for m in months.values()}
    reg = load("fill_registry")["placeholders"]
    for key in MONTH_PLACEHOLDERS:
        assert reg[key]["example"]["ne"] in nepali, key


# Choice 9: a section's temp is soil temperature from the probe.
def test_section_temperature_is_worded_as_soil_temperature_from_the_probe():
    node = next(t for t in _screen("each_part")["texts"] if t["id"] == "how_warm")
    assert "soil" in node["en"].lower() and "माटो" in node["ne"]
    assert "probe" in load("fill_registry")["placeholders"]["temp"]["how"]
