"""Windowed reads of cloud-optimised GeoTIFF assets over the fetch box (HLS-VI, ECOSTRESS tiled). Pure
helpers only; the network part is exercised by the real fetch."""
import pytest

from pipeline.fetch import cogwindows as cw

LINKS = ["https://x/HLS.S30.T45RUL.2021305T045939.v2.0.Fmask.tif", "https://x/HLS-VI.S30.T45RUL.2021305T045939.v2.0.NDVI.tif",
         "https://x/HLS-VI.S30.T45RUL.2021305T045939.v2.0.NDWI.tif",
         "https://x/ECOv003_L2T_LSTE_00367_002_45RUL_20180730T100514_01_LST.tif",
         "https://x/ECOv003_L2T_LSTE_00367_002_45RUL_20180730T100514_01_LST_err.tif"]


def test_assets_are_matched_by_their_exact_suffix():
    assert cw.pick_assets(LINKS, [".NDVI.tif", ".Fmask.tif"]) == {".NDVI.tif": LINKS[1], ".Fmask.tif": LINKS[0]}
    assert cw.pick_assets(LINKS, ["_LST.tif"]) == {"_LST.tif": LINKS[3]}         # not _LST_err.tif


def test_a_missing_asset_is_an_error():
    with pytest.raises(ValueError, match="EVI"):
        cw.pick_assets(LINKS, [".EVI.tif"])


@pytest.mark.parametrize("ur,when", [
    ("HLS.S30.T45RUL.2021305T045939.v2.0", "2021-11-01T04:59:39"),
    ("ECOv003_L2T_LSTE_00367_002_45RUL_20180730T100514_01", "2018-07-30T10:05:14"),
    ("ECOv002_L2T_LSTE_00367_002_45RUL_20180730T100514_0712_01", "2018-07-30T10:05:14")])
def test_acquisition_time_is_read_from_the_granule_name(ur, when):
    assert str(cw.granule_time(ur).isoformat()) == when


def test_v002_fills_only_overpasses_that_v003_lacks():
    v3 = ["ECOv003_L2T_LSTE_00367_002_45RUL_20180730T100514_01"]
    v2 = ["ECOv002_L2T_LSTE_00367_002_45RUL_20180730T100514_0712_01", "ECOv002_L2T_LSTE_00400_001_45RUL_20180801T090000_0712_01"]
    assert cw.missing_from(v3, v2) == ["ECOv002_L2T_LSTE_00400_001_45RUL_20180801T090000_0712_01"]


# --- L6 (REVIEW_NOTES): a boundless read must never invent "clear" (0) pixels outside the granule ------------
import json

import numpy as np
from rasterio.transform import from_origin
from rasterio.windows import Window


def test_the_pixels_of_a_window_outside_the_source_are_marked():
    m = cw.outside_source(Window(col_off=-2, row_off=-1, width=5, height=3), height=4, width=4)
    assert m.shape == (3, 5)
    assert m[0].all() and m[:, :2].all() and not m[1:, 2:].any()


def test_the_fill_for_outside_pixels_is_the_nodata_or_nan_when_there_is_none():
    assert cw.boundless_fill(255.0) == 255.0 and cw.boundless_fill(-19999.0) == -19999.0
    assert np.isnan(cw.boundless_fill(None)) and np.isnan(cw.boundless_fill(float("nan")))


def _src(path, a, nodata=None, transform=from_origin(300000, 3100020, 70, 70), crs="EPSG:32645"):
    import rasterio
    with rasterio.open(path, "w", driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype=a.dtype.name,
                       crs=crs, transform=transform, nodata=nodata) as dst:
        dst.write(a, 1)
    return path


def test_a_window_past_the_edge_of_a_source_without_nodata_reads_nan_not_zero(tmp_path):
    import rasterio
    f = _src(tmp_path / "qc.tif", np.zeros((4, 4), dtype="uint16"))              # QC 0 = best quality
    with rasterio.open(f) as src:
        a, n_out = cw.read_window(src, Window(col_off=2, row_off=2, width=4, height=4))
    assert n_out == 12 and np.isnan(a).sum() == 12 and (a[:2, :2] == 0).all()


def test_a_window_past_the_edge_of_a_source_with_nodata_reads_its_nodata(tmp_path):
    import rasterio
    f = _src(tmp_path / "fmask.tif", np.zeros((4, 4), dtype="uint8"), nodata=255)
    with rasterio.open(f) as src:
        a, n_out = cw.read_window(src, Window(col_off=-1, row_off=0, width=2, height=2))
    assert n_out == 2 and a[:, 0].tolist() == [255.0, 255.0] and a[:, 1].tolist() == [0.0, 0.0]


def test_hls_tags_tell_whether_a_cached_window_left_its_granule():
    tags = {"ULX": "300000", "ULY": "3100020", "NCOLS": "3660", "NROWS": "3660", "SPATIAL_RESOLUTION": "30"}
    inside = from_origin(340080.0, 3066690.0, 30, 30)
    assert cw.outside_pixels_from_tags(inside, (336, 338), tags) == 0
    west = from_origin(299940.0, 3066690.0, 30, 30)                                # 2 columns west of the tile
    assert cw.outside_pixels_from_tags(west, (10, 5), tags) == 20
    assert cw.outside_pixels_from_tags(inside, (336, 338), {}) is None               # extent not in the tags


# --- L7 (REVIEW_NOTES): a data card per set from the cached files only ---------------------------------------

FIELD = {"id": "t", "lat": 27.690767, "lon": 85.441792,
         "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]}


def test_pixels_over_the_field_polygon_are_counted_in_the_rasters_own_grid():
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:4326", "EPSG:32645", [85.441487], [27.691037])              # NW corner of the field
    t = from_origin(xs[0], ys[0], 30, 30)                                             # 30 m grid from the NW corner
    n = cw.field_pixel_count(FIELD["polygon"], "EPSG:32645", t, (6, 6))
    assert n["centre_inside"] == 4 and 4 <= n["touching"] <= 9


def _granule(raw, ur, assets, bands, acquired):
    import rasterio
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:4326", "EPSG:32645", [85.4415], [27.6912])
    t = from_origin(xs[0] - 90, ys[0] + 90, 30, 30)
    with rasterio.open(raw / f"{ur}.tif", "w", driver="GTiff", height=6, width=6, count=len(bands), dtype="float64",
                       crs="EPSG:32645", transform=t) as dst:
        for i, b in enumerate(bands, 1):
            dst.write(np.full((6, 6), b, dtype="float64"), i)
        dst.update_tags(granule=ur, acquired=acquired, assets=json.dumps(assets))


HLS_META = {".NDVI.tif": {"dtype": "int16", "nodata": -19999.0, "scale": 0.0001, "offset": 0.0,
                          "tags": {"long_name": "Normalized Difference Vegetation Index", "scale_factor": "0.0001",
                                   "add_offset": "0.0", "_FillValue": "-19999", "ULX": "300000", "ULY": "3100020",
                                   "NCOLS": "3660", "NROWS": "3660", "SPATIAL_RESOLUTION": "30"}},
            ".Fmask.tif": {"dtype": "uint8", "nodata": 255.0, "scale": 1.0, "offset": 0.0, "tags": {}}}


def test_a_set_card_is_built_from_the_cached_granules_without_any_network(tmp_path, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "earthaccess", None)
    raw = tmp_path / "raw" / "hls_l30" / "t"
    raw.mkdir(parents=True)
    _granule(raw, "HLS-VI.L30.T45RUL.2013114T045006.v2.0", HLS_META, [5000.0, 64.0], "2013-04-24 04:50:06")
    _granule(raw, "HLS-VI.L30.T45RUL.2013130T045000.v2.0", HLS_META, [-19999.0, 255.0], "2013-05-10 04:50:00")
    (raw / "failures.json").write_text('{"HLS-VI.L30.T45RUL.2013146T045000.v2.0": "HTTP 500"}\n')
    (raw / "granules.json").write_text(json.dumps(["a", "b", "c"]))
    card = json.loads(cw.write_set_card(FIELD, "hls_l30", data_dir=tmp_path).read_text())
    assert card["dataset"] == "hls_l30" and card["product"] == "HLSL30_VI" and "v2.0" in card["version"]
    assert card["variable"] == ["NDVI", "Fmask"] and card["date_range"] == ["2013-04-24", "2013-05-10"]
    assert card["scale_factor"]["NDVI"] == 0.0001 and card["raw_attrs"]["NDVI"]["_FillValue"] == -19999.0
    assert card["fill_values_removed"]["NDVI"]["pixels_with_fill"] == 36
    assert card["records_dropped"] == {"granules_listed": 3, "granules_cached": 2, "failures": 1}
    assert card["pixel_count"]["centre_inside"] >= 1
    assert "later" in card["quality_flags_used"] and "diary" in card["quality_flags_used"]
    assert card["notes"].count("outside its source granule") == 1 and "0 of 2" in card["notes"]


def test_a_set_that_is_not_cached_is_skipped(tmp_path):
    assert cw.write_set_card(FIELD, "eco_esi", data_dir=tmp_path) is None


ECO_META = {"_LST.tif": {"dtype": "float32", "nodata": float("nan"), "scale": 1.0, "offset": 0.0, "tags": {}},
            "_QC.tif": {"dtype": "uint16", "nodata": None, "scale": 1.0, "offset": 0.0, "tags": {}},
            "_cloud.tif": {"dtype": "uint8", "nodata": None, "scale": 1.0, "offset": 0.0, "tags": {}}}


def test_values_outside_the_rule_12_range_are_counted_and_nodata_is_listed_per_version(tmp_path):
    raw = tmp_path / "raw" / "eco_lste" / "t"
    raw.mkdir(parents=True)
    _granule(raw, "ECOv002_L2T_LSTE_21859_012_45RUL_20220514T222653_0712_02", ECO_META, [1305.8, 3.0, 0.0],
             "2022-05-14 22:26:53")
    v3 = {**ECO_META, "_cloud.tif": dict(ECO_META["_cloud.tif"], nodata=255.0)}
    _granule(raw, "ECOv003_L2T_LSTE_00367_002_45RUL_20180730T100514_01", v3, [300.0, 3.0, 255.0], "2018-07-30 10:05:14")
    card = json.loads(cw.write_set_card(FIELD, "eco_lste", data_dir=tmp_path).read_text())
    assert card["range_warnings"]["LST"] == {"rule": "temp_c -30 to 50 C (LST in K - 273.15)", "granules": 1, "pixels": 36}
    assert card["fill_values_removed"]["cloud"]["nodata"] == ["255.0", "None"]
    assert card["fill_values_removed"]["cloud"]["pixels_with_fill"] == 36
    assert card["version"] == "V002 (1 granules), V003 (1 granules)"


def test_flag_zeros_on_pixels_without_a_main_value_are_counted(tmp_path):
    raw = tmp_path / "raw" / "eco_lste" / "t"
    raw.mkdir(parents=True)
    _granule(raw, "ECOv002_L2T_LSTE_21859_012_45RUL_20220514T222653_0712_02", ECO_META, [float("nan"), 0.0, 0.0],
             "2022-05-14 22:26:53")
    card = json.loads(cw.write_set_card(FIELD, "eco_lste", data_dir=tmp_path).read_text())
    assert card["raw_attrs"]["flag_zero_where_main_missing"] == {"QC": 36, "cloud": 36}
    assert "never by QC or cloud == 0" in card["notes"]


# --- owner's batch decisions item 25 (rules.yaml ecostress.qc_needs_valid_value) ---
def test_qc_and_cloud_count_only_where_the_measured_value_is_valid():
    import numpy as np
    lst = np.array([[300.0, np.nan], [250.0, 0.0]])
    qc = np.array([[0, 0], [0, 0]], dtype="uint16")              # 0 = best quality
    cloud = np.array([[0, 0], [1, 0]], dtype="uint8")            # 0 = clear
    out_qc, out_cloud = cw.layers_where_valid(lst, qc, cloud, valid_range=(200.0, 400.0))
    assert out_qc.dtype.kind == "f" and np.isnan(out_qc[0, 1]) and np.isnan(out_qc[1, 1])
    assert out_qc[0, 0] == 0 and out_cloud[1, 0] == 1 and np.isnan(out_cloud[1, 1])


def test_a_missing_value_never_reads_as_best_quality_on_a_cached_v002_window():
    """A real V002 window whose LST is missing on every pixel: no QC or cloud value survives."""
    import numpy as np
    path = cw.REPO / "data/raw/eco_lste/demo/ECOv002_L2T_LSTE_00367_002_45RUL_20180730T100513_0712_01.tif"
    if not path.exists():
        pytest.skip("cached ECOSTRESS window not present")
    import rasterio
    with rasterio.open(path) as s:
        lst, qc, cloud = s.read(1), s.read(2), s.read(3)
    out_qc, out_cloud = cw.layers_where_valid(lst, qc, cloud, valid_range=(150.0, 400.0))
    assert np.isnan(out_qc).all() and np.isnan(out_cloud).all()
