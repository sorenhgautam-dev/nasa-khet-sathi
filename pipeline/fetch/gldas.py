"""GLDAS-2.1 Noah land-surface model, monthly, 0.25 degree (GLDAS_NOAH025_M v2.1): a CHECK on the twin only (owner,
2026-11-14; VALIDATION 4.2d). Model-based: Noah 3.6 forced with GDAS, AGRMET radiation and GPCP v1.3 rain (the
files' own `source` attribute). It never feeds the twin and no number shown to farmers uses it.

    .venv/bin/python -m pipeline.fetch.gldas --field demo [--workers 4]
    .venv/bin/python -m pipeline.fetch.gldas --field demo --from-cache      # rebuild the table and card, no network

Each month is one small DAP4 subset (the 3 x 3 cells around the field's cell, the variables below) from NASA
Earthdata Cloud OPeNDAP (GES DISC's own Hyrax for GLDAS answered "410 Service Retired" on 2026-11-14; the cloud
granules have DMR++ files). Login: ~/.netrc via Earthdata Login redirects. Cached as netCDF-4 in
data/raw/gldas/<field>/, so reruns resume; failures in failures.json and every missing month listed (exit 1).
Writes data/clean/<field>/gldas.parquet (one row per month, the field's cell, plus the 3 x 3 mean of two columns)
and data/cards/<field>/gldas.json.

Units (the files' own `units` attributes, checked on every read): soil moisture kg m-2 per layer (= mm of water;
divided by the layer's thickness in mm it is m3/m3), Evap_tavg and Rainf_f_tavg kg m-2 s-1 (x 86,400 = mm/day; a
monthly file holds the month's mean rate), PotEvap_tavg, ESoil_tavg, Tveg_tavg, ECanop_tavg W m-2 (latent-heat
fluxes: / 2.45 MJ/kg x 86,400 s = mm/day, FAO-56's latent heat). Noah's potential evaporation is a Penman-type
potential evaporation of the model's own surface, not FAO-56's grass-reference ET0: it is the closest GLDAS has.
"""
import argparse
import datetime as dt
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd

from pipeline.fetch import guards as g

REPO = Path(__file__).resolve().parents[2]
SHORT_NAME, VERSION = "GLDAS_NOAH025_M", "2.1"
COLLECTION = "C1342986036-GES_DISC"            # CMR, 2026-11-14
CLOUD_OPENDAP = f"https://opendap.earthdata.nasa.gov/collections/{COLLECTION}/granules/"
RES, LAT0, LON0, NLAT, NLON = 0.25, -59.875, -179.875, 600, 1440   # the files' own lat and lon (DMR, 2026-11-14)
LAYER_MM = {"SoilMoi0_10cm_inst": 100.0, "SoilMoi10_40cm_inst": 300.0, "SoilMoi40_100cm_inst": 600.0,
            "SoilMoi100_200cm_inst": 1000.0}
FLUX = ["Evap_tavg", "Rainf_f_tavg"]                                  # kg m-2 s-1
ENERGY = ["PotEvap_tavg", "ESoil_tavg", "Tveg_tavg", "ECanop_tavg"]   # W m-2
VARIABLES = list(LAYER_MM) + ["RootMoist_inst"] + FLUX + ENERGY
UNITS_IN = {**{v: "kg m-2" for v in list(LAYER_MM) + ["RootMoist_inst"]}, **{v: "kg m-2 s-1" for v in FLUX},
            **{v: "W m-2" for v in ENERGY}}
LAMBDA_J_KG = 2.45e6        # FAO-56 (Allen et al. 1998) ch. 3, eq. 20 and Annex 3: latent heat of vaporization 2.45 MJ/kg
SECONDS_PER_DAY = 86400.0
FLUX_LIMIT_MM_DAY = 500.0   # golden rule 12's daily rain bound, applied to the size of every water flux (a unit check)
OUT_NAMES = {"Evap_tavg": "et", "Rainf_f_tavg": "rain", "PotEvap_tavg": "pet", "ESoil_tavg": "esoil",
             "Tveg_tavg": "tveg", "ECanop_tavg": "ecanop"}


def cell_index(lat, lon):
    """(row, col) of the 0.25-degree cell holding a point."""
    j, i = math.floor((lat - (LAT0 - RES / 2)) / RES + 1e-9), math.floor((lon - (LON0 - RES / 2)) / RES + 1e-9)
    if not (0 <= j < NLAT and 0 <= i < NLON):
        raise ValueError(f"point {lat}, {lon} lies outside the GLDAS grid")
    return j, i


def cell_centre(j, i):
    return round(LAT0 + RES * j, 4), round(LON0 + RES * i, 4)


def constraint(cell, variables=VARIABLES):
    """DAP4 constraint for the 3 x 3 cells around `cell`, one time step."""
    j, i = cell
    rows, cols = f"[{j - 1}:1:{j + 1}]", f"[{i - 1}:1:{i + 1}]"
    return ";".join([f"/{v}[0:1:0]{rows}{cols}" for v in variables] + [f"/lat{rows}", f"/lon{cols}", "/time", "/time_bnds"])


def layer_theta(kg_m2, var):
    return float(kg_m2) / LAYER_MM[var]


def flux_mm_day(kg_m2_s):
    return float(kg_m2_s) * SECONDS_PER_DAY


def energy_mm_day(w_m2):
    return float(w_m2) * SECONDS_PER_DAY / LAMBDA_J_KG


def _text(v):
    v = np.ravel(v)[0] if isinstance(v, np.ndarray) else v
    return v.decode() if isinstance(v, bytes) else str(v)


def _check_flux(x, name):
    if not np.isfinite(x) or abs(x) > FLUX_LIMIT_MM_DAY:
        raise g.DataGuardError(f"{name} = {x} mm/day: outside +-{FLUX_LIMIT_MM_DAY} (unit check). Not clipped.")


def read_month(path, cell, expect_month=None):
    """One cached subset -> one row: the field's cell converted (and the 3 x 3 mean of theta_0_100 and ET). Fails
    loudly on wrong units, a shifted grid, a fill in the field's cell, a value outside rule 12, or a file whose own
    time_bnds is not `expect_month` ('2001-02'; 2026-11-14: under parallel requests the cloud OPeNDAP answered 3 of
    300 months with another month's granule)."""
    import h5py
    want_lat = [cell_centre(cell[0] + k, 0)[0] for k in (-1, 0, 1)]
    want_lon = [cell_centre(0, cell[1] + k)[1] for k in (-1, 0, 1)]
    with h5py.File(path, "r") as h:
        lat, lon = np.asarray(h["lat"][:], float), np.asarray(h["lon"][:], float)
        if len(lat) != 3 or len(lon) != 3 or np.abs(lat - want_lat).max() > 1e-3 or np.abs(lon - want_lon).max() > 1e-3:
            raise ValueError(f"subset grid lat {lat.tolist()} lon {lon.tolist()} is not the 3 x 3 around {cell}")
        t0, t1 = (float(x) for x in np.ravel(h["time_bnds"][:])[:2])
        raw, fills = {}, {}
        for v in VARIABLES:
            units = _text(h[v].attrs.get("units", b""))
            if units != UNITS_IN[v]:
                raise g.DataGuardError(f"{v}: units '{units}', expected '{UNITS_IN[v]}'")
            fv = h[v].attrs.get("_FillValue", np.array([-9999.0], dtype="f4"))
            a, n = g.mask_fill(np.asarray(h[v][0]), list(np.ravel(fv)))
            if np.isnan(a[1, 1]):
                raise g.DataGuardError(f"{v}: fill in the field's cell ({path})")
            raw[v], fills[v] = a, n
    month = pd.Timestamp("2000-01-01") + pd.Timedelta(t0, unit="D")
    if month.day != 1 or month.hour != 0:
        raise ValueError(f"{path}: time_bnds start {month} is not the first of a month")
    if expect_month is not None and month.strftime("%Y-%m") != expect_month:
        raise g.DataGuardError(f"{path}: the file holds {month.strftime('%Y-%m')}, not {expect_month}")
    days = t1 - t0
    row = {"month": month, "days": int(round(days))}
    layers = {"SoilMoi0_10cm_inst": "0_10cm", "SoilMoi10_40cm_inst": "10_40cm", "SoilMoi40_100cm_inst": "40_100cm",
              "SoilMoi100_200cm_inst": "100_200cm"}
    for v, tag in layers.items():
        row[f"sm_{tag}_mm"] = float(raw[v][1, 1])
        row[f"theta_{tag}_m3m3"] = layer_theta(raw[v][1, 1], v)
    top = ["SoilMoi0_10cm_inst", "SoilMoi10_40cm_inst", "SoilMoi40_100cm_inst"]
    row["theta_0_100cm_m3m3"] = sum(float(raw[v][1, 1]) for v in top) / 1000.0
    row["rootzone_mm"] = float(raw["RootMoist_inst"][1, 1])
    for v in FLUX:
        row[f"{OUT_NAMES[v]}_mm_day"] = flux_mm_day(raw[v][1, 1])
    for v in ENERGY:
        row[f"{OUT_NAMES[v]}_mm_day"] = energy_mm_day(raw[v][1, 1])
    row["et_mm"] = row["et_mm_day"] * days
    row["pet_mm"] = row["pet_mm_day"] * days
    nb = sum(raw[v] for v in top) / 1000.0
    row["theta_0_100cm_3x3_m3m3"] = float(np.nanmean(nb))
    row["et_3x3_mm_day"] = float(np.nanmean(raw["Evap_tavg"])) * SECONDS_PER_DAY
    row["fills_3x3"] = int(sum(fills.values()))
    g.check_table(pd.DataFrame([row]), {**{c: "theta_m3m3" for c in row if c.startswith("theta_")}, "rain_mm_day": "rain_mm"})
    for c in ("et_mm_day", "pet_mm_day", "esoil_mm_day", "tveg_mm_day", "ecanop_mm_day"):
        _check_flux(row[c], c)
    for c in ("sm_0_10cm_mm", "sm_10_40cm_mm", "sm_40_100cm_mm", "sm_100_200cm_mm", "rootzone_mm"):
        g.assert_nonnegative([row[c]], c)
    return row


def missing_months(have, first, last):
    want = pd.period_range(first, last, freq="M")
    got = {pd.Timestamp(t).to_period("M") for t in have}
    return [str(p) for p in want if p not in got]


def raw_attributes(path):
    """Golden rule 12a: each variable's units, scale_factor, add_offset, _FillValue, valid_range (and the file's
    vmin/vmax, which are that month's global extremes, not a documented valid range)."""
    import h5py
    out = {}
    with h5py.File(path, "r") as h:
        for v in VARIABLES:
            a = {k: (_text(x) if isinstance(x, (bytes, np.bytes_)) or (isinstance(x, np.ndarray) and x.dtype.kind == "S")
                     else (np.ravel(x)[0].item() if isinstance(x, np.ndarray) else x))
                 for k, x in h[v].attrs.items() if k not in ("DIMENSION_LIST", "REFERENCE_LIST") and not k.startswith("_Netcdf4")}
            out[v] = {**g.describe_raw_attrs(a), **{k: a[k] for k in ("vmin", "vmax", "long_name") if k in a}}
    return out


def month_of(granule_ur):
    """'GLDAS_NOAH025_M.2.1:GLDAS_NOAH025_M.A200101.021.nc4' -> '2001-01'."""
    tag = granule_ur.split(".A")[1][:6]
    return f"{tag[:4]}-{tag[4:]}"


def cache_name(month):
    return f"GLDAS_NOAH025_M.A{month.replace('-', '')}.021.sub.nc4"


def month_of_cache(path):
    """'.../GLDAS_NOAH025_M.A200102.021.sub.nc4' -> '2001-02'."""
    tag = Path(path).name.split(".A")[1][:6]
    return f"{tag[:4]}-{tag[4:]}"


def _get(session, url, cell, dest):
    import requests
    session = session or requests.Session()      # one session per request: a shared one is not thread-safe
    r = session.get(url + ".dap.nc4", params={"dap4.ce": constraint(cell)}, timeout=180)
    if r.status_code != 200 or not r.content.startswith(b"\x89HDF"):
        raise RuntimeError(f"HTTP {r.status_code}, {len(r.content)} bytes, not a netCDF-4 file")
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(r.content)
    try:
        read_month(tmp, cell, expect_month=month_of_cache(dest))      # the granule asked for, or no file
    except Exception:
        tmp.unlink()
        raise
    tmp.replace(dest)


def granule_urls(start, end):
    import earthaccess
    earthaccess.login(strategy="netrc", persist=False)
    out = {}
    for x in earthaccess.search_data(short_name=SHORT_NAME, version=VERSION, temporal=(start, end)):
        ur = x["umm"]["GranuleUR"]
        links = [u["URL"] for u in x["umm"].get("RelatedUrls", []) if u["URL"].startswith(CLOUD_OPENDAP)]
        out[month_of(ur)] = links[0] if links else CLOUD_OPENDAP + quote(ur, safe="")
    return out


def fetch(field, workers=4, data_dir=REPO / "data", start="2001-01-01", end="2025-12-31"):
    raw = Path(data_dir) / "raw" / "gldas" / field["id"]
    raw.mkdir(parents=True, exist_ok=True)
    cell = cell_index(field["lat"], field["lon"])
    urls = granule_urls(start, end)
    todo = [(m, u) for m, u in sorted(urls.items()) if not (raw / cache_name(m)).exists()]
    print(f"GLDAS: {len(urls)} month(s) in CMR, {len(todo)} to fetch", flush=True)
    fails = {}                                   # Earthdata Login credentials from ~/.netrc, one session per request
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(_get, None, u, cell, raw / cache_name(m)): m for m, u in todo}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:                  # recorded and retried on the next run, never dropped silently
                fails[futs[f]] = f"{type(e).__name__}: {str(e)[:160]}"
            if n % 50 == 0:
                print(f"GLDAS: {n}/{len(todo)} fetched, {len(fails)} failed", flush=True)
    (raw / "failures.json").write_text(json.dumps(fails, indent=1) + "\n")
    return build(field, data_dir, start, end, failures=fails, listed=len(urls))


def build(field, data_dir=REPO / "data", start="2001-01-01", end="2025-12-31", failures=None, listed=None):
    data_dir = Path(data_dir)
    raw = data_dir / "raw" / "gldas" / field["id"]
    cell = cell_index(field["lat"], field["lon"])
    files = sorted(raw.glob("GLDAS_NOAH025_M.A*.sub.nc4"))
    if not files:
        raise RuntimeError(f"no cached GLDAS files in {raw}")
    attrs = raw_attributes(files[0])
    for v, a in attrs.items():
        print(f"[gldas raw attrs] {v}: {a}")
    import h5py
    with h5py.File(files[0], "r") as h:
        source = _text(h.attrs.get("source", b"ABSENT"))
    rows = [read_month(f, cell, expect_month=month_of_cache(f)) for f in files]
    df = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)
    df = df[(df["month"] >= pd.Timestamp(start)) & (df["month"] <= pd.Timestamp(end))].reset_index(drop=True)
    if df["month"].duplicated().any():
        raise g.DataGuardError("repeated month in the GLDAS cache")
    missing = missing_months(df["month"], start[:7], end[:7])
    out = data_dir / "clean" / field["id"] / "gldas.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    lat_c, lon_c = cell_centre(*cell)
    card = g.make_card(
        dataset="gldas", product=f"{SHORT_NAME} (GLDAS-2.1 Noah land surface model L4 monthly 0.25 x 0.25 degree)",
        version=f"{VERSION} (CMR {COLLECTION})", variable=VARIABLES, units_in=UNITS_IN,
        units_out={"soil layers": "sm_<layer>_mm (kg m-2 = mm) and theta_<layer>_m3m3 (mm / layer thickness in mm); "
                                  "theta_0_100cm_m3m3 = (0-10 + 10-40 + 40-100 cm) / 1000 mm",
                   "Evap_tavg, Rainf_f_tavg": "x 86,400 -> mm/day (month's mean rate); et_mm = mm/day x days",
                   "PotEvap_tavg, ESoil_tavg, Tveg_tavg, ECanop_tavg": "W m-2 x 86,400 / 2.45e6 J/kg -> mm/day (FAO-56 latent heat)"},
        scale_factor=None,
        fill_values_removed={"_FillValue": -9999.0, "in the field's cell": 0, "in the 3 x 3 cells": int(df["fills_3x3"].sum())},
        quality_flags_used="none: the product has no quality layer (model output)",
        records_dropped={"months_listed_in_cmr": listed, "months_cached": len(files), "months_in_table": len(df),
                         "missing_months": missing, "failures": failures or {}},
        date_range=[str(df["month"].min().date()), str((df["month"].max() + pd.offsets.MonthEnd(0)).date())] if len(df) else [],
        time_zone="monthly means of the model's 3-hourly UTC steps (time_bnds: the calendar month in UTC)",
        pixel_count={"field_cell": 1, "fetched": "3 x 3 cells around it"},
        source=f"NASA GES DISC, {SHORT_NAME} v{VERSION} (Beaudoing & Rodell, NASA/GSFC/HSL), via Earthdata Cloud OPeNDAP; "
               f"model-based (file 'source': {source})",
        resolution="0.25 x 0.25 degree, monthly", raw_attrs=attrs,
        location={"cell": {"row": cell[0], "col": cell[1], "lat_centre": lat_c, "lon_centre": lon_c,
                           "bounds": [lon_c - RES / 2, lat_c - RES / 2, lon_c + RES / 2, lat_c + RES / 2]},
                  "field": {"lat": field["lat"], "lon": field["lon"]}},
        notes=("A check on the twin only (VALIDATION 4.2d); never the twin's input, never shown to farmers. Model output: "
               "Noah 3.6 forced with GDAS, AGRMET radiation and GPCP v1.3 daily rain, which is gauge-adjusted (GPCC), so it "
               "may share gauges with IMERG Final. Noah's potential evaporation is not FAO-56's grass-reference ET0. The "
               "whole fetch box lies in this one 0.25-degree cell (about 25 x 28 km: the eastern Kathmandu valley and the "
               "hills around it). vmin/vmax in raw_attrs are each file's global extremes, not a valid range, so rule 12's "
               "ranges are the hard limits (soil moisture 0 to 0.6 m3/m3, rain 0 to 500 mm/day; every other water flux "
               f"within +-{FLUX_LIMIT_MM_DAY:.0f} mm/day as a unit check)."),
        range_warnings={})
    card_path = g.write_card(card, data_dir / "cards" / field["id"])
    return {"table": out, "card": card_path, "rows": len(df), "missing": missing}


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--from-cache", action="store_true")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    r = build(field) if a.from_cache else fetch(field, workers=a.workers)
    ensure_credit(REPO / "CREDITS.md", f"- NASA GLDAS-2.1 Noah monthly 0.25 deg ({SHORT_NAME} v{VERSION}, GES DISC, "
                                       f"Earthdata Cloud OPeNDAP), soil moisture and evapotranspiration for the field's cell, "
                                       f"2001-2025, fetched {dt.date.today()} (check on the twin only)")
    print(f"{r['rows']} months -> {r['table']}; card {r['card']}; missing {r['missing']}")
    return 1 if r["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
