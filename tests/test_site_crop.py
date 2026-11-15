"""One crop answer on every screen (owner, 2026-11-15, job A): until the farmer answers, every screen uses our guess from
space; after they answer, their answer. The plans (effPlans), "What you do now" (farmPlans' own plan), Next 3 and 6
months (plan_words and actions by winterCrop) and Weather ahead (weather_lines by winterCrop) all take the crop from
winterId / curOption / swapId. Run on the real Kharipati and Bhaktapur files, in node, with the app's own functions."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "site" / "js" / "app.js").read_text()
FEATS = (REPO / "site" / "js" / "features.js").read_text()
NEEDED = ["winterId", "swapId", "curOption", "effPlans", "winterCrop", "farmPlans"]


def _fn(name):
    m = re.search(r"\n  function " + name + r"\(.*?\n  \}\n", APP, re.S)
    assert m, f"app.js function {name}"
    return m.group(0)


def _run(fid, answer):
    """What each screen would show for the field, with the farmer's answer (None: not answered yet)."""
    F = json.loads((REPO / "site" / "data" / "fields" / f"{fid}.json").read_text())
    sd = json.loads((REPO / "site" / "data" / "simple" / f"{fid}.json").read_text())
    order = re.search(r"\n  var VERDICT_ORDER = .*?;\n", APP).group(0)
    js = (f"var S = {{winter: {json.dumps(answer)}}};\n{order}\n" + "".join(_fn(n) for n in NEEDED) + f"""
var F = {json.dumps(F)}, sd = {json.dumps(sd)};
var crop = winterCrop(F, sd), cur = effPlans(F)[0], fp = farmPlans(F, sd, 3, sd.start || 'medium'), fp6 = farmPlans(F, sd, 6, sd.start || 'medium');
var own = fp.own ? fp.own.p.crops.map(function (c) {{ return c.crop; }}) : [];
var wl = sd.weather_lines && sd.weather_lines[crop];
console.log(JSON.stringify({{winterId: winterId(F, S.winter), crop: crop,
  plans_current: cur.crops.map(function (c) {{ return c.crop; }}),
  what_you_do_now: own, what_you_do_now_6: fp6.own ? fp6.own.p.crops.map(function (c) {{ return c.crop; }}) : [],
  suggestion: fp.pick ? fp.pick.p.crops.map(function (c) {{ return c.crop; }}) : [], keep: !!fp.keep,
  weather_warns: wl ? JSON.stringify(wl.no) : ''}}));""")
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
@pytest.mark.parametrize("fid, answer, winter, other", [
    ("kharipati", None, "wheat", "potato"),          # our guess from space: rice then wheat
    ("kharipati", "rice_potato", "potato", "wheat"),  # the farmer's answer wins
    ("kharipati", "rice_wheat", "wheat", "potato"),
    ("demo", None, "potato", "wheat"),                # the demo's guess is rice then potato
    ("demo", "rice_wheat", "wheat", "potato")])
def test_every_screen_uses_the_guess_until_the_farmer_answers_then_their_answer(fid, answer, winter, other):
    r = _run(fid, answer)
    assert r["crop"] == winter                                            # Next 3 and 6 months, Weather ahead
    assert r["plans_current"] == ["rice", winter]                         # the plans: "What you do now"
    assert r["what_you_do_now"] == ["rice", winter] == r["what_you_do_now_6"]
    # a change is never what they do now; when no plan is usually better the card keeps their crop (rules.yaml
    # simple_cards.suggest_change_only_if_better, owner 2026-11-15)
    assert r["suggestion"] != ["rice", winter] or (r["keep"] and r["suggestion"] == ["rice", winter])
    assert winter in r["weather_warns"] and other not in r["weather_warns"]   # the warnings name their crop only


def test_no_screen_reads_the_default_crop_or_the_answer_except_through_the_helpers():
    """co['default'] only in winterId/swapId; S.winter only where the answer is read, set or reset."""
    for m in re.finditer(r"co\['default'\]|co\.default\b", APP):
        start = APP.rfind("\n  function ", 0, m.start())
        assert re.match(r"\n  function (winterId|swapId)\(", APP[start:]), APP[start:start + 60]
    allowed = ("curOption", "effPlans", "winterQuestion", "guessCard", "chooseField", "swapId", "winterId")
    for m in re.finditer(r"S\.winter\b", APP):
        start = APP.rfind("\n  function ", 0, m.start())
        name = re.match(r"\n  function (\w+)", APP[start:]).group(1)
        assert name in allowed or "store.get('winter')" in APP[m.start() - 5:m.start() + 60], name
    assert "S.winter && R.plans" not in FEATS and "K.swapId(F, S.winter)" in FEATS   # the 25-year replay
