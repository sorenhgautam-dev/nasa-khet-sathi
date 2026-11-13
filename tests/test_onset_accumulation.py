"""Second monsoon-onset measure: the anomalous accumulation (rules.yaml onset_accumulation; Noska & Misra 2016, GRL 43,
p. 4548, eqs. 1-2). C(i) = sum_{n=1..i} (D(n) - Dbar) from 1 January; onset = the day after C's absolute minimum,
searched from 1 January to 30 September. Dbar = the record's mean daily rain (climatological, the paper) or the year's
own mean (own_year, Claude's variant). No printed per-year example exists, so each series below is built so that its
answer follows from the definition by hand."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import onset_accumulation as oa
from pipeline.fetch.rules import load_rules

R = load_rules()["onset_accumulation"]
ALPHA = load_rules()["trends"]["alpha"]


def _year(spans, year=2010, base=0.0):
    """One calendar year of daily rain: `base` mm a day, and mm a day over each (first 'MM-DD', last 'MM-DD', mm)."""
    s = pd.Series(base, index=pd.date_range(f"{year}-01-01", f"{year}-12-31"), dtype=float)
    for first, last, mm in spans:
        s[pd.Timestamp(f"{year}-{first}"):pd.Timestamp(f"{year}-{last}")] = mm
    return s


def test_the_rules_are_the_committed_rule():
    assert R["feeds_shift_days"].startswith("own_year variant on the twin's rain")
    assert set(R["variants"]) == {"climatological", "own_year"}
    assert R["sanity_window"] == ["06-02", "06-29"] and R["edge_days"] == 2
    assert R["dhm_onset_dates"][2001] == "06-03" and R["dhm_onset_dates"][2024] == "06-10"
    assert len(R["dhm_onset_dates"]) == 24


def test_onset_is_the_day_after_the_minimum():
    """10 mm a day from 15 June to 14 September (92 days), dry otherwise: Dbar = 920 / 365 = 2.5205 mm. C falls by
    Dbar every day to 14 June (day 165) and rises from 15 June: minimum C(14 Jun) = -165 x 920 / 365 = -415.89 mm,
    onset 15 June."""
    s = _year([("06-15", "09-14", 10.0)])
    c = oa.accumulation(s, s.mean())
    assert c[pd.Timestamp("2010-06-14")] == pytest.approx(-165 * 920 / 365)
    r = oa.onset_in_year(s, s.mean())
    assert r["minimum_on"] == pd.Timestamp("2010-06-14") and r["onset"] == pd.Timestamp("2010-06-15")
    assert r["minimum_mm"] == pytest.approx(-415.89, abs=0.01)


def test_rain_below_the_mean_does_not_end_the_fall():
    """2 mm a day in May (below Dbar = (62 + 1,220) / 365 = 3.51 mm) and 10 mm a day June-September: C keeps falling
    through May, so the onset is 1 June, not 1 May."""
    s = _year([("05-01", "05-31", 2.0), ("06-01", "09-30", 10.0)])
    assert s.mean() == pytest.approx(1282 / 365)
    assert oa.onset_in_year(s, s.mean())["onset"] == pd.Timestamp("2010-06-01")


def test_the_two_variants_differ_on_a_wet_and_a_dry_year():
    """2010: 6 mm a day in May, 20 in June-September (2,626 mm); 2011 the same x 0.25 (656.5 mm).
    Climatological Dbar = 3,282.5 / 730 = 4.4966: May's 6 mm in 2010 is above it (onset 1 May), May's 1.5 mm in 2011 is
    below it (onset 1 June). Own-year Dbar 7.1945 and 1.7986: May is below both, so both years start on 1 June."""
    wet = _year([("05-01", "05-31", 6.0), ("06-01", "09-30", 20.0)], 2010)
    dry = _year([("05-01", "05-31", 1.5), ("06-01", "09-30", 5.0)], 2011)
    rain = pd.concat([wet, dry])
    rates = oa.reference_rates(rain, "climatological")
    assert rates[2010] == rates[2011] == pytest.approx(3282.5 / 730)
    clim = oa.onsets(rain, "climatological", R)
    assert clim["dates"] == {"2010": "2010-05-01", "2011": "2011-06-01"}
    own_rates = oa.reference_rates(rain, "own_year")
    assert own_rates[2010] == pytest.approx(2626 / 365) and own_rates[2011] == pytest.approx(656.5 / 365)
    own = oa.onsets(rain, "own_year", R)
    assert own["dates"] == {"2010": "2010-06-01", "2011": "2011-06-01"}


def test_own_year_onset_does_not_move_when_a_year_is_scaled():
    """k x D gives k x C: the day of the minimum stays, for any k > 0 (the reason the own_year variant exists)."""
    rng = np.random.default_rng(0)
    s = pd.Series(rng.gamma(0.4, 4.0, 365), index=pd.date_range("2010-01-01", "2010-12-31"))
    s[pd.Timestamp("2010-06-10"):pd.Timestamp("2010-09-20")] += 12.0
    base = oa.onsets(s, "own_year", R)["dates"]["2010"]
    for k in (0.5, 1.4, 2.3):
        assert oa.onsets(s * k, "own_year", R)["dates"]["2010"] == base


def test_two_rainy_seasons_a_short_early_spell_does_not_win():
    """8 mm a day 1-10 April and 10 mm a day 1 July-30 September; Dbar = 1,000 / 365 = 2.7397 mm.
    C(31 Mar) = -90 Dbar = -246.6; C(10 Apr) = -246.6 + 10 x (8 - Dbar) = -194.0; C(30 Jun) = -181 Dbar + 80 = -415.9,
    lower: the absolute minimum is 30 June, onset 1 July."""
    s = _year([("04-01", "04-10", 8.0), ("07-01", "09-30", 10.0)])
    c = oa.accumulation(s, s.mean())
    assert c[pd.Timestamp("2010-03-31")] == pytest.approx(-90 * 1000 / 365)
    assert c[pd.Timestamp("2010-06-30")] == pytest.approx(80 - 181 * 1000 / 365)
    assert oa.onset_in_year(s, s.mean())["onset"] == pd.Timestamp("2010-07-01")


def test_two_rainy_seasons_a_big_early_season_wins():
    """20 mm a day through April, a 15-day dry gap, then 10 mm a day 16 May-30 September: the April excess is far
    larger than the gap's deficit, so the absolute minimum is 31 March and the onset 1 April (absolute, not last)."""
    s = _year([("04-01", "04-30", 20.0), ("05-16", "09-30", 10.0)])
    assert oa.onset_in_year(s, s.mean())["onset"] == pd.Timestamp("2010-04-01")


def test_a_flat_bottom_goes_to_its_first_day():
    """Rain exactly Dbar on 1-5 June (3.25 mm, with 10 mm a day 6 June-30 September: Dbar = 1,186.25 / 365 = 3.25):
    C is flat from 31 May to 5 June. The minimum is first reached on 31 May, so the onset is 1 June."""
    s = _year([("06-01", "06-05", 3.25), ("06-06", "09-30", 10.0)])
    assert s.mean() == pytest.approx(3.25)
    r = oa.onset_in_year(s, s.mean())
    assert r["minimum_on"] == pd.Timestamp("2010-05-31") and r["onset"] == pd.Timestamp("2010-06-01")


def test_no_rain_at_all_has_no_onset():
    s = _year([])
    assert oa.onset_in_year(s, 0.0)["onset"] is None
    assert oa.onsets(s, "own_year", R)["dates"] == {"2010": None}
    assert oa.onsets(s, "climatological", R)["dates"] == {"2010": None}


def test_a_dry_year_in_a_wet_record_is_pinned_at_the_end():
    """Climatological Dbar > 0 and a year with no rain: C falls all year, the minimum is the last day searched
    (30 September), the onset 1 October, and the year is at a window edge."""
    rain = pd.concat([_year([("06-01", "09-30", 10.0)], 2010), _year([], 2011)])
    out = oa.onsets(rain, "climatological", R)
    assert out["dates"]["2011"] == "2011-10-01" and out["at_edge"] == [2011]
    assert out["dates"]["2010"] == "2010-06-01"


def test_rain_all_year():
    """The same rain every day: own-year C is 0 every day (flat), no onset. In a record whose other year is drier,
    the climatological C rises from 1 January: minimum on 1 January, onset 2 January, at a window edge."""
    steady = _year([], 2010, base=5.0)
    assert oa.onsets(steady, "own_year", R)["dates"] == {"2010": None}
    rain = pd.concat([steady, _year([("06-01", "09-30", 3.0)], 2011)])
    out = oa.onsets(rain, "climatological", R)
    assert out["dates"]["2010"] == "2010-01-02" and 2010 in out["at_edge"]


def test_rain_after_30_september_is_not_searched():
    """A season starting 10 October: C falls until 9 October, but the search ends on 30 September, so the minimum is
    30 September (onset 1 October, at the edge)."""
    s = _year([("10-10", "12-31", 10.0)])
    r = oa.onset_in_year(s, s.mean())
    assert r["minimum_on"] == pd.Timestamp("2010-09-30") and r["onset"] == pd.Timestamp("2010-10-01")


@pytest.mark.parametrize("day,edge", [("01-01", True), ("01-03", True), ("01-04", False), ("09-27", False),
                                      ("09-28", True), ("09-30", True)])
def test_window_edges_are_2_days_at_either_end(day, edge):
    assert oa.at_edge(pd.Timestamp(f"2010-{day}"), "09-30", 2) is edge


def test_a_missing_day_or_value_fails_loudly():
    s = _year([("06-01", "09-30", 10.0)])
    with pytest.raises(ValueError, match="missing"):
        oa.onsets(s.drop(pd.Timestamp("2010-07-04")), "own_year", R)
    s[pd.Timestamp("2010-07-04")] = np.nan
    with pytest.raises(ValueError, match="missing"):
        oa.onsets(s, "climatological", R)


def test_an_unknown_variant_fails():
    with pytest.raises(ValueError, match="variant"):
        oa.reference_rates(_year([]), "both")


def test_calendar_day_ignores_leap_years():
    """15 June is calendar day 166 in every year (it is day 167 of 2012), so a leap year adds no false shift."""
    assert oa.calendar_day(pd.Timestamp("2011-06-15")) == 166
    assert oa.calendar_day(pd.Timestamp("2012-06-15")) == 166
    assert oa.calendar_day(pd.Timestamp("2012-02-29")) == 60
    assert oa.calendar_day_to_text(166) == "15 Jun"


def _t(slope, low, high, p=0.5):
    return {"slope_per_year": slope, "low": low, "high": high, "p": p}


def test_trust_all_four_parts_hold():
    v = oa.trust(median_day=166, window=["06-02", "06-29"], edge_years={"corrected": [], "uncorrected": []},
                 t_corrected=_t(0.2, -0.1, 0.5), t_uncorrected=_t(0.1, -0.2, 0.4), alpha=ALPHA)
    assert v["sanity"] and v["not_pinned"] and v["robust_to_rain"] and v["trusted"]
    assert v["clear_shift"] is False                    # p 0.5 >= 0.05: "no clear shift"


def test_trust_the_window_is_inclusive_and_sourced():
    """2 June is calendar day 153, 29 June day 180 (DHM's 31 May and 27 June, 2 days later for Kathmandu)."""
    ok = dict(window=["06-02", "06-29"], edge_years={"corrected": [], "uncorrected": []},
              t_corrected=_t(0, -1, 1), t_uncorrected=_t(0, -1, 1), alpha=ALPHA)
    assert oa.trust(median_day=153, **ok)["sanity"] and oa.trust(median_day=180, **ok)["sanity"]
    assert not oa.trust(median_day=152, **ok)["sanity"] and not oa.trust(median_day=181, **ok)["sanity"]
    assert not oa.trust(median_day=136, **ok)["trusted"]          # the kept rule's 16 May fails it
    assert not oa.trust(median_day=None, **ok)["trusted"]


def test_trust_fails_on_any_year_at_an_edge_on_either_rain():
    v = oa.trust(median_day=166, window=["06-02", "06-29"], edge_years={"corrected": [], "uncorrected": [2019]},
                 t_corrected=_t(0, -1, 1), t_uncorrected=_t(0, -1, 1), alpha=ALPHA)
    assert not v["not_pinned"] and not v["trusted"]


@pytest.mark.parametrize("tc,tu,robust", [
    (_t(0.3, 0.1, 0.5), _t(-0.2, -0.4, -0.05), False),   # opposite signs
    (_t(0.6, 0.5, 0.8), _t(0.2, 0.0, 0.4), False),       # same sign, ranges do not overlap
    (_t(0.0, -0.2, 0.3), _t(-0.3, -0.6, 0.0), True),     # a zero slope never has the opposite sign; ranges touch at 0
    (_t(-0.4, -0.8, -0.1), _t(-0.2, -0.5, 0.1), True),
])
def test_trust_robust_to_the_rain_version(tc, tu, robust):
    v = oa.trust(median_day=166, window=["06-02", "06-29"], edge_years={"corrected": [], "uncorrected": []},
                 t_corrected=tc, t_uncorrected=tu, alpha=ALPHA)
    assert v["robust_to_rain"] is robust and v["trusted"] is robust


def test_shift_days_is_slope_times_24_years_or_null():
    """Sen's slope -0.25 day/yr [-0.6, +0.1] over 2001-2025: -6.0 days [-14.4, +2.4]; kept even though the range holds
    0 ('no clear shift'). Not trusted: every value null."""
    t = {"slope_per_year": -0.25, "low": -0.6, "high": 0.1, "first": 2001, "last": 2025}
    assert oa.shift_export(True, t) == {"shift_days": -6.0, "shift_days_low": -14.4, "shift_days_high": 2.4}
    assert oa.shift_export(False, t) == {"shift_days": None, "shift_days_low": None, "shift_days_high": None}


def test_agreement_with_dhm():
    ours = {2001: 160, 2002: 165, 2003: 170, 2004: 175}
    same = oa.agreement(ours, {y: d - 3 for y, d in ours.items()})
    assert same["n"] == 4 and same["spearman"] == pytest.approx(1.0) and same["median_difference_days"] == 3
    assert same["spearman_p"] == pytest.approx(0.0, abs=1e-9)
    rev = oa.agreement(ours, {2001: 175, 2002: 170, 2003: 165, 2004: 160, 2030: 150})
    assert rev["n"] == 4 and rev["spearman"] == pytest.approx(-1.0)
    assert oa.agreement({2001: None, 2002: 160}, {2001: 160, 2002: 160})["n"] == 1


@pytest.mark.parametrize("trusted,clear,slope", [(False, False, None), (True, False, -6.0), (True, True, -12.0),
                                                  (True, True, 9.0)])
def test_plain_words_are_short(trusted, clear, slope):
    """Farmer-facing words: at most 8 words a sentence, and the GPM break is always named."""
    words = oa.plain_words(trusted, clear, slope, median_text="15 Jun")
    sentences = [s for s in words.replace("!", ".").split(".") if s.strip()]
    assert sentences and all(len(s.split()) <= 8 for s in sentences)
    assert "2017" in words
    if not trusted:
        assert "cannot tell" in words
