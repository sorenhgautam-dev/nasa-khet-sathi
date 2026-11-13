"""Build step 10: the scalar Kalman update (CLAUDE.md "Probe fusion") and the numbers it needs (rules.yaml probe.kalman).
Every expected number below is worked by hand in the comment beside it."""
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.twin import kalman as kf


# ---------- predict, update, sure ----------

def test_update_hand_worked():
    # K = 100 / (100 + 25) = 0.8; x = 60 + 0.8 x (40 - 60) = 44; P = (1 - 0.8) x 100 = 20
    x, p, k = kf.update(60.0, 100.0, 40.0, 25.0)
    assert k == pytest.approx(0.8) and x == pytest.approx(44.0) and p == pytest.approx(20.0)


def test_a_second_update_hand_worked():
    # from (44, 20): K = 20 / 45 = 0.4444; x = 44 + 0.4444 x (40 - 44) = 42.2222; P = 0.5556 x 20 = 11.1111
    x, p, k = kf.update(44.0, 20.0, 40.0, 25.0)
    assert k == pytest.approx(4 / 9) and x == pytest.approx(42.22222, abs=1e-5) and p == pytest.approx(11.11111, abs=1e-5)


def test_sure_hand_worked():
    # 1 - sqrt(20) / sqrt(400) = 1 - 4.47214 / 20 = 0.776393
    assert kf.sure(20.0, 400.0) == pytest.approx(0.776393, abs=1e-6)
    assert kf.sure(100.0, 400.0) == pytest.approx(0.5)          # 1 - 10/20
    assert kf.sure(400.0, 400.0) == 0.0
    assert kf.sure(900.0, 400.0) == 0.0                         # clamped: never below 0
    assert kf.sure(0.0, 400.0) == 1.0


def test_predict_hand_worked():
    assert kf.predict(20.0, 2.5) == pytest.approx(22.5)          # one day
    assert kf.predict(20.0, 2.5, days=4) == pytest.approx(30.0)  # 20 + 4 x 2.5
    assert kf.predict(95.0, 2.5, days=4, cap=100.0) == 100.0     # 105 capped at 100


@pytest.mark.parametrize("args", [(60.0, -1.0, 40.0, 25.0), (60.0, 100.0, 40.0, -5.0), (60.0, 0.0, 40.0, 0.0)])
def test_update_refuses_impossible_variances(args):
    with pytest.raises(ValueError):
        kf.update(*args)


def test_sure_needs_a_positive_p0():
    with pytest.raises(ValueError):
        kf.sure(1.0, 0.0)


# ---------- one session = one measurement (rules.yaml probe.kalman.one_session_one_measurement) ----------

def test_a_session_is_one_measurement_from_the_prior():
    # z = median(38, 40, 45) = 40; from the prior (60, 100) with R 25: x 44, P 20, sure 0.776393; before: 1 - 10/20 = 0.5
    f = kf.fuse_session(60.0, 100.0, 400.0, [38.0, 40.0, 45.0], 25.0)
    assert f["z"] == 40.0 and f["z_used"] == 40.0 and not f["z_limited"]
    assert f["wetness"] == pytest.approx(44.0) and f["var"] == pytest.approx(20.0)
    assert f["sure"] == pytest.approx(0.776393, abs=1e-6) and f["sure_before"] == pytest.approx(0.5)
    # thirty equal lines do not stack: the answer is the same as for one line
    g = kf.fuse_session(60.0, 100.0, 400.0, [40.0] * 30, 25.0)
    assert g["var"] == pytest.approx(20.0) and g["sure"] == pytest.approx(f["sure"])


def test_a_reading_wetter_than_field_capacity_is_limited_and_flagged():
    # z 120 -> 100 for the update: x = 60 + 0.8 x 40 = 92
    f = kf.fuse_session(60.0, 100.0, 400.0, [120.0], 25.0)
    assert f["z"] == 120.0 and f["z_used"] == 100.0 and f["z_limited"] and f["wetness"] == pytest.approx(92.0)


def test_the_prior_ages_after_its_as_of_day():
    # rules.yaml probe.kalman.age_after_as_of: P = min(prior + Q x days, P0)
    assert kf.aged_prior_var(100.0, 5.0, 400.0, 0) == 100.0
    assert kf.aged_prior_var(100.0, 5.0, 400.0, 11) == pytest.approx(155.0)    # 100 + 11 x 5
    assert kf.aged_prior_var(100.0, 5.0, 400.0, 100) == 400.0                  # capped at P0
    with pytest.raises(ValueError):
        kf.aged_prior_var(100.0, 5.0, 400.0, -1)


# ---------- P0, anomalies and the SMAP comparison ----------

def _yearly(values_by_year, start="2001-01-01", end="2003-12-31", trend_per_day=0.0):
    d = pd.date_range(start, end)
    base = np.array([values_by_year[y] for y in d.year], dtype=float)
    return pd.Series(base + trend_per_day * d.dayofyear.to_numpy(), index=d)


def test_p0_is_the_variance_across_years_for_this_time_of_year():
    # 50, 60, 70 in 2001-2003: sample variance (n - 1) = ((-10)^2 + 0 + 10^2) / 2 = 100 on every calendar day
    s = _yearly({2001: 50.0, 2002: 60.0, 2003: 70.0})
    assert kf.p0_var(s, "2026-07-01", (2001, 2003), 15) == pytest.approx(100.0)


def test_p0_leaves_the_seasons_change_inside_the_window_out():
    # the same 0.5-a-day rise every year adds nothing across years: still 100 (pooling the 31 days would add to it)
    s = _yearly({2001: 50.0, 2002: 60.0, 2003: 70.0}, trend_per_day=0.5)
    assert kf.p0_var(s, "2026-07-01", (2001, 2003), 15) == pytest.approx(100.0)


def test_anomalies_remove_each_calendar_days_mean():
    # a constant per year: the anomaly is the year's value minus the mean of the years, 60 -> -10, 0, +10
    s = _yearly({2001: 50.0, 2002: 60.0, 2003: 70.0})
    a = kf.anomalies(s, 15)
    assert a["2001-06-15"] == pytest.approx(-10.0) and a["2002-06-15"] == pytest.approx(0.0)
    assert a["2003-06-15"] == pytest.approx(10.0) and a["2001-01-01"] == pytest.approx(-10.0)


def test_smap_fit_hand_worked():
    # a_t = [1,2,3,4], a_s = [1,3,2,4]: deviations (-1.5,-0.5,0.5,1.5), (-1.5,0.5,-0.5,1.5); Sxy = 4, Sxx = Syy = 5
    # r = 0.8, rho = 1 - r^2 = 0.36, k = 0.8; residual d = (-0.3,-0.9,0.9,0.3), sum d^2 = 1.8 (= 0.36 x 5)
    # phi = [(-0.3)(-0.9) + (-0.9)(0.9) + (0.9)(0.3)] / 1.8 = -0.27 / 1.8 = -0.15
    f = kf.smap_fit(np.array([1.0, 2, 3, 4]), np.array([1.0, 3, 2, 4]))
    assert f["r"] == pytest.approx(0.8) and f["rho"] == pytest.approx(0.36) and f["k"] == pytest.approx(0.8)
    assert f["phi"] == pytest.approx(-0.15)


def test_kalman_numbers_hand_worked():
    # P0 400, rho 0.36 -> prior 144, sure_prior 1 - sqrt(144/400) = 1 - 0.6 = 0.4; phi -0.15 -> Q = 144 x 0.9775 = 140.76
    n = kf.kalman_numbers(400.0, {"r": 0.8, "rho": 0.36, "k": 0.8, "phi": -0.15})
    assert n["prior_var"] == pytest.approx(144.0) and n["sure_prior"] == pytest.approx(0.4)
    assert n["q_var_per_day"] == pytest.approx(140.76)


def test_prior_from_smap_aligns_the_shared_days_only():
    # twin 2001-2004, SMAP 2002-2005; shared 2002-2004 (365 + 365 + 366 days). SMAP's anomalies are 0.001 x the twin's:
    # r = 1, nothing is left over (rho 0, so the prior variance and Q are 0)
    tw = _yearly({2001: 40.0, 2002: 50.0, 2003: 60.0, 2004: 70.0}, end="2004-12-31")
    sm = 0.2 + 0.001 * _yearly({2002: 50.0, 2003: 60.0, 2004: 70.0, 2005: 99.0}, start="2002-01-01", end="2005-12-31")
    f = kf.prior_from_smap(tw, sm, 15)
    assert f["n_days"] == 1096 and f["first"] == "2002-01-01" and f["last"] == "2004-12-31"
    assert f["r"] == pytest.approx(1.0) and f["rho"] == pytest.approx(0.0, abs=1e-12)
    assert kf.kalman_numbers(400.0, f)["q_var_per_day"] == pytest.approx(0.0, abs=1e-9)


# ---------- the twin's state on the as-of day ----------

LIB = load_crops()
CURRENT = [{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "potato", "window": 0, "position": "middle"}]


def test_the_plan_runs_through_the_as_of_day_with_the_crop_in_the_ground():
    # rice 23 Jun - 10 Oct, potato sown 30 Oct (plans.json spans): on 3 Nov 2026 the potato is in its 5th day
    plan = kf.plan_through(CURRENT, LIB, "2001-01-01", "2026-11-03")
    assert plan[0] == ("rice", "2001-06-23") and plan[-1] == ("potato", "2026-10-30") and plan[-2] == ("rice", "2026-06-23")
    assert kf.plan_through(CURRENT, LIB, "2001-01-01", "2026-10-29")[-1] == ("rice", "2026-06-23")


def test_state_on_the_last_day_hand_worked():
    # Dr 30, TAW 120, RAW 42: Ks 1 (30 <= 42), wetness 100 x (1 - 30/120) = 75
    d = pd.DataFrame({"date": pd.to_datetime(["2026-10-29", "2026-10-30", "2026-10-31"]),
                      "segment": ["bare", "potato", "potato"], "crop": [None, "potato", "potato"],
                      "dr_mm": [20.0, 25.0, 30.0], "taw_mm": [150.0, 120.0, 120.0], "raw_mm": [60.0, 42.0, 42.0]})
    s = kf.state_on_last_day(d)
    assert s["date"] == "2026-10-31" and s["crop"] == "potato" and s["crop_sown"] == "2026-10-30" and s["crop_day"] == 2
    assert s["ks"] == 1.0 and s["wetness_pct"] == pytest.approx(75.0)
    # Dr 90: Ks = (120 - 90) / (120 - 42) = 30 / 78 = 0.384615; wetness 25
    d.loc[2, "dr_mm"] = 90.0
    s = kf.state_on_last_day(d)
    assert s["ks"] == pytest.approx(0.384615, abs=1e-6) and s["wetness_pct"] == pytest.approx(25.0)


def test_bare_ground_is_named_bare():
    d = pd.DataFrame({"date": pd.to_datetime(["2026-10-12"]), "segment": ["bare"], "crop": [None],
                      "dr_mm": [10.0], "taw_mm": [150.0], "raw_mm": [60.0]})
    s = kf.state_on_last_day(d)
    assert s["crop"] == "bare" and s["crop_sown"] is None and s["crop_day"] is None
    assert math.isclose(s["wetness_pct"], 100 * (1 - 10 / 150))
