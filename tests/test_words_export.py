"""site/data/words.json (owner's answer 16 to REVIEW_2, 2026-11-13): the screen words, glossary and crop explainers
published for the site, built from pipeline/words/ so the site cannot drift from the tested texts."""
import json
from pathlib import Path

from pipeline.export import build_words as bw

REPO = Path(__file__).resolve().parents[1]


def test_words_hold_the_screens_the_shared_words_the_glossary_and_the_explainers():
    w = bw.build_words()
    assert set(w) == {"about", "screens", "shared", "glossary", "crop_explainers"}
    assert len(w["screens"]) == 10 and "crop_names" in w["shared"] and "months" in w["shared"]
    assert w["about"]["nepali_review"] in ("needs native-speaker review", "reviewed")


def test_words_are_the_tested_source_texts_unchanged():
    w = bw.build_words()
    src = json.loads((REPO / "pipeline" / "words" / "screens.json").read_text())
    assert w["screens"] == src["screens"] and w["shared"] == src["shared"]
    assert w["glossary"] == json.loads((REPO / "pipeline" / "words" / "glossary.json").read_text())["terms"]


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
