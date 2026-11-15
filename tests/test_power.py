"""Build step 2: NASA POWER daily point fetch. The fixture is a real two-day API response."""
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import power
from pipeline.fetch.guards import CARD_FIELDS, DataGuardError

FIXTURE = Path(__file__).parent / "fixtures" / "power_demo_20010101_20010102.json"
FIELD = {"id": "demo", "lat": 27.67, "lon": 85.43}


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


def test_url_asks_for_the_six_parameters_as_daily_point_ag_json():
    url = power.build_url(27.67, 85.43, "20010101", "20011231")
    for part in ["/api/temporal/daily/point", "community=AG", "format=JSON", "latitude=27.67",
                 "longitude=85.43", "start=20010101", "end=20011231"]:
        assert part in url
    for p in ["T2M_MAX", "T2M_MIN", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]:
        assert p in url


def test_parse_gives_unit_named_columns_with_the_real_values(payload):
    df, _ = power.parse(payload)
    assert list(df.columns) == ["date", "tmax_c", "tmin_c", "rh_pct", "ws2m_ms", "rs_mj_m2_day", "rain_mm"]
    first = df.iloc[0]
    assert first["date"] == pd.Timestamp("2001-01-01")
    assert first["tmax_c"] == 19.98 and first["tmin_c"] == 8.33 and first["rain_mm"] == 0.48


def test_parse_turns_fill_values_into_missing_and_counts_them(payload):
    payload["properties"]["parameter"]["RH2M"]["20010102"] = -999.0
    df, info = power.parse(payload)
    assert np.isnan(df.loc[1, "rh_pct"])
    assert info["fill_removed"]["rh_pct"] == 1 and info["fill_removed"]["tmax_c"] == 0


def test_parse_reads_the_header(payload):
    _, info = power.parse(payload)
    assert info["time_standard"] == "LST"
    assert info["api_version"] == "v2.10.3"
    assert info["fill_value"] == -999.0
    assert info["cell_elevation_m"] == 1269.39


def test_parse_prints_raw_attributes_before_converting(payload, capsys):  # rule 12a
    power.parse(payload)
    out = capsys.readouterr().out
    assert "T2M_MAX" in out and "_FillValue" in out and "-999" in out


def test_parse_fails_loudly_when_a_unit_changes(payload):
    payload["parameters"]["T2M_MAX"]["units"] = "K"
    with pytest.raises(DataGuardError, match="T2M_MAX"):
        power.parse(payload)


def test_parse_fails_when_a_parameter_is_missing(payload):
    del payload["properties"]["parameter"]["WS2M"]
    with pytest.raises(DataGuardError, match="WS2M"):
        power.parse(payload)


@pytest.mark.parametrize("param,value", [
    ("T2M_MAX", 61.0), ("T2M_MIN", -31.0), ("RH2M", 101.0), ("PRECTOTCORR", 501.0),
    ("PRECTOTCORR", -0.5), ("WS2M", -0.1), ("ALLSKY_SFC_SW_DWN", -1.0),
])
def test_check_fails_loudly_on_impossible_values(payload, param, value):
    payload["properties"]["parameter"][param]["20010102"] = value
    df, _ = power.parse(payload)
    with pytest.raises(DataGuardError):
        power.check(df)


def test_check_passes_the_real_values(payload):
    df, _ = power.parse(payload)
    assert power.check(df) == {"tmax_c": 0, "tmin_c": 0, "rh_pct": 0, "rain_mm": 0}


def test_check_fails_on_a_missing_day(payload):
    df, _ = power.parse(payload)
    df.loc[1, "date"] = pd.Timestamp("2001-01-03")
    with pytest.raises(DataGuardError, match="missing"):
        power.check(df)


def test_check_fails_on_a_repeated_day(payload):
    df, _ = power.parse(payload)
    df.loc[1, "date"] = df.loc[0, "date"]
    with pytest.raises(DataGuardError, match="repeated"):
        power.check(df)


def test_year_chunks_split_a_range_by_calendar_year():
    assert power.year_chunks("2001-12-30", "2002-01-02") == [("20011230", "20011231"), ("20020101", "20020102")]


def test_fetch_writes_table_and_card_and_reuses_the_cache(tmp_path, payload):
    calls = []

    def fake_get(url):
        calls.append(url)
        return copy.deepcopy(payload)

    out = power.fetch(FIELD, "2001-01-01", "2001-01-02", data_dir=tmp_path, get_json=fake_get)
    assert len(pd.read_parquet(out["table"])) == 2 and len(calls) == 1
    card = json.loads(Path(out["card"]).read_text())
    assert set(CARD_FIELDS) <= set(card)
    assert card["time_zone"].startswith("LST") and card["pixel_count"] == 1
    assert card["date_range"] == ["2001-01-01", "2001-01-02"]
    power.fetch(FIELD, "2001-01-01", "2001-01-02", data_dir=tmp_path, get_json=fake_get)
    assert len(calls) == 1  # second run read the cached raw file
    near = {"id": "kharipati", "lat": 27.686299, "lon": 85.463624}       # config power_point_of: the demo's cached point
    out = power.fetch(near, "2001-01-01", "2001-01-02", data_dir=tmp_path, get_json=fake_get, point=FIELD)
    assert len(calls) == 1 and "nothing downloaded" in json.loads(Path(out["card"]).read_text())["notes"]
    with pytest.raises(DataGuardError, match="not cached"):                              # never downloads
        power.fetch(near, "2002-01-01", "2002-01-02", data_dir=tmp_path, get_json=fake_get, point=FIELD)
    with pytest.raises(DataGuardError, match="POWER cells"):                             # another cell: refused
        power.fetch({**near, "lat": 27.8}, "2001-01-01", "2001-01-02", data_dir=tmp_path, get_json=fake_get, point=FIELD)


def test_fetch_keeps_each_field_in_its_own_folder(tmp_path, payload):
    out = power.fetch({"id": "kenya", "lat": 27.67, "lon": 85.43}, "2001-01-01", "2001-01-02",
                      data_dir=tmp_path, get_json=lambda url: copy.deepcopy(payload))
    assert Path(out["table"]) == tmp_path / "clean" / "kenya" / "power.parquet"
    assert Path(out["card"]) == tmp_path / "cards" / "kenya" / "power.json"
    assert list((tmp_path / "raw" / "power" / "kenya").glob("*/*.json"))


def test_fetch_refuses_a_response_for_the_wrong_dates(tmp_path, payload):
    with pytest.raises(DataGuardError, match="dates"):
        power.fetch(FIELD, "2002-01-01", "2002-01-02", data_dir=tmp_path,
                    get_json=lambda url: copy.deepcopy(payload))


def test_a_moved_field_point_does_not_reuse_the_old_points_cache(tmp_path, payload):
    """Owner, 2026-11-12: the demo field moved to a placeholder point; its POWER cache must not be reused."""
    calls = []

    def fake_get(url):
        calls.append(url)
        return copy.deepcopy(payload)

    power.fetch(FIELD, "2001-01-01", "2001-01-02", data_dir=tmp_path, get_json=fake_get)
    power.fetch({**FIELD, "lat": 27.6785, "lon": 85.427417}, "2001-01-01", "2001-01-02", data_dir=tmp_path,
                get_json=fake_get)
    assert len(calls) == 2 and "27.6785" in calls[1]
