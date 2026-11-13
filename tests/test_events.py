"""One weather event per calendar year for the field (owner's answer 9 to REVIEW_2, 2026-11-13; rules.yaml events):
pipeline/plans/events.py. A worked example on eleven made-up years."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch.rules import load_rules
from pipeline.plans import events as ev

R = load_rules()["events"]


def _rain():
    """2001-2011, dry except: one monsoon day (15 Jul), one winter day (15 Jan) and, in 2005, a 300 mm October day."""
    idx = pd.date_range("2001-01-01", "2011-12-31")
    s = pd.Series(0.0, index=idx)
    for y in range(2001, 2012):
        s[f"{y}-07-15"] = 100.0 + 10.0 * (y - 2001)          # monsoon rain: 100, 110, ... 200
        s[f"{y}-01-15"] = 10.0 + (y - 2001)                  # winter rain: 10, 11, ... 20
    s["2003-07-15"], s["2007-07-15"] = 20.0, 30.0            # the two driest monsoons
    s["2003-01-15"], s["2005-01-15"] = 0.5, 1.0              # the two driest winters
    s["2005-10-04"] = 300.0                                  # the record's wettest day, outside both seasons
    return s


def test_the_rules_are_the_owners():
    assert R["seasons"] == {"monsoon": [6, 7, 8, 9], "winter": [12, 1, 2]}
    assert R["drought_decile_max"] == 2 and R["flood_decile_min"] == 9 and R["precedence"] == ["drought", "flood"]


def test_drought_is_a_season_in_the_lowest_fifth_and_says_which_season():
    out = ev.field_year_events(_rain(), R)
    assert out["events"]["2007"] == "drought" and out["event_seasons"]["2007"] == "monsoon"
    assert out["events"]["2005"] == "drought" and out["event_seasons"]["2005"] == "winter"


def test_a_year_dry_in_both_seasons_is_a_drought_without_one_season():
    out = ev.field_year_events(_rain(), R)
    assert out["events"]["2003"] == "drought" and "2003" not in out["event_seasons"]


def test_flood_is_the_calendar_years_wettest_day_in_the_top_fifth_and_drought_goes_first():
    out = ev.field_year_events(_rain(), R)
    assert [y for y, e in out["events"].items() if e == "flood"] == ["2010", "2011"]
    assert out["events"]["2005"] == "drought"                # 300 mm on one day, but the winter was dry: drought first
    assert out["detail"]["2005"]["wettest_day_mm"] == 300.0 and out["detail"]["2005"]["flood_class"] is True


def test_every_calendar_year_gets_one_event_and_the_first_winter_is_left_out():
    out = ev.field_year_events(_rain(), R)
    assert list(out["events"]) == [str(y) for y in range(2001, 2012)]
    assert sum(e == "none" for e in out["events"].values()) == 6
    assert out["detail"]["2001"]["winter_mm"] is None        # December 2000 is not in the record
    assert out["detail"]["2002"]["winter_mm"] == 11.0 and out["detail"]["2002"]["monsoon_mm"] == 110.0


def test_the_event_does_not_depend_on_any_plan():
    """The same rain gives the same events, whatever is grown: the function takes no crop seasons at all."""
    import inspect
    assert list(inspect.signature(ev.field_year_events).parameters) == ["rain", "rules"]


def test_missing_rain_is_refused():
    s = _rain()
    s["2006-07-15"] = np.nan
    with pytest.raises(ValueError, match="missing"):
        ev.field_year_events(s, R)


def test_frost_is_never_a_replay_event():
    with pytest.raises(ValueError, match="frost"):
        ev.field_year_events(_rain(), {**R, "precedence": ["drought", "flood", "frost"]})
