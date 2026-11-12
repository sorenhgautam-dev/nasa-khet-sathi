"""Candidate placeholder fields (owner, 2026-11-12): 60 m squares of WorldCover 2021 cropland with a 30 m
cropland margin and no built-up pixel within 100 m, whose HLS greenness shows a monsoon crop and a winter
crop in each recent year. The owner checks the candidates on satellite imagery and picks one.

    .venv/bin/python -m pipeline.fetch.placeholder --field demo

Crop-season test: in each test year, the highest monthly median NDVI in July-October (monsoon) and in
December (previous year) to March (winter) must both exceed the bare-soil line, NDVI 0.25 (CLAUDE.md
"Bare days": start at 0.25). A plot built over recently fails in the years after. That line alone does
not separate a fallow or cleared plot among fields (its 30 m pixels mix with the neighbours), so passing
squares are ranked by their weaker season's peak, and the winter rise (winter peak minus the
October-November low after the rice harvest) is reported for each. HLS here ends in December 2025.

REVIEW_NOTES M11: the soil-distance limit is rules.yaml soilgrids.nearest_cell_max_m; without the cached
SoilGrids maps the distance is "unknown" and not used to rank. The config's chosen field is checked
against the same built-up rule; if its margin is closer than the rule allows, its label says so and names
the owner's acceptance (OWNER_EXCEPTIONS) or says it is NOT accepted.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch.worldcover import CROPLAND, KM_PER_DEG, distance_km, square_polygon

REPO = Path(__file__).resolve().parents[2]
BUILT = 50
CLEAR_OF_BUILT_M = 100          # the search's rule: no built-up pixel within 100 m of the 30 m margin
MARGIN_M = 30
# Squares the owner accepted although they miss the built-up rule: (lat, lon) -> acceptance
OWNER_EXCEPTIONS = {(27.690767, 85.441792): "accepted by the owner, 2026-11-12"}   # REVIEW_NOTES, owner response


def _box_sum(ii, r0, r1, c0, c1):
    return ii[r1, c1] - ii[r0, c1] - ii[r1, c0] + ii[r0, c0]


def cropland_squares(classes, transform, lat, side_m=60, margin_m=30, clear_of_built_m=100):
    a = np.asarray(classes)
    lat_m = abs(transform.e) * KM_PER_DEG * 1000
    lon_m = abs(transform.a) * KM_PER_DEG * 1000 * math.cos(math.radians(lat))
    nr, nc = math.ceil((side_m + 2 * margin_m) / lat_m), math.ceil((side_m + 2 * margin_m) / lon_m)
    br, bc = math.ceil(clear_of_built_m / lat_m), math.ceil(clear_of_built_m / lon_m)
    ci = np.pad((a == CROPLAND).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    bi = np.pad((a == BUILT).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    out = []
    H, W = a.shape
    for r0 in range(br, H - nr - br + 1):
        for c0 in range(bc, W - nc - bc + 1):
            if _box_sum(ci, r0, r0 + nr, c0, c0 + nc) != nr * nc:
                continue
            if _box_sum(bi, r0 - br, r0 + nr + br, c0 - bc, c0 + nc + bc) != 0:
                continue
            lon = transform.c + transform.a * (c0 + nc / 2)
            la = transform.f + transform.e * (r0 + nr / 2)
            out.append({"lat": round(la, 6), "lon": round(lon, 6), "window_rows_cols": [r0, r0 + nr, c0, c0 + nc]})
    return out


def season_check(monthly, years, bare_ndvi):
    """monthly: Series of NDVI indexed 'YYYY-MM'. Both seasons must top `bare_ndvi` in every year."""
    peaks, failed, rise = [], [], []
    for y in years:
        mon = [monthly.get(f"{y}-{m:02d}", np.nan) for m in (7, 8, 9, 10)]
        win = [monthly.get(f"{y - 1}-12", np.nan)] + [monthly.get(f"{y}-{m:02d}", np.nan) for m in (1, 2, 3)]
        aut = [monthly.get(f"{y - 1}-{m:02d}", np.nan) for m in (10, 11)]        # after the rice harvest
        pm, pw = np.nanmax(mon) if np.isfinite(mon).any() else np.nan, np.nanmax(win) if np.isfinite(win).any() else np.nan
        trough = np.nanmin(aut) if np.isfinite(aut).any() else np.nan
        rise.append(None if not (np.isfinite(pw) and np.isfinite(trough)) else round(float(pw - trough), 3))
        peaks += [pm, pw]
        if not (pm > bare_ndvi and pw > bare_ndvi):
            failed.append(y)
    finite = [p for p in peaks if np.isfinite(p)]
    return {"passes": not failed, "failed_years": failed, "min_peak": float(min(finite)) if finite else float("nan"),
            "peaks": [None if not np.isfinite(p) else round(float(p), 3) for p in peaks], "winter_rise": rise}


def sample_monthly(comp, keys, transform, crs, lon, lat, half_m):
    """Mean monthly NDVI over the HLS pixels whose centres lie within the square."""
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:4326", crs, [lon], [lat])
    x, y = xs[0], ys[0]
    cols = np.arange(comp.shape[2]); rows = np.arange(comp.shape[1])
    cx = transform.c + transform.a * (cols + 0.5)
    cy = transform.f + transform.e * (rows + 0.5)
    cc = np.nonzero(np.abs(cx - x) <= half_m)[0]
    rr = np.nonzero(np.abs(cy - y) <= half_m)[0]
    if len(cc) == 0 or len(rr) == 0:
        raise ValueError("no HLS pixel centre inside the square")
    sub = comp[:, rr[0]:rr[-1] + 1, cc[0]:cc[-1] + 1]
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            vals = np.nanmean(sub.reshape(len(keys), -1), axis=1)
    return pd.Series(vals, index=keys), int(len(rr) * len(cc))


def soil_limit_m(rules):
    """REVIEW_NOTES M11: the limit is rules.yaml soilgrids.nearest_cell_max_m, never a number written here."""
    return rules["soilgrids"]["nearest_cell_max_m"]


def soil_rank(distance_m, limit_m):
    """0 = within the limit or unknown (an unknown distance is reported, never compared), 1 = beyond it."""
    return 0 if distance_m is None else int(distance_m > limit_m)


def rank(cands, limit_m):
    out = sorted(cands, key=lambda c: (soil_rank(c["soilgrids_nearest_m"], limit_m), -round(c["min_peak"], 2),
                                       c["distance_km"]))
    return [{**c, "soilgrids_nearest_m": "unknown" if c["soilgrids_nearest_m"] is None else c["soilgrids_nearest_m"]}
            for c in out]


def soil_distances(wcs_dir, cands):
    """Metres from each candidate to the nearest SoilGrids cell where every cached map (all properties and
    depths) has a prediction (soilgrids_wcs.prediction_mask); None for each if any map is missing."""
    import rasterio

    from pipeline.fetch.soilgrids import DEPTHS, PROPS
    from pipeline.fetch.soilgrids_wcs import prediction_mask
    files = {(p, d): Path(wcs_dir) / f"{p}_{d}_mean.tif" for p in PROPS for d in DEPTHS}
    if not cands or not all(f.exists() for f in files.values()):
        return [None] * len(cands)
    grids, nodatas = {}, {}
    for k, f in files.items():
        with rasterio.open(f) as s:
            grids[k], nodatas[k], t = s.read(1), s.nodata, s.transform
    r, c = np.nonzero(prediction_mask(grids, nodatas))
    if len(r) == 0:
        return [None] * len(cands)
    vlat, vlon = np.radians(t.f + t.e * (r + 0.5)), np.radians(t.c + t.a * (c + 0.5))
    out = []
    for k in cands:
        la, lo = math.radians(k["lat"]), math.radians(k["lon"])
        h = np.sin((vlat - la) / 2) ** 2 + math.cos(la) * np.cos(vlat) * np.sin((vlon - lo) / 2) ** 2
        out.append(int(round(float((2 * 6371008.8 * np.arcsin(np.sqrt(h))).min()))))
    return out


def distance_to_class_m(classes, transform, lat, lon, half_m, cls):
    """Metres from an axis-aligned square (half side `half_m`, centred on lat, lon) to the nearest edge of a
    pixel of class `cls` (local flat-earth metres; fine over a few hundred metres). None if no such pixel."""
    a = np.asarray(classes)
    r, c = np.nonzero(a == cls)
    if len(r) == 0:
        return None
    m_lat = KM_PER_DEG * 1000
    m_lon = m_lat * math.cos(math.radians(lat))
    dy = (transform.f + transform.e * (r + 0.5) - lat) * m_lat
    dx = (transform.c + transform.a * (c + 0.5) - lon) * m_lon
    ex = np.maximum(np.abs(dx) - half_m - abs(transform.a) * m_lon / 2, 0)
    ey = np.maximum(np.abs(dy) - half_m - abs(transform.e) * m_lat / 2, 0)
    return float(np.hypot(ex, ey).min())


def margin_exception_label(lat, lon, margin_to_built_m, rule_m=CLEAR_OF_BUILT_M):
    """None when the margin keeps the rule; otherwise the exception, with the owner's acceptance if recorded."""
    if margin_to_built_m is None or margin_to_built_m >= rule_m:
        return None
    ok = OWNER_EXCEPTIONS.get((round(lat, 6), round(lon, 6)))
    return (f"exception: margin {margin_to_built_m:.0f} m from built-up, below the {rule_m} m rule; "
            + (ok if ok else "NOT accepted: ask the owner"))


def reference_squares(field, classes=None, transform=None, rule_m=CLEAR_OF_BUILT_M, margin_m=MARGIN_M):
    """The field config's own square ('chosen') and the squares it replaced ('earlier', from
    `earlier_placeholders` in the config, each with `why_replaced`). REVIEW_NOTES H3: never label the
    config's current field as rejected. With the WorldCover classes, the chosen square's margin is checked
    against the built-up rule (M11) and any exception is written into its label."""
    lats = [p[1] for p in field["polygon"]]
    side = (max(lats) - min(lats)) * KM_PER_DEG * 1000
    chosen = {"role": "chosen", "lat": field["lat"], "lon": field["lon"], "side_m": side}
    if classes is None:
        chosen["label"] = "Chosen placeholder field (built-up margin not checked)"
    else:
        d = distance_to_class_m(classes, transform, field["lat"], field["lon"], side / 2 + margin_m, BUILT)
        chosen["margin_to_built_up_m"] = None if d is None else round(d, 1)
        exc = margin_exception_label(field["lat"], field["lon"], d, rule_m)
        chosen["label"] = "Chosen placeholder field" + (f" ({exc})" if exc else f" (margin clear of built-up by {rule_m} m or more)")
    out = [chosen]
    for e in field.get("earlier_placeholders") or []:
        out.append({"role": "earlier", "lat": e["lat"], "lon": e["lon"], "side_m": e["side_m"],
                    "label": f"Earlier placeholder ({e['why_replaced']})"})
    return out


def pick(cands, n, min_apart_km):
    chosen = []
    for c in cands:
        if all(distance_km(c["lat"], c["lon"], d["lat"], d["lon"]) >= min_apart_km for d in chosen):
            chosen.append(c)
        if len(chosen) == n:
            break
    return chosen


def plot(classes, wt, best, refs, origin, series, path, bare):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    cls = [10, 20, 30, 40, 50, 60, 80]
    cols = ["#006400", "#ffbb22", "#ffff4c", "#f096ff", "#fa0000", "#b4b4b4", "#0064c8"]   # WorldCover legend colours
    fig = plt.figure(figsize=(13, max(10, 1.7 * len(series))))
    gs = fig.add_gridspec(len(series), 2, width_ratios=[1, 1.35])
    ax = fig.add_subplot(gs[:, 0])
    ext = [wt.c, wt.c + wt.a * classes.shape[1], wt.f + wt.e * classes.shape[0], wt.f]
    ax.imshow(classes, extent=ext, cmap=ListedColormap(cols), norm=BoundaryNorm([c - 0.5 for c in cls] + [80.5], 7),
              interpolation="nearest")
    for i, c in enumerate(best, 1):
        ax.plot(c["lon"], c["lat"], "s", mfc="none", mec="#0b0b0b", ms=12, mew=2)
        ax.annotate(str(i), (c["lon"], c["lat"]), xytext=(8, 6), textcoords="offset points", fontsize=12, weight="bold")
    for r in refs:
        chosen = r["role"] == "chosen"
        ax.plot(r["lon"], r["lat"], "*" if chosen else "x", color="#0b0b0b", ms=13 if chosen else 11, mew=2.5)
        ax.annotate("field" if chosen else "earlier", (r["lon"], r["lat"]), xytext=(8, -12), textcoords="offset points",
                    fontsize=9, weight="bold" if chosen else "normal")
    ax.plot(origin["lon"], origin["lat"], "+", color="#0b0b0b", ms=12, mew=2)
    ax.set_title("WorldCover 2021: candidates 1-3, chosen field (*), earlier placeholders (x), old point (+)",
                 loc="left", fontsize=10)
    ax.ticklabel_format(useOffset=False, style="plain"); ax.tick_params(labelsize=7)
    for k, (name, s) in enumerate(series):
        a = fig.add_subplot(gs[k, 1])
        s = s[[m >= "2019-01" for m in s.index]]
        x = pd.to_datetime(s.index + "-15")
        a.plot(x, s.to_numpy(), "-o", color="#2a78d6", ms=3, lw=1.2)
        a.axhline(bare, color="#898781", ls="--", lw=1)
        a.set_ylim(0, 1); a.set_ylabel("NDVI", fontsize=8); a.tick_params(labelsize=7)
        a.set_title(name, loc="left", fontsize=9)
    fig.axes[-1].set_xlabel("HLS monthly median NDVI, clear sky (dashed: bare-soil line 0.25)", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=105); plt.close(fig)


def _worldcover(data, field_id):
    import rasterio
    wc = sorted((Path(data) / "raw" / "worldcover" / field_id).glob("worldcover_2021_*_box.tif"))[0]
    with rasterio.open(wc) as src:
        return src.read(1), src.transform


def relabel(field, data=REPO / "data"):
    """Rewrite only the chosen field's label and built-up margin in placeholder_candidates.json (WorldCover only):
    no NDVI recomputation, and the candidate list the owner chose from keeps its order and numbers."""
    path = Path(data) / "clean" / field["id"] / "placeholder_candidates.json"
    out = json.loads(path.read_text())
    classes, wt = _worldcover(data, field["id"])
    chosen = reference_squares(field, classes, wt)[0]
    if (round(out["chosen_field"]["lat"], 6), round(out["chosen_field"]["lon"], 6)) != (round(chosen["lat"], 6), round(chosen["lon"], 6)):
        raise ValueError("placeholder_candidates.json was built for another chosen field; rerun the full search")
    out["chosen_field"].update(label=chosen["label"], margin_to_built_up_m=chosen["margin_to_built_up_m"])
    path.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--relabel", action="store_true",
                    help="only rewrite the chosen field's label and built-up margin in placeholder_candidates.json")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    data = REPO / "data"
    if a.relabel:
        print(json.dumps(relabel(field, data)["chosen_field"], indent=1))
        return 0
    from pipeline.diary.ndvi import monthly_composites
    origin = field["origin_point"]
    classes, wt = _worldcover(data, field["id"])
    comp, counts, keys, ht, hcrs = monthly_composites([data / "raw" / "hls_l30" / field["id"], data / "raw" / "hls_s30" / field["id"]])
    np.savez_compressed(data / "clean" / field["id"] / "hls_monthly_ndvi.npz", ndvi=comp.astype("float32"),
                        clear_obs=counts.astype("int16"), months=np.array(keys), transform=np.array(tuple(ht)[:6]),
                        crs=np.array(str(hcrs)))
    from pipeline.fetch.rules import load_rules
    limit = soil_limit_m(load_rules())                                # rules.yaml soilgrids.nearest_cell_max_m
    years, bare = [2023, 2024, 2025], 0.25
    cands = cropland_squares(classes, wt, origin["lat"], side_m=60, margin_m=MARGIN_M, clear_of_built_m=CLEAR_OF_BUILT_M)
    print(f"{len(cands)} cropland squares clear of buildings; {len(keys)} HLS months {keys[0]} to {keys[-1]}", flush=True)
    scored = []
    for c in cands[::3]:                                   # every third: neighbours overlap almost entirely
        s, npx = sample_monthly(comp, keys, ht, hcrs, c["lon"], c["lat"], 30)
        r = season_check(s, years, bare)
        if r["passes"]:
            scored.append({**c, **r, "hls_pixels": npx, "distance_km": round(distance_km(origin["lat"], origin["lon"], c["lat"], c["lon"]), 3)})
    soil_m = soil_distances(data / "raw" / "soilgrids" / field["id"] / "wcs", scored)
    for c, d in zip(scored, soil_m):
        c["soilgrids_nearest_m"] = d
    scored = rank(scored, limit)                       # an unknown soil distance is reported, never compared
    best = pick(scored, 3, 0.5)
    refs = reference_squares(field, classes, wt)       # the config's field (with any margin exception), then earlier ones
    ref_series = []
    for r in refs:
        s, npx = sample_monthly(comp, keys, ht, hcrs, r["lon"], r["lat"], r["side_m"] / 2)
        r.update(season_check(s, years, bare), side_m=round(r["side_m"], 1), hls_pixels=npx)
        ref_series.append(s)
    out = {"rule": {"side_m": 60, "margin_m": MARGIN_M, "clear_of_built_m": CLEAR_OF_BUILT_M, "years": years,
                    "bare_ndvi": bare, "soilgrids_nearest_cell_max_m": limit},
           "passing": len(scored), "candidates": [{**c, "polygon": square_polygon(c["lat"], c["lon"], 60)} for c in best],
           "chosen_field": refs[0], "earlier_placeholders": refs[1:]}
    (data / "clean" / field["id"] / "placeholder_candidates.json").write_text(json.dumps(out, indent=1) + "\n")
    series = [(f"Candidate {i}: {c['lat']:.5f} N, {c['lon']:.5f} E", sample_monthly(comp, keys, ht, hcrs, c["lon"], c["lat"], 30)[0])
              for i, c in enumerate(best, 1)] + [(f"{r['label']}: {r['lat']:.6f} N, {r['lon']:.6f} E", s)
                                                 for r, s in zip(refs, ref_series)]
    plot(classes, wt, best, refs, origin, series, data / "plots" / field["id"] / "placeholder_candidates.png", bare)
    print(json.dumps({"passing": len(scored), "candidates": [{k: c[k] for k in ("lat", "lon", "min_peak", "winter_rise", "distance_km", "soilgrids_nearest_m", "peaks")} for c in best],
                      "chosen_field": refs[0], "earlier_placeholders": refs[1:]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
