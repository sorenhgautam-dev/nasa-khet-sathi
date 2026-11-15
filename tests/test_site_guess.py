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
    body = re.search(r"function guessCard\(F, box, after\) \{.*?\n  \}", APP, re.S).group(0)
    assert "guessButtons(" in body and "o.id === def" not in body
