"""The 2040 outlook (build step 9; rules.yaml future): delta change (pipeline/future/deltas.py) and the plan runs
(pipeline/future/runs.py). Worked numbers by hand below; saturation vapour pressures from FAO-56 eq. 11 (Annex 2,
Table 2.3: e0(15) = 1.705, e0(16) = 1.818, e0(25) = 3.168, e0(26) = 3.361 kPa)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import guards as g
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.rules import load_rules
from pipeline.future import deltas as dl
from pipeline.future import runs as ru
from pipeline.twin import inputs
from pipeline.twin.et0 import et0_mm

REPO = Path(__file__).resolve().parents[1]
LIB = load_crops()
RULES = load_rules()
SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200],
                     "theta_fc_m3m3": [0.32, 0.33, 0.33], "theta_wp_m3m3": [0.15, 0.20, 0.22]})
CN = {"bare": 91, "wheat": 83, "rice": 83, "potato": 85, "lentil": 81}


def _model_days(years, calendar, value):
    """Synthetic model days (one model, one experiment): value(month) per day."""
    rows = []
    for y in years:
        for m in range(1, 13):
            n = 30 if calendar == "360_day" else pd.Period(f"2001-{m:02d}").days_in_month   # noleap: Feb 28
            rows += [(y, m, d, value(m)) for d in range(1, n + 1)]
    return pd.DataFrame(rows, columns=["year", "month", "day", "v"])


def _daily(calendar, hist_pr, fut_pr, hist_t, fut_t):
    h = _model_days([1995, 1996], calendar, hist_pr).rename(columns={"v": "pr_mm"})
    h["tasmax_c"] = _model_days([1995, 1996], calendar, hist_t)["v"]
    h["tasmin_c"] = h["tasmax_c"] - 10
    f = _model_days([2026, 2027], calendar, fut_pr).rename(columns={"v": "pr_mm"})
    f["tasmax_c"] = _model_days([2026, 2027], calendar, fut_t)["v"]
    f["tasmin_c"] = f["tasmax_c"] - 10 + 0.5
    return pd.concat([h.assign(experiment="historical"), f.assign(experiment="ssp245")]).assign(model="M", calendar=calendar)


PERIODS = {"historical": [1995, 1996], "future": [2026, 2027]}


def test_temperature_change_is_a_monthly_difference():
    d = _daily("noleap", lambda m: 2.0, lambda m: 2.0, lambda m: 10.0 + m, lambda m: 10.0 + m + (1.5 if m == 7 else 0.0))
    c = dl.model_change(d, "M", "ssp245", PERIODS, window_months=3)
    assert c["dtmax_c"][7] == pytest.approx(1.5) and c["dtmax_c"][1] == pytest.approx(0.0)
    assert all(v == pytest.approx(0.5 + (1.5 if m == 7 else 0.0)) for m, v in c["dtmin_c"].items())


def test_rain_ratio_pools_the_three_months_centred_on_each_month():
    # history 2 mm every day but 4 mm in January; future 8 mm in January (noleap calendar)
    d = _daily("noleap", lambda m: 4.0 if m == 1 else 2.0, lambda m: 8.0 if m == 1 else 2.0, lambda m: 20.0, lambda m: 20.0)
    r = dl.model_change(d, "M", "ssp245", PERIODS, window_months=3)["rain_ratio"]
    assert r[1] == pytest.approx(366 / 242)      # Dec+Jan+Feb: (62 + 248 + 56) / (62 + 124 + 56) = 1.5124
    assert r[2] == pytest.approx(366 / 242)      # Jan+Feb+Mar: (248 + 56 + 62) / (124 + 56 + 62)
    assert r[12] == pytest.approx(370 / 246)     # Nov+Dec+Jan: (60 + 62 + 248) / (60 + 62 + 124) = 1.5041
    assert r[6] == pytest.approx(1.0)
    d360 = _daily("360_day", lambda m: 4.0 if m == 1 else 2.0, lambda m: 8.0 if m == 1 else 2.0, lambda m: 20.0, lambda m: 20.0)
    assert dl.model_change(d360, "M", "ssp245", PERIODS, 3)["rain_ratio"][1] == pytest.approx(360 / 240)  # 30-day months
    assert dl.model_change(d, "M", "ssp245", PERIODS, 1)["rain_ratio"][1] == pytest.approx(2.0)          # own month only


def test_a_period_with_a_missing_year_or_no_rain_is_refused():
    d = _daily("noleap", lambda m: 2.0, lambda m: 2.0, lambda m: 20.0, lambda m: 20.0)
    with pytest.raises(ValueError):
        dl.model_change(d[d["year"] != 1996], "M", "ssp245", PERIODS, 3)
    dry = _daily("noleap", lambda m: 0.0 if m in (12, 1, 2) else 2.0, lambda m: 2.0, lambda m: 20.0, lambda m: 20.0)
    with pytest.raises(ValueError):
        dl.model_change(dry, "M", "ssp245", PERIODS, 3)   # no historical rain in the window: no ratio


def _weather(n_days=730, tmax=25.0, tmin=15.0, rh=60.0, rain=3.0, tmin_corr=None):
    d = pd.date_range("2001-01-01", periods=n_days)
    w = pd.DataFrame({"date": d, "tmin_c_power": tmin, "tmax_c_power": tmax, "tmin_c": tmin if tmin_corr is None else tmin_corr,
                      "tmax_c": tmax, "tmin_frost_c": tmin - 1.0, "rh_pct": rh, "ws2m_ms": 2.0, "rs_mj_m2_day": 18.0,
                      "rain_mm": rain, "rain_uncorrected_mm": rain * 1.5, "rain_source": "gpm"})
    ea, cap = inputs.ea_held_from_power_kpa(w["rh_pct"], w["tmax_c_power"], w["tmin_c_power"], w["tmin_c"])
    w["ea_kpa"], w["ea_capped"] = ea, cap
    args = (w["tmax_c"], w["tmin_c"], w["ws2m_ms"], w["rs_mj_m2_day"], 1325.0, 27.69, w["date"].dt.day_of_year)
    w["et0_mm"], w["et0_rh_held_mm"] = et0_mm(*args, ea=ea), et0_mm(*args, rh_mean=w["rh_pct"])
    return w


def test_no_change_reproduces_the_weather_table_as_weather_py_builds_it():
    w = _weather(tmin_corr=12.0)
    out = dl.apply_change(w, dl.uniform_change(0.0, 1.0), elev_m=1325.0, lat_deg=27.69)
    for c in ("et0_mm", "et0_rh_held_mm", "ea_kpa", "rain_mm", "tmax_c", "tmin_c"):
        assert np.allclose(out[c].to_numpy(float), w[c].to_numpy(float), rtol=0, atol=1e-12), c


def test_warming_holds_relative_humidity_so_vapour_pressure_follows():
    w = _weather()
    out = dl.apply_change(w, dl.uniform_change(1.0, 1.0), elev_m=1325.0, lat_deg=27.69)
    # 60% x (e0(26) + e0(16)) / 2 = 0.6 x (3.361 + 1.818) / 2 = 1.554 kPa (was 0.6 x (3.168 + 1.705) / 2 = 1.462)
    assert out["ea_kpa"].iloc[0] == pytest.approx(1.554, abs=0.001)
    assert w["ea_kpa"].iloc[0] == pytest.approx(1.462, abs=0.001)
    assert (out["tmax_c"] == 26.0).all() and (out["tmin_c"] == 16.0).all() and (out["tmin_frost_c"] == 15.0).all()
    assert (out["tmax_c_power"] == 26.0).all() and (out["tmin_c_power"] == 16.0).all()
    exp = et0_mm(26.0, 16.0, 2.0, 18.0, 1325.0, 27.69, 1, ea=out["ea_kpa"].iloc[0])
    assert out["et0_mm"].iloc[0] == pytest.approx(exp, rel=1e-12)
    assert (out["et0_mm"] > w["et0_mm"]).all()                    # warmer days use more water


def test_the_vapour_pressure_cap_follows_the_shifted_corrected_tmin():
    w = _weather(rh=95.0, tmin_corr=10.0)                          # POWER's ea above e0 of the corrected Tmin: capped
    out = dl.apply_change(w, dl.uniform_change(2.0, 1.0), elev_m=1325.0, lat_deg=27.69)
    assert out["ea_capped"].all()
    assert out["ea_kpa"].iloc[0] == pytest.approx(0.6108 * np.exp(17.27 * 12.0 / (12.0 + 237.3)))   # e0(12 C) = 1.403 kPa


def test_rain_ratio_scales_both_rain_versions_by_month():
    w = _weather()
    ch = dl.uniform_change(0.0, 1.0)
    ch["rain_ratio"][1] = 1.2
    out = dl.apply_change(w, ch, elev_m=1325.0, lat_deg=27.69)
    jan = out["date"].dt.month == 1
    assert np.allclose(out.loc[jan, "rain_mm"], 3.6) and out.loc[~jan, "rain_mm"].eq(3.0).all()
    assert np.allclose(out.loc[jan, "rain_uncorrected_mm"], 5.4)
    assert out["rain_source"].eq("gpm").all()                     # flags and sources are untouched


def test_guards_stop_a_change_that_breaks_the_weather():
    w = _weather(tmax=16.0, tmin=15.0)
    ch = dl.uniform_change(0.0, 1.0)
    ch["dtmin_c"] = {m: 1.5 for m in range(1, 13)}                 # Tmin would pass Tmax: never clipped
    with pytest.raises(g.DataGuardError):
        dl.apply_change(w, ch, elev_m=1325.0, lat_deg=27.69)
    with pytest.raises(g.DataGuardError):                          # 300 mm x 1.8 = 540 mm in a day
        dl.apply_change(_weather(rain=300.0), dl.uniform_change(0.0, 1.8), elev_m=1325.0, lat_deg=27.69)
    with pytest.raises(ValueError):                                # a month without a change
        dl.apply_change(w, {"dtmax_c": {1: 0.0}, "dtmin_c": {1: 0.0}, "rain_ratio": {1: 1.0}}, 1325.0, 27.69)


def test_spread_is_median_lowest_and_highest_run():
    s = ru.spread([{"run": "a", "harvest": 70.0}, {"run": "b", "harvest": 80.0}, {"run": "c", "harvest": 75.0},
                   {"run": "d", "harvest": 90.0}], "harvest")
    assert (s["median"], s["low"], s["high"], s["n"]) == (77.5, 70.0, 90.0, 4)
    assert (s["low_run"], s["high_run"]) == ("a", "d")


def _wx(years=8, rain_winter=0.0):
    d = pd.date_range("2001-01-01", periods=365 * years + years // 4 + 1)
    rain = np.where(d.month.isin([6, 7, 8, 9]), 12.0, rain_winter)
    return pd.DataFrame({"date": d, "et0_mm": 3.5, "rain_mm": rain, "ws2m_ms": 2.0, "ea_kpa": 1.5, "tmax_c": 25.0})


SPECS = [{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "wheat", "window": 0, "position": "end"}]


def test_plan_run_matches_run_plans_evaluate():
    sys.path.insert(0, str(REPO / "scripts"))
    from run_plans import evaluate
    w = _wx()
    r = ru.plan_run(SPECS, w, LIB, SOIL, CN, RULES)
    e = evaluate(SPECS, w, LIB, SOIL, CN, RULES, 1.0)
    assert r["harvest"] == e["harvest"] and r["stability"] == e["stability"] and r["years"] == e["years"]
    assert r["irrigation_mm"] == pytest.approx(e["irrigation_mm"], abs=0.05)
    assert r["dry_days"] == e["dry_days"]


def test_a_dry_winter_lowers_rain_fed_wheat_and_raises_the_water_it_needs():
    wet, dry = ru.plan_run(SPECS, _wx(rain_winter=3.0), LIB, SOIL, CN, RULES), ru.plan_run(SPECS, _wx(), LIB, SOIL, CN, RULES)
    assert dry["harvest"] < wet["harvest"] and dry["dry_days"] > wet["dry_days"]
    assert dry["irrigation_mm"] > wet["irrigation_mm"]
    assert 0 <= dry["harvest"] <= 100


def test_plausibility_compares_our_median_with_a_published_range():
    ours = {"ssp245": {"annual_dtas_c": {"median": 0.9}, "annual_rain_change_pct": {"median": 12.0}}}
    ref = {"ssp245": {"dtas_c": [0.5, 1.2], "rain_change_pct": [-5.0, 10.0]}}
    c = dl.compare_published(ours, ref)
    assert c["ssp245"]["dtas_c"] == {"ours": 0.9, "published": [0.5, 1.2], "inside": True}
    assert c["ssp245"]["rain_change_pct"]["inside"] is False
    assert c["all_inside"] is False


def test_plan_run_follows_the_bare_soil_switch_as_run_plans_does():
    """With rules.yaml bare_soil.apply on (FAO-56's surface layer, pipeline/twin/evaporation.py) both give the same."""
    import copy
    sys.path.insert(0, str(REPO / "scripts"))
    from run_plans import evaluate
    rules_on = copy.deepcopy(RULES)
    rules_on["bare_soil"]["apply"] = True
    soil = SOIL.assign(sand_pct=33.6, clay_pct=20.6)
    w = _wx()
    on, off = ru.plan_run(SPECS, w, LIB, soil, CN, rules_on), ru.plan_run(SPECS, w, LIB, soil, CN, RULES)
    e = evaluate(SPECS, w, LIB, soil, CN, rules_on, 1.0)
    assert on["harvest"] == e["harvest"] and on["dry_days"] == e["dry_days"]
    assert on["irrigation_mm"] == pytest.approx(e["irrigation_mm"], abs=0.05)
    assert on != off                                              # the switch reaches the outlook
