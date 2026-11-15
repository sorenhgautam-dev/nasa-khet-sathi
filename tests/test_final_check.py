"""scripts/final_check.py, the one command before the final push (owner's launch brief, 2026-11-14). The real test
suite, git and the network are never run from here: the steps take a fake runner, and the live comparison runs against a
local server in a temporary folder."""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pipeline.export.validate import load_schema
from scripts import final_check as fc

HEAD = "8c7acbc" + "1" * 33


@pytest.fixture(autouse=True)
def _outside_final_check(monkeypatch):
    """final_check runs the suite with KHET_FINAL_CHECK=1; these tests use fake runners, so they clear it."""
    monkeypatch.delenv("KHET_FINAL_CHECK", raising=False)


class Runner:
    """Answers each command like the real tool would; records what was run."""

    def __init__(self, fail=(), dirty=""):
        self.fail, self.dirty, self.calls = set(fail), dirty, []

    def __call__(self, cmd, cwd, env=None):
        self.calls.append(list(cmd))
        joined = " ".join(map(str, cmd))
        if cmd[0] == "git":
            if "rev-parse" in cmd:
                return 0, HEAD + "\n"
            if "log" in cmd:
                return 0, "2026-11-14\n"
            if "status" in cmd:
                return 0, self.dirty
        for key in self.fail:
            if key in joined:
                return 1, f"FAILED tests/test_x.py::test_y - boom\nFAIL site/data/x.json: {key} broke\n"
        return 0, "ok\n"


def _site(tmp_path, app_js="fetch('data/index.json');\n"):
    site = tmp_path / "site"
    (site / "data" / "basemap").mkdir(parents=True)
    (site / "js").mkdir()
    (site / "index.html").write_text('<!doctype html><link rel="stylesheet" href="css/app.css"><a href="https://nasa.gov">NASA</a>')
    (site / "js" / "app.js").write_text(app_js)
    (site / "data" / "index.json").write_text('{"fields": []}')
    (site / "data" / "basemap" / "demo.jpg").write_bytes(b"\xff\xd8\xff" + bytes(range(256)))
    (site / "data" / "live.json").write_text('{"section": "s1"}')            # git-ignored: exists during the demo only
    (site / "data" / ".live.json.tmp").write_text("{}")
    return site


def test_every_check_passes_and_the_stamp_is_written(tmp_path, capsys):
    _site(tmp_path)
    r = Runner()
    assert fc.main([], runner=r, repo=tmp_path, today="2026-11-15") == 0
    out = capsys.readouterr().out
    assert "RESULT: PASS" in out and out.count("PASS ") >= 6
    ran = [" ".join(map(str, c)) for c in r.calls]
    assert any("-m pytest" in c for c in ran) and any("pipeline.export.validate --final" in c for c in ran)
    assert any("scripts/check_site.py --final" in c for c in ran) and any("scripts/scan_history.py" in c for c in ran)
    # the offline list is named from the stamp (scripts/build_offline.py): rebuilt after the stamp, before every check
    off = next(i for i, c in enumerate(ran) if "scripts/build_offline.py" in c)
    assert off < min(i for i, c in enumerate(ran) if "-m pytest" in c or "check_site.py" in c)
    stamp = json.loads((tmp_path / "site" / "data" / "version.json").read_text())
    Draft202012Validator(load_schema("version_schema.json")).validate(stamp)
    assert stamp == {"commit": HEAD, "commit_short": "8c7acbc", "commit_date": "2026-11-14", "checked_on": "2026-11-15",
                     "uncommitted_changes": False, "made_by": "scripts/final_check.py"}


def test_the_stamp_ignores_its_own_change_but_says_when_other_files_are_not_committed(tmp_path):
    _site(tmp_path)
    assert fc.git_stamp(Runner(dirty=" M site/data/version.json\n"), tmp_path, "2026-11-15")["uncommitted_changes"] is False
    assert fc.git_stamp(Runner(dirty=" M site/data/version.json\n?? docs/x.md\n"), tmp_path, "2026-11-15")["uncommitted_changes"]
    # site/sw.js is rebuilt from the stamp (offline list), so it changes with it
    assert fc.git_stamp(Runner(dirty=" M site/data/version.json\n M site/sw.js\n"), tmp_path, "2026-11-15")["uncommitted_changes"] is False


def test_rerunning_on_the_same_day_and_commit_leaves_the_stamp_byte_for_byte(tmp_path):
    _site(tmp_path)
    fc.main([], runner=Runner(), repo=tmp_path, today="2026-11-15")
    p = tmp_path / "site" / "data" / "version.json"
    before = p.read_bytes()
    assert fc.write_stamp(p, fc.git_stamp(Runner(), tmp_path, "2026-11-15")) is False and p.read_bytes() == before


@pytest.mark.parametrize("key", ["pytest", "pipeline.export.validate", "check_site.py", "scan_history.py"])
def test_one_failing_check_fails_the_whole_and_shows_why(tmp_path, capsys, key):
    _site(tmp_path)
    assert fc.main([], runner=Runner(fail=[key]), repo=tmp_path, today="2026-11-15") == 1
    out = capsys.readouterr().out
    assert "RESULT: FAIL" in out and "Do not push" in out
    assert "FAILED tests/test_x.py::test_y" in out or f"{key} broke" in out


@pytest.mark.parametrize("name, text", [
    ("index.html", '<link rel="preconnect" href="https://fonts.googleapis.com">'),
    ("index.html", '<script src="https://cdn.example.org/x.js"></script>'),
    ("index.html", '<img src="//example.org/a.png">'),
    ("js/app.js", "D.head.append(h('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter' }));"),
    ("js/app.js", "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {}).addTo(m);"),
    ("js/app.js", "fetch('https://api.example.org/x')"),
    ("js/app.js", "img.src = 'https://example.org/a.png';"),
    ("js/app.js", "new EventSource('https://example.org/stream')"),
    ("js/app.js", "import x from 'https://cdn.example.org/m.js';"),
    ("css/app.css", "@import url('https://fonts.googleapis.com/css2?family=Inter');"),
    ("css/app.css", ".a { background: url(https://example.org/bg.png); }"),
])
def test_an_outside_request_at_runtime_is_found(tmp_path, name, text):
    site = _site(tmp_path)
    (site / name).parent.mkdir(parents=True, exist_ok=True)
    (site / name).write_text(text + "\n")
    hits = fc.outside_requests(site)
    assert [h["file"] for h in hits] == [name] and hits[0]["line"] == 1


def test_links_namespaces_and_relative_paths_are_not_outside_requests(tmp_path):
    site = _site(tmp_path, app_js=(
        "m.attributionControl.setPrefix('<a href=\"https://leafletjs.com\">Leaflet</a>');\n"
        "var a = h('a', { href: 'https://www.openstreetmap.org/copyright' }, 'OSM');\n"
        "var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');\n"
        "L.imageOverlay('data/basemap/demo.jpg', b).addTo(m); fetch('data/index.json');\n"))
    (site / "css").mkdir()
    (site / "css" / "app.css").write_text(".a{background:url(../img/x.svg)} .b{background:url(\"data:image/svg+xml,"
                                          "%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E\")}\n"
                                          "@font-face{font-family:Inter;src:url(../fonts/inter-latin-var.woff2) format('woff2')}\n")
    assert fc.outside_requests(site) == []


def test_the_real_leaflet_copy_makes_no_outside_request():
    vendor = Path(__file__).resolve().parents[1] / "site" / "vendor"
    assert fc.outside_requests(vendor) == []


def test_an_outside_request_fails_the_final_check(tmp_path, capsys):
    _site(tmp_path, app_js="L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(m);\n")
    assert fc.main([], runner=Runner(), repo=tmp_path, today="2026-11-15") == 1
    assert "tile.openstreetmap.org" in capsys.readouterr().out


def test_the_files_compared_are_what_the_site_publishes(tmp_path):
    site = _site(tmp_path)
    (site / "data" / ".DS_Store").write_bytes(b"x")
    files = fc.site_files(site)
    assert "data/live.json" not in files and "data/.live.json.tmp" not in files and "data/.DS_Store" not in files
    assert {"index.html", "js/app.js", "data/index.json", "data/basemap/demo.jpg"} <= set(files)


@pytest.fixture
def live(tmp_path):
    """A copy of the site served on localhost, standing in for the live address."""
    served = tmp_path / "served"
    site = _site(tmp_path)
    import shutil
    shutil.copytree(site, served)
    handler = partial(SimpleHTTPRequestHandler, directory=str(served))
    handler.log_message = lambda *a, **k: None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield site, served, f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


def test_the_live_site_matches_byte_for_byte(live, capsys):
    site, served, url = live
    res = fc.compare_live(url, site)
    assert res["differs"] == [] and res["missing"] == [] and "data/basemap/demo.jpg" in res["same"]


def test_a_changed_or_missing_live_file_is_named(live):
    site, served, url = live
    (served / "data" / "index.json").write_text('{"fields": [1]}')
    (served / "data" / "basemap" / "demo.jpg").unlink()
    res = fc.compare_live(url, site)
    assert res["differs"] == ["data/index.json"] and res["missing"] == ["data/basemap/demo.jpg"]


def test_with_live_no_new_stamp_is_written_and_the_comparison_decides(live, capsys):
    site, served, url = live
    root = site.parent
    assert fc.main(["--live", url], runner=Runner(), repo=root, today="2026-11-15") == 0
    assert not (site / "data" / "version.json").exists()
    (served / "data" / "index.json").write_text("{}")
    assert fc.main(["--live", url, "--live-only"], runner=Runner(), repo=root, today="2026-11-15") == 1
    out = capsys.readouterr().out
    assert "data/index.json" in out and "RESULT: FAIL" in out


def test_the_test_step_does_not_run_inside_its_own_test_run(tmp_path, capsys, monkeypatch):
    _site(tmp_path)
    monkeypatch.setenv("KHET_FINAL_CHECK", "1")
    r = Runner()
    assert fc.main([], runner=r, repo=tmp_path, today="2026-11-15") == 1        # a check that did not run is no pass
    assert not any("pytest" in " ".join(map(str, c)) for c in r.calls)
    assert "inside final_check" in capsys.readouterr().out
