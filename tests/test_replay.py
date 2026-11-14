"""Build step 5 (parts that do not need GPM): replay a rotation through every season of the record, both
rain-fed and irrigated (owner, step-4 review item 3), with the Ky sensitivity for crops whose Ky is
assumed (item 4). Synthetic weather; crop values from crops.json."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.plans import simulate as sim

LIB = load_crops()
SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200],
                     "theta_fc_m3m3": [0.32, 0.33, 0.33], "theta_wp_m3m3": [0.15, 0.20, 0.22],
                     "sand_pct": [40.0, 40.0, 40.0], "clay_pct": [20.0, 20.0, 20.0]})   # loam: FAO-56 bare soil needs the texture
CN = {"bare": 91, "wheat": 83, "rice": 83, "potato": 85}
OPTS = dict(bare_kc=0.3)


def _weather(start="2001-01-01", end="2025-12-31", monsoon_only=True):
    d = pd.date_range(start, end)
    rain = np.where(d.month.isin([6, 7, 8, 9]), 12.0, 0.0) if monsoon_only else np.full(len(d), 3.0)
    # wind and humidity columns as in the real weather table (fetch/weather.py), for the Kc climate adjustment
    return pd.DataFrame({"date": d, "et0_mm": 3.5, "rain_mm": rain, "tmin_frost_c": 5.0,
                         "ws2m_ms": 2.0, "ea_kpa": 1.5, "tmax_c": 25.0})


def test_rotation_plan_keeps_only_seasons_inside_the_record():
    plan = sim.rotation_plan(["wheat", "rice"], LIB, "2001-01-01", "2025-12-31")
    assert plan[0] == ("rice", "2001-06-23")                      # wheat sown Nov 2000 has no weather
    assert sum(c == "rice" for c, _ in plan) == 25 and sum(c == "wheat" for c, _ in plan) == 24
    assert [d for _, d in plan] == sorted(d for _, d in plan)


def test_rotation_plan_refuses_overlapping_crops():
    with pytest.raises(ValueError, match="overlap"):
        sim.rotation_plan(["rice", "rice"], LIB, "2001-01-01", "2003-12-31")


def test_replay_gives_one_row_per_year_2001_to_2025_with_harvest_0_to_100():
    out = sim.replay(_weather(), ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)
    years = out["years"]
    assert [y["year"] for y in years] == list(range(2001, 2026))
    assert all(0 <= y["harvest"] <= 100 and y["dry_days"] >= 0 for y in years)
    assert years[0]["crops"] == ["rice"] and years[1]["crops"] == ["wheat", "rice"]
    for name, seg in out["segments"].items():
        assert abs(seg["balance_residual_mm"]) < 1.0, name


def test_each_season_belongs_to_the_year_it_is_harvested():
    out = sim.replay(_weather(), ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)
    wheat = [s for s in out["seasons"] if s["crop"] == "wheat"]
    assert wheat[0]["start"] == "2001-10-30" and wheat[0]["year"] == 2002


def test_dry_winters_hurt_rain_fed_wheat_but_not_irrigated_wheat():
    dry = sim.replay(_weather(), ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)
    wet = sim.replay(_weather(), ["wheat", "rice"], LIB, SOIL, CN, irrigated=True, **OPTS)
    w_dry = [s for s in dry["seasons"] if s["crop"] == "wheat"]
    w_wet = [s for s in wet["seasons"] if s["crop"] == "wheat"]
    assert all(s["harvest_pct"] < 90 for s in w_dry)
    assert all(s["harvest_pct"] == pytest.approx(100.0) and s["irrigation_mm"] > 0 for s in w_wet)


def test_a_year_combines_its_crops_as_mean_harvest_and_summed_dry_days_and_water():
    seasons = [{"crop": "wheat", "year": 2002, "harvest_pct": 60.0, "dry_days": 10, "ky_assumed": False,
                "irrigation_mm": 120.0, "pond_supply_mm": 0.0},
               {"crop": "rice", "year": 2002, "harvest_pct": 100.0, "dry_days": 0, "ky_assumed": True,
                "irrigation_mm": 300.0, "pond_supply_mm": 300.0}]
    y = sim.yearly(seasons)[0]
    assert y == {"year": 2002, "harvest": 80.0, "dry_days": 10, "crops": ["wheat", "rice"], "ky_assumed": True,
                 "irrigation_mm": 420.0, "pond_supply_mm": 300.0}


def test_replay_reports_irrigation_and_pond_water_per_season_and_year_in_both_cases():
    """H1: the paddy's pond water is irrigation, reported per season and per year; rain-fed gets none."""
    for irrigated in (False, True):
        out = sim.replay(_weather(), ["rice", "potato"], LIB, SOIL, CN, irrigated=irrigated, **OPTS)
        for y in out["years"]:
            ss = [s for s in out["seasons"] if s["year"] == y["year"]]
            assert y["irrigation_mm"] == pytest.approx(sum(s["irrigation_mm"] for s in ss))
            assert y["pond_supply_mm"] == pytest.approx(sum(s["pond_supply_mm"] for s in ss))
        rice = [s for s in out["seasons"] if s["crop"] == "rice"]
        if irrigated:
            assert all(s["pond_supply_mm"] > 0 and s["irrigation_mm"] >= s["pond_supply_mm"] for s in rice)
        else:
            assert all(s["irrigation_mm"] == 0.0 and s["pond_supply_mm"] == 0.0 for s in out["seasons"])
        for name, seg in out["segments"].items():
            assert abs(seg["balance_residual_mm"]) < 1e-6, name


def test_rain_fed_rice_feels_a_thin_monsoon():
    """H1: rain of 1.5 mm every day never makes a 10-day dry spell, so the old rule kept rain-fed rice ponded at
    100%. With no outside water the bucket dries below RAW and the harvest falls; irrigated rice stays at 100%."""
    w = _weather()
    w["rain_mm"] = 1.5
    dry = sim.replay(w, ["rice", "potato"], LIB, SOIL, CN, irrigated=False, **OPTS)
    wet = sim.replay(w, ["rice", "potato"], LIB, SOIL, CN, irrigated=True, **OPTS)
    assert all(s["harvest_pct"] < 100 and s["dry_days"] > 0 for s in dry["seasons"] if s["crop"] == "rice")
    assert all(s["harvest_pct"] == pytest.approx(100.0) for s in wet["seasons"])


def test_the_configured_rice_then_potato_rotation_replays_every_year():
    out = sim.replay(_weather(), ["rice", "potato"], LIB, SOIL, CN, irrigated=False, **OPTS)
    assert [y["year"] for y in out["years"]] == list(range(2001, 2026))
    assert out["partial_years"] == {"2001": ["rice"]}         # potato sown Oct 2000 has no weather


def test_a_rotation_with_a_crop_that_cannot_be_simulated_is_refused():
    with pytest.raises(ValueError, match="buckwheat cannot be simulated"):
        sim.rotation_plan(["rice", "buckwheat"], LIB, "2001-01-01", "2025-12-31")


def test_ky_sensitivity_changes_only_crops_whose_ky_is_assumed():
    seasons = [{"crop": "wheat", "year": 2002, "sum_eta_mm": 50.0, "sum_etc_mm": 100.0, "dry_days": 5},
               {"crop": "rice", "year": 2002, "sum_eta_mm": 50.0, "sum_etc_mm": 100.0, "dry_days": 5}]
    s = sim.ky_sensitivity(seasons, LIB, [0.8, 1.0, 1.2])
    assert s[0.8]["rice"] == [pytest.approx(60.0)] and s[1.2]["rice"] == [pytest.approx(40.0)]
    assert s[0.8]["wheat"] == s[1.2]["wheat"] == [pytest.approx(100 * (1 - 1.15 * 0.5))]


def test_season_indicators_for_events_are_reported_and_frost_is_not_one():
    """M1 (owner, 2026-11-12): frost is not a replay event, so the replay carries no frost indicator."""
    w = _weather()
    w.loc[w["date"] == pd.Timestamp("2010-07-10"), "rain_mm"] = 180.0
    w.loc[w["date"] == pd.Timestamp("2010-01-15"), "tmin_frost_c"] = -3.0
    out = sim.replay(w, ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)
    rice10 = next(s for s in out["seasons"] if s["crop"] == "rice" and s["year"] == 2010)
    assert rice10["rain_max_day_mm"] == 180.0
    assert not any(k.startswith("tmin_frost") for s in out["seasons"] for k in s)


def test_station_dry_run_uses_only_runs_of_well_covered_years():
    from pipeline.twin.inputs import covered_year_runs
    d = pd.date_range("2015-01-01", "2022-12-31")
    has = pd.Series(True, index=d)
    has[(d.year == 2018) & (d.dayofyear % 2 == 0)] = False      # 2018: half the days
    has[d.year == 2020] = False
    runs = covered_year_runs(has, min_fraction=0.9)
    assert runs == [(2015, 2017), (2019, 2019), (2021, 2022)]


# --- silent-failure review (ECC silent-failure-hunter, 2026-11-12): fail loudly, never a plausible wrong number

def test_a_missing_et0_or_rain_value_stops_the_replay():
    for col in ("et0_mm", "rain_mm"):
        w = _weather()
        w.loc[w["date"] == pd.Timestamp("2002-01-10"), col] = np.nan
        with pytest.raises(ValueError, match=col):
            sim.replay(w, ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)


def test_a_gap_in_the_dates_stops_the_replay():
    w = _weather()
    w = w[(w["date"] < "2002-01-01") | (w["date"] > "2002-01-20")]
    with pytest.raises(ValueError, match="consecutive"):
        sim.replay(w, ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)


def test_harvest_refuses_a_non_finite_water_use():
    from pipeline.twin.yield_ import harvest_pct
    with pytest.raises(ValueError, match="finite"):
        harvest_pct(float("nan"), 300.0, 1.0)


def test_a_soil_that_holds_no_water_stops_the_season():
    dry_soil = SOIL.assign(theta_wp_m3m3=SOIL["theta_fc_m3m3"])
    with pytest.raises(ValueError, match="TAW"):
        sim.replay(_weather(), ["wheat", "rice"], LIB, dry_soil, CN, irrigated=False, **OPTS)


def test_power_filling_days_outside_the_gpm_record_is_a_problem():
    d = pd.date_range("2001-01-01", "2006-12-31")
    src = np.where(d.year <= 2005, "gpm", "power")                 # GPM file stops at the end of 2005
    w = pd.DataFrame({"date": d, "rain_source": src})
    assert any("outside the GPM record" in p for p in sim.rain_record_problems(w))
    src2 = np.where(d == pd.Timestamp("2004-03-01"), "power", "gpm")  # one gap inside the record: allowed (D)
    assert sim.rain_record_problems(pd.DataFrame({"date": d, "rain_source": src2})) == []


def test_a_missing_rain_source_is_a_problem():
    d = pd.date_range("2001-01-01", "2001-12-31")
    w = pd.DataFrame({"date": d, "rain_source": "missing"})
    assert any("missing" in p for p in sim.rain_record_problems(w))


@pytest.mark.parametrize("value,case", [("rain-only", "rain-fed"), ("canal", "irrigated"), ("well", "irrigated"),
                                        ("irrigated", "irrigated")])
def test_known_water_sources_map_to_a_case(value, case):
    assert sim.export_case(value) == case


def test_an_unknown_water_source_spelling_is_refused():
    with pytest.raises(ValueError, match="water_source"):
        sim.export_case("rain only")


def test_a_record_too_short_for_any_season_says_so():
    with pytest.raises(sim.NoSeasonError):
        sim.rotation_plan(["wheat", "rice"], LIB, "2001-01-01", "2001-03-31")


def test_years_whose_crops_differ_from_the_rotation_are_listed():
    out = sim.replay(_weather(), ["wheat", "rice"], LIB, SOIL, CN, irrigated=False, **OPTS)
    assert out["partial_years"] == {"2001": ["rice"]}



# --- scripts/run_replay.py run(): both water cases carry the per-year water; no paddy_rice rule is read ---

def test_run_replay_writes_irrigation_and_pond_water_per_year_without_any_paddy_rule():
    from pipeline.fetch.rules import load_rules
    from scripts import run_replay as rr
    rules = {k: v for k, v in load_rules().items() if k != "paddy_rice"}
    out = rr.run(_weather(), ["rice", "potato"], LIB, SOIL, CN, rules)
    for case in ("rain-fed", "irrigated"):
        assert all({"irrigation_mm", "pond_supply_mm"} <= set(y) for y in out[case]["years"])
        assert all({"irrigation_mm", "pond_supply_mm"} <= set(s) for s in out[case]["seasons"])
        assert set(out[case]["events"].values()) <= {"none", "drought", "flood"}
    assert sum(y["pond_supply_mm"] for y in out["irrigated"]["years"]) > 0
    assert sum(y["irrigation_mm"] for y in out["rain-fed"]["years"]) == 0.0


def test_a_season_without_a_harvest_number_stops_the_year_sum():
    """L2: a season cut short by the record's end has harvest_pct None; the year rule must refuse it loudly."""
    seasons = [{"crop": "rice", "year": 2025, "harvest_pct": None, "dry_days": 0, "irrigation_mm": 0.0,
                "pond_supply_mm": 0.0, "start": "2025-06-23", "harvest_note": "no harvest number: season cut short"}]
    with pytest.raises(ValueError, match="cut short"):
        sim.yearly(seasons)


def test_an_unknown_water_source_exports_the_rain_fed_case_with_the_irrigated_beside_it():
    """Owner's batch decisions item 8: keep it unknown; harvest/dry_days/event are 'if you can't water',
    the irrigated object is 'if you can water'."""
    assert sim.export_case("unknown") == "rain-fed"
    assert sim.export_case(None) == "rain-fed"


def _rules_with_fallback():
    return {"replay": {"rotation_unknown": ["rice", "potato"], "rotation_unknown_fields": ["demo"]}}


def test_a_set_rotation_is_used_as_it_is():
    rot, label = sim.rotation_for({"id": "kenya", "current_rotation": ["maize", "lentil"]}, _rules_with_fallback())
    assert rot == ["maize", "lentil"] and "PLACEHOLDER" not in label


def test_the_demo_field_falls_back_to_the_placeholder_rotation_labelled():
    rot, label = sim.rotation_for({"id": "demo", "current_rotation": None}, _rules_with_fallback())
    assert rot == ["rice", "potato"] and "PLACEHOLDER" in label


def test_any_other_field_without_a_rotation_stops():
    """Item 16: rice then potato means nothing for a field abroad; fail loudly (rule 12c)."""
    with pytest.raises(ValueError, match="current_rotation"):
        sim.rotation_for({"id": "kenya", "current_rotation": None}, _rules_with_fallback())


def test_the_rules_name_the_demo_as_the_only_fallback_field():
    from pipeline.fetch.rules import load_rules
    assert load_rules()["replay"]["rotation_unknown_fields"] == ["demo"]
