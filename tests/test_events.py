"""Per-year replay events (contract: none, drought, flood), rules in rules.yaml `events`, sources opened
2026-11-12: rainfall deciles (Gibbs & Maher 1967, classes per NDMC), DHM Nepal rain-intensity scale. Frost
is not a replay event (owner, 2026-11-12, REVIEW_NOTES M1): it is shown only as a risk band in the monthly
calendar."""
import pytest

from pipeline.fetch.rules import load_rules
from pipeline.plans import events as ev

R = load_rules()["events"]


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


def test_a_very_heavy_rain_day_is_a_flood():
    seasons = [_s("rice", 2001 + i) for i in range(10)]
    seasons[3]["rain_max_day_mm"] = 100.0
    seasons[4]["rain_max_day_mm"] = 99.9
    flags = ev.season_flags(seasons, R)
    assert "flood" in flags[3] and "flood" not in flags[4]


def test_a_year_takes_one_event_by_precedence_and_every_year_gets_one():
    seasons = [_s("potato", 2001 + i, rain=100.0 + i) for i in range(10)] + [_s("rice", 2001 + i) for i in range(10)]
    seasons[0]["rain_max_day_mm"] = 120.0           # 2001: driest potato season AND a flood day
    seasons[15]["rain_max_day_mm"] = 150.0          # 2006: flood in rice
    years = ev.year_events(seasons, R)
    assert years["2001"] == "drought" and years["2006"] == "flood" and years["2005"] == "none"
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
