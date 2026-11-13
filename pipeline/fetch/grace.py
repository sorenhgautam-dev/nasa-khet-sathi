"""GRACE/GRACE-FO JPL mascon CRI RL06.3 v4 (TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4, decision D5):
monthly liquid-water-equivalent thickness for the grid cell holding the field (diary.groundwater, D7).

    .venv/bin/python -m pipeline.fetch.grace --field demo

One global netCDF file (44 MB) via earthaccess; read with h5py. The 0.5-degree grid carries 3-degree
equal-area mascons (file attribute), so the value is regional context, far larger than any field or the
fetch box (the whole box lies in one 0.5-degree cell). The CRI filter is already applied.

Scale factor (owner, 2026-11-12, REVIEW_NOTES M4): the UNSCALED series and trend are the main numbers. The
file's gridded CRI scale factor is recorded in the card with its value at the cell, and is NOT applied:
the factor is CLM-based (land hydrology) and the mascon includes glaciers and snow; no source was found
for applying it here. The trend it would give is written beside it, for the record only.
Writes data/clean/<field>/grace.parquet (unscaled) and the data card.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
EPOCH = pd.Timestamp("2002-01-01")


def _text(v):
    return v.decode() if isinstance(v, bytes) else str(v)


def cell_index(lat, lon, lat_bounds, lon_bounds):
    lon360 = lon % 360
    i = np.nonzero((lat_bounds[:, 0] <= lat) & (lat < lat_bounds[:, 1]))[0]
    j = np.nonzero((lon_bounds[:, 0] <= lon360) & (lon360 < lon_bounds[:, 1]))[0]
    if len(i) != 1 or len(j) != 1:
        raise ValueError(f"no unique GRACE grid cell for {lat}, {lon}")
    return int(i[0]), int(j[0])


def shared_file(raw_root, field_id, pattern):
    """A global file (one file covers every field) under raw_root/<field_id>/, else the same file already held for
    another field under raw_root/<other>/ (build step 11: never downloaded twice). None if no field holds it."""
    raw_root = Path(raw_root)
    own = sorted((raw_root / field_id).glob(pattern))
    if own:
        return own[-1]
    held = sorted(f for d in sorted(raw_root.glob("*")) if d.is_dir() for f in d.glob(pattern))
    return held[-1] if held else None


def series(time_days, lwe, unc, fill, valid):
    lwe, unc = np.where(lwe == fill, np.nan, lwe), np.where(unc == fill, np.nan, unc)
    bad = np.isfinite(lwe) & ((lwe < valid[0]) | (lwe > valid[1]))
    if bad.any():
        raise ValueError(f"{int(bad.sum())} value(s) outside the product's valid range {valid}")
    dates = EPOCH + pd.to_timedelta(np.asarray(time_days, dtype=float) * 86400, unit="s")
    return pd.DataFrame({"date": dates, "lwe_thickness_cm": lwe, "uncertainty_cm": unc})


SCALE_NOT_APPLIED = ("not applied (owner, 2026-11-12): the factor is CLM-based (land hydrology) and the mascon "
                     "includes glaciers and snow; no source was found for applying it here")


def linear_trend_cm_per_year(df, col="lwe_thickness_cm"):
    """Ordinary least-squares slope of the monthly series in cm per year (gaps skipped, never filled). For the
    card only: the trend rule and confidence for diary.groundwater are set at step 6 (D7)."""
    ok = df[col].notna()
    years = (df.loc[ok, "date"] - df.loc[ok, "date"].iloc[0]).dt.total_seconds() / (365.25 * 86400)
    return float(np.polyfit(years.to_numpy(), df.loc[ok, col].to_numpy(dtype=float), 1)[0])


def scale_factor_record(factor, trend_cm_per_year=None):
    """REVIEW_NOTES M4: the CRI scale factor at the cell, recorded and never applied."""
    rec = {"value": float(factor), "applied": False, "reason": SCALE_NOT_APPLIED,
           "file_description": "Gridded scale factors to be used with mascon solution that has the CRI filter "
                               "applied; based on CLM data from 2002-2009"}
    if trend_cm_per_year is not None:
        rec["trend_if_applied_cm_per_year"] = float(trend_cm_per_year) * float(factor)
    return rec


def fetch(field, data_dir=REPO / "data", rules=None):
    import earthaccess
    import h5py

    from pipeline.fetch import guards as g

    data_dir = Path(data_dir)
    raw = data_dir / "raw" / "grace" / field["id"]
    raw.mkdir(parents=True, exist_ok=True)
    nc = sorted(raw.glob("GRCTellus.JPL.*.nc"))
    shared = None if nc else shared_file(raw.parent, field["id"], "GRCTellus.JPL.*.nc")
    if shared is not None:                                 # the global file held for another field (build step 11)
        nc = [shared]
    if not nc:
        earthaccess.login(strategy="netrc", persist=False)
        gr = earthaccess.search_data(short_name="TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4")
        earthaccess.download(gr, local_path=str(raw), threads=1)
        nc = sorted(raw.glob("GRCTellus.JPL.*.nc"))
    with h5py.File(nc[-1], "r") as h:
        def attrs(v):
            return {k: (v.attrs[k].decode() if isinstance(v.attrs[k], bytes) else np.asarray(v.attrs[k]).tolist())
                    for k in v.attrs if k not in ("DIMENSION_LIST", "REFERENCE_LIST", "CLASS", "NAME")
                    and not k.startswith("_Netcdf4")}
        raw_attrs = {"lwe_thickness": attrs(h["lwe_thickness"]), "uncertainty": attrs(h["uncertainty"]),
                     "time": attrs(h["time"]), "grid": _text(h.attrs["geospatial_lat_resolution"])}
        print("raw attributes:", json.dumps(raw_attrs, default=str)[:900])
        print("rule 12a, lwe_thickness:", json.dumps(g.describe_raw_attrs(raw_attrs["lwe_thickness"]), default=str))
        i, j = cell_index(field["lat"], field["lon"], h["lat_bounds"][:], h["lon_bounds"][:])
        fill = float(np.ravel(raw_attrs["lwe_thickness"]["_FillValue"])[0])
        valid = (float(np.ravel(raw_attrs["lwe_thickness"]["valid_min"])[0]),
                 float(np.ravel(raw_attrs["lwe_thickness"]["valid_max"])[0]))
        df = series(h["time"][:], h["lwe_thickness"][:, i, j], h["uncertainty"][:, i, j], fill, valid)
        cell = {"lat_bounds": h["lat_bounds"][i].tolist(), "lon_bounds": h["lon_bounds"][j].tolist(),
                "mascon_ID": float(h["mascon_ID"][i, j]), "land_mask": float(h["land_mask"][i, j])}
        factor = float(h["scale_factor"][i, j])
    from pipeline.fetch.rules import load_rules
    rules = rules or load_rules()
    trend = linear_trend_cm_per_year(df)
    first, last = df.loc[df["lwe_thickness_cm"].notna(), "date"].agg(["min", "max"])
    cell["trend_unscaled_cm_per_year"] = trend
    cell["trend_method"] = (f"ordinary least squares over the monthly unscaled series {first.date()} to {last.date()} "
                            "(gaps skipped); the D7 trend rule and confidence are set at step 6")
    cell["cri_scale_factor"] = scale_factor_record(factor, trend)
    out = data_dir / "clean" / field["id"] / "grace.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    card = g.make_card(
        dataset="grace", product="JPL GRACE and GRACE-FO mascon CRI", version="RL06.3Mv04 (TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4)",
        variable=["lwe_thickness_cm (unscaled; the CRI scale factor is not applied)", "uncertainty_cm"],
        units_in="cm", units_out="cm",
        scale_factor=None, fill_values_removed={str(fill): int(df["lwe_thickness_cm"].isna().sum())},
        quality_flags_used="none in the file; 1-sigma uncertainty kept per month (per 3-degree mascon)",
        records_dropped=0, date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone="UTC (monthly solutions; date = middle of each solution's time bounds)", pixel_count=1,
        source="Wiese, Yuan, Boening, Landerer & Watkins, JPL GRACE and GRACE-FO Mascon Ocean, Ice, and Hydrology Equivalent Water Height CRI Filtered RL06.3Mv04, PO.DAAC, CMR C3195527175-POCLOUD",
        resolution="0.5 deg grid; native resolution 3-degree equal-area mascons (regional, far larger than the field)",
        raw_attrs=raw_attrs, location={"field": [field["lat"], field["lon"]], "cell": cell},
        notes=(f"{len(df)} monthly solutions, {int(df['lwe_thickness_cm'].isna().sum())} without a value; the "
               "GRACE / GRACE-FO gap (mid-2017 to mid-2018) is missing months, not fills. Anomaly relative to the "
               f"product's own baseline. Unscaled trend {trend:+.3f} cm/yr (OLS, for the record; the D7 rule is step 6). "
               f"A CRI scale factor exists ({factor:.4f} at this cell) but is {SCALE_NOT_APPLIED}; with it the trend "
               f"would be {trend * factor:+.3f} cm/yr. CAVEAT: " + rules["groundwater"]["caveat"]
               + (f" File: the global file already held for another field, {shared.relative_to(data_dir)} (not downloaded again)."
                  if shared is not None else "")))
    return {"table": out, "card": g.write_card(card, data_dir / "cards" / field["id"]), "df": df, "cell": cell}


def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    r = fetch(load_field(a.field))
    d = r["df"]
    print(f"{len(d)} months {d['date'].min().date()} to {d['date'].max().date()}; cell {r['cell']}\n"
          f"lwe_thickness_cm: min {d['lwe_thickness_cm'].min():.1f}, max {d['lwe_thickness_cm'].max():.1f}\n"
          f"trend (unscaled, OLS) {r['cell']['trend_unscaled_cm_per_year']:+.3f} cm/yr; with the CRI factor (not applied) "
          f"{r['cell']['cri_scale_factor']['trend_if_applied_cm_per_year']:+.3f} cm/yr\n-> {r['table']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
