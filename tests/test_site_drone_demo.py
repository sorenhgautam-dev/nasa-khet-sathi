"""Phone as drone (owner, 2026-11-15): a demo mode for the in-person demo and the video, on the laptop's hotspot only,
never on the public site. The phone's photo from above stays on the phone; 4 pots stand in for the field's 4 parts; the
fog clears only with real calibrated numbers; the public photo step says when NASA saw the field from space."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import check_site

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
APP = (SITE / "js" / "app.js").read_text()
WORDS = json.loads((SITE / "data" / "words.json").read_text())


def demo_block():
    a, b = APP.index("// ---------------- phone as drone"), APP.index("// ---------------- end of phone as drone")
    return APP[a:b]


def word(group, key):
    return WORDS["shared"][group][key]


def screen_word(screen, key):
    s = next(s for s in WORDS["screens"] if s["id"] == screen)
    return next(t for t in s["texts"] if t["id"] == key)


# ---------- the guard: the laptop's hotspot only, and only with the git-ignored switch ----------

@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_demo_mode_only_on_the_laptop_or_its_hotspot_never_on_the_public_site():
    m = re.search(r"function demoHost\(hn\) \{.*?\n  \}", APP, re.S)
    assert m, "demoHost(hn) is the address half of the guard"
    cases = {"localhost": True, "127.0.0.1": True, "192.168.1.23": True, "172.20.10.2": True, "10.0.0.5": True,
             "khet-laptop.local": True, "sorenhgautam-dev.github.io": False, "172.32.0.1": False, "8.8.8.8": False,
             "example.com": False, "192.168.1.23.github.io": False, "": False}
    js = m.group(0) + "\nconsole.log(JSON.stringify(" + json.dumps(list(cases)) + ".map(demoHost)));"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert dict(zip(cases, got)) == cases


def test_the_switch_file_is_git_ignored_never_tracked_and_refused_by_the_freeze_check(tmp_path):
    ign = subprocess.run(["git", "check-ignore", "-q", "site/data/demo.json"], cwd=REPO)
    assert ign.returncode == 0, ".gitignore must cover site/data/demo.json"
    tracked = subprocess.run(["git", "ls-files", "site/data/demo.json"], cwd=REPO, capture_output=True, text=True).stdout
    assert not tracked.strip()
    (tmp_path / "data").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>")
    (tmp_path / "data" / "demo.json").write_text('{"demo": true}')
    assert any(p["kind"] == "demo switch" for p in check_site.site_problems(tmp_path, final=True))
    assert not check_site.site_problems(tmp_path, final=False)   # allowed on the laptop during the demo


def test_demo_mode_needs_both_the_address_and_the_switch():
    b = demo_block()
    assert "demoHost(location.hostname)" in b and "getJSON('data/demo.json', true)" in b
    assert re.search(r"d\.demo === true", b)
    # the public site never even asks for the switch file: the address test comes first
    assert re.search(r"demoHost\(location\.hostname\)\s*\?\s*getJSON\('data/demo\.json'", b)


def test_the_switch_script_writes_and_removes_only_the_ignored_file():
    src = (REPO / "scripts" / "demo_mode.py").read_text()
    assert "site/data/demo.json" in src or '"site" / "data" / "demo.json"' in src
    assert "check-ignore" in src


# ---------- the photo stays on the phone ----------

def test_the_photo_is_never_uploaded_or_stored():
    b = demo_block()
    assert "capture: 'environment'" in b and "accept: 'image/*'" in b and "URL.createObjectURL" in b
    for bad in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "indexedDB", "FormData",
                "photoDB", "FileReader", "toDataURL", "WebSocket"):
        assert bad not in b, f"the demo block must not use {bad}: the photo stays on the phone, in memory only"


def test_the_photo_screen_shows_the_time_taken_the_grid_and_is_this_your_farm():
    b = demo_block()
    assert "T('drone.taken')" in b and "T('where.is_this')" in b and "T('drone.yes')" in b
    assert "fieldBox(F, " in b and "photo:" in b      # the 2 x 2 grid of the field's own 4 parts, drawn on the photo


# ---------- every demo screen says what it is ----------

def test_every_demo_screen_carries_the_demo_label():
    b = demo_block()
    assert "function demoLabel()" in b and "T('drone.label')" in b
    photo = b[b.index("function demoPhoto("):b.index("function potWord(")]
    assert "demoLabel()" in photo and "if (S.demo) return demoPhoto(F);" in APP
    for scr, nxt in (("parts", "SCREENS.soil"), ("soil", "SCREENS.choose")):
        body = APP[APP.index(f"SCREENS.{scr} = function"):APP.index(nxt + " = function")]
        assert "S.demo ? demoLabel()" in body or "demo ? demoLabel()" in body, scr
    lab = word("drone", "label")
    assert lab["en"] == "Demo: 4 pots stand in for a field. This phone stands in for our drone."
    assert lab["ne"].strip() and "४" in lab["ne"]


def test_every_drone_word_used_is_published_in_english_and_nepali():
    used = set(re.findall(r"T\('drone\.([a-z0-9_]+)'", APP))
    # the two families named in pieces (T('drone.pot_' + w), T('drone.chip_' + w)) by potWord's words
    used = (used - {"pot_", "chip_"}) | {f"pot_{w}" for w in ("wetter", "drier", "same", "none")} \
        | {f"chip_{w}" for w in ("wetter", "drier", "same")}
    have = WORDS["shared"]["drone"]
    assert used and not used - set(have), sorted(used - set(have))
    for k in have:
        assert have[k]["en"].strip() and have[k]["ne"].strip(), k


# ---------- the pots' readings: on the photo, never as the field's parts ----------

def test_demo_readings_never_reach_the_field_parts():
    pdata = APP[APP.index("function probeData()"):APP.index("function anyTested(")]
    assert "demoOn()" in pdata and "!demo" in pdata, "in demo mode probeData ignores live.json (the pots), so Today, " \
                                                    "Choose and How we know never show them as the field's parts"


def test_the_pots_results_come_only_from_the_sticks_relative_words():
    b = demo_block()
    for k in ("pot_wetter", "pot_drier", "pot_same", "pot_none"):
        assert f"'{k[4:]}'" in b or k in b
    assert "relative" in b and "Math.random" not in b


def test_the_fog_on_the_pots_clears_only_with_calibrated_numbers():
    sure = APP[APP.index("function sureOf("):APP.index("function fogOpacity(")]
    assert re.search(r"pd\.demo && !\(r && r\.water_pct != null\)", sure), "a pot's fog clears only with a calibrated reading"


# ---------- the public photo step: when NASA saw the field from space ----------

def test_the_public_photo_step_says_when_nasa_saw_the_field():
    w = screen_word("where", "seen_space")
    assert w["en"] == "Seen from space by NASA on {date}. Next, our drone takes this photo."
    assert "{date}" in w["ne"]
    photo = APP[APP.index("SCREENS.photo = function"):APP.index("SCREENS.parts = function")]
    assert "seenLine(" in photo
    seen = APP[APP.index("function seenLine("):]
    seen = seen[:seen.index("\n  }\n")]
    assert "data/basemap/" in seen and "b.date" in seen and "fmtDate(b.date)" in seen
    assert r"/^\d{4}-\d\d-\d\d$/" in seen, "only a full acquisition date; else the line is left out"
    assert "abroad()" in seen, "abroad fields show only the world picture: no date line"
    demo = json.loads((SITE / "data" / "basemap" / "demo.json").read_text())
    assert re.fullmatch(r"\d{4}-\d\d-\d\d", demo["date"])


# ---------- the square on the camera step, and the corners after it (owner, 2026-11-15) ----------

def test_the_camera_step_shows_the_square_and_its_words():
    b = demo_block()
    assert "function guideBox()" in b and "T('drone.fit_guide')" in b
    assert re.search(r"p \? fieldBox\(F, 'sway', \{ photo: p\.url \}\)\s*: guideBox\(\)", b)    # before the photo: the square
    for k, en in (("fit_guide", "Fit the 4 pots inside the square."), ("fit_drag", "Drag the corners to fit the 4 pots."),
                  ("fit_done", "Done"), ("fit_again", "Fit again")):
        w = word("drone", k)
        assert w["en"] == en and w["ne"].strip() and w["ne_review"] == "needs native-speaker review"


def test_after_the_photo_four_corners_are_dragged_before_the_parts_are_drawn():
    b = demo_block()
    assert "function fitView(raw)" in b and b.count("setPointerCapture") == 1 and "pointercancel" in b
    assert "S.demoRaw = { url: URL.createObjectURL(f), at: new Date(), quad: null }" in b and "S.demoPhoto = null" in b
    assert "if (raw && !p)" in b                                             # a new photo goes to the corners first
    css = (SITE / "css" / "app.css").read_text()
    assert re.search(r"\.fitbox \.fithandle \{[^}]*touch-action: none", css)   # dragging never scrolls the page
    assert ".fieldbox.photo > img.ph { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: fill; }" in css


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_corners_map_the_square_exactly():
    m = re.search(r"function quadMap\(q\) \{.*?\n  \}", APP, re.S)
    assert m, "quadMap(q): the unit square onto the dragged corners"
    js = m.group(0) + """
var q = [[10, 20], [110, 30], [100, 140], [5, 120]], f = quadMap(q), par = quadMap([[0, 0], [4, 0], [6, 2], [2, 2]]);
console.log(JSON.stringify({ corners: [f(0, 0), f(1, 0), f(1, 1), f(0, 1)], mid: par(0.5, 0.5), edge: par(0.5, 0) }));"""
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    for p, want in zip(got["corners"], [[10, 20], [110, 30], [100, 140], [5, 120]]):
        assert p == pytest.approx(want, abs=1e-9)
    assert got["mid"] == pytest.approx([3, 1]) and got["edge"] == pytest.approx([2, 0])   # a parallelogram stays affine


def test_the_straightened_photo_stays_on_the_phone():
    b = demo_block()
    body = b[b.index("function straighten("):]
    assert "getImageData" in body and "toBlob(" in body and "URL.createObjectURL(b)" in body
    assert "URL.revokeObjectURL" in b
