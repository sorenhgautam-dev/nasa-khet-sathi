"""NASA LP DAAC AppEEARS area requests for the field's fetch box (MODIS, SMAP). Only the request building
and the bundle file choice are tested here; the network calls are thin wrappers."""
import pytest

from pipeline.fetch import appeears as ap

BOX = [85.379227, 27.625034, 85.480773, 27.714966]


def test_area_task_covers_the_box_with_the_dates_and_layers():
    t = ap.area_task("demo_modis", BOX, "2001-01-01", "2025-12-31",
                     [("MOD13Q1.061", "_250m_16_days_NDVI"), ("MOD13Q1.061", "_250m_16_days_pixel_reliability")])
    assert t["task_type"] == "area" and t["task_name"] == "demo_modis"
    assert t["params"]["dates"] == [{"startDate": "01-01-2001", "endDate": "12-31-2025"}]
    assert t["params"]["layers"][1] == {"product": "MOD13Q1.061", "layer": "_250m_16_days_pixel_reliability"}
    assert t["params"]["output"] == {"format": {"type": "netcdf4"}, "projection": "native"}
    ring = t["params"]["geo"]["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1] and len(ring) == 5                      # GeoJSON rings are closed
    assert {(x, y) for x, y in ring} == {(85.379227, 27.625034), (85.480773, 27.625034),
                                         (85.480773, 27.714966), (85.379227, 27.714966)}


def test_only_data_files_are_downloaded_from_a_bundle():
    files = [{"file_name": "MOD13Q1.061_250m_aid0001.nc", "file_id": "a"},
             {"file_name": "demo-MOD13Q1-061-QA-lookup.csv", "file_id": "b"},
             {"file_name": "demo-request.json", "file_id": "c"},
             {"file_name": "README.md", "file_id": "d"}]
    assert [f["file_id"] for f in ap.wanted_files(files)] == ["a", "b", "c", "d"]
    assert [f["file_id"] for f in ap.wanted_files(files, only_nc=True)] == ["a"]


def test_credentials_are_never_part_of_the_task():
    t = ap.area_task("x", BOX, "2015-03-31", "2025-12-31", [("SPL4SMGP.008", "Geophysical_Data_sm_rootzone")])
    text = str(t).lower()
    assert "password" not in text and "token" not in text and "netrc" not in text


def test_dates_must_be_in_order():
    with pytest.raises(ValueError, match="before"):
        ap.area_task("x", BOX, "2025-12-31", "2001-01-01", [("MOD13Q1.061", "_250m_16_days_NDVI")])


# --- L7 (REVIEW_NOTES): a data card per downloaded task from the cached bundle only --------------------------
import json

import numpy as np

SINU = ('PROJCS["unknown",GEOGCS["unknown",DATUM["unknown",SPHEROID["unknown",6371007.181,0]],PRIMEM["Greenwich",0],'
        'UNIT["degree",0.0174532925199433]],PROJECTION["Sinusoidal"],PARAMETER["longitude_of_center",0],'
        'PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1]]')
FIELD = {"id": "t", "lat": 27.690767, "lon": 85.441792,
         "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]}


def _bundle(task_dir, complete=True):
    import h5py
    from rasterio.warp import transform as warp
    task_dir.mkdir(parents=True)
    xs, ys = warp("EPSG:4326", SINU, [85.4418], [27.6908])
    res = 231.6563582625
    x = xs[0] + res * (np.arange(4) - 1.5)
    y = ys[0] - res * (np.arange(3) - 1.0)
    with h5py.File(task_dir / "MOD13Q1.061_250m_aid0001.nc", "w") as h:
        t = h.create_dataset("time", data=np.array([30412800, 31795200], dtype="int32"))
        t.attrs["units"] = np.bytes_("seconds since 2000-01-01 00:00:00+00:00")
        h.create_dataset("xdim", data=x)
        h.create_dataset("ydim", data=y)
        c = h.create_dataset("crs", data=np.int8(0))
        c.attrs["spatial_ref"] = np.bytes_(SINU)
        ndvi = np.full((2, 3, 4), 5000, dtype="int16")
        ndvi[1, 0, 0] = -3000
        v = h.create_dataset("_250m_16_days_NDVI", data=ndvi)
        for k, val in (("_FillValue", np.array([-3000], dtype="int16")), ("units", np.bytes_("NDVI")),
                       ("scale_factor", np.array([0.0001])), ("add_offset", np.array([0.0])),
                       ("valid_min", np.array([-2000], dtype="int16")), ("valid_max", np.array([10000], dtype="int16")),
                       ("grid_mapping", np.bytes_("crs")), ("long_name", np.bytes_("250m 16 days NDVI"))):
            v.attrs[k] = val
    if complete:
        (task_dir / "COMPLETE").write_text(json.dumps(["MOD13Q1.061_250m_aid0001.nc"]) + "\n")


def test_a_task_card_is_built_from_the_cached_bundle_without_any_network(tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "requests", None)
    _bundle(tmp_path / "raw" / "appeears" / "t" / "modis")
    path = ap.write_task_card(FIELD, "modis", data_dir=tmp_path)
    card = json.loads(path.read_text())
    assert card["dataset"] == "modis" and card["product"] == "MOD13Q1.061"
    lay = card["raw_attrs"]["_250m_16_days_NDVI"]
    assert lay["units"] == "NDVI" and lay["scale_factor"] == 0.0001 and lay["_FillValue"] == -3000
    assert lay["valid_range"] == [-2000, 10000]
    assert card["fill_values_removed"]["_250m_16_days_NDVI"]["cells_with_fill"] == 1
    assert card["date_range"] == ["2000-12-18", "2001-01-03"] and card["records_dropped"]["time_steps"] == 2
    assert card["pixel_count"]["touching"] >= 1
    assert "later" in card["quality_flags_used"] and "diary" in card["quality_flags_used"]


def test_a_task_that_is_not_downloaded_is_skipped(tmp_path):
    _bundle(tmp_path / "raw" / "appeears" / "t" / "smap_l3_am", complete=False)
    assert ap.write_task_card(FIELD, "smap_l3_am", data_dir=tmp_path) is None
    assert ap.write_task_card(FIELD, "smap_l4_2015", data_dir=tmp_path) is None
