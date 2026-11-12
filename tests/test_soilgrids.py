"""SoilGrids 2.0 at the field (step 4 soil water). Payloads follow the real REST response layout; the
unit blocks are copied from the live API on 2026-11-12. The demo point itself returns no prediction
(all null), so the fetch searches outward in 250 m steps and labels the distance."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

from pipeline.fetch import soilgrids as sg
from pipeline.fetch.guards import CARD_FIELDS, DataGuardError
from pipeline.fetch.rules import load_rules

UNITS = {  # verbatim from the live REST response, 2026-11-12
    "bdod": {"d_factor": 100, "mapped_units": "cg/cm³", "target_units": "kg/dm³", "uncertainty_unit": ""},
    "clay": {"d_factor": 10, "mapped_units": "g/kg", "target_units": "%", "uncertainty_unit": ""},
    "sand": {"d_factor": 10, "mapped_units": "g/kg", "target_units": "%", "uncertainty_unit": ""},
    "soc": {"d_factor": 10, "mapped_units": "dg/kg", "target_units": "g/kg", "uncertainty_unit": ""},
    "wv0033": {"d_factor": 10, "mapped_units": "(10-2 cm³/cm³)*10", "target_units": "10-2 cm³/cm³", "uncertainty_unit": ""},
    "wv1500": {"d_factor": 10, "mapped_units": "(10-2 cm³/cm³)*10", "target_units": "10-2 cm³/cm³", "uncertainty_unit": ""},
}
DEPTHS = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)]
VALUES = {"bdod": 135, "clay": 203, "sand": 380, "soc": 250, "wv0033": 330, "wv1500": 180}


def _payload(lon, lat, values=VALUES, units=UNITS):
    layers = []
    for name, u in units.items():
        depths = [{"range": {"top_depth": t, "bottom_depth": b, "unit_depth": "cm"}, "label": f"{t}-{b}cm",
                   "values": {"mean": values.get(name) if values else None}} for t, b in DEPTHS]
        layers.append({"name": name, "unit_measure": u, "depths": depths})
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"layers": layers}}


def test_parse_converts_with_the_factors_the_api_reports():
    df, info = sg.parse(_payload(85.45, 27.70))
    row = df.iloc[0]
    assert row["theta_fc_m3m3"] == pytest.approx(0.330) and row["theta_wp_m3m3"] == pytest.approx(0.180)
    assert row["clay_pct"] == pytest.approx(20.3) and row["sand_pct"] == pytest.approx(38.0)
    assert row["soc_g_kg"] == pytest.approx(25.0) and row["bdod_kg_dm3"] == pytest.approx(1.35)
    assert list(df["top_cm"]) == [t for t, _ in DEPTHS] and not info["all_null"]


def test_parse_fails_loudly_if_the_api_changes_a_unit():
    units = dict(UNITS, clay=dict(UNITS["clay"], target_units="g/kg"))
    with pytest.raises(DataGuardError, match="clay"):
        sg.parse(_payload(85.45, 27.70, units=units))


def test_an_all_null_answer_is_recognised():
    _, info = sg.parse(_payload(85.43, 27.67, values=None))
    assert info["all_null"]


def test_check_fails_when_field_capacity_is_not_above_wilting_point():
    df, _ = sg.parse(_payload(85.45, 27.70, values=dict(VALUES, wv1500=330)))
    with pytest.raises(DataGuardError, match="wilting"):
        sg.check(df)


def test_candidate_points_ring_outward_in_steps():
    pts = sg.candidate_points(27.67, 85.43, step_m=250, max_m=1000)
    assert len(pts) == 32 and [p[2] for p in pts[:8]] == [250] * 8 and pts[-1][2] == 1000
    lat, lon, d = pts[2]                                      # due east, 250 m
    east_m = (lon - 85.43) * 111320 * math.cos(math.radians(27.67))
    assert lat == pytest.approx(27.67) and east_m == pytest.approx(250, rel=0.01)


def test_fetch_uses_the_nearest_cell_with_values_and_labels_the_distance(tmp_path):
    calls = []
    pts = sg.candidate_points(27.67, 85.43, 250, 1000)
    target = pts[2][:2]

    def fake(url):
        calls.append(url)
        hit = f"lat={target[0]:.6f}" in url and f"lon={target[1]:.6f}" in url
        return _payload(target[1], target[0]) if hit else _payload(0, 0, values=None)

    field = {"id": "demo", "lat": 27.67, "lon": 85.43}
    out = sg.fetch(field, data_dir=tmp_path, get_json=fake, rules=load_rules())
    card = json.loads(Path(out["card"]).read_text())
    assert set(CARD_FIELDS) <= set(card)
    assert card["location"]["distance_m"] == 250 and card["location"]["requested"] == [27.67, 85.43]
    assert "REST" in card["notes"] and "no prediction" in card["notes"]
    n = len(calls)
    sg.fetch(field, data_dir=tmp_path, get_json=fake, rules=load_rules())
    assert len(calls) == n                                    # second run: all from the cache


def test_fetch_fails_when_no_cell_within_the_limit_has_values(tmp_path):
    limit = load_rules()["soilgrids"]["nearest_cell_max_m"]              # 3000 m since 2026-11-12 (owner, M5)
    with pytest.raises(DataGuardError, match=f"{limit} m"):
        sg.fetch({"id": "demo", "lat": 27.67, "lon": 85.43}, data_dir=tmp_path,
                 get_json=lambda url: _payload(0, 0, values=None), rules=load_rules())


def test_a_partly_null_answer_is_not_a_prediction():
    """REVIEW_NOTES M5: a cell counts only where every property and depth has a value."""
    _, info = sg.parse(_payload(85.45, 27.70, values=dict(VALUES, sand=None)))
    assert not info["all_null"] and not info["complete"]
    _, info = sg.parse(_payload(85.45, 27.70))
    assert info["complete"]


def test_fetch_skips_a_partly_null_cell_for_the_next_complete_one(tmp_path):
    pts = sg.candidate_points(27.67, 85.43, 250, 1000)
    partial, full = pts[0][:2], pts[1][:2]

    def fake(url):
        at = lambda t: f"lat={t[0]:.6f}" in url and f"lon={t[1]:.6f}" in url
        if at(partial):
            return _payload(partial[1], partial[0], values=dict(VALUES, clay=None))
        return _payload(full[1], full[0]) if at(full) else _payload(0, 0, values=None)

    out = sg.fetch({"id": "demo", "lat": 27.67, "lon": 85.43}, data_dir=tmp_path, get_json=fake, rules=load_rules())
    card = json.loads(Path(out["card"]).read_text())
    assert card["location"]["used"] == [round(full[0], 6), round(full[1], 6)]


def test_the_rest_module_never_overwrites_the_table_the_twin_reads(tmp_path):
    """soilgrids.parquet (the twin's soil) is written by soilgrids_wcs.py; the REST answer has its own files."""
    pts = sg.candidate_points(27.67, 85.43, 250, 1000)
    fake = lambda url: _payload(pts[0][1], pts[0][0])
    out = sg.fetch({"id": "demo", "lat": 27.67, "lon": 85.43}, data_dir=tmp_path, get_json=fake, rules=load_rules())
    assert Path(out["table"]).name == "soilgrids_rest.parquet" and Path(out["card"]).name == "soilgrids_rest.json"
    assert not (tmp_path / "clean" / "demo" / "soilgrids.parquet").exists()
