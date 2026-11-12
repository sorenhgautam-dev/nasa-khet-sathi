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
