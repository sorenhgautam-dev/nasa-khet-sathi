"""Running a crop sequence through the bucket (step 4). Synthetic weather; crop values from crops.json."""
import itertools

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.twin import season as s
from pipeline.twin import soil_water as sw
from pipeline.twin.crops import kc_curve, season_length

LIB = load_crops()


def _weather(start="2015-10-01", end="2016-12-31", rain=3.0, et0=4.0):
    d = pd.date_range(start, end)
    return pd.DataFrame({"date": d, "et0_mm": et0, "rain_mm": rain})


SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200],
                     "theta_fc_m3m3": [0.32, 0.33, 0.33], "theta_wp_m3m3": [0.15, 0.20, 0.22]})
PLAN = [("wheat", "2015-11-15"), ("rice", "2016-06-25")]
CN = {"bare": 91, "wheat": 83, "rice": 83}
OPTS = dict(bare_kc=0.3, irrigated=False)


def test_simulate_returns_one_row_per_day_with_segments():
    daily, _ = s.simulate(_weather(), PLAN, LIB, SOIL, CN, **OPTS)
    assert len(daily) == len(_weather())
    runs = [k for k, _ in itertools.groupby(daily["segment"])]
    assert runs == ["bare", "wheat", "bare", "rice", "bare"]


def test_the_wheat_season_has_the_crops_json_length():
    daily, summary = s.simulate(_weather(), PLAN, LIB, SOIL, CN, **OPTS)
    w = summary["wheat"]
    assert w["start"] == "2015-11-15" and w["days"] == season_length(LIB["wheat"]["stages_days"])


def test_rice_harvest_uses_the_assumed_ky_and_says_it_is_assumed():
    _, summary = s.simulate(_weather(), PLAN, LIB, SOIL, CN, **OPTS)
    assert 0 <= summary["rice"]["harvest_pct"] <= 100
    assert "assumed" in summary["rice"]["harvest_note"] and summary["rice"]["ky_assumed"] is True


def test_irrigated_wheat_gets_water_whenever_dr_passes_raw_and_has_no_dry_days():
    _, summary = s.simulate(_weather(rain=0.0), PLAN, LIB, SOIL, CN, **{**OPTS, "irrigated": True})
    w = summary["wheat"]
    assert w["irrigation_mm"] > 0 and w["dry_days"] == 0 and w["harvest_pct"] == pytest.approx(100.0)
    for name, seg in summary["segments"].items():
        assert abs(seg["balance_residual_mm"]) < 1.0, name


def test_rain_fed_wheat_gets_no_irrigation():
    _, summary = s.simulate(_weather(rain=0.0), PLAN, LIB, SOIL, CN, **OPTS)
    assert summary["wheat"]["irrigation_mm"] == 0.0


def test_bare_soil_is_never_irrigated():
    daily, _ = s.simulate(_weather(rain=0.0), PLAN, LIB, SOIL, CN, **{**OPTS, "irrigated": True})
    assert daily.loc[daily["segment"] == "bare", "irrigation_mm"].sum() == 0.0


def test_wheat_gets_a_harvest_number_between_0_and_100():
    _, summary = s.simulate(_weather(rain=0.0), PLAN, LIB, SOIL, CN, **OPTS)
    assert 0 <= summary["wheat"]["harvest_pct"] < 100 and summary["wheat"]["dry_days"] > 0


@pytest.mark.parametrize("irrigated", [False, True])
def test_each_segment_balance_closes_within_1_mm(irrigated):
    rng = np.random.default_rng(5)
    w = _weather()
    w["rain_mm"] = rng.gamma(0.5, 12.0, len(w)) * (rng.random(len(w)) < 0.4)
    _, summary = s.simulate(w, PLAN, LIB, SOIL, CN, **{**OPTS, "irrigated": irrigated})
    for name, seg in summary["segments"].items():
        assert abs(seg["balance_residual_mm"]) < 1e-6, name


# --- H1: paddy water. Only an irrigated paddy is ponded; its pond water is irrigation (REVIEW_NOTES H1) ---

def test_rain_fed_paddy_gets_no_outside_water_and_is_the_ordinary_bucket():
    """Rain 1.5 mm every day never makes a 10-day dry spell, so the old rule kept rain-fed rice ponded and
    unstressed all season on outside water. Now it gets none: it is the plain bucket with rice's Zr and p."""
    w = _weather(rain=1.5)
    daily, summary = s.simulate(w, PLAN, LIB, SOIL, CN, **OPTS)
    r = summary["rice"]
    assert r["ponded_days"] == 0 and r["pond_supply_mm"] == 0.0 and r["irrigation_mm"] == 0.0
    assert r["dry_days"] > 0 and r["harvest_pct"] < 100.0
    rice = daily[daily["segment"] == "rice"]
    seg = w.iloc[rice.index[0]: rice.index[-1] + 1][["rain_mm", "et0_mm"]].copy()
    seg["kc"] = kc_curve(LIB["rice"]["stages_days"], LIB["rice"]["kc"])
    ref = sw.run_bucket(seg, taw_mm=rice["taw_mm"].iloc[0], p_table=LIB["rice"]["p"], cn=CN["rice"],
                        dr0_mm=daily.loc[rice.index[0] - 1, "dr_mm"])     # the bare spell before uses rice's Zr
    assert np.allclose(rice["eta_mm"].to_numpy(), ref["eta_mm"].to_numpy())


def test_irrigated_paddy_is_ponded_all_season_and_its_pond_water_is_irrigation():
    """Worked number, no rain: day 1 refills the depletion the rice season starts with, every later day
    refills yesterday's ETc. Pond water = starting depletion + sum of ETc - the last day's ETc."""
    daily, summary = s.simulate(_weather(rain=0.0), PLAN, LIB, SOIL, CN, **{**OPTS, "irrigated": True})
    r = summary["rice"]
    rice = daily[daily["segment"] == "rice"]
    dr_start = daily.loc[rice.index[0] - 1, "dr_mm"]
    assert dr_start > 0
    assert r["ponded_days"] == r["days"] and r["dry_days"] == 0 and r["harvest_pct"] == pytest.approx(100.0)
    assert r["pond_supply_mm"] == pytest.approx(dr_start + rice["etc_mm"].sum() - rice["etc_mm"].iloc[-1])
    assert r["irrigation_mm"] == pytest.approx(r["pond_supply_mm"])


# --- L2: overlapping crops are refused; a season cut short by the record's end gets no harvest number ---

def test_a_crop_sown_before_the_previous_crop_ends_is_refused():
    plan = [("wheat", "2015-11-15"), ("rice", "2016-03-01")]     # wheat (140 d) runs to 2016-04-02
    with pytest.raises(ValueError, match="before"):
        s.simulate(_weather(), plan, LIB, SOIL, CN, **OPTS)


def test_a_crop_sown_the_day_after_the_previous_one_ends_is_fine():
    end = pd.Timestamp("2015-11-15") + pd.Timedelta(season_length(LIB["wheat"]["stages_days"]), unit="D")
    daily, _ = s.simulate(_weather(), [("wheat", "2015-11-15"), ("rice", str(end.date()))], LIB, SOIL, CN, **OPTS)
    assert "rice" in set(daily["segment"])


def test_a_season_cut_short_by_the_end_of_the_record_gets_no_harvest_number():
    _, summary = s.simulate(_weather(end="2016-08-01"), PLAN, LIB, SOIL, CN, **OPTS)
    r, w = summary["rice"], summary["wheat"]
    assert r["days"] == 38                                       # 25 June to 1 August 2016, of 110 days
    assert r["complete"] is False and r["harvest_pct"] is None and "cut short" in r["harvest_note"]
    assert w["complete"] is True and w["harvest_pct"] is not None


# --- H4: crops the library cannot simulate are refused by name ---

@pytest.mark.parametrize("crop", ["buckwheat", "mustard"])
def test_a_crop_that_cannot_be_simulated_is_refused(crop):
    with pytest.raises(ValueError, match=f"{crop} cannot be simulated"):
        s.simulate(_weather(), [(crop, "2016-07-01")], LIB, SOIL, {**CN, crop: 83}, **OPTS)


def test_depletion_carries_over_as_a_fraction_between_segments():
    assert s.carry_over(30.0, 100.0, 200.0) == pytest.approx(60.0)


# --- build step 2a: FAO-56 surface-layer evaporation on bare days (bare_kc given as a setting dict) ---
from pipeline.twin import evaporation as ev  # noqa: E402

FAO56 = {"method": "fao56_surface_layer", "ze_m": 0.10, "tew_mm": 25.7, "rew_mm": 9.0, "kc_max": 1.20, "texture": "loam"}


@pytest.mark.parametrize("irrigated", [False, True])
def test_fao56_bare_soil_keeps_each_segment_balance_closed(irrigated):
    rng = np.random.default_rng(5)
    w = _weather()
    w["rain_mm"] = rng.gamma(0.5, 12.0, len(w)) * (rng.random(len(w)) < 0.4)
    daily, summary = s.simulate(w, PLAN, LIB, SOIL, CN, bare_kc=FAO56, irrigated=irrigated)
    for name, seg in summary["segments"].items():
        assert abs(seg["balance_residual_mm"]) < 1e-6, name
    bare = daily[daily["segment"] == "bare"]
    assert bare["irrigation_mm"].sum() == 0.0 and (bare["ks"] == 1.0).all() and bare["de_mm"].notna().all()


def test_fao56_bare_spell_starts_from_the_root_zones_relative_depletion():
    """rules.yaml bare_soil.de_start: De on a bare spell's first day = TEW x Dr / TAW of the depletion handed over."""
    daily, summary = s.simulate(_weather(rain=0.5), PLAN, LIB, SOIL, CN, bare_kc=FAO56, irrigated=False)
    i = daily.index[(daily["segment"] == "bare") & (daily.index > daily.index[daily["segment"] == "wheat"][-1])][0]
    taw = daily.loc[i, "taw_mm"]
    dr0 = s.carry_over(daily.loc[i - 1, "dr_mm"], daily.loc[i - 1, "taw_mm"], taw)
    assert daily.loc[i, "de_start_mm"] == pytest.approx(ev.de_start_mm(dr0, taw, 25.7))
    seg = summary["segments"]["bare_2"]
    assert seg["de_start_mm"] == pytest.approx(daily.loc[i, "de_start_mm"]) and seg["bare_method"] == "fao56_surface_layer"


def test_a_long_dry_fallow_hands_the_next_crop_a_wetter_profile_than_the_constant_kc():
    """No rain in the 12 weeks between wheat and rice: Kc 0.3 keeps drawing on rice's whole root zone; FAO-56's
    surface layer can give at most TEW (25.7 mm) beyond the depletion it starts from."""
    w = _weather(rain=0.0, et0=5.0)
    w.loc[w["date"] < "2016-03-01", "rain_mm"] = 6.0                   # wheat stays wet; the fallow is dry
    d_old, _ = s.simulate(w, PLAN, LIB, SOIL, CN, bare_kc=0.3, irrigated=False)
    d_new, sm = s.simulate(w, PLAN, LIB, SOIL, CN, bare_kc=FAO56, irrigated=False)
    i = d_new.index[d_new["segment"] == "rice"][0]
    assert d_new.loc[i - 1, "dr_mm"] < d_old.loc[i - 1, "dr_mm"]
    fallow = d_new[(d_new["segment"] == "bare") & (d_new.index < i) & (d_new["date"] > "2016-03-01")]
    assert fallow["eta_mm"].sum() <= 25.7 + 1e-9


def test_the_default_bare_soil_is_still_the_constant_kc_with_no_new_columns():
    daily, summary = s.simulate(_weather(), PLAN, LIB, SOIL, CN, **OPTS)
    bare = daily[daily["segment"] == "bare"]
    assert np.allclose(bare["etc_mm"], 0.3 * 4.0) and "de_mm" not in daily and "bare_method" not in summary["segments"]["bare_1"]


# --- proposal 2c (rules.yaml paddy_rainfed, PROPOSED, apply false): when rain-fed paddy can be transplanted ---
RULE_2C = {"prep_mm": 150.0, "prep_days": 30, "max_delay_days": 30}
PLAN_2C = [("rice", "2016-06-25"), ("wheat", "2016-10-20")]                 # rice (110 d) ends 12 Oct 2016


def _rain_from(first, mm, end="2017-06-30"):
    w = _weather(start="2016-01-01", end=end, rain=0.0)
    w.loc[w["date"] >= first, "rain_mm"] = mm
    return w


def test_enough_land_preparation_rain_keeps_the_planned_day():
    """10 mm a day from 1 June: 250 mm between 26 May (30 days before 25 June) and 25 June, more than 150 mm."""
    w = _rain_from("2016-06-01", 10.0)
    plan, info = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C)
    assert plan == PLAN_2C and info[0]["delay_days"] == 0 and info[0]["failed"] is False
    assert info[0]["prep_rain_mm"] == pytest.approx(250.0)


def test_late_rain_delays_transplanting_and_pushes_the_next_crop():
    """10 mm a day from 25 June: 150 mm is reached on 9 July (15 rainy days): 14 days late. Rice then ends 26 Oct,
    so wheat, planned for 20 Oct, moves to 27 Oct."""
    w = _rain_from("2016-06-25", 10.0)
    plan, info = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C)
    assert plan == [("rice", "2016-07-09"), ("wheat", "2016-10-27")]
    assert info[0]["delay_days"] == 14 and info[0]["transplanted"] == "2016-07-09" and not info[0]["failed"]


def test_too_little_rain_by_the_latest_day_fails_the_season_and_its_harvest_is_0():
    """5 mm a day from 1 July: 150 mm only on 30 July, 35 days late (more than 30): the season fails. It stays at its
    planned day (so the year keeps its crops) and paddy_outcome sets its harvest to 0."""
    w = _rain_from("2016-07-01", 5.0)
    plan, info = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C)
    assert plan == PLAN_2C and info[0]["failed"] is True and info[0]["prep_rain_mm"] == pytest.approx(5.0 * 25)
    _, summary = s.simulate(w, plan, LIB, SOIL, CN, **OPTS)
    seasons = s.paddy_outcome(summary["seasons"], info)
    rice = next(x for x in seasons if x["crop"] == "rice")
    assert rice["harvest_pct"] == 0.0 and "not transplanted" in rice["harvest_note"] and rice["transplant_failed"] is True
    wheat = next(x for x in seasons if x["crop"] == "wheat")
    assert wheat["harvest_pct"] == next(x for x in summary["seasons"] if x["crop"] == "wheat")["harvest_pct"]


def test_a_crop_pushed_past_the_end_of_the_record_is_dropped():
    w = _rain_from("2016-06-25", 10.0, end="2017-03-10")                    # wheat from 27 Oct needs to 15 Mar
    plan, info = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C)
    assert plan == [("rice", "2016-07-09")] and info[0]["dropped_after"] == ["wheat"]


def test_crops_that_are_not_paddy_are_left_alone():
    w = _rain_from("2016-12-01", 0.0)
    plan, info = s.paddy_transplant([("wheat", "2016-10-20")], w["date"], w["rain_mm"], LIB, RULE_2C)
    assert plan == [("wheat", "2016-10-20")] and info == []


def test_a_failed_paddy_pushed_by_an_earlier_late_crop_still_gets_harvest_0():
    """Rice 2016 is 14 days late, so wheat moves to 27 Oct and ends 15 Mar 2017; a (synthetic) rice planned for
    10 Mar 2017 must wait until 16 Mar, and with no rain in 2017 it fails: its harvest is 0 at the day it is kept."""
    w = _rain_from("2016-06-25", 10.0, end="2017-12-31")
    w.loc[w["date"] >= "2016-09-01", "rain_mm"] = 0.0
    plan = PLAN_2C + [("rice", "2017-03-10")]
    new, info = s.paddy_transplant(plan, w["date"], w["rain_mm"], LIB, RULE_2C)
    assert new[-1] == ("rice", "2017-03-16") and info[-1]["failed"] is True and info[-1]["start"] == "2017-03-16"
    _, summary = s.simulate(w, new, LIB, SOIL, CN, **OPTS)
    rice_2017 = [x for x in s.paddy_outcome(summary["seasons"], info) if x["crop"] == "rice"][-1]
    assert rice_2017["start"] == "2017-03-16" and rice_2017["harvest_pct"] == 0.0


# --- item 4a (rules.yaml season_dates, apply false): the farmer's sowing dates from the satellite's seasons ---
PLAN_4A = [("rice", "2016-06-23"), ("potato", "2016-10-30")]               # rice to 10 Oct; potato to 21 Feb 2017
MONSOON_2016 = {"start": "2016-07-01", "peak": "2016-08-20", "end": "2016-10-25"}
WINTER_2017 = {"start": "2017-01-07", "peak": "2017-03-18", "end": "2017-05-18"}


def test_a_detected_season_sets_sowing_at_green_up_minus_the_initial_stage():
    """Rice: green-up 1 Jul 2016 - 22 days (initial stage) = 9 Jun. Potato (harvested in 2017, the winter peak's
    year): 7 Jan 2017 - 25 days = 13 Dec 2016. Lengths stay the crop's own (110 and 115 days)."""
    new, info = s.plan_from_seasons(PLAN_4A, [MONSOON_2016, WINTER_2017], LIB, last_day="2017-12-31")
    assert new == [("rice", "2016-06-09"), ("potato", "2016-12-13")]
    assert [x["source"] for x in info] == ["hls", "hls"]
    assert info[0]["detected_minus_crop_days"] == (pd.Timestamp("2016-10-25") - pd.Timestamp("2016-07-01")).days + 1 - 110


def test_a_year_without_a_detected_season_keeps_the_calendar_date():
    new, info = s.plan_from_seasons(PLAN_4A, [WINTER_2017], LIB, last_day="2017-12-31")
    assert new == [("rice", "2016-06-23"), ("potato", "2016-12-13")] and info[0]["source"] == "calendar"


def test_a_season_in_another_slot_or_year_is_not_used():
    winter_2016 = {"start": "2016-01-07", "peak": "2016-03-18", "end": "2016-05-18"}     # potato of 2016, not 2017
    new, _ = s.plan_from_seasons(PLAN_4A, [winter_2016], LIB, last_day="2017-12-31")
    assert new == PLAN_4A


def test_an_overlap_moves_the_later_crop_to_the_day_after():
    """Rice green-up 1 Aug -> sown 10 Jul, ends 27 Oct; potato green-up 10 Nov -> 16 Oct, which overlaps: 28 Oct."""
    late_monsoon = {"start": "2016-08-01", "peak": "2016-09-10", "end": "2016-11-05"}
    early_winter = {"start": "2016-11-10", "peak": "2017-01-20", "end": "2017-03-01"}
    new, info = s.plan_from_seasons(PLAN_4A, [late_monsoon, early_winter], LIB, last_day="2017-12-31")
    assert new == [("rice", "2016-07-10"), ("potato", "2016-10-28")] and info[1]["moved_by_overlap"] is True


def test_a_season_pushed_past_the_record_is_dropped():
    new, info = s.plan_from_seasons(PLAN_4A, [MONSOON_2016, WINTER_2017], LIB, last_day="2017-03-31")
    assert new == [("rice", "2016-06-09")] and info[1]["dropped"] is True


def test_the_slot_of_a_crop_is_the_slot_of_its_calendar_seasons_middle():
    assert s.crop_slot("rice", "2016-06-23", LIB) == "monsoon"
    assert s.crop_slot("potato", "2016-10-30", LIB) == "winter" and s.crop_slot("wheat", "2016-11-15", LIB) == "winter"


# --- owner's decisions 2026-11-14: 4a and 4c together. A paddy dated by the satellite keeps its day (its real delay is
# already in the observation); only calendar-dated paddy seasons wait for the land-preparation rain ---
def test_a_satellite_dated_paddy_is_kept_as_it_is():
    w = _rain_from("2016-07-01", 5.0)                                        # would fail by the rule
    plan, info = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C, keep={("rice", "2016-06-25")})
    assert plan == PLAN_2C and info == []


def test_last_day_lets_a_season_run_past_the_rain_record():
    w = _rain_from("2016-06-25", 10.0, end="2017-03-10")
    plan, _ = s.paddy_transplant(PLAN_2C, w["date"], w["rain_mm"], LIB, RULE_2C, last_day="2017-06-30")
    assert plan == [("rice", "2016-07-09"), ("wheat", "2016-10-27")]
