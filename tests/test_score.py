"""Plan scoring and selection (CLAUDE.md "Plans" steps 3-4, build step 7). Worked examples for
pipeline/plans/score.py."""
import numpy as np
import pandas as pd
import pytest

from pipeline.plans import score as sc

FAM = {"rice": {"family": "Poaceae", "legume": False}, "wheat": {"family": "Poaceae", "legume": False},
       "potato": {"family": "Solanaceae", "legume": False}, "lentil": {"family": "Fabaceae", "legume": True}}


def _y(year, h, crops, irr=0.0, dry=0):
    return {"year": year, "harvest": h, "crops": crops, "irrigation_mm": irr, "dry_days": dry}


def test_only_complete_years_count():
    ys = [_y(2001, 99.0, ["rice"]), _y(2002, 80.0, ["potato", "rice"]), _y(2003, 60.0, ["potato", "rice"])]
    assert [y["year"] for y in sc.complete(ys, ["rice", "potato"])] == [2002, 2003]


def test_harvest_is_the_mean_and_stability_the_10th_percentile_year():
    ys = [_y(2000 + i, h, ["rice"]) for i, h in enumerate([50, 60, 70, 80, 90, 100, 100, 100, 100, 100, 100])]
    m = sc.harvest_metrics(ys)
    assert m["harvest"] == pytest.approx(np.mean([50, 60, 70, 80, 90] + [100] * 6))
    assert m["stability"] == pytest.approx(np.percentile([50, 60, 70, 80, 90] + [100] * 6, 10))     # 60


def test_water_score_is_the_share_of_crop_water_use_rain_covers():
    """ETc 800 mm a year, irrigation 200 mm: rain covers 75% -> 75; with groundwater falling and a factor 1.5
    the 25% from irrigation counts as 37.5% -> 62.5."""
    assert sc.water_score(irrigation_mm=200, etc_mm=800, strict=1.0) == 75.0
    assert sc.water_score(irrigation_mm=200, etc_mm=800, strict=1.5) == 62.5
    assert sc.water_score(irrigation_mm=900, etc_mm=800, strict=1.0) == 0.0


def test_cover_is_the_share_of_the_year_inside_a_crop_season():
    assert sc.cover_score(225) == pytest.approx(100 * 225 / 365)
    assert sc.cover_score(400) == 100.0


def test_pest_break_needs_a_change_of_family_at_every_turn_including_the_next_year():
    assert sc.pest_break(["rice", "potato"], FAM)
    assert not sc.pest_break(["rice", "wheat"], FAM)
    assert not sc.pest_break(["rice"], FAM)                        # rice follows rice the next year
    assert sc.has_legume(["rice", "lentil"], FAM) and not sc.has_legume(["rice", "wheat"], FAM)


def test_erosion_index_weights_erosive_rain_by_cover():
    """Rain 20, 5 and 30 mm on three days; only rain >= 12.7 mm is erosive; index = sum P^beta x C with
    beta = 1 for the example: bare all three days = 50; a crop with C 0.2 on day 3 = 20 + 6 = 26."""
    rain = np.array([20.0, 5.0, 30.0])
    c_bare = sc.erosion_index(rain, np.array([1.0, 1.0, 1.0]), threshold_mm=12.7, beta=1.0)
    c_crop = sc.erosion_index(rain, np.array([1.0, 1.0, 0.2]), threshold_mm=12.7, beta=1.0)
    assert (c_bare, c_crop) == (pytest.approx(50.0), pytest.approx(26.0))
    assert sc.soil_kept_score(c_crop, c_bare) == pytest.approx(48.0)


def test_daily_cover_factor_from_the_plan_seasons():
    days = pd.date_range("2020-01-01", periods=10)
    c = sc.daily_c(days, [("rice", "2020-01-03", "2020-01-05")], {"rice": 0.15}, c_bare=1.0)
    assert list(c) == [1.0, 1.0, 0.15, 0.15, 0.15, 1.0, 1.0, 1.0, 1.0, 1.0]


def test_pareto_keeps_plans_no_other_beats_on_every_score():
    rows = [{"id": "a", "x": 1, "y": 5}, {"id": "b", "x": 2, "y": 4}, {"id": "c", "x": 1, "y": 4}, {"id": "d", "x": 2, "y": 4}]
    assert sorted(r["id"] for r in sc.pareto(rows, ["x", "y"])) == ["a", "b", "d"]


def test_cover_gap_plan_is_the_best_cover_that_keeps_the_harvest():
    rows = [{"id": "cur", "harvest": 80, "cover": 60, "stability": 70},
            {"id": "p1", "harvest": 85, "cover": 70, "stability": 60},
            {"id": "p2", "harvest": 70, "cover": 95, "stability": 50},
            {"id": "p3", "harvest": 81, "cover": 80, "stability": 75}]
    assert sc.pick_cover_gap(rows, "cur")["id"] == "p3"                   # p2 covers more but loses harvest
    assert sc.pick_safest(rows, exclude={"cur", "p3"}, min_cover=0)["id"] == "p1"


def test_the_erosivity_season_weight_peaks_in_july():
    w = sc.month_weight([1, 7], 0.5412)
    assert w[1] == pytest.approx(1.5412) and w[0] == pytest.approx(0.4588)
    rain = np.array([20.0, 20.0])
    assert sc.erosion_index(rain, np.ones(2), 12.7, 1.0, weight=w) == pytest.approx(20 * 0.4588 + 20 * 1.5412)


# ---------- owner's decisions 4 and 5 (2026-11-13): rice in every suggested plan; "Safest in bad years" ----------

def _row(pid, crops, harvest, stability, cover, water=50.0, soil=50.0):
    return {"id": pid, "crops": crops, "harvest": harvest, "stability": stability, "cover": cover, "water": water,
            "soil_kept": soil, "pest_break": 0, "nitrogen": 0}


def test_safest_plan_is_the_best_bad_year_among_plans_keeping_todays_cover():
    rows = [_row("cur", ["rice", "potato"], 73, 66, 62),
            _row("a", ["rice", "wheat"], 90, 84, 69),
            _row("b", ["rice"], 99, 95, 30),                          # safest of all, but leaves the field bare
            _row("c", ["rice", "lentil"], 82, 76, 67)]
    assert sc.pick_safest(rows, exclude={"cur"}, min_cover=62)["id"] == "a"
    assert sc.pick_safest(rows, exclude={"cur", "a"}, min_cover=62)["id"] == "c"


def test_suggested_plans_all_keep_rice_and_differ_from_each_other():
    """A maize plan beats everything but has no rice, so it is never suggested; the Pareto set is taken among the
    rice plans. Cover the gap: the highest cover keeping today's harvest; safest: the best bad year among the rest
    that keep today's cover."""
    rows = [_row("cur", ["rice", "potato"], 73, 66, 62),
            _row("maize_wheat", ["maize", "wheat"], 95, 90, 80, 90, 90),
            _row("rice_wheat", ["rice", "wheat"], 90, 84, 69, 55, 72),
            {**_row("rice_lentil", ["rice", "lentil"], 82, 76, 67, 47, 72), "pest_break": 1, "nitrogen": 1},
            _row("rice_alone", ["rice"], 99, 95, 30, 60, 40)]
    keys = ["harvest", "stability", "water", "cover", "soil_kept", "pest_break", "nitrogen"]
    out = sc.choose_three(rows, "cur", keys, must_include="rice")
    assert out["cover_gap"] == "rice_wheat" and out["safest"] == "rice_lentil"
    assert "maize_wheat" not in out["pareto"] and out["eligible"] == 4
    without_breaks = sc.choose_three(rows, "cur", keys[:5], must_include="rice")   # rice_lentil is then dominated:
    assert without_breaks["safest"] == "rice_lentil" and without_breaks["safest_from"] == "all rice plans"


def test_the_three_plans_grow_different_crops():
    """CLAUDE.md: compare at least three rotations. A second rice-then-wheat (rice sown two weeks earlier) is the same
    rotation, so 'safest' passes over it to the best plan with other crops (2026-11-13, after the first run)."""
    rows = [_row("cur", ["rice", "potato"], 73, 66, 62),
            _row("rice_wheat_15jun", ["rice", "wheat"], 90, 84, 69, 51, 74),
            _row("rice_wheat_1jun", ["rice", "wheat"], 89, 85, 69, 48, 70),
            {**_row("rice_lentil", ["rice", "lentil"], 81, 76, 67, 45, 74), "pest_break": 1, "nitrogen": 1},
            _row("potato_rice_spring", ["potato", "rice"], 82, 74, 62, 42, 71)]
    keys = ["harvest", "stability", "water", "cover", "soil_kept", "pest_break", "nitrogen"]
    out = sc.choose_three(rows, "cur", keys, must_include="rice")
    assert out["cover_gap"] == "rice_wheat_15jun" and out["safest"] == "rice_lentil"


def test_third_plan_fallback_when_no_other_rotation_keeps_todays_cover():
    """rules.yaml plans.third_plan_fallback (2026-11-14, a field abroad): Madagascar's FAO zone calendar gives three rice
    rotations only (scores as computed there from the calendar: cover 81.6, 85.8, 44.7), so the third plan is the best bad
    year among the rotations left, whatever its cover. With two rotations only, there is no third plan: NOT READY."""
    rows = [_row("cur", ["rice", "potato"], 60, 46, 81.6),
            _row("rice_wheat", ["rice", "wheat"], 70, 55, 85.8),
            _row("rice_alone", ["rice"], 91, 87, 44.7)]
    keys = ["harvest", "stability", "water", "cover", "soil_kept", "pest_break", "nitrogen"]
    out = sc.choose_three(rows, "cur", keys, must_include="rice")
    assert out["cover_gap"] == "rice_wheat" and out["safest"] == "rice_alone"
    assert out["safest_from"] == "all rice plans, any cover"
    with pytest.raises(ValueError, match="NOT READY"):
        sc.choose_three(rows[:2], "cur", keys, must_include="rice")
