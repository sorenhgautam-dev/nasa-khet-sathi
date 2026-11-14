"""The 25-Year Replay's window runs (pipeline/plans/window.py, rules.yaml window_replay) and the ONI reader
(pipeline/fetch/oni.py). The window run must give the existing twin's days (twin/season.simulate) exactly."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import oni
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.guards import DataGuardError
from pipeline.plans import window as win
from pipeline.twin import season as s

LIB = load_crops()
SOIL = pd.DataFrame({"top_cm": [0, 30, 100], "bottom_cm": [30, 100, 200],
                     "theta_fc_m3m3": [0.32, 0.33, 0.33], "theta_wp_m3m3": [0.15, 0.20, 0.22]})
CN = {"bare": 91, "wheat": 83, "rice": 83, "potato": 85}
SURFACE = {"method": "fao56_surface_layer", "tew_mm": 25.7, "rew_mm": 9.0, "kc_max": 1.2}
CLASSES = {"worked_min": 80, "failed_below": 50}


def _weather(start="2015-10-01", end="2016-12-31"):
    d = pd.date_range(start, end)
    i = np.arange(len(d))
    return pd.DataFrame({"date": d, "et0_mm": 3.0 + 1.5 * np.sin(i / 30.0), "rain_mm": np.where(i % 9 == 0, 22.0, 0.0),
                         "u2_ms": 1.5 + 0.5 * np.cos(i / 11.0), "rhmin_pct": 40.0 + 15 * np.sin(i / 50.0)})


@pytest.mark.parametrize("bare,kc_climate", [(0.3, False), (SURFACE, False), (SURFACE, True)])
def test_a_window_from_field_capacity_gives_the_twins_own_days(bare, kc_climate):
    w = _weather()
    plan = [("wheat", "2015-11-15"), ("rice", "2016-06-25")]
    daily, _ = s.simulate(w, plan, LIB, SOIL, CN, bare_kc=bare, irrigated=False, kc_climate=kc_climate)
    seasons = win.crop_seasons([{"crop": "wheat", "start": "11-15"}, {"crop": "rice", "start": "06-25"}], LIB,
                               "2015-10-01", "2016-04-30")
    ours = win.run_window(w, [x for x in seasons if pd.Timestamp("2015-10-01") <= x[1] < pd.Timestamp("2017-01-01")], LIB, SOIL, CN, bare, pd.Timestamp("2015-10-01"),
                          pd.Timestamp("2016-04-30"), 0.0, kc_climate=kc_climate)
    ref = daily[daily["date"] <= "2016-04-30"]
    assert len(ours) == len(ref)
    for col in ("eta_mm", "etc_mm", "dr_mm"):
        np.testing.assert_allclose(ours[col].to_numpy(), ref[col].to_numpy(), atol=1e-9)
    assert (ours["dry_day"].to_numpy() == ref["dry_day"].to_numpy()).all()


@pytest.mark.parametrize("kc_climate", [False, True])
def test_a_crop_in_the_ground_restarts_from_the_twins_state_and_gives_its_days(kc_climate):
    """Started mid-season with the twin's own depletion of the day before, the window continues the twin exactly."""
    w = _weather()
    daily, _ = s.simulate(w, [("wheat", "2015-11-15")], LIB, SOIL, CN, bare_kc=SURFACE, irrigated=False, kc_climate=kc_climate)
    day = pd.Timestamp("2016-01-20")
    prev = daily[daily["date"] == day - pd.Timedelta(1, unit="D")].iloc[0]
    seasons = [("wheat", pd.Timestamp("2015-11-15"), pd.Timestamp("2015-11-15") + pd.Timedelta(139, unit="D"))]
    ours = win.run_window(w, seasons, LIB, SOIL, CN, SURFACE, day, pd.Timestamp("2016-05-19"),
                          prev["dr_mm"] / prev["taw_mm"], kc_climate=kc_climate)
    ref = daily[(daily["date"] >= day) & (daily["date"] <= "2016-05-19")]
    np.testing.assert_allclose(ours["eta_mm"].to_numpy(), ref["eta_mm"].to_numpy(), atol=1e-9)
    np.testing.assert_allclose(ours["dr_mm"].to_numpy(), ref["dr_mm"].to_numpy(), atol=1e-9)
    assert ours["crop"].iloc[0] == "wheat" and ours["crop"].iloc[-1] is None   # wheat ends 2016-04-02, then bare


def test_windows_seasons_and_starts_as_the_rules_say():
    assert win.window_end("2026-11-04", 3) == pd.Timestamp("2027-02-03")
    assert win.window_end("2026-11-04", 6) == pd.Timestamp("2027-05-03")
    seas = win.crop_seasons([{"crop": "rice", "start": "06-23"}, {"crop": "potato", "start": "10-30"}], LIB,
                            "2010-11-04", "2011-05-03")
    inside = win.in_window(seas, "2010-11-04", "2011-05-03")
    assert [(x["crop"], str(x["sow"].date()), x["in_ground_at_start"]) for x in inside] == [("potato", "2010-10-30", True)]
    # potato p 0.35 (crops.json): dry = (1 + 0.35) / 2 = 0.675, medium = 0.35 / 2 = 0.175, wet = 0
    assert [win.start_fraction(k, 0.35) for k in ("dry", "medium", "wet")] == pytest.approx([0.675, 0.175, 0.0])
    assert win.start_of(4.195 / 96.9, 0.35) == "medium" and win.start_of(0.36, 0.35) == "dry"


def test_score_class_and_reason_worked_numbers():
    d = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=6), "crop": [None, "potato", "potato", "potato", None, None],
                      "eta_mm": [1, 2, 2, 1, 1, 1.0], "etc_mm": [1, 2, 2, 2, 1, 1.0],
                      "dry_day": [False, False, True, True, False, False], "rain_mm": [0, 5, 0, 0, 0, 1.0]})
    out = win.summarise(d, "2020-01-05", CLASSES)
    # WRSI over the crop days: 100 x (2 + 2 + 1) / (2 + 2 + 2) = 83.3 -> 83, worked (80 or more)
    assert out == {"result": "worked", "score": 83, "dry_days": 2, "rain_mm": 5.0,
                   "reason": {"code": "dry_spell", "month": "01", "days": 2}}
    assert [win.classify(x, CLASSES) for x in (80, 79, 50, 49, None)] == ["worked", "struggled", "struggled", "failed", None]
    assert win.summarise(d.assign(dry_day=False), "2020-01-06", CLASSES)["reason"] == {"code": "no_dry_days"}
    assert win.summarise(d.assign(crop=None), "2020-01-06", CLASSES) | {} == {
        "result": None, "score": None, "dry_days": 0, "rain_mm": 6.0, "reason": {"code": "no_crop_in_window"}}


ONI_TEXT = """ SEAS  YR   TOTAL   ANOM
  JAS 2026  29.12   2.16
  ASO 2026  29.23   2.46
  NDJ 2025  26.00  -0.50
  OND 2025  26.10  -0.49
"""


def test_oni_parse_states_and_the_season_before_the_start():
    df = oni.parse(ONI_TEXT)
    assert list(df.columns) == ["season", "year", "total_c", "anom_c"] and len(df) == 4
    now = oni.last_season_before(df, "2026-11-04")
    assert (now["season"], now["year"], now["anom_c"]) == ("ASO", 2026, 2.46)
    assert oni.last_season_before(df, "2026-02-01")["season"] == "NDJ"      # NDJ 2025 ends January 2026
    assert [oni.state(x, 0.5) for x in (0.5, 0.49, -0.49, -0.5)] == ["el_nino", "neutral", "neutral", "la_nina"]
    with pytest.raises(DataGuardError):
        oni.parse(ONI_TEXT.replace("SEAS", "SEASON"))
    with pytest.raises(DataGuardError):
        oni.parse(ONI_TEXT + "  XYZ 2026  1 2\n")
