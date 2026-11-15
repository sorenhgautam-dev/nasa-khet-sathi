"""Near-real-time weather for the twin's state "now" (build step 10; rules.yaml probe.kalman.as_of).

    .venv/bin/python -m pipeline.fetch.now --field demo [--workers 4] [--from-cache]

NASA POWER daily (community AG; GEOS-IT meteorology, FLASHFlux solar for the latest weeks) and GPM IMERG Late V07 daily
(GPM_3IMERGDL) from the day after weather.parquet ends to the last day on which POWER has every input the twin uses and
IMERG Late has rain (`as_of`). Nothing after it is filled or guessed. Those days are built EXACTLY as
pipeline/fetch/weather.py builds weather.parquet: Kathmandu-valley offsets and frost quantile mapping fitted on the same
history, rain merge (decision D: POWER fills only days IMERG lacks, capped), the GPM break correction with the factors
fitted on IMERG Final months applied to the Late days (owner's answer 7 to REVIEW_2; rules.yaml gpm_series), ET0 with
the vapour pressure held from POWER. weather.py's build() writes weather.parquet, so it cannot be called here: the same
steps are rebuilt from the same imported pieces, and the whole 2001-2025 history is rebuilt with them and must equal
weather.parquet (reproduction()) before any new day is written.

Reads data/clean/<field>/{power,gpm,weather}.parquet, the station table and cards; writes data/raw/power_now/<field>/,
data/raw/gpm_now/<field>/late/, data/clean/<field>/weather_now.parquet and data/cards/<field>/weather_now.json. Never
touches weather.parquet, power.parquet or gpm.parquet. POWER days are local solar time; IMERG days are UTC days.
"""
import argparse
import datetime as dt
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.checks.spikes import spike_days
from pipeline.fetch import gpm, power
from pipeline.fetch import guards as g
from pipeline.fetch import weather as wx
from pipeline.twin import bias, inputs as tin, qmap
from pipeline.twin.et0 import et0_mm

REPO = Path(__file__).resolve().parents[2]
NEEDED = ["tmax_c", "tmin_c", "rh_pct", "ws2m_ms", "rs_mj_m2_day"]     # every POWER input the twin uses (rain: IMERG)
LATE = "GPM_3IMERGDL"
FLOAT_TOL = 1e-9


# ---------- pure pieces ----------

def last_complete_day(df, cols):
    """The last day with every column in `cols`; any missing value before it fails loudly (golden rule 12c)."""
    ok = df[cols].notna().all(axis=1).to_numpy()
    if not ok.any():
        raise g.DataGuardError(f"no day has all of {cols}")
    last = int(np.flatnonzero(ok)[-1])
    gaps = df["date"].iloc[:last + 1][~ok[:last + 1]]
    if len(gaps):
        raise g.DataGuardError(f"{len(gaps)} day(s) miss a twin input before the last complete day, first "
                               f"{gaps.iloc[0].date()}: not filled, not guessed")
    return pd.Timestamp(df["date"].iloc[last])


def as_of_day(power_df, gpm_df, cols=NEEDED):
    """rules.yaml probe.kalman.as_of: the last POWER day with every input, and no later than IMERG Late's last rain day."""
    p = last_complete_day(power_df, cols)
    has = gpm_df.loc[gpm_df["rain_mm"].notna(), "date"]
    if has.empty:
        raise g.DataGuardError("IMERG Late has no rain day: no rain, no state (decision D)")
    return min(p, pd.Timestamp(has.max()))


def join_weather(hist, new):
    """weather.parquet followed by weather_now.parquet: same columns, consecutive days."""
    if list(hist.columns) != list(new.columns):
        raise ValueError(f"the two weather tables have different columns: {list(hist.columns)} / {list(new.columns)}")
    out = pd.concat([hist, new], ignore_index=True)
    d = pd.DatetimeIndex(out["date"])
    if not (d[1:] - d[:-1] == pd.Timedelta(1, unit="D")).all():
        raise ValueError("the joined weather is not consecutive days (a gap or an overlap between the two tables)")
    return out


def build_days(field, inputs, power_new, gpm_new, rules):
    """weather.py's steps on the history (and the new days, when given). Returns {table, info}; the history rows must equal
    weather.parquet (reproduction). The corrections are fitted on the history only, exactly as weather.py fits them."""
    tc, hist_power, station = rules["temperature_correction"], inputs["power"], inputs["station"]
    pw = hist_power if power_new is None else pd.concat([hist_power, power_new[hist_power.columns]], ignore_index=True)
    pw = pw.reset_index(drop=True)
    df, corrections = pd.DataFrame({"date": pw["date"]}), {}
    for col in tc["columns"]:
        flag = col.replace("_c", "_corrected")
        df[f"{col}_power"] = pw[col]
        df[col], df[flag] = pw[col], False
        if station is None:
            corrections[col] = {"label": "uncorrected POWER (no nearby station)", "applied": False}
            continue
        if not wx.station_corrects(field):      # as weather.py: a station without correction_label is for validation only
            corrections[col] = {"label": "uncorrected POWER (the station is for validation only: no correction_label)",
                                "applied": False}
            continue
        c = bias.build_correction(hist_power, station, col, tc["min_shared_days_per_year"], tc["min_shared_days_per_month"])
        label = f"{field.get('correction_label', 'station-based correction')} (station {field.get('validation_station')})"
        if c["apply"]:
            df[col] = bias.apply_offsets(pw, col, c["offsets"]).to_numpy()
            df[flag] = df["date"].dt.month.map(lambda m: c["offsets"][m]["offset"] is not None).to_numpy()
        corrections[col] = {"label": label if c["apply"] else f"not applied ({label})", "applied": c["apply"],
                            "offsets_by_month": {m: o["offset"] for m, o in c["offsets"].items()}}
        if col == "tmin_c" and c["apply"]:
            cn = rules["cold_nights"]
            ch = qmap.compare_cold_night_methods(hist_power, station, col, cn["seasons"], tc["min_shared_days_per_year"],
                                                 cn["min_shared_days_per_month"], cn["quantiles"], cn["frost_night_c"])
            if cn["roles"]["frost"] == "quantile mapping":
                df["tmin_frost_c"] = qmap.apply_qmap(pw, col, ch["qmap_models"]).to_numpy()
                df["tmin_frost_corrected"] = df["date"].dt.month.map(lambda m: ch["qmap_models"][m] is not None).to_numpy()
    frost = "quantile mapped onto the station, for frost risk bands only"
    if "tmin_frost_c" not in df:
        df["tmin_frost_c"], df["tmin_frost_corrected"], frost = df["tmin_c"], df["tmin_corrected"], "same as tmin_c"
    warned = g.check_table(df, {"tmax_c": "temp_c", "tmin_c": "temp_c", "tmin_frost_c": "temp_c"})
    for c in ("tmin_c", "tmin_frost_c"):
        wx.check_tmin_not_above_tmax(df, c)
    for col in ("rh_pct", "ws2m_ms", "rs_mj_m2_day"):
        df[col] = pw[col]
    gp = inputs["gpm"][["date", "rain_mm", "product"]]
    if gpm_new is not None:
        gp = pd.concat([gp, gpm_new[["date", "rain_mm", "product"]]], ignore_index=True)
    rain = tin.merge_rain(df["date"], gp.set_index("date")["rain_mm"], pw.set_index("date")["rain_mm"],
                          rules["power_rain"]["never_fill_years"])
    fills = tin.fill_by_year(rain)
    breaches = tin.fill_cap_breaches(fills["by_year"], rules["power_rain"]["max_filled_fraction_per_year"])
    if breaches:
        raise g.DataGuardError(f"POWER would fill more than the cap of a year's rain days: {breaches}")
    rain, break_info = wx.correct_gpm_break(rain, gp, rules["gpm_series"], field["id"], field=field,
                                            break_test=inputs.get("break_test"))
    df = df.merge(rain, on="date")
    elev = field.get("elevation_m") or inputs["power_card"]["location"]["elevation_m"]
    ea, capped = tin.ea_held_from_power_kpa(pw["rh_pct"], pw["tmax_c"], pw["tmin_c"], df["tmin_c"])
    df["ea_kpa"], df["ea_capped"] = ea, capped
    args = (df["tmax_c"], df["tmin_c"], df["ws2m_ms"], df["rs_mj_m2_day"], elev, field["lat"], df["date"].dt.day_of_year)
    df["et0_mm"] = et0_mm(*args, ea=ea)
    df["et0_rh_held_mm"] = et0_mm(*args, rh_mean=df["rh_pct"])
    for col in ("et0_mm", "et0_rh_held_mm"):
        g.assert_nonnegative(df[col].to_numpy(), col)
    return {"table": df, "info": {"corrections": corrections, "frost_method": frost, "range_warnings": warned,
                                  "rain_fill": fills, "rain_break": break_info, "elevation_m": elev}}


def reproduction(table, weather):
    """Compare the rebuilt rows with weather.parquet, column by column (floats within 1e-9, others equal)."""
    t = table[table["date"].isin(weather["date"])].reset_index(drop=True)
    diffs, same = {}, len(t) == len(weather) and set(weather.columns) <= set(t.columns)
    if same:
        for c in weather.columns:
            a, b = t[c], weather[c].reset_index(drop=True)
            if pd.api.types.is_float_dtype(b):
                d = np.abs(a.to_numpy(float) - b.to_numpy(float))
                both_nan = np.isnan(a.to_numpy(float)) & np.isnan(b.to_numpy(float))
                diffs[c] = float(np.nanmax(np.where(both_nan, 0.0, d))) if len(d) else 0.0
                same = same and not np.isnan(diffs[c]) and diffs[c] <= FLOAT_TOL
            else:
                eq = bool((a.astype(str).to_numpy() == b.astype(str).to_numpy()).all())
                diffs[c] = 0.0 if eq else 1.0
                same = same and eq
    return {"rows": int(len(t)), "identical": bool(same), "max_abs_diff": diffs}


# ---------- I/O ----------

def history_inputs(field, data_dir=REPO / "data"):
    fid = field["id"]
    clean, cards = Path(data_dir) / "clean" / fid, Path(data_dir) / "cards" / fid
    st_id = field.get("validation_station")
    st_path = clean / f"ghcn_{st_id}.parquet" if st_id else None
    bt = Path(data_dir) / "checks" / fid / "break_test.json"        # the field's own break test, as weather.py reads it
    return {"break_test": json.loads(bt.read_text()) if bt.exists() else None,
            "power": pd.read_parquet(clean / "power.parquet"),
            "station": pd.read_parquet(st_path) if st_path and st_path.exists() else None,
            "gpm": pd.read_parquet(clean / "gpm.parquet"),
            "weather": pd.read_parquet(clean / "weather.parquet"),
            "power_card": json.loads((cards / "power.json").read_text())}


def fetch_power(field, start, end, data_dir, from_cache=False, get_json=None):
    """POWER daily for start..end (one request), cached by fetch date; fills become NaN (power.parse prints the raw
    attributes first, rule 12a; power.check range-checks, rule 12b-c)."""
    raw = Path(data_dir) / "raw" / "power_now" / field["id"] / f"{float(field['lat']):.6f}_{float(field['lon']):.6f}"
    if field.get("power_point_of"):   # the other field's cached request in the same POWER cells: read only, never downloaded
        pts = sorted((Path(data_dir) / "raw" / "power_now" / field["power_point_of"]).glob("*_*"))
        if len(pts) != 1 or not power.same_cell(field, dict(zip(("lat", "lon"), map(float, pts[0].name.split("_"))))):
            raise g.DataGuardError(f"power_point_of {field['power_point_of']}: no single cached point in this field's POWER cells")
        raw, from_cache = pts[0], True
    s, e = pd.Timestamp(start).strftime("%Y%m%d"), pd.Timestamp(end).strftime("%Y%m%d")
    if from_cache:
        found = sorted(raw.glob(f"{s}_*_fetched_*.json"))
        if not found:
            raise FileNotFoundError(f"no cached POWER request in {raw}")
        cache = found[-1]
        e = cache.name.split("_")[1]
        payload = json.loads(cache.read_text())
    else:
        cache = raw / f"{s}_{e}_fetched_{dt.date.today()}.json"
        payload = (get_json or power._http_get_json)(power.build_url(field["lat"], field["lon"], s, e))
    df, info = power.parse(payload)
    want = pd.date_range(pd.Timestamp(s), pd.Timestamp(e))
    if len(df) != len(want) or (df["date"].to_numpy() != want.to_numpy()).any():
        raise g.DataGuardError(f"POWER returned {df['date'].min().date()} to {df['date'].max().date()} for {s} to {e}")
    warned = power.check(df)
    if not from_cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(payload))
    return df, {**info, "range_warnings": warned, "cache": str(cache.relative_to(REPO) if cache.is_relative_to(REPO) else cache)}


def fetch_gpm_late(field, start, end, data_dir, workers=4, from_cache=False):
    """IMERG Late V07 daily box subsets (gpm.py's helpers and guards), cached in data/raw/gpm_now/<field>/late/."""
    raw = Path(data_dir) / "raw" / "gpm_now" / field["id"] / "late"
    raw.mkdir(parents=True, exist_ok=True)
    idx = gpm.box_indices(field["fetch_box"])
    links, fails = {}, {}
    if not from_cache:
        import earthaccess
        import requests
        earthaccess.login(strategy="netrc", persist=False)
        found = earthaccess.search_data(short_name=LATE, version="07", temporal=(str(pd.Timestamp(start).date()),
                                                                                 str(pd.Timestamp(end).date())))
        links = {pd.Timestamp(x["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]): x.data_links()[0]
                 for x in found}
        todo = [(d, raw / f"{d.date()}.nc4", link) for d, link in sorted(links.items())
                if pd.Timestamp(start) <= d <= pd.Timestamp(end) and not (raw / f"{d.date()}.nc4").exists()]
        print(f"IMERG Late: {len(links)} day(s) in CMR; {len(todo)} to fetch", flush=True)
        s = requests.Session()
        with ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(gpm._get, s, link, idx, dest): d for d, dest, link in todo}
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:                      # recorded and counted, never silent
                    fails[str(futs[f].date())] = f"{type(e).__name__}: {str(e)[:160]}"
        (raw.parent / "failures.json").write_text(json.dumps(fails, indent=1) + "\n")
        (raw.parent / "links.json").write_text(json.dumps({str(d.date()): l for d, l in sorted(links.items())}, indent=0) + "\n")
    elif (raw.parent / "links.json").exists():
        links = {pd.Timestamp(d): l for d, l in json.loads((raw.parent / "links.json").read_text()).items()}
    fi, fj = gpm.cell_index(field["lat"], field["lon"])
    field_cell = (fi - idx[0], fj - idx[2])
    want_lon, want_lat = gpm.cell_centres(*idx)
    files = {d: raw / f"{d.date()}.nc4" for d in pd.date_range(start, end) if (raw / f"{d.date()}.nc4").exists()}
    if not files:
        raise RuntimeError(f"no IMERG Late file in {raw}")
    attrs = gpm.raw_attributes(next(iter(files.values())))
    print("raw attributes (IMERG Late precipitation, first file):", json.dumps(attrs["precipitation"], default=str), flush=True)
    rows = []
    for d in pd.date_range(start, end):
        if d in files:
            rows.append({"date": d, "product": "late", **gpm.read_subset(files[d], field_cell, want_lon, want_lat)})
        else:
            rows.append({"date": d, "product": "late", "rain_mm": np.nan, "rain_box_mean_mm": np.nan, "cells": 0,
                         "field_cell_fill": False, "box_fills": 0})
    df = pd.DataFrame(rows)
    versions = sorted({m.group(1) for l in links.values() for m in [re.search(r"\.(V\d+[A-Z]?)\.nc4", l)] if m})
    return df, {"raw_attrs": attrs, "versions": versions, "failures": fails, "field_cell": field_cell,
                "box_cells_lon": want_lon, "box_cells_lat": want_lat, "files": len(files),
                "days_without_file": [str(d.date()) for d in pd.date_range(start, end) if d not in files]}


def build(field, data_dir=REPO / "data", rules=None, workers=4, from_cache=False, end=None, credits_path=None):
    from pipeline.fetch.rules import load_rules
    rules = rules or load_rules()
    fid, data_dir = field["id"], Path(data_dir)
    hist = history_inputs(field, data_dir)
    w = hist["weather"]
    start = pd.Timestamp(w["date"].max()) + pd.Timedelta(1, unit="D")
    end = pd.Timestamp(end) if end else pd.Timestamp(dt.date.today()) - pd.Timedelta(1, unit="D")
    pnew, pinfo = fetch_power(field, start, end, data_dir, from_cache=from_cache)
    gnew, ginfo = fetch_gpm_late(field, start, end, data_dir, workers=workers, from_cache=from_cache)
    p_last, g_last = last_complete_day(pnew, NEEDED), pd.Timestamp(gnew.loc[gnew["rain_mm"].notna(), "date"].max())
    as_of = as_of_day(pnew, gnew)
    by_input = {c: str(pnew.loc[pnew[c].notna(), "date"].max().date()) for c in NEEDED + ["rain_mm"]}
    pnew, gnew = pnew[pnew["date"] <= as_of].reset_index(drop=True), gnew[gnew["date"] <= as_of].reset_index(drop=True)
    out = build_days(field, hist, pnew, gnew, rules)
    rep = reproduction(out["table"], w)
    if not rep["identical"]:
        raise g.DataGuardError(f"rebuilding 2001-2025 with this module does not give weather.parquet: {rep}. "
                               "weather.py or its inputs changed; nothing written")
    table = out["table"]
    now = table[table["date"] >= start][list(w.columns)].reset_index(drop=True)
    info = out["info"]
    n_filled = int(now["rain_filled"].sum())
    late_card = {"product": "GPM IMERG Late daily (GPM_3IMERGDL)", "version": "V07 (" + ", ".join(ginfo["versions"]) + ")",
                 "source": "Huffman et al., NASA GES DISC, doi:10.5067/GPM/IMERGDL/DAY/07", "resolution": "0.1 deg"}
    src, res = wx.column_sources(now, field.get("validation_station") if hist["station"] is not None else None,
                                 info["corrections"], info["frost_method"], late_card, n_filled, info["elevation_m"])
    rb = info["rain_break"] or {}
    src["rain_mm"] = (f"GPM IMERG Late V07 daily ({', '.join(ginfo['versions'])}), satellite-based, the field's 0.1 deg cell, "
                      f"UTC days; scaled month by month with the factors fitted on IMERG Final months, 2001-2016 level over "
                      f"{rb.get('from', '?')} onwards (owner's answer 7 to REVIEW_2; rules.yaml gpm_series); days IMERG lacks "
                      f"filled from {wx.POWER_SRC}, PRECTOTCORR, flagged ({n_filled} day(s))")
    if rb.get("gauge_calibration", {}).get("applied"):
        src["rain_mm"] += "; then times two factors fitted on four DHM gauges (rules.yaml gpm_series.gauge_calibration)"
    src["rain_uncorrected_mm"] = src["rain_mm"].split("; scaled")[0] + "; as published, without the break correction"
    out_path = data_dir / "clean" / fid / "weather_now.parquet"
    now.to_parquet(out_path, index=False)
    flags = spike_days({"power": pnew[["date", "rain_mm"]], "gpm": gnew[["date", "rain_mm"]]},
                       rules["rain_spike"]["min_mm"], rules["rain_spike"]["ratio"])
    limited_by = "POWER solar (FLASHFlux)" if pd.Timestamp(by_input["rs_mj_m2_day"]) == as_of else (
        "IMERG Late" if g_last == as_of else "POWER meteorology")
    card = g.make_card(
        dataset="weather_now", product="Twin input weather, near-real-time (derived: NASA POWER daily + GPM IMERG Late V07)",
        version="pipeline 2026-11-14 (pipeline/fetch/now.py)", variable=list(now.columns),
        units_in={"power": pinfo["units_in"], "gpm_late": "mm/day (daily mean rate = the UTC day's rain)"},
        units_out="unit in each column name", scale_factor=None,
        fill_values_removed={"power_fill_value": pinfo["fill_value"],
                             "power_days_after_as_of_dropped": int((pd.date_range(as_of, end).size - 1)),
                             "gpm_late_fill_in_field_cell": int(gnew["field_cell_fill"].sum())},
        quality_flags_used="none (POWER carries no per-value flag; IMERG precipitation only)",
        records_dropped=int((pd.date_range(as_of, end).size - 1)),
        date_range=[str(start.date()), str(as_of.date())],
        time_zone="POWER days: local solar time (API header time_standard LST); IMERG days: UTC days (05:45-05:45 Nepal time)",
        pixel_count=1, source=src, resolution=res,
        raw_attrs={"power": pinfo["raw_attrs"], "gpm_late": ginfo["raw_attrs"]},
        range_warnings={"power": pinfo["range_warnings"], "weather": info["range_warnings"]},
        corrections={"temperature": info["corrections"], "frost_method": info["frost_method"],
                     "rain_fill": info["rain_fill"]["by_year"].get(as_of.year), "rain_break": rb,
                     "reproduction_of_weather_parquet": rep},
        cross_source_flags=flags,
        location={"lat": field["lat"], "lon": field["lon"], "elevation_m": info["elevation_m"],
                  "gpm_field_cell": ginfo["field_cell"]},
        summary={"as_of": str(as_of.date()), "limited_by": limited_by, "last_day_by_power_input": by_input,
                 "imerg_late_last_day": str(g_last.date()), "power_last_complete_day": str(p_last.date()),
                 "requested_through": str(end.date()), "days": int(len(now)), "imerg_late_versions": ginfo["versions"],
                 "imerg_late_days_without_file": len(ginfo["days_without_file"]), "imerg_late_failures": len(ginfo["failures"]),
                 "power_cache": pinfo["cache"]},
        notes=("Built by the same steps as weather.parquet (pipeline/fetch/weather.py), with the corrections fitted on the "
               "same 2001-2025 history; the rebuilt history equals weather.parquet (corrections.reproduction_of_weather_parquet). "
               f"Days after {as_of.date()} are not used: POWER's inputs or IMERG Late are not complete yet. Spike flags: "
               "POWER against IMERG Late only (no station days in this period)."))
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        from pipeline.fetch.credits import ensure_credit
        ensure_credit(credits_path, f"- NASA POWER daily API (near-real-time: GEOS-IT, FLASHFlux; model-based) and NASA GPM IMERG "
                                    f"Late V07 daily (GPM_3IMERGDL, GES DISC OPeNDAP), field `{fid}`, {start.date()} to "
                                    f"{as_of.date()}, fetched {dt.date.today()} by pipeline/fetch/now.py (the twin's state now, "
                                    "build step 10)")
    return {"table": out_path, "card": card_path, "card_data": card, "as_of": as_of}


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--from-cache", action="store_true", help="rebuild from the cached raw files only (no network)")
    ap.add_argument("--end", default=None, help="last day to request (default: yesterday)")
    a = ap.parse_args(argv)
    r = build(load_field(a.field), workers=a.workers, from_cache=a.from_cache, end=a.end, credits_path=REPO / "records" / "credits.txt")
    s = r["card_data"]["summary"]
    print(f"as of {s['as_of']} (limited by {s['limited_by']}); {s['days']} days; last day by POWER input "
          f"{s['last_day_by_power_input']}; IMERG Late to {s['imerg_late_last_day']} ({s['imerg_late_versions']}); "
          f"history reproduced: {r['card_data']['corrections']['reproduction_of_weather_parquet']['identical']}")
    print(f"-> {r['table']}\n-> {r['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
