"""Per-year replay events (contract: none, drought, flood), rules in rules.yaml `events`, sources opened
2026-11-12: rainfall deciles (Gibbs & Maher 1967, classes per NDMC) and ETCCDI's Rx1day. The flood rule is
fixed in advance from those sources, never tuned on the known floods, which are validation layer 4.1
(owner, 2026-11-12). Frost
is not a replay event (owner, 2026-11-12, REVIEW_NOTES M1): it is shown only as a risk band in the monthly
calendar."""
import pytest
import yaml

from pipeline.fetch.rules import RULES_PATH, load_rules
from pipeline.plans import events as ev

R = load_rules()["events"]
R_SOURCES = {k: v["source"] for k, v in yaml.safe_load(RULES_PATH.read_text())["events"].items()}


def _s(crop, year, rain=500.0, maxday=40.0):
    return {"crop": crop, "year": year, "rain_mm": rain, "rain_max_day_mm": maxday}


def test_the_rules_have_no_frost_event():
    assert "frost" not in R and R["precedence"] == ["drought", "flood"]


def test_the_driest_fifth_of_a_crops_seasons_is_drought():
    seasons = [_s("rice", 2001 + i, rain=100.0 + 10 * i) for i in range(25)]
    flags = ev.season_flags(seasons, R)
    assert [s["year"] for s, f in zip(seasons, flags) if "drought" in f] == [2001, 2002, 2003, 2004, 2005]


def test_deciles_are_per_crop():
    seasons = [_s("rice", 2001 + i, rain=1000.0 + i) for i in range(10)] + \
              [_s("wheat", 2001 + i, rain=50.0 + i) for i in range(10)]
    flags = ev.season_flags(seasons, R)
    assert sum("drought" in f for f in flags[:10]) == 2 and sum("drought" in f for f in flags[10:]) == 2


def test_the_flood_rule_is_a_decile_class_not_a_fixed_amount():
    assert R["flood_decile_min"] == 9 and "flood_day_mm" not in R
    assert "Rx1day" in R_SOURCES["flood_decile_min"] and "9-10" in R_SOURCES["flood_decile_min"]


def test_the_years_with_the_heaviest_day_in_deciles_9_10_are_flood_years():
    """25 years, wettest day 40 + i mm: the top fifth (ranks 21-25, deciles 9-10) are floods, whatever the mm."""
    seasons = [_s("rice", 2001 + i, maxday=40.0 + i) for i in range(25)]
    assert ev.flood_years(seasons, R) == {2021, 2022, 2023, 2024, 2025}


def test_a_years_heaviest_day_is_taken_over_all_its_seasons():
    """Rx1day of a year = its wettest crop-season day, whichever crop it fell in; a dry winter does not flood."""
    seasons = [_s("rice", 2001 + i, maxday=60.0) for i in range(10)] + \
              [_s("potato", 2001 + i, maxday=5.0) for i in range(10)]
    seasons[2]["rain_max_day_mm"] = 90.0             # 2003 rice
    seasons[17]["rain_max_day_mm"] = 95.0            # 2008 potato
    assert ev.flood_years(seasons, R) == {2003, 2008}


def test_ties_share_an_average_rank():
    """Equal heaviest days get the same decile, so ties never split by list order."""
    seasons = [_s("rice", 2001 + i, maxday=50.0) for i in range(10)]
    assert ev.flood_years(seasons, R) == set()       # all rank 5.5 -> decile 6


def test_a_year_takes_one_event_by_precedence_and_every_year_gets_one():
    seasons = [_s("potato", 2001 + i, rain=100.0 + i) for i in range(10)] + \
              [_s("rice", 2001 + i, maxday=40.0 + i) for i in range(10)]
    seasons[10]["rain_max_day_mm"] = 120.0          # 2001: driest potato season AND the heaviest day of the record
    years = ev.year_events(seasons, R)
    assert years["2001"] == "drought"               # drought before flood
    assert years["2010"] == "flood"                 # 2nd heaviest day: decile 10
    assert years["2005"] == "none"
    assert sorted(years) == [str(y) for y in range(2001, 2011)]
    assert set(years.values()) <= {"none", "drought", "flood"}


def test_a_freezing_night_never_produces_an_event():
    """Even a season carrying a frost Tmin far below every former threshold (wheat 0 C, potato -2 C) gets none."""
    seasons = [{**_s(c, 2001 + i), "tmin_frost_min_c": -10.0, "tmin_frost_min_mid_c": -10.0}
               for c in ("wheat", "potato") for i in range(10)]
    seasons = [{**s, "rain_mm": 500.0 + i} for i, s in enumerate(seasons)]   # ranks: deciles 1-2 are drought
    flags = ev.season_flags(seasons, R)
    assert not any("frost" in f for f in flags)
    assert "frost" not in set(ev.year_events(seasons, R).values())


def test_an_event_outside_the_contract_in_the_precedence_is_refused():
    with pytest.raises(ValueError, match="frost"):
        ev.year_events([_s("rice", 2001)], {**R, "precedence": ["drought", "flood", "frost"]})
