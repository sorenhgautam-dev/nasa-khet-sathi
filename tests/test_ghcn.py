"""NOAA GHCN-Daily station record (validation only). Format and units from the GHCN-Daily readme,
Version 3.35: PRCP tenths of mm, TMAX/TMIN tenths of degrees C, missing = -9999."""
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import ghcn
from pipeline.fetch.guards import CARD_FIELDS, DataGuardError

ST = "NP000444540"
SAMPLE = "\n".join([
    f"{ST},20150101,PRCP,25,,,S,",
    f"{ST},20150101,TMAX,182,,,S,",
    f"{ST},20150101,TMIN,-12,,,S,",
    f"{ST},20150102,PRCP,0,,,S,",
    f"{ST},20150102,TMAX,190,,G,S,",    # failed a quality check (Q-FLAG G): dropped
    f"{ST},20150102,SNWD,10,,,S,",      # element we do not use
    f"{ST},20150103,PRCP,-9999,,,S,",   # missing
    f"{ST},19990101,PRCP,50,,,S,",      # outside 2001-2025
]) + "\n"


def test_parse_converts_tenths_to_unit_named_columns():
    df, _ = ghcn.parse(SAMPLE, ST)
    row = df.set_index("date").loc[pd.Timestamp("2015-01-01")]
    assert row["rain_mm"] == pytest.approx(2.5) and row["tmax_c"] == pytest.approx(18.2)
    assert row["tmin_c"] == pytest.approx(-1.2)


def test_quality_flagged_values_are_dropped_and_counted():
    df, info = ghcn.parse(SAMPLE, ST)
    assert info["qc_dropped"]["tmax_c"] == 1
    assert np.isnan(df.set_index("date").loc[pd.Timestamp("2015-01-02"), "tmax_c"])


def test_missing_values_are_dropped_and_counted():
    _, info = ghcn.parse(SAMPLE, ST)
    assert info["missing_dropped"]["rain_mm"] == 1


def test_observation_times_are_counted_not_assumed():
    _, info = ghcn.parse(SAMPLE, ST)
    assert info["obs_time_present"] == 0
    _, info = ghcn.parse(SAMPLE.replace(f"{ST},20150101,PRCP,25,,,S,", f"{ST},20150101,PRCP,25,,,S,0845"), ST)
    assert info["obs_time_present"] == 1


def test_only_2001_to_2025_is_kept():
    df, _ = ghcn.parse(SAMPLE, ST)
    assert df["date"].min() >= pd.Timestamp("2001-01-01")


def test_records_per_year_counts_present_values():
    df, _ = ghcn.parse(SAMPLE, ST)
    assert ghcn.records_per_year(df, "rain_mm") == {2015: 2}


def test_a_row_from_another_station_is_refused():
    with pytest.raises(DataGuardError, match="station"):
        ghcn.parse(SAMPLE.replace(f"{ST},20150103", "XX000000000,20150103"), ST)


def test_impossible_temperature_fails_loudly():
    df, _ = ghcn.parse(SAMPLE.replace("TMAX,182", "TMAX,612"), ST)
    with pytest.raises(DataGuardError, match="tmax_c"):
        ghcn.check(df)


def test_fetch_writes_table_and_card_from_the_cache(tmp_path):
    calls = []

    def fake_get(url):
        calls.append(url)
        return gzip.compress(SAMPLE.encode())

    out = ghcn.fetch({"id": "demo"}, ST, data_dir=tmp_path, get_bytes=fake_get)
    assert Path(out["table"]) == tmp_path / "clean" / "demo" / f"ghcn_{ST}.parquet"
    card = json.loads(Path(out["card"]).read_text())
    assert set(CARD_FIELDS) <= set(card)
    ghcn.fetch({"id": "demo"}, ST, data_dir=tmp_path, get_bytes=fake_get)
    assert len(calls) == 1
