"""Local Impact 4a: bare days and crop seasons for every cropland pixel of a field's fetch box, by the field diary's
own methods (rules.yaml area_map and sample_fields, committed before the first run in cb85cc8). No new download.

    .venv/bin/python scripts/run_area_map.py --field demo [--workers 6]

Writes data/checks/<field>/area_map.json (numbers, uncertainty, the field check, every prepared field in the box),
site/data/area/<field>_bare_days.png, <field>_seasons.png and <field>.json (bounds, classes, legend, sources).
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.area import pixels as px  # noqa: E402
from pipeline.area import render as rd  # noqa: E402
from pipeline.area import stats as st  # noqa: E402
from pipeline.diary import greenness as gr  # noqa: E402
from pipeline.diary import ndvi as nd  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.export.build_story import _DEVANAGARI as NE_DIGITS  # noqa: E402

END = "2025-12-31"


def read_hls(field, data, cols_mask):
    """Every cached HLS granule window: (dates, raw int16 NDVI where clear else fill, at the pixels in cols_mask)."""
    import rasterio
    files = [f for s in ("hls_l30", "hls_s30") for f in sorted((data / "raw" / s / field["id"]).glob("[!.]*.tif"))]
    dates, rows, grid, fill, scale = [], [], None, None, None
    for f in files:
        with rasterio.open(f) as src:
            if grid is None:
                grid = (src.shape, src.transform, src.crs)
            if (src.shape, src.transform) != grid[:2]:
                raise ValueError(f"{f.name}: window grid differs from the first granule's")
            meta = json.loads(src.tags()["assets"])[".NDVI.tif"]
            if fill is None:
                fill, scale = float(meta["nodata"]), float(meta["scale"])
            if (float(meta["nodata"]), float(meta["scale"])) != (fill, scale):
                raise ValueError(f"{f.name}: NDVI fill or scale differs")
            raw = src.read(1)
            nd.scale_ndvi(raw, fill, scale)                       # the guard: fails loudly outside -1..1
            clear = nd.clear_mask(src.read(2))
            rows.append(np.where(clear, raw, np.int16(fill))[cols_mask])
            dates.append(pd.Timestamp(src.tags()["acquired"]).normalize())
    return pd.DatetimeIndex(dates), np.stack(rows), grid, fill, scale, len(files)


def field_way(dates, raw, fill, scale, min_clear, start, years, ndvi_max, S):
    """The diary's own field series from the field's pixels (mean of clear pixels, kept at >= min_clear of them)."""
    v = raw.astype(float); v[raw == fill] = np.nan; v *= scale
    obs = [gr.field_observation(v[i], np.isfinite(v[i]), np.ones(v.shape[1], bool), min_clear)["ndvi"] for i in range(len(v))]
    o = pd.DataFrame({"date": dates, "ndvi": obs}).dropna()
    first = max(o["date"].min(), pd.Timestamp(start))
    o = o[o["date"] >= first]
    u, m = px.same_day_mean(o["date"], o["ndvi"].to_numpy()[:, None])
    daily = px.daily_matrix(u, m, str(first.date()), END)
    days = pd.date_range(first, END)
    b, h = px.yearly_counts(daily, days, years, ndvi_max)
    peaks = px.pixel_season_peak_years(days, daily[:, 0], S)
    return {"bare_by_year": {str(y): int(b[i, 0]) for i, y in enumerate(years)},
            "days_with_value": {str(y): int(h[i, 0]) for i, y in enumerate(years)},
            "seasons_by_year": dict(zip(map(str, years), px.count_by_year(peaks, years))), "first_obs": str(first.date()),
            "daily": daily[:, 0], "days": days}


def summarise_way(w, A):
    ok = [y for y, h in w["days_with_value"].items() if h >= A["min_days_with_value"]]
    mb = float(np.mean([w["bare_by_year"][y] for y in ok])) if len(ok) >= A["min_years"] else None
    ms = float(np.mean([w["seasons_by_year"][y] for y in ok])) if len(ok) >= A["min_years"] else None
    return {"mean_bare_days": None if mb is None else round(mb, 1), "mean_seasons_a_year": None if ms is None else round(ms, 2),
            "seasons_class": None if ms is None else int(st.season_class(np.array([ms]))[0]), "years_counted": len(ok)}


def r3(x):
    return None if x is None else round(float(x), 3)


NE_REVIEW = "needs native-speaker review"


def _in10(x):
    return int(round(x * 10))


def site_json(field, A, out, site_dir):
    """site/data/area/<field>.json: bounds for L.imageOverlay, classes and colours, plain-word legend (English, at
    most 8 words a line; Nepali drafted by SI, needs a native speaker's review), the numbers, the sources."""
    K, box, n = A["classes"], field["fetch_box"], out["numbers"]
    br = K["bare_days_breaks"]
    bare_cls = [{"code": 0, "min_days": 0, "max_days": br[0], "en": f"Under {br[0]} days", "ne": f"{br[0]} दिनभन्दा कम"}]
    bare_cls += [{"code": i + 1, "min_days": lo, "max_days": hi, "en": f"{lo} to {hi} days", "ne": f"{lo} देखि {hi} दिन"}
                 for i, (lo, hi) in enumerate(zip(br[:-1], br[1:]))]
    bare_cls += [{"code": len(br), "min_days": br[-1], "max_days": None, "en": f"{br[-1]} days or more", "ne": f"{br[-1]} दिन वा बढी"}]
    for c, col in zip(bare_cls, K["bare_days_colours"]):
        c["colour"] = col
    seas_cls = [{"code": i, "crops_a_year": i, "en": en, "ne": ne, "colour": col} for i, (en, ne, col) in enumerate(zip(
        ["No crop seen", "One crop", "Two crops", "Three or more crops"],
        ["बाली देखिएन", "एक बाली", "दुई बाली", "तीन वा बढी बाली"], K["seasons_colours"]))]
    seas_cls[3]["crops_a_year"] = "3 or more"
    no_data = {"code": -1, "colour": K["no_data_colour"], "en": "Not enough clear pictures", "ne": "सफा तस्बिर पुगेनन्"}
    common_en = ["Seen from space, 2014 to 2025.", "Each square is 30 metres.", "Space sees green, not which crop.",
                 "No colour: not farmland on the map.", "Your own field may differ."]
    common_ne = [s.translate(NE_DIGITS) for s in ["अन्तरिक्षबाट हेरिएको, 2014 देखि 2025।", "हरेक कोठा 30 मिटरको।", "भू-उपग्रहले हरियो देख्छ, कुन बाली होइन।",
                 "रङ नभएको ठाउँ: नक्सामा खेत होइन।", "तपाईंको आफ्नै खेत फरक हुन सक्छ।"]]
    mb, lb, ts = n["median_bare_days"], n["share_long_bare"], n["share_two_seasons"]
    nums = [{"id": "median_bare_days", "value": round(mb["value"]), "low": round(mb["low"]), "high": round(mb["high"]), "unit": "days a year",
             "en": [f"A typical field here is bare {round(mb['value'])} days.", f"Could be {round(mb['low'])} to {round(mb['high'])} days."],
             "ne": [s.translate(NE_DIGITS) for s in [f"यहाँको सामान्य खेत वर्षमा {round(mb['value'])} दिन खाली रहन्छ।", f"{round(mb['low'])} देखि {round(mb['high'])} दिन हुन सक्छ।"]]},
            {"id": "share_long_bare", "value": r3(lb["value"]), "low": r3(lb["low"]), "high": r3(lb["high"]), "unit": "share of cropland",
             "en": [f"{_in10(lb['value'])} in 10 fields: bare over two months.", f"Could be {_in10(lb['low'])} to {_in10(lb['high'])} in 10."],
             "ne": [s.translate(NE_DIGITS) for s in [f"10 मध्ये {_in10(lb['value'])} खेत दुई महिनाभन्दा बढी खाली।", f"10 मध्ये {_in10(lb['low'])} देखि {_in10(lb['high'])} हुन सक्छ।"]]},
            {"id": "share_two_seasons", "value": r3(ts["value"]), "low": r3(ts["low"]), "high": r3(ts["high"]), "unit": "share of cropland",
             "en": [f"{_in10(ts['value'])} in 10 fields: two crops a year.", f"Could be {_in10(ts['low'])} to {_in10(ts['high'])} in 10."],
             "ne": [s.translate(NE_DIGITS) for s in [f"10 मध्ये {_in10(ts['value'])} खेतमा वर्षमा दुई बाली।", f"10 मध्ये {_in10(ts['low'])} देखि {_in10(ts['high'])} हुन सक्छ।"]]}]
    doc = {"id": field["id"], "placeholder": True,
           "note": "Map of the farmland around the PLACEHOLDER demo field (its fetch box). Proposal: not yet in the contract.",
           "bounds": [[box[1], box[0]], [box[3], box[2]]], "bbox": box,
           "image": {"crs": "EPSG:3857 (Web Mercator), for Leaflet L.imageOverlay(url, bounds)", "width": out["pngs"]["bare_days"]["width"],
                     "height": out["pngs"]["bare_days"]["height"], "ground_pixel_m": A["render"]["ground_pixel_m"],
                     "css": "image-rendering: pixelated (the classes must not blur into new colours)", "transparent": "not cropland"},
           "layers": [{"id": "bare_days", "image": out["pngs"]["bare_days"]["file"], "bytes": out["pngs"]["bare_days"]["bytes"],
                       "title": {"en": "Days of bare ground each year", "ne": "हरेक वर्ष जमिन खाली रहने दिन"},
                       "classes": bare_cls, "no_data": no_data, "legend": {"en": common_en, "ne": common_ne}},
                      {"id": "seasons", "image": out["pngs"]["seasons"]["file"], "bytes": out["pngs"]["seasons"]["bytes"],
                       "title": {"en": "Crops grown each year", "ne": "हरेक वर्ष लगाइने बाली"},
                       "classes": seas_cls, "no_data": no_data, "legend": {"en": common_en, "ne": common_ne}}],
           "numbers": nums, "ne_status": NE_REVIEW,
           "fields_in_area": sorted(out["fields"]),
           "sources": [{"name": "NASA HLS (Landsat 8/9, Sentinel-2)", "product": "HLSL30_VI and HLSS30_VI v2.0, NDVI and Fmask",
                        "resolution": "30 m", "years": "2014-2025", "type": "satellite"},
                       {"name": "ESA WorldCover", "product": "10 m 2021 v200, cropland class (user's accuracy for Asia 80.6% +/- 2.8)",
                        "resolution": "10 m (cropland if half of a 30 m square)", "years": "2021", "type": "satellite"}],
           "method": {"en": "Bare days and crop seasons as for the demo field's diary, for every cropland pixel; "
                            "range = bare threshold 0.20 to 0.30 and WorldCover's published accuracy, worst case",
                      "checks": "data/checks/demo/area_map.json (VALIDATION 3.23)"}}
    path = site_dir / f"{field['id']}.json"
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"-> {path.relative_to(REPO)} ({path.stat().st_size} bytes)")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--chunk", type=int, default=1500)
    ap.add_argument("--smoke", type=int, default=0, help="debug only: keep this many cropland pixels (numbers meaningless)")
    a = ap.parse_args(argv)
    import rasterio
    t0 = time.time()
    field, rules = load_field(a.field), load_rules()
    A, S = rules["area_map"], rules["season_detection"]
    ndvi_max, shift = rules["bare_days"]["ndvi_max"], A["threshold_shift"]
    thresholds = [round(ndvi_max - shift, 4), ndvi_max, round(ndvi_max + shift, 4)]
    years = list(range(A["years"][0], A["years"][1] + 1))
    start = rules["greenness"]["hls_from"]
    data = REPO / "data"
    out_checks = data / "checks" / field["id"]
    site_dir = REPO / "site" / "data" / "area"
    site_dir.mkdir(parents=True, exist_ok=True)

    # grid, cropland
    first = sorted((data / "raw" / "hls_l30" / field["id"]).glob("[!.]*.tif"))[0]
    with rasterio.open(first) as src:
        shape, ht, hcrs = src.shape, src.transform, src.crs
    wcf = sorted((data / "raw" / "worldcover" / field["id"]).glob("worldcover_2021_*_box.tif"))[0]
    with rasterio.open(wcf) as src:
        wc, wt, wcrs = src.read(1), src.transform, src.crs
    C = A["cropland"]
    frac, n_wc = px.cropland_fraction(wc, wt, wcrs, shape, ht, hcrs, C["worldcover_class"])
    exp = px.expected_centres(wt, field["origin_point"]["lat"], 30)
    crop = px.cropland_mask(frac, n_wc, exp, C["min_cropland_fraction"], C["min_coverage_fraction"])
    if a.smoke:                                                    # debug only
        keep_px = np.nonzero(crop.ravel())[0][::max(1, int(crop.sum()) // a.smoke)][:a.smoke]
        crop = np.isin(np.arange(crop.size), keep_px).reshape(crop.shape)
    pure = crop & (frac >= A["pure_check_min_fraction"])
    in_box = n_wc >= C["min_coverage_fraction"] * exp
    print(f"grid {shape}; WorldCover centres per 30 m pixel expected {exp:.2f}; in box {int(in_box.sum())} pixels; "
          f"cropland {int(crop.sum())} ({crop.sum() * 0.09:.0f} ha), pure {int(pure.sum())}", flush=True)

    # prepared fields inside the box (the demo and the samples)
    fields = {}
    for p in sorted((REPO / "config" / "fields").glob("*.yaml")):
        f = load_field(p.stem)
        b = field["fetch_box"]
        if f.get("polygon") and all(b[0] < x < b[2] and b[1] < y < b[3] for x, y in f["polygon"]):
            fields[f["id"]] = (f, gr.field_mask(shape, ht, hcrs, f["polygon"]))
    use = crop.copy()
    for f, m in fields.values():
        use |= m
    flat_use = np.nonzero(use.ravel())[0]
    print(f"prepared fields in the box: {list(fields)}; pixels to process {len(flat_use)}", flush=True)

    dates, raw, grid, fill, scale, n_files = read_hls(field, data, use)
    keep = dates >= pd.Timestamp(start)
    dates, raw = dates[keep], raw[keep]
    print(f"{n_files} granules read ({int(keep.sum())} from {start}); {time.time() - t0:.0f} s", flush=True)

    # per pixel, in parallel blocks
    P = raw.shape[1]
    blocks = [slice(i, min(i + a.chunk, P)) for i in range(0, P, a.chunk)]
    args = [(dates, raw[:, b], fill, scale, start, END, years, thresholds, S) for b in blocks]
    bare = {t: np.zeros((len(years), P), int) for t in thresholds}
    has = np.zeros((len(years), P), int)
    seas = np.zeros((len(years), P), int)
    with Pool(a.workers) as pool:
        for k, (bb, hh, ss) in enumerate(pool.imap(px.process_chunk, args)):
            b = blocks[k]
            for t in thresholds:
                bare[t][:, b] = bb[t]
            has[:, b], seas[:, b] = hh, ss
            print(f"  block {k + 1}/{len(blocks)} done, {time.time() - t0:.0f} s", flush=True)

    counted = has >= A["min_days_with_value"]
    mean_bare = {t: st.mean_over_counted(bare[t], counted, A["min_years"]) for t in thresholds}
    mean_seas = st.mean_over_counted(seas, counted, A["min_years"])
    scls = st.season_class(mean_seas)

    def grid_of(vec, fillv=np.nan):
        g = np.full(shape[0] * shape[1], fillv, dtype=float)
        g[flat_use] = vec
        return g.reshape(shape)

    MB = {t: grid_of(mean_bare[t]) for t in thresholds}
    SC = grid_of(scls, -2).astype(int)
    MS = grid_of(mean_seas)

    def numbers_for(mask):
        res = {}
        for t in thresholds:
            res[str(t)] = st.numbers(MB[t][mask], SC[mask], A["long_bare_days"])
        return res

    main_n, pure_n = numbers_for(crop), numbers_for(pure)
    c = st.commission(A["worldcover_accuracy"]["asia_cropland_users_pct"], A["worldcover_accuracy"]["asia_cropland_users_ci_pct"])
    m = main_n[str(ndvi_max)]
    vals = MB[ndvi_max][crop]
    wc_b = {"median_bare_days": st.median_bound(vals, c), "share_long_bare": st.share_bound(m["share_long_bare"], c),
            "share_two_seasons": st.share_bound(m["share_two_seasons"], c)}
    thr_vals = {k: [main_n[str(t)][k] for t in thresholds] for k in ("median_bare_days", "share_long_bare")}

    # year by year (that year's per-pixel values; a pixel-year counts with min_days_with_value)
    flat_crop = crop.ravel()[flat_use]
    per_year = {}
    for i, y in enumerate(years):
        okb = counted[i] & flat_crop
        yb = bare[ndvi_max][i][okb]
        per_year[str(y)] = {"pixels": int(okb.sum()), "median_bare_days": float(np.median(yb)),
                            "share_long_bare": float((yb > A["long_bare_days"]).mean()),
                            "share_two_seasons": float((seas[i][okb] == 2).mean())}

    def entry(key, value, unit):
        lo = min([wc_b[key][0]] + thr_vals.get(key, []))
        hi = max([wc_b[key][1]] + thr_vals.get(key, []))
        yv = [per_year[y][key] for y in per_year]
        return {"value": r3(value), "low": r3(lo), "high": r3(hi), "unit": unit,
                "threshold_range": [r3(v) for v in thr_vals[key]] if key in thr_vals else "not applicable: the season method does not use the bare threshold",
                "worldcover_bound": [r3(v) for v in wc_b[key]],
                "single_years": {"lowest": r3(min(yv)), "highest": r3(max(yv)),
                                 "lowest_year": int(min(per_year, key=lambda y: per_year[y][key])),
                                 "highest_year": int(max(per_year, key=lambda y: per_year[y][key]))},
                "pure_cropland_pixels_only": r3(pure_n[str(ndvi_max)][key])}

    numbers = {"median_bare_days": entry("median_bare_days", m["median_bare_days"], "days a year"),
               "share_long_bare": entry("share_long_bare", m["share_long_bare"], f"share of cropland bare more than {A['long_bare_days']} days a year"),
               "share_two_seasons": entry("share_two_seasons", m["share_two_seasons"], "share of cropland with two crop seasons a year")}
    bcls = st.bare_class(MB[ndvi_max], A["classes"]["bare_days_breaks"])
    shares_bare = {str(k): r3((bcls[crop] == k).mean()) for k in range(-1, len(A["classes"]["bare_days_breaks"]) + 1)}
    shares_seas = {str(k): r3((SC[crop] == k).mean()) for k in range(-1, 4)}

    # VALIDATION 3.23: the field check
    demo_mask = fields[field["id"]][1]
    dj = json.loads((out_checks / "diary_bare_days.json").read_text())
    sj = json.loads((out_checks / "diary_seasons.json").read_text())
    g = pd.read_parquet(data / "clean" / field["id"] / "greenness_field.parquet")
    hls = g[g["source"].str.startswith("hls")].dropna(subset=["ndvi"])
    first_hls = max(hls["date"].min(), pd.Timestamp(start))
    obs = hls[hls["date"] >= first_hls]
    u, mm = px.same_day_mean(obs["date"], obs["ndvi"].to_numpy()[:, None])
    daily = px.daily_matrix(u, mm, str(first_hls.date()), END)
    days = pd.date_range(first_hls, END)
    b, h = px.yearly_counts(daily, days, years, ndvi_max)
    a_bare = all(int(b[i, 0]) == dj["by_year"][str(y)]["bare_days"] and int(h[i, 0]) == dj["by_year"][str(y)]["days_with_value"]
                 for i, y in enumerate(years))
    from pipeline.diary import seasons as se
    sm_ = se.smooth(daily[:, 0][np.isfinite(daily[:, 0])], S["smooth_window_days"], S["smooth_polyorder"])
    dd = days[np.isfinite(daily[:, 0])]
    th = se.threshold_seasons(dd, sm_, S["min_amplitude"], S["threshold_fraction"], S["min_amplitude_range_fraction"], S["min_amplitude_range_years"])
    mine = sorted((str(s["start"].date()), str(s["peak"].date()), str(s["end"].date())) for s in th)
    theirs = sorted((r["start"], r["peak"], r["end"]) for rows in sj["chosen"]["seasons_by_year"].values() for r in rows if r["source"] == "hls")
    a_seas = mine == theirs
    diary_bare = dj["summary"]["mean_bare_days_hls_years"]
    diary_seas = [sum(1 for r in sj["chosen"]["seasons_by_year"].get(str(y), []) if r["source"] == "hls") for y in years]
    diary_cls = int(st.season_class(np.array([np.mean(diary_seas)]))[0])
    pix_bare = MB[ndvi_max][demo_mask]
    pix_cls = SC[demo_mask]
    b_ok = bool(np.nanmin(pix_bare) <= diary_bare <= np.nanmax(pix_bare))
    c_ok = bool((pix_cls == diary_cls).all())
    field_check = {"a_code_path": {"bare_days_by_year_identical": a_bare, "seasons_identical": a_seas,
                                   "seasons_compared": len(theirs), "first_hls_obs": str(first_hls.date())},
                   "b_bare_days": {"diary_mean_bare_days_hls_years": diary_bare,
                                   "field_pixels_mean_bare_days": [r3(v) for v in pix_bare], "pass": b_ok},
                   "c_seasons": {"diary_seasons_by_year": diary_seas, "diary_class": diary_cls,
                                 "field_pixels_mean_seasons": [r3(v) for v in MS[demo_mask]],
                                 "field_pixels_class": pix_cls.tolist(), "pass": c_ok},
                   "pass": bool(a_bare and a_seas and b_ok and c_ok)}
    print(f"field check: {json.dumps(field_check)}", flush=True)

    # every prepared field in the box, the diary's way and on the map
    col_of = {int(i): k for k, i in enumerate(flat_use)}
    summaries = {}
    for fid, (f, mask) in fields.items():
        cols = [col_of[int(i)] for i in np.nonzero(mask.ravel())[0]]
        w = field_way(dates, raw[:, cols], fill, scale, rules["greenness"]["min_clear_fraction"], start, years, ndvi_max, S)
        summaries[fid] = {"name": f["name"], "lat": f["lat"], "lon": f["lon"], "hls_pixels": len(cols),
                          "pixels_cropland": int(crop[mask].sum()), "diary_way": summarise_way(w, A),
                          "diary_way_bare_by_year": w["bare_by_year"], "diary_way_seasons_by_year": w["seasons_by_year"],
                          "map_pixels": {"mean_bare_days": [r3(v) for v in MB[ndvi_max][mask]],
                                         "mean_seasons_a_year": [r3(v) for v in MS[mask]], "seasons_class": SC[mask].tolist()}}
        print(f"{fid}: {summaries[fid]['diary_way']} map pixels {summaries[fid]['map_pixels']}", flush=True)
    if field["id"] in summaries:
        field_check["a_code_path"]["raw_stack_way_equals_diary"] = (
            summaries[field["id"]]["diary_way_bare_by_year"] == {str(y): dj["by_year"][str(y)]["bare_days"] for y in years})

    # PNG layers
    K = A["classes"]
    t3857, w3857, h3857 = rd.mercator_grid(field["fetch_box"], A["render"]["ground_pixel_m"])
    lay_b = np.where(crop, np.where(bcls >= 0, bcls, -1), -2)
    lay_s = np.where(crop, np.where(SC >= 0, SC, -1), -2)
    pngs = {}
    for name, lay, cols in (("bare_days", lay_b, K["bare_days_colours"]), ("seasons", lay_s, K["seasons_colours"])):
        wl = rd.warp_classes(lay, ht, hcrs, t3857, (h3857, w3857))
        path = rd.write_png(wl, cols, K["no_data_colour"], site_dir / f"{field['id']}_{name}.png")
        pngs[name] = {"file": path.name, "bytes": path.stat().st_size, "width": w3857, "height": h3857}
        if path.stat().st_size >= 100_000:
            raise ValueError(f"{path.name} is {path.stat().st_size} bytes: over the 100 KB limit")
    print(f"PNGs: {pngs}", flush=True)

    box = field["fetch_box"]
    out = {"labels": {"what": "every WorldCover 2021 cropland pixel of the demo fetch box (30 m HLS grid), by the field diary's own methods",
                      "rules": "config/rules.yaml area_map (committed before the first run, cb85cc8)",
                      "placeholder": "a map of the area around a PLACEHOLDER demo field; no pixel is a known farmer's field",
                      "what_ndvi_shows": "green cover from space, not which crop"},
           "grid": {"crs": str(hcrs), "shape": list(shape), "transform": list(tuple(ht)[:6]),
                    "worldcover_centres_expected_per_pixel": round(exp, 2)},
           "cropland": {"pixels": int(crop.sum()), "area_ha": round(float(crop.sum() * 0.09), 1), "pure_pixels": int(pure.sum()),
                        "box_pixels": int(in_box.sum()), "share_of_box": r3(crop.sum() / in_box.sum())},
           "hls": {"granules": n_files, "used_from": start, "years": years, "thresholds": thresholds},
           "numbers": numbers, "class_shares_bare_days": shares_bare, "class_shares_seasons": shares_seas,
           "class_keys": {"bare_days": "-1 not enough clear pictures; 0 under 30; 1 30-60; 2 60-90; 3 90-120; 4 120 or more days a year",
                          "seasons": "-1 not enough clear pictures; 0, 1, 2, 3 = 3 or more crop seasons a year"},
           "single_years": per_year, "worldcover_commission_used": c, "all_numbers_by_threshold": main_n,
           "pure_numbers_by_threshold": pure_n, "field_check": field_check, "fields": summaries, "pngs": pngs,
           "runtime_s": round(time.time() - t0)}
    (out_checks / "area_map.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"-> {(out_checks / 'area_map.json').relative_to(REPO)}  ({time.time() - t0:.0f} s)")
    print(json.dumps(numbers, indent=1))
    print("bare classes", shares_bare, "season classes", shares_seas)
    site_json(field, A, out, site_dir)
    return 0 if field_check["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
