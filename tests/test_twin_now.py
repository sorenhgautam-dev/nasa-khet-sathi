"""Build step 10: the twin's state "now" (pipeline/fetch/now.py, scripts/run_twin_now.py; rules.yaml probe.kalman).
The near-real-time days must be built exactly as pipeline/fetch/weather.py builds weather.parquet: the history is rebuilt
by the same code and must equal weather.parquet before any 2026 day is written."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import now

REPO = Path(__file__).resolve().parents[1]
CLEAN = REPO / "data" / "clean" / "demo"
COLS = ["tmax_c", "tmin_c", "rh_pct", "ws2m_ms", "rs_mj_m2_day"]


def _power(days=10, solar_until=7, met_until=9):
    d = pd.date_range("2026-11-01", periods=days)
    df = pd.DataFrame({"date": d, **{c: np.arange(days, dtype=float) + 1 for c in COLS}, "rain_mm": 1.0})
    df.loc[df.index > met_until - 1, ["tmax_c", "tmin_c", "rh_pct", "ws2m_ms", "rain_mm"]] = np.nan
    df.loc[df.index > solar_until - 1, "rs_mj_m2_day"] = np.nan
    return df


def test_the_last_complete_power_day_is_set_by_the_latest_input():
    # meteorology to day 9 (9 Nov), solar to day 7 (7 Nov): the last day with every input is 7 Nov
    assert now.last_complete_day(_power(), COLS) == pd.Timestamp("2026-11-07")


def test_a_gap_before_the_last_complete_day_fails_loudly():
    df = _power()
    df.loc[2, "tmax_c"] = np.nan
    with pytest.raises(now.g.DataGuardError, match="2026-11-03"):
        now.last_complete_day(df, COLS)


def test_as_of_is_the_last_day_both_sources_have():
    gpm = pd.DataFrame({"date": pd.date_range("2026-11-01", periods=10), "rain_mm": 0.5})
    assert now.as_of_day(_power(), gpm, COLS) == pd.Timestamp("2026-11-07")
    gpm.loc[gpm.index > 4, "rain_mm"] = np.nan                       # IMERG Late only to 5 Nov
    assert now.as_of_day(_power(), gpm, COLS) == pd.Timestamp("2026-11-05")


def test_joining_the_two_tables_needs_consecutive_days_and_the_same_columns():
    a = pd.DataFrame({"date": pd.date_range("2025-12-30", periods=2), "x_mm": [1.0, 2.0]})
    b = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=2), "x_mm": [3.0, 4.0]})
    assert list(now.join_weather(a, b)["x_mm"]) == [1.0, 2.0, 3.0, 4.0]
    with pytest.raises(ValueError, match="consecutive"):
        now.join_weather(a, b.assign(date=pd.date_range("2026-01-02", periods=2)))
    with pytest.raises(ValueError, match="columns"):
        now.join_weather(a, b.rename(columns={"x_mm": "y_mm"}))


@pytest.mark.skipif(not (CLEAN / "weather.parquet").exists(), reason="needs the demo field's cleaned data")
def test_the_history_is_rebuilt_exactly_as_weather_py_built_it():
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.rules import load_rules
    field, rules = load_field("demo"), load_rules()
    inputs = now.history_inputs(field, REPO / "data")
    out = now.build_days(field, inputs, power_new=None, gpm_new=None, rules=rules)
    w = pd.read_parquet(CLEAN / "weather.parquet")
    rep = now.reproduction(out["table"], w)
    assert rep["rows"] == len(w) and rep["identical"], rep


@pytest.mark.skipif(not (CLEAN / "twin_state.json").exists(), reason="run scripts/run_twin_now.py first")
def test_the_twin_state_has_the_keys_the_sections_code_reads():
    s = json.loads((CLEAN / "twin_state.json").read_text())
    for k in ("field", "date", "plan", "water_case", "crop", "dr_mm", "taw_mm", "raw_mm", "ks", "wetness_pct",
              "p0_var", "prior_var", "sure_prior", "q_var_per_day", "sources", "labels"):
        assert k in s, k
    assert 0 <= s["wetness_pct"] <= 100 and 0 <= s["sure_prior"] <= 1 and 0 <= s["ks"] <= 1
    assert s["wetness_pct"] == pytest.approx(100 * (1 - s["dr_mm"] / s["taw_mm"]), abs=0.01)     # stored to 2 decimals
    assert s["prior_var"] <= s["p0_var"] and s["q_var_per_day"] >= 0
    card = json.loads((REPO / "data" / "cards" / "demo" / "weather_now.json").read_text())
    assert s["date"] == card["date_range"][1]
