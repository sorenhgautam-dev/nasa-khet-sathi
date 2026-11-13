"""Plain words per plan (build step 7; pipeline/plans/explain.py): which template lines a plan gets, from its numbers."""
import json

import pytest

from pipeline.plans import explain as ex
from pipeline.words.texts import load

LIB = json.load(open("config/crops.json"))["crops"]
WORDS = {"tabs": load("tabs"), "shared": load("screens")["shared"]}


def _plan(pid, crops, score, **kw):
    return {"id": pid, "crops": [{"crop": c, "start": s, "end": e} for c, s, e in crops], "score": score, **kw}


CUR = _plan("current", [("rice", "06-23", "10-10"), ("potato", "10-30", "02-21")],
            {"harvest": 72.3, "water": 38.2, "cover": 61.6, "soil_kept": 73.6}, pest_break=1, windows=[None, None], stability=65.7,
            thirsty={"rice": {"month": 9, "dry_days_per_year": 6.0}, "potato": {"month": 1, "dry_days_per_year": 20.0}})
GAP = _plan("cover_gap", [("rice", "06-15", "10-02"), ("wheat", "10-15", "03-03")],
            {"harvest": 89.6, "water": 50.8, "cover": 68.5, "soil_kept": 74.4}, pest_break=0,
            needs_water_window=True, windows=[None, "Irrigated Condition"],
            score_uncorrected_rain={"harvest": 93.0, "water": 55.0, "cover": 68.5, "soil_kept": 72.4})
SAFE = _plan("safest", [("rice", "06-15", "10-02"), ("lentil", "10-15", "02-24")],
             {"harvest": 80.8, "water": 44.5, "cover": 66.6, "soil_kept": 74.2}, pest_break=1, windows=[None, None],
             stability=75.6)
DIARY = {"shift_days": None, "bare_days": 62, "groundwater": {"direction": "falling"},
         "months": [{"frost": "risk", "cover": "crop"}] + [{"frost": "none", "cover": "crop"}] * 9
         + [{"frost": "none", "cover": "bare"}] * 2}                  # the satellite: bare in November and December
TIPS = {"thirsty_min_dry_days_per_year": 5, "thirsty_skip_crops": ["rice"]}
YEARS = [{"year": y, "event": "drought" if y in (2009, 2013) else "none"} for y in range(2002, 2026)]
CTX = {"diary": DIARY, "replay": {"current": YEARS, "cover_gap": YEARS, "safest": YEARS}, "water_source_unknown": True,
       "placeholder": True, "rain_corrected": True, "rain_fix_year": 2017, "legume_option": "lentil", "tips": TIPS,
       "plan_sources": [{"name": "GPM IMERG", "type": "satellite", "resolution": "0.1 deg", "years": "2001-2025"}]}


def test_bare_months_are_the_months_without_a_crop_day_after_the_last_harvest():
    assert ex.bare_months(GAP["crops"]) == [4, 5]                     # wheat to 3 Mar, rice from 15 Jun
    assert ex.bare_months(CUR["crops"]) == [3, 4, 5]


def test_cover_gap_with_wheat_is_flagged_for_water_and_names_lentil_as_the_option():
    held = ex.conditions(GAP, CUR, CTX, LIB)
    assert {"plan_is_cover_gap", "needs_water_window", "legume_option", "rain_corrected", "rain_changes_harvest",
            "harvest_better", "cover_better", "has_rice"} <= held
    out = ex.render(GAP, CUR, CTX, LIB, WORDS)
    assert "Wheat here usually needs watering." in out["tabs"]["check"]
    assert "Lentil after rice is another choice." in out["tabs"]["check"]
    assert "Without our rain fix, it was 93." in out["tabs"]["evidence"]
    assert "Near here, those gauge reports stopped in 2017." in out["tabs"]["unknown"]
    assert "२०१७" in out["tabs_ne"]["unknown"] and len(out["tips"]) == len(out["tips_ne"])


def test_safest_plan_says_why_and_has_no_lentil_option_line_of_its_own():
    held = ex.conditions(SAFE, CUR, CTX, LIB)
    assert "plan_is_safest" in held and "legume_option" not in held and "has_legume" in held
    out = ex.render(SAFE, CUR, CTX, LIB, WORDS)
    # owner's answer 3 to REVIEW_2 (2026-11-13): the plan is "Feed your soil"; it is not called the safest
    assert out["tabs"]["why"].startswith("This plan is here to feed your soil. Lentil feeds the soil for the next crop.")
    assert "Bad years hurt it less than now." in out["tabs"]["why"]
    assert "bad_years_better" not in ex.conditions({**SAFE, "stability": 60.0}, CUR, CTX, LIB)
    assert "covered as much as now" not in out["tabs"]["why"]


def test_current_plan_tips_name_its_thirsty_months_and_first_bare_month():
    """Owner's answer 5 to REVIEW_2 (2026-11-13): no rice tip for now; the straw tip names the satellite's first
    bare month (November), not the plan calendar's (March)."""
    out = ex.render(CUR, CUR, CTX, LIB, WORDS)
    assert out["tips"] == ["Potato gets most thirsty in January. Water it then if you can.",
                           "Cover bare soil with straw in November."]


def test_a_crop_that_is_rarely_thirsty_gets_no_tip():
    rare = {**GAP, "thirsty": {"wheat": {"month": 2, "dry_days_per_year": 4.9}, "maize": {"month": 5, "dry_days_per_year": 5.0}}}
    out = ex.render(rare, CUR, CTX, LIB, WORDS)
    assert out["tips"] == ["Maize gets most thirsty in May. Water it then if you can."]


def test_a_suggested_plan_gets_the_straw_tip_only_where_its_own_calendar_is_bare_too():
    assert ex.straw_month(GAP, DIARY) is None                          # wheat stands in November and December
    late = _plan("cover_gap", [("rice", "06-15", "10-02")], GAP["score"])
    assert ex.straw_month(late, DIARY) == 11 and ex.straw_month(CUR, DIARY) == 11
    assert ex.straw_month(CUR, {"months": [{"cover": "crop"}] * 12}) is None


def test_the_harvest_gain_is_a_range_over_the_root_depths():
    """Owner's answer 4: 'about 8 to 22 more', and the unknown tab says why."""
    g = {**GAP, "gain_range": {"low": 8.2, "high": 22.4}}
    held = ex.conditions(g, CUR, CTX, LIB)
    assert {"harvest_gain_range", "has_gain_range"} <= held and "harvest_gain_single" not in held
    out = ex.render(g, CUR, CTX, LIB, WORDS)
    assert "Harvest: about 8 to 22 more." in out["tabs"]["benefits"] and "८ देखि २२" in out["tabs_ne"]["benefits"]
    assert "We don't know how deep roots reach here. So the harvest gain is a range." in out["tabs"]["unknown"]
    one = ex.render({**GAP, "gain_range": {"low": 9.6, "high": 10.3}}, CUR, CTX, LIB, WORDS)
    assert "Harvest: about 10 more, out of 100." in one["tabs"]["benefits"]
    maybe = ex.render({**GAP, "gain_range": {"low": -3.0, "high": 6.2}}, CUR, CTX, LIB, WORDS)
    assert "Harvest: up to 6 more, maybe none." in maybe["tabs"]["benefits"]
    assert "has_gain_range" not in ex.conditions({**CUR, "gain_range": {"low": 1, "high": 2}}, CUR, CTX, LIB)


def test_rain_that_reads_high_and_soil_from_far_away_are_said_in_the_unknown_tab():
    out = ex.render(CUR, CUR, {**CTX, "rain_reads_high": True, "soil_distance_m": 859}, LIB, WORDS)
    assert "Our rain may still read too high." in out["tabs"]["unknown"]
    assert "The soil numbers come from 859 m away." in out["tabs"]["unknown"] and "८५९" in out["tabs_ne"]["unknown"]
    plain = ex.render(CUR, CUR, CTX, LIB, WORDS)
    assert "may still read too high" not in plain["tabs"]["unknown"] and "m away" not in plain["tabs"]["unknown"]


def test_dry_years_are_called_drier_than_usual_and_the_gap_plan_counts_its_own_days():
    g = {**GAP, "cover_days": 250}
    out = ex.render(g, {**CUR, "cover_days": 225}, CTX, LIB, WORDS)
    assert "Drier than usual: 2 of 24 years." in out["tabs"]["evidence"]
    assert out["tabs"]["why"].startswith("The ground is bare about 62 days yearly. This plan grows crops 25 more days.")


def test_legume_option_is_the_legume_of_the_best_rice_plan_with_one():
    rows = [{"crops": ["rice", "lentil"], "stability": 75, "harvest": 80}, {"crops": ["maize", "lentil"], "stability": 90, "harvest": 90},
            {"crops": ["rice", "wheat"], "stability": 84, "harvest": 90}]
    assert ex.legume_option(rows, "rice", LIB) == "lentil" and ex.legume_option(rows[2:], "rice", LIB) is None
