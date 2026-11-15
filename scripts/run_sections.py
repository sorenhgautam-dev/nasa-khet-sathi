"""Build step 8 (small version): the field in small parts. Writes data/checks/<field>/sections.json.

    .venv/bin/python scripts/run_sections.py --field demo

Rules: config/rules.yaml `sections` (committed before the first run), with greenness.min_clear_fraction and
season_detection's smoothing. Pure functions: pipeline/sections/ (grid, attributes, status). This script only reads
the cached files and writes the result:
- the sections: the field's polygon split by its own corners (about one 30 m HLS pixel each);
- greenness per section from the cached HLS-VI box windows (data/raw/hls_l30|hls_s30/<field>/*.tif), by area weights,
  in the diary's seasons (data/checks/<field>/diary_seasons.json), and the pre-declared 'usually greener' test;
- low ground from NASADEM (data/clean/<field>/nasadem_box.tif): TPI over 500 m, Weiss's valley class, null within the
  DEM's stated error;
- status and wetness from the twin's state (data/clean/<field>/twin_state.json) when it exists, else grey and null;
- what every section shares (the soil cell, the rain and weather cells, the one twin bucket) and draft 'unknown' lines.
Nothing here goes into the field file: the integrator merges it (contract additions proposed in the output).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.diary import ndvi as nd  # noqa: E402
from pipeline.diary.guess import slot_of  # noqa: E402
from pipeline.fetch import gpm  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.nasadem import pixel_metres  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.sections import attributes as at  # noqa: E402
from pipeline.sections import grid  # noqa: E402
from pipeline.sections import status as st  # noqa: E402

HLS_GUIDE = {
    "document": "Harmonized Landsat and Sentinel-2 (HLS) Product User Guide, product version 2.0 (Ju et al., last "
                "updated April 2026), read 2026-11-14",
    "landsat_l30": "Only L1TP images; Tier 2 images have 'geolocation error up to 30 m in the x or y direction' "
                   "(about 5% of L1TP; sec. 3.1). Collection 2 is 'produced from the refined ground control points "
                   "(GCP) with the Sentinel-2 Global Reference Image (GRI) as an absolute reference' (sec. 2). "
                   "Landsat is resampled to the MGRS grid by cubic convolution (sec. 4.3).",
    "sentinel_s30": "Sentinel-2 L1C: '12 m circular error at 90% probability (CE90)' before the GRI (August 2021), "
                    "'5.1 m (CE90)' after; S30 images observed before August 2021 'have poorer geolocation quality but "
                    "are acceptable for most applications because the geolocation error is less than half of a 30 m HLS "
                    "pixel' (sec. 3.1). Resampled to 30 m with an area-weighted average (sec. 4.3).",
    "cloud_mask": "QA is resampled from the inner 2 x 2 input pixels and 'the presence of any label there will turn on "
                  "the corresponding output QA bit' (sec. 4.3): clouds are masked generously, never thinned.",
    "what_it_means_for_a_30_m_section": "A 12 m shift (Sentinel-2 before August 2021, CE90) is 40% of a pixel's width, "
                                        "and a Tier-2 Landsat image can be a whole pixel off. On any one image up to "
                                        "about 40% of a section's value can come from the next pixel, on top of the "
                                        "mixing below. The sections are compared over many seasons: only a difference "
                                        "that keeps its sign says something about the part itself.",
}

NASADEM_GUIDE = ("NASADEM User Guide (Buckley et al., January 2020) sec. 4.2.2.1: SRTM's requirement was a '10-m "
                 "relative height error' (90%); a global assessment found 'average absolute and relative height errors "
                 "to be ~6.8 m and 7 m' (Rodriguez et al. 2005, 2006). Radar heights include roofs and trees near the field.")


def _hls_files(field, data):
    return [(s, f) for s in ("hls_l30", "hls_s30") for f in sorted((data / "raw" / s / field["id"]).glob("[!.]*.tif"))]


def hls_section_series(field, sections, rules, data):
    """Per HLS granule window: each section's area-weighted NDVI (None when under the clear rule). Returns the table,
    each section's pixel weights and the grid description."""
    import rasterio
    from rasterio.warp import transform as warp

    files = _hls_files(field, data)
    if not files:
        raise FileNotFoundError("no cached HLS windows for this field")
    with rasterio.open(files[0][1]) as src:
        crs, t, shape = src.crs, src.transform, src.shape
    weights = {}
    for s in sections:
        lons, lats = [p[0] for p in s["polygon"]], [p[1] for p in s["polygon"]]
        xs, ys = warp("EPSG:4326", crs, lons, lats)
        xs2, ys2 = warp("EPSG:4326", "EPSG:32645", lons, lats)
        if max(abs(a - b) for a, b in zip(xs + ys, xs2 + ys2)) > 0.01:
            raise ValueError("the HLS window's CRS is not UTM zone 45N to within 1 cm")
        weights[s["id"]] = at.pixel_weights(list(zip(xs, ys)), tuple(t)[:6], shape)
    rows = [w["row"] for ws in weights.values() for w in ws]
    cols = [w["col"] for ws in weights.values() for w in ws]
    r0, r1, c0, c1 = min(rows), max(rows), min(cols), max(cols)
    win = rasterio.windows.Window(c0, r0, c1 - c0 + 1, r1 - r0 + 1)
    min_clear = rules["greenness"]["min_clear_fraction"]
    out = []
    for sensor, f in files:
        with rasterio.open(f) as src:
            if (src.shape, src.transform) != (shape, t):
                raise ValueError(f"{f.name}: window grid differs from the first granule's")
            meta = json.loads(src.tags()["assets"])[".NDVI.tif"]
            v = nd.scale_ndvi(src.read(1, window=win), float(meta["nodata"]), float(meta["scale"]))
            clear = nd.clear_mask(src.read(2, window=win))
            row = {"date": pd.Timestamp(src.tags()["acquired"]).normalize(), "sensor": sensor}
        for sid, ws in weights.items():
            idx = [(w["row"] - r0, w["col"] - c0) for w in ws]
            obs = at.section_observation([v[i] for i in idx], [clear[i] for i in idx], [w["weight"] for w in ws], min_clear)
            row[sid], row[f"{sid}_clear"] = obs["ndvi"], obs["clear_share"]
        out.append(row)
    grid_info = {"crs": str(crs.to_string() if crs.to_epsg() else "UTM zone 45N (WGS 84 ellipsoid), as EPSG:32645"),
                 "transform": [round(x, 3) for x in tuple(t)[:6]], "shape": list(shape),
                 "note": "rows and cols of the cached HLS box window (data/raw/hls_l30|hls_s30/<field>/*.tif), 30 m pixels"}
    return pd.DataFrame(out).sort_values(["date", "sensor"]).reset_index(drop=True), weights, grid_info


def diary_seasons(field, data):
    d = json.loads((data / "checks" / field["id"] / "diary_seasons.json").read_text())
    rows = [r for rs in d["chosen"]["seasons_by_year"].values() for r in rs if r["source"] == "hls"]
    out = [{k: pd.Timestamp(r[k]) for k in ("start", "peak", "end")} for r in rows]
    for s in out:
        s["slot"] = slot_of(s)
    return sorted(out, key=lambda s: s["peak"]), d["chosen"]["method"]


def greenness(field, sections, rules, data):
    S, D = rules["sections"], rules["season_detection"]
    table, weights, grid_info = hls_section_series(field, sections, rules, data)
    ids = [s["id"] for s in sections]
    area = {s["id"]: s["area_m2"] for s in sections}
    common = table.dropna(subset=ids).copy()
    common["field"] = [at.weighted_mean([r[i] for i in ids], [area[i] for i in ids]) for _, r in common.iterrows()]
    seasons, method = diary_seasons(field, data)
    hls_from = pd.Timestamp(rules["greenness"]["hls_from"])
    common = common[common["date"] >= hls_from]
    peaks = {k: at.season_peaks(common["date"], common[k], seasons, D["smooth_window_days"], D["smooth_polyorder"],
                                S["min_obs_per_season"]) for k in ids + ["field"]}
    by_season, anomalies, slot_anoms = {i: [] for i in ids}, {i: [] for i in ids}, {}
    for j, s in enumerate(seasons):
        fp = peaks["field"][j]["peak"]
        for i in ids:
            sp = peaks[i][j]["peak"]
            a = sp - fp if sp is not None and fp is not None else None
            by_season[i].append({"year": int(s["peak"].year), "slot": s["slot"], "start": str(s["start"].date()),
                                 "peak_date": str(s["peak"].date()), "end": str(s["end"].date()), "obs": peaks[i][j]["obs"],
                                 "peak": None if sp is None else round(sp, 4), "field_peak": None if fp is None else round(fp, 4),
                                 "anomaly": None if a is None else round(a, 4)})
            if a is not None:
                anomalies[i].append(a)
                slot_anoms.setdefault(s["slot"], {k: [] for k in ids})[i].append(a)
    field_peaks = [p["peak"] for p in peaks["field"]]
    floor = at.size_floor(field_peaks, S["size_floor_relative"])          # owner, 2026-11-14 (Ju et al. 2025)
    test = at.usually(anomalies, S["alpha"], S["ci_level"], floor)
    by_slot = {slot: at.usually(v, S["alpha"], S["ci_level"], floor) for slot, v in slot_anoms.items()}

    # check: the field (all sections) against the diary's own field series (4 pixel centres inside, unweighted)
    diary = pd.read_parquet(data / "clean" / field["id"] / "greenness_field.parquet")
    diary = diary[diary["source"].str.startswith("hls")].dropna(subset=["ndvi"])
    m = common.merge(diary.rename(columns={"source": "sensor", "ndvi": "diary_ndvi"})[["date", "sensor", "diary_ndvi"]],
                     on=["date", "sensor"])
    diff = m["field"] - m["diary_ndvi"]
    check = {"images_matched": int(len(m)), "mean_difference": round(float(diff.mean()), 4) if len(m) else None,
             "mean_abs_difference": round(float(diff.abs().mean()), 4) if len(m) else None,
             "r": round(float(m["field"].corr(m["diary_ndvi"])), 4) if len(m) > 2 else None,
             "note": "field (all sections) = area-weighted mean of the sections on images where every section counts; "
                     "diary = mean of the HLS pixels whose centres lie inside the field, image kept when 75% of them are clear"}
    counts = {"granules": int(len(table)), "by_sensor": {k: int(v) for k, v in table["sensor"].value_counts().items()},
              "per_section_counted": {i: int(table[i].notna().sum()) for i in ids},
              "common_images": int(len(common)), "first": str(common["date"].min().date()), "last": str(common["date"].max().date())}
    series = {"date": [str(d.date()) for d in common["date"]], "sensor": list(common["sensor"]),
              "field": [round(float(x), 4) for x in common["field"]], **{i: [round(float(x), 4) for x in common[i]] for i in ids}}
    size = {"floor_ndvi": round(floor, 4) if floor is not None else None, "relative": S["size_floor_relative"],
            "field_median_season_peak": round(float(np.median([p for p in field_peaks if p is not None])), 4),
            "rule": "greener / less green need the sign test (Holm) AND |median anomaly| > floor; otherwise same "
                    "('about the same'); owner, 2026-11-14",
            "source": "Ju et al. 2025, RSE 324:114723, abstract: same-day Landsat/Sentinel-2 'between-sensor VI "
                      "difference is below 4.5% for most of the indices' (545 same-day pairs)"}
    return {"size_floor": size, "weights": weights, "grid": grid_info, "by_season": by_season, "test": test, "by_slot": by_slot,
            "check_vs_diary": check, "counts": counts, "series": series, "season_method": method, "seasons": len(seasons)}


def low_ground(field, sections, rules, data):
    import rasterio
    S = rules["sections"]
    with rasterio.open(data / "clean" / field["id"] / "nasadem_box.tif") as src:
        dem, slope, t = src.read(1).astype(float), src.read(2).astype(float), src.transform
        desc = src.descriptions
    if desc[:2] != ("elevation_m", "slope_deg"):
        raise ValueError(f"nasadem_box.tif bands are {desc}, expected elevation_m, slope_deg")
    dx, dy = pixel_metres(abs(t.e), field["lat"])
    out = {}
    for s in sections:
        ws = at.pixel_weights([tuple(p) for p in s["polygon"]], tuple(t)[:6], dem.shape)
        px = []
        for w in ws:
            r = at.tpi_at(dem, w["row"], w["col"], dx, dy, S["tpi_radius_m"])
            px.append({**w, "elevation_m": float(dem[w["row"], w["col"]]), "slope_deg": float(slope[w["row"], w["col"]]),
                       "tpi_m": r["tpi_m"], "sd_m": r["sd_m"], "n": r["n"]})
        wsum = lambda k: float(sum(p["weight"] * p[k] for p in px))  # noqa: E731
        tpi, sd = wsum("tpi_m"), wsum("sd_m")
        out[s["id"]] = {"low_ground": at.low_ground(tpi, sd, S["tpi_threshold_sd"], S["dem_relative_error_m"]),
                        "tpi_m": round(tpi, 2), "sd_m": round(sd, 2), "elevation_m": round(wsum("elevation_m"), 1),
                        "slope_deg": round(wsum("slope_deg"), 2), "tpi_in_sd": round(tpi / sd, 2) if sd > 0 else None,
                        "dem_pixels": [{"row": p["row"], "col": p["col"], "weight": round(p["weight"], 4),
                                        "elevation_m": p["elevation_m"], "tpi_m": round(p["tpi_m"], 2)} for p in px],
                        "circle_pixels": px[0]["n"]}
    return out, {"dx_m": round(dx, 2), "dy_m": round(dy, 2)}


def shared_block(field, rules, data, twin):
    cards = data / "cards" / field["id"]
    soil = json.loads((cards / "soilgrids.json").read_text())
    gpm_card = json.loads((cards / "gpm.json").read_text())
    power = json.loads((cards / "power.json").read_text())
    i, j = gpm.cell_index(field["lat"], field["lon"])
    lon0, lat0 = round(-180 + gpm.RES * i, 4), round(-90 + gpm.RES * j, 4)
    loc = gpm_card["location"]
    card_centre = [loc["box_cells_lon"][loc["field_cell"][0]], loc["box_cells_lat"][loc["field_cell"][1]]]
    centre = [round(lon0 + gpm.RES / 2, 4), round(lat0 + gpm.RES / 2, 4)]

    def merra_cell(lat, lon):
        clat, clon = round(lat / 0.5) * 0.5, -180 + round((lon + 180) / 0.625) * 0.625
        return [round(clon - 0.3125, 4), round(clat - 0.25, 4), round(clon + 0.3125, 4), round(clat + 0.25, 4)]

    pl = power["location"]
    return {
        "soil": {"what": "every section uses the one SoilGrids cell the twin uses", "used_lat_lon": soil["location"]["used"],
                 "distance_m": soil["location"]["distance_m"], "resolution": soil["resolution"],
                 "note": "the nearest SoilGrids 2.0 cell with a prediction, not the field's own (data/cards/<field>/soilgrids.json)"},
        "rain": {"what": "every section gets the twin's rain from one GPM IMERG cell", "cell_bounds_lon_lat": [lon0, lat0, round(lon0 + gpm.RES, 4), round(lat0 + gpm.RES, 4)],
                 "centre_matches_card": centre == card_centre, "resolution": "0.1 deg (about 10 km)"},
        "weather": {"what": "every section gets NASA POWER temperature, humidity, wind and sunshine from one cell (model-based)",
                    "cell_bounds_lon_lat": merra_cell(field["lat"], field["lon"]),
                    "requested_point": [pl["lon"], pl["lat"]],
                    "same_cell_as_requested_point": merra_cell(field["lat"], field["lon"]) == merra_cell(pl["lat"], pl["lon"]),
                    "resolution": "0.5 x 0.625 deg meteorology", "note": "cell bounds computed from the grid the POWER card names, not read from the API"},
        "twin": {"what": "one soil-water bucket for the whole field: every section shares its status and wetness",
                 "state": None if twin is None else {k: twin.get(k) for k in ("date", "as_of_label", "plan", "water_case", "crop",
                                                                             "sure_prior", "uncorrected_rain") if k in twin},
                 "file": f"data/clean/{field['id']}/twin_state.json", "found": twin is not None},
    }


UNKNOWN_LINES = {
    "shared": "All parts share one soil and weather.",
    "pixel": "Each part is one dot from space.",
    "mixing": "Those dots do not match the parts.",
    "trees": "Greener can mean weeds or trees too.",
    "low_cant_tell": "Height maps cannot find low spots here.",
    "probe": "The probe tells the parts apart.",
}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--twin-state", help="twin state file (default data/clean/<field>/twin_state.json)")
    ap.add_argument("--out", help="output file (default data/checks/<field>/sections.json)")
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    rules["sections"].update(field.get("sections") or {})    # sectioning is per field (owner, 2026-11-15): its config first
    S, data = rules["sections"], REPO / "data"
    pc = field.get("patches")       # a drawn field's patches (rules.yaml sections.patches), else the 30 m grid
    sections = [{"id": p["id"], "polygon": p["polygon"], "area_m2": p["area_m2"]} for p in grid.patches(
        field["polygon"], (field["lon"], field["lat"]), pc["cell_m"], pc["min_piece_m2"], pc["ids"])[0]] if pc else \
        grid.grid_sections(field["polygon"], cell_m=S["cell_m"], max_sections=S["max_sections"], coarsen_factor=S["coarsen_factor"])
    g = greenness(field, sections, rules, data)
    lg, dem_px = low_ground(field, sections, rules, data)
    tpath = Path(a.twin_state) if a.twin_state else data / "clean" / field["id"] / "twin_state.json"
    twin = json.loads(tpath.read_text()) if tpath.exists() else None
    stat = st.from_twin_state(twin, S["status_red_ks_below"])
    un = (twin or {}).get("uncorrected_rain")        # the same bucket on GPM rain as published (owner's decision 1: a range)
    stat_un = st.from_twin_state({"dr_mm": un.get("dr_mm"), "taw_mm": twin["taw_mm"], "raw_mm": twin["raw_mm"],
                                  "ks": un.get("ks"), "wetness_pct": un.get("wetness_pct")},
                                 S["status_red_ks_below"]) if un else None
    out_sections = []
    for s in sections:
        sid, ws = s["id"], g["weights"][s["id"]]
        t = g["test"][sid]
        if pc and s["area_m2"] < 900:    # rules.yaml sections.sub_pixel_patches: patches share their 30 m pixels
            t = dict(t, word="can't tell", why="smaller than one 30 m HLS pixel (rules.yaml sections.sub_pixel_patches)")
        out_sections.append({
            "id": sid, "polygon": s["polygon"], "area_m2": s["area_m2"],
            "hls_pixels": [{"row": w["row"], "col": w["col"], "weight": round(w["weight"], 4)} for w in ws],
            "main_pixel_share": round(ws[0]["weight"], 4),
            "greenness": {"usually": t["word"],
                          "test": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in t.items() if k != "word"} | {
                              "ci": None if t["ci"] is None else [round(x, 4) for x in t["ci"]]},
                          "by_slot": {slot: {"word": v[sid]["word"], "n": v[sid]["n"], "positive": v[sid]["positive"],
                                             "negative": v[sid]["negative"], "p": round(v[sid]["p"], 5),
                                             "median": None if v[sid]["median"] is None else round(v[sid]["median"], 4)}
                                      for slot, v in g["by_slot"].items()},
                          "by_season": g["by_season"][sid]},
            **lg[sid],
            "status": stat["status"],
            "wetness_pct": None if stat["wetness_pct"] is None else round(stat["wetness_pct"], 1),
            **({"status_uncorrected_rain": stat_un["status"],
                "wetness_pct_uncorrected_rain": None if stat_un["wetness_pct"] is None else round(stat_un["wetness_pct"], 1)}
               if stat_un else {})})
    all_low_null = all(x["low_ground"] is None for x in out_sections)
    shared_px = {}
    for s in out_sections:
        for p in s["hls_pixels"]:
            shared_px.setdefault((p["row"], p["col"]), set()).add(s["id"])
    unknown = [UNKNOWN_LINES[k] for k in ("shared", "pixel", "mixing", "trees")]
    if all_low_null:
        unknown.append(UNKNOWN_LINES["low_cant_tell"])
    unknown.append(UNKNOWN_LINES["probe"])
    doc = {
        "labels": {"field": field["name"], "placeholder": bool(field.get("placeholder")),
                   "rules": "rules.yaml sections (committed before the first run, in 5dce176; size floor, owner 2026-11-14, in e5b9aef)",
                   "what_it_is": "the field split into parts of about one 30 m satellite pixel; each part's own greenness "
                                 "history from HLS, a low-ground flag from NASADEM, and the twin's status (shared)",
                   "not_crop": "NDVI shows green cover, not which crop or how good: greener can be weeds, trees or a "
                               "neighbour's field in a mixed pixel"},
        "sections": out_sections,
        "field_summary": {"sections": len(sections), "hls_pixels_touching_field": len(shared_px),
                          "hls_pixels_shared_by_sections": sum(1 for v in shared_px.values() if len(v) > 1),
                          "main_pixel_share_min": min(s["main_pixel_share"] for s in out_sections),
                          "aligned_with_hls_grid": all(s["main_pixel_share"] > 0.99 for s in out_sections),
                          "usually_words": {s["id"]: s["greenness"]["usually"] for s in out_sections},
                          "low_ground": {s["id"]: s["low_ground"] for s in out_sections},
                          "status": stat["status"], "wetness_pct": out_sections[0]["wetness_pct"]},
        "greenness_method": {"seasons_from": f"diary_seasons.json, chosen method '{g['season_method']}', {g['seasons']} HLS seasons",
                             "size_floor": g["size_floor"],
                             "counts": g["counts"], "check_vs_diary_field_series": g["check_vs_diary"],
                             "min_decidable_seasons": at.min_decidable_n(S["alpha"], len(sections)),
                             "hls_grid": g["grid"], "hls_geolocation": HLS_GUIDE},
        "low_ground_method": {"tpi_radius_m": S["tpi_radius_m"], "threshold_sd": S["tpi_threshold_sd"],
                              "dem_relative_error_m": S["dem_relative_error_m"], "dem_pixel_m": dem_px,
                              "nasadem_accuracy": NASADEM_GUIDE},
        "shared": shared_block(field, rules, data, twin),
        "unknown_lines_en": unknown,
        "contract_proposal": {"per_section_add": {"greener": "one of 'greener', 'less green', 'same', 'can't tell' (sections.json greenness.usually; the site says 'a little greener', 'a little less green', 'about the same')",
                                                  "low_ground": "true, false or null (null = can't tell: within NASADEM's stated error)"},
                              "keep": "id, polygon, status, wetness, temp, sure as they are"},
        "image_series": g["series"],
    }
    path = Path(a.out) if a.out else data / "checks" / field["id"] / "sections.json"
    path.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(f"{len(sections)} sections; HLS pixels touching the field {len(shared_px)}, shared by sections "
          f"{doc['field_summary']['hls_pixels_shared_by_sections']}; main pixel share "
          + ", ".join(f"{s['id']} {s['main_pixel_share']:.2f}" for s in out_sections))
    print(f"images: {g['counts']}; check vs diary: {g['check_vs_diary']}")
    for s in out_sections:
        t = s["greenness"]["test"]
        print(f"  {s['id']}: usually {s['greenness']['usually']!r} (n {t['n']}, +{t['positive']} -{t['negative']}, p {t['p']}, "
              f"Holm {t['holm_rejected']}, median {t['median']}, CI {t['ci']}); by slot "
              + "; ".join(f"{k} {v['word']} ({v['positive']}+/{v['negative']}-)" for k, v in s["greenness"]["by_slot"].items())
              + f"; TPI {s['tpi_m']} m, SD {s['sd_m']} m, low ground {s['low_ground']}; status {s['status']}, wetness {s['wetness_pct']}")
    print(f"twin state: {'found (' + str(tpath) + ')' if twin else 'not found: status grey, wetness null'}"
          + (f"; uncorrected rain: {stat_un['status']}, wetness {stat_un['wetness_pct']}" if stat_un else "") + f"\n-> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
