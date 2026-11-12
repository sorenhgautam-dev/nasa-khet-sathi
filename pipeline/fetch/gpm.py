"""GPM IMERG daily V07 (decisions D1, D6): the twin's rain, for the fetch box and the field's cell.

    .venv/bin/python -m pipeline.fetch.gpm --field demo [--workers 4]
    .venv/bin/python -m pipeline.fetch.gpm --field demo --from-cache     # rebuild from cached files, no network

D1: GPM_3IMERGDF (Final) through its last day in CMR (2025-09-30 on 2026-11-12), then GPM_3IMERGDL
(Late) for the rest of 2025; the switch is recorded in the card's `segments`. Each day is a tiny
OPeNDAP subset (the box's 0.1-degree cells) from GES DISC's Hyrax server, cached as netCDF-4 in
data/raw/gpm/<field>/<product>/ and read with h5py, so reruns resume. Login: ~/.netrc via Earthdata
Login redirects; the account must have accepted the GES DISC EULA (earthaccess reports
EulaNotAccepted otherwise). Days: UTC days (00:00-24:00 UTC = 05:45-05:45 Nepal time; TODO-VERIFY in
the IMERG V07 documentation; each cached file's BeginTime/EndTime attributes are kept in the card).
`precipitation` is a daily mean rate in mm/day, so one day's value is that day's rain in mm.
Writes data/clean/<field>/gpm.parquet (date, rain_mm in the field's cell, rain_box_mean_mm, product) and
the card.

Partial failures never pass quietly (REVIEW_NOTES M2): every day without a value is counted by reason
(download failed, no granule in CMR, not cached, or a real _FillValue in the field's cell), and `main`
exits non-zero listing every day that has no file.
"""
import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RES = 0.1                      # IMERG V07 grid: 3600 x 1800 cells from -180 E and -90 N (DDS, 2026-11-12)
ARCHIVE = "https://data.gesdisc.earthdata.nasa.gov/data/"
OPENDAP_HOSTS = ["https://gpm1.gesdisc.eosdis.nasa.gov/opendap/",   # GES DISC Hyrax; gpm1 refused connections on
                 "https://gpm2.gesdisc.eosdis.nasa.gov/opendap/"]   # 2026-11-12 while gpm2 served the same paths
RAIN_RANGE = (0.0, 500.0)      # golden rule 12b (IMERG documents no valid range of its own)
PRODUCTS = ("final", "late")   # cache folders, in priority order (D1)
TIME_ZONE = ("UTC days (00:00-24:00 UTC = 05:45-05:45 Nepal time; TODO-VERIFY in the IMERG V07 documentation; "
             "the files' own BeginTime/EndTime attributes are in raw_attrs.file)")


def cell_index(lat, lon):
    return int(math.floor((lon + 180) / RES + 1e-9)), int(math.floor((lat + 90) / RES + 1e-9))


def box_indices(box):
    i0, j0 = cell_index(box[1], box[0])
    i1, j1 = cell_index(box[3], box[2])
    return i0, i1, j0, j1


def cell_centres(i0, i1, j0, j1):
    return ([round(-180 + RES * (i + 0.5), 4) for i in range(i0, i1 + 1)],
            [round(-90 + RES * (j + 0.5), 4) for j in range(j0, j1 + 1)])


def opendap_url(archive_link, idx, host=OPENDAP_HOSTS[0]):
    i0, i1, j0, j1 = idx
    if not archive_link.startswith(ARCHIVE):
        raise ValueError(f"unexpected GPM archive link {archive_link}")
    return (host + archive_link[len(ARCHIVE):] + ".nc4"
            + f"?precipitation[0:0][{i0}:{i1}][{j0}:{j1}],lon[{i0}:{i1}],lat[{j0}:{j1}],time[0:0]")


def segments(start, end, last_final):
    seg = [("final", str(start.date()), str(min(end, last_final).date()))]
    if end > last_final:
        seg.append(("late", str((last_final + pd.Timedelta(1, unit="D")).date()), str(end.date())))
    return seg


def _text(v):
    return v.decode() if isinstance(v, bytes) else v


def raw_attributes(path):
    """Golden rule 12a: the precipitation variable's units, scale_factor, add_offset, _FillValue and
    valid_range (ABSENT when the file has none), plus the file's own day bounds."""
    import h5py

    from pipeline.fetch.guards import describe_raw_attrs
    with h5py.File(path, "r") as h:
        attrs = {k: _text(v) for k, v in h["precipitation"].attrs.items()
                 if k not in ("DIMENSION_LIST", "REFERENCE_LIST") and not k.startswith("_Netcdf4")}
        file_attrs = {k: _text(h.attrs[k]) for k in ("BeginDate", "BeginTime", "EndDate", "EndTime", "title", "DOI")
                      if k in h.attrs}
    for k, v in attrs.items():
        if isinstance(v, np.ndarray) and v.size == 1:
            attrs[k] = v.item()
    return {"precipitation": describe_raw_attrs(attrs), "file": file_attrs}


def read_subset(path, field_cell, expect_lon=None, expect_lat=None):
    import h5py

    from pipeline.fetch.guards import mask_fill
    with h5py.File(path, "r") as h:
        p = h["precipitation"]
        units = _text(p.attrs.get("units", b""))
        if units != "mm/day":
            raise ValueError(f"precipitation units are '{units}', expected mm/day")
        fill = np.ravel(p.attrs.get("_FillValue", np.float32(-9999.9)))[0]
        raw = np.asarray(p[0])
        lon, lat = np.asarray(h["lon"][:], dtype=float), np.asarray(h["lat"][:], dtype=float)
    for got, want in ((lon, expect_lon), (lat, expect_lat)):
        if want is not None and (len(got) != len(want) or np.abs(got - np.asarray(want)).max() > 1e-3):
            raise ValueError(f"subset grid {got.tolist()} does not match the requested cells {list(want)}")
    a, n_fill = mask_fill(raw, [fill])
    if n_fill == 0:                                     # a fill written in another precision (h5py float32 vs doc)
        near = np.isclose(a, float(fill))
        a[near], n_fill = np.nan, int(near.sum())
    bad = np.isfinite(a) & ((a < RAIN_RANGE[0]) | (a > RAIN_RANGE[1]))
    if bad.any():
        raise ValueError(f"GPM rain {a[bad].tolist()} mm/day outside the range {RAIN_RANGE}")
    return {"rain_mm": float(a[field_cell]), "rain_box_mean_mm": float(np.nanmean(a)) if np.isfinite(a).any() else np.nan,
            "cells": int(a.size), "field_cell_fill": bool(np.isnan(a[field_cell])), "box_fills": n_fill}


def missing_days(dates, cached, cmr_products=None, failures=None):
    """Why each day without a cached file has none: 'failed' (its download failed), 'no_granule' (CMR has no
    granule for it), 'not_cached' (no file and no recorded failure; in a from-cache run CMR is not asked)."""
    failures = failures or {}
    out = {"failed": [], "no_granule": [], "not_cached": []}
    for d in dates:
        if d in cached:
            continue
        key = str(pd.Timestamp(d).date())
        if key in failures:
            out["failed"].append(key)
        elif cmr_products is not None and d not in cmr_products:
            out["no_granule"].append(key)
        else:
            out["not_cached"].append(key)
    return out


def day_ranges(days):
    """['2025-10-01', '2025-10-02', '2025-10-07'] -> ['2025-10-01..2025-10-02', '2025-10-07']."""
    ds = sorted(pd.Timestamp(d) for d in days)
    out, run = [], []
    for d in ds:
        if run and d - run[-1] != pd.Timedelta(1, unit="D"):
            out.append(run)
            run = []
        run.append(d)
    if run:
        out.append(run)
    return [str(r[0].date()) if len(r) == 1 else f"{r[0].date()}..{r[-1].date()}" for r in out]


def cached_files(raw):
    """{day: (product, path)} for data/raw/gpm/<field>/{final,late}/YYYY-MM-DD.nc4; Final wins over Late."""
    out = {}
    for prod in reversed(PRODUCTS):
        for f in sorted((Path(raw) / prod).glob("*.nc4")):
            out[pd.Timestamp(f.stem)] = (prod, f)
    return out


def build(field, data_dir, start, end, last_final, cmr_products=None, failures=None, mode="fetch"):
    """Read the cached daily files for start..end and write gpm.parquet and the card. cmr_products
    ({day: product}) comes from the CMR search in a fetch run, None in a from-cache run."""
    from pipeline.fetch import guards as g

    data_dir = Path(data_dir)
    raw = data_dir / "raw" / "gpm" / field["id"]
    idx = box_indices(field["fetch_box"])
    fi, fj = cell_index(field["lat"], field["lon"])
    field_cell = (fi - idx[0], fj - idx[2])
    want_lon, want_lat = cell_centres(*idx)
    seg = segments(pd.Timestamp(start), pd.Timestamp(end), last_final)
    files = cached_files(raw)
    if cmr_products is not None:                    # a fetch run: only the product CMR named for that day counts
        files = {d: (p, raw / p / f"{d.date()}.nc4") for d, p in cmr_products.items()
                 if (raw / p / f"{d.date()}.nc4").exists()}
    dates = pd.date_range(start, end)
    present = [d for d in dates if d in files]
    if not present:
        raise RuntimeError(f"no cached GPM file for {start} to {end} in {raw}")
    attrs = raw_attributes(files[present[0]][1])
    print("raw attributes (precipitation, first file):", json.dumps(attrs["precipitation"], default=str), flush=True)
    seg_of = {}
    for prod, a, b in seg:
        for d in pd.date_range(a, b):
            seg_of[d] = prod
    rows = []
    for d in dates:
        if d in files:
            prod, f = files[d]
            rows.append({"date": d, "product": prod, **read_subset(f, field_cell, want_lon, want_lat)})
        else:
            prod = (cmr_products or {}).get(d) or seg_of.get(d, "none")
            rows.append({"date": d, "product": prod, "rain_mm": np.nan, "rain_box_mean_mm": np.nan, "cells": 0,
                         "field_cell_fill": False, "box_fills": 0})
    df = pd.DataFrame(rows)
    why = missing_days(dates, set(files), cmr_products, failures)
    out = data_dir / "clean" / field["id"] / "gpm.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df[["date", "rain_mm", "rain_box_mean_mm", "product"]].to_parquet(out, index=False)
    valid = df.loc[df["rain_mm"].notna(), "date"]
    fill_label = f"{float(np.ravel(attrs['precipitation']['_FillValue'])[0]):.1f} (_FillValue) in the field's cell" \
        if attrs["precipitation"]["_FillValue"] != "ABSENT" else "_FillValue ABSENT in the file"
    n_fill = int(df["field_cell_fill"].sum())
    seg_cards = []
    for prod, a, b in seg:
        part = df[(df["date"] >= a) & (df["date"] <= b)]
        ds = {str(d.date()) for d in part["date"]}
        seg_cards.append({"product": prod, "from": a, "to": b, "days": len(part),
                          "days_with_value": int(part["rain_mm"].notna().sum()),
                          "days_fill_in_field_cell": int(part["field_cell_fill"].sum()),
                          **{f"days_{k}": len([x for x in v if x in ds]) for k, v in why.items()}})
    lost = {k: len(v) for k, v in why.items()}
    card = g.make_card(
        dataset="gpm", product="GPM IMERG daily", version="V07 (GPM_3IMERGDF Final, then GPM_3IMERGDL Late)",
        variable="precipitation (daily mean rate)", units_in="mm/day", units_out="rain_mm (mm per UTC day)",
        scale_factor=None, fill_values_removed={fill_label: n_fill},
        quality_flags_used="none (precipitation_cnt not used yet)",
        records_dropped=int(df["rain_mm"].isna().sum()),
        date_range=[str(valid.min().date()), str(valid.max().date())] if len(valid) else [],
        time_zone=TIME_ZONE, pixel_count=int(df["cells"].max()),
        source="Huffman et al., GPM IMERG Final/Late Precipitation L3 1 day 0.1 degree V07, NASA GES DISC",
        resolution="0.1 deg (about 10 km); the field's cell and the box mean",
        raw_attrs={"precipitation": attrs["precipitation"], "file": attrs["file"],
                   "grid": "lon 3600 x lat 1800, 0.1 deg"},
        segments=seg_cards,
        location={"box_cells_lon": want_lon, "box_cells_lat": want_lat, "field_cell": field_cell},
        notes=(f"{'Built from the cache (no CMR search; product from the cache folder, last Final day from the files)' if mode == 'cache' else 'Fetch run'}; "
               f"requested {start} to {end} ({len(dates)} days). Days without a value: {int(df['rain_mm'].isna().sum())} = "
               f"download failed {lost['failed']} + no granule in CMR {lost['no_granule']} + not cached {lost['not_cached']} "
               f"+ a real _FillValue in the field's cell {n_fill}. Failed days: {day_ranges(why['failed']) or 'none'}; "
               f"no granule: {day_ranges(why['no_granule']) or 'none'}; not cached: {day_ranges(why['not_cached']) or 'none'}. "
               "Missing days stay missing here; the weather table fills them from POWER, flags them and caps the fill "
               "(decision D), never 2001-2003."))
    return {"table": out, "card": g.write_card(card, data_dir / "cards" / field["id"]), "df": df, "missing": why}


def build_from_cache(field, data_dir=REPO / "data", start="2001-01-01", end="2025-12-31"):
    """REVIEW_NOTES M2: gpm.parquet and the card from the cached daily files alone (no CMR search). The
    product comes from the cache folder; the last Final day is the last cached Final file."""
    raw = Path(data_dir) / "raw" / "gpm" / field["id"]
    finals = sorted(pd.Timestamp(f.stem) for f in (raw / "final").glob("*.nc4"))
    if not finals:
        raise RuntimeError(f"no cached Final files in {raw / 'final'}")
    fpath = raw / "failures.json"
    failures = json.loads(fpath.read_text()) if fpath.exists() else {}
    return build(field, data_dir, start, end, finals[-1], cmr_products=None, failures=failures, mode="cache")


def _get(session, link, idx, dest):
    import requests
    last = None
    for host in OPENDAP_HOSTS:
        try:
            r = session.get(opendap_url(link, idx, host), timeout=180)
            break
        except requests.ConnectionError as e:
            last = e
    else:
        raise RuntimeError(f"no GES DISC OPeNDAP host reachable: {last}")
    if r.status_code != 200 or not r.content.startswith(b"\x89HDF"):
        raise RuntimeError(f"HTTP {r.status_code}, {len(r.content)} bytes, not a netCDF-4 file (EULA accepted?)")
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(r.content)
    tmp.replace(dest)


def fetch(field, workers=4, data_dir=REPO / "data", start="2001-01-01", end="2025-12-31"):
    import earthaccess
    import requests

    data_dir = Path(data_dir)
    earthaccess.login(strategy="netrc", persist=False)
    idx = box_indices(field["fetch_box"])
    final = earthaccess.search_data(short_name="GPM_3IMERGDF", version="07", temporal=(start, end))
    days = {pd.Timestamp(x["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10]): ("final", x.data_links()[0])
            for x in final}
    last_final = max(days)
    late = earthaccess.search_data(short_name="GPM_3IMERGDL", version="07",
                                   temporal=(str((last_final + pd.Timedelta(1, unit="D")).date()), end))
    for x in late:
        d = pd.Timestamp(x["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:10])
        days.setdefault(d, ("late", x.data_links()[0]))
    raw = data_dir / "raw" / "gpm" / field["id"]
    todo = []
    for d, (prod, link) in sorted(days.items()):
        dest = raw / prod / f"{d.date()}.nc4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            todo.append((d, dest, link))
    print(f"GPM: {len(days)} day(s) in CMR ({sum(p == 'final' for p, _ in days.values())} Final, last {last_final.date()}); "
          f"{len(todo)} to fetch", flush=True)
    fails = {}
    s = requests.Session()                      # credentials for urs.earthdata.nasa.gov come from ~/.netrc
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(_get, s, link, idx, dest): d for d, dest, link in todo}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                f.result()
            except Exception as e:
                fails[str(futs[f].date())] = f"{type(e).__name__}: {str(e)[:160]}"
            if n % 250 == 0:
                print(f"GPM: {n}/{len(todo)} fetched, {len(fails)} failed", flush=True)
    (raw / "failures.json").write_text(json.dumps(fails, indent=1) + "\n")
    if len(fails) == len(todo) and todo:
        raise RuntimeError(f"every GPM request failed, e.g. {next(iter(fails.values()))}")
    r = build(field, data_dir, start, end, last_final, cmr_products={d: p for d, (p, _) in days.items()},
              failures=fails, mode="fetch")
    return {**r, "fails": fails}


def main(argv=None, data_dir=None, field=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--from-cache", action="store_true",
                    help="build gpm.parquet and the card from the cached daily files only (no CMR search, no network)")
    ap.add_argument("--start", default="2001-01-01")
    ap.add_argument("--end", default="2025-12-31")
    a = ap.parse_args(argv)
    field = field or load_field(a.field)
    data_dir = Path(data_dir) if data_dir else REPO / "data"
    if a.from_cache:
        r = build_from_cache(field, data_dir=data_dir, start=a.start, end=a.end)
    else:
        r = fetch(field, workers=a.workers, data_dir=data_dir, start=a.start, end=a.end)
    d = r["df"]
    print(f"{int(d['rain_mm'].notna().sum())} of {len(d)} days with rain; "
          f"{int(d['field_cell_fill'].sum())} real fill(s) in the field's cell\n-> {r['table']}\n-> {r['card']}")
    lost = {k: v for k, v in r["missing"].items() if v}
    if lost:
        for k, v in lost.items():
            print(f"GPM: {len(v)} day(s) {k.replace('_', ' ')}: {', '.join(day_ranges(v))}", file=sys.stderr)
        print("GPM: incomplete; the card records every missing day. Rerun the fetch, then --from-cache.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
