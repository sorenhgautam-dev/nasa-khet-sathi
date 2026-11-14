"""The water a real paddy loses (owner's item 3, 2026-11-14; rules.yaml paddy_losses, off until switched on): seepage
and percolation (FAO Training Manual 4, sec. 4.4, Step 5: 'on average PERC = 5 mm/day') on the paddy's wet days, and
the puddling water before transplanting (Step 4: 'SAT = 200 mm'). Worked numbers by hand below."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.plans import twin_options as to
from pipeline.twin import season
from pipeline.twin import soil_water as sw

LIB = load_crops()


def test_step_takes_the_loss_from_the_drainage_first_then_from_the_root_zone():
    # dry day at field capacity: 0 - 2 + 4 + 5 = 7 mm depleted, all 5 mm of the loss from the root zone
    s = sw.step(0.0, 2.0, 0.0, 0.0, 4.0, 100.0, 0.24, loss_mm=5.0)
    assert (s["dr_mm"], s["dp_mm"], s["sp_mm"], s["eta_mm"]) == (7.0, 0.0, 5.0, 4.0)
    # wet day: 0 - 20 + 4 + 5 = -11: 11 mm drains (16 without the loss): the loss is the drainage, relabelled
    s = sw.step(0.0, 20.0, 0.0, 0.0, 4.0, 100.0, 0.24, loss_mm=5.0)
    assert (s["dr_mm"], s["dp_mm"], s["sp_mm"]) == (0.0, 11.0, 5.0)
    assert "sp_mm" not in sw.step(0.0, 20.0, 0.0, 0.0, 4.0, 100.0, 0.24)          # unchanged without the loss


def test_step_never_dries_past_the_wilting_point_the_loss_gives_way_first():
    # Ks = (100 - 98) / (0.76 x 100) = 0.0263, ETa 0.105; 98 + 0.105 + 5 = 103.105 > TAW 100: the 3.105 mm too much
    # comes off the loss (5 -> 1.895), not off ETa
    s = sw.step(98.0, 0.0, 0.0, 0.0, 4.0, 100.0, 0.24, loss_mm=5.0)
    k = 2.0 / 76.0
    assert s["dr_mm"] == 100.0 and s["eta_mm"] == pytest.approx(k * 4.0) and s["sp_mm"] == pytest.approx(2.0 - k * 4.0)


def _days(rain):
    return pd.DataFrame({"rain_mm": rain, "et0_mm": 4.0, "kc": 1.0})


def test_rainfed_paddy_loses_water_only_on_its_wet_days():
    """TAW 100, p 0.2 + 0.04 x (5 - 4) = 0.24 (RAW 24, Ks 1), CN 70 (Ia 21.8 mm: no runoff below it), PERC 5.
    Day 1 starts at field capacity (wet): 0 - 2 + 4 + 5 = 7. Day 2 starts at 7, rain 3 leaves 4 (not wet): 7 - 3 + 4 = 8.
    Day 3 starts at 8, rain 15 refills it (wet): 8 - 15 + 4 + 5 = 2. Day 4 starts at 2, no rain (not wet): 6.
    Balance: rain 20 = ETa 16 + losses 10 + drainage 0 - 6 (storage fell by 6)."""
    out = sw.run_bucket(_days([2.0, 3.0, 15.0, 0.0]), 100.0, 0.2, 70, sp_mm=5.0)
    assert out["dr_mm"].tolist() == [7.0, 8.0, 2.0, 6.0] and out["sp_mm"].tolist() == [5.0, 0.0, 5.0, 0.0]
    assert out["rain_mm"].sum() - out["eta_mm"].sum() - out["sp_mm"].sum() - out["dp_mm"].sum() == -6.0
    assert "sp_mm" not in sw.run_bucket(_days([2.0, 3.0]), 100.0, 0.2, 70).columns


def test_irrigated_paddy_top_up_replaces_the_loss_every_day():
    """Ponded every day: the morning refill brings the root zone back to field capacity, so every day is wet.
    No rain: day 1 0 + 4 + 5 = 9; days 2 and 3 refill 9 then lose 9 again. Irrigation 0 + 9 + 9 = 18 (ETc + PERC)."""
    out = sw.run_bucket(_days([0.0, 0.0, 0.0]), 100.0, 0.2, 70, ponded=np.ones(3, bool), sp_mm=5.0)
    assert out["irrigation_mm"].tolist() == [0.0, 9.0, 9.0] and out["dr_mm"].tolist() == [9.0, 9.0, 9.0]
    assert out["pond_supply_mm"].sum() == 18.0 and out["sp_mm"].sum() == 15.0


def test_land_preparation_water_of_a_watered_paddy():
    """FAO SAT 200 mm, of which the rain of the preparation days gave 120 and the pond's first refill 30: 50 mm more."""
    assert season.land_prep_irrigation_mm(200.0, 120.0, 30.0) == 50.0
    assert season.land_prep_irrigation_mm(200.0, 250.0, 0.0) == 0.0


SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200], "theta_fc_m3m3": [0.32, 0.33, 0.33],
                     "theta_wp_m3m3": [0.15, 0.20, 0.22], "sand_pct": [33.6, 30, 28], "clay_pct": [20.6, 25, 30]})
CN = {"bare": 91, "rice": 83, "potato": 85}


def _w():
    d = pd.date_range("2015-01-01", "2016-06-30")
    rain = [9.0 if x.month in (7, 8, 9) and x.day % 3 else (0.0 if x.month in (7, 8, 9) else 0.3) for x in d]
    return pd.DataFrame({"date": d, "et0_mm": 4.0, "rain_mm": rain})


def _rules(losses, prep=True):
    return {"bare_soil": {"kc": 0.3, "apply": False}, "kc_climate": {"apply": False},
            "season_dates": {"apply": False},
            "paddy_rainfed": {"apply": prep, "prep_mm": 150, "prep_days": 21, "max_delay_days": 30},
            "paddy_losses": {"apply": losses, "perc_mm_day": 5, "sat_mm": 200}}


def test_with_the_switch_on_the_rain_fed_rice_is_drier_and_the_balance_closes():
    """The seepage and percolation alone (no land-preparation rule, the same transplanting day)."""
    plan = [("rice", "2015-07-01"), ("potato", "2015-10-30")]
    off = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(False, prep=False), irrigated=False, plan=plan)
    on = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(True, prep=False), irrigated=False, plan=plan)
    r_off, r_on = (next(s for s in r["seasons"] if s["crop"] == "rice") for r in (off, on))
    assert r_on["sum_eta_mm"] < r_off["sum_eta_mm"] and r_on["seepage_percolation_mm"] > 0
    assert "seepage_percolation_mm" not in r_off
    assert max(abs(s["balance_residual_mm"]) for s in on["segments"].values()) < 1e-9


def test_with_the_switch_on_land_preparation_needs_fao_s_200_mm_counted_once():
    """2015: 9 mm on every day of July-September whose day number is not a multiple of 3, 0.3 mm a day before. Planned
    day 1 July, nursery 21 days before (10 June): 10-30 June give 6.3 mm. The 150-mm rule (Bouman) is met on the 16th wet
    day of July, 23 July (6.3 + 16 x 9 = 150.3 mm). FAO's 200 mm needs 22 wet days (204.3 mm), the 22nd being 1 August,
    after the latest day (1 July + 30 = 31 July, when the rain is 6.3 + 21 x 9 = 195.3 mm): the season fails, harvest 0.
    One threshold (FAO's replaces Bouman's), never the two added."""
    plan = [("rice", "2015-07-01"), ("potato", "2015-10-30")]
    off = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(False), irrigated=False, plan=plan)
    on = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(True), irrigated=False, plan=plan)
    assert off["paddy_info"][0]["transplanted"] == "2015-07-23"
    x = on["paddy_info"][0]
    assert x["failed"] is True and x["prep_rain_mm"] == pytest.approx(195.3)
    assert next(s for s in on["seasons"] if s["crop"] == "rice")["harvest_pct"] == 0.0


def test_watered_paddy_irrigation_grows_by_the_losses_and_the_land_preparation():
    plan = [("rice", "2015-07-01"), ("potato", "2015-10-30")]
    off = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(False), irrigated=True, plan=plan)
    on = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(True), irrigated=True, plan=plan)
    r_off, r_on = (next(s for s in r["seasons"] if s["crop"] == "rice") for r in (off, on))
    # the prep window (10-30 June) has 0.3 mm a day = 6.3 mm; the root zone starts the season full after a bare spell?
    assert r_on["land_prep_mm"] == pytest.approx(max(0.0, 200.0 - 6.3 - r_on["first_refill_mm"]))
    assert r_on["irrigation_mm"] == pytest.approx(r_on["pond_supply_mm"] + r_on["land_prep_mm"])
    assert r_on["pond_supply_mm"] > r_off["pond_supply_mm"] and r_on["harvest_pct"] == r_off["harvest_pct"] == 100.0
    assert max(abs(s["balance_residual_mm"]) for s in on["segments"].values()) < 1e-9
