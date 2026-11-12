"""Build step 6a: the field diary's first parts, from the cleaned data. Writes data/checks/<field>/diary_*.json.

    .venv/bin/python scripts/run_diary.py --field demo            # onset, greenness series, bare days

Rules in config/rules.yaml (monsoon_onset; gpm_series for the trend caveat). Pure functions live in
pipeline/diary/; this script only reads files and writes the results.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.diary import greenness as gr  # noqa: E402
from pipeline.diary import ndvi  # noqa: E402
from pipeline.diary import onset as on  # noqa: E402
from pipeline.fetch import guards as g  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402


def _doy_to_date(doy):
    """Day of year as a plain date in a non-leap year, e.g. 161 -> '10 Jun'."""
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(round(doy) - 1, unit="D")).strftime("%d %b").lstrip("0")


def run_onset(field, rules, out_dir):
    w = pd.read_parquet(REPO / "data" / "clean" / field["id"] / "weather.parquet")
    if (w["rain_source"] != "gpm").any():
        raise ValueError("onset needs the twin's GPM rain on every day (D6); the weather table has other sources")
    rain = w.set_index("date")["rain_mm"]
    res = on.onsets(rain, rules["monsoon_onset"])
    doys = [d for d in res["day_of_year"].values() if d is not None]
    summary = {"years": len(res["day_of_year"]), "years_without_onset": [y for y, d in res["day_of_year"].items() if d is None],
               "median_day_of_year": statistics.median(doys) if doys else None,
               "median_date": _doy_to_date(statistics.median(doys)) if doys else None,
               "earliest": min(res["by_dry_spell_days"][str(rules["monsoon_onset"]["dry_spell_days"])].values(), default=None, key=lambda d: d[5:] if d else "99"),
               "latest": max((d for d in res["by_dry_spell_days"][str(rules["monsoon_onset"]["dry_spell_days"])].values() if d), default=None, key=lambda d: d[5:])}
    robust = {}
    for spell, by_year in res["by_dry_spell_days"].items():
        diffs = [(pd.Timestamp(by_year[y]) - pd.Timestamp(res["by_dry_spell_days"]["10"][y])).days
                 for y in by_year if by_year[y] and res["by_dry_spell_days"]["10"][y]]
        robust[spell] = {"years_same_as_10_day_rule": sum(1 for d in diffs if d == 0), "years_earlier": sum(1 for d in diffs if d < 0),
                         "median_shift_days": statistics.median(diffs) if diffs else None}
    out = {"labels": {"field": field["name"], "rain": "GPM IMERG V07 (Final to 2025-09-30, Late after), 0.1 deg cell holding the field, UTC days",
                      "rule": "rules.yaml monsoon_onset (CLAUDE.md 'Field diary'; Claude's readings marked TODO-CONFIRM there)",
                      "climatology_check": rules["monsoon_onset"]["climatology_check"]["value"] if isinstance(rules["monsoon_onset"]["climatology_check"], dict) else rules["monsoon_onset"]["climatology_check"],
                      "gpm_break_caveat": rules["gpm_series"]["trend_caveat"],
                      "trend": "not computed in step 6a (trends are step 6c, and carry the caveat above)"},
           **res, "summary": summary, "robustness": robust}
    path = out_dir / "diary_onset.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"onset, rule with {rules['monsoon_onset']['dry_spell_days']}-day dry spells:")
    for y, d in res["by_dry_spell_days"][str(rules["monsoon_onset"]["dry_spell_days"])].items():
        alt = [res["by_dry_spell_days"][s][y] for s in res["by_dry_spell_days"] if s != "10"]
        print(f"  {y}: {d or 'none'}   (15-day: {alt[0] or 'none'}, 20-day: {alt[1] or 'none'})")
    print(f"median onset {summary['median_date']} (day {summary['median_day_of_year']}); "
          f"check: {out['labels']['climatology_check']}; no onset in {summary['years_without_onset'] or 'no year'}")
    for spell, r in robust.items():
        print(f"  {spell}-day dry spells vs 10: same {r['years_same_as_10_day_rule']} years, earlier {r['years_earlier']}, "
              f"median shift {r['median_shift_days']} days")
    print(f"caveat: {rules['gpm_series']['trend_caveat']}\n-> {path.relative_to(REPO)}")
    return out


def hls_observations(field, rules, data):
    """One row per cached HLS granule window: date, sensor, field NDVI (or None), clear fraction."""
    import rasterio
    rows, mask, grid = [], None, None
    for s in ("hls_l30", "hls_s30"):
        for f in sorted((data / "raw" / s / field["id"]).glob("[!.]*.tif")):
            with rasterio.open(f) as src:
                if mask is None:
                    grid = (src.shape, src.transform)
                    mask = gr.field_mask(src.shape, src.transform, src.crs, field["polygon"])
                if (src.shape, src.transform) != grid:
                    raise ValueError(f"{f.name}: window grid differs from the first granule's")
                meta = json.loads(src.tags()["assets"])[".NDVI.tif"]
                nd = ndvi.scale_ndvi(src.read(1), float(meta["nodata"]), float(meta["scale"]))
                obs = gr.field_observation(nd, ndvi.clear_mask(src.read(2)), mask, rules["greenness"]["min_clear_fraction"])
                rows.append({"date": pd.Timestamp(src.tags()["acquired"]).normalize(), "source": s, **obs})
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True), int(mask.sum())


def modis_observations(field, rules, data):
    """One row per MOD13Q1 composite at the pixel holding the field centre: actual pixel date, NDVI, reliability."""
    import h5py
    with h5py.File(data / "raw" / "appeears" / field["id"] / "modis" / "MOD13Q1.061_250m_aid0001.nc", "r") as f:
        v = f["_250m_16_days_NDVI"]
        print("MOD13Q1 NDVI raw attributes:", g.describe_raw_attrs({k: v.attrs[k] for k in v.attrs
              if k in ("scale_factor", "add_offset", "_FillValue", "valid_min", "valid_max", "units")}))
        r, c = gr.modis_pixel(field["lat"], field["lon"], f["ydim"][:], f["xdim"][:])
        raw = v[:, r, c].astype(float)
        rel = f["_250m_16_days_pixel_reliability"][:, r, c]
        doy = f["_250m_16_days_composite_day_of_the_year"][:, r, c]
        t0 = pd.to_datetime(f["time"][:], unit="s", origin="2000-01-01")
        scale, fill = float(v.attrs["scale_factor"][0]), float(v.attrs["_FillValue"][0])
        lo, hi = float(v.attrs["valid_min"][0]), float(v.attrs["valid_max"][0])
    keep = (raw != fill) & (raw >= lo) & (raw <= hi) & pd.Series(rel).isin(rules["greenness"]["modis_reliability_ok"]).to_numpy() & (doy > 0)
    nd = raw * scale
    g.assert_in_range(nd[keep], "ndvi", "modis_ndvi")
    dates = []
    for start, d in zip(t0, doy):           # the pixel's own day; a composite may cross 1 January
        y = start.year + (1 if d > 0 and d < start.dayofyear - 20 else 0)
        dates.append(pd.Timestamp(f"{y}-01-01") + pd.Timedelta(int(d) - 1, unit="D") if d > 0 else pd.NaT)
    df = pd.DataFrame({"date": dates, "source": "modis", "ndvi": np.where(keep, nd, np.nan), "reliability": rel})
    return df, {"row": r, "col": c, "composites": int(len(df)), "kept": int(keep.sum())}


def run_greenness(field, rules, out_dir, data):
    hls, n_px = hls_observations(field, rules, data)
    mod, mod_px = modis_observations(field, rules, data)
    clean = data / "clean" / field["id"]
    both = pd.concat([hls.assign(reliability=np.nan), mod.assign(clear_fraction=np.nan, n_pixels=np.nan)], ignore_index=True)
    both = both.sort_values(["date", "source"]).reset_index(drop=True)
    both.to_parquet(clean / "greenness_field.parquet", index=False)
    hls_ok = hls.dropna(subset=["ndvi"])
    first_hls = max(hls_ok["date"].min(), pd.Timestamp(rules["greenness"]["hls_from"]))
    use = pd.concat([mod[mod["date"] < first_hls].dropna(subset=["ndvi"])[["date", "ndvi"]],
                     hls_ok[hls_ok["date"] >= first_hls][["date", "ndvi"]]])
    daily = gr.daily_series(use, "2001-01-01", "2025-12-31")
    bare = gr.bare_days(daily, rules["bare_days"]["ndvi_max"], rules["bare_days"]["uncertain_gap_days"])
    pairs = gr.pair_observations(hls_ok[["date", "ndvi"]], mod.dropna(subset=["ndvi"])[["date", "ndvi"]],
                                 rules["greenness"]["pair_max_days"])
    diff = pairs["ndvi_b"] - pairs["ndvi_a"]
    comp = {"pairs": int(len(pairs)), "modis_minus_hls_mean": round(float(diff.mean()), 3) if len(pairs) else None,
            "r": round(float(pairs["ndvi_a"].corr(pairs["ndvi_b"])), 3) if len(pairs) > 2 else None,
            "note": "MODIS pixel about 230 m, mixing the 60 m field with its surroundings; HLS = the field's own 30 m pixels"}
    yrs = bare["by_year"]
    def mean_bare(years):
        v = [yrs[str(y)]["bare_days"] for y in years if str(y) in yrs and yrs[str(y)]["days_with_value"] >= 300]
        return round(sum(v) / len(v), 1) if v else None
    out = {"labels": {"field": field["name"], "series": f"MODIS MOD13Q1 v061 (pixel holding the field centre, reliability "
                      f"{rules['greenness']['modis_reliability_ok']}) before {first_hls.date()}, HLS v2.0 L30+S30 ({n_px} field pixels, "
                      f">= {rules['greenness']['min_clear_fraction']:.0%} clear) from then",
                      "bare_rule": f"interpolated NDVI below {rules['bare_days']['ndvi_max']} (CLAUDE.md, not yet tuned); uncertain when clear "
                                   f"observations are more than {rules['bare_days']['uncertain_gap_days']} days apart"},
           "observations": {"hls_images": int(len(hls)), "hls_clear": int(len(hls_ok)), "modis": mod_px},
           "summary": {"mean_bare_days_modis_years": mean_bare(range(2001, first_hls.year)),
                       "mean_bare_days_hls_years": mean_bare(range(first_hls.year + 1, 2026))},
           "modis_vs_hls": comp, **bare}
    path = out_dir / "diary_bare_days.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    card = g.make_card(dataset="greenness_field", product="Field NDVI series: HLS-VI v2.0 (L30, S30) and MOD13Q1 v061",
                       version="HLS 2.0; MOD13Q1 061", variable=["NDVI"], units_in="int16 scaled (HLS 0.0001; MODIS 0.0001)",
                       units_out="NDVI (unitless, -1 to 1)", scale_factor=0.0001,
                       fill_values_removed={"HLS -19999": "per pixel", "MODIS -3000": "per composite"},
                       quality_flags_used=f"HLS Fmask bits 0-5 zero, >= {rules['greenness']['min_clear_fraction']:.0%} of field pixels; "
                                          f"MODIS pixel reliability in {rules['greenness']['modis_reliability_ok']}",
                       records_dropped={"hls_images_not_clear_enough": int(len(hls) - len(hls_ok)),
                                        "modis_composites_dropped": mod_px["composites"] - mod_px["kept"]},
                       date_range=[str(both["date"].min().date()), str(both["date"].max().date())],
                       time_zone="UTC acquisition (HLS); MODIS: the pixel's composite day", pixel_count={"hls": n_px, "modis": 1},
                       source="NASA LP DAAC HLS-VI v2.0 and MOD13Q1 v061 (AppEEARS)", resolution="HLS 30 m; MODIS 250 m (231.7 m)",
                       raw_attrs={"modis_pixel": mod_px}, notes="Built by scripts/run_diary.py (step 6a)" +
                       (" for a PLACEHOLDER field." if field.get("placeholder") else "."))
    g.write_card(card, data / "cards" / field["id"])
    print(f"greenness: HLS {len(hls_ok)} clear of {len(hls)} images ({n_px} field pixels); MODIS {mod_px['kept']} of "
          f"{mod_px['composites']} composites kept (pixel row {mod_px['row']}, col {mod_px['col']}); HLS used from {first_hls.date()}")
    print(f"bare days a year (>= 300 days with a value): MODIS years {out['summary']['mean_bare_days_modis_years']}, "
          f"HLS years {out['summary']['mean_bare_days_hls_years']}")
    for y in range(2001, 2026):
        b = yrs.get(str(y))
        if b:
            print(f"  {y}: bare {b['bare_days']:3d}, days with value {b['days_with_value']:3d}, uncertain {b['uncertain_days']:3d}")
    print(f"MODIS vs HLS: {comp}\n-> {path.relative_to(REPO)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    out_dir = REPO / "data" / "checks" / field["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    run_onset(field, rules, out_dir)
    run_greenness(field, rules, out_dir, REPO / "data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
