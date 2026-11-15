"""Owner, 2026-11-15 (afternoon): 'Make the app really, really simple for someone who has never used an app.' Keep the
design and every result; change only how much each screen says and shows. Rules for every farmer screen: one question
and one answer, the rest behind one tap ('More'); one big main button, always in the same place, saying what happens next,
secondary actions as small links; symbols before words (a tick, '=' and a cross, each with a word for screen readers); the
main line 6 words or fewer, other lines 8 or fewer; no numbers unless they help a decision; the 24-year sheet: one big
line, one row of symbols, 'Tap a square to see the year', nothing else."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "site" / "js" / "app.js").read_text()
FEATS = (REPO / "site" / "js" / "features.js").read_text()
CSS = (REPO / "site" / "css" / "app.css").read_text()
WORDS = json.loads((REPO / "site" / "data" / "words.json").read_text())
FARMER = ["home", "photo", "parts", "soil", "today", "next", "weather"]


def _screen(name):
    m = re.search(r"\n  SCREENS\." + name + r" = function.*?\n  \};\n", APP, re.S)
    assert m, name
    return m.group(0)


def _fn(name, src=APP):
    m = re.search(r"\n  function " + name + r"\(.*?\n  \}\n", src, re.S)
    assert m, f"function {name}"
    return m.group(0)


def _w(key):
    node = WORDS["shared"]
    for k in key.split("."):
        node = node[k]
    return node


def test_the_compare_rule_in_the_site_is_the_one_in_rules_yaml():
    rules = yaml.safe_load((REPO / "config" / "rules.yaml").read_text())
    def find(o):
        if isinstance(o, dict):
            v = o.get("value")
            if isinstance(v, dict) and "better_by" in v and "worse_by" in v:
                return v
            for x in o.values():
                r = find(x)
                if r:
                    return r
        return None
    v = find(rules)
    m = re.search(r"var COMPARE = \{ better_by: (\d+), worse_by: (\d+) \}", APP)
    assert m and (int(m.group(1)), int(m.group(2))) == (v["better_by"], v["worse_by"])


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
@pytest.mark.parametrize("fid", ["kharipati", "demo", "sample-1", "sample-2", "sample-3", "sample-4"])
def test_the_24_squares_add_up_to_the_counts_the_back_end_gave_every_answer(fid):
    """yearMarks rebuilds each past season's mark (better, same, worse) from replay/<id>.json; for every winter crop
    answer, window, soil start and plan, its counts equal plan_words' counts (pipeline/export/build_simple.py)."""
    sd = json.loads((REPO / "site" / "data" / "simple" / f"{fid}.json").read_text())
    rep = json.loads((REPO / "site" / "data" / "replay" / f"{fid}.json").read_text())
    compare = re.search(r"\n  var COMPARE = .*?;\n", APP).group(0)
    js = compare + _fn("ownReplayId") + _fn("yearMarks") + f"""
var sd = {json.dumps(sd)}, rep = {json.dumps(rep)}, bad = [], n = 0;
Object.keys(sd.plan_words).forEach(function (crop) {{ Object.keys(sd.plan_words[crop]).forEach(function (w) {{
  Object.keys(sd.plan_words[crop][w]).forEach(function (st) {{ var row = sd.plan_words[crop][w][st];
    Object.keys(row).forEach(function (pid) {{ if (row[pid].now) return; n++;
      var c = {{better: 0, same: 0, worse: 0}}; yearMarks(rep, crop, pid, w, st).forEach(function (m) {{ c[m.kind]++; }});
      if (JSON.stringify(c) !== JSON.stringify(row[pid].counts)) bad.push([crop, w, st, pid, c, row[pid].counts]);
    }}); }}); }}); }});
console.log(JSON.stringify({{n: n, bad: bad}}));"""
    r = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert r["n"] > 0 and r["bad"] == []


def test_the_24_year_sheet_is_one_line_one_row_and_the_tap_line():
    body = _fn("openYears")
    assert "T('farm.years_line'" in body and "T('farm.years_tap')" in body and "class: 'yrow'" in body
    for extra in ("lines(", "nasaTags(", "noteBox(", "moreBox(", "srcs(", "btn2(", "btn3(", "cta("):
        assert extra not in body, extra                                   # nothing else
    assert "'aria-label'" in body                                         # each square says its year and its word
    assert "{crop}" in _w("farm.years_line")["en"] and "{count}" in _w("farm.years_line")["ne"]


def test_symbols_come_with_a_word_for_screen_readers():
    body = _fn("symEl")
    assert "'aria-hidden': 'true'" in body and "class: 'sr'" in body
    assert re.search(r"\.sr \{[^}]*clip", CSS)
    for k in ("better", "same", "worse"):
        assert _w("farm.sym_" + k)["en"] and _w("farm.sym_" + k)["ne"]
    assert ("✓" in APP or "\\u2713" in APP) and ("✗" in APP or "\\u2717" in APP)
    assert "symEl(" in _fn("wordLine")


def test_one_big_main_button_per_farmer_screen_in_the_same_place():
    for name in FARMER:
        body = _screen(name)
        ctas = re.findall(r"\bcta: ([^\n]*)", body)
        assert ctas, name
        for c in ctas:
            assert "btn2(" not in c and "roundBtn(" not in c and "ctapair" not in c, (name, c)   # secondary: small links
    assert re.search(r"\.s-cta \{[^}]*position: sticky[^}]*bottom", CSS)   # always at the bottom of the screen
    assert re.search(r"\.lnk \{", CSS)


def test_more_holds_the_rest_on_the_busy_screens():
    for name in ("home", "photo", "soil", "next", "weather"):
        assert "moreBox(" in _screen(name), name
    assert "moreBox(" in _fn("openPlan") and "K.moreBox(" in FEATS


def test_main_lines_6_words_and_new_lines_8_words_or_fewer():
    titles = [("home.hero_1", "home.hero_2"), ("where.sky_h1", "where.sky_h2"), ("check_soil.h1", "check_soil.h2"),
              ("each_part.today_h1", "each_part.today_h2"), ("what_to_grow.next_h1", "what_to_grow.next_h2"),
              ("what_to_grow.next_h1", "what_to_grow.next_h2_6"), ("check_soil.choose_h1", "check_soil.choose_h2")]
    scr = {s["id"]: {t["id"]: t for t in s["texts"]} for s in json.loads((REPO / "pipeline" / "words" / "screens.json").read_text())["screens"]}
    for a, b in titles:
        sa, ka = a.split("."); sb, kb = b.split(".")
        en = scr[sa][ka]["en"] + " " + scr[sb][kb]["en"]
        assert len(en.split()) <= 6, en
    for k in ("more", "sym_better", "sym_same", "sym_worse", "years_line", "years_tap", "untested_all", "next_parts"):
        w = _w("farm." + k)
        for lang in ("en", "ne"):
            for s in re.split(r"[.।?!]\s*", w[lang]):
                assert len(s.split()) <= 8, (k, lang, s)
        assert not re.search(r"\d", re.sub(r"\{\w+\}", "", w["en"])), k   # no number typed into a farmer's words
