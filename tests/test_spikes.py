"""Owner decision B: flag any day where one rain source exceeds 50 mm and is more than five times
another source. Flags are reported, never used to delete data."""
import numpy as np
import pandas as pd

from pipeline.checks.spikes import spike_days

MIN_MM, RATIO = 50, 5


def _s(values, start="2025-03-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=len(values)), "rain_mm": values})


def _flags(**sources):
    return spike_days(sources, MIN_MM, RATIO)


def test_the_dry_season_spike_is_flagged():
    (f,) = _flags(power=_s([233.66]), station=_s([3.8]))
    assert f["date"] == "2025-03-01" and f["high_source"] == "power" and f["low_source"] == "station"
    assert f["high_mm"] == 233.66 and f["low_mm"] == 3.8


def test_a_real_flood_seen_by_both_is_not_flagged():
    assert _flags(power=_s([93.26]), station=_s([194.1])) == []


def test_the_high_value_must_exceed_50_mm():
    assert _flags(a=_s([50.0]), b=_s([0.0])) == []
    assert len(_flags(a=_s([50.1]), b=_s([0.0]))) == 1


def test_the_high_value_must_be_more_than_five_times_the_other():
    assert _flags(a=_s([60.0]), b=_s([12.0])) == []          # exactly five times: not more than
    assert len(_flags(a=_s([60.0]), b=_s([11.9]))) == 1


def test_a_day_missing_from_the_other_source_is_not_compared():
    assert _flags(a=_s([233.0]), b=_s([np.nan])) == []


def test_any_source_can_be_the_high_one():
    (f,) = _flags(power=_s([3.0]), station=_s([120.0]))
    assert f["high_source"] == "station"


def test_three_sources_give_one_flag_per_pair_that_disagrees():
    flags = _flags(gpm=_s([4.0]), power=_s([233.0]), station=_s([3.0]))
    assert sorted((f["high_source"], f["low_source"]) for f in flags) == [("power", "gpm"), ("power", "station")]


# --- owner, 2026-11-12: when GPM arrives, the three sources vote on each flagged day ---
from pipeline.checks.spikes import vote  # noqa: E402


def _vote(power, station, gpm):
    sources = {"power": _s([power]), "station": _s([station]), "gpm": _s([gpm])}
    flags = spike_days({k: v for k, v in sources.items() if k != "gpm"}, MIN_MM, RATIO)
    return vote(flags, sources, MIN_MM, RATIO)[0]["vote"]


def test_gpm_agreeing_with_a_high_station_marks_a_real_local_storm():
    assert _vote(power=16.0, station=134.6, gpm=120.0)["label"] == "real local storm"


def test_gpm_agreeing_with_power_marks_the_station_suspect():
    assert _vote(power=16.0, station=134.6, gpm=15.0)["label"] == "station value suspect"


def test_gpm_agreeing_with_a_low_station_marks_a_power_spike():
    assert _vote(power=233.7, station=3.8, gpm=4.0)["label"] == "POWER spike"


def test_gpm_agreeing_with_both_leaves_the_day_undecided():
    assert _vote(power=11.0, station=60.0, gpm=30.0)["label"] == "undecided"


def test_without_a_gpm_value_there_is_no_vote_yet():
    assert _vote(power=233.7, station=3.8, gpm=np.nan)["label"] == "no third source yet"


def test_inputs_are_not_changed():
    a, c = _s([233.0]), _s([3.0])
    before = a.copy()
    _flags(a=a, c=c)
    pd.testing.assert_frame_equal(a, before)
