"""Publish the site's words: site/data/words.json (owner's answer 16 to REVIEW_2, 2026-11-13).

    .venv/bin/python -m pipeline.export.build_words

The ten screens' texts, the shared words (buttons, crop names, months, source kinds, joining words), the glossary
and the crop explainers, exactly as they stand in pipeline/words/ (the files the tests check: eight-word sentences,
no science words, English and Nepali side by side). The site reads this one file; nobody retypes a text.
The plans' tabs and tips are not here: they are filled from the numbers and travel inside each field file.
Every Nepali text keeps its `ne_review` mark until a person has reviewed it (golden rule: a person reviews every
text; owner's answer 15).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORDS = REPO / "pipeline" / "words"


def _load(name):
    return json.loads((WORDS / f"{name}.json").read_text())


def build_words():
    screens, glossary, explainers = _load("screens"), _load("glossary"), _load("crop_explainers")
    marks = json.dumps([screens, glossary, explainers], ensure_ascii=False)
    pending = "needs native-speaker review" in marks
    return {
        "about": {"what": "Every word on the screens, in English (en) and Nepali (ne). Built from pipeline/words/ by "
                          "pipeline/export/build_words.py; do not edit by hand.",
                  "nepali_review": "needs native-speaker review" if pending else "reviewed",
                  "placeholders": "Texts may hold {names} in braces: fill them from the field file (the same names in "
                                  "both languages; Nepali digits are Devanagari)."},
        "screens": screens["screens"],
        "shared": screens["shared"],
        "glossary": glossary["terms"],
        "crop_explainers": explainers["explainers"],
    }


def main(argv=None):
    dest = Path(argv[0]) if argv else REPO / "site" / "data" / "words.json"
    dest.write_text(json.dumps(build_words(), indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
