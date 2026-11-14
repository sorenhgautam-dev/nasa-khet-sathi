"""pipeline/plans/risk.py: the three small checks of 2026-11-14 (rules.yaml rain_risk, fertiliser_saver, heat_clock).
Worked numbers by hand."""
import pandas as pd
import pytest

from pipeline.fetch.cropslib import load_crops
from pipeline.plans import risk

LIB = load_crops()


def test_the_harvest_window_is_the_fao56_late_stage_ending_on_the_crops_last_day():
    # rice 22 late days ending 10 Oct: 10 Oct - 21 days = 19 Sep
    assert risk.window_mmdd({"crop": "rice", "start": "06-23", "end": "10-10"}, LIB, "late") == ("09-19", "10-10")
    # potato 30 late days ending 21 Feb: 21 Feb - 29 days = 23 Jan
    assert risk.window_mmdd({"crop": "potato", "start": "10-30", "end": "02-21"}, LIB, "late") == ("01-23", "02-21")
    # wheat 35 late days ending 3 Mar (365-day year): 3 Mar - 34 days = 28 Jan; the other sowing ends 3 Apr -> 28 Feb
    assert risk.window_mmdd({"crop": "wheat", "start": "10-15", "end": "03-03"}, LIB, "late") == ("01-28", "03-03")
    assert risk.window_mmdd({"crop": "wheat", "start": "11-15", "end": "04-03"}, LIB, "late") == ("02-28", "04-03")
    # the whole season is sowing day to last day
    assert risk.window_mmdd({"crop": "potato", "start": "10-30", "end": "02-21"}, LIB, "season") == ("10-30", "02-21")


def test_the_wheat_book_windows_count_days_after_the_sowing_day():
    # day 0 = the sowing day, a 365-day year. 15 Nov + 20 = 5 Dec (30 Nov is +15); + 100 = 23 Feb (31 Dec +46,
    # 31 Jan +77); + 90 = 13 Feb; + 110 = 5 Mar (28 Feb +105). 15 Oct + 20 = 4 Nov (31 Oct +16); + 100 = 23 Jan (30 Nov +46,
    # 31 Dec +77); + 90 = 13 Jan; + 110 = 2 Feb (31 Jan +108)
    late, early = {"crop": "wheat", "start": "11-15", "end": "04-03"}, {"crop": "wheat", "start": "10-15", "end": "03-03"}
    assert risk.window_mmdd(late, LIB, (20, 100)) == ("12-05", "02-23")
    assert risk.window_mmdd(late, LIB, (90, 110)) == ("02-13", "03-05")
    assert risk.window_mmdd(early, LIB, (20, 100)) == ("11-04", "01-23")
    assert risk.window_mmdd(early, LIB, (90, 110)) == ("01-13", "02-02")
    assert risk.window_days("12-05", "02-23") == 81 and risk.window_days("02-13", "03-05") == 21   # 27 + 31 + 23; 16 + 5
    assert risk.window_days("06-23", "10-10") == 110                                               # 8 + 31 + 31 + 30 + 10


def test_a_window_across_new_year_belongs_to_the_year_it_ends():
    m, d, y = [10, 10, 12, 1, 2, 2, 3], [29, 30, 31, 1, 21, 22, 1], [2001, 2001, 2001, 2002, 2002, 2002, 2002]
    s = risk.season_of(y, m, d, "10-30", "02-21")
    assert [None if pd.isna(x) else int(x) for x in s] == [None, 2002, 2002, 2002, 2002, None, None]
    s2 = risk.season_of([2002, 2002, 2002], [9, 9, 10], [18, 19, 10], "09-19", "10-10")      # within one year
    assert [None if pd.isna(x) else int(x) for x in s2] == [None, 2002, 2002]


def test_complete_seasons_need_the_whole_window_inside_the_record():
    assert risk.complete_seasons(1995, 2014, "10-30", "02-21") == list(range(1996, 2015))      # 19: crosses 1 January
    assert risk.complete_seasons(1995, 2014, "01-28", "03-03") == list(range(1995, 2015))      # 20
    assert risk.complete_seasons(2026, 2040, "10-30", "02-21") == list(range(2027, 2041))      # 14


def test_heavy_rain_counts_a_day_of_exactly_50_mm_dhm_bounds_are_inclusive():
    dates = pd.to_datetime(["2002-09-18", "2002-09-19", "2002-10-01", "2003-10-10", "2003-10-11", "2004-09-30"])
    rain = [80.0, 50.0, 64.25, 49.9, 120.0, 12.0]
    rows = risk.heavy_rain_years(dates, rain, "09-19", "10-10", [2002, 2003, 2004], 50.0)
    # 18 Sep and 11 Oct lie outside the window; 49.9 is not heavy; 50.0 is
    assert rows == [{"year": 2002, "days": 2, "max_mm": 64.2}, {"year": 2003, "days": 0, "max_mm": 49.9},
                    {"year": 2004, "days": 0, "max_mm": 12.0}]
    assert sum(r["days"] > 0 for r in rows) == 1


def test_the_temperature_rules_follow_their_words():
    assert list(risk.risky([34.0, 34.1], {"above_c": 34})) == [False, True]                 # "above 34"
    assert list(risk.risky([34.9, 35.0], {"at_or_above_c": 35})) == [False, True]           # "35 or higher"
    assert list(risk.risky([1.0, 1.1, -2.0], {"at_or_below_c": 1})) == [True, False, True]  # "1 and less"
    assert list(risk.risky([0.0, -0.1, 0.5], {"below_c": 0})) == [False, True, False]       # "below 0", strictly


def test_the_longest_dry_run_is_cut_at_both_ends_of_the_season_and_1_mm_is_not_dry():
    dates = pd.date_range("2002-06-20", "2002-07-05")
    #       20  21  22 |23   24   25   26  27   28  29   30  1   2 | 3   4   5   (the season: 23 Jun to 2 Jul)
    rain = [0, 0, 0, 0, 0.5, 3.0, 0, 0.9, 0, 1.0, 0, 0, 0, 0, 0, 0]
    # inside: dry 23-24 (2: the run from 20 Jun is cut), wet 25, dry 26-28 (3; 0.9 is under 1 mm), 29 Jun has exactly
    # 1 mm (not dry), dry 30 Jun-2 Jul (3: the run to 5 Jul is cut). Longest 3; uncut it would be 5 or 6
    assert risk.longest_dry_runs(dates, rain, "06-23", "07-02", [2002], 1.0) == {2002: 3}
    # across 1 January the season is the year it ends: 30 Dec 2002 to 2 Jan 2003, all dry -> 2003: 4
    d2 = pd.date_range("2002-12-29", "2003-01-03")
    assert risk.longest_dry_runs(d2, [5, 0, 0, 0, 0, 5], "12-30", "01-02", [2003], 1.0) == {2003: 4}
    with pytest.raises(ValueError):          # a gap in the days is never counted as a run
        risk.longest_dry_runs(dates.delete(5), rain[:5] + rain[6:], "06-23", "07-02", [2002], 1.0)


def test_typical_is_the_median_rounded_half_up_and_the_worst_are_the_three_longest_later_year_first():
    by_year = {2002: 30, 2003: 41, 2004: 40, 2005: 41, 2006: 12, 2007: 55}
    # sorted 12 30 40 41 41 55: median (40 + 41) / 2 = 40.5 -> 41 (Python's round would give 40); 55 in 2007, then the
    # tie of 41 days: 2005 before 2003
    assert risk.typical_worst(by_year) == {"typical": 41, "worst": [{"year": 2007, "days": 55}, {"year": 2005, "days": 41},
                                                                     {"year": 2003, "days": 41}]}
    assert risk.typical_worst({2002: 3, 2003: 4, 2004: 9})["typical"] == 4


def test_days_per_season_counts_each_complete_season_once():
    dates = pd.to_datetime(["2001-12-31", "2002-01-05", "2002-12-01", "2003-01-01", "2003-02-22"])
    out = risk.days_by_season(dates.year, dates.month, dates.day, [0.5, 3.0, 1.0, -1.0, -5.0], {"at_or_below_c": 1},
                              "10-30", "02-21", [2002, 2003])
    assert out == {2002: 1, 2003: 2}             # 22 Feb 2003 is after the window


def test_model_means_compare_each_models_past_with_its_own_future():
    rows = []
    for model, cal in (("A", "360_day"), ("B", "365_day")):
        for exp, years in (("historical", (1995, 1996)), ("ssp245", (2026, 2027))):
            for y in range(years[0], years[1] + 1):
                for d in (1, 2, 30):             # 30 Feb exists only in the 360-day calendar
                    if d == 30 and cal != "360_day":
                        continue
                    hot = 36.0 if (exp == "ssp245" and d != 2) or (model == "B" and d == 1) else 20.0
                    rows.append({"model": model, "experiment": exp, "calendar": cal, "year": y, "month": 2, "day": d,
                                 "tasmax_c": hot, "tasmin_c": 5.0})
    df = pd.DataFrame(rows)
    m = risk.model_means(df, "tasmax_c", {"at_or_above_c": 35}, "02-01", "02-30", {"historical": (1995, 1996), "ssp245": (2026, 2027)})
    # A: past 0 a season, future 2 (1 and 30 Feb); B: past 1 (1 Feb), future 1 (1 Feb; no 30 Feb)
    assert m == {"A": {"historical": 0.0, "ssp245": 2.0}, "B": {"historical": 1.0, "ssp245": 1.0}}
    s = risk.scenario_summary(m, "ssp245")
    assert s["median"] == 1.5 and (s["low"], s["high"]) == (1.0, 2.0) and s["past_median"] == 0.5
    assert s["models"] == [{"model": "A", "past": 0.0, "future": 2.0}, {"model": "B", "past": 1.0, "future": 1.0}]


def test_urea_nitrogen_share_comes_from_its_formula():
    w = {"H": 1.0080, "C": 12.011, "N": 14.007, "O": 15.999}     # IUPAC CIAAW abridged 2024
    assert risk.urea_n_share(w) == pytest.approx(28.014 / 60.056)
    assert round(risk.urea_n_share(w), 4) == 0.4665


def test_urea_saved_per_hectare_from_the_carry_over_range():
    s = risk.urea_saved([23, 45], 0.466, 50)
    # 23 / 0.466 = 49.36 kg -> 49; 45 / 0.466 = 96.57 kg -> 97; bags 0.987 -> 1.0 and 1.931 -> 1.9; whole bags 1 and 2
    assert s == {"n_kg_ha": [23, 45], "urea_kg_ha": [49, 97], "bags_ha": [1.0, 1.9], "bags_ha_whole": [1, 2]}


def test_a_sample_field_shares_the_climate_cell_only_inside_the_same_quarter_degree():
    from pipeline.export import build_risks as br
    assert br._cell(27.690767) == br._cell(27.6885) == 27.625          # demo and sample-1: cell 27.5-27.75 N
    assert br._cell(85.441792) == br._cell(85.475542) == 85.375        # and 85.25-85.5 E (the card: centre 27.625, 85.375)
    assert br._cell(85.51) == 85.625                                    # the next cell east


REPO = __import__("pathlib").Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("kind", ["rainrisk", "fertiliser", "heatclock"])
def test_the_exported_files_validate_link_nothing_outside_and_a_broken_count_is_caught(kind):
    import copy
    import json
    from pipeline.export import validate as val
    from scripts import check_site
    path = REPO / "site" / "data" / kind / "demo.json"
    if not path.exists():
        pytest.skip("not exported yet")
    doc, field = json.loads(path.read_text()), json.loads((REPO / "site/data/fields/demo.json").read_text())
    assert val.validate_feature(kind, doc, field) == []
    assert check_site.data_link_problems(f"data/{kind}/demo.json", doc) == []
    bad = copy.deepcopy(doc)
    if kind == "rainrisk":
        bad["plans"][0]["crops"][0]["count"] += 1
        want = "count does not count"
    elif kind == "fertiliser":
        bad["urea_kg_ha"][0] += 1
        want = "not n_kg_ha / urea_n_share"
    else:
        bad["checks"][0]["today"]["years_with"] += 1
        want = "years_with and good_news"
    assert any(want in e for e in val.validate_feature(kind, bad, field))


def test_the_demo_files_hold_the_dry_runs_and_the_wheat_book_checks():
    import copy
    import json
    from pipeline.export import validate as val
    rr, hc = (REPO / "site" / "data" / k / "demo.json" for k in ("rainrisk", "heatclock"))
    if not (rr.exists() and hc.exists()):
        pytest.skip("not exported yet")
    rr, hc = json.loads(rr.read_text()), json.loads(hc.read_text())
    for p in rr["plans"]:
        for c in p["crops"]:
            d = c["dry_run"]
            assert (d["window"]["from"], d["window"]["to"]) == (c["sow"], c["end"]) and len(d["years"]) == 24
            assert d["typical_low"] <= d["typical"] <= d["typical_high"] and len(d["worst"]) == 3
    bad = copy.deepcopy(rr)
    bad["plans"][0]["crops"][0]["dry_run"]["typical"] += 1
    assert any("dry_run" in e for e in val.validate_feature("rainrisk", bad))
    book = {c["id"]: (c["window"]["from"], c["window"]["to"], c["sure"]) for c in hc["checks"] if "sure" in c}
    assert book == {"wheat_1015_floret_formation_heat": ("11-04", "01-23", "estimate"),
                    "wheat_1015_flowering_cold": ("01-13", "02-02", "estimate"),
                    "wheat_1115_floret_formation_heat": ("12-05", "02-23", "estimate"),
                    "wheat_1115_flowering_cold": ("02-13", "03-05", "estimate")}
    assert [c["id"] for c in hc["checks"]][:4] == ["potato_1030_cold", "potato_1030_heat", "wheat_1015_heat", "wheat_1115_heat"]
