"""NEX-GDDP-CMIP6 daily series at the field's 0.25 deg cell, for the 2040 outlook (build step 9; rules.yaml future).

    .venv/bin/python -m pipeline.fetch.nexgddp --field demo                 # fetch (resumable), then build
    .venv/bin/python -m pipeline.fetch.nexgddp --field demo --build-only    # rebuild from the cache only

Product: NASA Earth Exchange Global Daily Downscaled Projections, CMIP6 (NEX-GDDP-CMIP6), daily, 0.25 deg, bias-
corrected and downscaled (BCSD) from CMIP6 models (Thrasher et al. 2022, Scientific Data 9, 262). Not in CMR; read from
NASA NCCS's THREDDS server, one file per model, experiment, variable and year:
  catalogue   https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/<model>/<experiment>/<variant>/<var>/catalog.xml
  point CSV   https://ds.nccs.nasa.gov/thredds/ncss/grid/<urlPath>?var=<var>&latitude=<lat>&longitude=<lon>&temporal=all&accept=csv
  attributes  https://ds.nccs.nasa.gov/thredds/dodsC/<urlPath>.das   (units, _FillValue, time:calendar, cmip6_license)
Rules (rules.yaml future, committed before the first download): pr, tasmax, tasmin; historical 1995-2014, ssp245 and
ssp585 2026-2040; every model offering all of them, one variant folder each, GFDL-CM4_gr2 left out; models fetched in a
random order fixed by seed 2026; v2.0 where v1.x sits beside it; the cell nearest the field, requested at its centre.

Raw answers are cached BY CELL, data/raw/nexgddp/<cell>/<model>/<experiment>/<var>_<year>.csv (+ <var>.das), so fields in
the same cell reuse them; a file is written only after it passed the guards (units, grid point, calendar rows, range), so
a rerun skips it. <model>/manifest.json says whether the model is complete. Writes data/clean/<field>/nexgddp_daily.parquet
(model, experiment, year, month, day, calendar, pr_mm, tasmax_c, tasmin_c: model days, never real dates) and
data/cards/<field>/nexgddp.json.
"""
import argparse
import http.client
import json
import math
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch import guards as g

REPO = Path(__file__).resolve().parents[2]
BASE = "https://ds.nccs.nasa.gov/thredds"
ROOT = "AMES/NEX/GDDP-CMIP6"
RES = 0.25
LEFT_OUT = {"GFDL-CM4_gr2": "GFDL-CM4 again, downscaled from that model's second output grid (rules.yaml future.models)"}
UNITS = {"pr": "kg m-2 s-1", "tasmax": "K", "tasmin": "K"}
COLUMN = {"pr": "pr_mm", "tasmax": "tasmax_c", "tasmin": "tasmin_c"}
KIND = {"pr": "rain_mm", "tasmax": "temp_c", "tasmin": "temp_c"}
NS = {"t": "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0", "x": "http://www.w3.org/1999/xlink"}
FILE_RE = re.compile(r"^(?P<var>[A-Za-z]+)_day_(?P<model>.+)_(?P<exp>historical|ssp\d{3})_(?P<variant>r\d+i\d+p\d+f\d+)_"
                     r"(?P<grid>g[a-z0-9]+)_(?P<year>\d{4})(?:_v(?P<version>\d+(?:\.\d+)*))?\.nc$")


class MissingFiles(ValueError):
    """A model lacks a file the rule needs, or offers two that cannot be told apart."""


# ---------------------------------------------------------------- pure helpers (tests/test_nexgddp.py)

def cell_centre(lat, lon, res=RES):
    """Centre of the 0.25 deg grid cell holding (lat, lon); longitude on the grid's 0-360 axis."""
    lon360 = float(lon) % 360.0
    c = lambda v: round(math.floor(v / res) * res + res / 2, 6)  # noqa: E731
    return c(float(lat)), c(lon360)


def cell_key(clat, clon):
    return f"cell_{clat:.3f}_{clon:.3f}"


def eligible_models(names):
    return sorted(n for n in names if n not in LEFT_OUT)


def model_order(names, seed):
    """The models in a random order fixed by `seed` (rules.yaml future.fetch_order_seed): same answer for any input order."""
    return [str(n) for n in np.random.default_rng(seed).permutation(sorted(names))]


def parse_file_name(name):
    m = FILE_RE.match(name)
    if not m:
        return None
    d = m.groupdict()
    d["year"] = int(d["year"])
    return d


def parse_catalog(xml_text):
    """{'refs': [sub-catalogue titles], 'files': [{name, url_path}]} of a THREDDS catalog.xml."""
    root = ET.fromstring(xml_text)
    refs = [r.get(f"{{{NS['x']}}}title") for r in root.iter(f"{{{NS['t']}}}catalogRef")]
    files = [{"name": d.get("name"), "url_path": d.get("urlPath")} for d in root.iter(f"{{{NS['t']}}}dataset")
             if d.get("urlPath")]
    return {"refs": refs, "files": files}


def pick_files(entries, var, exp, years):
    """{year: {name, url_path, version}}: the one file of each year, or the _v2.0 file where several sit side by side
    (rules.yaml future.file_version). A missing year, or several files with no v2.0, raises MissingFiles."""
    by_year = {}
    for e in entries:
        f = parse_file_name(e["name"])
        if f and f["var"] == var and f["exp"] == exp and f["year"] in years:
            by_year.setdefault(f["year"], []).append({**e, "version": f["version"], "variant": f["variant"],
                                                      "grid": f["grid"]})
    out = {}
    for y in years:
        c = by_year.get(y, [])
        if not c:
            raise MissingFiles(f"{var} {exp}: no file for {y}")
        if len(c) > 1:
            v2 = [e for e in c if e["version"] == "2.0"]
            if len(v2) != 1:
                raise MissingFiles(f"{var} {exp} {y}: {len(c)} files and not exactly one v2.0: {[e['name'] for e in c]}")
            c = v2
        out[y] = c[0]
    if len({(e["variant"], e["grid"]) for e in out.values()}) > 1:
        raise MissingFiles(f"{var} {exp}: files mix variants or grids")
    return out


def parse_csv(text, var):
    """A NetcdfSubset point CSV -> {units, lat, lon, rows: DataFrame(year, month, day, value)}. Model dates (30 February
    in a 360-day calendar) are kept as numbers, never turned into real dates."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        raise g.DataGuardError(f"{var}: empty answer")
    m = re.search(rf"(?:^|,){re.escape(var)}\[unit=\"([^\"]*)\"\]", lines[0])
    if not m:
        raise g.DataGuardError(f"{var}: no '{var}[unit=...]' column in the answer's header: {lines[0][:200]}")
    rows = []
    for ln in lines[1:]:
        parts = ln.split(",")
        t = parts[0]
        rows.append((int(t[0:4]), int(t[5:7]), int(t[8:10]), float(parts[2]), float(parts[3]), float(parts[-1])))
    df = pd.DataFrame(rows, columns=["year", "month", "day", "lat", "lon", "value"])
    lats, lons = set(df["lat"]), set(df["lon"])
    if len(lats) != 1 or len(lons) != 1:
        raise g.DataGuardError(f"{var}: more than one grid point in the answer")
    return {"units": m.group(1), "lat": lats.pop(), "lon": lons.pop(), "rows": df[["year", "month", "day", "value"]]}


def convert(values, var, units, fills):
    """Raw values -> (pr mm/day or temperature deg C, number of fill values removed). Fails loudly on an unexpected
    unit or on a converted value outside golden rule 12's range; never clips."""
    if units != UNITS[var]:
        raise g.DataGuardError(f"{var}: units '{units}', expected '{UNITS[var]}' (Tech Note v2); not converted")
    raw = np.asarray(values, dtype=np.float32)
    a, n_fill = g.mask_fill(raw, list(fills))
    n_nan = int(np.isnan(raw).sum())
    a = a * 86400.0 if var == "pr" else a - 273.15            # kg m-2 s-1 = mm/s; K -> deg C
    g.assert_in_range(a[np.isfinite(a)], KIND[var], COLUMN[var])
    return a, n_fill + n_nan


def parse_das(text):
    """OPeNDAP .das text -> {variable: {attribute: value}} (numbers as float, strings unquoted)."""
    out, cur = {}, None
    for ln in text.splitlines():
        s = ln.strip()
        m = re.match(r"^([A-Za-z0-9_.]+) \{$", s)
        if m and s != "Attributes {":
            cur = out.setdefault(m.group(1), {})
            continue
        if s == "}":
            cur = None
            continue
        m = re.match(r"^(\w+) (\w+) (.*);$", s)
        if cur is not None and m:
            typ, name, val = m.groups()
            if typ == "String":
                cur[name] = val.strip().strip('"')
            else:
                nums = [float(v) for v in val.split(",")]
                cur[name] = nums[0] if len(nums) == 1 else nums
    return out


def check_year_rows(rows, year, calendar):
    """One row per model day of `year`, as many as the calendar has (360_day 360; noleap / 365_day 365; standard,
    gregorian, proleptic_gregorian 365 or 366 by the leap-year rule); fails loudly otherwise."""
    if (rows["year"] != year).any():
        raise g.DataGuardError(f"rows of another year than {year}")
    if rows.duplicated(["month", "day"]).any():
        raise g.DataGuardError(f"{year}: a day appears twice")
    leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0
    want = {"360_day": 360, "noleap": 365, "365_day": 365, "all_leap": 366, "366_day": 366,
            "standard": 366 if leap else 365, "gregorian": 366 if leap else 365,
            "proleptic_gregorian": 366 if leap else 365}.get(calendar)
    if want is None:
        raise g.DataGuardError(f"unknown calendar '{calendar}'")
    if len(rows) != want:
        raise g.DataGuardError(f"{year}: {len(rows)} days, the '{calendar}' calendar has {want}")


# ---------------------------------------------------------------- network and cache (I/O: allowed in fetch/)

_stats = {"requests": 0, "retries": 0, "failures": 0}
_lock = threading.Lock()


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def http_get(url, timeout=300, retries=5, backoff_s=10):
    """GET with retries and exponential back-off on 429, 5xx, time-outs and dropped connections; a 404 is final."""
    for attempt in range(retries + 1):
        with _lock:
            _stats["requests"] += 1
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "khet-sathi-pipeline (research, NEX-GDDP point)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                with _lock:
                    _stats["failures"] += 1
                raise
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ConnectionError, OSError):
            if attempt == retries:
                with _lock:
                    _stats["failures"] += 1
                raise
        with _lock:
            _stats["retries"] += 1
        time.sleep(backoff_s * 2 ** attempt)


def _atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text)
    tmp.replace(path)


def catalog(path_parts, cache_root):
    """A THREDDS catalogue (cached under data/raw/nexgddp/catalog/)."""
    rel = "/".join(path_parts)
    f = Path(cache_root) / "catalog" / (rel.replace("/", "__") or "top") / "catalog.xml"
    if f.exists():
        return parse_catalog(f.read_text())
    text = http_get(f"{BASE}/catalog/{ROOT}/{rel + '/' if rel else ''}catalog.xml", timeout=120)
    _atomic_write(f, text)
    return parse_catalog(text)


def discover(model, rules, cache_root):
    """{exp: {'variant', 'files': {var: {year: entry}}}} for one model, or raises MissingFiles."""
    fut = rules["future"]
    years = {"historical": range(fut["periods"]["historical"][0], fut["periods"]["historical"][1] + 1)}
    for s in fut["scenarios"]:
        years[s] = range(fut["periods"]["future"][0], fut["periods"]["future"][1] + 1)
    exps = catalog([model], cache_root)["refs"]
    out = {}
    for exp, yrs in years.items():
        if exp not in exps:
            raise MissingFiles(f"{model}: no {exp} folder")
        variants = catalog([model, exp], cache_root)["refs"]
        if len(variants) != 1:
            raise MissingFiles(f"{model} {exp}: {len(variants)} variant folders {variants} (rules.yaml future.models: one)")
        v = variants[0]
        have = catalog([model, exp, v], cache_root)["refs"]
        files = {}
        for var in fut["variables"]:
            if var not in have:
                raise MissingFiles(f"{model} {exp} {v}: no {var}")
            files[var] = pick_files(catalog([model, exp, v, var], cache_root)["files"], var, exp, list(yrs))
        out[exp] = {"variant": v, "files": files}
    return out


def csv_path(cell_dir, model, exp, var, year):
    return Path(cell_dir) / model / exp / f"{var}_{year}.csv"


def das_path(cell_dir, model, exp, var):
    return Path(cell_dir) / model / exp / f"{var}.das"


def fetch_das(cell_dir, model, exp, var, entry):
    p = das_path(cell_dir, model, exp, var)
    if not p.exists():
        _atomic_write(p, http_get(f"{BASE}/dodsC/{entry['url_path']}.das", timeout=120))
    das = parse_das(p.read_text())
    raw = g.describe_raw_attrs(das.get(var, {}))
    log(f"{model} {exp} {var} raw attributes: {json.dumps(raw)}; calendar {das.get('time', {}).get('calendar')}; "
        f"licence {das.get('NC_GLOBAL', {}).get('cmip6_license')}; file version {das.get('NC_GLOBAL', {}).get('version')}")
    return das


def validate_answer(text, var, year, cell, das):
    """Guards on one year's answer: unit, grid point = the cell centre, the calendar's days, fill and range."""
    p = parse_csv(text, var)
    if abs(p["lat"] - cell[0]) > 1e-6 or abs(p["lon"] % 360 - cell[1]) > 1e-6:
        raise g.DataGuardError(f"{var} {year}: the server returned grid point {p['lat']}, {p['lon']}, not the cell {cell}")
    if das.get(var, {}).get("units") not in (None, p["units"]):
        raise g.DataGuardError(f"{var} {year}: CSV unit '{p['units']}' differs from the file's '{das[var]['units']}'")
    check_year_rows(p["rows"], year, das.get("time", {}).get("calendar", "unknown"))
    fills = [x for k in ("_FillValue", "missing_value") for x in np.ravel([das.get(var, {}).get(k, [])])]
    vals, n_missing = convert(p["rows"]["value"].to_numpy(), var, p["units"], fills)
    return p, vals, n_missing


def fetch_year(cell_dir, cell, model, exp, var, year, entry, das):
    """One model-experiment-variable-year: download, guard, cache. Returns {ok, cached, error}; never raises."""
    path = csv_path(cell_dir, model, exp, var, year)
    if path.exists():
        return {"ok": True, "cached": True}
    url = (f"{BASE}/ncss/grid/{entry['url_path']}?var={var}&latitude={cell[0]}&longitude={cell[1]}"
           f"&temporal=all&accept=csv")
    try:
        text = http_get(url)
        validate_answer(text, var, year, cell, das)
    except Exception as e:  # noqa: BLE001 - recorded in the manifest; the model is then incomplete
        log(f"FAILED {model} {exp} {var} {year}: {type(e).__name__}: {e}")
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "file": entry["name"]}
    _atomic_write(path, text)
    return {"ok": True, "cached": False}


def run_fetch(cell, cache_root, rules, workers=4, only=None, max_models=None):
    """Fetch every eligible model in the seeded order; models complete one after another. Returns the manifests."""
    cell_dir = Path(cache_root) / cell_key(*cell)
    names = catalog([], cache_root)["refs"]
    order = model_order(eligible_models(names), rules["future"]["fetch_order_seed"])
    if only:
        order = [m for m in order if m in only]
    if max_models:
        order = order[:max_models]
    _atomic_write(cell_dir / "fetch_order.json", json.dumps({"seed": rules["future"]["fetch_order_seed"], "order": order,
                                                             "left_out": LEFT_OUT, "catalogue_models": names}, indent=1))
    log(f"cell {cell}; {len(order)} models in the seeded order: {order}")
    manifests = {}

    def prepare(model):
        if (cell_dir / model / "manifest.json").exists() and \
                json.loads((cell_dir / model / "manifest.json").read_text()).get("complete"):
            return None
        plan = discover(model, rules, cache_root)
        return plan, {(e, v): fetch_das(cell_dir, model, e, v, next(iter(plan[e]["files"][v].values())))
                      for e in plan for v in plan[e]["files"]}

    # the next model's catalogue and attribute requests run while this model downloads (one model ahead)
    with ThreadPoolExecutor(max_workers=workers) as ex, ThreadPoolExecutor(max_workers=1) as ahead:
        nxt = ahead.submit(prepare, order[0]) if order else None
        for k, model in enumerate(order, 1):
            t0, mpath = time.time(), cell_dir / model / "manifest.json"
            cur, nxt = nxt, (ahead.submit(prepare, order[k]) if k < len(order) else None)
            try:
                got = cur.result()
                if got is None:
                    manifests[model] = json.loads(mpath.read_text())
                    log(f"[{k}/{len(order)}] {model}: complete in the cache")
                    continue
                plan, das = got
            except Exception as e:  # noqa: BLE001 - the model is left out and reported
                log(f"[{k}/{len(order)}] {model}: LEFT OUT: {type(e).__name__}: {e}")
                man = {"model": model, "complete": False, "left_out": f"{type(e).__name__}: {e}"}
                _atomic_write(mpath, json.dumps(man, indent=1))
                manifests[model] = man
                continue
            jobs = {(e, v, y): ex.submit(fetch_year, cell_dir, cell, model, e, v, y, ent, das[(e, v)])
                    for e in plan for v in plan[e]["files"] for y, ent in plan[e]["files"][v].items()}
            res = {key: f.result() for key, f in jobs.items()}
            errors = {f"{e} {v} {y}": r["error"] for (e, v, y), r in res.items() if not r["ok"]}
            man = {"model": model, "complete": not errors, "errors": errors, "cell": list(cell),
                   "experiments": {e: {"variant": plan[e]["variant"],
                                       "calendar": das[(e, next(iter(plan[e]["files"])))].get("time", {}).get("calendar"),
                                       "files": {v: {str(y): {"name": ent["name"], "version": ent["version"]}
                                                     for y, ent in plan[e]["files"][v].items()}
                                                 for v in plan[e]["files"]}} for e in plan},
                   "attributes": {f"{e} {v}": {"raw": g.describe_raw_attrs(das[(e, v)].get(v, {})),
                                               "calendar": das[(e, v)].get("time", {}).get("calendar"),
                                               "licence": das[(e, v)].get("NC_GLOBAL", {}).get("cmip6_license"),
                                               "file_version": das[(e, v)].get("NC_GLOBAL", {}).get("version")}
                                  for (e, v) in das},
                   "fetched": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            _atomic_write(mpath, json.dumps(man, indent=1))
            manifests[model] = man
            new = sum(1 for r in res.values() if r["ok"] and not r.get("cached"))
            log(f"[{k}/{len(order)}] {model}: {'COMPLETE' if not errors else f'INCOMPLETE ({len(errors)} failed)'}; "
                f"{new} new files, {time.time() - t0:.0f} s; http {_stats}")
    return manifests


# ---------------------------------------------------------------- build the field's clean table and card

def complete_models(cell_dir):
    """Models whose manifest says complete, in the fetch order."""
    cell_dir = Path(cell_dir)
    order_file = cell_dir / "fetch_order.json"
    order = json.loads(order_file.read_text())["order"] if order_file.exists() else sorted(
        p.name for p in cell_dir.iterdir() if p.is_dir())
    out = []
    for m in order:
        p = cell_dir / m / "manifest.json"
        if p.exists() and json.loads(p.read_text()).get("complete"):
            out.append(m)
    return out


def load_model(cell_dir, model, cell):
    """One complete model's daily values from the cache, re-checked by the same guards. Returns (DataFrame, stats)."""
    man = json.loads((Path(cell_dir) / model / "manifest.json").read_text())
    frames, missing = [], 0
    for exp, info in man["experiments"].items():
        per_var = []
        for var, files in info["files"].items():
            das = parse_das(das_path(cell_dir, model, exp, var).read_text())
            for y in sorted(int(k) for k in files):
                p, vals, n_missing = validate_answer(csv_path(cell_dir, model, exp, var, y).read_text(), var, y, cell, das)
                missing += n_missing
                per_var.append(p["rows"][["year", "month", "day"]].assign(var=var, v=vals))
        long = pd.concat(per_var)
        days = {v: set(map(tuple, grp[["year", "month", "day"]].to_numpy())) for v, grp in long.groupby("var")}
        if len({frozenset(s) for s in days.values()}) != 1:
            raise g.DataGuardError(f"{model} {exp}: the variables do not cover the same model days")
        d = long.set_index(["year", "month", "day", "var"])["v"].unstack("var").rename(columns=COLUMN).reset_index()
        das0 = parse_das(das_path(cell_dir, model, exp, next(iter(info["files"]))).read_text())
        frames.append(d.assign(model=model, experiment=exp, calendar=das0.get("time", {}).get("calendar")))
    df = pd.concat(frames, ignore_index=True)[["model", "experiment", "year", "month", "day", "calendar"]
                                              + list(COLUMN.values())]
    return df, {"missing_values": missing, "manifest": man}


def build(field, data_dir=REPO / "data", cache_root=None, models=None):
    """data/clean/<field>/nexgddp_daily.parquet and data/cards/<field>/nexgddp.json from the complete models."""
    data_dir = Path(data_dir)
    cache_root = Path(cache_root or data_dir / "raw" / "nexgddp")
    cell = cell_centre(field["lat"], field["lon"])
    cell_dir = cache_root / cell_key(*cell)
    done = complete_models(cell_dir)
    if models is not None:
        done = [m for m in done if m in models]
    if not done:
        raise RuntimeError(f"no complete NEX-GDDP-CMIP6 model in {cell_dir}")
    frames, mans, missing = [], {}, 0
    for m in done:
        df, st = load_model(cell_dir, m, cell)
        frames.append(df)
        mans[m] = st["manifest"]
        missing += st["missing_values"]
    daily = pd.concat(frames, ignore_index=True)
    out = data_dir / "clean" / field["id"] / "nexgddp_daily.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    daily.to_parquet(out, index=False)
    order = json.loads((cell_dir / "fetch_order.json").read_text())
    others = {p.name: json.loads((p / "manifest.json").read_text()).get("left_out") or
              f"incomplete: {len(json.loads((p / 'manifest.json').read_text()).get('errors', {}))} file(s) failed"
              for p in cell_dir.iterdir() if p.is_dir() and (p / "manifest.json").exists() and p.name not in done}
    versions = sorted({f["version"] or "none" for man in mans.values() for e in man["experiments"].values()
                       for v in e["files"].values() for f in v.values()})
    km = 6371.0 * math.radians(1) * math.hypot(cell[0] - field["lat"],
                                               ((cell[1] - field["lon"] % 360)) * math.cos(math.radians(field["lat"])))
    first = mans[done[0]]["attributes"]
    card = g.make_card(
        dataset="nexgddp", product="NEX-GDDP-CMIP6 (NASA Earth Exchange Global Daily Downscaled Projections, CMIP6), "
                                   "daily, BCSD; NASA NCCS THREDDS NetcdfSubset point answers",
        version="file versions used: " + ", ".join(versions) + " (v2.0 where v1.x sits beside it; per file in each "
                "model's manifest)",
        variable=list(UNITS), units_in=UNITS,
        units_out={"pr_mm": "mm per model day (kg m-2 s-1 x 86400)", "tasmax_c": "deg C (K - 273.15)",
                   "tasmin_c": "deg C (K - 273.15)"},
        scale_factor=None, fill_values_removed={"1e20 (_FillValue / missing_value) or NaN": missing},
        quality_flags_used="none (the product has none)", records_dropped=missing,
        date_range={"historical": "1995-2014", "ssp245": "2026-2040", "ssp585": "2026-2040"},
        time_zone="model days in each model's own calendar (time stamps at 12:00 UTC); only monthly means are used",
        pixel_count=1,
        source="NASA Earth Exchange (NEX), NEX-GDDP-CMIP6 (Thrasher et al. 2022, Scientific Data 9, 262), via "
               "https://ds.nccs.nasa.gov/thredds (AMES/NEX/GDDP-CMIP6); model-based (downscaled climate projections)",
        resolution=f"0.25 deg (about 25 km): one grid cell, centre {cell[0]} N, {cell[1]} E",
        raw_attrs={k: v["raw"] for k, v in first.items()},
        location={"cell_lat": cell[0], "cell_lon_0_360": cell[1], "field_lat": field["lat"], "field_lon": field["lon"],
                  "field_to_cell_centre_km": round(km, 2), "cell": cell_key(*cell)},
        summary={"models_used": done, "n_models": len(done), "fetch_order": order["order"],
                 "fetch_order_seed": order["seed"], "left_out_or_incomplete": others, "left_out_by_rule": LEFT_OUT,
                 "per_model": {m: {"variants": {e: i["variant"] for e, i in man["experiments"].items()},
                                   "calendar": sorted({a["calendar"] for a in man["attributes"].values()}),
                                   "licence": sorted({str(a["licence"]) for a in man["attributes"].values()}),
                                   "file_version_attr": sorted({str(a["file_version"]) for a in man["attributes"].values()})}
                               for m, man in mans.items()},
                 "rows": len(daily)},
        notes="Rules: config/rules.yaml future (committed before the first download). Raw answers cached by cell in "
              f"data/raw/nexgddp/{cell_key(*cell)}/. Days are model days (360_day and noleap calendars have no real "
              "dates); the outlook uses monthly means only.")
    card_path = g.write_card(card, data_dir / "cards" / field["id"])
    return {"table": out, "card": card_path, "models": done, "others": others}


def main(argv=None):
    from pipeline.fetch.credits import ensure_credit
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.rules import load_rules
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--models", default=None, help="comma-separated subset (still in the seeded order)")
    ap.add_argument("--max-models", type=int, default=None)
    ap.add_argument("--build-only", action="store_true")
    a = ap.parse_args(argv)
    field, rules = load_field(a.field), load_rules()
    cache_root = REPO / "data" / "raw" / "nexgddp"
    cell = cell_centre(field["lat"], field["lon"])
    if not a.build_only:
        run_fetch(cell, cache_root, rules, a.workers, a.models.split(",") if a.models else None, a.max_models)
    r = build(field, REPO / "data", cache_root)
    ensure_credit(REPO / "CREDITS.md",
                  f"- NEX-GDDP-CMIP6 (NASA Earth Exchange; Thrasher et al. 2022), pr, tasmax, tasmin at the 0.25 deg cell "
                  f"{cell[0]} N, {cell[1]} E (field `{field['id']}`), historical 1995-2014 and ssp245 / ssp585 2026-2040, "
                  "fetched from 2026-11-14 via NASA NCCS THREDDS by pipeline/fetch/nexgddp.py (the 2040 outlook; the "
                  f"models used are listed in data/cards/{field['id']}/nexgddp.json)")
    log(f"{len(r['models'])} complete model(s): {r['models']}; others: {r['others']}\n-> {r['table']}\n-> {r['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
