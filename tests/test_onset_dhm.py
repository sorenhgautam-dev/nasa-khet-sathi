"""DHM's official onset dates as the record of a monsoon shift (owner, 2026-11-14; rules.yaml monsoon_onset_dhm):
shift_days from Sen's slope (Mann-Kendall as pipeline/diary/trends.py), the usual start window (25th-75th percentile),
late years (after 20 June, the owner's threshold), the cross-check agreement test, and the plain words."""
import pandas as pd
import pytest

from pipeline.diary import onset_dhm as od
from pipeline.fetch.rules import RULES_PATH, load_rules

R = load_rules()["monsoon_onset_dhm"]
ALPHA = load_rules()["trends"]["alpha"]
CSV = RULES_PATH.parent / "dhm_onset_dates.csv"
BS = {1: "माघ", 2: "फागुन", 3: "चैत", 4: "बैशाख", 5: "जेठ", 6: "असार", 7: "साउन", 8: "भदौ", 9: "असोज",
      10: "कात्तिक", 11: "मंसिर", 12: "पुस"}
GREG = {5: "मे", 6: "जुन", 7: "जुलाई"}


def _sentences(text):
    for mark in ("।", "!", "?"):
        text = text.replace(mark, ".")
    return [s for s in text.split(".") if s.strip()]


def test_the_rules_are_the_owners():
    assert R["record"] == {"file": "config/dhm_onset_dates.csv", "years": [2001, 2024]}
    assert R["start_window"]["percentiles"] == [25, 75] and R["late_after"] == "06-20"
    assert R["bs_dates"]["month_starts_on_day"] == 15


def test_the_dhm_table_is_in_config_with_its_notice():
    d = pd.read_csv(CSV, dtype=str).set_index("year")
    assert list(d.index.astype(int)) == list(range(1968, 2025))
    assert d.loc["1996", "onset"] == "1996-05-31" and d.loc["1982", "onset"] == "1982-06-27"  # DHM p. 1 extremes
    assert d.loc["2009", "onset"] == "2009-06-23"
    assert d["document"].str.contains("Table 1").all() and (d["page"] == "3").all()
    notice = (RULES_PATH.parent / "dhm_onset_dates.NOTICE.md").read_text()
    assert "not covered by this repository's MIT licence" in notice and "eastern Nepal" in notice
    first_copy = load_rules()["onset_accumulation"]["dhm_onset_dates"]          # committed with the first rule
    assert all(d.loc[str(y), "onset"][5:] == md for y, md in first_copy.items())


def test_record_days_are_calendar_days_inside_the_record_years():
    """3 June = 151 + 3 = 154; 16 June is 151 + 16 = 167 in every year, also in leap 2012 (its day of year is 168)."""
    dates = {2000: "2000-06-06", 2001: "2001-06-03", 2012: "2012-06-16", 2025: "2025-06-01"}
    assert od.record_days(dates, [2001, 2024]) == {2001: 154, 2012: 167}


def test_shift_on_a_straight_line():
    """Onset 160 + 0.5 x (year - 2001), 2001-2024: Sen's slope 0.5 day/yr exactly, x (2024 - 2001) = 11.5 days,
    its range collapses on it, Mann-Kendall p far below 0.05: a clear shift, later."""
    days = {y: 160 + 0.5 * (y - 2001) for y in range(2001, 2025)}
    s = od.shift(days, ALPHA)
    assert (s["shift_days"], s["shift_days_low"], s["shift_days_high"]) == (11.5, 11.5, 11.5)
    assert s["clear"] is True and s["direction"] == "later" and s["p"] < 0.001


def test_shift_with_a_range_through_zero_is_no_clear_shift():
    days = {y: (160 if y % 2 else 164) for y in range(2001, 2025)}
    s = od.shift(days, ALPHA)
    assert s["shift_days_low"] <= 0 <= s["shift_days_high"]
    assert s["clear"] is False and s["direction"] == "no clear shift"


def test_start_window_is_the_middle_half():
    """numpy.percentile (linear) of 160, 162, 164, 166, 168: 25th = 162 (11 June), 75th = 166 (15 June)."""
    w = od.start_window({2001: 160, 2002: 162, 2003: 164, 2004: 166, 2005: 168}, [25, 75])
    assert (w["from_day"], w["to_day"], w["from"], w["to"]) == (162, 166, "06-11", "06-15")
    assert w["median"] == "06-13"


def test_start_window_rounds_each_end_to_the_nearest_day():
    """160, 161, 170, 171: 25th = 160.75 -> 161 (10 June), 75th = 170.25 -> 170 (19 June)."""
    w = od.start_window({2001: 160, 2002: 161, 2003: 170, 2004: 171}, [25, 75])
    assert (w["from_day"], w["to_day"]) == (161, 170) and (w["from"], w["to"]) == ("06-10", "06-19")


def test_late_is_strictly_after_20_june():
    dates = {2005: "2005-06-20", 2009: "2009-06-23", 2010: "2010-06-17", 2014: "2014-06-20"}
    late = od.late_years(dates, "06-20")
    assert late == {"after": "06-20", "years": [2009], "count": 1, "of": 4, "share": 0.25,
                    "on_the_day": [2005, 2014]}


@pytest.mark.parametrize("t,agrees", [
    ({"low": -0.5, "high": 0.3}, True),       # holds 0 and overlaps DHM's range
    ({"low": 0.1, "high": 0.9}, False),       # excludes 0: a clear shift
    ({"low": -2.0, "high": -0.6}, False),     # excludes 0
    ({"low": -3.0, "high": 3.0}, True),       # wide, but holds 0 and overlaps
])
def test_agreement_with_dhm(t, agrees):
    dhm = {"low": -0.5, "high": 0.333}
    assert od.agrees(t, dhm) is agrees


def test_agreement_needs_overlap_too():
    assert od.agrees({"low": -0.5, "high": 0.1}, {"low": 0.2, "high": 0.5}) is False


@pytest.mark.parametrize("month,day,bs", [(6, 9, ("जेठ", 26)), (6, 16, ("असार", 2)), (6, 20, ("असार", 6)),
                                          (5, 31, ("जेठ", 17)), (6, 14, ("जेठ", 31)), (1, 3, ("पुस", 20))])
def test_approximate_bikram_sambat_date(month, day, bs):
    """Each BS month taken to start on the 15th (rules.yaml bs_dates): 9 June = 9 + 31 (May) - 15 + 1 = Jestha 26;
    16 June = Asar 2; 3 January = 3 + 31 (December) - 15 + 1 = Poush 20."""
    assert od.bs_date(month, day, BS, start_day=15) == bs


def test_nepali_digits():
    assert od.ne_digits("9–16 June 2009") == "९–१६ June २००९"


WIN = {"from": "06-09", "to": "06-16"}
LATE = {"after": "06-20", "years": [2009], "count": 1, "of": 24, "share": 1 / 24, "on_the_day": [2005, 2014, 2019]}
NOSHIFT = {"clear": False, "direction": "no clear shift", "shift_days": -2.2}


def _words(shift=NOSHIFT, xcheck=None, late=LATE):
    return od.words(shift, WIN, late, xcheck or {"chirps": True, "gpm_2001_2016": True}, first_year=2001,
                    bs_names=BS, greg_names=GREG, start_day=15)


def test_words_are_short_in_both_languages():
    w = _words()
    for screen in ("diary_shift", "next3_rice", "how_we_know"):
        for lang in ("en", "ne"):
            text = " ".join(w[screen][lang])
            assert all(len(s.split()) <= 8 for s in _sentences(text)), (screen, lang, text)
        assert w[screen]["ne_review"] == "needs native-speaker review"


def test_words_say_the_numbers():
    w = _words()
    en = " ".join(w["next3_rice"]["en"])
    assert "9–16 June" in en and "In 24 years, 1 came after 20 June." in en and "2009" in en
    ne = " ".join(w["next3_rice"]["ne"])
    assert "जेठ २६ देखि असार २ तिर (जुन ९–१६)" in ne and "असार ६ तिर (जुन २०)" in ne and "२००९" in ne
    assert "No clear change since 2001." in " ".join(w["diary_shift"]["en"])


def test_three_records_agree_only_when_all_do():
    assert "Three independent records agree." in " ".join(_words()["diary_shift"]["en"])
    one = " ".join(_words(xcheck={"chirps": False, "gpm_2001_2016": True})["diary_shift"]["en"])
    assert "Three" not in one and "One satellite rain check does not agree." in one
    both = " ".join(_words(xcheck={"chirps": False, "gpm_2001_2016": False})["how_we_know"]["en"])
    assert "The two satellite rain checks do not agree." in both


def test_words_for_a_clear_shift_and_no_late_year():
    w = _words(shift={"clear": True, "direction": "earlier", "shift_days": -9.6},
               late={**LATE, "years": [], "count": 0, "share": 0.0})
    assert "The rains now start about 10 days earlier." in " ".join(w["diary_shift"]["en"])
    assert "Three" not in " ".join(w["diary_shift"]["en"])        # DHM itself shows a shift
    assert "In 24 years, none came after 20 June." in " ".join(w["next3_rice"]["en"])
