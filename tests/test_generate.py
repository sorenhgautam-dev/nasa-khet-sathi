"""Plan generation (CLAUDE.md "Plans" step 1, build step 7): every sequence of crop seasons that fits the year
without overlapping. Worked examples for pipeline/plans/generate.py."""
import pandas as pd
import pytest

from pipeline.plans import generate as ge
from pipeline.twin.crops import sow_date

LIB = {
    "rice": {"stages_days": {"ini": 20, "dev": 30, "mid": 40, "late": 20},            # 110 days
             "calendar": {"default": 1, "windows": [
                 {"sow": "05-15", "sow_end": "06-15", "harvest": "09-01", "harvest_end": "10-01", "days": [110]},
                 {"sow": "06-01", "sow_end": "07-15", "harvest": "09-15", "harvest_end": "11-01", "days": [110]}]}},
    "potato": {"stages_days": {"ini": 25, "dev": 30, "mid": 30, "late": 30},          # 115 days
               "calendar": {"default": 0, "windows": [
                   {"sow": "10-15", "sow_end": "11-14", "harvest": "02-01", "harvest_end": "03-15", "days": [115]}]}},
    "wheat": {"stages_days": {"ini": 15, "dev": 30, "mid": 60, "late": 35},           # 140 days
              "calendar": {"default": 0, "windows": [
                  {"sow": "10-01", "sow_end": "10-31", "harvest": "02-15", "harvest_end": "03-31", "days": [140]}]}},
}


def test_sow_date_in_another_window_and_position():
    assert sow_date(LIB["rice"]["calendar"], 2010, "start", window=0) == pd.Timestamp("2010-05-15")
    assert sow_date(LIB["rice"]["calendar"], 2010, "end") == pd.Timestamp("2010-07-15")      # default window 1
    with pytest.raises(ValueError, match="window 5 does not exist"):
        sow_date(LIB["rice"]["calendar"], 2010, window=5)


def test_options_are_every_window_and_position():
    opts = ge.options(LIB, ["rice", "potato"], ("start", "middle", "end"))
    assert len(opts) == (2 + 1) * 3
    assert {"crop": "rice", "window": 0, "position": "end"} in opts


def test_season_in_a_year_runs_sow_to_sow_plus_length_minus_one():
    s, e = ge.season_in_year({"crop": "potato", "window": 0, "position": "start"}, LIB, 2010)
    assert (s, e) == (pd.Timestamp("2010-10-15"), pd.Timestamp("2011-02-06"))        # 115 days


def test_rice_then_potato_fits_and_rice_then_wheat_overlaps():
    """Rice sown 23 Jun (middle of window 1) ends 10 Oct; potato sown 30 Oct fits; wheat sown 1 Oct does not."""
    rice = {"crop": "rice", "window": 1, "position": "middle"}
    assert ge.fits([rice, {"crop": "potato", "window": 0, "position": "middle"}], LIB)
    assert not ge.fits([rice, {"crop": "wheat", "window": 0, "position": "start"}], LIB)


def test_the_last_season_must_end_before_the_first_is_sown_the_next_year():
    """Wheat sown 31 Oct ends 19 Mar; rice sown 15 May fits after it. Potato sown 14 Nov ends 8 Mar: fits too.
    Two potato seasons cannot share one year."""
    assert ge.fits([{"crop": "rice", "window": 0, "position": "start"}, {"crop": "wheat", "window": 0, "position": "end"}], LIB)
    assert not ge.fits([{"crop": "potato", "window": 0, "position": "start"}, {"crop": "potato", "window": 0, "position": "end"}], LIB)


def test_generate_lists_single_crops_and_fitting_pairs_once():
    plans = ge.generate(LIB, ["rice", "potato"], ("middle",))
    ids = [ge.plan_id(p) for p in plans]
    assert len(ids) == len(set(ids))
    assert "rice.w1.middle" in ids and "potato.w0.middle" in ids
    assert "rice.w1.middle+potato.w0.middle" in ids
    assert all(ge.fits(p, LIB) for p in plans)


def test_plan_dates_lists_every_season_inside_the_record_in_order():
    plan = [{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "potato", "window": 0, "position": "middle"}]
    d = ge.plan_dates(plan, LIB, "2010-01-01", "2011-12-31")
    assert d == [("rice", "2010-06-23"), ("potato", "2010-10-30"), ("rice", "2011-06-23")]


def test_a_window_whose_own_season_length_excludes_the_twin_crop_is_not_used():
    """The twin grows wheat for 140 days; a window listing 180-day seasons describes another crop length."""
    lib = {"wheat": {"stages_days": {"ini": 15, "dev": 30, "mid": 60, "late": 35},
                     "calendar": {"default": 0, "windows": [
                         {"sow": "10-15", "sow_end": "11-15", "harvest": "03-15", "harvest_end": "04-15", "days": [135, 145]},
                         {"sow": "08-15", "sow_end": "09-15", "harvest": "02-15", "harvest_end": "03-15", "days": [180]}]}}}
    opts = ge.options(lib, ["wheat"], ("middle",))
    assert opts == [{"crop": "wheat", "window": 0, "position": "middle"}]
    assert ge.window_fits_length(lib["wheat"], 1) is False
