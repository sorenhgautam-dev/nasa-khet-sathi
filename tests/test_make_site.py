"""The deploy-anywhere kit (owner's item 3, 2026-11-14): scripts/make_site.py writes a config with TODOs (never guesses),
picks the build steps from the field's profile and copies a static site folder with one field."""
import argparse
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def _kit():
    spec = importlib.util.spec_from_file_location("make_site", REPO / "scripts" / "make_site.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _args(**kw):
    base = dict(lat=-18.834125, lon=47.436917, size_m=60.0, name="Rakoto's field", country="Madagascar", country_code="MG",
                aez=None, rotation=None, rotation_source=None, station=None, box_km=2.0, short_record=False)
    return argparse.Namespace(**{**base, **kw})


def test_the_square_is_the_size_asked_around_the_point():
    from pipeline.fetch.worldcover import distance_km
    sq = _kit().square(27.690767, 85.441792, 60)
    (x0, y0), (x1, _), (_, y1) = sq[0], sq[1], sq[2]
    assert distance_km(y0, x0, y0, x1) * 1000 == pytest.approx(60, abs=0.5)
    assert distance_km(y0, x0, y1, x0) * 1000 == pytest.approx(60, abs=0.5)


def test_the_config_leaves_every_unknown_null_with_a_todo():
    m = _kit()
    text = m.config_text(_args(), "rakoto-s-field")
    cfg = yaml.safe_load(text)
    assert m.slug("Rakoto's field") == "rakoto-s-field" and cfg["id"] == "rakoto-s-field"
    assert cfg["current_rotation"] is None and cfg["water_source"] is None and cfg["validation_station"] is None
    assert cfg["fao_crop_calendar"] == {"country": "MG", "aez": None} and "TODO: aez" in text
    assert cfg["record_years"] == [2001, 2025] and len(cfg["polygon"]) == 4
    full = yaml.safe_load(m.config_text(_args(aez="004", rotation="rice, potato", short_record=True), "x"))
    assert full["current_rotation"] == ["rice", "potato"] and full["fao_crop_calendar"]["aez"] == "004"
    assert full["record_years"] == [2016, 2025]


def test_the_global_defaults_build_the_core_steps_without_nepals_rain_versions():
    m = _kit()
    steps = m.build_steps({"id": "x"}, "default")
    assert steps[:4] == ["weather", "rain_check", "diary", "replay"] and "plans" in steps and "export" in steps
    assert not set(m.PROFILE_ONLY) & set(steps)
    assert not {"index", "story", "validate", "site_check", "verification", "onset_dhm", "replay_dhm"} & set(steps)
    nepal = m.build_steps({"id": "demo"}, "NP")
    assert {"plans_dhm", "verification", "onset_dhm"} <= set(nepal) and "story" not in nepal


def test_the_site_folder_holds_the_app_and_one_fields_data(tmp_path):
    m = _kit()
    site = tmp_path / "site"
    for d in ("js", "css", "data/fields", "data/labels", "data/basemap"):
        (site / d).mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html>")
    (site / "js" / "app.js").write_text("//")
    (site / "data" / "words.json").write_text("{}")
    (site / "data" / "fields" / "abroad.json").write_text("{}")
    (site / "data" / "fields" / "demo.json").write_text("{}")
    (site / "data" / "labels" / "abroad.json").write_text("{}")
    (site / "data" / "basemap" / "world.json").write_text("{}")
    field = {"id": "abroad", "name": "Abroad", "country": "Madagascar", "lat": -18.83, "lon": 47.44,
             "bbox": [47.40, -18.85, 47.44, -18.81]}
    copied = m.copy_site(field, tmp_path / "out", site=site)
    assert sorted(copied) == ["fields/abroad.json", "labels/abroad.json"]
    out = tmp_path / "out"
    assert (out / "index.html").exists() and (out / "js" / "app.js").exists() and not (out / "data" / "fields" / "demo.json").exists()
    idx = json.loads((out / "data" / "index.json").read_text())
    assert [f["id"] for f in idx["fields"]] == ["abroad"] and (out / "data" / "basemap" / "world.json").exists()
    with pytest.raises(SystemExit, match="outside site"):
        m.copy_site(field, site / "x", site=site)


def test_the_final_check_skips_exactly_the_kits_profile_only_site_files():
    """validate.NOT_ON_DEFAULTS (the files --final does not ask of a field on the global defaults) are the site files of
    the steps the kit leaves out there (PROFILE_ONLY; plans_dhm and plans_untuned write none, replay_window writes replay/)."""
    from pipeline.export import validate as va
    site_kind = {"replay_window": "replay", "simple": "simple", "rainrisk": "rainrisk", "fertiliser": "fertiliser",
                 "heatclock": "heatclock", "plans_dhm": None, "plans_untuned": None}
    assert set(_kit().PROFILE_ONLY) == set(site_kind)
    assert set(va.NOT_ON_DEFAULTS) == {k for k in site_kind.values() if k}
