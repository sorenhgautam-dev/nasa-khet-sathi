"""Self-hosted NASA map backgrounds (owner's launch brief, 2026-11-14: no outside request at runtime):
pipeline/fetch/basemap.py. The pure parts are tested with worked numbers; the GIBS request is replaced by a fake session,
so these tests never touch the network."""
import io
import json
import math

import numpy as np
import pytest
from jsonschema import Draft202012Validator
from PIL import Image

from pipeline.export.validate import load_schema
from pipeline.fetch import basemap as bm

BOX = [85.379227, 27.625034, 85.480773, 27.714966]          # the demo fetch box (config/fields/demo.yaml)


def _png(w, h, rgba=(110, 110, 85, 255), transparent=0):
    a = np.zeros((h, w, 4), dtype=np.uint8)
    a[...] = rgba
    a.reshape(-1, 4)[:transparent, 3] = 0
    buf = io.BytesIO()
    Image.fromarray(a, "RGBA").save(buf, "PNG")
    return buf.getvalue()


def test_web_mercator_matches_the_epsg_3857_formulas():
    # x = R lambda, y = R ln tan(pi/4 + phi/2), R = 6378137 m (EPSG:3857); 180 deg east is half the world, 20037508.34 m
    assert bm.mercator(180, 0)[0] == pytest.approx(20037508.342789244)
    x, y = bm.mercator(85.43, 27.67)
    assert x == pytest.approx(6378137 * math.radians(85.43))
    assert y == pytest.approx(6378137 * math.log(math.tan(math.pi / 4 + math.radians(27.67) / 2)))
    assert bm.mercator(0, bm.MERCATOR_MAX_LAT)[1] == pytest.approx(20037508.342789244, rel=1e-9)


def test_the_box_request_uses_gibs_zoom_12_pixels():
    # zoom 12 of GoogleMapsCompatible: 2 x 20037508.34 m / (256 x 4096) = 38.2185 m per pixel
    assert bm.LEVEL12_M == pytest.approx(38.21851414258813)
    req = bm.box_request(BOX)
    x0, y0, x1, y1 = req["bbox"]
    assert (x1 - x0) == pytest.approx(11304.05, abs=0.1) and (y1 - y0) == pytest.approx(11303.94, abs=0.1)
    assert req["width"] == req["height"] == 296                      # 11304 / 38.22 = 295.8
    # one pixel on the ground at 27.67 N: 38.22 x cos(27.67) = 33.8 m
    assert bm.ground_m_per_px(req, BOX) == pytest.approx(33.8, abs=0.1)


def test_leaflet_bounds_are_south_west_then_north_east():
    assert bm.leaflet_bounds(BOX) == [[27.625034, 85.379227], [27.714966, 85.480773]]


def test_granule_stats_count_coverage_clear_and_haze_from_fmask():
    # Fmask bits: 1 cloud; bits 6-7 aerosol (01 low, 10 moderate, 11 high); 255 = no data
    f = np.array([[0, 64, 128, 192], [2, 255, 64, 64]], dtype=np.uint8)
    s = bm.granule_stats(f)
    assert s["coverage"] == pytest.approx(7 / 8)
    assert s["clear"] == pytest.approx(6 / 8)               # 0, 64, 128, 192, 64, 64 (aerosol bits do not matter)
    assert s["hazy"] == pytest.approx(2 / 7)                # 128 (moderate) and 192 (high) among the 7 valid pixels


def _row(date, clear=0.999, hazy=0.05, coverage=1.0, sensor="hls_l30"):
    return {"date": date, "sensor": sensor, "clear": clear, "hazy": hazy, "coverage": coverage}


def test_the_clearest_least_hazy_recent_dry_season_image_is_chosen():
    rows = [_row("2025-11-11", hazy=0.046), _row("2023-11-14", hazy=0.16), _row("2025-06-01", hazy=0.0),
            _row("2021-12-01", hazy=0.0), _row("2025-01-27", hazy=0.90), _row("2024-12-20", clear=0.95, hazy=0.0),
            _row("2024-02-01", coverage=0.97, hazy=0.0)]
    order, rule = bm.rank_dates(rows, last_year=2025)
    assert rule == "dry season"
    # June is not dry season, 2021 is not recent, 2024-12-20 is too cloudy, 2024-02-01 does not cover the box
    assert [r["date"] for r in order] == ["2025-11-11", "2023-11-14", "2025-01-27"]


def test_a_tie_on_haze_goes_to_the_clearer_then_the_most_recent_image():
    rows = [_row("2023-12-01", hazy=0.01, clear=0.995), _row("2024-12-01", hazy=0.01, clear=0.995),
            _row("2023-01-05", hazy=0.01, clear=0.999)]
    order, _ = bm.rank_dates(rows, last_year=2025)
    assert [r["date"] for r in order] == ["2023-01-05", "2024-12-01", "2023-12-01"]


def test_without_a_clear_dry_season_image_any_month_of_the_recent_years_is_tried_and_said():
    order, rule = bm.rank_dates([_row("2025-06-01", hazy=0.2)], last_year=2025)
    assert rule == "any month" and [r["date"] for r in order] == ["2025-06-01"]
    assert bm.rank_dates([_row("2025-06-01", clear=0.5)], last_year=2025) == ([], None)


def test_to_jpeg_keeps_the_image_and_counts_the_transparent_pixels():
    jpg, info = bm.to_jpeg(_png(40, 30, transparent=3), max_bytes=300_000)
    im = Image.open(io.BytesIO(jpg))
    assert im.format == "JPEG" and im.size == (40, 30) and im.mode == "RGB"
    assert info["transparent_px"] == 3 and info["bytes"] == len(jpg) <= 300_000 and 60 <= info["quality"] <= 90


def test_an_image_with_no_data_fails_loudly_instead_of_being_published():
    with pytest.raises(bm.BasemapError, match="no data"):
        bm.to_jpeg(_png(10, 10, transparent=50), max_bytes=300_000)          # half of it transparent
    with pytest.raises(bm.BasemapError, match="blank"):
        bm.to_jpeg(_png(10, 10, rgba=(0, 0, 0, 255)), max_bytes=300_000)


def test_an_image_that_cannot_fit_its_size_limit_fails_loudly():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 255, (400, 400, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(noise, "RGB").save(buf, "PNG")
    with pytest.raises(bm.BasemapError, match="300 KB|bytes"):
        bm.to_jpeg(buf.getvalue(), max_bytes=20_000)


def test_fields_that_share_a_fetch_box_share_one_image_named_after_their_area():
    index = {"fields": [{"id": "demo", "area": "demo"}, {"id": "sample-1", "area": "demo"}, {"id": "far", "area": None}]}
    boxes = {"demo": BOX, "sample-1": BOX, "far": [47.40, -18.85, 47.44, -18.81]}
    g = bm.group_fields(index, boxes)
    assert g == [{"name": "demo", "box": BOX, "fields": ["demo", "sample-1"]},
                 {"name": "far", "box": [47.40, -18.85, 47.44, -18.81], "fields": ["far"]}]


def test_a_field_may_not_be_called_world():
    with pytest.raises(bm.BasemapError, match="world"):
        bm.group_fields({"fields": [{"id": "world"}]}, {"world": BOX})


def test_the_json_beside_each_image_validates_against_its_schema():
    schema = load_schema("basemap_schema.json")
    req = bm.box_request(BOX)
    doc = bm.field_doc("demo", "demo", BOX, req, bm.HLS_LAYERS["hls_l30"], "2025-11-11",
                       chosen="the clearest dry-season image")
    Draft202012Validator(schema).validate(doc)
    assert doc["image"] == "data/basemap/demo.jpg" and doc["bounds"] == [[27.625034, 85.379227], [27.714966, 85.480773]]
    assert doc["crs"] == "EPSG:3857" and doc["native_zoom"] == 12 and "GIBS" in doc["attribution"]
    w = bm.world_doc(1024)
    Draft202012Validator(schema).validate(w)
    assert w["bounds"] == [[-bm.MERCATOR_MAX_LAT, -180.0], [bm.MERCATOR_MAX_LAT, 180.0]] and w["date"] == "2004-08"


class FakeSession:
    def __init__(self, bodies):
        self.bodies, self.calls = list(bodies), []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append(params)
        body = self.bodies.pop(0)

        class R:
            status_code = 200
            content = body
            headers = {"content-type": "image/png"}

            def raise_for_status(self):
                pass
        return R()


def test_fetch_tries_the_next_date_when_gibs_has_no_picture_and_caches_the_raw_png(tmp_path):
    rows = [_row("2025-11-11"), _row("2023-11-14")]
    req = {"bbox": [0, 0, 10, 10], "width": 10, "height": 10}
    s = FakeSession([_png(10, 10, transparent=100), _png(10, 10)])
    got = bm.fetch_first_good(rows, req, tmp_path, session=s, max_bytes=300_000)
    assert got["row"]["date"] == "2023-11-14" and [c["TIME"] for c in s.calls] == ["2025-11-11", "2023-11-14"]
    assert got["skipped"][0]["date"] == "2025-11-11" and "no data" in got["skipped"][0]["why"]
    assert len(list(tmp_path.glob("*.png"))) == 2
    s2 = FakeSession([])                                    # the second run reads the cache: no request at all
    again = bm.fetch_first_good(rows[1:], req, tmp_path, session=s2, max_bytes=300_000)
    assert again["row"]["date"] == "2023-11-14" and s2.calls == []


def test_the_wms_request_is_a_plain_epsg_3857_getmap():
    p = bm.wms_params("HLS_L30_Nadir_BRDF_Adjusted_Reflectance", {"bbox": [1, 2, 3, 4], "width": 5, "height": 6}, "2025-11-11")
    assert p["SERVICE"] == "WMS" and p["REQUEST"] == "GetMap" and p["CRS"] == "EPSG:3857" and p["BBOX"] == "1,2,3,4"
    assert (p["WIDTH"], p["HEIGHT"], p["TIME"], p["FORMAT"]) == (5, 6, "2025-11-11", "image/png")
    assert "TIME" not in bm.wms_params("BlueMarble_NextGeneration", {"bbox": [1, 2, 3, 4], "width": 5, "height": 6}, None)


def test_the_published_basemaps_validate_and_stay_small():
    from pathlib import Path
    d = Path(__file__).resolve().parents[1] / "site" / "data" / "basemap"
    if not d.exists():
        pytest.skip("no basemap published yet (python -m pipeline.fetch.basemap)")
    schema = load_schema("basemap_schema.json")
    for j in sorted(d.glob("*.json")):
        doc = json.loads(j.read_text())
        Draft202012Validator(schema).validate(doc)
        img = d / Path(doc["image"]).name
        limit = bm.MAX_WORLD_BYTES if doc["id"] == "world" else bm.MAX_FIELD_BYTES
        assert img.read_bytes()[:3] == b"\xff\xd8\xff" and img.stat().st_size <= limit
