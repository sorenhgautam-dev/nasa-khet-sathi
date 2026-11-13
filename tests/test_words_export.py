"""site/data/words.json (owner's answer 16 to REVIEW_2, 2026-11-13): the screen words, glossary and crop explainers
published for the site, built from pipeline/words/ so the site cannot drift from the tested texts.

Draft languages (2026-11-13, night): Hindi, Bengali, Spanish, French and Swahili, machine-translated by SI from the
English in pipeline/words/drafts/<lang>.json. They sit beside "en" and "ne" in each text node; English and Nepali are
unchanged. Verbatim quotations (the crop explainers' sources, the glossary's basis) stay in their original English.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from pipeline.export import build_words as bw
from pipeline.words.texts import MAX_WORDS_GLOSSARY, MAX_WORDS_SCREEN, placeholders, sentences, word_count

REPO = Path(__file__).resolve().parents[1]
DRAFT_LANGS = ("hi", "bn", "es", "fr", "sw")
DRAFT_STATUS = "machine-translated (SI), needs native-speaker review"
DANDA_LANGS = {"hi", "bn"}                     # sentences end with the danda, like Nepali
BS_MONTHS = ("माघ", "फागुन", "चैत", "बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज", "कात्तिक", "मंसिर", "पुस")


def _source(name):
    return json.loads((REPO / "pipeline" / "words" / f"{name}.json").read_text())


def _draft(lang):
    return json.loads((REPO / "pipeline" / "words" / "drafts" / f"{lang}.json").read_text())


def _strip_drafts(obj):
    """The published blocks without the draft-language keys: what English and Nepali looked like before."""
    obj = copy.deepcopy(obj)
    def walk(o):
        if isinstance(o, dict):
            for lang in DRAFT_LANGS:
                o.pop(lang, None)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return obj


def _split(text, lang):
    return sentences(text, "ne" if lang in DANDA_LANGS else "en")


# ---------- English and Nepali: unchanged ----------

def test_words_hold_the_screens_the_shared_words_the_glossary_the_explainers_and_the_languages():
    w = bw.build_words()
    assert set(w) == {"about", "screens", "shared", "glossary", "crop_explainers", "languages"}
    assert len(w["screens"]) == 10 and "crop_names" in w["shared"] and "months" in w["shared"]
    assert w["about"]["nepali_review"] in ("needs native-speaker review", "reviewed")


def test_words_are_the_tested_source_texts_unchanged():
    """English and Nepali are exactly the tested sources; the drafts only add keys beside them."""
    w = bw.build_words()
    src = _source("screens")
    assert _strip_drafts(w["screens"]) == src["screens"] and _strip_drafts(w["shared"]) == src["shared"]
    assert _strip_drafts(w["glossary"]) == _source("glossary")["terms"]
    assert _strip_drafts(w["crop_explainers"]) == _source("crop_explainers")["explainers"]


def test_the_published_file_is_up_to_date():
    """Fails when pipeline/words/ changed and `python -m pipeline.export.build_words` was not rerun."""
    path = REPO / "site" / "data" / "words.json"
    assert path.exists(), "run: python -m pipeline.export.build_words"
    assert json.loads(path.read_text()) == bw.build_words()


def test_every_nepali_text_still_says_whether_a_person_has_reviewed_it():
    w = bw.build_words()
    text = json.dumps(w, ensure_ascii=False)
    assert text.count('"ne_review"') > 100          # owner's answer 15: the mark stays until the owner says done


def test_the_validator_checks_the_words_file():
    from pipeline.export.validate import words_problems
    assert words_problems(bw.build_words()) == []
    broken = bw.build_words()
    del broken["glossary"]
    assert words_problems(broken) != [] and words_problems({"screens": []}) != []


# ---------- the draft languages ----------

def test_text_keys_are_unique_and_cover_every_english_text():
    keys = list(bw.iter_texts(bw.source_blocks()))
    assert len(keys) == len({k for k, _ in keys}) > 250
    assert "screens.home.texts.tagline" in dict(keys) and "crop_explainers.cover.claims.0" in dict(keys)


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_every_draft_has_every_key_of_the_english_source(lang):
    """Same keys as the English; each entry records the English it translates, so a changed English text shows up
    here as stale (re-translate it) instead of being published with an old meaning."""
    english = bw.text_keys()
    texts = _draft(lang)["texts"]
    assert set(texts) == set(english), (f"missing: {sorted(set(english) - set(texts))}; "
                                        f"extra: {sorted(set(texts) - set(english))}")
    stale = [k for k, e in texts.items() if e["en"] != english[k]]
    assert not stale, f"English changed since translation: {stale}"
    assert all(str(e[lang]).strip() for e in texts.values())


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_draft_placeholders_and_numbers_match_the_english(lang):
    for key, e in _draft(lang)["texts"].items():
        assert placeholders(e[lang]) == placeholders(e["en"]), key
        digits = lambda s: sorted(re.findall(r"\d+", re.sub(r"\{[a-z0-9_]+\}", "", s)))
        assert digits(e[lang]) == digits(e["en"]), f"{key}: numbers stay as the same digits"


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_draft_screen_sentences_have_eight_words_or_fewer(lang):
    long = []
    for key, e in _draft(lang)["texts"].items():
        if key.startswith("glossary."):
            continue
        long += [(key, s) for s in _split(e[lang], lang) if word_count(s) > MAX_WORDS_SCREEN]
    assert not long, "\n".join(f"{k}: {word_count(s)} words: {s}" for k, s in long)


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_draft_glossary_meanings_are_one_short_sentence(lang):
    for key, e in _draft(lang)["texts"].items():
        if key.startswith("glossary.") and key.endswith(".say"):
            said = _split(e[lang], lang)
            assert len(said) == 1 and word_count(said[0]) <= MAX_WORDS_GLOSSARY, (key, e[lang])


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_draft_months_are_gregorian(lang):
    """Bikram Sambat months stay Nepali only."""
    for key, e in _draft(lang)["texts"].items():
        assert not any(m in e[lang] for m in BS_MONTHS), key
    if lang in DANDA_LANGS:
        for key, e in _draft(lang)["texts"].items():
            static = re.sub(r"\{[a-z0-9_]+\}", "", e[lang])
            assert "." not in static, f"{key}: full stop in {lang} (use the danda): {e[lang]!r}"


@pytest.mark.parametrize("lang", DRAFT_LANGS)
def test_every_draft_language_is_flagged_and_labelled(lang):
    meta = _draft(lang)["language"]
    entry = {x["code"]: x for x in bw.build_words()["languages"]}[lang]
    for m in (meta, entry):
        assert m["draft"] is True and m["status"] == DRAFT_STATUS
        assert m["label"]["en"] == "Draft translation" and str(m["label"][lang]).strip()
        assert m["quote_label"]["en"] == "Quotation in the original English" and str(m["quote_label"][lang]).strip()
        assert str(m["name"]).strip() and str(m["name_en"]).strip()
    assert entry["missing"] == []


def test_english_and_nepali_are_listed_first_and_are_not_drafts():
    langs = bw.build_words()["languages"]
    assert [x["code"] for x in langs] == ["ne", "en", *DRAFT_LANGS]
    assert langs[0]["draft"] is False and langs[1]["draft"] is False


def test_every_published_text_carries_every_draft_language():
    w = bw.build_words()
    for key, node in bw.iter_texts({k: w[k] for k in ("screens", "shared", "glossary", "crop_explainers")}):
        for lang in DRAFT_LANGS:
            assert str(node.get(lang, "")).strip(), f"{key}: no {lang}"


def test_the_quotes_stay_in_english():
    """Verbatim quotations (crop explainers' sources: 21 quotes, 18 from FAO; the glossary's basis) are never
    translated, so no adaptation of a licensed text (e.g. CC BY-NC-SA 3.0 IGO) is published."""
    w = bw.build_words()
    src = _source("crop_explainers")["explainers"]
    quotes = {}
    for k, e in src.items():
        for i, claim in enumerate(e["claims"]):
            quotes[f"crop_explainers.{k}.claims.{i}"] = claim["source"]
            assert w["crop_explainers"][k]["claims"][i]["source"] == claim["source"]     # published as it is
    assert len(quotes) == 21 and sum(s["publisher"] == "FAO" for s in quotes.values()) == 18
    basis = {t["id"]: t["basis"] for t in _source("glossary")["terms"]}
    assert {t["id"]: t["basis"] for t in w["glossary"]} == basis
    for lang in DRAFT_LANGS:
        texts = _draft(lang)["texts"]
        for key, source in quotes.items():
            q = texts[key]["quote"]
            assert q["text"] == source["quote"] and q["lang"] == "en" and q["translated"] is False, (lang, key)
            assert source["publisher"] in q["source"] and source["url"] in q["source"], (lang, key)
        quoted = [k for k, e in texts.items() if "quote" in e]
        assert sorted(quoted) == sorted(quotes), lang
        assert not any(lang in claim["source"] for e in w["crop_explainers"].values() for claim in e["claims"])
