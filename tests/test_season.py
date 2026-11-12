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
