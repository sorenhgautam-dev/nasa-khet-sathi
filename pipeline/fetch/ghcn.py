"""NOAA NCEI GHCN-Daily station record, for validation only (never a model input).

    .venv/bin/python -m pipeline.fetch.ghcn --field demo

Station from config/fields/<field>.yaml `validation_station`. Format and units: GHCN-Daily readme,
Version 3.35 (PRCP tenths of mm; TMAX, TMIN tenths of degrees C; missing = -9999), and
readme-by_station.txt (ID, YYYYMMDD, ELEMENT, VALUE, M-FLAG, Q-FLAG, S-FLAG, OBS-TIME).
A value with any Q-FLAG (failed a quality check) is dropped and counted.
"""
import argparse
import csv
import datetime as dt
import gzip
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from pipeline.fetch import guards as g
from pipeline.fetch.credits import ensure_credit
from pipeline.fetch.fields import load_field

URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/{station}.csv.gz"
REPO = Path(__file__).resolve().parents[2]
ELEMENTS = {"PRCP": ("rain_mm", "rain_mm"), "TMAX": ("tmax_c", "temp_c"), "TMIN": ("tmin_c", "temp_c")}
TENTHS = 0.1
MISSING = -9999
YEARS = (2001, 2025)


def parse(text, station):
    rows = {col: {} for col, _ in ELEMENTS.values()}
    qc, missing, raw_count = ({col: 0 for col, _ in ELEMENTS.values()} for _ in range(3))
    obs_time_present = 0
    for r in csv.reader(io.StringIO(text)):
        if not r:
            continue
        sid, date, elem, value, _m, qflag = r[:6]
        if sid != station:
            raise g.DataGuardError(f"row for station {sid} in the file for station {station}")
        if elem not in ELEMENTS or not (YEARS[0] <= int(date[:4]) <= YEARS[1]):
            continue
        col = ELEMENTS[elem][0]
        raw_count[col] += 1
        obs_time_present += bool(len(r) > 7 and r[7].strip())
        if int(value) == MISSING:
            missing[col] += 1
        elif qflag.strip():
            qc[col] += 1
        else:
            rows[col][pd.Timestamp(date)] = int(value) * TENTHS
    dates = sorted(set().union(*[set(v) for v in rows.values()]))
    df = pd.DataFrame({"date": pd.DatetimeIndex(dates)})
    for col, values in rows.items():
        df[col] = [values.get(d, np.nan) for d in dates]
    info = {"qc_dropped": qc, "missing_dropped": missing, "raw_records": raw_count,
            "obs_time_present": obs_time_present}
    return df, info


def check(df):
    return g.check_table(df, {col: kind for col, kind in ELEMENTS.values()})


def records_per_year(df, col):
    present = df.loc[df[col].notna(), "date"].dt.year
    return {int(y): int(n) for y, n in present.value_counts().sort_index().items()}


def _http_get_bytes(url):
    r = requests.get(url, timeout=300, headers={"User-Agent": "khet-sathi-pipeline"})
    r.raise_for_status()
    return r.content


def fetch(field, station, data_dir=REPO / "data", get_bytes=_http_get_bytes, credits_path=None):
    fid, data_dir = field["id"], Path(data_dir)
    raw = data_dir / "raw" / "ghcn" / f"{station}.csv.gz"
    raw.parent.mkdir(parents=True, exist_ok=True)
    blob = raw.read_bytes() if raw.exists() else get_bytes(URL.format(station=station))
    print(f"[ghcn raw attrs] {station}: {g.describe_raw_attrs({'units': 'PRCP tenths of mm; TMAX/TMIN tenths of deg C (readme v3.35)', '_FillValue': MISSING})}")
    df, info = parse(gzip.decompress(blob).decode(), station)
    if not raw.exists():
        raw.write_bytes(blob)
    warned = check(df)
    out = data_dir / "clean" / fid / f"ghcn_{station}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    card = g.make_card(
        dataset=f"ghcn_{station}", product="NOAA NCEI GHCN-Daily, by_station CSV", version="3.35 (readme, 2026-11-11)",
        variable=list(ELEMENTS), units_in={"PRCP": "tenths of mm", "TMAX": "tenths of deg C", "TMIN": "tenths of deg C"},
        units_out={e: c for e, (c, _) in ELEMENTS.items()}, scale_factor=TENTHS,
        fill_values_removed={"fill_value": MISSING, "count_by_column": info["missing_dropped"]},
        quality_flags_used="any non-blank Q-FLAG dropped", records_dropped=info["qc_dropped"],
        date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone=(f"station observation day; OBS-TIME given on {info['obs_time_present']} of "
                   f"{sum(info['raw_records'].values())} records used (day boundary TODO-VERIFY)"),
        pixel_count="n/a: one station point, about 7 km from the demo field",
        source=f"NOAA NCEI GHCN-Daily station {station} (ground station)", resolution="point",
        raw_attrs={"units": "tenths (readme v3.35)", "scale_factor": TENTHS, "add_offset": "ABSENT",
                   "_FillValue": MISSING, "valid_range": "ABSENT"},
        range_warnings=warned,
        notes=f"Validation only. Records per year (PRCP): {records_per_year(df, 'rain_mm')}",
    )
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        ensure_credit(credits_path, f"- NOAA NCEI GHCN-Daily v3.35, station {station} (validation only), "
                                    f"field `{fid}`, {card['date_range'][0]} to {card['date_range'][1]}, fetched {dt.date.today()}")
    return {"table": out, "card": card_path, "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    field = load_field(ap.parse_args(argv).field)
    station = field.get("validation_station")
    if not station:
        sys.exit(f"config/fields/{field['id']}.yaml has no validation_station")
    out = fetch(field, station, credits_path=REPO / "CREDITS.md")
    c = out["card_data"]
    print(f"-> {out['table']}\n-> {out['card']}\nqc dropped {c['records_dropped']}, missing {c['fill_values_removed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
