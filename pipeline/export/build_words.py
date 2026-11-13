"""Publish the site's words: site/data/words.json (owner's answer 16 to REVIEW_2, 2026-11-13).

    .venv/bin/python -m pipeline.export.build_words

The ten screens' texts, the shared words (buttons, crop names, months, source kinds, joining words), the glossary
and the crop explainers, exactly as they stand in pipeline/words/ (the files the tests check: eight-word sentences,
no science words, English and Nepali side by side). The site reads this one file; nobody retypes a text.
The plans' tabs and tips are not here: they are filled from the numbers and travel inside each field file.
Every Nepali text keeps its `ne_review` mark until a person has reviewed it (golden rule: a person reviews every
text; owner's answer 15).

Draft languages (2026-11-13, night): Hindi (hi), Bengali (bn), Spanish (es), French (fr) and Swahili (sw), machine-
translated by SI from the English, in pipeline/words/drafts/<lang>.json. Each draft text is added beside "en" and "ne"
in its node; English and Nepali are unchanged. A draft entry is used only while the English it was translated from is
still the English of that node; otherwise the node gets no text in that language (the site shows the English) and the
key is listed in the language's "missing". `languages` lists every language, Nepali first, with the draft flag, the
status and the label the site shows beside a draft language's name. Verbatim quotations (the crop explainers'
sources, the glossary's basis) are never translated: they stay in the original English.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORDS = REPO / "pipeline" / "words"
DRAFTS = WORDS / "drafts"
DRAFT_LANGS = ("hi", "bn", "es", "fr", "sw")
NE_PENDING = "needs native-speaker review"


def _load(name):
    return json.loads((WORDS / f"{name}.json").read_text())


def _load_draft(lang):
    return json.loads((DRAFTS / f"{lang}.json").read_text())


def source_blocks():
    """The four published blocks, freshly read from pipeline/words/ (safe to change)."""
    screens, glossary, explainers = _load("screens"), _load("glossary"), _load("crop_explainers")
    return {"screens": screens["screens"], "shared": screens["shared"], "glossary": glossary["terms"],
            "crop_explainers": explainers["explainers"]}


def iter_texts(obj, path=""):
    """Yield (key, node) for every text node (an object with an English string). The key names list items by their
    id where they have one, else by position: 'screens.home.texts.tagline', 'shared.months.Jan',
    'glossary.ndvi.say', 'crop_explainers.cover.claims.0'."""
    if isinstance(obj, dict):
        if isinstance(obj.get("en"), str):
            yield path, obj
            return
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                yield from iter_texts(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            seg = v["id"] if isinstance(v, dict) and "id" in v else str(i)
            yield from iter_texts(v, f"{path}.{seg}")


def text_keys():
    """{key: English text} for every text the drafts must translate."""
    return {k: n["en"] for k, n in iter_texts(source_blocks())}


def build_words():
    blocks = source_blocks()
    pending = NE_PENDING in json.dumps(blocks, ensure_ascii=False)
    languages = [
        {"code": "ne", "name": "नेपाली", "name_en": "Nepali", "draft": False,
         "status": NE_PENDING if pending else "reviewed"},
        {"code": "en", "name": "English", "name_en": "English", "draft": False, "status": "source text"},
    ]
    nodes = list(iter_texts(blocks))
    for lang in DRAFT_LANGS:
        draft = _load_draft(lang)
        texts, missing = draft["texts"], []
        for key, node in nodes:
            entry = texts.get(key) or {}
            if entry.get("en") == node["en"] and str(entry.get(lang, "")).strip():
                node[lang] = entry[lang]
            else:
                missing.append(key)
        meta = draft["language"]
        languages.append({"code": lang, "name": meta["name"], "name_en": meta["name_en"], "draft": True,
                          "status": meta["status"], "label": meta["label"], "quote_label": meta["quote_label"],
                          "missing": missing})
    return {
        "about": {"what": "Every word on the screens, in English (en) and Nepali (ne), with draft machine translations "
                          "beside them (see 'languages'). Built from pipeline/words/ by "
                          "pipeline/export/build_words.py; do not edit by hand.",
                  "nepali_review": NE_PENDING if pending else "reviewed",
                  "placeholders": "Texts may hold {names} in braces: fill them from the field file (the same names in "
                                  "both languages; Nepali digits are Devanagari).",
                  "drafts": "hi, bn, es, fr and sw are machine-translated (SI) from the English and need native-speaker "
                            "review: show each language's 'label' beside its name whenever it is chosen. A node without "
                            "a text in that language (listed in 'missing') shows the English. Numbers are ASCII digits; "
                            "fill placeholders as they are, names from shared.crop_names and shared.months in the same "
                            "language. Months are Gregorian (Bikram Sambat is Nepali only). The crop explainers' source "
                            "quotes and the glossary's basis stay in the original English: show them with "
                            "'quote_label', never translated."},
        **blocks,
        "languages": languages,
    }


def main(argv=None):
    dest = Path(argv[0]) if argv else REPO / "site" / "data" / "words.json"
    dest.write_text(json.dumps(build_words(), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
