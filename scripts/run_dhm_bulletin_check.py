"""The twin's 2025 rain against DHM's own monthly gauge totals (VALIDATION 3.9c; REVIEW_2 Phase 3, 2026-11-13).

    .venv/bin/python scripts/run_dhm_bulletin_check.py --field demo

An independent check of the 2017 rain correction: DHM's monthly bulletins print each month's measured total at
Bhaktapur (about 2.3 km from the field), Changu Narayan and Kathmandu Airport. These are DHM's own gauges, not the
synoptic-derived GHCN series the correction was tested on, and none of them reaches IMERG after 2016. The
transcribed table is PRELIMINARY data, (c) DHM, used for validation only and kept under data/ (never in the public
repository): data/raw/dhm_bulletins/<field>/monthly_2025.csv. Without that file this prints NOT YET POSSIBLE.
Writes data/checks/<field>/rain_vs_dhm_2025.json and the data card; changes nothing else.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks.rain_check import ratio_to_gauges  # noqa: E402
from pipeline.fetch import guards as g  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402


def monthly(series_by_date):
    s = series_by_date.dropna()
    return {str(p): float(v) for p, v in s.groupby(s.index.to_period("M")).sum().items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    src = REPO / "data" / "raw" / "dhm_bulletins" / field["id"] / "monthly_2025.csv"
    if not src.exists():
        print(f"NOT YET POSSIBLE: {src.relative_to(REPO)} does not exist (transcribe DHM's monthly bulletins; validation only)")
        return 2
    t = pd.read_csv(src, comment="#")
    g.assert_in_range(t["rain_mm"].to_numpy(float), "rain_mm", "dhm monthly rain_mm", valid_range=(0.0, 3000.0))
    gauges = {m: grp["rain_mm"].tolist() for m, grp in t.groupby("month")}
    nearest = {m: grp.loc[grp["station"] == "Bhaktapur", "rain_mm"].tolist() for m, grp in t.groupby("month")}
    clean = REPO / "data" / "clean" / field["id"]
    w = pd.read_parquet(clean / "weather.parquet").set_index("date")
    w.index = pd.DatetimeIndex(w.index)
    gpm = pd.read_parquet(clean / "gpm.parquet")
    late_start = pd.DatetimeIndex(gpm.loc[gpm["product"].astype(str) == "late", "date"]).min()   # IMERG Late days (D1)
    series = {"gpm_as_published": w["rain_uncorrected_mm"], "twin_rain": w["rain_mm"]}
    for name, file, col in (("chirps", "chirps.parquet", "rain_mm"), ("power", "power.parquet", "rain_mm")):
        if (clean / file).exists():
            d = pd.read_parquet(clean / file)
            d = d.set_index("date") if "date" in d.columns else d
            d.index = pd.DatetimeIndex(d.index)
            series[name] = d[col]
    final_months = [m for m in gauges if pd.Period(m).end_time < late_start]
    late_months = [m for m in gauges if pd.Period(m).start_time >= late_start]
    out = {"labels": {"field": field["name"], "gauges": sorted(t["station"].unique()),
                      "source": "DHM Climate Division, monthly 'Preliminary Precipitation and Temperature Summary', Annex 1 (PRELIMINARY; "
                                "(c) DHM; validation only, not redistributed)",
                      "method": "monthly totals; the months are summed before dividing; ratio = series / mean of the three gauges",
                      "caveat": "Six months of one year; gauges are points, a GPM cell is about 10 km; DHM's rain day ends at 08:45 "
                                "local, so single days differ by up to a day.",
                      "imerg_final_months": final_months, "imerg_late_months": late_months}, "against_three_gauges": {},
           "against_bhaktapur_alone": {}}
    for name, s in series.items():
        m = monthly(s)
        for label, months in (("imerg_final_months", final_months), ("imerg_late_months", late_months)):
            out["against_three_gauges"].setdefault(label, {})[name] = ratio_to_gauges(m, {k: gauges[k] for k in months})
            out["against_bhaktapur_alone"].setdefault(label, {})[name] = ratio_to_gauges(m, {k: nearest[k] for k in months})
    day = t.dropna(subset=["max_day_mm"])
    out["wettest_station_day_oct_2025_mm"] = {r.station: r.max_day_mm for r in day[day["month"] == "2025-10"].itertuples()}
    out["wettest_twin_day_oct_2025"] = {"date": str(w.loc["2025-10", "rain_mm"].idxmax().date()), "mm": round(float(w.loc["2025-10", "rain_mm"].max()), 1)}
    path = REPO / "data" / "checks" / field["id"] / "rain_vs_dhm_2025.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    card = g.make_card(
        dataset="dhm_bulletins", product="DHM monthly 'Preliminary Precipitation and Temperature Summary', Annex 1", version="2025 (preliminary)",
        variable="monthly precipitation total; wettest day of the month", units_in="mm", units_out="rain_mm (mm per month)", scale_factor=None,
        fill_values_removed="none (transcribed by hand; an empty cell is a value not read)", quality_flags_used="none (DHM marks the data preliminary)",
        records_dropped=0, date_range=[str(t["month"].min()), str(t["month"].max())],
        time_zone="Nepal time; DHM's rain day ends at 08:45 local (03:00 UTC)", pixel_count=int(t["station"].nunique()),
        source="Department of Hydrology and Meteorology, Nepal (dhm.gov.np), (c) DHM; validation only, kept under data/, never redistributed",
        resolution="three station points: Bhaktapur (about 2.3 km from the field), Changu Narayan, Kathmandu Airport",
        raw_attrs="a hand-transcribed table: no file attributes", range_warnings={"rain_mm": 0},
        notes="Transcribed 2026-11-13 from six bulletins (2025-04, -08, -09, -10, -11, -12) saved beside the table; every value re-read "
              "in the bulletin text by the reviewing session (REVIEW_2). Checks only (VALIDATION 3.9c).")
    g.write_card(card, REPO / "data" / "cards" / field["id"])
    for label in ("imerg_final_months", "imerg_late_months"):
        r3, r1 = out["against_three_gauges"][label], out["against_bhaktapur_alone"][label]
        print(f"{label} {r3['twin_rain']['months']}: " + "; ".join(f"{k} {v['ratio']} (Bhaktapur alone {r1[k]['ratio']})" for k, v in r3.items()))
    print(f"-> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
