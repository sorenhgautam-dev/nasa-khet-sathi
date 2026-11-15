"""Offline use (owner, 2026-11-15, Part 2): the web app manifest, the service worker's saved files (scripts/build_offline.py,
site/sw.js) and its guards. The worker never runs on the laptop or its hotspot, never saves live readings, practice
readings or demo-mode data, and removes itself if its file list is wrong."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import build_offline as bo

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
SW = (SITE / "sw.js").read_text()
APP = (SITE / "js" / "app.js").read_text()


def test_a_first_visit_saves_the_whole_web_app_and_nothing_always_fresh():
    """Owner, 2026-11-15 afternoon: 'make the entire webapp offline': a first visit saves every file of the site (every
    field, How we know, Behind the scenes, the world page and its pictures), except sw.js itself and NEVER (the live
    reading, the demo-mode switch and the recorded test readings always come fresh)."""
    main, files = bo.first_visit(SITE)
    assert main == json.loads((SITE / "data" / "index.json").read_text())["fields"][0]["id"]
    every = {p.relative_to(SITE).as_posix() for p in SITE.rglob("*") if p.is_file() and not p.name.startswith(".")}
    assert set(files) == every - set(bo.NEVER) - {"sw.js"}
    for f in ("index.html", "manifest.webmanifest", "js/app.js", "js/world.js", "data/basemap/world.jpg", "data/story.json",
              "data/behind.json", f"data/fields/{main}.json", "data/fields/demo.json", "data/fields/ambohidratrimo.json"):
        assert f in files, f
    assert not set(bo.NEVER) & set(files) and "sw.js" not in files
    assert all((SITE / f).is_file() for f in files)


def test_the_worker_carries_the_current_list_and_a_version_named_from_the_stamp():
    assert bo.check(SITE) == [], "run scripts/build_offline.py"
    stamp = json.loads((SITE / "data" / "version.json").read_text())["commit_short"]
    assert re.search(r"const VERSION = 'ks-" + stamp + r"-[0-9a-f]{10}';", SW)


def test_the_check_finds_a_wrong_list(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(SITE, site)
    (site / "js" / "how.js").unlink()                        # a listed file missing: the list is wrong
    assert any("missing" in p for p in bo.check(site))
    shutil.copytree(SITE, site, dirs_exist_ok=True)
    (site / "img" / "new.svg").write_text("<svg/>")           # a new site file the list does not hold: stale
    assert any("stale" in p for p in bo.check(site))


def test_the_worker_only_handles_same_origin_gets_and_never_saves_the_always_fresh_files():
    assert "r.method !== 'GET'" in SW and "u.origin !== self.location.origin" in SW
    assert "r.cache === 'no-store'" in SW                    # getJSON(path, true): live.json and demo.json
    for f in ("data/live.json", "data/demo.json", "data/probe_log.json"):
        assert f in bo.NEVER


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_never_on_the_laptop_or_its_hotspot():
    cases = {"localhost": True, "127.0.0.1": True, "192.168.1.23": True, "172.20.10.2": True, "10.0.0.5": True,
             "khet-laptop.local": True, "sorenhgautam-dev.github.io": False, "172.32.0.1": False, "example.vercel.app": False}
    m = re.search(r"const LOCAL = (/.*?/i);", SW)
    js = f"const LOCAL = {m.group(1)};\nconsole.log(JSON.stringify({json.dumps(list(cases))}.map(h => LOCAL.test(h))));"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert dict(zip(cases, got)) == cases
    reg = re.search(r"function offline\(\) \{.*?\n  \}", APP, re.S).group(0)
    assert "demoHost(location.hostname)" in reg and "unregister" in reg and "try" in reg
    assert "install" in SW and "unregister()" in SW            # a failed list removes the worker


def test_the_manifest_and_its_icons():
    m = json.loads((SITE / "manifest.webmanifest").read_text())
    assert m["name"] == "Khet Sathi · खेत साथी" and m["start_url"] == "./" and m["scope"] == "./" and m["display"] == "standalone"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes and any(i.get("purpose") == "maskable" for i in m["icons"])
    for i in m["icons"]:
        assert (SITE / i["src"]).is_file() and not i["src"].startswith("/")
    html = (SITE / "index.html").read_text()
    assert 'rel="manifest" href="manifest.webmanifest"' in html and 'rel="apple-touch-icon"' in html


def test_the_offline_line_is_a_word_nepali_first_and_marked():
    w = json.loads((REPO / "pipeline" / "words" / "screens.json").read_text())["shared"]["offline"]["line"]
    assert w["en"] == "Offline: showing your saved field." and w["ne"] and w["ne_review"] == "needs native-speaker review"
    assert "T('offline.line')" in APP
