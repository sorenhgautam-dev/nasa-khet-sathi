"""The four features of the farmer's question (2026-11-14): labels, Field Pulse, Data Check-up, their validation, the
site check of their links and the farmer scoring (rules.yaml labels, pulse, checkup, window_replay)."""
import copy
import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from pipeline.checks import verify as v
from pipeline.export import build_checkup as bc
from pipeline.export import build_labels as bl
from pipeline.export import build_pulse as bp
from pipeline.export import validate as val
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.rules import load_rules
from scripts import check_site, run_verification as rv

REPO = Path(__file__).resolve().parents[1]
RULES = load_rules()
CARD = {"rain_months": {"status": "ESTIMATE", "k": 13, "n": 20}, "rain_month_words": {"status": "VERIFIED", "k": 12, "n": 12},
        "flood_years": {"status": "ESTIMATE", "k": 2, "n": 2}, "drought_years": {"status": "NOT YET VERIFIABLE", "k": 2, "n": 4},
        "harvest_years": {"status": "NOT YET VERIFIABLE", "k": 0, "n": 0,
                          "replay_window": {"status": "ESTIMATE", "k": 4, "n": 6}}}


def test_a_label_is_verified_only_with_a_verified_row_and_takes_the_weakest_of_several_rows():
    f = {"id": "x", "correction_label": "valley"}
    assert bl.label_for("rain_month_words", f, RULES, CARD) | {"sources": None} == {
        "sure": "verified", "status": "VERIFIED", "k": 12, "n": 12, "scale": "valley", "rain_corrected": True,
        "sources": None, "scorecard": "rain_month_words"}
    ev = bl.label_for("replay_event", f, RULES, CARD)       # flood ESTIMATE + drought NOT YET VERIFIABLE: weakest, k and n summed
    assert (ev["sure"], ev["status"], ev["k"], ev["n"]) == ("estimate", "NOT YET VERIFIABLE", 4, 6)
    rw = bl.label_for("replay_window", f, RULES, CARD)      # the sub-row the farmer scoring writes
    assert (rw["status"], rw["k"], rw["n"]) == ("ESTIMATE", 4, 6)
    assert bl.label_for("pulse_modis", f, RULES, CARD)["status"] == "NOT YET VERIFIABLE"     # no yardstick row
    assert bl.label_for("replay_window", f, RULES, {})["status"] == "NOT YET VERIFIABLE"   # no scorecard at all


def test_a_label_takes_the_coarsest_scale_of_the_inputs_that_mainly_drive_it():
    valley, abroad = {"id": "x", "correction_label": "valley"}, {"id": "y"}
    assert bl.label_for("pulse_hls", valley, RULES, {})["scale"] == "field"
    assert bl.label_for("pulse_curve", valley, RULES, {})["scale"] == "neighbourhood"           # HLS 30 m and MODIS 250 m
    assert bl.label_for("plan_harvest", valley, RULES, {})["scale"] == "valley"                 # twin: GPM, corrected POWER, SoilGrids
    assert bl.label_for("plan_harvest", abroad, RULES, {})["scale"] == "region"                 # uncorrected POWER, 55 km
    assert bl.label_for("plan_water", valley, RULES, {})["sources"] == ["gpm", "power", "soilgrids", "grace"]  # GRACE listed, not scaling
    assert bl.label_for("groundwater", valley, RULES, {})["scale"] == "region"


def test_pulse_points_typical_dates_and_seasons_follow_the_diary():
    g = pd.DataFrame({"date": ["2001-01-09", "2013-04-01", "2013-05-01", "2013-05-01", "2013-06-01"],
                      "source": ["modis", "hls_l30", "hls_s30", "modis", "hls_l30"], "ndvi": [0.31862, None, 0.5, 0.4, 0.61]})
    pts = bp.observations(g, "2013-04-11")
    assert pts == {"hls": [["2013-05-01", 0.5], ["2013-06-01", 0.61]], "modis": [["2001-01-09", 0.319]]}
    chosen = {"2023": [{"start": "2022-12-16", "peak": "2023-03-17", "end": "2023-05-21", "peak_ndvi": 0.8, "source": "hls"}],
              "2024": [{"start": "2023-12-20", "peak": "2024-03-09", "end": "2024-05-15", "peak_ndvi": 0.8, "source": "hls"}],
              "2025": [{"start": "2025-01-02", "peak": "2025-03-18", "end": "2025-05-17", "peak_ndvi": 0.8, "source": "hls"}]}
    ss = bp.seasons(chosen)
    assert [s["slot"] for s in ss] == ["winter"] * 3 and ss[0]["greenup"] == "2022-12-16"
    t = bp.typical(ss, ["rice", "potato"], load_crops())
    # green-up days from 1 January of the season's year: -16, -12, +1 -> median -12 = 20 Dec; potato's initial stage is
    # 25 days (crops.json), so planting = 25 Nov. End: 140, 135, 136 -> 136 = 17 May (a 365-day year)
    assert t == [{"slot": "winter", "crop": "potato", "planting": "11-25", "greenup": "12-20", "peak": "03-17",
                  "harvest": "05-17", "years": [2023, 2025], "n": 3}]


def test_checkup_counts_complete_years_and_reads_only_the_fields_own_evidence():
    d = pd.date_range("2019-01-01", "2020-12-30")
    assert bc.complete_year_totals(d, [1.0] * len(d)) == {2019: 365.0}     # 2020 lacks 31 Dec: not complete
    bt = {"found": True, "year": 2017, "gauge_loss": {"year": 2017, "yearly_mean_pct": {"2016": 96.58, "2017": 62.92, "2018": 56.33}},
          "chirps_pettitt": {"p": 0.237, "change_after": 2004}, "gpm_pettitt": {"p": 0.0014, "change_after": 2016}}
    ev = {e["id"]: e for e in bc.evidence(bt, None, None)}
    assert sorted(ev) == ["chirps_steady", "gauge_weight", "pettitt_gpm"]
    assert ev["gauge_weight"]["after_yearly_pct"] == [56, 63] and "before_pct" not in ev["gauge_weight"]


def test_season_dates_score_within_one_dekad_of_the_farmers_dates():
    seasons = [{"year": 2025, "slot": "winter", "source": "hls", "greenup": "2024-12-19", "end": "2025-05-17"},
               {"year": 2025, "slot": "monsoon", "source": "hls", "greenup": "2025-07-05", "end": "2025-10-20"}]
    farmer = [("potato", 2025, date(2024, 11, 20), date(2025, 5, 30)),     # planting 19 Dec - 25 = 24 Nov: 4 days; end 13 days
              ("rice", 2025, date(2025, 6, 20), date(2025, 10, 25)),       # 5 Jul - 22 = 13 Jun: 7 days; end 5 days
              ("rice", 2024, date(2024, 6, 20), date(2024, 10, 25))]       # no 2024 season: both fail
    assert v.season_date_passes(farmer, seasons, {"potato": 25, "rice": 22}, 10) == [True, False, True, True, False, False]


def test_farmer_files_score_only_once_locked_and_never_after_a_change(tmp_path, monkeypatch):
    monkeypatch.setattr(rv, "ROOT", tmp_path)
    monkeypatch.setattr(rv, "FARMER", tmp_path / "data/field_visit")
    assert rv._locked_csv("f", "farmer_years.csv", ["kind", "year", "crop"]) is None
    p = tmp_path / "data/field_visit/f/farmer_years.csv"
    p.parent.mkdir(parents=True)
    p.write_text("kind,year,crop,why\nworst,2023,potato,dry winter\n")
    with pytest.raises(SystemExit, match="is not locked"):
        rv._locked_csv("f", "farmer_years.csv", ["kind", "year", "crop"])
    (tmp_path / "config").mkdir()
    (tmp_path / "config/locked_test.yaml").write_text(
        f"data/field_visit/f/farmer_years.csv: {hashlib.sha256(p.read_bytes()).hexdigest()}\n")
    assert rv._locked_csv("f", "farmer_years.csv", ["kind", "year", "crop"])[0]["year"] == "2023"
    p.write_text("kind,year,crop,why\nworst,2024,potato,dry winter\n")
    with pytest.raises(SystemExit, match="changed after it was locked"):
        rv._locked_csv("f", "farmer_years.csv", ["kind", "year", "crop"])


def test_feature_files_link_only_to_the_sites_own_files():
    assert check_site.data_link_problems("data/pulse/x.json", {"nearby": {"map": "data/area/x.json"}}) == []
    bad = check_site.data_link_problems("data/pulse/x.json", {"a": ["/data/x.json", {"b": "https://example.org"}]})
    assert len(bad) == 2 and {b["kind"] for b in bad} == {"data link"}


@pytest.mark.skipif(not (REPO / "site/data/replay/demo.json").exists(), reason="no exported replay yet")
def test_validate_catches_a_replay_result_that_does_not_follow_its_score():
    doc = json.loads((REPO / "site/data/replay/demo.json").read_text())
    field = json.loads((REPO / "site/data/fields/demo.json").read_text())
    assert val.validate_feature("replay", doc, field) == []
    bad = copy.deepcopy(doc)
    row = bad["plans"][0]["results"]["m6"]["medium"][0]
    row["result"] = "worked" if row["result"] != "worked" else "failed"
    errs = val.validate_feature("replay", bad, field)
    assert any("does not follow its score" in e for e in errs) and any("summary does not count" in e for e in errs)
