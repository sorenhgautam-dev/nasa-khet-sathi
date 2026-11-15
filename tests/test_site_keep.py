"""Suggest a change only when another plan is 'usually better than now' (owner, 2026-11-15 afternoon, answer 3; rules.yaml
simple_cards.suggest_change_only_if_better, committed before this code). When none is, the card says 'Keep growing
[crop].', one line 'None of our other plans usually did better.', no 'Try it in one part first' button, and the other
plans below with their own symbols. Run in node with the app's own functions on the real Kharipati and Bhaktapur files:
our guess (wheat on Kharipati) and the farmer's answer (potato), English and Nepali."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "site" / "js" / "app.js").read_text()
WORDS = json.loads((REPO / "site" / "data" / "words.json").read_text())
NEEDED = ["winterId", "swapId", "curOption", "effPlans", "winterCrop", "farmPlans"]


def _fn(name):
    m = re.search(r"\n  function " + name + r"\(.*?\n  \}\n", APP, re.S)
    assert m, f"app.js function {name}"
    return m.group(0)


def _pick(fid, answer, n):
    F = json.loads((REPO / "site" / "data" / "fields" / f"{fid}.json").read_text())
    sd = json.loads((REPO / "site" / "data" / "simple" / f"{fid}.json").read_text())
    order = re.search(r"\n  var VERDICT_ORDER = .*?;\n", APP).group(0)
    js = (f"var S = {{winter: {json.dumps(answer)}}};\n{order}\n" + "".join(_fn(x) for x in NEEDED) + f"""
var F = {json.dumps(F)}, sd = {json.dumps(sd)};
var s = farmPlans(F, sd, {n}, sd.start || 'medium'), win = '{"m6" if n == 6 else "m3"}';
var pw = sd.plan_words[winterCrop(F, sd)][win][sd.start || 'medium'];
console.log(JSON.stringify({{crop: winterCrop(F, sd), keep: !!s.keep, pick_own: !!(s.pick && s.pick.own),
  pick: s.pick ? s.pick.id : null, others: s.others.map(function (x) {{ return [x.id, pw[x.id].verdict]; }}),
  verdicts: Object.keys(pw).filter(function (k) {{ return !pw[k].now; }}).map(function (k) {{ return [k, pw[k].verdict]; }})}}));""")
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
@pytest.mark.parametrize("n", [3, 6])
@pytest.mark.parametrize("fid, answer, crop", [("kharipati", None, "wheat"), ("kharipati", "rice_potato", "potato"),
                                               ("demo", None, "potato"), ("demo", "rice_wheat", "wheat")])
def test_a_change_is_suggested_only_when_another_plan_is_usually_better(fid, answer, crop, n):
    r = _pick(fid, answer, n)
    assert r["crop"] == crop
    better = [k for k, v in r["verdicts"] if v == "better"]
    if better:                                   # a change: the pick is one of the better plans, never the farmer's own
        assert not r["keep"] and not r["pick_own"] and r["pick"] in better
    else:                                        # keep: the farmer's own plan, and every other plan listed below it
        assert r["keep"] and r["pick_own"]
        assert sorted(k for k, _ in r["others"]) == sorted(k for k, _ in r["verdicts"])


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_our_guess_on_kharipati_keeps_wheat_and_the_answer_potato_suggests_wheat():
    """Kharipati, next 3 months, medium start: for a wheat grower every other plan is usually worse (24 of 24 winters for
    potato), so 'Keep growing wheat.'; for a potato grower wheat is usually better (24 of 24), so the change is suggested."""
    guess = _pick("kharipati", None, 3)
    assert guess["keep"] and all(v != "better" for _, v in guess["verdicts"])
    answer = _pick("kharipati", "rice_potato", 3)
    assert not answer["keep"] and answer["pick"] == "cover_gap"


def test_the_keep_words_in_english_and_nepali():
    farm = WORDS["shared"]["farm"]
    assert farm["keep_growing"]["en"] == "Keep growing {crop}." and "{crop}" in farm["keep_growing"]["ne"]
    assert farm["none_better"]["en"] == "None of our other plans usually did better."
    for k in ("keep_growing", "none_better"):
        assert farm[k]["ne"] and farm[k]["ne_review"] == "needs native-speaker review"
        assert len(farm[k]["en"].split()) <= 8 and len(farm[k]["ne"].split()) <= 8
    assert len(farm["keep_growing"]["en"].split()) <= 6                     # the card's main line


def test_next_3_and_next_6_show_the_keep_card_without_a_trial_button():
    body = re.search(r"\n  function keepCard\(.*?\n  \}\n", APP, re.S).group(0)
    assert "farm.keep_growing" in body and "farm.none_better" in body and "tryBtn" not in body and "symEl(" in body
    nxt = re.search(r"\n  SCREENS\.next = function.*?\n  \};\n", APP, re.S).group(0)
    assert nxt.count("keepCard(") == 2                                        # Next 6 and Next 3
    fp = re.search(r"\n  function farmPlans\(.*?\n  \}\n", APP, re.S).group(0)
    assert "VERDICT_ORDER.better" in fp and "keep:" in fp
