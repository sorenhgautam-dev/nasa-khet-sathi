"""Build step 11 (the field abroad): the fetch modules and the rain check work for any field, with the demo unchanged.
Every test has a worked number."""
import json
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import placeholder as ph


# --- placeholder.py: the zone's two seasons come from the field config; the demo keeps Nepal's ---

def _monthly(values):
    return pd.Series(values)


def test_the_demo_default_seasons_are_nepals_monsoon_and_winter():
    # 2023: monsoon Jul-Oct peak 0.70; winter Dec 2022-Mar 2023 peak 0.45; trough Oct-Nov 2022 low 0.20 -> rise 0.25
    m = _monthly({"2023-07": 0.5, "2023-08": 0.7, "2022-12": 0.3, "2023-01": 0.45, "2022-10": 0.35, "2022-11": 0.2})
    r = ph.season_check(m, [2023], 0.25)
    assert r == {"passes": True, "failed_years": [], "min_peak": 0.45, "peaks": [0.7, 0.45], "winter_rise": [0.25]}
    assert ph.season_check(m, [2023], 0.25, seasons=ph.DEMO_SEASONS) == r


def test_a_southern_field_tests_its_own_rainy_and_dry_seasons():
    seasons = ph.seasons_from_config({"seasons": [{"name": "rainy", "months": [1, 2, 3, 4]},
                                                  {"name": "dry", "months": [7, 8, 9]}],
                                      "trough": {"months": [5, 6]}})
    m = _monthly({"2023-02": 0.6, "2023-03": 0.5, "2023-05": 0.22, "2023-06": 0.2, "2023-08": 0.4,
                  "2024-02": 0.65, "2024-06": 0.21, "2024-08": 0.23})          # 2024: the dry season stays bare
    r = ph.season_check(m, [2023, 2024], 0.25, seasons=seasons)
    assert r["passes"] is False and r["failed_years"] == [2024]
    assert r["peaks"] == [0.6, 0.4, 0.65, 0.23]
    assert r["dry_rise"] == [0.2, 0.02]                                           # 0.40 - 0.20; 0.23 - 0.21
    assert r["min_peak"] == 0.23 and "winter_rise" not in r


def test_a_season_that_crosses_the_new_year_starts_in_the_previous_year():
    assert ph.season_months({"months": [12, 1, 2, 3]}, 2024) == ["2023-12", "2024-01", "2024-02", "2024-03"]
    assert ph.season_months({"months": [10, 11], "ends_in_year": -1}, 2024) == ["2023-10", "2023-11"]
    assert ph.season_months({"months": [7, 8, 9]}, 2024) == ["2024-07", "2024-08", "2024-09"]


def test_the_demo_config_has_no_seasons_and_gets_nepals():
    from pipeline.fetch.fields import load_field
    assert ph.seasons_from_config(load_field("demo").get("placeholder_seasons")) == ph.DEMO_SEASONS


def test_a_field_without_a_polygon_has_no_chosen_square_yet():
    assert ph.reference_squares({"lat": -18.83, "lon": 47.42, "polygon": None}) == []


# --- rain check B for any field: the break test (rules.yaml gpm_series.break_test, committed 6d2919c before any run) ---

from pipeline.checks import rain_check as rc  # noqa: E402

RULE = {"gauge_drop_pct_points": 20, "min_months_per_year": 6, "min_years_before": 5, "pettitt_p_max": 0.05,
        "change_year_tolerance": 1}


def _gauge_months(before=97.0, after=60.0, from_year=2017, last="2025-09"):
    months = [str(p) for p in pd.period_range("2001-01", last, freq="M")]
    return pd.DataFrame({"month": months, "imerg_gauge_weight_pct": [before if int(m[:4]) < from_year else after for m in months]})


def test_the_gauge_loss_year_is_the_first_year_that_stays_far_below_the_years_before():
    t = _gauge_months()
    t.loc[t["month"].str.startswith("2010"), "imerg_gauge_weight_pct"] = 70.0     # one bad year that recovers
    r = rc.gauge_loss_year(t, 20, 6, 5)
    assert r["year"] == 2017
    # mean of 2001-2016 = (15 x 97 + 70) / 16 = 95.3125; 2017 is 60, a drop of 35.3 points
    assert r["before_mean_pct"] == pytest.approx(95.3125) and r["drop_pct_points"] == pytest.approx(35.3125)
    assert r["yearly_mean_pct"][2025] == 60.0


def test_a_year_with_too_few_months_does_not_count_and_no_drop_means_no_loss():
    assert rc.gauge_loss_year(_gauge_months(after=97.0), 20, 6, 5)["year"] is None
    t = _gauge_months(after=97.0, last="2025-03")                                    # 2025 has 3 months only
    t.loc[t["month"] >= "2025-01", "imerg_gauge_weight_pct"] = 10.0
    assert rc.gauge_loss_year(t, 20, 6, 5)["year"] is None
    t2 = _gauge_months(before=60.0, after=45.0)                                     # never gauged: a 15-point fall
    assert rc.gauge_loss_year(t2, 20, 6, 5)["year"] is None


def _yearly(values, first=2001):
    return {first + k: v for k, v in enumerate(values)}


def test_the_break_is_found_when_the_cause_the_step_and_a_steady_reference_all_hold():
    chirps = _yearly([1400.0 if k % 2 else 1500.0 for k in range(25)])               # alternates: no step
    gpm = {y: v * (1.2 if y < 2017 else 1.8) for y, v in chirps.items()}
    r = rc.break_test(_gauge_months(), gpm, chirps, RULE)
    assert r["found"] is True and r["year"] == 2017
    # GPM / CHIRPS: 16 years at 1.2, then 9 at 1.8 -> Pettitt K = 16 x 9 = 144, change after 2016,
    # p = 2 exp(-6 x 144^2 / (25^3 + 25^2)) = 2 exp(-7.65637) = 0.000947
    assert r["gpm_over_chirps_pettitt"]["k"] == 144 and r["gpm_over_chirps_pettitt"]["change_after"] == 2016
    assert r["gpm_over_chirps_pettitt"]["p"] == pytest.approx(0.000947, abs=2e-6)
    assert r["step_gpm_over_chirps"] == pytest.approx(1.5)
    assert r["checks"] == {"gauge_loss": True, "gpm_steps_against_chirps": True, "chirps_steady": True}


def test_no_break_when_the_reference_steps_too_or_a_line_of_evidence_is_missing():
    chirps = _yearly([1400.0 if y < 2017 else 2100.0 for y in range(2001, 2026)])     # CHIRPS itself steps in 2017
    gpm = {y: v * (1.2 if y < 2017 else 1.8) for y, v in chirps.items()}
    r = rc.break_test(_gauge_months(), gpm, chirps, RULE)
    assert r["found"] is False and r["checks"]["chirps_steady"] is False
    steady = _yearly([1400.0 if k % 2 else 1500.0 for k in range(25)])
    r2 = rc.break_test(None, {y: v * 1.5 for y, v in steady.items()}, steady, RULE)
    assert r2["found"] is False and any("no gauge-weight series" in w for w in r2["why_not"])
    r3 = rc.break_test(_gauge_months(), {y: 1500.0 for y in range(2001, 2026)}, None, RULE)
    assert r3["found"] is False and any("no CHIRPS" in w for w in r3["why_not"])
    r4 = rc.break_test(_gauge_months(after=97.0), {y: v * 1.5 for y, v in steady.items()}, steady, RULE)
    assert r4["found"] is False and r4["checks"]["gauge_loss"] is False


def test_the_committed_rule_is_the_one_the_tests_use():
    from pipeline.fetch.rules import load_rules
    bt = load_rules()["gpm_series"]["break_test"]
    assert {k: bt[k] for k in RULE} == RULE


# --- fetch modules: no Nepal assumption left for a field abroad; the demo's text and numbers unchanged ---

def test_imerg_utc_days_are_told_in_the_fields_local_time():
    from pipeline.fetch import gpm
    assert gpm.local_day_label(None) == "05:45-05:45 Nepal time"                       # the demo (no utc_offset key)
    assert gpm.local_day_label("+05:45") == "05:45-05:45 Nepal time"
    assert gpm.local_day_label("+03:00") == "03:00-03:00 local time (UTC+03:00)"
    assert gpm.local_day_label("-06:00") == "18:00-18:00 local time (UTC-06:00)"      # UTC midnight is 18:00 the day before
    assert gpm.time_zone_text(None) == gpm.TIME_ZONE                                     # the demo's card text, unchanged
    assert "03:00-03:00 local time (UTC+03:00)" in gpm.time_zone_text("+03:00") and "Nepal" not in gpm.time_zone_text("+03:00")


def test_the_station_day_boundary_is_told_in_the_fields_local_time():
    from pipeline.fetch import ghcn
    assert "05:45-05:45 Nepal time" in ghcn.day_boundary_text(None)
    t = ghcn.day_boundary_text("+03:00")
    assert "03:00-03:00 local time (UTC+03:00)" in t and "Nepal" not in t


def test_the_chirps_field_cell_comes_from_the_cached_box_and_the_field_as_it_is_now():
    from pipeline.fetch import chirps
    lat = np.array([-18.875, -18.825, -18.775])          # 0.05 deg cell centres
    lon = np.array([47.375, 47.425, 47.475])
    assert chirps.field_cell(lat, lon, -18.83, 47.42) == (1, 1)
    assert chirps.field_cell(lat, lon, -18.79, 47.44) == (2, 1)                       # a field moved after the fetch
    with pytest.raises(ValueError):
        chirps.field_cell(lat, lon, -18.70, 47.42)                                    # outside the cached cells


def test_a_global_file_held_for_another_field_is_reused(tmp_path):
    from pipeline.fetch.grace import shared_file
    (tmp_path / "demo").mkdir()
    f = tmp_path / "demo" / "GRCTellus.JPL.200204_202508.GLO.RL06.3M.MSCNv04CRI.nc"
    f.write_bytes(b"x")
    (tmp_path / "abroad").mkdir()
    assert shared_file(tmp_path, "abroad", "GRCTellus.JPL.*.nc") == f
    assert shared_file(tmp_path, "demo", "GRCTellus.JPL.*.nc") == f
    assert shared_file(tmp_path / "none", "abroad", "GRCTellus.JPL.*.nc") is None


def test_faostat_keeps_the_fields_country_and_crops():
    from pipeline.fetch import faostat as fs

    def row(area, item, year=2010, value=30000.0):
        return {"Area Code": area, "Area": "x", "Item Code": item, "Item": "i", "Element": "Yield", "Year": str(year),
                "Unit": "kg/ha", "Value": str(value), "Flag": "A"}
    rows = [row("149", "27"), row("129", "27", value=2500.0), row("129", "116", value=7000.0), row("129", "15")]
    df, _ = fs.parse(rows)                                                              # the demo: Nepal, rice/wheat/maize
    assert df["yield_kg_ha"].tolist() == [30000.0]
    df2, _ = fs.parse(rows, area="129", items={"27": "rice", "116": "potato"})
    assert sorted(zip(df2["crop"], df2["yield_kg_ha"])) == [("potato", 7000.0), ("rice", 2500.0)]
    assert fs.items_for(["rice", "potato"]) == {"27": "rice", "116": "potato"}


def test_a_validation_station_without_a_correction_label_corrects_nothing():
    from pipeline.fetch.weather import station_corrects
    assert station_corrects({"validation_station": "NP000444540", "correction_label": "Kathmandu-valley correction"})
    assert not station_corrects({"validation_station": "MA000067083"})                 # validation only (build step 11)
    assert not station_corrects({})


# --- scripts/fetch_field.py: one resumable driver ---

def _driver():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("fetch_field", Path(__file__).resolve().parents[1] / "scripts" / "fetch_field.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_before_the_square_is_picked_only_the_box_steps_run():
    ff = _driver()
    p = dict(ff.plan({"id": "x", "polygon": None, "validation_station": "S"}, {}))
    assert [k for k, v in p.items() if v == "run"] == ["worldcover", "hls_recent", "placeholder", "modis_submit", "modis",
                                                       "gpm", "chirps", "hls"]
    assert p["power"].startswith("wait") and p["rain_check"].startswith("wait") and len(p) == len(ff.STEPS)
    assert p["cropcalendar"] == "skip: fao_crop_calendar not in config"           # Nepal's fields keep crops.json


def test_a_held_modis_bundle_is_not_fetched_again_and_a_short_record_asks_only_for_its_years():
    ff = _driver()
    field = {"id": "x", "polygon": [[0, 0]] * 4}
    assert dict(ff.plan(field, {}, present={"modis_submit", "modis"}))["modis"] == "skip: already held"
    assert ff.command("gpm", field) == ["-m", "pipeline.fetch.gpm", "--workers", "6"]                 # 2001-2025: as before
    short = {**field, "record_years": [2016, 2025]}
    assert ff.command("gpm", short)[-4:] == ["--start", "2016-01-01", "--end", "2025-12-31"]
    assert ff.command("chirps", short) == ["-m", "pipeline.fetch.chirps", "--years", "2016-2025"]
    assert ff.command("hls", short)[-2:] == ["--since", "2016-01-01"] and ff.command("nasadem", short) == ["-m", "pipeline.fetch.nasadem"]


def test_done_steps_are_skipped_unless_forced_and_a_station_step_needs_a_station():
    ff = _driver()
    field = {"id": "x", "polygon": [[0, 0]] * 4}
    done = {"gpm": {"exit": 0}, "chirps": {"exit": 1}}
    p = dict(ff.plan(field, done))
    assert p["gpm"] == "skip: done" and p["chirps"] == "run" and p["ghcn"] == "skip: validation_station not in config"
    assert dict(ff.plan(field, done, only=["gpm"], force=["gpm"])) == {"gpm": "run"}


def test_the_station_card_says_validation_only_without_a_correction_label(tmp_path):
    import gzip
    from pipeline.fetch import ghcn
    text = "MA000067083,20200101,PRCP,12,,,S,\nMA000067083,20200101,TMAX,251,,,S,\nMA000067083,20200101,TMIN,152,,,S,\n"
    blob = gzip.compress(text.encode())
    abroad = {"id": "abroad", "validation_station": "MA000067083", "utc_offset": "+03:00"}
    c = ghcn.fetch(abroad, "MA000067083", data_dir=tmp_path, get_bytes=lambda u: blob)["card_data"]
    assert c["notes"].startswith("Validation only") and "03:00-03:00 local time (UTC+03:00)" in c["time_zone"]
    demo = {"id": "d2", "validation_station": "MA000067083", "correction_label": "x"}
    c2 = ghcn.fetch(demo, "MA000067083", data_dir=tmp_path, get_bytes=lambda u: blob)["card_data"]
    assert c2["notes"].startswith("Validation; also the reference for decision A") and "05:45-05:45 Nepal time" in c2["time_zone"]


def test_a_gpm_request_ending_before_the_last_final_day_asks_cmr_for_no_late_days(tmp_path, monkeypatch):
    import sys
    import types
    from pipeline.fetch import gpm
    calls = []

    class G(dict):
        def data_links(self):
            return ["https://data.gesdisc.earthdata.nasa.gov/data/x.HDF5"]

    def search_data(short_name, version, temporal):
        calls.append(short_name)
        return [G(umm={"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": d}}}) for d in ("2013-06-29T00", "2013-06-30T00")]
    monkeypatch.setitem(sys.modules, "earthaccess", types.SimpleNamespace(login=lambda **k: None, search_data=search_data))
    monkeypatch.setattr(gpm, "_get", lambda *a: (_ for _ in ()).throw(RuntimeError("offline")))
    field = {"id": "x", "lat": -18.83, "lon": 47.42, "fetch_box": [47.40, -18.85, 47.44, -18.81]}
    with pytest.raises(RuntimeError, match="every GPM request failed"):
        gpm.fetch(field, workers=1, data_dir=tmp_path, start="2013-06-29", end="2013-06-30")
    assert calls == ["GPM_3IMERGDF"]


def test_the_rain_check_names_normals_only_where_the_config_does():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("rrc", Path(__file__).resolve().parents[1] / "scripts" / "run_rain_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    demo = m.rain_check_config({"id": "demo", "validation_station": "NP000444540"})
    assert demo["normals"] == ["Bhaktapur", "Kathmandu Airport"] and demo["station_key"] == "airport"
    abroad = m.rain_check_config({"id": "ambohidratrimo", "validation_station": "MA000067083"})
    assert abroad["normals"] == [] and abroad["station_key"] == "ma000067083" and abroad["station_name"] == "MA000067083"


def test_a_sample_shares_its_demos_box_downloads_and_fetches_only_its_own_point(tmp_path):
    ff = _driver()
    demo = {"id": "demo", "fetch_box": [1, 2, 3, 4]}
    sample = {"id": "sample-1", "sample_of": "demo", "fetch_box": [1, 2, 3, 4], "polygon": [[0, 0]] * 4,
              "validation_station": "S"}
    assert ff.shares_box_with(sample, demo) == "demo"
    assert ff.shares_box_with({**sample, "fetch_box": [1, 2, 3, 5]}, demo) is None
    p = dict(ff.plan(sample, {}, shared_with="demo"))
    assert [k for k, v in p.items() if v.startswith("skip: box shared")] == ["worldcover", "hls_recent", "modis_submit", "modis",
                                                                            "gpm", "chirps", "hls"]
    assert p["placeholder"] == "skip: the square is in the config"
    assert p["gpm_build"] == "run" and p["power"] == "run" and p["ghcn"] == "run"
    for x in ("gpm", "hls_l30"):
        (tmp_path / x / "demo").mkdir(parents=True)
    assert ff.link_shared("sample-1", "demo", tmp_path) == ["gpm", "hls_l30"]
    assert (tmp_path / "gpm" / "sample-1").resolve() == (tmp_path / "gpm" / "demo").resolve()
    assert ff.link_shared("sample-1", "demo", tmp_path) == []                       # already linked: nothing new
