"""REVIEW_2 H6, stage A: the exporter builds any field from its config and its own cards, and the index is built from
every config. The demo's content must not change. Every test has a worked number."""
import json

import pytest

from pipeline.export import build_field_json as b
from pipeline.export.validate import validate_index

DEMO = {"id": "demo", "name": "Bhaktapur demo field (PLACEHOLDER location and rotation)", "country": "Nepal",
        "lat": 27.690767, "lon": 85.441792, "water_source": None, "validation_station": "NP000444540",
        "correction_label": "Kathmandu-valley correction", "bbox": [85.379227, 27.625034, 85.480773, 27.714966],
        "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]}
CARDS = {"power": {"version": "v2.10.3", "date_range": ["2001-01-01", "2025-12-31"]},
         "gpm": {"date_range": ["2001-01-01", "2025-12-31"],
                 "segments": [{"product": "final", "from": "2001-01-01", "to": "2025-09-30"},
                              {"product": "late", "from": "2025-10-01", "to": "2025-12-31"}]},
         "grace": {"date_range": ["2002-04-17", "2026-09-16"]},
         "ghcn": {"date_range": ["2001-01-01", "2025-08-24"]},
         "modis": {},
         "weather": {"date_range": ["2001-01-01", "2025-12-31"],
                     "corrections": {"tmin_c": {"applied": True}, "tmax_c": {"applied": True},
                                     "rain_break": {"applied": True, "from": "2017-01-01", "reference_years": [2001, 2016]}}}}


# --- the skeleton: identity from the config, no site file needed ---

def test_the_skeleton_comes_from_the_config_alone():
    s = b.skeleton(DEMO)
    assert list(s) == ["field", "diary", "plans", "replay", "future", "sources", "method"]
    assert s["field"] == {"name": DEMO["name"], "lat": 27.690767, "lon": 85.441792, "water_source": "unknown", "sections": []}
    assert s["future"] is None and s["method"] == {"season_detection": None}


# --- sources from the field's config and cards ---

def test_the_demos_sources_come_out_the_same_from_its_config_and_cards():
    assert b.sources_block(field=DEMO, cards=CARDS) == b.sources_block()


def test_the_station_row_is_measured_from_the_field_and_names_its_use():
    assert b.station_distance_text(27.690767, 85.441792, 27.700, 85.367) == "one point, 7 km west"     # 7.4 km at 278 deg
    assert b.station_distance_text(-18.834125, 47.436917, -18.800, 47.483) == "one point, 6 km north-east"
    abroad = {**DEMO, "id": "ambohidratrimo", "name": "Abroad (PLACEHOLDER)", "lat": -18.834125, "lon": 47.436917,
              "validation_station": "MA000067083", "correction_label": None}
    cards = {**CARDS, "weather": {**CARDS["weather"], "corrections": {"tmin_c": {"applied": False},
                                                                      "rain_break": {"applied": False}}}}
    s = {x["name"]: x for x in b.sources_block(field=abroad, cards=cards)}
    assert "Kathmandu Airport station" not in s
    st = s["Antananarivo/Ivato station"]
    assert st["product"] == "NOAA GHCN-Daily MA000067083 (checks only)" and st["resolution"] == "one point, 6 km north-east"
    assert "scaled back" not in s["GPM IMERG"]["product"] and "corrected to" not in s["NASA POWER"]["product"]
    assert s["GPM IMERG"]["product"] == "V07 Final daily (Late for Oct-Dec 2025)"


def test_a_field_without_a_station_or_modis_card_has_no_such_rows():
    field = {k: v for k, v in DEMO.items() if k not in ("validation_station", "correction_label")}
    cards = {k: v for k, v in CARDS.items() if k not in ("ghcn", "modis")}
    names = [x["name"] for x in b.sources_block(field=field, cards=cards)]
    assert "Kathmandu Airport station" not in names and "MODIS Terra" not in names and len(names) == 7


# --- the rain-check inputs are optional ---

RULES = {"gpm_series": {"level_caveat_ratio": 1.25}}


def test_rain_context_uses_the_normal_and_the_station_band_only_when_the_field_has_them():
    rc = {"normals_mm": {"Bhaktapur": {"annual": 1375.0}, "Kathmandu Airport": {"annual": 1502.0}},
          "break_correction": {"twin_rain_vs_station_all_shared_months": {"ratio": 1.5}}}
    c = b.rain_context(rc, 1853.0, RULES)
    # 1853 / 1375 = 1.35 >= 1.25; the station has 1 - 1/1.5 = 0.333 less rain, inside 0.25..0.40
    assert c["rain_reads_high"] is True and c["rain_level"]["ratio"] == 1.35 and c["station_rain_lower"] is True
    assert c["rain_level"]["station_normal_mm"] == 1375.0                      # the first normal named: Bhaktapur
    none = b.rain_context({"normals_mm": {}, "break_correction": None}, 1619.0, RULES)
    assert none == {"rain_reads_high": False, "rain_level": None, "station_rain_lower": False}


# --- the index, from every config ---

def test_the_index_lists_fields_with_a_file_and_groups_the_samples_in_their_area(tmp_path):
    from pipeline.export.build_index import build_index
    cfgs = [DEMO,
            {**DEMO, "id": "sample-1", "name": "Bhaktapur sample field 1 (PLACEHOLDER)", "sample": True, "sample_of": "demo",
             "lat": 27.688458, "lon": 85.475542},
            {**DEMO, "id": "ambohidratrimo", "name": "Abroad", "country": "Madagascar", "lat": -18.834125, "lon": 47.436917,
             "bbox": [47.400997, -18.847986, 47.439003, -18.812014]}]
    (tmp_path / "fields").mkdir()
    (tmp_path / "area").mkdir()
    for f in ("demo", "sample-1"):
        (tmp_path / "fields" / f"{f}.json").write_text("{}")
    (tmp_path / "area" / "demo.json").write_text(json.dumps({"bbox": DEMO["bbox"]}))
    idx = build_index(cfgs, tmp_path)
    assert [f["id"] for f in idx["fields"]] == ["demo", "sample-1"]          # abroad: no file yet, so not listed
    assert idx["fields"][1] == {"id": "sample-1", "name": "Bhaktapur sample field 1 (PLACEHOLDER)", "country": "Nepal",
                                "lat": 27.688458, "lon": 85.475542, "bbox": DEMO["bbox"], "sample": True, "area": "demo"}
    assert idx["areas"] == [{"id": "demo", "name": "Bhaktapur demo field area", "bbox": DEMO["bbox"],
                             "map": "data/area/demo.json", "fields": ["demo", "sample-1"]}]
    assert validate_index(idx) == []


def test_the_index_refuses_an_area_that_names_an_unlisted_field_or_an_id_with_an_underscore():
    idx = {"fields": [{"id": "demo", "name": "d", "country": "Nepal", "lat": 27.69, "lon": 85.44, "bbox": DEMO["bbox"],
                       "sample": False, "area": "demo"}],
           "areas": [{"id": "demo", "name": "a", "bbox": DEMO["bbox"], "map": "data/area/demo.json", "fields": ["demo", "x"]}]}
    assert any("x" in e for e in validate_index(idx))
    bad = json.loads(json.dumps(idx))
    bad["areas"][0]["fields"] = ["demo"]
    bad["fields"][0]["id"] = "sample_1"
    assert validate_index(bad)
    abs_map = json.loads(json.dumps(idx))
    abs_map["areas"][0]["fields"] = ["demo"]
    abs_map["areas"][0]["map"] = "/data/area/demo.json"                       # every site path is relative
    assert validate_index(abs_map)


def test_the_sample_configs_carry_ids_the_index_accepts():
    from pathlib import Path

    from pipeline.fetch.fields import load_field
    ids = sorted(p.stem for p in (Path(b.REPO) / "config" / "fields").glob("*.yaml"))
    import re
    assert all(re.fullmatch(r"[a-z0-9-]+", i) for i in ids), ids
    for i in ids:
        assert load_field(i)["id"] == i


# --- a sample is corrected when its own break test finds the 2017 break (rules.yaml correction_for_samples, 810b3c8) ---

G = {"correction_fields": ["demo"], "correction_from": "2017-01-01", "correction_for_samples": "text"}


def test_a_sample_is_corrected_only_when_its_own_test_finds_the_break_in_2017():
    from pipeline.checks.rain_check import break_corrected
    sample = {"id": "sample-1", "sample_of": "demo"}
    assert break_corrected({"id": "demo"}, G, None) is True                          # listed: always
    assert break_corrected(sample, G, {"found": True, "year": 2017}) is True
    assert break_corrected(sample, G, {"found": True, "year": 2019}) is False        # another year: the owner decides
    assert break_corrected(sample, G, {"found": False, "year": None}) is False
    assert break_corrected(sample, G, None) is False                                 # not tested yet
    assert break_corrected({"id": "ambohidratrimo"}, G, {"found": True, "year": 2017}) is False   # not a sample
    assert break_corrected(sample, {k: v for k, v in G.items() if k != "correction_for_samples"},
                           {"found": True, "year": 2017}) is False                    # no rule, no correction


def test_the_weather_table_scales_a_sample_whose_test_found_the_break():
    import pandas as pd
    from pipeline.fetch.weather import correct_gpm_break
    days = pd.date_range("2001-01-01", "2018-12-31")
    rain = pd.DataFrame({"date": days, "rain_mm": 2.0, "rain_source": "gpm"})
    rain.loc[rain["date"] >= "2017-01-01", "rain_mm"] = 3.0          # GPM jumps by half in 2017
    gpm = pd.DataFrame({"date": days, "product": "final", "rain_mm": rain["rain_mm"]})
    rule = {**G, "correction_reference_years": [2001, 2016], "correction_products": ["final"],
            "correction_factor_products": ["final"], "correction": "c", "trend_caveat": "t"}
    sample = {"id": "sample-1", "sample_of": "demo"}
    out, info = correct_gpm_break(rain, gpm, rule, "sample-1", field=sample, break_test={"found": True, "year": 2017})
    after = out[(out["date"] >= "2017-01-01") & (out["date"].dt.month != 2)]      # February: leap years in the reference
    assert info["applied"] is True and after["rain_mm"].round(6).eq(2.0).all()           # 3 mm x (62 / 93) = 2 mm in a 31-day month
    _, info2 = correct_gpm_break(rain, gpm, rule, "sample-1", field=sample, break_test={"found": False, "year": None})
    assert info2["applied"] is False


def test_a_corrected_samples_method_page_quotes_its_own_gauge_evidence():
    # the demo's card summary rounds to the numbers rules.yaml break_evidence quotes for it
    s = {"gauge_weight_before_pct": [96.0, 98.0], "gauge_weight_after_yearly_pct": [56.0, 71.8],
         "gpcc_stations_before": 50.3, "gpcc_stations_after": 0.8}
    assert b.evidence_from_card(s) == {"gauge_weight_before_pct": [96, 98], "gauge_weight_after_pct": [56, 72],
                                       "gpcc_stations_before": 50, "gpcc_stations_after": 1}
