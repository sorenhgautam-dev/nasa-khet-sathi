"""Kharipati is the only field the app shows (owner, 2026-11-15 afternoon; rules.yaml site_hidden_fields, committed first).
Hide, don't delete: the demo field, the four sample fields and the Dhulikhel preview leave index.json; their files,
configs and tests stay. A browser that remembered an old field opens Kharipati. No 'Sample field' chip and no blurry
satellite picture on the farmer path. The live soil-stick demo with the pots shows as a demo tray, never as Kharipati's
parts."""
import json
import re
from pathlib import Path

from pipeline.export.build_index import build_index
from pipeline.fetch.rules import load_rules

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "site" / "js" / "app.js").read_text()
HIDDEN = load_rules()["site_hidden_fields"]


def _fn(name):
    m = re.search(r"\n  function " + name + r"\(.*?\n  \}\n", APP, re.S)
    assert m, name
    return m.group(0)


def test_the_index_lists_kharipati_first_then_madagascar_and_hides_the_rest_without_deleting_them():
    idx = json.loads((REPO / "site" / "data" / "index.json").read_text())
    assert [f["id"] for f in idx["fields"]] == ["kharipati", "ambohidratrimo"]
    assert not idx.get("drone_previews") and [a["id"] for a in idx["areas"]] == ["kharipati"]
    for fid in ("demo", "sample-1", "sample-2", "sample-3", "sample-4"):
        assert fid in HIDDEN
        assert (REPO / "site" / "data" / "fields" / f"{fid}.json").exists() and (REPO / "config" / "fields" / f"{fid}.yaml").exists()


def test_build_index_leaves_out_hidden_fields_and_previews(tmp_path):
    (tmp_path / "fields").mkdir()
    (tmp_path / "drone").mkdir()
    cfgs = []
    for fid in ("a", "b"):
        (tmp_path / "fields" / f"{fid}.json").write_text("{}")
        cfgs.append({"id": fid, "name": fid, "country": "Nepal", "lat": 27.7, "lon": 85.4, "bbox": [85.4, 27.6, 85.5, 27.7]})
    (tmp_path / "drone" / "c.json").write_text("{}")
    cfgs.append({"id": "c", "name": "c", "country": "Nepal", "lat": 27.6, "lon": 85.5, "bbox": [85.5, 27.6, 85.6, 27.7]})
    idx = build_index(cfgs, tmp_path, hidden=["b", "c"])
    assert [f["id"] for f in idx["fields"]] == ["a"] and "drone_previews" not in idx


def test_live_json_names_its_field():
    from robot import bridge
    ctx = bridge.Context("serial:/dev/test", load_rules()["probe"], field="demo")
    assert bridge.live_doc("s1", "settling", "2026-11-15T16:00:00+05:45", ctx)["field"] == "demo"


def test_a_reading_for_another_field_or_no_field_is_a_demo_tray_never_kharipatis_parts():
    pdat = _fn("probeData")
    assert "lv.field === S.fid" in pdat and "kind: 'tray'" in pdat and "parts: {}" in pdat
    assert "pd.kind !== 'tray'" in _fn("forField").replace("\n", " ") or "kind !== 'tray'" in APP
    soil = re.search(r"\n  SCREENS\.soil = function.*?\n  \};\n", APP, re.S).group(0)
    assert "trayCard(" in soil and "x.field === S.fid" in soil                  # the live poll checks the field too
    tray = _fn("trayCard")
    assert "check_soil.tray_title" in tray and "check_soil.tray_line" in tray and "check_soil.tray_pot" in tray


def test_no_sample_chip_on_home_no_field_list_and_no_nasa_picture_under_a_drone_photo():
    home = re.search(r"\n  SCREENS\.home = function.*?\n  \};\n", APP, re.S).group(0)
    assert "fieldsList(" not in home and "f0.drone" in home                     # the chip only for a field without a drone photo
    osm = _fn("osm")
    assert ".drone" in osm                                                       # a field with a drone photo: no NASA 30 m picture


def test_a_browser_that_remembered_an_old_field_opens_kharipati_and_forgets_its_crop_answer():
    m = re.search(r"var fid = store\.get\('fid'\);.*?\n", APP, re.S)
    block = APP[m.start():m.start() + 400]
    assert "ids.indexOf(fid) >= 0 ? fid : (ids[0]" in block and "store.set('winter', null)" in block
