"""NOAA CPC Oceanic Nino Index (ONI): the El Nino / La Nina state of each 3-month season, for the 25-Year Replay
(rules.yaml window_replay.enso). A few KB of text; US government work, public domain.

    .venv/bin/python -m pipeline.fetch.oni --field demo

Format (the file's own header): SEAS YR TOTAL ANOM, one line per overlapping 3-month season (DJF, JFM, ... NDJ);
TOTAL is the Nino-3.4 sea-surface temperature and ANOM its anomaly, both deg C (ERSST.v5, 3-month running means).
The raw file is cached once in data/raw/oni/ (it is the same for every field); the clean table and card are per field.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import requests

from pipeline.fetch import guards as g
from pipeline.fetch.credits import ensure_credit
from pipeline.fetch.fields import load_field

URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
REPO = Path(__file__).resolve().parents[2]
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]   # middle months 1..12
HEADER = ["SEAS", "YR", "TOTAL", "ANOM"]


def parse(text):
    """The ONI table as [season, year, total_c, anom_c]; any line that does not fit the format stops (rule 12c)."""
    lines = [ln.split() for ln in text.splitlines() if ln.strip()]
    if not lines or lines[0] != HEADER:
        raise g.DataGuardError(f"ONI file header is {lines[0] if lines else 'missing'}, expected {HEADER}")
    rows = []
    for n, parts in enumerate(lines[1:], 2):
        if len(parts) != 4 or parts[0] not in SEASONS:
            raise g.DataGuardError(f"ONI file line {n} does not fit 'SEAS YR TOTAL ANOM': {parts}")
        rows.append({"season": parts[0], "year": int(parts[1]), "total_c": float(parts[2]), "anom_c": float(parts[3])})
    df = pd.DataFrame(rows)
    if df.duplicated(["season", "year"]).any():
        raise g.DataGuardError("ONI file repeats a season")
    return df


def last_season_before(df, day):
    """The latest season in the table whose 3 months end before `day`'s month (rules.yaml window_replay.enso.season_now)."""
    day = pd.Timestamp(day)
    end = df["year"] * 12 + df["season"].map(SEASONS.index) + 2    # the season's last month, counted from year 0 (NDJ: next Jan)
    ok = df[end < day.year * 12 + day.month]
    if ok.empty:
        raise ValueError(f"no ONI season ends before {day.date()}")
    return ok.iloc[(end[ok.index]).argmax()]


def state(anom_c, threshold_c):
    """el_nino at or above +threshold, la_nina at or below -threshold, else neutral (NOAA CPC)."""
    return "el_nino" if anom_c >= threshold_c else "la_nina" if anom_c <= -threshold_c else "neutral"


def _http_get_bytes(url):
    r = requests.get(url, timeout=120, headers={"User-Agent": "khet-sathi-pipeline"})
    r.raise_for_status()
    return r.content


def fetch(field, data_dir=REPO / "data", get_bytes=_http_get_bytes, credits_path=None, refresh=False):
    fid, data_dir = field["id"], Path(data_dir)
    raw = data_dir / "raw" / "oni" / "oni.ascii.txt"
    raw.parent.mkdir(parents=True, exist_ok=True)
    blob = get_bytes(URL) if refresh or not raw.exists() else raw.read_bytes()
    attrs = {"units": "deg C (TOTAL: Nino-3.4 SST; ANOM: its anomaly), CPC header SEAS YR TOTAL ANOM",
             "scale_factor": "ABSENT", "add_offset": "ABSENT", "_FillValue": "ABSENT", "valid_range": "ABSENT"}
    print(f"[oni raw attrs] {g.describe_raw_attrs(attrs)}")
    df = parse(blob.decode())
    raw.write_bytes(blob)
    warned = g.check_table(df.rename(columns={"total_c": "total", "anom_c": "anom"}), {"total": "temp_c", "anom": "temp_c"})
    out = data_dir / "clean" / fid / "oni.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    first, last = df.iloc[0], df.iloc[-1]
    card = g.make_card(
        dataset="oni", product="NOAA CPC Oceanic Nino Index (ONI), oni.ascii.txt", version=f"as fetched {dt.date.today()}",
        variable=["TOTAL", "ANOM"], units_in={"TOTAL": "deg C", "ANOM": "deg C"}, units_out={"TOTAL": "total_c", "ANOM": "anom_c"},
        scale_factor=None, fill_values_removed={"fill_value": "none documented", "count": 0},
        quality_flags_used="none in the file", records_dropped=0,
        date_range=[f"{first['season']} {first['year']}", f"{last['season']} {last['year']}"],
        time_zone="3-month seasons (calendar months)", pixel_count="n/a: one index for the Nino-3.4 region (5N-5S, 170W-120W)",
        source="NOAA Climate Prediction Center (US government, public domain)", resolution="Nino-3.4 region of the Pacific",
        raw_attrs=attrs, range_warnings=warned,
        notes=(f"{len(df)} seasons. ERSST.v5 3-month running means; anomalies against 30-year base periods updated every "
               "5 years (CPC). Used only for the 25-Year Replay's El Nino / La Nina highlight (rules.yaml window_replay.enso)."))
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        ensure_credit(credits_path, f"- NOAA CPC Oceanic Nino Index (ONI), {URL} (public domain), field `{fid}`, "
                                    f"{card['date_range'][0]} to {card['date_range'][1]}, fetched {dt.date.today()}")
    return {"table": out, "card": card_path, "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--refresh", action="store_true", help="download again even if data/raw/oni/oni.ascii.txt exists")
    a = ap.parse_args(argv)
    out = fetch(load_field(a.field), credits_path=REPO / "records" / "credits.txt", refresh=a.refresh)
    print(f"-> {out['table']}\n-> {out['card']}\n{out['card_data']['date_range']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
