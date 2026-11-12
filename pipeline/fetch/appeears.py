"""NASA LP DAAC AppEEARS area requests for a field's fetch box (MODIS MOD13Q1, SMAP L3 and L4).

    .venv/bin/python -m pipeline.fetch.appeears submit --field demo     # submit the tasks, record their ids
    .venv/bin/python -m pipeline.fetch.appeears download --field demo   # poll; download finished bundles

Why AppEEARS: MOD13Q1 is HDF4 (no reader here) and SMAP granules are global files; AppEEARS cuts each
product to the box on NASA's side and returns one netCDF-4 file per product (native projection, so no
resampling). Login: the Earthdata account in ~/.netrc, read with Python's netrc module; the token lives
in memory only and is never written or printed. Raw bundles go to data/raw/appeears/<field>/<task>/.
Citation: AppEEARS Team (2026), Application for Extracting and Exploring Analysis Ready Samples
(AppEEARS), NASA EOSDIS LP DAAC, USGS EROS, https://appeears.earthdatacloud.nasa.gov.
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




def main(argv=None):
    from pipeline.fetch.fields import load_field

    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "download"])
    ap.add_argument("--field", default="demo")
    ap.add_argument("--tasks", nargs="*", default=list(TASKS))
    ap.add_argument("--wait-s", type=int, default=0)
    a = ap.parse_args(argv)
    field = load_field(a.field)
    if a.action == "submit":
        submit(field, a.tasks)
    else:
        download(field, wait_s=a.wait_s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
