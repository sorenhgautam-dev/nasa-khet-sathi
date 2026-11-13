"""Monsoon onset per year (CLAUDE.md "Field diary", build step 6a). Rule, from 15 May: the first day d that is
wet and starts a 5-day window holding at least 2 wet days (>= 1 mm) and at least 10 mm in all, with no run of
10 dry days (< 1 mm each) in the 20 days after d. Robustness: dry spells of 15 and 20 days. Worked examples."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import onset as on
from pipeline.fetch.rules import load_rules

R = load_rules()["monsoon_onset"]


def _year(rain_by_date, year=2010, base=0.0):
    """A daily series for one year: `base` mm every day, with the given dates overridden."""
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    s = pd.Series(base, index=idx, dtype=float)
    for d, mm in rain_by_date.items():
        s[pd.Timestamp(f"{year}-{d}")] = mm
    return s


def _wet_after(start, days=60, mm=3.0):
    """Steady rain of `mm` a day for `days` days from `start` (MM-DD)."""
    first = pd.Timestamp(f"2010-{start}")
    return {(first + pd.Timedelta(i, unit="D")).strftime("%m-%d"): mm for i in range(days)}


def test_the_rules_are_the_claude_md_rule():
    assert R["search_from"] == "05-15" and R["wet_day_mm"] == 1.0 and R["wet_days_min"] == 2
    assert R["window_days"] == 5 and R["total_mm"] == 10.0
    assert R["dry_spell_days"] == 10 and R["lookahead_days"] == 20
    assert R["robustness_dry_spell_days"] == [15, 20]


def test_a_steady_start_is_the_onset():
    s = _year({"06-01": 6.0, "06-02": 5.0, **_wet_after("06-03")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-01")


def test_a_false_start_followed_by_a_dry_spell_is_skipped():
    """8 + 8 mm on 20-21 May, then 12 dry days: rejected. The real onset is 10 June."""
    s = _year({"05-20": 8.0, "05-21": 8.0, "06-10": 6.0, "06-11": 6.0, **_wet_after("06-12")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-10")


def test_one_heavy_day_alone_is_not_an_onset():
    s = _year({"05-25": 30.0, "06-15": 5.0, "06-16": 6.0, **_wet_after("06-17")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-15")


def test_two_wet_days_must_reach_10_mm():
    s = _year({"05-25": 4.0, "05-26": 5.0, "06-15": 5.0, "06-16": 6.0, **_wet_after("06-17")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-15")


def test_the_two_wet_days_need_not_be_next_to_each_other():
    s = _year({"06-01": 6.0, "06-05": 5.0, **_wet_after("06-06")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-01")


def test_the_onset_day_itself_must_be_wet():
    """A dry 31 May before 6 + 5 mm on 1-2 June: the onset is 1 June, not 31 May."""
    s = _year({"05-31": 0.0, "06-01": 6.0, "06-02": 5.0, **_wet_after("06-03")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-01")


def test_rain_before_15_may_is_ignored():
    s = _year({"05-01": 20.0, "05-02": 20.0, **_wet_after("05-03", days=10), "06-01": 6.0, "06-02": 5.0,
               **_wet_after("06-03")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-01")


def test_a_longer_dry_spell_rule_keeps_a_start_the_10_day_rule_rejects():
    """12 dry days after a start: rejected with 10-day spells, kept with 15 or 20."""
    s = _year({"05-20": 8.0, "05-21": 8.0, "06-03": 6.0, "06-04": 6.0, **_wet_after("06-05")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-03")
    assert on.onset_date(s, {**R, "dry_spell_days": 15}) == pd.Timestamp("2010-05-20")
    assert on.onset_date(s, {**R, "dry_spell_days": 20}) == pd.Timestamp("2010-05-20")


def test_the_look_ahead_counts_from_the_onset_day():
    """Moron, Robertson & Boer 2009 count the look-ahead 'from the onset date': for a start on 1 June the 20 days
    are 1-20 June. A 10-day dry spell 12-21 June ends on day 21, outside them, so 1 June is the onset (counting
    from the day after, 2-21 June, would have rejected it)."""
    s = _year({"06-01": 6.0, "06-02": 5.0, **_wet_after("06-03", days=9), **_wet_after("06-22")})
    assert on.onset_date(s, R) == pd.Timestamp("2010-06-01")


def test_no_onset_by_the_end_of_the_search_gives_none():
    assert on.onset_date(_year({}), R) is None


def test_onset_needs_its_look_ahead_inside_the_record():
    """A start whose 20-day look-ahead runs past the record's end cannot be confirmed."""
    s = _year({"12-25": 6.0, "12-26": 6.0}).loc[:"2010-12-31"]
    assert on.onset_date(s, {**R, "search_until": "12-31"}) is None


def test_a_missing_day_fails_loudly():
    s = _year({"06-01": 6.0, "06-02": 5.0, **_wet_after("06-03")})
    s[pd.Timestamp("2010-06-10")] = np.nan
    with pytest.raises(ValueError, match="missing"):
        on.onset_date(s, R)


def test_onsets_per_year_and_the_robustness_runs():
    years = pd.concat([_year({"06-01": 6.0, "06-02": 5.0, **_wet_after("06-03")}, year=y) for y in (2010, 2011)])
    out = on.onsets(years, R)
    assert out["by_dry_spell_days"]["10"] == {"2010": "2010-06-01", "2011": "2011-06-01"}
    assert set(out["by_dry_spell_days"]) == {"10", "15", "20"}
    assert out["day_of_year"]["2010"] == pd.Timestamp("2010-06-01").dayofyear
