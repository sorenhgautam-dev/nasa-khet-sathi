"""The launch files in site/data (owner's launch brief, 2026-11-14): probe_log.json, version.json and basemap/*.json
are checked by `python -m pipeline.export.validate`, and scripts/check_site.py accepts them (and the self-hosted fonts).
Everything is built in tmp_path from the mock field; the real site/data is only read."""
import copy
import json
import shutil
from pathlib import Path

import pytest

from pipeline.export import validate as v
from pipeline.export.mock import build_field, build_index
from scripts import check_site as cs

REPO = Path(__file__).resolve().parents[1]
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100

VERSION = {"commit": "8c7acbc" + "0" * 33, "commit_short": "8c7acbc", "commit_date": "2026-11-14",
           "checked_on": "2026-11-15", "uncommitted_changes": False, "made_by": "scripts/final_check.py"}


def _line(t, m, phase):
    return {"time": f"2026-11-16T10:{t:02d}:00+05:45", "moisture": m, "temp": 18.0, "phase": phase}


def _part(sec="s1", minute=1):
    return {"section": sec, "time": f"2026-11-16T10:{minute + 1:02d}:00+05:45", "state": "done", "steady": True,
            "off_scale": False, "wetness": 45, "spread_pct": 1.0, "n": 10, "temp": 18.0, "water_pct": None,
            "give_or_take_pct": None, "band": None, "relative": None, "before": None, "after": None,
            "lines": [_line(minute, 45.0, "settle")] * 20 + [_line(minute, 45.0, "measure")] * 10}


PROBE_LOG = {"field": "demo", "note": "Recorded on 16 November 2026. x", "built": "2026-11-16T12:00:00+05:45",
             "recorded_on": ["2026-11-16"], "place": "the demo field", "twin_date": None, "bench": None, "skipped": [],
             "sessions": [{"id": "r", "source": "serial:COM3", "start": "2026-11-16T10:02:00+05:45",
                           "end": "2026-11-16T10:04:00+05:45", "parts": [_part("s1", 1), _part("s2", 3)]}]}


def _basemap(fid="demo"):
    world = fid == "world"
    return {"id": fid, "image": f"data/basemap/{'world' if world else 'demo'}.jpg",
            "bounds": [[-85.05, -180.0], [85.05, 180.0]] if world else [[27.625034, 85.379227], [27.714966, 85.480773]],
            "crs": "EPSG:3857", "size_px": [296, 296], "native_zoom": 12, "layer": "HLS_L30_Nadir_BRDF_Adjusted_Reflectance",
            "product": "HLS", "date": "2025-11-11", "resolution": "30 m", "attribution": "NASA HLS, via NASA GIBS",
            "chosen_by": "rule", "source": "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi"}


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    (d / "fields").mkdir(parents=True)
    (d / "basemap").mkdir()
    (d / "index.json").write_text(json.dumps(build_index()))
    (d / "fields" / "demo.json").write_text(json.dumps(build_field()))
    (d / "probe_log.json").write_text(json.dumps(PROBE_LOG))
    (d / "version.json").write_text(json.dumps(VERSION))
    for fid in ("demo", "world"):
        (d / "basemap" / f"{fid}.json").write_text(json.dumps(_basemap(fid)))
        (d / "basemap" / f"{fid}.jpg").write_bytes(JPEG)
    return d


def _fails(capsys, data_dir, *extra):
    code = v.main(["--data-dir", str(data_dir), *extra])
    return code, capsys.readouterr().out


def test_the_launch_files_validate(capsys, data_dir):
    code, out = _fails(capsys, data_dir)
    assert code == 0, out


@pytest.mark.parametrize("change, words", [
    (lambda d: d.update(recorded_on=["2026-11-17"]), "recorded_on"),
    (lambda d: d.update(field="nowhere"), "not listed in index.json"),
    (lambda d: d["sessions"][0]["parts"][0].update(section="s99"), "s99"),
    (lambda d: d["sessions"][0].update(source="fake_probe"), "serial"),
    (lambda d: d["sessions"][0]["parts"][0]["lines"].pop(), "measure"),
    (lambda d: d["sessions"][0]["parts"][0]["lines"].__setitem__(-1, _line(30, 45.0, "measure")), "after the part"),
])
def test_a_wrong_probe_log_is_refused(capsys, data_dir, change, words):
    doc = copy.deepcopy(PROBE_LOG)
    change(doc)
    (data_dir / "probe_log.json").write_text(json.dumps(doc))
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "probe_log.json" in out and words in out, out


def test_no_probe_log_is_fine_the_site_says_not_ready_yet(capsys, data_dir):
    (data_dir / "probe_log.json").unlink()
    code, out = _fails(capsys, data_dir)
    assert code == 0, out


@pytest.mark.parametrize("change, words", [
    (lambda d: d.update(commit="xyz"), "commit"),
    (lambda d: d.update(commit_short="1234567"), "commit_short"),
    (lambda d: d.update(checked_on="15 Nov"), "checked_on"),
])
def test_a_wrong_version_stamp_is_refused(capsys, data_dir, change, words):
    doc = dict(VERSION)
    change(doc)
    (data_dir / "version.json").write_text(json.dumps(doc))
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "version.json" in out and words in out, out


def test_a_basemap_needs_its_picture_small_and_around_its_field(capsys, data_dir):
    (data_dir / "basemap" / "demo.jpg").write_bytes(b"\x89PNG" + b"\x00" * 10)
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "not a JPEG" in out
    (data_dir / "basemap" / "demo.jpg").write_bytes(JPEG + b"\x00" * 300_001)
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "300 KB" in out
    (data_dir / "basemap" / "demo.jpg").write_bytes(JPEG)
    far = _basemap()
    far["bounds"] = [[-18.85, 47.40], [-18.81, 47.44]]
    (data_dir / "basemap" / "demo.json").write_text(json.dumps(far))
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "outside" in out
    (data_dir / "basemap" / "nowhere.json").write_text(json.dumps(_basemap("nowhere")))
    (data_dir / "basemap" / "demo.json").write_text(json.dumps(_basemap()))
    code, out = _fails(capsys, data_dir)
    assert code == 1 and "nowhere" in out and "not listed" in out


def test_the_final_check_wants_a_basemap_for_every_field_and_the_world(capsys, data_dir):
    (data_dir / "basemap" / "world.json").unlink()
    code, out = _fails(capsys, data_dir, "--final")
    assert code == 1 and "world.json" in out and "pipeline.fetch.basemap" in out


def test_the_real_launch_files_validate():
    d = REPO / "site" / "data"
    index = json.loads((d / "index.json").read_text())
    problems = v.launch_problems(d, index, final=False)
    assert problems == {}, problems


def test_check_site_accepts_the_fonts_basemaps_and_launch_files(tmp_path):
    site = tmp_path / "site"
    (site / "data" / "basemap").mkdir(parents=True)
    (site / "fonts").mkdir()
    (site / "index.html").write_text('<!doctype html><link rel="stylesheet" href="css/app.css">')
    (site / "data" / "probe_log.json").write_text(json.dumps(PROBE_LOG))
    (site / "data" / "version.json").write_text(json.dumps(VERSION))
    (site / "data" / "basemap" / "demo.json").write_text(json.dumps(_basemap()))
    (site / "data" / "basemap" / "demo.jpg").write_bytes(JPEG)
    (site / "fonts" / "inter-latin-var.woff2").write_bytes(b"wOF2" + b"\x00" * 10)
    (site / "fonts" / "OFL-Inter.txt").write_text("SIL Open Font License")
    (site / "fonts" / "fonts.css").write_text("@font-face{font-family:Inter;src:url(inter-latin-var.woff2) format('woff2')}")
    assert cs.site_problems(site, final=True) == []


def test_every_self_hosted_font_has_its_licence_beside_it():
    fonts = REPO / "site" / "fonts"
    woff2 = sorted(fonts.glob("*.woff2"))
    assert woff2, "site/fonts/ holds the woff2 files"
    for f in woff2:
        family = {"inter-tight": "InterTight", "inter": "Inter", "mukta": "Mukta"}
        key = next(k for k in family if f.name.startswith(k + "-"))
        lic = fonts / f"OFL-{family[key]}.txt"
        assert lic.exists() and "SIL OPEN FONT LICENSE" in lic.read_text().upper()
        assert f.read_bytes()[:4] == b"wOF2" and f.stat().st_size < 80_000
