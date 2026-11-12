"""NASADEM (NASADEM_HGT v001, 1 arc-second, about 30 m; decision D3) over a field's fetch box.

    .venv/bin/python -m pipeline.fetch.nasadem --field demo

Writes the box's elevation and slope to data/clean/<field>/nasadem_box.tif (band 1 elevation_m, band 2
slope_deg), the field's numbers to data/clean/<field>/nasadem_field.json, and the data card. Field
elevation feeds ET0 (FAO-56 eq. 7 pressure); slope is for revisiting the curve numbers (owner,
2026-11-12: terraced fields need terraced or contoured values). Slope: Horn (1981) 3x3 finite
differences, Proc. IEEE 69(1):14-47, as used by GDAL gdaldem.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

from pipeline.fetch.worldcover import KM_PER_DEG

REPO = Path(__file__).resolve().parents[2]


def pixel_metres(res_deg, lat):
    dy = res_deg * KM_PER_DEG * 1000
    return dy * math.cos(math.radians(lat)), dy


def slope_deg(dem, dx_m, dy_m):
    z = np.asarray(dem, dtype=float)
    s = np.full(z.shape, np.nan)
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * dx_m)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * dy_m)
    s[1:-1, 1:-1] = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    return s


def field_mask(shape, transform, polygon):
    from rasterio.features import geometry_mask
    ring = [list(p) for p in polygon] + [list(polygon[0])]
    return geometry_mask([{"type": "Polygon", "coordinates": [ring]}], out_shape=shape, transform=transform,
                         invert=True, all_touched=False)          # pixel centres inside the polygon


def field_stats(grid, transform, polygon):
    v = np.asarray(grid, dtype=float)[field_mask(np.shape(grid), transform, polygon)]
    v = v[np.isfinite(v)]
    if v.size == 0:
        raise ValueError("no pixel centre falls inside the field polygon")
    return {"pixels": int(v.size), "mean": float(v.mean()), "min": float(v.min()), "max": float(v.max())}


def check_heights(dem, nodata):
    n = int((np.asarray(dem) == nodata).sum())
    if n:
        raise ValueError(f"{n} void pixel(s) (value {nodata}) in NASADEM, which is supposed to be void-filled")


def fetch(field, data_dir=REPO / "data"):
    import earthaccess
    import rasterio
    from rasterio.windows import from_bounds

    from pipeline.fetch import guards as g

    data_dir = Path(data_dir)
    raw = data_dir / "raw" / "nasadem" / field["id"]
    raw.mkdir(parents=True, exist_ok=True)
    box = field["fetch_box"]
    earthaccess.login(strategy="netrc", persist=False)
    gr = earthaccess.search_data(short_name="NASADEM_HGT", version="001", bounding_box=tuple(box))
    if len(gr) != 1:
        raise ValueError(f"expected one NASADEM tile for the box, CMR returned {len(gr)}")
    files = [Path(str(f)) for f in earthaccess.download(gr, local_path=str(raw), threads=1)]
    z = files[0]
    tile = z.stem.split("_")[-1]
    with rasterio.open(f"/vsizip/{z}/{tile}.hgt") as src:
        attrs = {"driver": src.driver, "crs": str(src.crs), "res_deg": src.res, "dtype": src.dtypes[0],
                 "nodata": src.nodata, "tags": src.tags(), "units": "metres (NASADEM user guide: heights above the EGM96 geoid)"}
        print("raw attributes:", json.dumps(attrs, default=str))
        win = from_bounds(*box, src.transform).round_offsets().round_lengths()
        dem = src.read(1, window=win).astype(float)
        t = src.window_transform(win)
    check_heights(dem, attrs["nodata"])
    dx, dy = pixel_metres(abs(t.e), field["lat"])
    slope = slope_deg(dem, dx, dy)
    clean = data_dir / "clean" / field["id"]
    clean.mkdir(parents=True, exist_ok=True)
    out = clean / "nasadem_box.tif"
    with rasterio.open(out, "w", driver="GTiff", height=dem.shape[0], width=dem.shape[1], count=2,
                       dtype="float32", crs="EPSG:4326", transform=t, nodata=np.nan) as dst:
        dst.write(dem.astype("float32"), 1)
        dst.write(slope.astype("float32"), 2)
        dst.set_band_description(1, "elevation_m")
        dst.set_band_description(2, "slope_deg")
    el, sl = field_stats(dem, t, field["polygon"]), field_stats(slope, t, field["polygon"])
    summary = {"elevation_m": el, "slope_deg": sl, "placeholder_field": bool(field.get("placeholder")),
               "polygon": field["polygon"], "pixel_m": [round(dx, 2), round(dy, 2)]}
    (clean / "nasadem_field.json").write_text(json.dumps(summary, indent=1) + "\n")
    card = g.make_card(
        dataset="nasadem", product="NASADEM_HGT (NASA DEM, SRTM reprocessed)", version="001",
        variable=["elevation_m", "slope_deg (derived, Horn 1981)"], units_in="m (int16)", units_out="m; degrees",
        scale_factor=None, fill_values_removed={str(attrs["nodata"]): 0}, quality_flags_used="none (void-filled product; .num source file not used)",
        records_dropped=0, date_range=["2000-02-11", "2000-02-21"], time_zone="n/a (one survey, SRTM mission)",
        pixel_count=int(el["pixels"]), source="NASA JPL (2020), NASADEM Merged DEM Global 1 arc second V001, NASA EOSDIS LP DAAC, doi:10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001",
        resolution="1 arc-second (about 31 m N-S, 27 m E-W here)", raw_attrs=attrs,
        location={"box": box, "field_polygon": field["polygon"], "tile": tile},
        notes=(f"Field: elevation {el['mean']:.1f} m (range {el['min']:.0f}-{el['max']:.0f}), slope mean "
               f"{sl['mean']:.1f} deg (max {sl['max']:.1f}) over {el['pixels']} pixels"
               + (" (PLACEHOLDER field)" if field.get("placeholder") else "")))
    return {"summary": summary, "card": g.write_card(card, data_dir / "cards" / field["id"]), "raster": out}


def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    res = fetch(load_field(a.field))
    print(json.dumps(res["summary"], indent=1), f"\n-> {res['raster'].relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
