"""Build step 2: NASA POWER daily point data for one field. Model-based (POWER reports its sources).

    .venv/bin/python -m pipeline.fetch.power --field demo        # 2001-01-01 to 2025-12-31

Decision D6 (owner, 2026-11-11): POWER supplies temperature, humidity, wind and sunshine to the
twin. The twin's rain comes from GPM IMERG (step 6); PRECTOTCORR is kept here only for
cross-checks. POWER days are local solar time (API header time_standard = "LST"); IMERG days are UTC.

Writes data/raw/power/<field>/<start>_<end>.json (one per calendar year, reused if present),
data/clean/<field>/power.parquet and data/cards/<field>/power.json.
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from pipeline.fetch import guards as g
from pipeline.fetch.credits import ensure_credit
from pipeline.fetch.fields import load_field

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
REPO = Path(__file__).resolve().parents[2]

# POWER parameter -> (clean column, unit the API must report, rule-12 guard kind; None = non-negative)
# Units as reported by the API's own `parameters` block, checked 2026-11-11 (DATA_AUDIT.md 1.1).
PARAMS = {
    "T2M_MAX": ("tmax_c", "C", "temp_c"),
    "T2M_MIN": ("tmin_c", "C", "temp_c"),
    "RH2M": ("rh_pct", "%", "rh_pct"),
    "WS2M": ("ws2m_ms", "m/s", None),
    "ALLSKY_SFC_SW_DWN": ("rs_mj_m2_day", "MJ/m^2/day", None),
    "PRECTOTCORR": ("rain_mm", "mm/day", "rain_mm"),
}
COLUMNS = ["date"] + [col for col, _, _ in PARAMS.values()]


def build_url(lat, lon, start, end):
    q = urllib.parse.urlencode({"parameters": ",".join(PARAMS), "community": "AG", "longitude": lon,
                                "latitude": lat, "start": start, "end": end, "format": "JSON"})
    return f"{API}?{q}"


def parse(payload):
    """POWER JSON -> (tidy daily table with unit-named columns, info for the data card)."""
    header = payload.get("header", {})
    fill = header.get("fill_value")
    if fill is None:
        raise g.DataGuardError("POWER header has no fill_value")
    units = payload.get("parameters", {})
    values = payload.get("properties", {}).get("parameter", {})
    raw_attrs = {}
    for p, (_, unit, _) in PARAMS.items():
        if p not in values or p not in units:
            raise g.DataGuardError(f"POWER response lacks parameter {p}")
        raw_attrs[p] = g.describe_raw_attrs({"units": units[p].get("units"), "_FillValue": fill})
        print(f"[power raw attrs] {p}: {raw_attrs[p]}")                      # rule 12a, before converting
        if units[p].get("units") != unit:
            raise g.DataGuardError(f"{p}: API reports units '{units[p].get('units')}', expected '{unit}'")
    dates = sorted(values["T2M_MAX"])
    for p in PARAMS:
        if sorted(values[p]) != dates:
            raise g.DataGuardError(f"{p}: its dates differ from T2M_MAX")
    data = {"date": pd.to_datetime(dates, format="%Y%m%d")}
    fill_removed = {}
    for p, (col, _, _) in PARAMS.items():
        raw = np.array([values[p][d] for d in dates], dtype=float)
        data[col], fill_removed[col] = g.mask_fill(raw, [fill])
    coords = payload.get("geometry", {}).get("coordinates", [])
    info = {
        "api_version": header.get("api", {}).get("version"),
        "sources": header.get("sources", []),
        "fill_value": fill,
        "time_standard": header.get("time_standard"),
        "units_in": {p: units[p]["units"] for p in PARAMS},
        "raw_attrs": raw_attrs,
        "fill_removed": fill_removed,
        "cell_elevation_m": coords[2] if len(coords) > 2 else None,
    }
    return pd.DataFrame(data)[COLUMNS], info


def check(df):
    """Rule 12b/c guards on a clean table. Returns {column: values warned about}."""
    d = df["date"]
    if d.duplicated().any():
        raise g.DataGuardError(f"{int(d.duplicated().sum())} repeated day(s), e.g. {d[d.duplicated()].iloc[0].date()}")
    want = pd.date_range(d.min(), d.max(), freq="D")
    if len(want) != len(d):
        gaps = want.difference(pd.DatetimeIndex(d))
        raise g.DataGuardError(f"{len(gaps)} missing day(s), e.g. {gaps[0].date()}")
    warned = g.check_table(df, {col: kind for col, _, kind in PARAMS.values() if kind})
    for col, _, kind in PARAMS.values():
        if kind is None:
            g.assert_nonnegative(df[col].to_numpy(), col)
    return warned


def year_chunks(start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    out = []
    for y in range(s.year, e.year + 1):
        a, b = max(s, pd.Timestamp(y, 1, 1)), min(e, pd.Timestamp(y, 12, 31))
        out.append((a.strftime("%Y%m%d"), b.strftime("%Y%m%d")))
    return out


def _http_get_json(url, tries=3):
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, timeout=180, headers={"User-Agent": "khet-sathi-pipeline"})
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == tries:
                raise
            time.sleep(5 * attempt)


def same_cell(a, b):
    """Do two points fall in the same POWER cells (0.5 x 0.625 deg meteorology, 1 x 1 deg solar)? Pure."""
    return (round(a["lat"] / 0.5) == round(b["lat"] / 0.5) and round(a["lon"] / 0.625) == round(b["lon"] / 0.625)
            and a["lat"] // 1 == b["lat"] // 1 and a["lon"] // 1 == b["lon"] // 1)


def fetch(field, start="2001-01-01", end="2025-12-31", data_dir=REPO / "data", get_json=_http_get_json,
          credits_path=None, point=None):
    """`point`: another field whose cached POWER point this field reads (config power_point_of): the same cells, never
    downloaded."""
    fid, data_dir = field["id"], Path(data_dir)
    if point is not None and not same_cell(field, point):
        raise g.DataGuardError(f"power_point_of {point['id']}: its point is not in this field's POWER cells")
    pt = point or field
    raw_dir = data_dir / "raw" / "power" / pt["id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    frames, infos = [], []
    for s, e in year_chunks(start, end):
        cache = raw_dir / f"{float(pt['lat']):.6f}_{float(pt['lon']):.6f}" / f"{s}_{e}.json"   # per point
        if point is not None and not cache.exists():
            raise g.DataGuardError(f"power_point_of {point['id']}: {cache} is not cached (this field never downloads)")
        payload = json.loads(cache.read_text()) if cache.exists() else get_json(build_url(field["lat"], field["lon"], s, e))
        df, info = parse(payload)
        want = pd.date_range(pd.Timestamp(s), pd.Timestamp(e), freq="D")
        if len(df) != len(want) or (df["date"].to_numpy() != want.to_numpy()).any():
            raise g.DataGuardError(f"POWER returned dates {df['date'].min().date()} to {df['date'].max().date()} "
                                   f"for a request of {s} to {e}")
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(payload))                              # cache only what passed
        frames.append(df)
        infos.append(info)
    for key in ("time_standard", "fill_value", "units_in", "api_version"):
        if any(i[key] != infos[0][key] for i in infos):
            raise g.DataGuardError(f"POWER responses disagree on {key} across years")

    table = pd.concat(frames, ignore_index=True)
    warned = check(table)
    clean_dir = data_dir / "clean" / fid
    clean_dir.mkdir(parents=True, exist_ok=True)
    table_path = clean_dir / "power.parquet"
    table.to_parquet(table_path, index=False)

    info = infos[0]
    fill_counts = {col: sum(i["fill_removed"][col] for i in infos) for col in info["fill_removed"]}
    card = g.make_card(
        dataset="power",
        product="NASA POWER Daily API, point endpoint, community AG",
        version=info["api_version"],
        variable=list(PARAMS),
        units_in=info["units_in"],
        units_out={p: col for p, (col, _, _) in PARAMS.items()},
        scale_factor=None,
        fill_values_removed={"fill_value": info["fill_value"], "count_by_column": fill_counts},
        quality_flags_used="none: the POWER response carries no per-value quality flag (TODO-VERIFY in POWER docs)",
        records_dropped=0,
        date_range=[str(table["date"].min().date()), str(table["date"].max().date())],
        time_zone=f"{info['time_standard']} (local solar time; from the API header time_standard)",
        pixel_count=1,
        source=f"NASA POWER, model-based (sources reported by the API: {', '.join(info['sources'])})",
        resolution=("0.5 x 0.625 deg meteorology (MERRA-2; GEOS-IT for the latest 1-3 months); 1 x 1 deg solar "
                    "(CERES SYN1deg Ed. 4.2 from 2001; FLASHFlux 4A for the latest 3-4 months). Source: POWER methodology docs"),
        raw_attrs=info["raw_attrs"],
        range_warnings=warned,
        location={"lat": field["lat"], "lon": field["lon"], "elevation_m": info["cell_elevation_m"],
                  "elevation_source": "POWER grid cell (API geometry)"},
        notes=((f"The cached point request of field {pt['id']} ({pt['lat']}, {pt['lon']}; config power_point_of): the same "
                f"POWER cells as this field's {field['lat']}, {field['lon']}, so the same values; nothing downloaded. "
                if point is not None else "") +
               f"Point request at {pt['lat']}, {pt['lon']}; one grid cell, so pixel_count is 1. POWER cell "
               f"elevation {info['cell_elevation_m']} m (not the field's). Every day kept; fill values became "
               "missing values. D6: rain for the twin comes from GPM IMERG; PRECTOTCORR is for cross-checks only."),
    )
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        ensure_credit(credits_path, f"- NASA POWER Daily API {info['api_version']} (model-based), field `{fid}`, "
                                    f"{card['date_range'][0]} to {card['date_range'][1]}, fetched {dt.date.today()}")
    return {"table": table_path, "card": card_path, "rows": len(table), "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--start", default="2001-01-01")
    ap.add_argument("--end", default="2025-12-31")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    src = field.get("power_point_of")   # the point the other field's own POWER table used (its card), not its centre
    point = {"id": src, **json.loads((REPO / "data" / "cards" / src / "power.json").read_text())["location"]} if src else None
    out = fetch(field, a.start, a.end, credits_path=REPO / "records" / "credits.txt", point=point)
    c = out["card_data"]
    print(f"\n{out['rows']} daily rows -> {out['table']}\ncard -> {out['card']}")
    print(f"date range {c['date_range']}, fill removed {c['fill_values_removed']['count_by_column']}, "
          f"range warnings {c['range_warnings']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
