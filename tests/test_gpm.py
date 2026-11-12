"""GPM IMERG daily V07 (D1, D6): the twin's rain. Final through the last Final day, then Late; per-day
subsets of the fetch box from GES DISC OPeNDAP. Synthetic subset files."""
import h5py
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import gpm


def test_grid_indices_cover_the_box_on_the_imerg_0_1_degree_grid():
    i0, i1, j0, j1 = gpm.box_indices([85.379227, 27.625034, 85.480773, 27.714966])
    assert (i0, i1) == (2653, 2654) and (j0, j1) == (1176, 1177)
    assert gpm.cell_index(27.6785, 85.427417) == (2654, 1176)       # field cell: 85.40-85.50 E, 27.60-27.70 N


def test_opendap_url_comes_from_the_archive_link():
    link = "https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGDF.07/2016/07/3B-DAY.MS.MRG.3IMERG.20160710-S000000-E235959.V07B.nc4"
    url = gpm.opendap_url(link, (2653, 2654, 1176, 1177))
    assert url.startswith("https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDF.07/2016/07/3B-DAY")
    assert url.endswith(".nc4.nc4?precipitation[0:0][2653:2654][1176:1177],lon[2653:2654],lat[1176:1177],time[0:0]")


def test_segments_switch_from_final_to_late_after_the_last_final_day():
    seg = gpm.segments(pd.Timestamp("2001-01-01"), pd.Timestamp("2025-12-31"), last_final=pd.Timestamp("2025-09-30"))
    assert seg == [("final", "2001-01-01", "2025-09-30"), ("late", "2025-10-01", "2025-12-31")]


def _subset(path, values, lon=(85.35, 85.45), lat=(27.65, 27.75), fill=-9999.9, units="mm/day"):
    with h5py.File(path, "w") as h:
        p = h.create_dataset("precipitation", data=np.array(values, dtype="float32").reshape(1, 2, 2))
        p.attrs["units"], p.attrs["_FillValue"] = np.bytes_(units), np.float32(fill)
        h.create_dataset("lon", data=np.array(lon, dtype="float32"))
        h.create_dataset("lat", data=np.array(lat))
    return path


def test_a_subset_gives_the_field_cell_and_the_box_mean(tmp_path):
    f = _subset(tmp_path / "d.nc4", [[1.0, 2.0], [3.0, 4.0]])          # [lon][lat]
    r = gpm.read_subset(f, field_cell=(1, 0))                             # lon index 1, lat index 0
    assert r["rain_mm"] == 3.0 and r["rain_box_mean_mm"] == 2.5


def test_fills_and_wrong_units_fail_loudly(tmp_path):
    with pytest.raises(ValueError, match="units"):
        gpm.read_subset(_subset(tmp_path / "a.nc4", [[1, 2], [3, 4]], units="mm/hr"), field_cell=(1, 0))
    r = gpm.read_subset(_subset(tmp_path / "b.nc4", [[1, 2], [-9999.9, 4]]), field_cell=(1, 0))
    assert np.isnan(r["rain_mm"])
    with pytest.raises(ValueError, match="range"):
        gpm.read_subset(_subset(tmp_path / "c.nc4", [[1, 2], [600.0, 4]]), field_cell=(1, 0))


def test_subset_coordinates_must_match_the_requested_cells(tmp_path):
    f = _subset(tmp_path / "d.nc4", [[1, 2], [3, 4]], lon=(80.05, 80.15))
    with pytest.raises(ValueError, match="grid"):
        gpm.read_subset(f, field_cell=(1, 0), expect_lon=(85.35, 85.45), expect_lat=(27.65, 27.75))


def test_a_second_opendap_host_can_serve_the_same_path():
    link = "https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/GPM_3IMERGDL.07/2025/10/3B-DAY-L.MS.MRG.3IMERG.20251001-S000000-E235959.V07B.nc4"
    urls = [gpm.opendap_url(link, (1, 2, 3, 4), host=h) for h in gpm.OPENDAP_HOSTS]
    assert len(urls) >= 2 and urls[1].startswith("https://gpm2.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGDL.07/")


# --- M2 (REVIEW_NOTES): raw attributes, honest card counts, from-cache rebuild, non-zero exit ---------------

def test_the_raw_precipitation_attributes_are_described_with_absent_ones_named(tmp_path):
    f = _subset(tmp_path / "d.nc4", [[1.0, 2.0], [3.0, 4.0]])
    a = gpm.raw_attributes(f)
    p = a["precipitation"]
    assert p["units"] == "mm/day" and p["_FillValue"] == pytest.approx(-9999.9, abs=1e-3)
    assert p["scale_factor"] == "ABSENT" and p["add_offset"] == "ABSENT" and p["valid_range"] == "ABSENT"


def test_a_fill_in_the_field_cell_is_reported_as_a_fill(tmp_path):
    r = gpm.read_subset(_subset(tmp_path / "b.nc4", [[1, 2], [-9999.9, 4]]), field_cell=(1, 0))
    assert np.isnan(r["rain_mm"]) and r["field_cell_fill"] is True
    r = gpm.read_subset(_subset(tmp_path / "c.nc4", [[1, 2], [3, -9999.9]]), field_cell=(1, 0))
    assert r["rain_mm"] == 3.0 and r["field_cell_fill"] is False


def test_days_without_a_file_are_sorted_by_reason():
    d = pd.date_range("2025-09-29", "2025-10-03")
    cached = {d[0], d[1]}
    cmr = {d[0]: "final", d[1]: "final", d[2]: "late", d[3]: "late"}          # 2025-10-03: no granule in CMR
    why = gpm.missing_days(d, cached, cmr_products=cmr, failures={"2025-10-01": "HTTP 500"})
    assert why == {"failed": ["2025-10-01"], "no_granule": ["2025-10-03"], "not_cached": ["2025-10-02"]}
    why = gpm.missing_days(d, cached, cmr_products=None, failures={})          # from cache: CMR not asked
    assert why == {"failed": [], "no_granule": [], "not_cached": ["2025-10-01", "2025-10-02", "2025-10-03"]}


def test_day_ranges_compress_consecutive_days():
    assert gpm.day_ranges(["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-07"]) == \
        ["2025-10-01..2025-10-03", "2025-10-07"]


GRID = dict(lon=(85.35, 85.45), lat=(27.65, 27.75))
FIELD = {"id": "t", "lat": 27.690767, "lon": 85.441792, "fetch_box": [85.379227, 27.625034, 85.480773, 27.714966]}


def _cache(tmp_path):
    raw = tmp_path / "raw" / "gpm" / "t"
    (raw / "final").mkdir(parents=True)
    (raw / "late").mkdir()
    _subset(raw / "final" / "2025-09-29.nc4", [[1.0, 2.0], [3.0, 4.0]], **GRID)
    _subset(raw / "final" / "2025-09-30.nc4", [[1.0, 2.0], [-9999.9, 4.0]], **GRID)    # a real fill in the field cell
    _subset(raw / "late" / "2025-10-02.nc4", [[0.5, 0.5], [7.5, 0.5]], **GRID)
    (raw / "failures.json").write_text('{"2025-10-01": "RuntimeError: HTTP 502"}\n')
    return raw


def test_from_cache_builds_the_table_and_an_honest_card_without_any_network(tmp_path, monkeypatch):
    import json
    import sys
    monkeypatch.setitem(sys.modules, "earthaccess", None)        # any import of earthaccess would fail
    monkeypatch.setitem(sys.modules, "requests", None)
    _cache(tmp_path)
    r = gpm.build_from_cache(FIELD, data_dir=tmp_path, start="2025-09-29", end="2025-10-03")
    df = pd.read_parquet(r["table"])
    assert list(df["rain_mm"].round(3).fillna(-1)) == [3.0, -1, -1, 7.5, -1]
    assert list(df["product"]) == ["final", "final", "late", "late", "late"]
    card = json.loads(r["card"].read_text())
    assert card["fill_values_removed"] == {"-9999.9 (_FillValue) in the field's cell": 1}
    assert card["records_dropped"] == 3
    assert card["date_range"] == ["2025-09-29", "2025-10-02"]                  # first and last day with a value
    assert "TODO-VERIFY" in card["time_zone"] and "05:45" in card["time_zone"]
    assert card["raw_attrs"]["precipitation"]["units"] == "mm/day"
    assert card["raw_attrs"]["precipitation"]["scale_factor"] == "ABSENT"
    seg = {s["product"]: s for s in card["segments"]}
    assert seg["final"]["to"] == "2025-09-30" and seg["late"]["from"] == "2025-10-01"
    assert seg["final"]["days_with_value"] == 1 and seg["final"]["days_fill_in_field_cell"] == 1
    assert seg["late"]["days_failed"] == 1 and seg["late"]["days_not_cached"] == 1
    assert r["missing"] == {"failed": ["2025-10-01"], "no_granule": [], "not_cached": ["2025-10-03"]}
    assert "from the cache" in card["notes"]


def test_main_exits_non_zero_and_lists_the_missing_days(tmp_path, capsys):
    _cache(tmp_path)
    code = gpm.main(["--field", "t", "--from-cache", "--start", "2025-09-29", "--end", "2025-10-03"],
                    data_dir=tmp_path, field=FIELD)
    err = capsys.readouterr().err
    assert code != 0 and "2025-10-01" in err and "2025-10-03" in err and "failed" in err


def test_main_exits_zero_when_every_day_has_a_file(tmp_path):
    _cache(tmp_path)
    code = gpm.main(["--field", "t", "--from-cache", "--start", "2025-09-29", "--end", "2025-09-30"],
                    data_dir=tmp_path, field=FIELD)
    assert code == 0                         # a real _FillValue is data, not a failed day
