"""The crop question on the photo screen (owner, 2026-11-15): 'Yes' is the option whose crops are our guess, and the other
button names the other rotation, so two buttons never mean the same answer (a rice-then-wheat guess showed 'Yes' and
'Rice, then wheat', and 'Yes' saved rice then potato)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP = (Path(__file__).resolve().parents[1] / "site" / "js" / "app.js").read_text()
CO = {"default": "rice_potato", "options": [{"id": "rice_potato", "crops": [{"crop": "rice"}, {"crop": "potato"}]},
                                            {"id": "rice_wheat", "crops": [{"crop": "rice"}, {"crop": "wheat"}]}]}


def _buttons(guess, co):
    m = re.search(r"function guessButtons\(guess, co\) \{.*?\n  \}", APP, re.S)
    assert m, "guessButtons(guess, co) builds the crop question's buttons"
    js = m.group(0) + f"\nconsole.log(JSON.stringify(guessButtons({json.dumps(guess)}, {json.dumps(co)})));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_yes_is_the_guess_and_the_other_button_is_the_other_rotation():
    wheat = _buttons(["rice", "wheat"], CO)
    assert [(b["id"], b["yes"]) for b in wheat] == [("rice_wheat", True), ("rice_potato", False)]
    potato = _buttons(["rice", "potato"], CO)
    assert [(b["id"], b["yes"]) for b in potato] == [("rice_potato", True), ("rice_wheat", False)]
    other = _buttons(["maize", "wheat"], CO)                       # no option is the guess: every button names its crops
    assert [b["yes"] for b in other] == [False, False]
    assert _buttons(["rice", "wheat"], None) == [{"id": None, "yes": True, "crops": []}]   # no options: one 'Yes'


def test_the_card_uses_it():
    body = re.search(r"function guessCard\(F, box, after(, extra)?\) \{.*?\n  \}", APP, re.S).group(0)
    assert "guessButtons(" in body and "o.id === def" not in body


def _winter(fn, field, answer):
    m = re.search(r"  function winterId\(F, answer\) \{.*?\n  \}\n.*?function swapId\(F, answer\) \{.*?\n", APP, re.S)
    assert m, "winterId(F, answer) and swapId(F, answer) pick what the farmer grows now"
    js = m.group(0) + f"\nconsole.log(JSON.stringify({fn}({json.dumps(field)}, {json.dumps(answer)})));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_one_answer_on_every_screen_our_guess_until_the_farmer_answers():
    """Fix A3 (owner, 2026-11-15): Kharipati's guess from space is rice then wheat while the file's default is rice then
    potato; before any answer every screen used the default, and only the photo screen said 'We think rice, then wheat'."""
    kh = {"diary": {"guess": ["rice", "wheat"]}, "current_options": CO}
    demo = {"diary": {"guess": ["rice", "potato"]}, "current_options": CO}
    assert _winter("winterId", kh, None) == "rice_wheat"            # no answer: our guess
    assert _winter("swapId", kh, None) == "rice_wheat"              # so the 'current' plan becomes rice then wheat
    assert _winter("winterId", kh, "rice_potato") == "rice_potato"  # the farmer's answer wins
    assert _winter("swapId", kh, "rice_potato") == "rice_potato"
    assert _winter("winterId", demo, None) == "rice_potato" and _winter("swapId", demo, None) is None   # the demo: unchanged
    assert _winter("winterId", {"diary": {"guess": ["maize"]}, "current_options": CO}, None) == "rice_potato"   # no match
    assert _winter("winterId", {"diary": {"guess": []}}, None) is None
    feats = (Path(__file__).resolve().parents[1] / "site" / "js" / "features.js").read_text()
    assert "K.swapId(F, S.winter)" in feats and "S.winter && R.plans" not in feats
    assert "opt = co && S.winter ?" not in APP and "S.winter || co['default']" not in APP
