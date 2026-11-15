"""pipeline/diary/weather_ahead.py: Weather ahead (rules.yaml weather_ahead), worked numbers."""
import numpy as np
import pandas as pd
import pytest

from pipeline.diary import weather_ahead as wa


def test_twelve_blocks_start_on_the_15th_and_are_keyed_by_their_gregorian_month():
    b = wa.blocks(15)
    assert len(b) == 12
    assert b[10] == {"key": "Nov", "from": "11-15", "to": "12-14"}
    assert b[11] == {"key": "Dec", "from": "12-15", "to": "01-14"}   # Poush crosses 1 January


def test_the_24_latest_blocks_lie_wholly_in_the_record():
    d0, d1 = pd.Timestamp("2001-01-01"), pd.Timestamp("2025-12-31")
    assert wa.block_years(11, 15, d0, d1, 24) == list(range(2002, 2026))
    assert wa.block_years(12, 15, d0, d1, 24) == list(range(2001, 2025))   # Dec 2025 needs Jan 2026
    assert wa.block_years(1, 15, d0, d1, 24) == list(range(2002, 2026))


def test_a_window_counted_in_days_after_sowing():
    # 15 Nov + 20 days = 5 Dec; + 100 days = 23 Feb (15 + 31 + 31 + 23); + 90 = 13 Feb; + 110 = 5 Mar
    assert wa.days_after("11-15", 20, 100) == ("12-05", "02-23")
    assert wa.days_after("11-15", 90, 110) == ("02-13", "03-05")


def test_fao56_stage_windows_of_a_plan_crop():
    potato = {"crop": "potato", "start": "10-30", "end": "02-21"}
    st = {"ini": 25, "dev": 30, "mid": 30, "late": 30}
    assert wa.stage_window(potato, st, "initial") == ("10-30", "11-23")     # days 0-24
    assert wa.stage_window(potato, st, "mid_late") == ("12-24", "02-21")    # from day 25 + 30 = 55
    assert wa.stage_window(potato, st, "late") == ("01-23", "02-21")        # the last 30 days, as rain_risk
    assert wa.stage_window(potato, st, "season") == ("10-30", "02-21")


def test_rice_has_no_big_rain_at_sowing_and_other_crops_keep_it():
    """Owner's answer 3, 2026-11-14 night: paddy is flooded at transplanting, so rice keeps only big rain at harvest."""
    from pipeline.fetch.cropslib import load_crops
    from pipeline.fetch.rules import load_rules
    lib, rules = load_crops(), load_rules()
    crops = [{"crop": "rice", "start": "06-15", "end": "10-12"}, {"crop": "lentil", "start": "11-01", "end": "03-15"}]
    checks = {(c["crop"], k) for k, _, c, *_ in wa._candidates(crops, lib, rules)}
    assert ("rice", "big_rain_harvest") in checks and ("rice", "big_rain_sowing") not in checks
    assert {("lentil", "big_rain_sowing"), ("lentil", "big_rain_harvest")} <= checks


def test_a_window_counts_in_a_block_only_when_it_holds_half_of_one_or_the_other():
    nov = {"key": "Nov", "from": "11-15", "to": "12-14"}
    dec = {"key": "Dec", "from": "12-15", "to": "01-14"}
    assert wa.attaches(nov, ("10-30", "02-21"))           # covers the whole block
    assert not wa.attaches(nov, ("12-10", "12-20"))       # 5 of its 11 days, 5 of the block's 30
    assert wa.attaches(dec, ("12-10", "12-20"))           # 6 of its 11 days
    assert wa.attaches(nov, ("12-05", "12-14"))           # all 10 of its days


def _frame(start, values, rain=None):
    d = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"date": d, "t": np.asarray(values, float),
                         "rain": np.asarray(rain if rain is not None else [0.0] * len(values), float)})


def test_a_year_is_hit_when_one_tested_day_passes_the_limit():
    # one block (Nov: 15 Nov - 14 Dec 2002), window 1-10 Dec: only 1-10 Dec are tested
    w = _frame("2002-11-15", [5.0] * 30)
    w.loc[w["date"] == "2002-11-20", "t"] = 0.5          # outside the window: not tested
    out = wa.year_values(w, "t", {"at_or_below_c": 1}, "cold", 11, 15, [2002], ("12-01", "12-10"))
    assert out == {2002: {"hit": False, "n": 0}}
    w.loc[w["date"] == "2002-12-03", "t"] = 1.0           # inside, and 1 C counts ('1 C or less')
    out = wa.year_values(w, "t", {"at_or_below_c": 1}, "cold", 11, 15, [2002], ("12-01", "12-10"))
    assert out == {2002: {"hit": True, "n": 1}}
    out = wa.year_values(w, "t", {"below_c": 1}, "cold", 11, 15, [2002], ("12-01", "12-10"))
    assert out[2002]["hit"] is False                      # strictly below 1: 1.0 does not count


def test_a_dry_spell_year_is_one_with_no_wet_day_in_the_tested_days():
    rain = [0.0] * 30
    rain[20] = 0.9                                        # 5 Dec: under 1 mm is still dry
    w = _frame("2002-11-15", [10.0] * 30, rain)
    out = wa.year_values(w, "rain", None, "dry_spell", 11, 15, [2002], ("12-01", "12-10"))
    assert out[2002]["hit"] is True
    w.loc[w["date"] == "2002-12-06", "rain"] = 1.0        # 1 mm is a wet day
    out = wa.year_values(w, "rain", None, "dry_spell", 11, 15, [2002], ("12-01", "12-10"))
    assert out[2002]["hit"] is False


def test_big_rain_is_twenty_mm_or_more_on_a_tested_day():
    rain = [0.0] * 30
    rain[17] = 19.9                                       # 2 Dec
    w = _frame("2002-11-15", [10.0] * 30, rain)
    assert wa.year_values(w, "rain", None, "big_rain", 11, 15, [2002], ("12-01", "12-10"), big_mm=20)[2002]["hit"] is False
    w.loc[w["date"] == "2002-12-02", "rain"] = 20.0
    out = wa.year_values(w, "rain", None, "big_rain", 11, 15, [2002], ("12-01", "12-10"), big_mm=20)
    assert out[2002] == {"hit": True, "n": 1}


def test_the_longest_dry_run_inside_a_block():
    #          dry dry WET dry dry dry wet(1.0) dry
    rain = [0, 0.5, 3, 0, 0, 0.9, 1.0, 0]
    assert wa.longest_run(np.array(rain) < 1.0) == 3
    assert wa.longest_run(np.array([], bool)) == 0


def test_typical_and_worst_years():
    runs = {2002: 10, 2003: 31, 2004: 12, 2005: 31, 2006: 9, 2007: 20}
    t = wa.typical_worst(runs)
    assert t["typical"] == 16                             # median (12 + 20) / 2 = 16
    assert t["worst"] == [{"year": 2005, "days": 31}, {"year": 2003, "days": 31}, {"year": 2007, "days": 20}]
    assert wa.typical_worst({2002: 3, 2003: 4})["typical"] == 4   # 3.5 rounds half up


def test_most_years_means_at_least_half():
    assert wa.often(12, 24) == "most"
    assert wa.often(11, 24) == "some"
    assert wa.often(1, 24) == "some"
    assert wa.often(0, 24) is None


def test_the_biggest_danger_is_the_one_seen_in_the_most_years():
    ds = [{"kind": "big_rain", "crop": "potato", "years": 9}, {"kind": "dry_spell", "crop": "wheat", "years": 9},
          {"kind": "cold", "crop": "wheat", "years": 3}, {"kind": "cold", "crop": "potato", "years": 9},
          {"kind": "heat", "crop": "potato", "years": 0}]
    ranked = wa.rank(ds, crop_order=["rice", "potato", "wheat"])
    assert [(d["kind"], d["crop"]) for d in ranked] == [("cold", "potato"), ("dry_spell", "wheat"),
                                                        ("big_rain", "potato"), ("cold", "wheat")]   # N = 0 left out


def test_is_it_changing():
    rising = {2002 + i: float(i) for i in range(24)}
    assert wa.change_word(rising, 0.05) == "more_common"
    assert wa.change_word({y: -v for y, v in rising.items()}, 0.05) == "less_common"
    assert wa.change_word({2002 + i: 2.0 for i in range(24)}, 0.05) == "cant_tell"      # the same every year
    assert wa.change_word({2002: 1.0, 2003: 2.0, 2004: 0.0}, 0.05) == "cant_tell"       # fewer than 4 years
    flat = {2002 + i: float(i % 2) for i in range(24)}                                 # 0, 1, 0, 1, ...
    assert wa.change_word(flat, 0.05) == "about_same"


def test_temperature_trends_leave_out_blocks_touching_2001_to_2003():
    assert wa.clean_years([2001, 2002, 2003, 2004, 2005], 11, [2001, 2002, 2003]) == [2004, 2005]
    # Poush 2003 runs 15 Dec 2003 - 14 Jan 2004: it touches 2003
    assert wa.clean_years([2003, 2004], 12, [2001, 2002, 2003]) == [2004]


def test_drying_is_thirds_of_the_twelve_block_means_with_wind_and_sun_in_their_top_third():
    # rules.yaml soil_drying: ET0 sorted 1.5 1.6 2.0 2.2 | 2.8 3.2 3.4 3.5 | 3.6 4.2 4.5 4.8
    et0 = [1.6, 2.2, 3.4, 4.5, 4.8, 4.2, 3.6, 3.5, 3.2, 2.8, 2.0, 1.54]
    wind = [1.0, 1.1, 1.6, 1.7, 1.5, 1.2, 0.9, 0.8, 0.85, 0.95, 1.3, 1.4]   # top four: Mar Apr May Dec
    sun = [12, 15, 19, 22, 23, 18, 14, 15.5, 15, 16, 13, 11]                # top four: Mar Apr May Jun
    d = wa.drying(et0, wind, sun, ["slow", "medium", "fast"])
    assert [x["word"] for x in d] == ["slow", "slow", "medium", "fast", "fast", "fast", "fast", "medium", "medium", "medium",
                                      "slow", "slow"]
    assert [m for m, x in zip(wa.KEYS, d) if x["wind"]] == ["Mar", "Apr", "May", "Dec"]
    assert [m for m, x in zip(wa.KEYS, d) if x["sun"]] == ["Mar", "Apr", "May", "Jun"]
    assert d[11]["et0_mm_day"] == 1.5 and d[0] == {"et0_mm_day": 1.6, "word": "slow", "wind": False, "sun": False}


def test_rain_and_temperature_words_are_terciles_of_the_twelve_blocks():
    rain = [5, 10, 20, 50, 130, 220, 340, 320, 170, 45, 6, 8]
    # sorted: 5 6 8 10 | 20 45 50 130 | 170 220 320 340
    assert wa.words12(rain, ["dry", "some_rain", "wet"]) == ["dry", "dry", "some_rain", "some_rain", "some_rain", "wet",
                                                              "wet", "wet", "wet", "some_rain", "dry", "dry"]
    with pytest.raises(ValueError):
        wa.words12(rain[:11], ["a", "b", "c"])
