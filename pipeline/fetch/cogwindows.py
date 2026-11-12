"""Read only the fetch box out of cloud-optimised GeoTIFF granules (HLS-VI, ECOSTRESS tiled), in parallel.

    .venv/bin/python -m pipeline.fetch.cogwindows --field demo --set hls_l30 hls_s30 eco_lste eco_esi
    .venv/bin/python -m pipeline.fetch.cogwindows --field demo --card     # data cards from the cache, no network

Each granule's assets (e.g. NDVI and Fmask) are read for the box's window only (box reprojected to the
granule's UTM grid) and cached as one multi-band GeoTIFF per granule in data/raw/<set>/<field>/, with
band names, scale, offset and fill kept as tags, so a rerun resumes where it stopped. Failures are listed
in failures.json and retried on the next run. Login: GDAL follows LP DAAC's redirect to Earthdata
Login with ~/.netrc and keeps the session cookie in a file outside the repository (deleted at the end).
ECOSTRESS (D4): V003 first; V002 only for overpasses V003 lacks.

Outside the granule (REVIEW_NOTES L6): pixels of the window that fall outside the source granule are
filled with the source's nodata, or with NaN when the source declares none (ECOSTRESS QC and cloud): a 0
there would read as "best quality" or "clear". Each asset's tags record that fill, the outside-pixel count
and the source extent.

Cards (REVIEW_NOTES L7): `--card` writes data/cards/<field>/<set>.json from the cached files alone (no
network) and prints each asset's raw attributes. Quality flags (Fmask, QC, cloud) are applied later, by the
diary step; the card says so.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]

SETS = {   # name -> [(short_name, version, start), ...] in priority order, asset suffixes
    "hls_l30": ([("HLSL30_VI", "2.0", "2013-04-11")], [".NDVI.tif", ".Fmask.tif"]),
    "hls_s30": ([("HLSS30_VI", "2.0", "2015-11-28")], [".NDVI.tif", ".Fmask.tif"]),
    "eco_lste": ([("ECO_L2T_LSTE", "003", "2018-07-09"), ("ECO_L2T_LSTE", "002", "2018-07-09")],
                 ["_LST.tif", "_QC.tif", "_cloud.tif"]),
    "eco_esi": ([("ECO_L4T_ESI", "003", "2018-07-09"), ("ECO_L4T_ESI", "002", "2018-07-09")],
                ["_ESI.tif", "_cloud.tif"]),
}


def pick_assets(links, suffixes):
    """{suffix: url}; an exact suffix match, so '_LST.tif' never picks '_LST_err.tif'."""
    out = {}
    for sfx in suffixes:
        hit = [u for u in links if u.endswith(sfx)]
        if len(hit) != 1:
            raise ValueError(f"asset {sfx}: {len(hit)} match(es) in the granule links")
        out[sfx] = hit[0]
    return out


def granule_time(ur):
    m = re.search(r"\.(\d{4})(\d{3})T(\d{6})\.", ur)              # HLS: YYYYDDDTHHMMSS
    if m:
        hms = m.group(3)
        secs = int(hms[:2]) * 3600 + int(hms[2:4]) * 60 + int(hms[4:])
        return pd.Timestamp(f"{m.group(1)}-01-01") + pd.Timedelta(int(m.group(2)) - 1, unit="D") + \
            pd.Timedelta(secs, unit="s")
    m = re.search(r"_(\d{8}T\d{6})_", ur)                           # ECOSTRESS: YYYYMMDDTHHMMSS
    if m:
        return pd.Timestamp(m.group(1))
    raise ValueError(f"no acquisition time in {ur}")


def missing_from(primary_urs, fallback_urs):
    have = {granule_time(u) for u in primary_urs}
    return [u for u in fallback_urs if granule_time(u) not in have]


def _gdal_env(cookie):
    return dict(GDAL_HTTP_COOKIEFILE=cookie, GDAL_HTTP_COOKIEJAR=cookie, GDAL_HTTP_NETRC="YES",
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="3", GDAL_HTTP_TIMEOUT="120")


def outside_source(window, height, width):
    """True for each pixel of an integer window that lies outside a source of height x width pixels."""
    rows = np.arange(int(window.row_off), int(window.row_off) + int(window.height))
    cols = np.arange(int(window.col_off), int(window.col_off) + int(window.width))
    return ((rows < 0) | (rows >= height))[:, None] | ((cols < 0) | (cols >= width))[None, :]


def boundless_fill(nodata):
    """The value for window pixels outside the source: its nodata, or NaN when it declares none (L6)."""
    return float("nan") if nodata is None or not np.isfinite(nodata) else float(nodata)


def layers_where_valid(value, *layers, valid_range):
    """Each quality layer as float, NaN wherever `value` (ECOSTRESS LST or ESI) is not a valid measurement:
    NaN, or outside the product's valid_range. A V002 QC or cloud layer reads 0 ('best quality', 'clear') where
    the value is missing, so it is trusted only beside a valid value (rules.yaml ecostress.qc_needs_valid_value;
    owner's batch decisions item 25, 2026-11-12; golden rule 12c). Pure."""
    v = np.asarray(value, dtype="float64")
    lo, hi = valid_range
    ok = np.isfinite(v) & (v >= lo) & (v <= hi)
    return tuple(np.where(ok, np.asarray(layer, dtype="float64"), np.nan) for layer in layers)


def read_window(src, window):
    """Boundless read of band 1 as float64; pixels outside the source get boundless_fill(src.nodata), never a
    value that could be read as data. Returns (array, number of outside pixels)."""
    a = src.read(1, window=window, boundless=True, fill_value=src.nodata if src.nodata is not None else 0)
    a = a.astype("float64")
    out = outside_source(window, src.height, src.width)
    a[out] = boundless_fill(src.nodata)
    return a, int(out.sum())


def outside_pixels_from_tags(transform, shape, tags):
    """For a cached window, how many pixels lie outside its source granule, from the granule's own extent
    tags (HLS: ULX, ULY, NCOLS, NROWS, SPATIAL_RESOLUTION). None when the tags do not give the extent."""
    try:
        ulx, uly = float(tags["ULX"]), float(tags["ULY"])
        ncols, nrows, res = int(tags["NCOLS"]), int(tags["NROWS"]), float(tags["SPATIAL_RESOLUTION"])
    except (KeyError, TypeError, ValueError):
        return None
    xs = transform.c + transform.a * (np.arange(shape[1]) + 0.5)
    ys = transform.f + transform.e * (np.arange(shape[0]) + 0.5)
    bad_x = (xs < ulx) | (xs > ulx + ncols * res)
    bad_y = (ys > uly) | (ys < uly - nrows * res)
    return int((bad_y[:, None] | bad_x[None, :]).sum())


def read_granule(ur, assets, box, out_path, cookie):
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    bands, meta, prof = [], {}, None
    with rasterio.Env(**_gdal_env(cookie)):
        for sfx, url in assets.items():
            with rasterio.open("/vsicurl/" + url) as src:
                b = transform_bounds("EPSG:4326", src.crs, *box, densify_pts=21)
                w = from_bounds(*b, src.transform).round_offsets().round_lengths()
                a, n_out = read_window(src, w)
                if prof is None:
                    prof = dict(crs=src.crs, transform=src.window_transform(w), height=a.shape[0], width=a.shape[1])
                bands.append(a)
                meta[sfx] = {"dtype": src.dtypes[0], "nodata": src.nodata, "scale": src.scales[0],
                             "offset": src.offsets[0], "tags": src.tags(),
                             "outside_source_fill": "NaN" if src.nodata is None else src.nodata,
                             "outside_source_pixels": n_out,
                             "source_extent": {"width": src.width, "height": src.height,
                                               "transform": list(src.transform)[:6]}}
    stack = np.stack(bands)
    with rasterio.open(out_path, "w", driver="GTiff", count=len(bands), dtype="float64", compress="deflate",
                       **prof) as dst:
        dst.write(stack)
        for i, sfx in enumerate(assets, 1):
            dst.set_band_description(i, sfx.strip("._").replace(".tif", ""))
        dst.update_tags(granule=ur, acquired=str(granule_time(ur)), assets=json.dumps(meta, default=str))
    return meta


def granules(set_name, box):
    import earthaccess
    products, _ = SETS[set_name]
    chosen = []
    for sn, ver, start in products:
        g = earthaccess.search_data(short_name=sn, version=ver, bounding_box=tuple(box), temporal=(start, "2025-12-31"))
        urs = [x["umm"]["GranuleUR"] for x in g]
        keep = set(missing_from([c["umm"]["GranuleUR"] for c in chosen], urs)) if chosen else set(urs)
        chosen += [x for x in g if x["umm"]["GranuleUR"] in keep]
        print(f"{set_name}: {sn} v{ver}: {len(g)} granule(s), {len(keep)} used")
    return chosen


def fetch_set(field, set_name, workers=6, cookie=None, limit=None):
    import earthaccess
    earthaccess.login(strategy="netrc", persist=False)
    raw = REPO / "data" / "raw" / set_name / field["id"]
    raw.mkdir(parents=True, exist_ok=True)
    gs = granules(set_name, field["fetch_box"])[:limit]
    todo = [g for g in gs if not (raw / f"{g['umm']['GranuleUR']}.tif").exists()]
    print(f"{set_name}: {len(gs)} granules, {len(gs) - len(todo)} cached, {len(todo)} to read", flush=True)
    fails, done = {}, 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {}
        for g in todo:
            ur = g["umm"]["GranuleUR"]
            try:
                assets = pick_assets(g.data_links(), SETS[set_name][1])
            except ValueError as e:
                fails[ur] = str(e)
                continue
            futs[ex.submit(read_granule, ur, assets, field["fetch_box"], raw / f".{ur}.part.tif", cookie)] = ur
        for f in as_completed(futs):
            ur = futs[f]
            try:
                f.result()
                os.replace(raw / f".{ur}.part.tif", raw / f"{ur}.tif")
                done += 1
                if done % 25 == 0:
                    print(f"{set_name}: {done}/{len(futs)} read", flush=True)
            except Exception as e:                      # recorded and retried next run, never silently dropped
                fails[ur] = f"{type(e).__name__}: {str(e)[:200]}"
    (raw / "failures.json").write_text(json.dumps(fails, indent=1) + "\n")
    (raw / "granules.json").write_text(json.dumps(sorted(g["umm"]["GranuleUR"] for g in gs), indent=0) + "\n")
    print(f"{set_name}: read {done}, failed {len(fails)} (see failures.json), total cached "
          f"{len(list(raw.glob('[!.]*.tif')))}", flush=True)
    return fails


# Units the cached tags do not carry (L7). Value ranges seen in the cache are written beside them in the card.
DOC_UNITS = {
    "NDVI": "unitless NDVI (stored x 10000: scale_factor tag 0.0001)",
    "Fmask": "bit flags (the granule's Fmask description tag)",
    "LST": "K (float32, NaN fill; ECOSTRESS Gridded and Tiled User Guide V2 (2023) Table 5; ECOL2 User Guide V3)",
    "QC": "bit flags (uint16; bits 1&0: 00 produced, 01 produced but degraded, 11 not produced: ECOL2 User Guide V3 Table 6)",
    "cloud": "cloud mask (uint8; 1 = cloud, 0 = absence; fill 255 in V003: Tiled User Guide V2 sec. 1.3; JET User Guide Table 5)",
    "ESI": "unitless ratio 0 to 1 (float32, NaN fill: Tiled User Guide V2 Table 11; JET User Guide Table 5)",
}
RESOLUTION = {"hls_l30": "30 m", "hls_s30": "30 m", "eco_lste": "70 m", "eco_esi": "70 m"}
# Golden rule 12b ranges checked on the raw cache (counted as warnings here: QC is not applied yet, so the
# diary step must mask by QC and then fail loudly on anything left). band -> (rule, kind, to rule units)
RULE12 = {"LST": ("temp_c -30 to 50 C (LST in K - 273.15)", "temp_c", lambda x, m: x - 273.15),
          "NDVI": ("ndvi -1 to 1 (stored value x scale_factor)", "ndvi", lambda x, m: x * (m.get("scale") or 1.0) + (m.get("offset") or 0.0))}


def granule_version(ur):
    m = re.search(r"\.v(\d+\.\d+)$", ur) or re.search(r"^ECOv(\d{3})_", ur)
    return ("v" if ur.startswith("HLS") else "V") + m.group(1) if m else "unknown"


def field_pixel_count(polygon, crs, transform, shape):
    """Pixels of a grid over the field polygon ([lon, lat] corners): centres inside, and touching."""
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    ring = [list(p) for p in polygon] + [list(polygon[0])]
    geom = transform_geom("EPSG:4326", crs, {"type": "Polygon", "coordinates": [ring]})
    inside = ~geometry_mask([geom], out_shape=shape, transform=transform, all_touched=False)
    touch = ~geometry_mask([geom], out_shape=shape, transform=transform, all_touched=True)
    return {"centre_inside": int(inside.sum()), "touching": int(touch.sum())}


def write_set_card(field, set_name, data_dir=REPO / "data"):
    """L7: the data card for one cached set, from the cached window files only (no network). None if not cached."""
    import rasterio

    from pipeline.fetch import guards as g
    data_dir = Path(data_dir)
    raw = data_dir / "raw" / set_name / field["id"]
    files = sorted(raw.glob("[!.]*.tif"))
    if not files:
        print(f"{set_name}: nothing cached in {raw}; skipped")
        return None
    from pipeline.fetch.guards import RANGES
    names, fills, vrange, dates, versions, grids, nodatas, warn = None, {}, {}, [], {}, {}, {}, {}
    flag_zero = {}                                      # flag band reads 0 where the main band (band 1) is missing
    out_checked = out_any = out_unknown = 0
    first_meta = None
    for f in files:
        with rasterio.open(f) as d:
            a, tags, tr = d.read(), d.tags(), d.transform
            key = (str(d.crs.to_wkt()) if d.crs else "None", tuple(tr)[:6], d.shape)
            grids.setdefault(key, (d.crs, tr, d.shape))
        meta = json.loads(tags["assets"])
        first_meta = first_meta or meta
        names = names or [sfx.strip("._").replace(".tif", "") for sfx in meta]          # as read_granule names bands
        dates.append(pd.Timestamp(tags["acquired"]))
        v = granule_version(tags["granule"])
        versions[v] = versions.get(v, 0) + 1
        n_out = None
        main_missing = None
        for i, (sfx, m) in enumerate(meta.items()):
            band = names[i]
            nod = m.get("nodata")
            x = a[i]
            is_fill = np.isnan(x) if nod is None or not np.isfinite(nod) else (x == nod) | np.isnan(x)
            fills[band] = fills.get(band, 0) + int(is_fill.sum())
            nodatas.setdefault(band, set()).add(str(nod))
            if i == 0:
                main_missing = is_fill
            elif band in ("QC", "cloud", "Fmask"):
                flag_zero[band] = flag_zero.get(band, 0) + int(((x == 0) & main_missing).sum())
            ok = x[~is_fill]
            if band in RULE12 and ok.size:
                lo12, hi12 = RANGES[RULE12[band][1]]
                conv = RULE12[band][2](ok, m)
                n_bad = int(((conv < lo12) | (conv > hi12)).sum())
                if n_bad:
                    w = warn.setdefault(band, {"rule": RULE12[band][0], "granules": 0, "pixels": 0})
                    w["granules"] += 1
                    w["pixels"] += n_bad
            if ok.size:
                lo, hi = vrange.get(band, (np.inf, -np.inf))
                vrange[band] = (min(lo, float(ok.min())), max(hi, float(ok.max())))
            if "outside_source_pixels" in m:
                n_out = (n_out or 0) + m["outside_source_pixels"]
            elif n_out is None:
                n_out = outside_pixels_from_tags(tr, x.shape, m.get("tags") or {})
        if n_out is None:
            out_unknown += 1
        else:
            out_checked += 1
            out_any += int(n_out > 0)
    raw_attrs = {}
    for i, (sfx, m) in enumerate(first_meta.items()):
        t = m.get("tags") or {}
        raw_attrs[names[i]] = {**g.describe_raw_attrs({k: t[k] for k in ("units", "valid_range") if k in t}),
                               "scale_factor": m.get("scale"), "add_offset": m.get("offset"), "_FillValue": m.get("nodata"),
                               "dtype": m.get("dtype"), "long_name": t.get("long_name", "ABSENT"), "asset": sfx}
        print(f"raw attributes {set_name} {names[i]}: {raw_attrs[names[i]]}")
    raw_attrs["flag_zero_where_main_missing"] = flag_zero
    flags = [b for b in names[1:] if b in ("QC", "cloud", "Fmask")]
    fails = json.loads((raw / "failures.json").read_text()) if (raw / "failures.json").exists() else {}
    listed = json.loads((raw / "granules.json").read_text()) if (raw / "granules.json").exists() else []
    if len(grids) == 1:
        crs, tr, shape = next(iter(grids.values()))
        pixels = field_pixel_count(field["polygon"], crs, tr, shape)
    else:
        pixels = {f"grid {k}": field_pixel_count(field["polygon"], c, t, s) for k, (c, t, s) in enumerate(grids.values())}
    products = SETS[set_name][0]
    card = g.make_card(
        dataset=set_name, product=products[0][0],
        version=", ".join(f"{v} ({n} granules)" for v, n in sorted(versions.items())),
        variable=names, units_in={b: DOC_UNITS.get(b, "TODO-VERIFY") for b in names},
        units_out={b: "as stored (scale and offset not applied in the cache)" for b in names},
        scale_factor={names[i]: m.get("scale") for i, m in enumerate(first_meta.values())},
        fill_values_removed={b: {"nodata": sorted(nodatas.get(b, [])), "pixels_with_fill": fills.get(b, 0),
                                 "removed": "not yet: masked by the diary step"} for b in names},
        quality_flags_used=("none yet: Fmask / QC / cloud are applied later, by the diary step (pipeline/diary); "
                            "the cache keeps them raw"),
        records_dropped={"granules_listed": len(listed), "granules_cached": len(files), "failures": len(fails)},
        date_range=[str(min(dates).date()), str(max(dates).date())], time_zone="UTC (acquisition times in the granule names)",
        pixel_count=pixels,
        source=f"NASA LP DAAC {', '.join(f'{sn} {ver}' for sn, ver, _ in products)} (cloud-optimised GeoTIFFs, windowed reads)",
        resolution=RESOLUTION.get(set_name, "native"), raw_attrs=raw_attrs,
        range_warnings={b: warn.get(b, {"rule": RULE12[b][0], "granules": 0, "pixels": 0}) for b in names if b in RULE12},
        location={"box_grid": [{"crs": str(c), "transform": list(t)[:6], "shape": list(s)} for c, t, s in grids.values()],
                  "field_polygon": field["polygon"]},
        notes=(f"{len(files)} cached granules {min(dates).date()} to {max(dates).date()}; versions {versions}. "
               f"Value ranges in the cache (fills excluded): { {b: [round(lo, 4), round(hi, 4)] for b, (lo, hi) in vrange.items()} }. "
               f"L6 check: {out_any} of {out_checked} granule windows checked had pixels outside its source granule; "
               f"{out_unknown} could not be checked (the source extent is not in their tags). "
               + (f"Flag bands read 0 on pixels where {names[0]} is missing: {flag_zero} (the granules' own no-data area "
                  f"where a flag declares no nodata): mask by {names[0]}, never by {' or '.join(flags)} == 0."
                  if any(flag_zero.values()) else "")))
    path = g.write_card(card, data_dir / "cards" / field["id"])
    print(f"{set_name}: card -> {path}")
    return path


def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--set", nargs="+", default=list(SETS))
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--card", action="store_true", help="write each set's data card from the cache only (no network)")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    if a.card:
        for s in a.set:
            write_set_card(field, s)
        return 0
    fd, cookie = tempfile.mkstemp(prefix="gdal_cookies_", suffix=".txt")      # outside the repository
    os.close(fd)
    try:
        for s in a.set:
            fetch_set(field, s, workers=a.workers, cookie=cookie, limit=a.limit)
    finally:
        os.remove(cookie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
