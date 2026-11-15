"""CHIRPS v3.0 daily rain, a cross-check on GPM only (rain check B, owner's go 2026-11-13). Never the twin's rain.

    .venv/bin/python -m pipeline.fetch.chirps --field demo [--years 2001-2025] [--deadline 2026-11-14T08:00:00+05:45]
    .venv/bin/python -m pipeline.fetch.chirps --field demo --from-cache          # rebuild from cached years only

Product: CHIRPS v3.0 daily final, `rnl` version (pentads disaggregated to days with ERA5; the other daily version
uses IMERG, which is what is being checked). Climate Hazards Center, UC Santa Barbara; public domain;
doi:10.15780/G2JQ0P. One global netCDF-4 file per year (about 3.9 GB):
https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/netcdf/byYear/chirps-v3.0.rnl.<year>.days_p05.nc
(precip, float32, mm/day, chunks of 31 days x 200 x 600 cells, gzip; _FillValue -9999; read 2026-11-13).
Only the chunks holding the fetch box are read, through HTTP range requests (pipeline/fetch/rangefile.py): about
12 chunks of 4-10 MB a year, about 14 minutes a year because the server often answers 429 (too many requests).
Each year's box values are cached in data/raw/chirps/<field>/rnl_<year>.npz, so reruns resume. Days are UTC
calendar-day labels (CHIRPS v3 daily README; station inputs keep their own windows).

Owner, 2026-11-13: run in the background overnight and stop if it is not finished by Saturday 08:00 (a bonus check):
--deadline stops it cleanly between or inside years; the cached years are still written. Years are fetched around
the 2017 break first (2013-2020), then outwards, so a stopped run still answers the question.

Writes data/clean/<field>/chirps.parquet (date, rain_mm in the field's 0.05 deg cell, rain_box_mean_mm) and the card.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/netcdf/byYear/chirps-v3.0.rnl.{year}.days_p05.nc"
RES = 0.05
FIRST_FIRST = (2013, 2020)          # fetched first: the years around GPM's January 2017 break


def year_order(first, last, core=FIRST_FIRST):
    """Years first..last, the core years (around the break) first, then alternately before and after them."""
    years = list(range(first, last + 1))
    head = [y for y in years if core[0] <= y <= core[1]]
    before = [y for y in reversed(years) if y < core[0]]
    after = [y for y in years if y > core[1]]
    tail = []
    while before or after:
        if after:
            tail.append(after.pop(0))
        if before:
            tail.append(before.pop(0))
    return head + tail


def box_cells(lat, lon, box, field_lat, field_lon):
    """Index ranges of the grid cells overlapping the fetch box [min_lon, min_lat, max_lon, max_lat] and the
    position of the field's own cell inside them. lat/lon are the grid's cell centres (any order)."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    rows = np.where((lat + RES / 2 > box[1]) & (lat - RES / 2 < box[3]))[0]
    cols = np.where((lon + RES / 2 > box[0]) & (lon - RES / 2 < box[2]))[0]
    if len(rows) == 0 or len(cols) == 0:
        raise ValueError("no CHIRPS cell overlaps the fetch box (outside 60 S-60 N?)")
    fr = int(np.argmin(np.abs(lat - field_lat)))
    fc = int(np.argmin(np.abs(lon - field_lon)))
    if abs(lat[fr] - field_lat) > RES / 2 + 1e-6 or abs(lon[fc] - field_lon) > RES / 2 + 1e-6:
        raise ValueError(f"the field ({field_lat}, {field_lon}) is not inside the nearest cell ({lat[fr]}, {lon[fc]})")
    if not (rows[0] <= fr <= rows[-1] and cols[0] <= fc <= cols[-1]):
        raise ValueError("the field's cell lies outside the fetch box")
    return (int(rows[0]), int(rows[-1])), (int(cols[0]), int(cols[-1])), (fr - int(rows[0]), fc - int(cols[0]))


def field_cell(lat, lon, field_lat, field_lon):
    """(row, col) of the cached box cell holding the field now (build step 11: a field abroad is fetched for its box
    before its square is picked). Fails loudly when the field is not inside a cached cell."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    fr, fc = int(np.argmin(np.abs(lat - field_lat))), int(np.argmin(np.abs(lon - field_lon)))
    if abs(lat[fr] - field_lat) > RES / 2 + 1e-6 or abs(lon[fc] - field_lon) > RES / 2 + 1e-6:
        raise ValueError(f"the field ({field_lat}, {field_lon}) is outside the cached CHIRPS cells")
    return fr, fc


def days_from_time(values, units):
    """'days since 1980-01-01 ...' -> DatetimeIndex (whole days only)."""
    unit, _, origin = units.partition(" since ")
    if unit.strip() != "days" or not origin:
        raise ValueError(f"unexpected time units '{units}'")
    v = np.asarray(values, float)
    if not np.allclose(v, np.round(v)):
        raise ValueError("time values are not whole days")
    return pd.Timestamp(origin.strip().split()[0]) + pd.to_timedelta(np.round(v).astype(int), unit="D")


def clean_values(raw, fills):
    """Fill values to NaN (counted); then the rain guard (golden rule 12b): 0 to 500 mm/day or fail loudly."""
    from pipeline.fetch import guards as g
    a, n_fill = g.mask_fill(np.asarray(raw), fills)
    g.assert_in_range(a[np.isfinite(a)], "rain_mm", "CHIRPS precip")
    return a, n_fill


def _text(v):
    if isinstance(v, bytes):
        return v.decode()
    if isinstance(v, np.ndarray) and v.size == 1:
        return v.item()
    return v.tolist() if isinstance(v, np.ndarray) else v


def read_year(year, field, deadline=None):
    """The fetch box's cells for one year, read remotely. Returns the arrays and the raw attributes."""
    import h5py

    from pipeline.fetch import guards as g
    from pipeline.fetch.rangefile import RangeFile
    rf = RangeFile(URL.format(year=year), deadline=deadline)
    with h5py.File(rf, "r") as h:
        lat, lon = h["latitude"][:], h["longitude"][:]
        (r0, r1), (c0, c1), fcell = box_cells(lat, lon, field["fetch_box"], field["lat"], field["lon"])
        p = h["precip"]
        attrs = {k: _text(v) for k, v in p.attrs.items() if k not in ("DIMENSION_LIST", "REFERENCE_LIST")
                 and not k.startswith("_Netcdf4")}
        raw_attrs = g.describe_raw_attrs(attrs)
        print(f"CHIRPS {year} raw attributes (precip): {json.dumps(raw_attrs, default=str)}", flush=True)
        if attrs.get("units") != "mm/day":
            raise g.DataGuardError(f"CHIRPS precip units are '{attrs.get('units')}', expected mm/day")
        if raw_attrs["scale_factor"] != "ABSENT" or raw_attrs["add_offset"] != "ABSENT":
            raise g.DataGuardError("CHIRPS precip has a scale_factor or add_offset: the reader does not apply them")
        raw = p[:, r0:r1 + 1, c0:c1 + 1]
        days = days_from_time(h["time"][:], _text(h["time"].attrs["units"]))
    want = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    if len(days) != len(want) or (days != want).any():
        raise g.DataGuardError(f"CHIRPS {year}: the time axis is not every day of the year ({len(days)} days)")
    fills = [x for k in ("_FillValue", "missing_value") for x in np.ravel([attrs.get(k, [])]) if x is not None]
    vals, n_fill = clean_values(raw, fills)
    return {"days": days, "values": vals, "lat": lat[r0:r1 + 1], "lon": lon[c0:c1 + 1], "field_cell": fcell,
            "attrs": attrs, "raw_attrs": raw_attrs, "fills": n_fill, "http": rf.stats()}


def cache_path(raw_dir, year):
    return Path(raw_dir) / f"rnl_{year}.npz"


def save_year(raw_dir, year, r):
    raw_dir.mkdir(parents=True, exist_ok=True)
    tmp = raw_dir / f"rnl_{year}.part.npz"
    np.savez(tmp, days=r["days"].strftime("%Y-%m-%d").to_numpy().astype("U10"), values=r["values"], lat=r["lat"], lon=r["lon"],
             field_cell=np.array(r["field_cell"]),
             meta=json.dumps({"raw_attrs": r["raw_attrs"], "attrs": r["attrs"], "fills": r["fills"], "http": r["http"]},
                             default=str))
    tmp.replace(cache_path(raw_dir, year))


def load_year(raw_dir, year):
    z = np.load(cache_path(raw_dir, year), allow_pickle=False)
    return {"days": pd.DatetimeIndex(z["days"]), "values": z["values"], "lat": z["lat"], "lon": z["lon"],
            "field_cell": tuple(int(x) for x in z["field_cell"]), **json.loads(str(z["meta"]))}


def build(field, data_dir, years_wanted, stopped=None):
    """chirps.parquet and the card from the cached years."""
    from pipeline.fetch import guards as g
    raw_dir = Path(data_dir) / "raw" / "chirps" / field["id"]
    have = [y for y in years_wanted if cache_path(raw_dir, y).exists()]
    if not have:
        raise RuntimeError(f"no cached CHIRPS year in {raw_dir}")
    rows, fills, http, first = [], 0, {"requests": 0, "retries": 0, "bytes": 0}, None
    for y in sorted(have):
        r = load_year(raw_dir, y)
        first = first or r
        fr, fc = field_cell(r["lat"], r["lon"], field["lat"], field["lon"])      # the field as it is now
        box_mean = np.nanmean(r["values"].reshape(len(r["days"]), -1), axis=1)
        rows.append(pd.DataFrame({"date": r["days"], "rain_mm": r["values"][:, fr, fc], "rain_box_mean_mm": box_mean}))
        fills += int(r["fills"])
        for k in http:
            http[k] += int(r["http"].get(k, 0))
    df = pd.concat(rows, ignore_index=True)
    out = Path(data_dir) / "clean" / field["id"] / "chirps.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    missing = [y for y in years_wanted if y not in have]
    fr, fc = field_cell(first["lat"], first["lon"], field["lat"], field["lon"])
    card = g.make_card(
        dataset="chirps", product="CHIRPS v3.0 daily final, rnl (ERA5-disaggregated)", version="3.0",
        variable="precip", units_in="mm/day", units_out="rain_mm (mm per UTC calendar day)", scale_factor=None,
        fill_values_removed={"-9999 (_FillValue / missing_value)": fills}, quality_flags_used="none (the product has none)",
        records_dropped=int(df["rain_mm"].isna().sum()),
        date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone=("UTC calendar-day labels: 'A CHIRPS3 daily value labelled with date D therefore uses the "
                   "disaggregation information for approximately 00:00 UTC on D to 00:00 UTC on D+1' (CHIRPS v3 daily "
                   "README); station inputs keep their own reporting windows"),
        pixel_count=int(first["values"].shape[1] * first["values"].shape[2]),
        source="Climate Hazards Center (UC Santa Barbara), CHIRPS v3.0 daily final rnl, public domain, doi:10.15780/G2JQ0P",
        resolution="0.05 deg (about 5.5 km); the field's cell and the mean of the cells overlapping the fetch box",
        raw_attrs={"precip": first["raw_attrs"]},
        location={"box_cells_lat": [float(x) for x in first["lat"]], "box_cells_lon": [float(x) for x in first["lon"]],
                  "field_cell_centre": [float(first["lat"][fr]), float(first["lon"][fc])]},
        notes=(f"A cross-check on GPM only (rain check B; owner's go 2026-11-13), never the twin's rain. Years cached: "
               f"{sorted(have)}; years not fetched: {missing or 'none'}"
               + (f" (stopped: {stopped})" if stopped else "") + f". HTTP: {http['requests']} requests, "
               f"{http['retries']} retries (429/5xx), {http['bytes'] / 1e6:.0f} MB."))
    return {"table": out, "card": g.write_card(card, Path(data_dir) / "cards" / field["id"]), "years": sorted(have),
            "missing": missing}


def fetch(field, data_dir, years, deadline=None):
    from pipeline.fetch.rangefile import DeadlineReached
    raw_dir = Path(data_dir) / "raw" / "chirps" / field["id"]
    stopped = None
    for y in year_order(min(years), max(years)):
        if y not in years or cache_path(raw_dir, y).exists():
            continue
        if deadline is not None and time.time() >= deadline:
            stopped = "deadline reached before the next year"
            break
        t0 = time.time()
        try:
            r = read_year(y, field, deadline=deadline)
        except DeadlineReached:
            stopped = f"deadline reached while reading {y} (that year not kept)"
            break
        save_year(raw_dir, y, r)
        print(f"CHIRPS {y}: {np.nansum(r['values'][:, r['field_cell'][0], r['field_cell'][1]]):.0f} mm in the field's cell; "
              f"{r['http']['requests']} requests, {r['http']['retries']} retries, {r['http']['bytes'] / 1e6:.0f} MB, "
              f"{time.time() - t0:.0f} s", flush=True)
    return stopped


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--years", default="2001-2025")
    ap.add_argument("--deadline", default=None, help="ISO time with offset, e.g. 2026-11-14T08:00:00+05:45")
    ap.add_argument("--from-cache", action="store_true")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    y0, _, y1 = a.years.partition("-")
    years = list(range(int(y0), int(y1 or y0) + 1))
    deadline = pd.Timestamp(a.deadline).timestamp() if a.deadline else None
    stopped = None if a.from_cache else fetch(field, REPO / "data", years, deadline)
    r = build(field, REPO / "data", years, stopped)
    if r["years"]:
        ensure_credit(REPO / "records" / "credits.txt",
                      f"- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; "
                      f"doi:10.15780/G2JQ0P), the cells overlapping field `{field['id']}`'s fetch box, "
                      f"{min(r['years'])}-{max(r['years'])}"
                      + (f" without {r['missing']}" if r["missing"] else "")
                      + f", fetched {pd.Timestamp.now().date()} by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)")
    print(f"years cached {r['years']}; missing {r['missing'] or 'none'}" + (f"; STOPPED: {stopped}" if stopped else "")
          + f"\n-> {r['table']}\n-> {r['card']}")
    return 3 if r["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
