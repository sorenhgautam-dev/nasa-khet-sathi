"""FAOSTAT national crop yields for Nepal (rice, wheat, maize), 2001 on: validation layer 4.3 only
(do the twin's good and bad years match the country's ups and downs?). Never shown to farmers as mass
per area (golden rule 11).

    .venv/bin/python -m pipeline.fetch.faostat --field demo

Source: FAOSTAT domain QCL "Production: Crops and livestock products", public bulk file (the FAOSTAT
API now needs an authorization token; checked 2026-11-11). Nepal is Area Code 149; items 27 Rice,
15 Wheat, 56 Maize (corn); element "Yield". Flags (A official, E estimated, I imputed, ...) are kept.
"""
import argparse
import csv
import datetime as dt
import io
import sys
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

from pipeline.fetch import guards as g
from pipeline.fetch.credits import ensure_credit
from pipeline.fetch.fields import load_field

URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip"
MEMBER = "Production_Crops_Livestock_E_All_Data_(Normalized).csv"
REPO = Path(__file__).resolve().parents[2]
AREA = "149"                                       # Nepal
ITEMS = {"27": "rice", "15": "wheat", "56": "maize"}
TO_KG_HA = {"kg/ha": 1.0, "hg/ha": 0.1}            # 1 hg = 0.1 kg
FIRST_YEAR = 2001


def parse(rows):
    out, flags, units = [], Counter(), set()
    for r in rows:
        if r["Area Code"] != AREA or r["Item Code"] not in ITEMS or r["Element"] != "Yield":
            continue
        year = int(r["Year"])
        if year < FIRST_YEAR or not r["Value"]:
            continue
        unit = r["Unit"]
        if unit not in TO_KG_HA:
            raise g.DataGuardError(f"FAOSTAT yield unit '{unit}' is not one we know how to convert")
        units.add(unit)
        flags[r["Flag"] or "(blank)"] += 1
        out.append({"year": year, "crop": ITEMS[r["Item Code"]], "item": r["Item"],
                    "yield_kg_ha": float(r["Value"]) * TO_KG_HA[unit], "flag": r["Flag"]})
    df = pd.DataFrame(out, columns=["year", "crop", "item", "yield_kg_ha", "flag"])
    if df.duplicated(["year", "crop"]).any():
        raise g.DataGuardError("repeated year and crop in FAOSTAT rows")
    if (df["yield_kg_ha"] <= 0).any():
        raise g.DataGuardError("FAOSTAT yield of zero or less")
    return df.sort_values(["crop", "year"]).reset_index(drop=True), {"units_in": sorted(units), "flags": dict(flags)}


def _http_get_bytes(url):
    r = requests.get(url, timeout=600, headers={"User-Agent": "khet-sathi-pipeline"})
    r.raise_for_status()
    return r.content


def fetch(field, data_dir=REPO / "data", get_bytes=_http_get_bytes, credits_path=None):
    fid, data_dir = field["id"], Path(data_dir)
    raw = data_dir / "raw" / "faostat" / "QCL_All_Data_Normalized.zip"
    raw.parent.mkdir(parents=True, exist_ok=True)
    blob = raw.read_bytes() if raw.exists() else get_bytes(URL)
    with zipfile.ZipFile(io.BytesIO(blob)) as z, z.open(MEMBER) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        print(f"[faostat raw attrs] columns: {reader.fieldnames}")
        df, info = parse(reader)
    if not raw.exists():
        raw.write_bytes(blob)
    out = data_dir / "clean" / fid / "faostat_yields.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    card = g.make_card(
        dataset="faostat_yields", product="FAOSTAT QCL, Production: Crops and livestock products (bulk, normalized)",
        version=f"bulk file fetched {dt.date.today()}", variable=["Yield: " + ", ".join(sorted(df['item'].unique()))],
        units_in=info["units_in"], units_out="yield_kg_ha", scale_factor=None,
        fill_values_removed="none: empty values skipped", quality_flags_used=f"kept, not filtered: {info['flags']}",
        records_dropped=0, date_range=[str(df['year'].min()), str(df['year'].max())] if len(df) else [],
        time_zone="n/a: calendar-year national values", pixel_count="n/a: national (Nepal, FAOSTAT area 149)",
        source="FAOSTAT (FAO), national statistics", resolution="country, yearly",
        raw_attrs={"units": info["units_in"], "scale_factor": "ABSENT", "add_offset": "ABSENT",
                   "_FillValue": "ABSENT", "valid_range": "ABSENT"},
        notes="Validation layer 4.3 only (year-to-year ups and downs). Never shown to farmers as mass per area.")
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        ensure_credit(credits_path, f"- FAOSTAT QCL bulk file (FAO), Nepal rice, wheat and maize yields, "
                                    f"{card['date_range'][0]} to {card['date_range'][1]}, fetched {dt.date.today()} (validation only)")
    return {"table": out, "card": card_path, "card_data": card, "rows": len(df)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    out = fetch(load_field(ap.parse_args(argv).field), credits_path=REPO / "CREDITS.md")
    c = out["card_data"]
    print(f"{out['rows']} rows -> {out['table']}\nunits {c['units_in']}, years {c['date_range']}, flags {c['quality_flags_used']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
