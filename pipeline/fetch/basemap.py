"""Self-hosted NASA map backgrounds (owner's launch brief, 2026-11-14: the live site makes no outside request at runtime,
so the OpenStreetMap tiles are replaced by NASA pictures served from site/data/basemap/).

    .venv/bin/python -m pipeline.fetch.basemap                       # every field in site/data/index.json, and the world
    .venv/bin/python -m pipeline.fetch.basemap --date 2025-11-11 --sensor hls_l30     # a date chosen by hand (said so)

For each prepared field: a true-colour picture of its fetch box (config/fields/<id>.yaml fetch_box) from NASA GIBS, the
HLS Nadir BRDF-Adjusted Reflectance layer (Landsat 8/9 or Sentinel-2, 30 m), in Web Mercator (EPSG:3857, what Leaflet
uses), so `L.imageOverlay(image, bounds)` lines up exactly. Fields with the same fetch box share one picture, named after
their area in index.json. Plus one small world picture (Blue Marble, August 2004) for the zoomed-out view.

Which date (the rule, fixed before any picture was looked at; Claude's choice, 2026-11-14): from the field's own cached
HLS box windows (data/raw/hls_l30|hls_s30/<field>/, pipeline/fetch/cogwindows.py), the granules of November to February
(the dry season, after the rice harvest) of the last three calendar years in the cache that cover the whole box and are
at least 99 % clear (HLS Fmask bits 0-5 zero, as the diary uses: pipeline/diary/ndvi.py); among them the least hazy
(share of pixels with Fmask aerosol level moderate or high, bits 6-7), then the clearer, then the more recent. If none
qualifies, any month of those years (said in the card and the json). If GIBS has no picture for the date (transparent),
the next one is tried, and the skipped dates are listed in the card.

Resolution: HLS is 30 m; GIBS serves it in EPSG:3857 at zoom 12 (38.2 m Mercator pixels, about 34 m on the ground at
27.7 N). The picture is fetched at that size, not enlarged: GIBS only repeats pixels when asked for more. The 60 m demo
field is two pixels wide on it.

Source: NASA GIBS WMS (https://gibs.earthdata.nasa.gov, no login). NASA's open data policy: free to use; GIBS asks for
the acknowledgement in ACKNOWLEDGE. Raw PNGs are cached in data/raw/basemap/<name>/; outputs: site/data/basemap/<name>.jpg,
site/data/basemap/<field>.json (pipeline/export/basemap_schema.json), data/cards/<field>/basemap.json, CREDITS.md.
"""
import argparse
import io
import json
import math
import sys
from datetime import date as _date
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
WMS = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi"
ACKNOWLEDGE = ("We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services "
               "(GIBS), part of NASA's Earth Science Data and Information System (ESDIS).")
R_EARTH_M = 6378137.0                                   # WGS 84 semi-major axis: the Web Mercator sphere (EPSG:3857)
MERCATOR_HALF_M = math.pi * R_EARTH_M                   # 20037508.34 m
MERCATOR_MAX_LAT = math.degrees(2 * math.atan(math.exp(math.pi)) - math.pi / 2)    # 85.0511 deg: the square world's edge
LEVEL12_M = 2 * MERCATOR_HALF_M / (256 * 2 ** 12)       # GIBS HLS in EPSG:3857: GoogleMapsCompatible_Level12 (38.2 m)
HLS_LAYERS = {"hls_l30": "HLS_L30_Nadir_BRDF_Adjusted_Reflectance", "hls_s30": "HLS_S30_Nadir_BRDF_Adjusted_Reflectance"}
WORLD_LAYER = "BlueMarble_NextGeneration"
PRODUCTS = {   # GIBS layer metadata (gibs.earthdata.nasa.gov/layer-metadata/v1.0/<layer>.json, read 2026-11-14)
    HLS_LAYERS["hls_l30"]: ("HLS Landsat 8/9 OLI (HLSL30 v2.0, LP DAAC), Nadir BRDF-Adjusted Reflectance, true colour",
                            "NASA HLS (Landsat 8/9)"),
    HLS_LAYERS["hls_s30"]: ("HLS Sentinel-2 MSI (HLSS30 v2.0, LP DAAC), Nadir BRDF-Adjusted Reflectance, true colour",
                            "NASA HLS (Sentinel-2)"),
    WORLD_LAYER: ("Blue Marble: Next Generation, August 2004 (MODIS; NASA Earth Observatory, Stockli et al. 2005)",
                  "NASA Blue Marble (Aug 2004)"),
}
DRY_MONTHS = (11, 12, 1, 2)
RECENT_YEARS = 3
MIN_CLEAR, MIN_COVERAGE = 0.99, 0.999
MAX_TRANSPARENT = 0.01                                  # more than 1 % without data: GIBS has no picture for that date
MAX_FIELD_BYTES, MAX_WORLD_BYTES = 300_000, 400_000     # owner's launch brief
WORLD_PX = 1024
QUALITIES = (90, 85, 80, 75, 70, 65, 60)
CLEAR_BITS, NO_DATA = 0b00111111, 255


class BasemapError(ValueError):
    """A picture that must not be published (no data, blank, too large) or a box that cannot be drawn."""


# ---------- pure ----------

def mercator(lon, lat):
    """(x, y) in EPSG:3857 metres."""
    return R_EARTH_M * math.radians(lon), R_EARTH_M * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def box_request(box, m_per_px=LEVEL12_M):
    """The GetMap box and size for [min_lon, min_lat, max_lon, max_lat] at GIBS's own pixel size."""
    x0, y0 = mercator(box[0], box[1])
    x1, y1 = mercator(box[2], box[3])
    return {"bbox": [x0, y0, x1, y1], "width": max(1, round((x1 - x0) / m_per_px)),
            "height": max(1, round((y1 - y0) / m_per_px))}


def ground_m_per_px(req, box):
    """Metres on the ground per image pixel at the box's middle latitude."""
    return (req["bbox"][2] - req["bbox"][0]) / req["width"] * math.cos(math.radians((box[1] + box[3]) / 2))


def leaflet_bounds(box):
    return [[box[1], box[0]], [box[3], box[2]]]


def granule_stats(fmask):
    """{coverage, clear, hazy} of one HLS Fmask window: share with data; share clear (bits 0-5 zero, of all pixels);
    share of the pixels with data whose aerosol level (bits 6-7) is moderate or high."""
    f = np.asarray(fmask)
    valid = f != NO_DATA
    fi = f.astype(np.uint16)
    clear = valid & ((fi & CLEAR_BITS) == 0)
    hazy = valid & (((fi >> 6) & 3) >= 2)
    n_valid = int(valid.sum())
    return {"coverage": float(valid.mean()), "clear": float(clear.mean()),
            "hazy": float(hazy.sum() / n_valid) if n_valid else 1.0}


def rank_dates(rows, last_year):
    """The candidate dates, best first, and the rule that found them ('dry season', 'any month' or None)."""
    years = range(last_year - RECENT_YEARS + 1, last_year + 1)
    ok = [r for r in rows if int(r["date"][:4]) in years and r["coverage"] >= MIN_COVERAGE and r["clear"] >= MIN_CLEAR]

    def key(r):
        return (round(r["hazy"], 4), -round(r["clear"], 4), -_date.fromisoformat(r["date"]).toordinal())
    dry = sorted((r for r in ok if int(r["date"][5:7]) in DRY_MONTHS), key=key)
    if dry:
        return dry, "dry season"
    if ok:
        return sorted(ok, key=key), "any month"
    return [], None


def wms_params(layer, req, when, fmt="image/png"):
    p = {"SERVICE": "WMS", "REQUEST": "GetMap", "VERSION": "1.3.0", "LAYERS": layer, "STYLES": "", "CRS": "EPSG:3857",
         "BBOX": ",".join(f"{v:.6f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v) for v in req["bbox"]),
         "WIDTH": req["width"], "HEIGHT": req["height"], "FORMAT": fmt, "TRANSPARENT": "TRUE"}
    if when:
        p["TIME"] = when
    return p


def to_jpeg(png_bytes, max_bytes, max_transparent=MAX_TRANSPARENT):
    """PNG from GIBS -> (JPEG bytes, info). Fails loudly on a picture without data, a blank one, or one that cannot be
    brought under max_bytes by quality 60."""
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes))
    print(f"  raw picture: format {im.format}, mode {im.mode}, size {im.size}, {len(png_bytes)} bytes")
    a = np.asarray(im.convert("RGBA"))
    transparent = int((a[..., 3] == 0).sum())
    share = transparent / (a.shape[0] * a.shape[1])
    if share > max_transparent:
        raise BasemapError(f"{share:.0%} of the picture has no data (GIBS has no image there for this date)")
    rgb = a[..., :3][a[..., 3] > 0]
    if rgb.size == 0 or float(rgb.mean()) < 5:
        raise BasemapError("the picture is blank (all black)")
    out = Image.fromarray(a[..., :3], "RGB")
    for q in QUALITIES:
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue(), {"quality": q, "bytes": buf.tell(), "size_px": list(out.size),
                                    "transparent_px": transparent, "mean_rgb": [round(float(v), 1) for v in rgb.mean(0)]}
    raise BasemapError(f"the picture is {buf.tell()} bytes at quality {QUALITIES[-1]}, over the "
                       f"{max_bytes // 1000} KB limit")


def group_fields(index, boxes):
    """[{name, box, fields}]: the index's fields grouped by fetch box, named after their area (else the first field)."""
    out = []
    for f in index["fields"]:
        if f["id"] == "world":
            raise BasemapError("a field may not be called 'world': that name is the world picture's")
        box = [float(v) for v in boxes[f["id"]]]
        g = next((g for g in out if g["box"] == box), None)
        if g:
            g["fields"].append(f["id"])
        else:
            out.append({"name": f.get("area") or f["id"], "box": box, "fields": [f["id"]]})
    return out


def field_doc(field_id, name, box, req, layer, when, chosen):
    product, short = PRODUCTS[layer]
    return {"id": field_id, "image": f"data/basemap/{name}.jpg", "bounds": leaflet_bounds(box), "crs": "EPSG:3857",
            "size_px": [req["width"], req["height"]], "native_zoom": 12, "layer": layer, "product": product, "date": when,
            "resolution": f"30 m (HLS); about {ground_m_per_px(req, box):.0f} m per picture pixel here (GIBS, Web Mercator zoom 12)",
            "attribution": f"{short}, {_date.fromisoformat(when):%d %b %Y}, via NASA GIBS",
            "chosen_by": chosen, "source": WMS}


def world_doc(size_px=WORLD_PX):
    product, short = PRODUCTS[WORLD_LAYER]
    km = 2 * MERCATOR_HALF_M / size_px / 1000
    return {"id": "world", "image": "data/basemap/world.jpg",
            "bounds": [[-MERCATOR_MAX_LAT, -180.0], [MERCATOR_MAX_LAT, 180.0]], "crs": "EPSG:3857",
            "size_px": [size_px, size_px], "native_zoom": int(math.log2(size_px / 256)), "layer": WORLD_LAYER,
            "product": product, "date": "2004-08",
            "resolution": f"500 m (Blue Marble); about {km:.0f} km per picture pixel at the equator",
            "attribution": f"{short}, via NASA GIBS", "chosen_by": "the whole world, for the zoomed-out view",
            "source": WMS}


# ---------- I/O ----------

def granule_rows(field_id, data_dir):
    """[{date, sensor, coverage, clear, hazy, granule}] from the field's cached HLS box windows (band 2 = Fmask)."""
    import rasterio
    rows = []
    for sensor in HLS_LAYERS:
        for f in sorted((Path(data_dir) / "raw" / sensor / field_id).glob("[!.]*.tif")):
            with rasterio.open(f) as src:
                acquired = src.tags()["acquired"]
                fmask = src.read(2)
            rows.append({"date": acquired[:10], "sensor": sensor, "granule": f.name, **granule_stats(fmask)})
    return rows


def fetch_png(layer, req, when, cache_dir, session):
    cache_dir = Path(cache_dir)
    path = cache_dir / f"{layer}_{when or 'static'}_{req['width']}x{req['height']}.png"
    if path.exists():
        return path.read_bytes(), path
    r = session.get(WMS, params=wms_params(layer, req, when), timeout=180,
                    headers={"User-Agent": "khet-sathi-pipeline (static site build)"})
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if not ctype.startswith("image/png"):
        raise BasemapError(f"GIBS answered {ctype!r}, not a PNG: {r.content[:300]!r}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content, path


def fetch_first_good(rows, req, cache_dir, session, max_bytes=MAX_FIELD_BYTES, tries=5):
    """The first candidate date for which GIBS has a whole picture: {row, jpeg, info, png_path, skipped}."""
    skipped = []
    for row in rows[:tries]:
        layer = HLS_LAYERS[row["sensor"]]
        print(f"  trying {layer} {row['date']} (clear {row['clear']:.4f}, hazy {row['hazy']:.3f})")
        png, path = fetch_png(layer, req, row["date"], cache_dir, session)
        try:
            jpeg, info = to_jpeg(png, max_bytes)
        except BasemapError as e:
            skipped.append({"date": row["date"], "sensor": row["sensor"], "why": str(e)})
            continue
        return {"row": row, "jpeg": jpeg, "info": info, "png_path": str(path), "skipped": skipped}
    raise BasemapError(f"no candidate date gave a whole picture (tried {[s['date'] for s in skipped]})")


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    tmp.replace(path)


def _card(field_id, doc, info, rule, rows_seen, skipped, data_dir, req, png_path):
    from pipeline.fetch import guards as g
    world = field_id == "world"
    card = g.make_card(
        dataset="basemap", product=doc["product"], version="GIBS WMS 'best' (EPSG:3857)" + ("" if world else "; HLS v2.0"),
        variable="true-colour picture (red, green, blue)", units_in="8-bit RGBA PNG rendered by GIBS",
        units_out="8-bit RGB JPEG (progressive)", scale_factor=None,
        fill_values_removed={"transparent_px": info["transparent_px"], "rule": f"fail if over {MAX_TRANSPARENT:.0%}"},
        quality_flags_used=("none (a static composite)" if world else
                            "HLS Fmask of the cached box windows: bits 0-5 clear, bits 6-7 aerosol level (date choice only)"),
        records_dropped={"dates_skipped": skipped}, date_range=[doc["date"], doc["date"]],
        time_zone="UTC acquisition date" if not world else "not applicable (monthly composite)",
        pixel_count={"picture_px": doc["size_px"]}, source=f"NASA GIBS WMS {WMS}; {ACKNOWLEDGE}",
        resolution=doc["resolution"],
        raw_attrs={"request": wms_params(doc["layer"], req, None if world else doc["date"]),
                   "raw_png": png_path, "jpeg": {k: info[k] for k in ("quality", "bytes", "mean_rgb")}},
        location={"bounds": doc["bounds"], "image": doc["image"]},
        notes=(doc["chosen_by"] + (f" (rule: {rule}; {rows_seen} cached HLS granules looked at)" if not world else "")))
    return g.write_card(card, Path(data_dir) / "cards" / field_id)


def build(site_data=REPO / "site" / "data", data_dir=REPO / "data", session=None, when=None, sensor=None, world=True,
          credits=REPO / "CREDITS.md"):
    import requests
    import yaml

    from pipeline.fetch.credits import ensure_credit
    session = session or requests.Session()
    site_data, data_dir = Path(site_data), Path(data_dir)
    index = json.loads((site_data / "index.json").read_text())
    boxes = {f["id"]: yaml.safe_load((REPO / "config" / "fields" / f"{f['id']}.yaml").read_text())["fetch_box"]
             for f in index["fields"]}
    made = []
    today = _date.today().isoformat()
    for grp in group_fields(index, boxes):
        name, box = grp["name"], grp["box"]
        print(f"{name}: box {box}, fields {', '.join(grp['fields'])}")
        req = box_request(box)
        if when:
            rows = [{"date": when, "sensor": sensor or "hls_l30", "clear": float("nan"), "hazy": float("nan")}]
            order, rule, seen = rows, "chosen by hand (--date)", 0
        else:
            src = max(grp["fields"], key=lambda f: len(list((data_dir / "raw" / "hls_l30" / f).glob("*.tif")))
                      + len(list((data_dir / "raw" / "hls_s30" / f).glob("*.tif"))))
            rows = granule_rows(src, data_dir)
            if not rows:
                raise BasemapError(f"no cached HLS windows for {grp['fields']}: run pipeline/fetch/cogwindows.py first")
            last = max(int(r["date"][:4]) for r in rows)
            order, rule = rank_dates(rows, last)
            seen = len(rows)
            if not order:
                raise BasemapError(f"{name}: no HLS granule of {last - RECENT_YEARS + 1}-{last} covers the box at least "
                                   f"{MIN_CLEAR:.0%} clear; pass --date and --sensor")
        got = fetch_first_good(order, req, data_dir / "raw" / "basemap" / name, session)
        row, info = got["row"], got["info"]
        if when:
            chosen = f"chosen by hand: {when}"
        else:
            chosen = (f"the least hazy {'November-February' if rule == 'dry season' else 'any-month'} HLS picture of "
                      f"{last - RECENT_YEARS + 1}-{last} that covers the whole box at least {MIN_CLEAR:.0%} clear "
                      f"(HLS Fmask): {row['clear']:.2%} clear, {row['hazy']:.1%} moderate or high aerosol")
        _write(site_data / "basemap" / f"{name}.jpg", got["jpeg"])
        layer = HLS_LAYERS[row["sensor"]]
        for fid in grp["fields"]:
            doc = field_doc(fid, name, box, req, layer, row["date"], chosen)
            _write(site_data / "basemap" / f"{fid}.json", json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
            _card(fid, doc, info, rule, seen, got["skipped"], data_dir, req, got["png_path"])
            ensure_credit(credits, f"- NASA GIBS WMS, {PRODUCTS[layer][0]}, {row['date']}, field `{fid}`'s fetch box, "
                                   f"fetched {today} by pipeline/fetch/basemap.py (the site's map background; "
                                   f"site/data/basemap/{name}.jpg)")
        made.append((name, row["date"], info["bytes"], info["size_px"]))
        print(f"  -> site/data/basemap/{name}.jpg {info['size_px']} {info['bytes']} bytes (quality {info['quality']}); "
              f"{row['date']} {layer}")
    if world:
        req = {"bbox": [-MERCATOR_HALF_M, -MERCATOR_HALF_M, MERCATOR_HALF_M, MERCATOR_HALF_M], "width": WORLD_PX,
               "height": WORLD_PX}
        png, path = fetch_png(WORLD_LAYER, req, None, data_dir / "raw" / "basemap" / "world", session)
        jpeg, info = to_jpeg(png, MAX_WORLD_BYTES)
        doc = world_doc(WORLD_PX)
        _write(site_data / "basemap" / "world.jpg", jpeg)
        _write(site_data / "basemap" / "world.json", json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        _card("world", doc, info, None, 0, [], data_dir, req, str(path))
        ensure_credit(credits, f"- NASA GIBS WMS, {PRODUCTS[WORLD_LAYER][0]}, the whole world at {WORLD_PX} px, fetched "
                               f"{today} by pipeline/fetch/basemap.py (the site's zoomed-out map; site/data/basemap/world.jpg)")
        made.append(("world", "2004-08", info["bytes"], info["size_px"]))
        print(f"  -> site/data/basemap/world.jpg {info['size_px']} {info['bytes']} bytes (quality {info['quality']})")
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="use this date instead of the rule (YYYY-MM-DD; said in the json and the card)")
    ap.add_argument("--sensor", choices=sorted(HLS_LAYERS), help="with --date: hls_l30 (Landsat) or hls_s30 (Sentinel-2)")
    ap.add_argument("--no-world", action="store_true", help="skip the world picture")
    a = ap.parse_args(argv)
    try:
        made = build(when=a.date, sensor=a.sensor, world=not a.no_world)
    except BasemapError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 2
    for name, when, n, size in made:
        print(f"{name}: {when}, {size[0]} x {size[1]} px, {n / 1000:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
