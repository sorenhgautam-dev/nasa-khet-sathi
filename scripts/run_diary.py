"""Build steps 6a and 6b: the field diary from the cleaned data. Writes data/checks/<field>/diary_*.json.

    .venv/bin/python scripts/run_diary.py --field demo                  # onset, greenness, bare days, seasons
    .venv/bin/python scripts/run_diary.py --field demo --steps seasons  # seasons only (step 6b)

Rules in config/rules.yaml (monsoon_onset; gpm_series for the trend caveat). Pure functions live in
pipeline/diary/; this script only reads files and writes the results.
--rain uncorrected (owner's decision 1, 2026-11-13): reruns the rain-based steps (onset, diary) on GPM as published
into data/checks/<field>/rain_uncorrected/; greenness and seasons are read from the main run.
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
from pipeline.diary import seasons as se  # noqa: E402
from pipeline.diary import groundwater as gwm  # noqa: E402
from pipeline.diary import guess as gu  # noqa: E402
from pipeline.diary import months as mo  # noqa: E402
from pipeline.diary import trends as tr  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.fetch import guards as g  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.ml import seasons as det  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402

RAIN = {"version": "corrected"}   # set by main (--rain)


def _weather(field, data=REPO / "data"):
    return with_rain(pd.read_parquet(data / "clean" / field["id"] / "weather.parquet"), RAIN["version"])


def _doy_to_date(doy):
    """Day of year as a plain date in a non-leap year, e.g. 161 -> '10 Jun'."""
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(round(doy) - 1, unit="D")).strftime("%d %b").lstrip("0")


def run_onset(field, rules, out_dir):
    w = _weather(field)
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
    out = {"labels": {"field": field["name"], "rain": "GPM IMERG V07 (Final to 2025-09-30, Late after), 0.1 deg cell holding the field, UTC days; "
                      + ("as published (uncorrected run)" if RAIN["version"] == "uncorrected" else
                         "Final days from 2017 scaled back to GPM's own 2001-2016 level (owner's decision 1, 2026-11-13)"),
                      "rule": "rules.yaml monsoon_onset (CLAUDE.md 'Field diary'; Claude's readings owner-approved 2026-11-13)",
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


# ---------- step 6b: seasons, three methods ----------

def _rule_methods(obs, start, end, S, bare_max):
    """Threshold and change-point methods on one set of clear observations (pure functions in diary/seasons)."""
    daily = gr.daily_series(obs, start, end).dropna(subset=["ndvi"]).reset_index(drop=True)
    dates = pd.DatetimeIndex(daily["date"])
    sm = se.smooth(daily["ndvi"], S["smooth_window_days"], S["smooth_polyorder"])
    sigma = se.observation_sigma(daily, sm)
    amp = (S["min_amplitude"], S["min_amplitude_range_fraction"], S["min_amplitude_range_years"])
    th = se.threshold_seasons(dates, sm, amp[0], S["threshold_fraction"], amp[1], amp[2])
    kinks = se.changepoints(daily["ndvi"], sigma, S["changepoint_params_per_change"], S["changepoint_min_size_days"])
    fit = se.piecewise_linear_fit(daily["ndvi"], kinks)
    cp = se.changepoint_seasons(dates, fit, kinks, *amp)
    return {"dates": dates, "daily": daily, "smooth": sm, "sigma": sigma, "kinks": len(kinks),
            "threshold": {"seasons": th, "labels": se.labels_from_seasons(dates, th, sm, bare_max)},
            "changepoint": {"seasons": cp, "labels": se.labels_from_seasons(dates, cp, fit, bare_max)}}


def _detective_features(res, weather, D):
    w = weather.set_index("date").reindex(res["dates"])
    return det.features(res["dates"], res["smooth"], w["rain_mm"], (w["tmax_c"] + w["tmin_c"]) / 2,
                        D["slope_days"], D["low_window_days"], D["weather_days"])


def _detective(model, res, weather, D, bare_max):
    raw = det.predict(model, _detective_features(res, weather, D))
    edge = np.where(res["smooth"] < bare_max, "bare", "harvested")
    raw = np.where(pd.isna(raw), edge, raw)                      # window edges: curve only, never 'growing'
    seasons, lab = se.seasons_from_labels(res["dates"], se.mode_filter(raw, D["mode_filter_days"]), res["smooth"],
                                          bare_max, D["min_season_days"])
    return {"seasons": seasons, "labels": lab}


def _by_date(res, method):
    return pd.Series(res[method]["labels"], index=res["dates"])


def _season_rows(seasons, source):
    return [{"start": str(s["start"].date()), "peak": str(s["peak"].date()), "end": str(s["end"].date()),
             "days": int((s["end"] - s["start"]).days) + 1, "peak_ndvi": s["peak_ndvi"], "source": source}
            for s in seasons]


def _match_shift(a, b, max_days=45):
    """Median absolute start, peak and end differences (days) between seasons of two methods whose peaks are
    within max_days of each other."""
    d = {"start": [], "peak": [], "end": []}
    for s in a:
        near = [t for t in b if abs((t["peak"] - s["peak"]).days) <= max_days]
        if near:
            t = min(near, key=lambda t: abs((t["peak"] - s["peak"]).days))
            for k in d:
                d[k].append(abs((t[k] - s[k]).days))
    return {k: (float(np.median(v)) if v else None) for k, v in d.items()} | {"matched": len(d["peak"]), "of": len(a)}


def run_seasons(field, rules, out_dir, data):
    S, D = rules["season_detection"], rules["season_detection"]["detective"]
    bare_max = rules["bare_days"]["ndvi_max"]
    g_all = pd.read_parquet(data / "clean" / field["id"] / "greenness_field.parquet").dropna(subset=["ndvi"])
    weather = _weather(field, data)[["date", "rain_mm", "tmax_c", "tmin_c"]]
    hls = g_all[g_all["source"].str.startswith("hls")]
    first_hls = max(hls["date"].min(), pd.Timestamp(rules["greenness"]["hls_from"]))
    obs = hls[hls["date"] >= first_hls][["date", "ndvi"]].reset_index(drop=True)
    mod = g_all[(g_all["source"] == "modis") & (g_all["date"] < first_hls)][["date", "ndvi"]].reset_index(drop=True)
    start, end = str(first_hls.date()), "2025-12-31"

    full = _rule_methods(obs, start, end, S, bare_max)
    dates = full["dates"]
    th_full, cp_full = _by_date(full, "threshold"), _by_date(full, "changepoint")
    agree = (th_full == cp_full).to_numpy()
    ref = th_full.where(agree)
    X_full = _detective_features(full, weather, D)
    n_obs = obs.groupby(obs["date"].dt.year).size()
    dense = [int(y) for y, n in n_obs.items() if n >= S["held_out_min_clear_obs"] and y > first_hls.year
             and dates.min() <= pd.Timestamp(f"{y}-01-01") and dates.max() >= pd.Timestamp(f"{y}-12-30")]
    labels_full = full["threshold"]["labels"]

    per_year, train_sizes = {}, {}
    for Y in dense:
        train_mask = dates.year.isin([y for y in dense if y != Y]) & agree
        model = det.train(X_full[train_mask], labels_full[train_mask], D["trees"], D["min_samples_leaf"], D["seed"])
        train_sizes[str(Y)] = int(train_mask.sum())
        thin = _rule_methods(se.thin(obs, Y, S["held_out_thin_days"]), start, end, S, bare_max)
        det_thin = _detective(model, thin, weather, D, bare_max)
        det_dense = _detective(model, full, weather, D, bare_max)
        ref_y = ref[(ref.index.year == Y)].dropna()

        def score(series):
            return round(se.agreement(series.reindex(ref_y.index).to_numpy(), ref_y.to_numpy()), 4)

        per_year[str(Y)] = {
            "reference_days": int(len(ref_y)),
            "clear_obs_full": int(n_obs[Y]), "clear_obs_thinned": int((se.thin(obs, Y, S["held_out_thin_days"])["date"].dt.year == Y).sum()),
            "thinned": {"threshold": score(_by_date(thin, "threshold")), "changepoint": score(_by_date(thin, "changepoint")),
                        "detective": score(pd.Series(det_thin["labels"], index=thin["dates"]))},
            "detective_on_all_obs": score(pd.Series(det_dense["labels"], index=dates)),
            "threshold_vs_changepoint_all_obs": round(float(agree[dates.year == Y].mean()), 4)}
        print(f"  held out {Y}: {per_year[str(Y)]['thinned']} (reference {len(ref_y)} days; detective on all obs "
              f"{per_year[str(Y)]['detective_on_all_obs']})")
    methods = ("threshold", "changepoint", "detective")
    mean = {m: round(float(np.mean([per_year[y]["thinned"][m] for y in per_year])), 4) for m in methods}
    best = se.choose_best(mean, "threshold", S["best_margin"])

    final_model = det.train(X_full[dates.year.isin(dense) & agree], labels_full[dates.year.isin(dense) & agree],
                            D["trees"], D["min_samples_leaf"], D["seed"])
    det_full = _detective(final_model, full, weather, D, bare_max)
    full["detective"] = det_full
    modis = _rule_methods(mod, "2001-01-01", str((first_hls - pd.Timedelta(1, unit="D")).date()), S, bare_max)
    modis["detective"] = _detective(final_model, modis, weather, D, bare_max)

    def by_year(seasons_hls, seasons_mod):
        out = {}
        for rows in (_season_rows(seasons_mod, "modis"), _season_rows(seasons_hls, "hls")):
            for r in rows:
                out.setdefault(r["peak"][:4], []).append(r)
        return dict(sorted(out.items()))

    out = {
        "labels": {"field": field["name"], "rule": "rules.yaml season_detection (comparison design fixed before it was run)",
                   "day_labels": "growing = a crop season, green-up to end; harvested = between seasons, NDVI >= "
                                 f"{bare_max} (stubble, residue or weeds); bare = between seasons, NDVI < {bare_max}",
                   "what_it_shows": "green cover from space, not which crop; the farmer confirms the calendar",
                   "no_ground_truth": "there is no field-observed calendar (placeholder field). The reference is the days on "
                                      "which the threshold and change-point methods agree on all observations; each method is "
                                      "scored on reproducing it from a thinned year. This measures robustness to sparse data, "
                                      "not accuracy, and the two rule-based methods made the reference",
                   "modis_years": "MODIS 16-day greenest-day composites of a 230 m pixel: seasons before "
                                  f"{first_hls.date()} are not comparable with HLS years"},
        "series": {"hls_from": str(first_hls.date()), "hls_clear_obs": int(len(obs)), "sigma_ndvi": round(full["sigma"], 4),
                   "changepoint_kinks": full["kinks"], "modis_composites": int(len(mod))},
        "held_out": {"years": dense, "thin_days": S["held_out_thin_days"], "training_days": train_sizes,
                     "per_year": per_year, "mean_score": mean, "best": best, "best_margin": S["best_margin"],
                     "threshold_vs_changepoint_all_obs": round(float(agree[dates.year.isin(dense)].mean()), 4)},
        "season_date_differences_days": {
            "changepoint_vs_threshold": _match_shift(full["threshold"]["seasons"], full["changepoint"]["seasons"]),
            "detective_vs_threshold": _match_shift(full["threshold"]["seasons"], det_full["seasons"])},
        "seasons_by_method": {m: by_year(full[m]["seasons"], modis[m]["seasons"]) for m in methods},
        "chosen": {"method": best, "seasons_by_year": by_year(full[best]["seasons"], modis[best]["seasons"])},
    }
    path = out_dir / "diary_seasons.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    days = pd.concat([pd.DataFrame({"date": modis["dates"], "ndvi_smooth": modis["smooth"], "label": modis[best]["labels"],
                                    "source": "modis"}),
                      pd.DataFrame({"date": dates, "ndvi_smooth": full["smooth"], "label": full[best]["labels"],
                                    "source": "hls"})], ignore_index=True)
    days["label"] = days["label"].astype(str)
    days.to_parquet(data / "clean" / field["id"] / "seasons_daily.parquet", index=False)
    print(f"seasons: held-out years {dense}; mean score {mean}; chosen: {best}")
    print(f"threshold vs change-point agreement on all obs (held-out years): {out['held_out']['threshold_vs_changepoint_all_obs']}")
    print(f"date differences: {out['season_date_differences_days']}\n-> {path.relative_to(REPO)}")
    return out


# ---------- step 6c: groundwater, trends, monthly calendar, rotation guess ----------

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _grace(field, rules, data):
    """diary.groundwater from the cleaned monthly series (pipeline/fetch/grace.py: unscaled, owner M4)."""
    df = pd.read_parquet(data / "clean" / field["id"] / "grace.parquet")
    card = json.loads((data / "cards" / field["id"] / "grace.json").read_text())
    s = gwm.monthly_series(df["date"], df["lwe_thickness_cm"])
    G = rules["groundwater"]
    t = gwm.trend(s, G["alpha"])
    cell = card.get("location", {}).get("cell", {})
    factor = cell.get("cri_scale_factor", {}).get("value")
    out = {"trend_cm_per_year": round(t["trend_cm_per_year"], 2),
           "direction": gwm.direction(t["trend_cm_per_year"], t["p"], G["alpha"]), "confidence": gwm.confidence(t["p"])}
    detail = {**t, "cell_lat_bounds": cell.get("lat_bounds"), "cell_lon_bounds": cell.get("lon_bounds"),
              "cri_scale_factor": factor, "scale_factor_applied": False,
              "trend_if_scale_factor_applied_cm_per_year": round(t["trend_cm_per_year"] * factor, 2) if factor else None,
              "solutions": int(df["lwe_thickness_cm"].notna().sum()),
              "median_uncertainty_cm": round(float(df["uncertainty_cm"].median()), 2),
              "ols_trend_cm_per_year_from_card": cell.get("trend_unscaled_cm_per_year"),
              "caveat": G["caveat"]}
    return out, detail


def _onset_doy(out_dir):
    d = json.loads((out_dir / "diary_onset.json").read_text())
    return {int(y): v for y, v in d["day_of_year"].items()}, d


def run_diary_6c(field, rules, out_dir, data, base_dir=None):
    """base_dir: where the rain-free results (seasons, bare days) are read; out_dir by default."""
    base_dir = base_dir or out_dir
    lib = load_crops()
    clean = data / "clean" / field["id"]
    w = _weather(field, data)
    rain = pd.Series(w["rain_mm"].to_numpy(float), index=pd.DatetimeIndex(w["date"]))
    tmax = pd.Series(w["tmax_c"].to_numpy(float), index=pd.DatetimeIndex(w["date"]))
    tfrost = pd.Series(w["tmin_frost_c"].to_numpy(float), index=pd.DatetimeIndex(w["date"]))
    T, M = rules["trends"], rules["months"]
    caveat = rules["gpm_series"]["trend_caveat"]

    gw_out, gw_detail = _grace(field, rules, data)

    doy, onset_doc = _onset_doy(out_dir)
    pinned = tr.pinned_years(doy, rules["monsoon_onset"]["search_from"], within_days=2)   # each year's own 15 May
    series = {"onset_day_of_year": doy,
              "hot_days": tr.hot_days(tmax, T["hot_day"]["base_years"], T["hot_day"]["pct"], T["hot_day"]["window_days"]),
              "longest_dry_spell_days": tr.longest_dry_spell(rain, T["dry_day_mm"]),
              "heavy_rain_days": tr.heavy_rain_days(rain, T["heavy_rain_mm"])}
    trends = {}
    for k, vals in series.items():
        r = tr.mk_sen(vals, T["alpha"])
        chg = tr.over_record(r, r["first"], r["last"])
        trends[k] = {**{x: (round(v, 3) if isinstance(v, float) else v) for x, v in r.items()},
                     "change_over_record": chg[0], "change_low": chg[1], "change_high": chg[2],
                     "values": {str(y): v for y, v in sorted(vals.items())},
                     "caveat": caveat if k != "hot_days" else T["hot_day_caveat"]}
    # REVIEW_2 H8 and the owner's answer 11 (2026-11-13): NASA POWER's 2001-2003 are faulty here (rain, daytime
    # temperature, humidity), so every trend is reported for the whole record AND without those years (2004-2025)
    faulty = rules["power_rain"]["never_fill_years"]
    for k, vals in series.items():
        r = tr.mk_sen(tr.without_years(vals, faulty), T["alpha"])
        trends[k]["without_faulty_years"] = {**{x: (round(v, 3) if isinstance(v, float) else v) for x, v in r.items()},
                                             "years_left_out": list(faulty)}
    shift = trends["onset_day_of_year"]
    onset_note = (f"The onset rule (kept as set by the owner) is pinned at the search start (15-17 May) in {pinned} of "
                  f"{len(doy)} years: it finds the first lasting rain spell, not the monsoon's arrival, so its trend "
                  "cannot show a monsoon shift (VALIDATION 4.1d).")

    # monthly calendar
    rain_m = rain.groupby([rain.index.year, rain.index.month]).sum().groupby(level=1).mean()
    tmax_m = tmax.groupby(tmax.index.month).mean()
    rotation, rot_label = sim.rotation_for(field, rules)
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    cover_c, by_cover = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by_cover["bare"], **{c: by_cover[cover_c[c]] for c in rotation}}
    rep = sim.replay(w, rotation, lib, soil, cn, bare_kc=rules["bare_soil"]["kc"], irrigated=False,
                     kc_climate=rules["kc_climate"]["apply"])
    daily = rep["daily"]
    wet = pd.Series((1 - daily["dr_mm"] / daily["taw_mm"]).to_numpy(float), index=pd.DatetimeIndex(daily["date"]))
    wet_m = wet.groupby(wet.index.month).mean()
    coldest = mo.coldest_by_month(tfrost)
    frost_cal = mo.frost_by_calendar_month(coldest, M["frost_c"], M["frost_risk_c"])
    lab = pd.read_parquet(clean / "seasons_daily.parquet")
    lab = lab[(lab["source"] == "hls") & (lab["date"].dt.year >= 2014)]
    cover = mo.cover_by_month(pd.Series(lab["label"].to_numpy(), index=pd.DatetimeIndex(lab["date"])))
    words = {"rain": mo.tercile_words(rain_m.reindex(range(1, 13)).to_numpy(), ("low", "medium", "high")),
             "soil": mo.tercile_words(wet_m.reindex(range(1, 13)).to_numpy(), ("dry", "medium", "wet")),
             "heat": mo.tercile_words(tmax_m.reindex(range(1, 13)).to_numpy(), ("none", "some", "high"))}
    months = [{"m": MONTH_NAMES[i], "rain": words["rain"][i], "soil": words["soil"][i], "heat": words["heat"][i],
               "frost": frost_cal[i + 1], "cover": cover[i + 1]} for i in range(12)]
    jan2010 = coldest[(2010, 1)]
    frost_check = {"month": "2010-01", "coldest_night_c": round(jan2010, 2),
                   "band": mo.frost_band(jan2010, M["frost_c"], M["frost_risk_c"]),
                   "nights_below_0": int((tfrost["2010-01"] < M["frost_c"]).sum()),
                   "nights_below_2": int((tfrost["2010-01"] < M["frost_risk_c"]).sum())}

    # rotation guess
    sj = json.loads((base_dir / "diary_seasons.json").read_text())
    hls_seasons = [{k: pd.Timestamp(r[k]) for k in ("start", "peak", "end")}
                   for rows in sj["chosen"]["seasons_by_year"].values() for r in rows if r["source"] == "hls"]
    crops = [c for c in lib if lib[c].get("stages_days")]
    gs = gu.guess(hls_seasons, lib, crops)
    win = gs["slots"]["winter"]["fit"]
    rw = {"rice_then_wheat": gs["slots"]["monsoon"]["fit"]["rice"]["median_total"] + win["wheat"]["median_total"],
          "rice_then_potato": gs["slots"]["monsoon"]["fit"]["rice"]["median_total"] + win["potato"]["median_total"]}

    bare = json.loads((base_dir / "diary_bare_days.json").read_text())["summary"]["mean_bare_days_hls_years"]
    shift_days = None if pinned > len(doy) / 2 else shift["change_over_record"]
    export = {"shift_days": shift_days, "bare_days": int(round(bare)), "guess": gs["guess"],
              "groundwater": gw_out, "months": months}
    out = {"labels": {"field": field["name"], "rotation_for_soil": f"{rotation} ({rot_label}), rain-fed twin",
                      "rain_version": RAIN["version"],
                      "rain_caveat": caveat, "onset_note": onset_note,
                      "frost_caveat": "frost Tmin (quantile-mapped) overcounts cold nights against the station: a risk band, never a count",
                      "guess_note": "timing only: NDVI shows green cover, not which crop; the farmer confirms"},
           "export": export, "groundwater": gw_detail, "trends": trends, "onset_pinned_years": pinned,
           "months_values": {"rain_mm": {MONTH_NAMES[m - 1]: round(float(v), 1) for m, v in rain_m.items()},
                             "soil_wetness_0_1": {MONTH_NAMES[m - 1]: round(float(v), 3) for m, v in wet_m.items()},
                             "tmax_c": {MONTH_NAMES[m - 1]: round(float(v), 1) for m, v in tmax_m.items()},
                             "median_coldest_night_c": {MONTH_NAMES[m - 1]: round(float(np.median([v for (y, mm), v in coldest.items() if mm == m])), 1) for m in range(1, 13)}},
           "frost_check_2010_01": frost_check, "rotation_guess": gs, "rotation_compare": rw}
    path = out_dir / "diary.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"groundwater: {gw_out} (p {gw_detail['p']:.3g}, {gw_detail['first']}..{gw_detail['last']}, cell lat "
          f"{gw_detail['cell_lat_bounds']} lon {gw_detail['cell_lon_bounds']}; OLS {gw_detail['ols_trend_cm_per_year_from_card']:+.2f}; "
          f"if the scale factor were applied {gw_detail['trend_if_scale_factor_applied_cm_per_year']}, not applied: owner M4)")
    for k, v in trends.items():
        print(f"trend {k}: {v['slope_per_year']:+.3f}/yr [{v['low']:+.3f}, {v['high']:+.3f}], p {v['p']:.3f}, "
              f"over record {v['change_over_record']} [{v['change_low']}, {v['change_high']}]")
    print(f"onset pinned at search start in {pinned} of {len(doy)} years")
    for mrow in months:
        print("  ", mrow)
    print(f"frost check Jan 2010: {frost_check}")
    for slot in ("monsoon", "winter"):
        fits = sorted(gs["slots"][slot]["fit"].items(), key=lambda kv: kv[1]["median_total"])
        print(f"guess {slot}: " + "; ".join(f"{c} {f['median_total']:.0f} (start {f['median_start']:.0f}, end "
                                             f"{f['median_end']:.0f}, length {f['median_length']:.0f})" for c, f in fits))
    print(f"guess: {gs['guess']}; rice-wheat {rw['rice_then_wheat']:.0f} vs rice-potato {rw['rice_then_potato']:.0f} days\n-> {path.relative_to(REPO)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--steps", default="onset,greenness,seasons,diary",
                    help="comma list of onset, greenness, seasons, diary")
    ap.add_argument("--rain", choices=("corrected", "uncorrected"), default="corrected")
    a = ap.parse_args(argv)
    steps = set(a.steps.split(","))
    field, rules = load_field(a.field), load_rules()
    RAIN["version"] = a.rain
    base_dir = REPO / "data" / "checks" / field["id"]
    out_dir = base_dir / "rain_uncorrected" if a.rain == "uncorrected" else base_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.rain == "uncorrected" and steps - {"onset", "diary"}:
        print("--rain uncorrected reruns the rain-based steps only (onset, diary); greenness and seasons come from the main run")
        steps &= {"onset", "diary"}
    if "onset" in steps:
        run_onset(field, rules, out_dir)
    if "greenness" in steps:
        run_greenness(field, rules, out_dir, REPO / "data")
    if "seasons" in steps:
        run_seasons(field, rules, out_dir, REPO / "data")
    if "diary" in steps:
        run_diary_6c(field, rules, out_dir, REPO / "data", base_dir=base_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
