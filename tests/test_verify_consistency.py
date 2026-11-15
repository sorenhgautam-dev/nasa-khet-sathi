"""Job D (owner, 2026-11-15): the consistency checks of rules.yaml verification.outputs rotation_guess, cover_months,
season_dates (the drone photo of 5 May 2026, one field and one date; the FAO crop calendar and the district crop
statistics, area level) and probe_water (the spoon cups, leave one cup out). Worked numbers."""
import pytest

from pipeline.checks import verify as v

CAL = {"rice": {"windows": [{"sow": "05-15", "sow_end": "06-15", "harvest": "09-15", "harvest_end": "10-15"},
                            {"sow": "06-01", "sow_end": "07-15", "harvest": "10-15", "harvest_end": "11-15"}], "default": 1},
       "wheat": {"windows": [{"sow": "10-15", "sow_end": "11-15", "harvest": "03-15", "harvest_end": "04-15"}], "default": 0},
       "potato": {"windows": [{"sow": "10-15", "sow_end": "11-15", "harvest": "02-15", "harvest_end": "03-15"}], "default": 0}}


def test_the_guess_is_a_cereal_on_the_drone_day_has_calendar_windows_and_is_grown_in_the_district():
    ok, rows = v.guess_consistency(["rice", "wheat"], CAL, {"rice": [4250, 3599], "wheat": [3000, 1869]},
                                   drone_seen="cereal", cereals=["rice", "wheat", "maize"])
    assert ok == [True, True, True, True, True] and len(rows) == 5          # drone, 2 calendar, 2 district
    ok2, _ = v.guess_consistency(["rice", "potato"], CAL, {"rice": [4250], "potato": [1336, 0]},
                                 drone_seen="cereal", cereals=["rice", "wheat"])
    assert ok2 == [False, True, True, True, False]                          # potato is no cereal; one year with 0 ha
    ok3, rows3 = v.guess_consistency(["rice", "lentil"], CAL, {"rice": [1]})   # no drone; lentil: no window, not in file
    assert ok3 == [True, False, True] and any("listed, not scored" in r["case"] for r in rows3)


def test_bare_months_follow_the_calendar_windows_and_the_drone_month_is_not_bare():
    """Rice 1 Jun-15 Nov and wheat 15 Oct-15 Apr (default windows): only May's 15th is in neither, so May is the
    calendar's one bare month."""
    cover = {m: "crop" for m in v.MONTHS}
    ok, _ = v.cover_consistency(cover, ["rice", "wheat"], CAL, drone_month="May")
    assert len(ok) == 13 and ok[0] is True and ok.count(False) == 1         # May is 'crop' here, the calendar says bare
    cover["May"] = "bare"
    ok, _ = v.cover_consistency(cover, ["rice", "wheat"], CAL, drone_month="May")
    assert ok[0] is False and ok[1:] == [True] * 12                         # the drone saw a crop in May


def test_season_ends_against_the_drone_day_and_the_calendars_harvest_windows():
    """Winter seasons ending 1 May and 19 May (median 10 May) hold 5 May; wheat's harvest window 15 Mar-15 Apr, give or
    take 10 days, ends 25 Apr, so 10 May is outside. Monsoon seasons ending 18 Oct and 22 Oct (median 20 Oct) lie in
    rice's 15 Oct-15 Nov."""
    seasons = [{"start": "2014-12-27", "peak": "2015-03-20", "end": "2015-05-01"},
               {"start": "2016-01-04", "peak": "2016-03-10", "end": "2016-05-19"},
               {"start": "2015-06-20", "peak": "2015-08-20", "end": "2015-10-18"},
               {"start": "2016-06-22", "peak": "2016-08-22", "end": "2016-10-22"}]
    ok, rows = v.season_consistency(seasons, ["rice", "wheat"], CAL, drone_date="05-05", tol_days=10)
    assert ok == [True, True, False]
    assert [r["case"].split(":")[0] for r in rows] == ["drone", "monsoon harvest", "winter harvest"]


def test_groundwater_direction_against_each_published_study():
    studies = [{"cite": "A 2014", "direction": "falling"}, {"cite": "B 2025", "direction": "falling"}]
    assert v.direction_cases("falling", studies)[0] == [True, True]
    assert v.direction_cases("steady", studies)[0] == [False, False]


def test_the_2040_change_has_the_sign_of_nepals_2019_projections_and_the_sizes_are_only_reported():
    """Ours (VALIDATION 4.7): SSP2-4.5 Tmax +0.70, Tmin +0.91 -> mean +0.805 C, rain +4.77 %; SSP5-8.5 +0.89 and +0.95 ->
    +0.92 C, rain +4.03 %. MoFE 2019 Table 8: RCP4.5 +0.92 C, +2.1 %; RCP8.5 +1.07 C, +6.4 %. Every sign agrees."""
    plaus = {"ssp245": {"dtmax_c": {"ours": 0.7}, "dtmin_c": {"ours": 0.91}, "rain_change_pct": {"ours": 4.77}},
             "ssp585": {"dtmax_c": {"ours": 0.89}, "dtmin_c": {"ours": 0.95}, "rain_change_pct": {"ours": 4.03}}}
    mofe = {"rcp45": {"temp_c": 0.92, "rain_pct": 2.1}, "rcp85": {"temp_c": 1.07, "rain_pct": 6.4}}
    ok, rows = v.sign_cases(plaus, mofe)
    assert ok == [True, True, True, True]
    assert [round(r["ours"], 3) for r in rows] == [0.805, 4.77, 0.92, 4.03] and [r["mofe"] for r in rows] == [0.92, 2.1, 1.07, 6.4]
    plaus["ssp245"]["rain_change_pct"]["ours"] = -1.0
    assert v.sign_cases(plaus, mofe)[0] == [True, False, True, True]


def test_spoon_cups_each_scored_on_a_line_fitted_to_the_others():
    """The 4 hand-copied cups (water 0, 5, 10, 15 % against probe 8, 36, 68, 87 %): each cup's water from the line on the
    other three is within 4 water-% points (0.04 m3/m3)."""
    cups = [{"water_pct": 0.0, "value_pct": 8.0}, {"water_pct": 5.0, "value_pct": 36.0},
            {"water_pct": 10.0, "value_pct": 68.0}, {"water_pct": 15.0, "value_pct": 87.0}]
    ok, rows = v.spoon_cases(cups, tol_m3m3=0.04)
    assert ok == [True, True, True, True]
    # by hand: -0.684, -0.045, 1.305, -1.734 water-% (RMSE 1.138, as config/probe_calibration.yaml's 0.0114 m3/m3)
    assert [round(r["error_m3m3"], 5) for r in rows] == [-0.00684, -0.00045, 0.01305, -0.01734]
