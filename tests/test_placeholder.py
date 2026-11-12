"""Placeholder-field search (pipeline/fetch/placeholder.py), REVIEW_NOTES M11: the soil-distance limit comes
from rules.yaml, a missing SoilGrids map gives "unknown" (never a None > limit TypeError), and a chosen field
that misses the built-up rule says so in its label. Synthetic grids only."""
import numpy as np
import pytest
from rasterio.transform import from_origin

from pipeline.fetch import placeholder as ph
from pipeline.fetch.worldcover import KM_PER_DEG

RES = 1 / 12000


def test_the_soil_distance_limit_is_read_from_rules():
    from pipeline.fetch.rules import load_rules
    assert ph.soil_limit_m(load_rules()) == load_rules()["soilgrids"]["nearest_cell_max_m"]
    assert ph.soil_limit_m({"soilgrids": {"nearest_cell_max_m": 1234}}) == 1234


def test_an_unknown_soil_distance_is_not_compared():
    assert ph.soil_rank(None, 3000) == 0 and ph.soil_rank(2999, 3000) == 0 and ph.soil_rank(3001, 3000) == 1
    cands = [{"soilgrids_nearest_m": None, "min_peak": 0.8, "distance_km": 1.0},
             {"soilgrids_nearest_m": 5000, "min_peak": 0.9, "distance_km": 1.0}]
    ranked = ph.rank(cands, limit_m=3000)
    assert ranked[0]["soilgrids_nearest_m"] == "unknown"        # unknown is reported, and not pushed down
    assert ranked[1]["soilgrids_nearest_m"] == 5000


def test_without_soilgrids_maps_every_distance_is_unknown(tmp_path):
    assert ph.soil_distances(tmp_path / "wcs", [{"lat": 27.69, "lon": 85.44}]) == [None]


def test_soil_distances_count_only_cells_where_every_map_has_values(tmp_path):
    import rasterio

    from pipeline.fetch.soilgrids import DEPTHS, PROPS
    t = from_origin(85.40, 27.70, 0.0025, 0.0025)
    wcs = tmp_path / "wcs"
    wcs.mkdir()
    for p in PROPS:
        for d in DEPTHS:
            a = np.zeros((4, 4), dtype="int16")
            a[0, 3] = 300                                          # complete cell
            if p.startswith("wv"):
                a[1, 1] = 300                                      # water maps only: not a prediction
            with rasterio.open(wcs / f"{p}_{d}_mean.tif", "w", driver="GTiff", height=4, width=4, count=1,
                               dtype="int16", crs="EPSG:4326", transform=t) as dst:
                dst.write(a, 1)
    lat, lon = 27.70 - 1.5 * 0.0025, 85.40 + 1.5 * 0.0025               # centre of cell (1, 1)
    d = ph.soil_distances(wcs, [{"lat": lat, "lon": lon}])[0]
    expect = np.hypot(2 * 0.0025 * KM_PER_DEG * 1000 * np.cos(np.radians(lat)), 1 * 0.0025 * KM_PER_DEG * 1000)
    assert d == pytest.approx(expect, abs=2)                       # to cell (0, 3), not (1, 1)


def test_the_distance_from_a_square_to_a_class_is_measured_to_pixel_edges():
    a = np.full((200, 200), 40, dtype=np.uint8)
    a[100, 150] = 50                                               # one built-up pixel
    t = from_origin(85.0, 27.1, RES, RES)
    lat = t.f + t.e * 100.5
    lon = t.c + t.a * 100.5                                        # square centred 50 pixels west of it
    px_x = RES * KM_PER_DEG * 1000 * np.cos(np.radians(lat))
    d = ph.distance_to_class_m(a, t, lat, lon, half_m=60, cls=50)
    assert d == pytest.approx(50 * px_x - px_x / 2 - 60, abs=0.5)


def test_a_margin_below_the_built_up_rule_is_labelled_as_an_exception():
    lab = ph.margin_exception_label(27.690767, 85.441792, 77.1, rule_m=100)
    assert lab == "exception: margin 77 m from built-up, below the 100 m rule; accepted by the owner, 2026-11-12"
    assert "NOT accepted" in ph.margin_exception_label(27.70, 85.40, 60.0, rule_m=100)
    assert ph.margin_exception_label(27.690767, 85.441792, 120.0, rule_m=100) is None


def test_the_chosen_field_label_carries_its_exception():
    a = np.full((400, 400), 40, dtype=np.uint8)
    t = from_origin(85.43, 27.70, RES, RES)
    field = {"lat": 27.690767, "lon": 85.441792,
             "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]],
             "earlier_placeholders": [{"lat": 27.690542, "lon": 85.441792, "side_m": 60, "why_replaced": "moved north"}]}
    r = (27.690767 - t.f) / t.e
    c = (85.441792 - t.c) / t.a
    a[int(r), int(c) + 13] = 50                                    # built-up about 120 m east of the centre
    refs = ph.reference_squares(field, classes=a, transform=t)
    assert refs[0]["role"] == "chosen" and refs[0]["margin_to_built_up_m"] < 100
    assert "exception: margin" in refs[0]["label"] and "accepted by the owner, 2026-11-12" in refs[0]["label"]
    assert refs[1]["role"] == "earlier" and "Earlier placeholder" in refs[1]["label"]
    assert ph.reference_squares(field)[0]["label"] == "Chosen placeholder field (built-up margin not checked)"


def test_relabel_rewrites_only_the_reference_labels_and_keeps_the_candidates(tmp_path):
    import json

    import rasterio
    a = np.full((400, 400), 40, dtype=np.uint8)
    t = from_origin(85.43, 27.70, RES, RES)
    a[int((27.690767 - t.f) / t.e), int((85.441792 - t.c) / t.a) + 13] = 50
    wc_dir = tmp_path / "raw" / "worldcover" / "t"
    wc_dir.mkdir(parents=True)
    with rasterio.open(wc_dir / "worldcover_2021_N27E084_box.tif", "w", driver="GTiff", height=400, width=400, count=1,
                       dtype="uint8", crs="EPSG:4326", transform=t) as dst:
        dst.write(a, 1)
    clean = tmp_path / "clean" / "t"
    clean.mkdir(parents=True)
    old = {"rule": {"side_m": 60}, "passing": 5, "candidates": [{"lat": 1.0, "lon": 2.0, "min_peak": 0.8}],
           "chosen_field": {"role": "chosen", "lat": 27.690767, "lon": 85.441792, "label": "Chosen placeholder field",
                            "min_peak": 0.78},
           "earlier_placeholders": [{"role": "earlier", "lat": 27.690542, "lon": 85.441792, "label": "Earlier placeholder (moved north)"}]}
    (clean / "placeholder_candidates.json").write_text(json.dumps(old))
    field = {"id": "t", "lat": 27.690767, "lon": 85.441792,
             "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]],
             "earlier_placeholders": [{"lat": 27.690542, "lon": 85.441792, "side_m": 60, "why_replaced": "moved north"}]}
    ph.relabel(field, tmp_path)
    new = json.loads((clean / "placeholder_candidates.json").read_text())
    assert new["candidates"] == old["candidates"] and new["passing"] == 5
    assert "exception: margin" in new["chosen_field"]["label"] and new["chosen_field"]["min_peak"] == 0.78
    assert new["chosen_field"]["margin_to_built_up_m"] < 100
    assert new["earlier_placeholders"] == old["earlier_placeholders"]
