"""ESA WorldCover 2021 (v200, 10 m) over a field's fetch box.

    .venv/bin/python -m pipeline.fetch.worldcover --field demo [--nearest-square]

Owner, 2026-11-12: the demo point (27.67 N, 85.43 E) is in Bhaktapur's old city, not farmland, and the
real field is not known yet. So every dataset is fetched for a box of about 5 km each way around the
point. The placeholder field itself is chosen with pipeline/fetch/placeholder.py and lives in
config/fields/<field>.yaml; this module never writes a field (REVIEW_NOTES M11/H3: it used to write the
first, rejected 100 m square to placeholder_field.json). `--nearest-square` still runs that first search
(the nearest 100 m cropland square with a 30 m cropland margin) and writes worldcover_nearest_square.json,
labelled as a search result, NOT the field.

Tiles (REVIEW_NOTES L5): every 3 x 3 degree tile the box touches is read, and the windows are mosaicked
on the tiles' shared 1/12000-degree grid, so a box across a tile edge works with no code change.

Source: ESA WorldCover 10 m 2021 v200 (Zanaga et al. 2022, doi:10.5281/zenodo.7254221), CC BY 4.0,
public cloud-optimised GeoTIFF tiles (no login). Only the box window is read and cached.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
TILE_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
            "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif")
CROPLAND = 40
EARTH_RADIUS_KM = 6371.0088                    # IUGG mean Earth radius (Moritz 2000, Geodetic Reference System 1980)
KM_PER_DEG = EARTH_RADIUS_KM * math.pi / 180


def box_around(lat, lon, half_km):
    """[min_lon, min_lat, max_lon, max_lat] reaching `half_km` north, south, east and west of the point."""
    dlat = half_km / KM_PER_DEG
    dlon = half_km / (KM_PER_DEG * math.cos(math.radians(lat)))
    return [round(lon - dlon, 6), round(lat - dlat, 6), round(lon + dlon, 6), round(lat + dlat, 6)]


def distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def square_polygon(lat, lon, side_m):
    """Four [lon, lat] corners (SW, SE, NE, NW; ring not closed, as in the contract)."""
    hl = side_m / 2000 / KM_PER_DEG
    hn = side_m / 2000 / (KM_PER_DEG * math.cos(math.radians(lat)))
    return [[round(lon - hn, 6), round(lat - hl, 6)], [round(lon + hn, 6), round(lat - hl, 6)],
            [round(lon + hn, 6), round(lat + hl, 6)], [round(lon - hn, 6), round(lat + hl, 6)]]


def find_cropland_square(classes, transform, target_lon, target_lat, side_m=100, margin_m=30):
    """Nearest window of (side + 2 margin) metres that is entirely cropland; returns its centre and polygon."""
    res_deg = abs(transform.e)
    lat_m = res_deg * KM_PER_DEG * 1000
    lon_m = abs(transform.a) * KM_PER_DEG * 1000 * math.cos(math.radians(target_lat))
    nr, nc = math.ceil((side_m + 2 * margin_m) / lat_m), math.ceil((side_m + 2 * margin_m) / lon_m)
    crop = (np.asarray(classes) == CROPLAND).astype(np.int64)
    ii = np.pad(crop.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    counts = ii[nr:, nc:] - ii[:-nr, nc:] - ii[nr:, :-nc] + ii[:-nr, :-nc]
    rows, cols = np.nonzero(counts == nr * nc)
    if len(rows) == 0:
        raise ValueError(f"no {side_m} m square of cropland with a {margin_m} m cropland margin in this grid")
    lons = transform.c + transform.a * (cols + nc / 2)          # north-up grid, no rotation
    lats = transform.f + transform.e * (rows + nr / 2)
    d = np.array([distance_km(target_lat, target_lon, la, lo) for la, lo in zip(lats, lons)])
    k = int(d.argmin())
    lat, lon = round(float(lats[k]), 6), round(float(lons[k]), 6)
    r0, c0 = int(rows[k]), int(cols[k])
    return {"lat": lat, "lon": lon, "polygon": square_polygon(lat, lon, side_m), "side_m": side_m,
            "margin_m": margin_m, "distance_km": round(float(d[k]), 3), "cropland_fraction": 1.0,
            "window_rows_cols": [r0, r0 + nr, c0, c0 + nc], "candidates": int(len(rows))}


TILE_DEG = 3
NO_DATA = 0                                    # WorldCover class 0 = no data (legend); also fills any unread gap


def _tile_name(lat, lon):
    la, lo = int(math.floor(lat / 3) * 3), int(math.floor(lon / 3) * 3)
    return f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"


def tiles_for_box(box):
    """Every 3 x 3 degree tile the box [min_lon, min_lat, max_lon, max_lat] touches, south to north, west to east.
    An edge exactly on a tile boundary does not pull in the next tile (it holds no pixel of it)."""
    eps = 1e-9
    lo0, lo1 = (math.floor(box[0] / TILE_DEG) * TILE_DEG, math.floor((box[2] - eps) / TILE_DEG) * TILE_DEG)
    la0, la1 = (math.floor(box[1] / TILE_DEG) * TILE_DEG, math.floor((box[3] - eps) / TILE_DEG) * TILE_DEG)
    return [_tile_name(la, lo) for la in range(la0, la1 + 1, TILE_DEG) for lo in range(lo0, lo1 + 1, TILE_DEG)]


def mosaic(parts):
    """Place windows [(array, transform), ...] that share one north-up grid (same pixel size, aligned origins)
    into one array; cells no window covers are NO_DATA. Returns (array, transform)."""
    from rasterio.transform import from_origin
    res_x, res_y = parts[0][1].a, -parts[0][1].e
    for a, t in parts:
        if not (math.isclose(t.a, res_x) and math.isclose(-t.e, res_y)):
            raise ValueError("windows do not share one pixel size")
    west = min(t.c for _, t in parts)
    north = max(t.f for _, t in parts)
    offs = [(round((north - t.f) / res_y), round((t.c - west) / res_x)) for _, t in parts]
    for (r, c), (_, t) in zip(offs, parts):
        if abs(west + c * res_x - t.c) > res_x * 1e-3 or abs(north - r * res_y - t.f) > res_y * 1e-3:
            raise ValueError("windows are not aligned on one grid")
    h = max(r + a.shape[0] for (r, _), (a, _) in zip(offs, parts))
    w = max(c + a.shape[1] for (_, c), (a, _) in zip(offs, parts))
    out = np.full((h, w), NO_DATA, dtype=parts[0][0].dtype)
    for (r, c), (a, _) in zip(offs, parts):
        out[r:r + a.shape[0], c:c + a.shape[1]] = a
    return out, from_origin(west, north, res_x, res_y)


def fetch(field, box, data_dir=REPO / "data"):
    import rasterio
    from rasterio.windows import from_bounds

    from pipeline.fetch import guards as g

    raw = Path(data_dir) / "raw" / "worldcover" / field["id"]
    raw.mkdir(parents=True, exist_ok=True)
    tiles = tiles_for_box(box)
    parts, attrs = [], {}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        for tile in tiles:
            with rasterio.open("/vsicurl/" + TILE_URL.format(tile=tile)) as src:
                attrs[tile] = {"crs": str(src.crs), "res_deg": src.res, "dtype": src.dtypes[0], "nodata": src.nodata,
                               "tags": src.tags()}
                print(f"raw attributes {tile}:", json.dumps(attrs[tile], default=str)[:600])
                b = (max(box[0], src.bounds.left), max(box[1], src.bounds.bottom),
                     min(box[2], src.bounds.right), min(box[3], src.bounds.top))
                win = from_bounds(*b, src.transform).round_offsets().round_lengths()
                parts.append((src.read(1, window=win), src.window_transform(win)))
                cmap = src.colormap(1)
                profile = dict(src.profile)
    a, t = mosaic(parts)
    profile.update(height=a.shape[0], width=a.shape[1], transform=t)
    tile = "+".join(tiles)
    attrs = attrs[tiles[0]] if len(tiles) == 1 else {"tiles": attrs}
    legend_tags = (attrs if len(tiles) == 1 else next(iter(attrs["tiles"].values())))["tags"]
    out = raw / f"worldcover_2021_{tile}_box.tif"
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(a, 1)
        dst.write_colormap(1, cmap)
    legend = {int(k): v for k, v in (ln.split(None, 1) for ln in legend_tags["legend"].strip().splitlines())}
    bad = sorted(set(np.unique(a).tolist()) - set(legend) - {0})
    if bad:
        raise g.DataGuardError(f"WorldCover classes outside the legend: {bad}")
    counts = {legend.get(int(v), "no data"): int(c) for v, c in zip(*np.unique(a, return_counts=True))}
    card = g.make_card(
        dataset="worldcover", product="ESA WorldCover 10 m 2021", version="v200 (algorithm V2.0.0)",
        variable="Map (land-cover class)", units_in="class code", units_out="class code",
        scale_factor=None, fill_values_removed={"0 (no data)": int((a == 0).sum())},
        quality_flags_used="none (the map has no quality layer)", records_dropped=0,
        date_range=["2021-01-01", "2021-12-31"], time_zone="n/a (annual map)", pixel_count=int(a.size),
        source=f"ESA WorldCover (Zanaga et al. 2022, doi:10.5281/zenodo.7254221), CC BY 4.0, tile(s) {tile}",
        resolution="1/12000 deg (about 10 m)", raw_attrs=attrs,
        location={"box": box, "point": [field["lat"], field["lon"]]},
        notes=(f"Class counts in the fetch box: {counts}. Tiles read: {tiles} (windows mosaicked on the shared "
               "grid; 0 = no data). Used only to place the placeholder field."))
    return {"classes": a, "transform": t, "raw": out, "card": g.write_card(card, Path(data_dir) / "cards" / field["id"]),
            "counts": counts, "colormap": cmap}


def main(argv=None, field=None, data_dir=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--nearest-square", action="store_true",
                    help="also run the first placeholder search (nearest 100 m cropland square); a search result, NOT the field")
    a = ap.parse_args(argv)
    field = field or load_field(a.field)
    data_dir = Path(data_dir) if data_dir else REPO / "data"
    origin = field.get("origin_point") or {"lat": field["lat"], "lon": field["lon"]}
    box = field.get("fetch_box") or box_around(origin["lat"], origin["lon"], 5.0)
    res = fetch({**field, **origin}, box, data_dir=data_dir)
    print(f"class counts: {res['counts']}\n-> {res['raw']}\n-> {res['card']}")
    if a.nearest_square:
        sq = find_cropland_square(res["classes"], res["transform"], origin["lon"], origin["lat"])
        out = data_dir / "clean" / field["id"] / "worldcover_nearest_square.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "status": (f"Search result only, NOT the field: the nearest {sq['side_m']} m cropland square to the origin point "
                       f"(the first placeholder method, superseded by pipeline/fetch/placeholder.py). The field is "
                       f"config/fields/{field['id']}.yaml."),
            "box": box, "origin": origin, "square": sq, "class_counts": res["counts"], "raw": str(res["raw"])}, indent=1) + "\n")
        print(f"nearest square (NOT the field): {json.dumps(sq)}\n-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
