"""The twin's three switches applied the same way by every runner (pipeline/plans/twin_options.py): rules.yaml bare_soil
(2a), season_dates (4a) and paddy_rainfed (4c). Synthetic weather; crop values from crops.json."""
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.plans import simulate as sim
from pipeline.plans import twin_options as to

LIB = load_crops()
SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200], "theta_fc_m3m3": [0.32, 0.33, 0.33],
                     "theta_wp_m3m3": [0.15, 0.20, 0.22], "sand_pct": [33.6, 30, 28], "clay_pct": [20.6, 25, 30]})
CN = {"bare": 91, "rice": 83, "potato": 85, "wheat": 83}
PLAN = [("rice", "2015-06-23"), ("potato", "2015-10-30"), ("rice", "2016-06-23"), ("potato", "2016-10-30")]
SEASONS = [{"start": "2016-07-01", "peak": "2016-08-20", "end": "2016-10-25"}]              # monsoon 2016 only


def _w():
    d = pd.date_range("2015-01-01", "2017-06-30")
    rain = [8.0 if (x.month in (7, 8, 9) and not (x.year == 2015 and x.month == 7 and x.day < 25)) else 0.5 for x in d]
    return pd.DataFrame({"date": d, "et0_mm": 4.0, "rain_mm": rain})


def _rules(dates=False, paddy=False):
    return {"bare_soil": {"kc": 0.3, "apply": False}, "kc_climate": {"apply": False},
            "season_dates": {"apply": dates}, "paddy_rainfed": {"apply": paddy, "prep_mm": 150, "prep_days": 21, "max_delay_days": 30}}


def test_with_every_switch_off_it_is_the_plain_replay():
    r = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(), irrigated=False, plan=PLAN, farmer=True, seasons=SEASONS)
    p = sim.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, bare_kc=0.3, irrigated=False, plan=PLAN)
    assert [y["harvest"] for y in r["years"]] == [y["harvest"] for y in p["years"]] and r["plan"] == PLAN


def test_season_dates_move_only_the_farmers_plan_in_years_with_a_season():
    r = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(dates=True), irrigated=True, plan=PLAN, farmer=True, seasons=SEASONS)
    assert r["plan"][2] == ("rice", "2016-06-09") and r["plan"][0] == ("rice", "2015-06-23")      # 1 Jul - 22 days
    s = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(dates=True), irrigated=True, plan=PLAN, farmer=False, seasons=SEASONS)
    assert s["plan"] == PLAN                                                                       # a suggested plan


def test_the_paddy_rule_waits_for_rain_on_calendar_days_and_keeps_satellite_days():
    """2015: rain of 8 mm a day starts 25 Jul; land preparation (150 mm since 2 Jun) is reached on 9 Aug: 47 days late,
    more than 30, so the 2015 rice fails (harvest 0). 2016's rice is dated by the satellite and kept."""
    r = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(dates=True, paddy=True), irrigated=False, plan=PLAN,
                  farmer=True, seasons=SEASONS)
    rice = [x for x in r["seasons"] if x["crop"] == "rice"]
    assert rice[0]["harvest_pct"] == 0.0 and rice[0]["transplant_failed"] is True
    assert rice[1]["start"] == "2016-06-09" and "transplant_failed" not in rice[1]


def test_the_paddy_rule_never_touches_the_watered_case():
    r = to.replay(_w(), ["rice", "potato"], LIB, SOIL, CN, _rules(paddy=True), irrigated=True, plan=PLAN)
    assert r["plan"] == PLAN and all("transplant_failed" not in x for x in r["seasons"])


def test_a_plan_is_the_farmers_when_its_id_is_attached():
    rules = _rules(dates=True)
    to.attach(rules, SEASONS, ["rice.w1.middle+potato.w0.middle"])
    assert to.is_farmer([{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "potato", "window": 0, "position": "middle"}], rules)
    assert not to.is_farmer([{"crop": "rice", "window": 0, "position": "end"}, {"crop": "potato", "window": 0, "position": "middle"}], rules)
    assert to.seasons_of(rules) == SEASONS


def test_future_plan_run_and_run_plans_evaluate_agree_with_every_switch_on():
    """pipeline/future/runs.plan_run and scripts/run_plans.evaluate give the same numbers when the farmer's plan takes the
    satellite's dates (4a) and rain-fed paddy waits for its land-preparation rain (4c)."""
    import sys
    from pathlib import Path

    import numpy as np

    from pipeline.fetch.rules import load_rules
    from pipeline.future import runs as ru
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from run_plans import evaluate
    d = pd.date_range("2001-01-01", "2006-12-31")
    w = pd.DataFrame({"date": d, "et0_mm": 3.5, "rain_mm": np.where(d.month.isin([7, 8, 9]), 12.0, 0.3),
                      "ws2m_ms": 2.0, "ea_kpa": 1.5, "tmax_c": 25.0})
    specs = [{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "wheat", "window": 0, "position": "end"}]
    rules = load_rules()
    rules["season_dates"] = {**rules.get("season_dates", {}), "apply": True}
    rules["paddy_rainfed"] = {**rules["paddy_rainfed"], "apply": True}
    to.attach(rules, [{"start": "2004-07-10", "peak": "2004-08-25", "end": "2004-10-20"}], {"rice.w1.middle+wheat.w0.end"})
    cn = {"bare": 91, "wheat": 83, "rice": 83}
    r, e = ru.plan_run(specs, w, LIB, SOIL, cn, rules), evaluate(specs, w, LIB, SOIL, cn, rules, 1.0)
    assert r["years"] == e["years"] and r["harvest"] == pytest.approx(e["harvest"]) and r["stability"] == pytest.approx(e["stability"])
    rf = to.replay(w, ["rice", "wheat"], LIB, SOIL, cn, rules, irrigated=False,
                   plan=sim.rotation_plan(["rice", "wheat"], LIB, w["date"].min(), w["date"].max()), farmer=True)
    assert rf["season_dates"] and rf["paddy_info"]                         # both switches did something
