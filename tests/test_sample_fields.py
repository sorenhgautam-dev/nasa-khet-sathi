"""More sample fields across the demo box (Local Impact 4b; rules.yaml sample_fields, committed in cb85cc8)."""
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from pipeline.area import samples as sm
from pipeline.fetch.fields import load_field

REPO = Path(__file__).resolve().parents[1]
ORIGIN = {"lat": 27.67, "lon": 85.43}


def test_quadrants_split_at_the_origin():
    assert sm.quadrant(27.69, 85.44, ORIGIN) == "NE" and sm.quadrant(27.69, 85.42, ORIGIN) == "NW"
    assert sm.quadrant(27.65, 85.44, ORIGIN) == "SE" and sm.quadrant(27.65, 85.42, ORIGIN) == "SW"


def test_spread_pick_takes_the_best_per_quadrant_far_enough_apart():
    demo = (27.690767, 85.441792)
    ranked = [{"lat": 27.6910, "lon": 85.4420, "id": "a"},     # NE, 30 m from the demo: too close
              {"lat": 27.7000, "lon": 85.4700, "id": "b"},     # NE, about 4 km away: taken
              {"lat": 27.7010, "lon": 85.4710, "id": "c"},     # NE again: quadrant full
              {"lat": 27.6800, "lon": 85.4000, "id": "d"},     # NW: taken
              {"lat": 27.6810, "lon": 85.4040, "id": "e"},     # NW: full
              {"lat": 27.6400, "lon": 85.4600, "id": "f"},     # SE: taken
              {"lat": 27.6695, "lon": 85.4040, "id": "g"}]     # SW but about 1.2 km from d: too close
    got = sm.spread_pick(ranked, demo, ORIGIN, 1.5)
    assert [c["id"] for c in got] == ["b", "d", "f"]
    assert [c["quadrant"] for c in got] == ["NE", "NW", "SE"]


def test_sample_config_is_a_labelled_placeholder_in_the_demo_box(tmp_path):
    demo = load_field("demo")
    cand = {"lat": 27.65, "lon": 85.40, "quadrant": "SW"}
    cfg = sm.sample_config(2, cand, demo, why="test")
    path = tmp_path / "sample-2.yaml"
    sm.write_yaml(path, cfg, header="# test header\n")
    f = load_field("sample-2", tmp_path)
    assert f["placeholder"] is True and f["sample"] is True and f["sample_of"] == "demo"
    assert f["name"] == "Bhaktapur sample field 2 (PLACEHOLDER)"
    assert f["water_source"] is None and f["fetch_box"] == demo["fetch_box"] and f["bbox"] == demo["bbox"]
    assert f["current_rotation"] == demo["current_rotation"]
    assert f["current_rotation_options"] == demo["current_rotation_options"]
    assert "PLACEHOLDER" in f["current_rotation_source"]
    assert (f["validation_station"], f["correction_label"]) == (demo["validation_station"], demo["correction_label"])
    lats = [p[1] for p in f["polygon"]]
    assert (max(lats) - min(lats)) * 111194.9 == pytest.approx(60, abs=0.2)
    assert f["origin_point"] == demo["origin_point"]


@pytest.mark.skipif(not (REPO / "data" / "clean" / "demo" / "hls_monthly_ndvi.npz").exists(), reason="needs the cached HLS composites")
def test_generalised_placeholder_keeps_the_demo_defaults():
    """Another agent generalised placeholder.py (2026-11-13, night): with no seasons given, candidate 1 of the demo
    search must score exactly as recorded in placeholder_candidates.json."""
    from pipeline.fetch import placeholder as ph
    z = np.load(REPO / "data" / "clean" / "demo" / "hls_monthly_ndvi.npz")
    from affine import Affine
    t = Affine(*z["transform"].tolist())
    rec = json.loads((REPO / "data" / "clean" / "demo" / "placeholder_candidates.json").read_text())["candidates"][0]
    s, n = ph.sample_monthly(z["ndvi"], [str(k) for k in z["months"]], t, str(z["crs"]), rec["lon"], rec["lat"], 30)
    r = ph.season_check(s, [2023, 2024, 2025], 0.25)
    assert r["passes"] and r["peaks"] == rec["peaks"] and r["winter_rise"] == rec["winter_rise"]
    assert r["min_peak"] == pytest.approx(rec["min_peak"]) and n == rec["hls_pixels"]


def test_written_sample_configs_load_if_present():
    for p in sorted((REPO / "config" / "fields").glob("sample_*.yaml")):
        f = load_field(p.stem)
        assert f["sample"] is True and f["placeholder"] is True and "PLACEHOLDER" in f["name"]
        b = f["fetch_box"]
        assert b[0] < f["lon"] < b[2] and b[1] < f["lat"] < b[3]
        assert yaml.safe_load(p.read_text())["id"] == p.stem
