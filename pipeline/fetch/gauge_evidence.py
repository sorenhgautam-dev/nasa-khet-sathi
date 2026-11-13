"""The gauge evidence behind the 2017 rain break, made reproducible (VALIDATION 3.9b; REVIEW_2 M6, 2026-11-13).

    .venv/bin/python -m pipeline.fetch.gauge_evidence --field demo               # fetch what is missing, then build
    .venv/bin/python -m pipeline.fetch.gauge_evidence --field demo --from-cache  # build from the cached files only

Until this module the numbers in rules.yaml gpm_series.break_evidence (and on the site's method page) had been read
by hand by a research sub-agent. Two public sources, CHECKS ONLY (never the twin's rain):

1. GPM_3IMERGM V07 (monthly IMERG Final), `gaugeRelativeWeighting` (percent: the weight the gauge analysis has in
   the final estimate) and `precipitation` (mm/hr) for the 3 x 3 cells of 0.1 deg around the field's cell: OPeNDAP
   subsets from NASA GES DISC, as pipeline/fetch/gpm.py does for the daily files (Earthdata login in ~/.netrc).
2. GPCC Full Data Monthly Product V2022, 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD
   open data, no login), `numgauge` (stations in the box that month) and `precip` (mm/month) for the box holding the
   field, 2001-2020 (the product ends in 2020).

Writes data/clean/<field>/gauge_evidence.parquet (one row per month) and the data card, whose `summary` holds the
ranges quoted in rules.yaml. Raw files are cached in data/raw/gauge_evidence/<field>/.
"""
import argparse
import calendar
import gzip
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch import guards as g

REPO = Path(__file__).resolve().parents[2]
IMERG_HOSTS = ("https://gpm1.gesdisc.eosdis.nasa.gov/opendap/", "https://gpm2.gesdisc.eosdis.nasa.gov/opendap/")
IMERG_PATH = "GPM_L3/GPM_3IMERGM.07/{y}/3B-MO.MS.MRG.3IMERG.{y}{m:02d}01-S000000-E235959.{m:02d}.V07B.HDF5.nc4"
GPCC_URL = "https://opendata.dwd.de/climate_environment/GPCC/full_data_monthly_v2022/10/full_data_monthly_v2022_{a}_{b}_10.nc.gz"
GPCC_DECADES = ((2001, 2010), (2011, 2020))


def imerg_index(lon, lat):
    """(lon index, lat index) of the 0.1 deg IMERG cell holding the point (grid edges at -180 and -90)."""
    return int(np.floor((lon + 180.0) * 10.0 + 1e-9)), int(np.floor((lat + 90.0) * 10.0 + 1e-9))


def gpcc_box(lats, lons, lat, lon):
    """(lat index, lon index) of the 1 deg GPCC box holding the point; fails if the file does not reach it."""
    lats, lons = np.asarray(lats, float), np.asarray(lons, float)
    i, j = int(np.argmin(np.abs(lats - lat))), int(np.argmin(np.abs(lons - lon)))
    if abs(lats[i] - lat) > 0.5 or abs(lons[j] - lon) > 0.5:
        raise g.DataGuardError(f"the GPCC grid does not hold {lat} N, {lon} E (nearest box centre {lats[i]}, {lons[j]})")
    return i, j


def summarise(table, break_from, gpcc_before_years=6):
    """The ranges quoted as the break's evidence. table: one row per month ('YYYY-MM') with imerg_gauge_weight_pct
    (the field's cell) and gpcc_stations; break_from 'YYYY-MM'. Months without a value are left out."""
    t = table.copy()
    t["p"] = pd.PeriodIndex(t["month"], freq="M")
    brk = pd.Period(break_from, freq="M")
    w = t.dropna(subset=["imerg_gauge_weight_pct"])
    before, after = w[w["p"] < brk], w[w["p"] >= brk]
    yearly_after = after.groupby(after["p"].dt.year)["imerg_gauge_weight_pct"].mean()
    low = w[w["imerg_gauge_weight_pct"] < 90.0]
    n = t.dropna(subset=["gpcc_stations"])
    nb = n[(n["p"] < brk) & (n["p"] >= brk - 12 * gpcc_before_years)]
    na = n[n["p"] >= brk]
    return {"break_from": str(brk),
            "gauge_weight_before_pct": [round(float(before["imerg_gauge_weight_pct"].min()), 1), round(float(before["imerg_gauge_weight_pct"].max()), 1)],
            "gauge_weight_after_yearly_pct": [round(float(yearly_after.min()), 1), round(float(yearly_after.max()), 1)],
            "gauge_weight_after_monthly_pct": [round(float(after["imerg_gauge_weight_pct"].min()), 1), round(float(after["imerg_gauge_weight_pct"].max()), 1)],
            "gauge_weight_first_month_below_90": str(low["p"].min()) if len(low) else None,
            "gpcc_stations_before": round(float(nb["gpcc_stations"].mean()), 1) if len(nb) else None,
            "gpcc_stations_after": round(float(na["gpcc_stations"].mean()), 1) if len(na) else None,
            "gpcc_before_years": gpcc_before_years,
            "months": {"before": int(len(before)), "after": int(len(after))}}


def fetch_imerg(field, months, raw):
    """Download the missing monthly subsets (3 x 3 cells around the field). Returns the months that failed."""
    import requests
    i, j = imerg_index(field["lon"], field["lat"])
    q = (f"?gaugeRelativeWeighting[0:0][{i - 1}:{i + 1}][{j - 1}:{j + 1}],precipitation[0:0][{i - 1}:{i + 1}][{j - 1}:{j + 1}],"
         f"lon[{i - 1}:{i + 1}],lat[{j - 1}:{j + 1}]")
    out = raw / "imergm"
    out.mkdir(parents=True, exist_ok=True)
    s, failed = requests.Session(), []
    for k, (y, m) in enumerate(months):
        dest = out / f"{y}-{m:02d}.nc4"
        if dest.exists():
            continue
        ok = False
        for host in (IMERG_HOSTS[k % 2], IMERG_HOSTS[(k + 1) % 2]):
            try:
                r = s.get(host + IMERG_PATH.format(y=y, m=m) + q, timeout=120)
            except requests.RequestException:
                continue
            if r.status_code == 200 and r.content.startswith(b"\x89HDF"):
                dest.write_bytes(r.content)
                ok = True
                break
        if not ok:
            failed.append(f"{y}-{m:02d}")
        if k % 25 == 0:
            print(f"  IMERG monthly {y}-{m:02d} ({k + 1}/{len(months)}), failed so far {len(failed)}", flush=True)
    return failed


def fetch_gpcc(raw):
    import requests
    out = raw / "gpcc"
    out.mkdir(parents=True, exist_ok=True)
    for a, b in GPCC_DECADES:
        nc = out / f"full_data_monthly_v2022_{a}_{b}_10.nc"
        if nc.exists():
            continue
        gz = nc.with_suffix(".nc.gz")
        if not gz.exists():
            r = requests.get(GPCC_URL.format(a=a, b=b), timeout=600)
            r.raise_for_status()
            gz.write_bytes(r.content)
        with gzip.open(gz, "rb") as fi, open(nc, "wb") as fo:
            shutil.copyfileobj(fi, fo)


def read_imerg(path, i, j):
    """The field cell's gauge weight (%), the 3 x 3 range, and the month's rain (mm) from one cached subset."""
    import h5py
    y, m = (int(x) for x in Path(path).stem.split("-"))
    with h5py.File(path, "r") as h:
        lon, lat = np.asarray(h["lon"][:], float), np.asarray(h["lat"][:], float)
        a, b = int(np.argmin(np.abs(lon - (i / 10.0 - 180.0 + 0.05)))), int(np.argmin(np.abs(lat - (j / 10.0 - 90.0 + 0.05))))
        if abs(lon[a] - (i / 10.0 - 180.0 + 0.05)) > 0.01 or abs(lat[b] - (j / 10.0 - 90.0 + 0.05)) > 0.01:
            raise g.DataGuardError(f"{path}: the cached cells {lon.tolist()} x {lat.tolist()} do not hold the field's cell")
        gw, pr = h["gaugeRelativeWeighting"], h["precipitation"]
        attrs = {n: {k: (v.attrs[k].decode() if isinstance(v.attrs[k], bytes) else np.asarray(v.attrs[k]).tolist())
                     for k in ("units", "_FillValue", "scale_factor", "add_offset", "valid_range") if k in v.attrs}
                 for n, v in (("gaugeRelativeWeighting", gw), ("precipitation", pr))}
        wv, _ = g.mask_fill(np.asarray(gw[0], float), [float(np.asarray(gw.attrs["_FillValue"]).ravel()[0])] if "_FillValue" in gw.attrs else [])
        pv, _ = g.mask_fill(np.asarray(pr[0], float), [float(np.asarray(pr.attrs["_FillValue"]).ravel()[0])] if "_FillValue" in pr.attrs else [])
    if np.nanmin(wv) < 0 or np.nanmax(wv) > 100:
        raise g.DataGuardError(f"{path}: gauge weight outside 0-100%: {np.nanmin(wv)}..{np.nanmax(wv)}")
    hours = calendar.monthrange(y, m)[1] * 24
    return {"month": f"{y}-{m:02d}", "imerg_gauge_weight_pct": float(wv[a, b]), "imerg_gauge_weight_min_3x3_pct": float(np.nanmin(wv)),
            "imerg_gauge_weight_max_3x3_pct": float(np.nanmax(wv)), "imerg_monthly_rain_mm": float(pv[a, b]) * hours}, attrs


def read_gpcc(raw, field):
    from scipy.io import netcdf_file
    rows, attrs = [], {}
    for a, b in GPCC_DECADES:
        path = raw / "gpcc" / f"full_data_monthly_v2022_{a}_{b}_10.nc"
        if not path.exists():
            continue
        with netcdf_file(str(path), "r", mmap=False) as nc:
            i, j = gpcc_box(nc.variables["lat"][:], nc.variables["lon"][:], field["lat"], field["lon"])
            n = np.asarray(nc.variables["numgauge"][:, i, j], float)
            p = np.asarray(nc.variables["precip"][:, i, j], float)
            for name in ("numgauge", "precip"):
                v = nc.variables[name]
                attrs[name] = {k: (getattr(v, k).decode() if isinstance(getattr(v, k), bytes) else np.asarray(getattr(v, k)).tolist())
                               for k in ("units", "_FillValue", "missing_value", "long_name") if hasattr(v, k)}
            box = [float(nc.variables["lat"][i]), float(nc.variables["lon"][j])]
        months = pd.period_range(f"{a}-01", f"{b}-12", freq="M")
        if len(months) != len(n):
            raise g.DataGuardError(f"{path}: {len(n)} time steps for {len(months)} months")
        fill = [f for f in (attrs["precip"].get("_FillValue"), attrs["precip"].get("missing_value")) if f is not None]
        p, _ = g.mask_fill(p, [float(np.asarray(f).ravel()[0]) for f in fill])
        if np.nanmin(n) < 0 or np.nanmin(p) < 0 or np.nanmax(p) > 3000:
            raise g.DataGuardError(f"{path}: station count or monthly rain out of range")
        rows += [{"month": str(m), "gpcc_stations": float(x), "gpcc_rain_mm": float(y)} for m, x, y in zip(months, n, p)]
        attrs["box_centre_lat_lon"] = box
    return pd.DataFrame(rows), attrs


def build(field, rules, data_dir=REPO / "data", failed=()):
    raw = Path(data_dir) / "raw" / "gauge_evidence" / field["id"]
    i, j = imerg_index(field["lon"], field["lat"])
    rows, attrs = [], {}
    for f in sorted((raw / "imergm").glob("*.nc4")):
        row, attrs = read_imerg(f, i, j)
        rows.append(row)
    if not rows:
        raise g.DataGuardError(f"no IMERG monthly subsets under {raw / 'imergm'}")
    print(f"raw attributes (IMERG monthly): {attrs}")
    table = pd.DataFrame(rows)
    gpcc, gattrs = read_gpcc(raw, field)
    print(f"raw attributes (GPCC): {gattrs}")
    table = table.merge(gpcc, on="month", how="outer").sort_values("month").reset_index(drop=True) if len(gpcc) else table.assign(gpcc_stations=np.nan, gpcc_rain_mm=np.nan)
    brk = str(rules["gpm_series"]["correction_from"])[:7]
    summary = summarise(table, brk)
    out = Path(data_dir) / "clean" / field["id"] / "gauge_evidence.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out, index=False)
    have = table.dropna(subset=["imerg_gauge_weight_pct"])
    card = g.make_card(
        dataset="gauge_evidence", product="GPM_3IMERGM V07 (monthly IMERG Final) and GPCC Full Data Monthly V2022 (1.0 deg)", version="IMERG V07B; GPCC V2022",
        variable=["gaugeRelativeWeighting", "precipitation", "numgauge", "precip"],
        units_in="percent; mm/hr; stations per box; mm/month", units_out="percent, mm per month, stations per box (one row per month)",
        scale_factor="IMERG monthly precipitation mm/hr x hours in the month", fill_values_removed="masked by each file's _FillValue (none at these cells)",
        quality_flags_used="none: these ARE the quality information (how much gauge data stands behind IMERG's estimate)",
        records_dropped={"imerg_months_not_fetched": list(failed)},
        date_range=[str(table["month"].min()), str(table["month"].max())], time_zone="calendar months (UTC)",
        pixel_count={"imerg_cells": 9, "gpcc_boxes": 1}, source="NASA GES DISC OPeNDAP (GPM_3IMERGM.07); DWD open data (GPCC, doi:10.5676/DWD_GPCC/FD_M_V2022_100)",
        resolution="IMERG 0.1 deg (the field's cell and its 8 neighbours); GPCC 1.0 deg box " + str(gattrs.get("box_centre_lat_lon")),
        raw_attrs={"imerg": attrs, "gpcc": gattrs}, range_warnings={},
        summary={**summary, "imerg_months_with_a_value": int(len(have)), "imerg_months": [str(have["month"].min()), str(have["month"].max())]},
        notes="Checks only (VALIDATION 3.9b): the evidence that IMERG Final's gauge input around the field is lost from "
              f"{brk}. rules.yaml gpm_series.break_evidence quotes this card's summary.")
    card_path = g.write_card(card, Path(data_dir) / "cards" / field["id"])
    return {"table": out, "card": card_path, "summary": summary, "months": len(have)}


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.rules import load_rules
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--start", default="2001-01")
    ap.add_argument("--end", default="2025-09", help="last month to ask for (IMERG Final is published some months late)")
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    raw = REPO / "data" / "raw" / "gauge_evidence" / field["id"]
    failed = []
    if not a.from_cache:
        months = [(p.year, p.month) for p in pd.period_range(a.start, a.end, freq="M")]
        failed = fetch_imerg(field, months, raw)
        fetch_gpcc(raw)
    r = build(field, rules, failed=failed)
    ensure_credit(REPO / "CREDITS.md",
                  "- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the "
                  f"3 x 3 cells around field `{field['id']}`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, "
                  "doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched "
                  f"{pd.Timestamp.now().date()} by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)")
    print(f"{r['months']} IMERG months with a value; not fetched: {failed or 'none'}\nsummary: {r['summary']}\n-> {r['table']}\n-> {r['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
