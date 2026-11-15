"""NOAA NCEI GHCN-Daily station record: validation, and (decision A) the reference for correcting
POWER temperature. Its rain is never a model input.

    .venv/bin/python -m pipeline.fetch.ghcn --field demo

Station from config/fields/<field>.yaml `validation_station`. Format and units: GHCN-Daily readme,
Version 3.35 (PRCP tenths of mm; TMAX, TMIN tenths of degrees C; missing = -9999), and
readme-by_station.txt (ID, YYYYMMDD, ELEMENT, VALUE, M-FLAG, Q-FLAG, S-FLAG, OBS-TIME).
A value with any Q-FLAG (failed a quality check) is dropped and counted.

S-FLAG (REVIEW_NOTES H2): kept per value (columns sflag_rain_mm, sflag_tmax_c, sflag_tmin_c) and counted per
element in the card. For Kathmandu Airport every 2001-2025 record is "S" (Global Summary of the Day), which
the readme describes as SFLAG_S_CAVEAT below: label station rain "synoptic-derived, use with caution"
wherever it is used as truth. Day boundary: S values are GSOD summaries "based on Greenwich Mean Time (GMT,
0000Z - 2359Z)" (GSOD readme, NCEI 10/28/2020), i.e. 05:45-05:45 Nepal time; PRCP "may include latter part of
previous day".
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
SFLAG_S_CAVEAT = ("derived from hourly synoptic reports exchanged on the GTS. Daily values derived in this fashion may "
                  "differ significantly from 'true' daily data, particularly for precipitation (i.e., use with caution).")
SFLAG_NAMES = {"S": "Global Summary of the Day (NCDC DSI-9618)"}       # GHCN-Daily readme v3.35, S-FLAG table
DAY_BOUNDARY = ("Day boundary: S-flag values are GSOD summaries on "
                "the GMT day (0000Z - 2359Z), i.e. {local}, and GSOD PRCP 'may include latter part of "
                "previous day' (GSOD readme, NCEI 10/28/2020). A best day-alignment lag of 0 against POWER shows only that "
                "no whole-day shift does better, not that the day boundaries match")


def day_boundary_text(utc_offset=None):
    """The station-day caveat in the field's local time (config `utc_offset`; none = the demo, Nepal)."""
    from pipeline.fetch.gpm import local_day_label
    return DAY_BOUNDARY.format(local=local_day_label(utc_offset))


def parse(text, station):
    rows = {col: {} for col, _ in ELEMENTS.values()}
    sflags = {col: {} for col, _ in ELEMENTS.values()}
    qc, missing, raw_count = ({col: 0 for col, _ in ELEMENTS.values()} for _ in range(3))
    source_flags = {}
    obs_time_present = 0
    for r in csv.reader(io.StringIO(text)):
        if not r:
            continue
        sid, date, elem, value, _m, qflag = r[:6]
        sflag = r[6].strip() if len(r) > 6 else ""
        if sid != station:
            raise g.DataGuardError(f"row for station {sid} in the file for station {station}")
        if elem not in ELEMENTS or not (YEARS[0] <= int(date[:4]) <= YEARS[1]):
            continue
        col = ELEMENTS[elem][0]
        raw_count[col] += 1
        counts = source_flags.setdefault(elem, {})
        counts[sflag or "blank"] = counts.get(sflag or "blank", 0) + 1
        obs_time_present += bool(len(r) > 7 and r[7].strip())
        if int(value) == MISSING:
            missing[col] += 1
        elif qflag.strip():
            qc[col] += 1
        else:
            rows[col][pd.Timestamp(date)] = int(value) * TENTHS
            sflags[col][pd.Timestamp(date)] = sflag or None
    dates = sorted(set().union(*[set(v) for v in rows.values()]))
    df = pd.DataFrame({"date": pd.DatetimeIndex(dates)})
    for col, values in rows.items():
        df[col] = [values.get(d, np.nan) for d in dates]
    for col, flags in sflags.items():
        df[f"sflag_{col}"] = pd.Series([flags.get(d) for d in dates], dtype="object")
    info = {"qc_dropped": qc, "missing_dropped": missing, "raw_records": raw_count,
            "obs_time_present": obs_time_present,
            "source_flags": {e: dict(sorted(c.items())) for e, c in sorted(source_flags.items())}}
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
        quality_flags_used={"q_flag": "any non-blank Q-FLAG dropped",
                            "s_flag": "kept per value (sflag_<column>), not filtered; counts below are records read, 2001-2025",
                            "source_flags": info["source_flags"],
                            "s_flag_names": {k: v for k, v in SFLAG_NAMES.items()
                                             if any(k in c for c in info["source_flags"].values())}},
        records_dropped=info["qc_dropped"],
        date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone=(f"station observation day; OBS-TIME given on {info['obs_time_present']} of "
                   f"{sum(info['raw_records'].values())} records used. " + day_boundary_text(field.get("utc_offset"))),
        pixel_count=("n/a: one station point; distance to the field TODO-VERIFY (the station's coordinates are in "
                     "ghcnd-stations.txt, which is not cached)"),
        source=f"NOAA NCEI GHCN-Daily station {station} (ground station)", resolution="point",
        raw_attrs={"units": "tenths (readme v3.35)", "scale_factor": TENTHS, "add_offset": "ABSENT",
                   "_FillValue": MISSING, "valid_range": "ABSENT"},
        range_warnings=warned,
        notes=(("Validation; also the reference for decision A (POWER temperature correction). " if field.get("correction_label")
                else "Validation only: the field config has no correction_label, so decision A does not use it. ")
               + f"Its rain is never a "
               f"model input. Records per year (PRCP): {records_per_year(df, 'rain_mm')}. S-FLAG counts (records read, "
               f"2001-2025): {info['source_flags']}. "
               + ("GHCN-Daily readme v3.35 on S-flag values: \"" + SFLAG_S_CAVEAT + "\" Station rain and temperature "
                  "used as truth must be labelled synoptic-derived, use with caution."
                  if any("S" in c for c in info["source_flags"].values()) else "")),
    )
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        use = "validation; temperature correction A" if field.get("correction_label") else "validation only"
        ensure_credit(credits_path, f"- NOAA NCEI GHCN-Daily v3.35, station {station} ({use}), "
                                    f"field `{fid}`, {card['date_range'][0]} to {card['date_range'][1]}, fetched {dt.date.today()}")
    return {"table": out, "card": card_path, "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    field = load_field(ap.parse_args(argv).field)
    station = field.get("validation_station")
    if not station:
        sys.exit(f"config/fields/{field['id']}.yaml has no validation_station")
    out = fetch(field, station, credits_path=REPO / "records" / "credits.txt")
    c = out["card_data"]
    print(f"-> {out['table']}\n-> {out['card']}\nqc dropped {c['records_dropped']}, missing {c['fill_values_removed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
