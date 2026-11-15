"""The B list (owner, 2026-11-15): Next 3 months and Next 6 months differ (monthSteps: what happens on the plan in each month),
and Weather ahead joins months that say the same thing (joinBlocks). Pure functions of site/js/app.js, run in node."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP = (Path(__file__).resolve().parents[1] / "site" / "js" / "app.js").read_text()
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def _fn(name):
    m = re.search(rf"  function {name}\(.*?\n", APP)
    assert m, f"{name}() is in app.js"
    start = m.start()
    depth, i = 0, APP.index("{", start)
    while True:                                   # the function's whole body, braces balanced
        depth += {"{": 1, "}": -1}.get(APP[i], 0)
        if depth == 0:
            return APP[start:i + 1]
        i += 1


def _run(expr, names):
    pre = re.search(r"  var MONTHS = \[.*?\];", APP).group(0) + "\n" + re.search(r"  var CUM = \[.*?\];", APP).group(0).split(", MDAYS")[0] + ";\n"
    js = pre + "\n".join(_fn(n) for n in names) + f"\nconsole.log(JSON.stringify({expr}));"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)


WHEAT = {"crops": [{"crop": "rice", "start": "06-15", "end": "10-30"}, {"crop": "wheat", "start": "11-10", "end": "03-31"}]}
ACTS = [{"text": "farm.act_sow_usual", "fill": {"crop": "wheat", "sow_month": "Oct"}},
        {"text": "farm.act_harvest_usual", "fill": {"crop": "wheat", "harvest_month": "Mar"}},
        {"text": "farm.act_then_plant_usual", "fill": {"new_crop": "rice", "sow_month": "Jun"}}]


def test_month_steps_name_what_happens_each_month():
    names = ["doy", "covers", "cropOn", "actMonth", "actKind", "monthSteps"]
    steps = _run(f"monthSteps({json.dumps(WHEAT)}, {json.dumps(ACTS)}, ['Oct', 'Nov', 'Feb', 'Mar', 'Apr', 'Jun'])", names)
    assert [(s["key"], s["kind"], s["crop"]) for s in steps] == [
        ("Oct", "sow", "wheat"), ("Nov", "grow", "wheat"), ("Feb", "grow", "wheat"), ("Mar", "harvest", "wheat"),
        ("Apr", "rest", None), ("Jun", "plant", "rice")]
    assert [len(s["acts"]) for s in steps] == [1, 0, 0, 1, 0, 1]      # each action is shown in its own month only


def test_weather_months_that_say_the_same_thing_are_joined():
    def wx(month, rain, temp, danger, tip):
        return {"usual": {"text": "farm.wx_usual", "fill": {"month": month, "rain_word": rain, "temp_word": temp}},
                "danger": {"text": danger}, "tip": {"text": tip} if tip else None}
    wl = {"Nov": wx("Nov", "dry", "cold", "farm.wx_hurt_potato_cold", "weather.tip_cold"),
          "Dec": wx("Dec", "dry", "cold", "farm.wx_hurt_potato_cold", "weather.tip_cold"),
          "Jan": wx("Jan", "dry", "cold", "farm.wx_hurt_potato_cold", "weather.tip_cold"),
          "Feb": wx("Feb", "some_rain", "cold", "farm.wx_calm", None),
          "Mar": wx("Mar", "some_rain", "mild", "farm.wx_calm", None),
          "Apr": wx("Apr", "some_rain", "mild", "farm.wx_calm", None)}
    groups = _run(f"joinBlocks(['Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'], {json.dumps(wl)})", ["sameWx", "joinBlocks"])
    assert [g["keys"] for g in groups] == [["Nov", "Dec", "Jan"], ["Feb"], ["Mar", "Apr"]]
    assert groups[0]["x"]["usual"]["fill"]["month"] == "Nov"            # the card keeps its first month's lines
