"""Weather ahead (owner, 2026-11-14 evening; rules.yaml weather_ahead): the optional 'weather' block of
site/data/fields/<field>.json, with its per-year detail and checks in data/checks/<field>/weather.json.

    .venv/bin/python scripts/run_weather.py --field demo

Reads the field file's plans and current options (so it runs after the 'export' step), the twin's weather
(data/clean/<field>/weather.parquet) and its rain versions, and adds the block to the field file; nothing else in the
file changes. Bikram Sambat months are Nepal's: a field outside Nepal gets no block.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.diary import weather_ahead as wa  # noqa: E402
from pipeline.export.build_replay import plans_of  # noqa: E402
from pipeline.export.validate import validate_field  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402

OTHER_RAIN = ("untuned", "dhm", "uncorrected")
SOURCES = [
    {"name": "NASA POWER", "product": "Daily API, T2M_MAX and T2M_MIN, corrected to Kathmandu Airport (monthly offset; "
                                      "frost nights by quantile mapping)", "resolution": "0.5 x 0.625 deg",
     "years": "2001-2025", "type": "model"},
    {"name": "GPM IMERG", "product": "GPM_3IMERGDF V07, break-corrected and gauge-tuned (the twin's rain)",
     "resolution": "0.1 deg", "years": "2001-2025", "type": "satellite"},
]
LIMITS = [
    {"name": "FAO, Bread Wheat: Improvement and Production (2002), ch. 3 and Table 3.1",
     "says": "wheat: above 30 C during floret formation (days 20-100 after sowing); frost below 0 C from heading to ten days after flowering (days 90-110)"},
    {"name": "FAO Irrigation and Drainage Paper 66 (2012)", "says": "wheat above 34 C at grain filling; potato heat 35 C or more, cold 1 C or less"},
    {"name": "FAO Irrigation and Drainage Paper 56 (1998), ch. 6", "says": "the crop stages: sowing weeks, flowering and grain fill, harvest weeks"},
    {"name": "DHM, Update of Climate Change Study of Nepal (2024), Table 6", "says": "a dry day has under 1 mm of rain; the longest run of dry days"},
    {"name": "ETCCDI R20mm", "says": "a day of 20 mm or more (DHM calls 50 mm or more heavy)"},
]


def plan_crops(doc):
    """Each crop and sowing day once, in the order of the field's plans."""
    out, seen = [], set()
    for _, _, crops in plans_of(doc):
        for c in crops:
            k = (c["crop"], c["start"], c["end"])
            if k not in seen:
                seen.add(k)
                out.append({"crop": c["crop"], "start": c["start"], "end": c["end"]})
    return out


def _known_events():
    import yaml
    return yaml.safe_load((REPO / "config" / "known_events.yaml").read_text())["events"]


def _normals(station="Bhaktapur"):
    df = pd.read_csv(REPO / "config" / "dhm_normals_1991_2020.csv")
    d = df[(df["station"] == station) & (df["variable"] == "precip_mm") & (df["month"] != "annual")]
    return [float(d[d["month"].astype(str) == str(m)]["value"].iloc[0]) for m in range(1, 13)]


def checks(w, blocks, r):
    """rules.yaml weather_ahead.checks (VALIDATION.md): checks only, nothing here changes the block."""
    words = r["weather_ahead"]["rain_word"]["words"]
    out = {}
    # rain words against DHM's Bhaktapur normals: blocks (half of each month and the next) and calendar months
    nm = _normals()
    dhm_blocks = wa.words12([(nm[i] + nm[(i + 1) % 12]) / 2 for i in range(12)], words)
    ours = [b["usual"]["rain"] for b in blocks]
    cal = w.assign(m=w["date"].dt.month, y=w["date"].dt.year).groupby(["y", "m"])["rain_mm"].sum().groupby("m").mean()
    ours_cal, dhm_cal = wa.words12(cal.to_list(), words), wa.words12(nm, words)
    out["rain_words"] = {
        "blocks": {"agree": sum(a == b for a, b in zip(ours, dhm_blocks)), "of": 12,
                   "differ": [{"block": b["key"], "ours": a, "dhm": d} for b, a, d in zip(blocks, ours, dhm_blocks) if a != d]},
        "calendar_months": {"agree": sum(a == b for a, b in zip(ours_cal, dhm_cal)), "of": 12,
                            "differ": [{"month": wa.KEYS[i], "ours": a, "dhm": d}
                                       for i, (a, d) in enumerate(zip(ours_cal, dhm_cal)) if a != d]}}
    # frost: the band of the block holding each known frost event, typical and in the event's own year
    ev = _known_events()
    sd = int(r["weather_ahead"]["blocks"]["starts_on_day"])
    bm, by = wa.block_of(w["date"], sd)
    mo = r["months"]
    frost = []
    # the day each event names (known_events.yaml summary); an event naming only "Jan" is tested in both blocks January touches
    days = {"cold_wave_2013_01": ["2013-01-08"], "cold_night_2010_01": ["2010-01-12"], "cold_wave_2018_01": ["2018-01-01", "2018-01-31"]}
    for e in ev:
        if e.get("category") != "frost" or e["id"] not in days:
            continue
        for d in days[e["id"]]:
            day = pd.Timestamp(d)
            m, y = wa.block_of([day], sd)
            m, y = int(m[0]), int(y[0])
            blk = next(b for b in blocks if b["key"] == wa.KEYS[m - 1])
            cold = float(w["tmin_frost_c"].to_numpy(float)[(bm == m) & (by == y)].min())
            frost.append({"event": e["id"], "valley": e.get("kathmandu_valley"), "date_used": str(day.date()),
                          "block": blk["key"], "typical_band": blk["usual"]["frost"],
                          "event_year_band": wa.frost_band(cold, float(mo["frost_c"]), float(mo["frost_risk_c"])),
                          "event_year_coldest_frost_c": round(cold, 1)})
    out["frost"] = frost
    # floods: a day of 20 mm or more on the event's dates or one day either side
    big = float(r["trends"]["heavy_rain_mm"])
    flood_days = {"kathmandu_flood_2002_07": ("2002-07-22", "2002-07-23"), "terai_floods_2017_08": ("2017-08-11", "2017-08-13"),
                  "melamchi_flood_2021_06": ("2021-06-15", "2021-06-15"), "unseasonal_rain_2021_10": ("2021-10-17", "2021-10-19"),
                  "kathmandu_floods_2024_09": ("2024-09-26", "2024-09-28"), "harvest_rain_2025_10": ("2025-10-03", "2025-10-05")}
    floods = []
    for e in ev:
        if e.get("category") != "flood" or e["id"] not in flood_days:
            continue
        a, b = (pd.Timestamp(x) for x in flood_days[e["id"]])
        s = w[(w["date"] >= a - pd.Timedelta(1, unit="D")) & (w["date"] <= b + pd.Timedelta(1, unit="D"))]
        floods.append({"event": e["id"], "valley": e.get("kathmandu_valley"), "dates": [str(a.date()), str(b.date())],
                       "max_mm": round(float(s["rain_mm"].max()), 1), "big_rain_day": bool((s["rain_mm"] >= big).any())})
    out["floods"] = {"hit": sum(f["big_rain_day"] for f in floods), "of": len(floods), "events": floods}
    # winter droughts: each block of the event (Nov-Apr) with a longest dry run above the block's median
    dry_mm = float(r["trends"]["dry_day_mm"])
    spans = {"drought_2005_06_and_monsoon_2006": ("2005-12-01", "2006-02-28"), "winter_drought_2008_09": ("2008-11-01", "2009-02-28"),
             "winter_drought_2015_16": ("2015-11-01", "2016-04-30"), "winter_drought_2020_21": ("2020-10-01", "2021-02-28"),
             "winter_drought_2022_23": ("2022-10-01", "2023-02-28"), "winter_drought_2023_24": ("2023-12-01", "2024-02-29"),
             "winter_drought_2024_25": ("2024-12-01", "2025-02-28")}
    droughts = []
    for e in ev:
        if e["id"] not in spans:
            continue
        a, b = (pd.Timestamp(x) for x in spans[e["id"]])
        tested = []
        for blk in blocks:
            m = wa.KEYS.index(blk["key"]) + 1
            if m not in (11, 12, 1, 2, 3, 4):
                continue
            for y in (a.year, b.year):
                start = pd.Timestamp(y, m, sd)
                end = pd.Timestamp(y + (m == 12), m % 12 + 1, sd - 1)
                if start < a or end > b or not (blk["years"][0] <= y <= blk["years"][1]):
                    continue
                run = wa.longest_run(w["rain_mm"].to_numpy(float)[(bm == m) & (by == y)] < dry_mm)
                med = float(np.median(list(_runs(w, m, sd, blk["years"], dry_mm).values())))
                tested.append({"block": blk["key"], "year": y, "dry_run": run, "block_median": med, "drier": run > med})
        droughts.append({"event": e["id"], "valley": e.get("kathmandu_valley"), "blocks": tested,
                         "drier": sum(t["drier"] for t in tested), "of": len(tested)})
    out["droughts"] = {"drier": sum(d["drier"] for d in droughts), "of": sum(d["of"] for d in droughts), "events": droughts}
    return out


def _runs(w, m, sd, span, dry_mm):
    bm, by = wa.block_of(w["date"], sd)
    return {y: wa.longest_run(w["rain_mm"].to_numpy(float)[(bm == m) & (by == y)] < dry_mm) for y in range(span[0], span[1] + 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    field = load_field(a.field)
    dest = REPO / "site" / "data" / "fields" / f"{a.field}.json"
    if field.get("country") != "Nepal":
        print(f"NOT FOR THIS FIELD: Weather ahead uses Bikram Sambat months (Nepal); {a.field} is in {field.get('country')}. "
              f"{dest} left unchanged.")
        return 0
    from scripts.common import rain_kw
    r = load_rules()
    doc = json.loads(dest.read_text())
    w = pd.read_parquet(REPO / "data" / "clean" / a.field / "weather.parquet")
    w["date"] = pd.to_datetime(w["date"])
    w = w.sort_values("date").reset_index(drop=True)
    versions = {v: with_rain(w, v, **rain_kw(r, v, a.field))["rain_mm"].to_numpy(float) for v in OTHER_RAIN}
    lib = load_crops(field=field)
    crops = plan_crops(doc)
    blocks, detail = wa.build(w, versions, crops, lib, r)
    block = {
        "basis": "what usually happened on this field in 24 years of its own record; not a forecast",
        "made_by": "scripts/run_weather.py (rules.yaml weather_ahead)",
        "years": 24, "block_starts_on_day": int(r["weather_ahead"]["blocks"]["starts_on_day"]),
        "label": {"sure": "estimate", "scale": "valley"},
        "blocks": blocks,
        "windows": [{"check": c, "crop": cr["crop"], "sow": cr["start"], "window": list(win)}
                    for c, _, cr, win, _, _ in wa._candidates(crops, lib, r)],
        "caveats": {"frost": "cold_nights_both_ways", "rain_trend": "gpm_break", "heat_trend": "power_2001_2003_left_out",
                    "big_rain": "20_mm_not_dhm_heavy"},
        "limits": LIMITS,
        "sources": SOURCES,
    }
    out = dict(doc)
    out.pop("weather", None)
    out["weather"] = block
    errs = validate_field(out)
    if errs:
        print(f"REFUSED: the weather block would break the contract: {errs[:5]}. {dest} left unchanged.")
        return 1
    ck = checks(w, blocks, r)
    path = REPO / "data" / "checks" / a.field / "weather.json"
    path.write_text(json.dumps({"export": block, "detail": detail, "checks": ck}, indent=1, ensure_ascii=False) + "\n")
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    for b in blocks:
        top = b["dangers"][0] if b["dangers"] else None
        print(f"{b['key']}: {b['usual']['rain']}, {b['usual']['temp']}, frost {b['usual']['frost']}; dry run typical "
              f"{b['dry_run']['typical']} d; top: " + (f"{top['check']} {top['crop']} {top['years']}/24 {top['change']}" if top else "none"))
    print(f"checks: rain words blocks {ck['rain_words']['blocks']['agree']}/12, calendar {ck['rain_words']['calendar_months']['agree']}/12; "
          f"floods {ck['floods']['hit']}/{ck['floods']['of']}; drought blocks drier {ck['droughts']['drier']}/{ck['droughts']['of']}; "
          f"frost {[(f['event'], f['typical_band'], f['event_year_band']) for f in ck['frost']]}")
    print(f"wrote {path.relative_to(REPO)} and the weather block of {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
