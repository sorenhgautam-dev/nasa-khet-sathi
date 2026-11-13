"""SMAP soil moisture for a field: clean the AppEEARS area files (CLAUDE.md "Data sources"; REVIEW_2 Phase 3).

    .venv/bin/python -m pipeline.fetch.smap --field demo     # reads data/raw/appeears/<field>/smap_*

Reads what pipeline/fetch/appeears.py downloaded (never the network) and writes data/clean/<field>/smap.parquet,
one row per UTC day, and the data card. A CHECK ON THE TWIN ONLY (scripts/run_smap_check.py): no number shown to
farmers comes from SMAP.

- SPL4SMGP v008 (L4, model-assisted: NASA's land model with SMAP brightness temperatures assimilated; label it
  model-based): 3-hourly `sm_rootzone` (0-100 cm) and `sm_surface` (0-5 cm), m3/m3, valid 0 to 0.9 (file
  attributes). A day's value is the mean of its eight 3-hourly values (time stamps 01:30 ... 22:30 UTC); a day with
  fewer is left empty and counted.
- SPL3SMP_E v006 (L3, radiometer retrievals on the 9 km grid): `soil_moisture` (AM, about 06:00 local) and
  `soil_moisture_pm`, cm3/cm3, valid 0.02 to 0.5 (file attributes), with `retrieval_qual_flag`. Only retrievals of
  recommended quality are kept: flag value 0 or 8 (bit 0 clear). The lookup table AppEEARS ships with the files
  (...-retrieval-qual-flag-lookup.csv) reads, for values 7, 9 and 13, "Soil moisture retrieval doesn't have
  recommended quality". A kept value outside the product's valid range fails loudly (golden rule 12c).
- Grid: EASE-Grid 2.0 Global (EPSG:6933), 9 km cells; the cell whose centre is nearest the field, and the field
  must lie inside it. A 9 km cell is not the field: it mixes the valley floor, the city and the hills.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch import guards as g

REPO = Path(__file__).resolve().parents[2]
CELL_M = 9008.05
L4_STEPS_PER_DAY = 8


def ease2_cell(xs, ys, lon, lat):
    """(row, col) of the EASE-Grid 2.0 Global cell that holds the point; fails if the point is in none."""
    from rasterio.warp import transform
    x, y = transform("EPSG:4326", "EPSG:6933", [float(lon)], [float(lat)])
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    row, col = int(np.argmin(np.abs(ys - y[0]))), int(np.argmin(np.abs(xs - x[0])))
    if abs(ys[row] - y[0]) > CELL_M / 2 or abs(xs[col] - x[0]) > CELL_M / 2:
        raise g.DataGuardError(f"the point {lat} N, {lon} E lies outside every SMAP cell of this file "
                               f"(nearest centre {abs(ys[row] - y[0]):.0f} m north-south, {abs(xs[col] - x[0]):.0f} m east-west away)")
    return row, col


def recommended(flags):
    """True where retrieval_qual_flag is 0 or 8: "A retrieval_qual_flag value of either 0 or 8 indicates high-quality
    retrievals" (NSIDC, DATA_AUDIT 1.5; bit 0 clear = recommended quality, 8 = only the freeze/thaw retrieval failed)."""
    return np.isin(np.asarray(flags).astype(np.int64), (0, 8))


def clean_l3(values, flags, fill, valid_range):
    """(values with everything but recommended-quality retrievals set to NaN, counts of what was dropped)."""
    v = np.asarray(values, dtype=float).copy()
    is_fill = np.isclose(v, fill)
    rec = recommended(flags) & ~is_fill
    out_rng = ~is_fill & ((v < valid_range[0]) | (v > valid_range[1]))
    if (rec & out_rng).any():
        bad = v[rec & out_rng]
        raise g.DataGuardError(f"SMAP L3: {bad.size} recommended-quality value(s) outside the product's valid range "
                               f"{valid_range}: {bad[:5].tolist()}")
    counts = {"fill": int(is_fill.sum()), "not_recommended_quality": int((~rec & ~is_fill & ~out_rng).sum()),
              "not_recommended_and_out_of_range": int((~rec & out_rng).sum()), "kept": int(rec.sum())}
    v[~rec] = np.nan
    return v, counts


def daily_mean(times, values, steps_per_day=L4_STEPS_PER_DAY):
    """(mean per UTC day, number of days with fewer than steps_per_day values, which are left empty)."""
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(times))
    by_day = s.groupby(s.index.normalize())
    mean, n = by_day.mean(), by_day.count()
    mean[n < steps_per_day] = np.nan
    return mean, int((n < steps_per_day).sum())


def monthly_anomaly(daily):
    """Monthly means minus the mean of the same calendar month over the series (months with any missing day dropped)."""
    daily = daily.dropna()
    full = daily.groupby([daily.index.year, daily.index.month]).agg(["mean", "count"])
    days = pd.Series([pd.Period(f"{y}-{m:02d}").days_in_month for y, m in full.index], index=full.index)
    m = full["mean"][full["count"] == days]
    m.index = pd.PeriodIndex([pd.Period(f"{y}-{mo:02d}") for y, mo in m.index], freq="M")
    return m - m.groupby(m.index.month).transform("mean")


def _read(path, names):
    import h5py
    with h5py.File(path, "r") as h:
        t = pd.to_datetime(np.asarray(h["time"][:], dtype="int64"), unit="s", origin=pd.Timestamp("2000-01-01"))
        out = {"time": t, "xs": np.asarray(h["fakedim1"][:], float), "ys": np.asarray(h["fakedim0"][:], float), "attrs": {}}
        for key, name in names.items():
            v = h[name]
            out[key] = v[...]
            out["attrs"][name] = {a: (v.attrs[a].decode() if isinstance(v.attrs[a], bytes) else np.asarray(v.attrs[a]).tolist())
                                  for a in ("units", "_FillValue", "valid_min", "valid_max", "scale_factor", "add_offset")
                                  if a in v.attrs}
    return out


def _one(x):
    return float(np.asarray(x).ravel()[0])


def build(field, data_dir=REPO / "data"):
    raw = Path(data_dir) / "raw" / "appeears" / field["id"]
    clean_dir = Path(data_dir) / "clean" / field["id"]
    parts, raw_attrs, cell = {}, {}, None
    # ----- L4: 3-hourly, one folder per year -----
    l4_files = sorted(raw.glob("smap_l4_*/SPL4SMGP.008_*.nc"))
    if not l4_files:
        raise g.DataGuardError(f"no SMAP L4 files under {raw} (pipeline.fetch.appeears download)")
    rz, sf, incomplete = [], [], 0
    for f in l4_files:
        d = _read(f, {"rz": "Geophysical_Data_sm_rootzone", "sf": "Geophysical_Data_sm_surface"})
        cell = ease2_cell(d["xs"], d["ys"], field["lon"], field["lat"])
        raw_attrs.update(d["attrs"])
        print(f"{f.parent.name}: raw attributes {d['attrs']}")
        for key, acc in (("rz", rz), ("sf", sf)):
            a = d["attrs"]["Geophysical_Data_sm_rootzone" if key == "rz" else "Geophysical_Data_sm_surface"]
            v, _ = g.mask_fill(d[key][:, cell[0], cell[1]], [_one(a["_FillValue"])])
            g.assert_in_range(v, "theta_m3m3", f"smap_l4_{key}", valid_range=(_one(a["valid_min"]), _one(a["valid_max"])))
            mean, n_inc = daily_mean(d["time"], v)
            incomplete += n_inc if key == "rz" else 0
            acc.append(mean)
    parts["smap_l4_rootzone_m3m3"], parts["smap_l4_surface_m3m3"] = pd.concat(rz).sort_index(), pd.concat(sf).sort_index()
    # ----- L3: one retrieval a day at most, AM and PM -----
    l3_counts = {}
    for half, sm_name, fl_name in (("am", "Soil_Moisture_Retrieval_Data_AM_soil_moisture", "Soil_Moisture_Retrieval_Data_AM_retrieval_qual_flag"),
                                   ("pm", "Soil_Moisture_Retrieval_Data_PM_soil_moisture_pm", "Soil_Moisture_Retrieval_Data_PM_retrieval_qual_flag_pm")):
        f = next(iter(sorted((raw / f"smap_l3_{half}").glob("SPL3SMP_E.006_*.nc"))), None)
        if f is None:
            continue
        d = _read(f, {"sm": sm_name, "fl": fl_name})
        a = d["attrs"][sm_name]
        print(f"smap_l3_{half}: raw attributes {d['attrs']}")
        raw_attrs.update(d["attrs"])
        r, c = ease2_cell(d["xs"], d["ys"], field["lon"], field["lat"])
        v, n = clean_l3(d["sm"][:, r, c], d["fl"][:, r, c], _one(a["_FillValue"]), (_one(a["valid_min"]), _one(a["valid_max"])))
        vals, cnt = np.unique(d["fl"][:, r, c][~np.isclose(d["sm"][:, r, c], _one(a["_FillValue"]))], return_counts=True)
        l3_counts[half] = {**n, "flag_values_with_a_retrieval": {int(k): int(x) for k, x in zip(vals, cnt)}}
        parts[f"smap_l3_{half}_m3m3"] = pd.Series(v, index=pd.DatetimeIndex(d["time"]).normalize())
    df = pd.DataFrame(parts).rename_axis("date").reset_index()
    kinds = {c: "theta_m3m3" for c in df.columns if c != "date"}
    warned = g.check_table(df, kinds, valid_ranges={c: ((0.0, 0.9) if "l4" in c else (0.02, 0.5)) for c in kinds})
    clean_dir.mkdir(parents=True, exist_ok=True)
    out = clean_dir / "smap.parquet"
    df.to_parquet(out, index=False)
    card = g.make_card(
        dataset="smap", product="SMAP SPL4SMGP (L4, model-assisted) and SPL3SMP_E (L3 enhanced radiometer)", version="L4 v008; L3 v006",
        variable=["sm_rootzone", "sm_surface", "soil_moisture (AM)", "soil_moisture_pm"],
        units_in="m3 m-3 (L4); cm3/cm3 (L3)", units_out="m3/m3 in each column name; one row per UTC day", scale_factor=1.0,
        fill_values_removed={"-9999 (L4)": 0, "-9999 (L3 AM, PM)": {k: v["fill"] for k, v in l3_counts.items()}},
        quality_flags_used=("L3: retrieval_qual_flag 0 or 8 (recommended quality) only; counts per half-orbit: "
                            f"{l3_counts}. L4 has no per-value flag (a model analysis)"),
        records_dropped={"l3_not_recommended": {k: v["not_recommended_quality"] + v["not_recommended_and_out_of_range"]
                                                for k, v in l3_counts.items()},
                         "l4_days_with_fewer_than_8_values": incomplete},
        date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone="UTC days (L4: the eight 3-hourly values stamped 01:30 to 22:30 UTC; L3: the file's daily time step)",
        pixel_count=1, source="NASA NSIDC DAAC via LP DAAC AppEEARS area requests (pipeline/fetch/appeears.py)",
        resolution="9 km EASE-Grid 2.0 Global cell (EPSG:6933); the cell holding the field, which mixes valley floor, city and hills",
        raw_attrs=raw_attrs, range_warnings=warned,
        location={"lat": field["lat"], "lon": field["lon"], "cell_row_col": list(cell)},
        notes=("A check on the twin only (scripts/run_smap_check.py); no number shown uses SMAP. L4 is model-based. "
               "L3: " + ("; ".join(f"{k.upper()} {v['kept']} recommended-quality retrievals of {v['kept'] + v['not_recommended_quality'] + v['not_recommended_and_out_of_range']}"
                                   for k, v in l3_counts.items()) or "no files")
               + ". Where none is of recommended quality the L3 columns are empty and L3 is not used."))
    card_path = g.write_card(card, Path(data_dir) / "cards" / field["id"])
    return {"table": out, "card": card_path, "rows": len(df), "l3": l3_counts, "l4_incomplete_days": incomplete}


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    field = load_field(ap.parse_args(argv).field)
    r = build(field)
    ensure_credit(REPO / "CREDITS.md",
                  "- NASA SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture Geophysical Data (SPL4SMGP v008, "
                  "model-assisted) and SMAP Enhanced L3 Radiometer Global Daily 9 km Soil Moisture (SPL3SMP_E v006), NSIDC "
                  f"DAAC via LP DAAC AppEEARS, the 9 km cell holding field `{field['id']}`, 2015-03-31 to 2025-12-31, cleaned "
                  f"{pd.Timestamp.now().date()} by pipeline/fetch/smap.py (a check on the twin only; no number shown uses it)")
    print(f"{r['rows']} days -> {r['table']}; card {r['card']}; L3 {r['l3']}; L4 days with fewer than 8 values: {r['l4_incomplete_days']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
