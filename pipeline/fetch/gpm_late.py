"""IMERG Late V07 for 2014-2019: rain check B's confirmation run (owner's go, 2026-11-13). A check only, never the
twin's rain.

    .venv/bin/python -m pipeline.fetch.gpm_late --field demo [--start 2014-01-01 --end 2019-12-31] [--workers 4]
    .venv/bin/python -m pipeline.fetch.gpm_late --field demo --from-cache

IMERG V07 Late (GPM_3IMERGDL) was reprocessed back to 1998 with a climatological gauge calibration instead of the
monthly GPCC gauge analysis that IMERG Final uses, so it should not step when the monthly gauges around the field
vanish in January 2017 (VALIDATION 3.9b). If Final jumps in 2017 and Late does not, Final's jump is the gauge loss.
Same daily OPeNDAP box subsets as pipeline/fetch/gpm.py (its helpers, its guards), cached separately in
data/raw/gpm_late_check/<field>/late/ and written to data/clean/<field>/gpm_late_check.parquet with its own card,
so the twin's GPM record (gpm.parquet) is never touched.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch import gpm

REPO = Path(__file__).resolve().parents[2]
SHORT_NAME = "GPM_3IMERGDL"


def raw_dir(data_dir, field):
    return Path(data_dir) / "raw" / "gpm_late_check" / field["id"] / "late"


def build(field, data_dir, start, end, failures=None):
    from pipeline.fetch import guards as g
    raw = raw_dir(data_dir, field)
    idx = gpm.box_indices(field["fetch_box"])
    fi, fj = gpm.cell_index(field["lat"], field["lon"])
    field_cell = (fi - idx[0], fj - idx[2])
    want_lon, want_lat = gpm.cell_centres(*idx)
    dates = pd.date_range(start, end)
    files = {d: raw / f"{d.date()}.nc4" for d in dates if (raw / f"{d.date()}.nc4").exists()}
    if not files:
        raise RuntimeError(f"no cached IMERG Late file in {raw}")
    attrs = gpm.raw_attributes(next(iter(files.values())))
    print("raw attributes (precipitation, first file):", json.dumps(attrs["precipitation"], default=str), flush=True)
    rows = []
    for d in dates:
        if d in files:
            rows.append({"date": d, **gpm.read_subset(files[d], field_cell, want_lon, want_lat)})
        else:
            rows.append({"date": d, "rain_mm": np.nan, "rain_box_mean_mm": np.nan, "cells": 0, "field_cell_fill": False,
                         "box_fills": 0})
    df = pd.DataFrame(rows)
    out = Path(data_dir) / "clean" / field["id"] / "gpm_late_check.parquet"
    df[["date", "rain_mm", "rain_box_mean_mm"]].to_parquet(out, index=False)
    missing = [str(d.date()) for d in dates if d not in files]
    valid = df.loc[df["rain_mm"].notna(), "date"]
    card = g.make_card(
        dataset="gpm_late_check", product="GPM IMERG Late daily (GPM_3IMERGDL)", version="V07",
        variable="precipitation (daily mean rate)", units_in="mm/day", units_out="rain_mm (mm per UTC day)",
        scale_factor=None, fill_values_removed={"_FillValue in the field's cell": int(df["field_cell_fill"].sum())},
        quality_flags_used="none", records_dropped=int(df["rain_mm"].isna().sum()),
        date_range=[str(valid.min().date()), str(valid.max().date())] if len(valid) else [],
        time_zone=gpm.TIME_ZONE, pixel_count=int(df["cells"].max()),
        source="Huffman et al., GPM IMERG Late Precipitation L3 1 day 0.1 degree V07, NASA GES DISC",
        resolution="0.1 deg (about 10 km); the field's cell and the box mean",
        raw_attrs={"precipitation": attrs["precipitation"], "file": attrs["file"]},
        location={"box_cells_lon": want_lon, "box_cells_lat": want_lat, "field_cell": field_cell},
        notes=(f"Rain check B confirmation only (owner's go, 2026-11-13); never the twin's rain. Requested {start} to "
               f"{end} ({len(dates)} days); days without a file: {len(missing)} "
               f"({gpm.day_ranges(missing) or 'none'}); failed downloads: {len(failures or {})}."))
    return {"table": out, "card": g.write_card(card, Path(data_dir) / "cards" / field["id"]), "df": df, "missing": missing}


def fetch(field, data_dir, start, end, workers=4):
    import earthaccess
    import requests
    earthaccess.login(strategy="netrc", persist=False)
    idx = gpm.box_indices(field["fetch_box"])
    found = earthaccess.search_data(short_name=SHORT_NAME, version="07", temporal=(start, end))
    days = {pd.Timestamp(x["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]): x.data_links()[0]
            for x in found}
    days = {d: link for d, link in days.items() if pd.Timestamp(start) <= d <= pd.Timestamp(end)}
    raw = raw_dir(data_dir, field)
    raw.mkdir(parents=True, exist_ok=True)
    todo = [(d, raw / f"{d.date()}.nc4", link) for d, link in sorted(days.items()) if not (raw / f"{d.date()}.nc4").exists()]
    print(f"IMERG Late: {len(days)} day(s) in CMR for {start} to {end}; {len(todo)} to fetch", flush=True)
    fails = {}
    s = requests.Session()                      # Earthdata Login credentials come from ~/.netrc
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(gpm._get, s, link, idx, dest): d for d, dest, link in todo}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:
                fails[str(futs[f].date())] = f"{type(e).__name__}: {str(e)[:160]}"
            if n % 250 == 0:
                print(f"IMERG Late: {n}/{len(todo)} fetched, {len(fails)} failed", flush=True)
    (raw.parent / "failures.json").write_text(json.dumps(fails, indent=1) + "\n")
    if todo and len(fails) == len(todo):
        raise RuntimeError(f"every IMERG Late request failed, e.g. {next(iter(fails.values()))}")
    return build(field, data_dir, start, end, fails)


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--end", default="2019-12-31")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--from-cache", action="store_true")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    if a.from_cache:
        r = build(field, REPO / "data", a.start, a.end)
    else:
        r = fetch(field, REPO / "data", a.start, a.end, a.workers)
        ensure_credit(REPO / "records" / "credits.txt",
                      f"- NASA GPM IMERG V07 Late daily (GPM_3IMERGDL, GES DISC OPeNDAP), the 0.1 deg cells of field "
                      f"`{field['id']}`'s fetch box, {a.start[:4]}-{a.end[:4]}, fetched {pd.Timestamp.now().date()} by "
                      "pipeline/fetch/gpm_late.py (rain check B confirmation only; never the twin's rain)")
    d = r["df"]
    print(f"{int(d['rain_mm'].notna().sum())} of {len(d)} days with rain; missing {len(r['missing'])}\n-> {r['table']}\n-> {r['card']}")
    return 1 if r["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
