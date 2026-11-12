"""NASA LP DAAC AppEEARS area requests for a field's fetch box (MODIS MOD13Q1, SMAP L3 and L4).

    .venv/bin/python -m pipeline.fetch.appeears submit --field demo     # submit the tasks, record their ids
    .venv/bin/python -m pipeline.fetch.appeears download --field demo   # poll; download finished bundles
    .venv/bin/python -m pipeline.fetch.appeears card --field demo       # data cards from the cached bundles, no network

Why AppEEARS: MOD13Q1 is HDF4 (no reader here) and SMAP granules are global files; AppEEARS cuts each
product to the box on NASA's side and returns one netCDF-4 file per product (native projection, so no
resampling). Login: the Earthdata account in ~/.netrc, read with Python's netrc module; the token lives
in memory only and is never written or printed. Raw bundles go to data/raw/appeears/<field>/<task>/.
Citation: AppEEARS Team (2026), Application for Extracting and Exploring Analysis Ready Samples
(AppEEARS), NASA EOSDIS LP DAAC, USGS EROS, https://appeears.earthdatacloud.nasa.gov.

Cards (REVIEW_NOTES L7): `card` writes data/cards/<field>/<task>.json for every downloaded task (COMPLETE
present) from its netCDF-4 files alone, read with h5py, printing each layer's raw attributes (units,
scale_factor, add_offset, _FillValue, valid_range). Tasks not downloaded yet are skipped. Quality layers are
applied later, by the diary step; the card says so.
"""
import argparse
import json
import netrc
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
API = "https://appeears.earthdatacloud.nasa.gov/api"

TASKS = {   # name -> (start, end, [(product, layer), ...]); layer names from GET /product/<product>, 2026-11-12
    "modis": ("2001-01-01", "2025-12-31", [
        ("MOD13Q1.061", "_250m_16_days_NDVI"), ("MOD13Q1.061", "_250m_16_days_pixel_reliability"),
        ("MOD13Q1.061", "_250m_16_days_VI_Quality"), ("MOD13Q1.061", "_250m_16_days_composite_day_of_the_year")]),
    # AppEEARS caps the files one request may make (a single SMAP L3 task was 57.2% over, 2026-11-12), so
    # L3 is split into AM and PM and the 3-hourly L4 into one task per year.
    "smap_l3_am": ("2015-03-31", "2025-12-31", [
        ("SPL3SMP_E.006", "Soil_Moisture_Retrieval_Data_AM_soil_moisture"),
        ("SPL3SMP_E.006", "Soil_Moisture_Retrieval_Data_AM_retrieval_qual_flag")]),
    "smap_l3_pm": ("2015-03-31", "2025-12-31", [
        ("SPL3SMP_E.006", "Soil_Moisture_Retrieval_Data_PM_soil_moisture_pm"),
        ("SPL3SMP_E.006", "Soil_Moisture_Retrieval_Data_PM_retrieval_qual_flag_pm")]),
    **{f"smap_l4_{y}": (f"{y}-01-01" if y > 2015 else "2015-03-31", f"{y}-12-31", [
        ("SPL4SMGP.008", "Geophysical_Data_sm_rootzone"), ("SPL4SMGP.008", "Geophysical_Data_sm_surface")])
       for y in range(2015, 2026)},
}


def area_task(name, box, start, end, layers):
    """AppEEARS area-task JSON for the box [min_lon, min_lat, max_lon, max_lat]."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    if not s < e:
        raise ValueError(f"start {start} must be before end {end}")
    x0, y0, x1, y1 = box
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"task_type": "area", "task_name": name,
            "params": {"dates": [{"startDate": s.strftime("%m-%d-%Y"), "endDate": e.strftime("%m-%d-%Y")}],
                       "layers": [{"product": p, "layer": lyr} for p, lyr in layers],
                       "output": {"format": {"type": "netcdf4"}, "projection": "native"},
                       "geo": {"type": "FeatureCollection", "features": [
                           {"type": "Feature", "properties": {},
                            "geometry": {"type": "Polygon", "coordinates": [ring]}}]}}}


def wanted_files(files, only_nc=False):
    return [f for f in files if (f["file_name"].endswith(".nc") or not only_nc)]


def _session():
    import requests
    creds = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    if not creds:
        raise RuntimeError("no urs.earthdata.nasa.gov entry in ~/.netrc")
    s = requests.Session()
    r = s.post(f"{API}/login", auth=(creds[0], creds[2]), timeout=120)
    r.raise_for_status()
    s.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return s


def _tasks_file(field_id):
    p = REPO / "data" / "raw" / "appeears" / field_id / "tasks.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def submit(field, names):
    p = _tasks_file(field["id"])
    done = json.loads(p.read_text()) if p.exists() else {}
    s = _session()
    try:
        for n in names:
            if n in done:
                print(f"{n}: already submitted as task {done[n]['task_id']}")
                continue
            start, end, layers = TASKS[n]
            t = area_task(f"{field['id']}_{n}", field["fetch_box"], start, end, layers)
            r = s.post(f"{API}/task", json=t, timeout=120)
            if not r.ok:
                raise RuntimeError(f"{n}: AppEEARS refused the task: {r.status_code} {r.text[:300]}")
            done[n] = {"task_id": r.json()["task_id"], "submitted": pd.Timestamp.now(tz="UTC").isoformat(),
                       "request": t}
            p.write_text(json.dumps(done, indent=1) + "\n")
            print(f"{n}: submitted task {done[n]['task_id']}")
    finally:
        s.post(f"{API}/logout", timeout=60)


def download(field, wait_s=0, poll_s=120):
    p = _tasks_file(field["id"])
    tasks = json.loads(p.read_text())
    import requests
    s = _session()
    t0, errors = time.time(), 0
    try:
        while True:
            try:
                pending = _download_round(s, tasks, p)
                errors = 0
            except requests.RequestException as e:          # a dropped connection: try again next round
                errors += 1
                print(f"network error ({type(e).__name__}), retry {errors}/10 in {poll_s} s", flush=True)
                if errors >= 10:
                    raise
                pending = ["(network error)"]
            if not pending or time.time() - t0 > wait_s:
                print("still processing: " + "; ".join(pending) if pending else "all tasks downloaded", flush=True)
                return pending
            time.sleep(poll_s)
    finally:
        try:
            s.post(f"{API}/logout", timeout=60)
        except Exception:
            pass                                             # logout failure leaves only a token that expires in 48 h


def _download_round(s, tasks, p):
    """One pass over the tasks: download each finished bundle once; return the ones still processing."""
    pending = []
    for n, info in tasks.items():
        out = p.parent / n
        if (out / "COMPLETE").exists():
            continue
        st = s.get(f"{API}/task/{info['task_id']}", timeout=120).json()
        if st.get("status") != "done":
            pending.append(f"{n}: {st.get('status')}")
            continue
        out.mkdir(exist_ok=True)
        bundle = s.get(f"{API}/bundle/{info['task_id']}", timeout=120).json()
        for f in wanted_files(bundle["files"]):
            dest = out / f["file_name"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            with s.get(f"{API}/bundle/{info['task_id']}/{f['file_id']}", stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
        (out / "COMPLETE").write_text(json.dumps([f["file_name"] for f in bundle["files"]]) + "\n")
        print(f"{n}: downloaded {len(bundle['files'])} file(s) to {out.relative_to(REPO)}", flush=True)
    return pending




def _attr(v):
    import numpy as np
    if isinstance(v, bytes):
        return v.decode()
    if isinstance(v, np.ndarray):
        return v.item() if v.size == 1 else v.tolist()
    return v.item() if hasattr(v, "item") else v


def read_nc(path):
    """Data layers (variables with a grid_mapping), their attributes, time stamps, grid and CRS of one
    AppEEARS netCDF-4 file, read with h5py."""
    import h5py
    import numpy as np
    out = {"layers": {}}
    with h5py.File(path, "r") as h:
        for name, v in h.items():
            if isinstance(v, h5py.Dataset) and "grid_mapping" in v.attrs:
                attrs = {k: _attr(a) for k, a in v.attrs.items()
                         if k not in ("DIMENSION_LIST", "REFERENCE_LIST", "Legend") and not k.startswith("_Netcdf4")}
                raw = v[...]
                fill = attrs.get("_FillValue")
                out["layers"][name] = {"attrs": attrs, "dtype": str(v.dtype), "shape": list(v.shape),
                                       "cells_with_fill": int((raw == fill).sum()) if fill is not None else 0,
                                       "grid_mapping": attrs["grid_mapping"]}
        tu = _attr(h["time"].attrs["units"])
        step, since = tu.split(" since ")
        t0 = pd.Timestamp(since.strip())
        t0 = t0.tz_convert(None) if t0.tzinfo else t0
        out["time"] = [t0 + pd.Timedelta(float(x), unit={"seconds": "s", "days": "D", "hours": "h"}[step.strip()])
                       for x in h["time"][:]]
        out["time_units"] = tu
        x, y = np.asarray(h["xdim"][:], dtype=float), np.asarray(h["ydim"][:], dtype=float)
        gm = next(iter(out["layers"].values()))["grid_mapping"] if out["layers"] else "crs"
        out["crs_wkt"] = _attr(h[gm].attrs["spatial_ref"])
        out["x"], out["y"] = x, y
    return out


def grid_transform(x, y):
    """Affine transform of a regular grid from its cell-centre coordinates (CF convention)."""
    from rasterio.transform import Affine
    dx, dy = x[1] - x[0], y[1] - y[0]
    return Affine(dx, 0.0, x[0] - dx / 2, 0.0, dy, y[0] - dy / 2)


def write_task_card(field, task, data_dir=REPO / "data"):
    """L7: the data card for one downloaded AppEEARS task, from its cached bundle only. None if not downloaded."""
    from pipeline.fetch import guards as g
    from pipeline.fetch.cogwindows import field_pixel_count
    d = Path(data_dir) / "raw" / "appeears" / field["id"] / task
    ncs = sorted(d.glob("*.nc")) if (d / "COMPLETE").exists() else []
    if not ncs:
        print(f"{task}: not downloaded (no COMPLETE bundle in {d}); skipped")
        return None
    layers, times, fills, pixels, raw_attrs, products, units = {}, [], {}, {}, {}, set(), set()
    for f in ncs:
        r = read_nc(f)
        times += r["time"]
        units.add(r["time_units"])
        pixels[f.name] = field_pixel_count(field["polygon"], r["crs_wkt"], grid_transform(r["x"], r["y"]),
                                           (len(r["y"]), len(r["x"])))
        for name, lay in r["layers"].items():
            a = lay["attrs"]
            raw_attrs[name] = {**g.describe_raw_attrs(a), "dtype": lay["dtype"], "long_name": a.get("long_name", "ABSENT"),
                               "file": f.name}
            print(f"raw attributes {task} {name}: {raw_attrs[name]}")
            fills[name] = {"_FillValue": a.get("_FillValue", "ABSENT"), "cells_with_fill": lay["cells_with_fill"],
                           "removed": "not yet: masked by the diary step"}
            layers[name] = a.get("units", "ABSENT")
        products.add(f.name.split("_")[0])
    _, _, wanted = TASKS[task]
    times = sorted(set(times))
    card = g.make_card(
        dataset=task, product=", ".join(sorted(products)),
        version=", ".join(sorted({p for p, _ in wanted})) + " (AppEEARS area task, native projection, netCDF-4)",
        variable=sorted(layers), units_in=layers, units_out={k: "as stored (scale and offset not applied in the cache)" for k in layers},
        scale_factor={k: v.get("scale_factor") for k, v in raw_attrs.items()}, fill_values_removed=fills,
        quality_flags_used=("none yet: the quality layers (e.g. pixel reliability, VI quality, retrieval flags) are applied "
                            "later, by the diary step (pipeline/diary); the cache keeps them raw"),
        records_dropped={"time_steps": len(times), "files": len(ncs),
                         "layers_requested": len(wanted), "layers_in_files": len(layers)},
        date_range=[str(times[0].date()), str(times[-1].date())] if times else [],
        time_zone=f"UTC ({'; '.join(sorted(units))}); composite or overpass dates as AppEEARS writes them",
        pixel_count=next(iter(pixels.values())) if len(pixels) == 1 else pixels,
        source=f"NASA LP DAAC AppEEARS area task ({', '.join(sorted({p for p, _ in wanted}))}), cut to the fetch box on NASA's side",
        resolution="native grid of the product (see raw_attrs; MOD13Q1 about 231.7 m sinusoidal)", raw_attrs=raw_attrs,
        location={"field_polygon": field["polygon"], "files": [f.name for f in ncs]},
        notes=(f"{len(times)} time steps {times[0].date() if times else '-'} to {times[-1].date() if times else '-'}; "
               "pixel_count counts grid cells over the field polygon (centres inside, and touching)."))
    path = g.write_card(card, Path(data_dir) / "cards" / field["id"])
    print(f"{task}: card -> {path}")
    return path


def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "download", "card"])
    ap.add_argument("--field", default="demo")
    ap.add_argument("--tasks", nargs="*", default=list(TASKS))
    ap.add_argument("--wait-s", type=int, default=0)
    a = ap.parse_args(argv)
    field = load_field(a.field)
    if a.action == "submit":
        submit(field, a.tasks)
    elif a.action == "card":
        for n in a.tasks:
            write_task_card(field, n)
    else:
        download(field, wait_s=a.wait_s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
