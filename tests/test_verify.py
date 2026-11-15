"""pipeline/checks/verify.py: the verification yardsticks' arithmetic (rules.yaml verification)."""
import pytest

from pipeline.checks import verify as v

RULES = {"threshold": 0.92, "n_min": 10}


@pytest.mark.parametrize("k,n,lo,hi", [
    # Newcombe 1998, Statistics in Medicine 17:857-872, Table II, method 3 (Wilson score, no continuity correction)
    (81, 263, 0.2553, 0.3662), (15, 148, 0.0624, 0.1605), (0, 20, 0.0, 0.1611), (1, 29, 0.0061, 0.1718),
])
def test_wilson_reproduces_newcombe(k, n, lo, hi):
    got = v.wilson(k, n)
    assert got[0] == pytest.approx(lo, abs=1e-4) and got[1] == pytest.approx(hi, abs=1e-4)


def test_wilson_of_nothing_is_none():
    assert v.wilson(0, 0) is None


@pytest.mark.parametrize("k,n,independent,status", [
    (23, 25, True, "VERIFIED"),            # 92.0 % exactly: the point estimate counts
    (22, 25, True, "ESTIMATE"),            # 88 %
    (9, 9, True, "NOT YET VERIFIABLE"),    # too few cases, however good
    (0, 0, True, "NOT YET VERIFIABLE"),    # no reference data yet
    (25, 25, False, "ESTIMATE"),           # only a consistency check: never VERIFIED
    (0, 0, False, "ESTIMATE"),             # a projection with no test yet is shown as an estimate
])
def test_grade(k, n, independent, status):
    assert v.grade(k, n, independent, RULES) == status


def test_score_carries_n_share_interval_and_status():
    s = v.score([True] * 11 + [False], True, RULES)
    assert (s["k"], s["n"], s["share"], s["status"]) == (11, 12, 0.9167, "ESTIMATE")
    assert s["ci95"] == pytest.approx([0.6461, 0.9851], abs=1e-4)


def test_within_relative_and_absolute():
    assert v.within([100, 130, 5], [110, 100, 0], rel=0.19) == [True, False, False]
    assert v.within([5, 25], [0, 10], abs_=10) == [True, False]
    assert v.within([100], [None], rel=0.19) == []          # a missing reference is skipped, not counted


def test_events_hits_and_false_alarms():
    flags = {2002: ("flood", None), 2009: ("drought", None), 2013: ("drought", "monsoon"), 2023: ("drought", None)}
    events = [(2002, "flood", None), (2021, "drought", "winter"), (2023, "drought", "winter")]
    listed = {(2009, "drought"), (2002, "flood"), (2021, "drought"), (2023, "drought")}
    controls = [(2023, "drought", "monsoon")]
    hits, alarms = v.events_skill(flags, events, listed, controls)
    assert hits == [True, False, True]
    # one entry per flagged season: 2002 flood ok, 2009 both seasons listed, 2013 monsoon not listed, 2023 winter ok,
    # 2023 monsoon contradicted by DHM's own gauges
    assert alarms == [False, False, False, True, False, True]


def test_beats_pairs_runs_by_key():
    plan = {"a": 70, "b": 60, "c": 66}
    current = {"a": 65, "b": 61, "c": 66, "d": 1}
    assert v.beats(plan, current) == [True, False, False]


def test_farmer_years_ranked_in_thirds():
    harvest = {2015 + i: h for i, h in enumerate([50, 60, 70, 80, 90, 100])}   # thirds: 2 lowest, 2 highest
    assert v.year_matches(harvest, worst=[2015, 2017], best=[2020, 2018]) == [True, False, True, False]


def test_same_direction_uses_first_differences():
    a = {2001: 1, 2002: 3, 2003: 2, 2004: 2}
    b = {2001: 10, 2002: 12, 2003: 15, 2004: 15}
    assert v.same_direction(a, b) == [True, False]          # 2004: no change in a, not scored


# ---- 2026-11-15 rows (rules.yaml verification.outputs frost_month_words, harvest_years.district, monsoon_shift) ----
# Illustrative normals, not DHM's: a cold January, a mild summer.
NORMALS = [1.5, 3.8, 7.5, 11.0, 15.0, 18.5, 19.5, 19.3, 17.8, 13.0, 7.0, 2.6]
WORDS = ["high", "risk", "none", "none", "none", "none", "none", "none", "none", "none", "risk", "high"]


def test_frost_words_in_the_order_of_the_normals_all_pass():
    assert v.frost_order_passes(WORDS, NORMALS, 0.0, 2.0) == [True] * 12


def test_frost_word_out_of_order_fails_both_months():
    w = list(WORDS)
    w[10] = "high"                      # November frostier than February, which is colder (3.8 against 7.0)
    got = v.frost_order_passes(w, NORMALS, 0.0, 2.0)
    assert got == [True, False] + [True] * 8 + [False, True]


def test_frost_word_breaks_the_bound_of_the_mean():
    n = list(NORMALS)
    n[0] = 1.0                          # mean night 1 C: the coldest night is below 2 C, so 'none' cannot be right
    w = ["none"] * 12
    assert v.frost_order_passes(w, n, 0.0, 2.0)[0] is False
    n[0] = -0.5                         # mean night below 0 C: the word must be 'high'
    w[0] = "risk"
    assert v.frost_order_passes(w, n, 0.0, 2.0)[0] is False


def test_equal_normals_are_not_ordered():
    n = [5.0] * 12
    w = ["risk", "none"] * 6
    assert v.frost_order_passes(w, n, 0.0, 2.0) == [True] * 12


def test_residual_signs_match_after_each_line_is_removed():
    ref = {x: 10 * x + e for x, e in zip(range(1, 6), [1, -1, 0, -1, 1])}   # the line is exactly 10x: residuals 1,-1,0,-1,1
    ours = {x: 50 + e for x, e in zip(range(1, 6), [2, -3, 0, 1, 4])}       # its line -1.6+0.8x: residuals 2.8,-3,-0.8,-0.6,1.6
    assert v.residual_sign_matches(ours, ref) == [True, True, True, True]  # year 3: the reference's zero is not scored
    ours = {x: 50 + e for x, e in zip(range(1, 6), [2, -3, 0, 1, -4])}      # its line 1.6-0.8x: residuals 1.2,-3,0.8,2.6,-1.6
    assert v.residual_sign_matches(ours, ref) == [True, True, False, False]


def test_residual_signs_need_shared_years():
    assert v.residual_sign_matches({1: 1.0, 2: 2.0}, {3: 1.0, 4: 2.0}) == []


@pytest.mark.parametrize("day,fy", [("2015-10-10", "2015/16"), ("2016-02-21", "2015/16"), ("2016-07-15", "2015/16"),
                                     ("2016-07-16", "2016/17"), ("2024-12-31", "2024/25")])
def test_fiscal_year_of_a_harvest(day, fy):
    from datetime import date
    assert v.fiscal_year(date.fromisoformat(day), "07-16") == fy


def test_shift_sentence_recomputed():
    years = list(range(2001, 2011))
    assert v.shift_kind(years, [160 + i for i in range(10)], 0.05) == "later"
    assert v.shift_kind(years, [170 - i for i in range(10)], 0.05) == "earlier"
    assert v.shift_kind(years, [160, 170] * 5, 0.05) == "no clear change"
