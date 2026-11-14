"""Feature 4, Data Check-up (rules.yaml checkup): how this field's rain record was checked, worded as a check ->
site/data/checkup/<field>.json. Every number is read from the field's own run (break_test.json, rain_check_b.json,
gauge_evidence.parquet, the weather card and table); only yearly sums and means are taken here.

    .venv/bin/python -m pipeline.export.build_checkup --field demo
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline.export.build_labels import label_for, load_scorecard
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules
from pipeline.twin.inputs import with_rain

REPO = Path(__file__).resolve().parents[2]
VERSIONS = (("tuned", "corrected"), ("untuned", "untuned"), ("dhm", "dhm"), ("uncorrected", "uncorrected"))


def _json(p):
    return json.loads(p.read_text()) if p.exists() else None


def complete_year_totals(dates, rain):
    """{year: total} over the years with every day present."""
    s = pd.Series(pd.to_numeric(pd.Series(rain), errors="coerce").to_numpy(float), index=pd.DatetimeIndex(dates)).dropna()
    g = s.groupby(s.index.year)
    return {int(y): float(v.sum()) for y, v in g if len(v) == (366 if pd.Timestamp(f"{y}-12-31").dayofyear == 366 else 365)}


def evidence(bt, rcb, gauge):
    """The evidence items this field's own run holds (rules.yaml checkup.contents)."""
    out, y0 = [], bt.get("year") or (bt.get("gauge_loss") or {}).get("year")
    gl = bt.get("gauge_loss") or {}
    if gl.get("yearly_mean_pct") and y0:
        yearly = {int(k): round(v, 1) for k, v in gl["yearly_mean_pct"].items()}
        item = {"id": "gauge_weight", "break_year": y0, "after_yearly_pct": [round(min(v for k, v in yearly.items() if k >= y0)),
                                                                          round(max(v for k, v in yearly.items() if k >= y0))],
                "yearly_pct": yearly, "source": "GPM_3IMERGM V07 gaugeRelativeWeighting, the field's 0.1 deg cell"}
        if gauge is not None:
            before = gauge[pd.to_datetime(gauge["month"]).dt.year < y0]["imerg_gauge_weight_pct"].dropna()
            item["before_pct"] = [round(float(before.min())), round(float(before.max()))]
        out.append(item)
    st = (bt.get("reported_not_required") or {}).get("gpcc_stations_yearly_mean")
    if st and y0:
        st = {int(k): v for k, v in st.items()}
        b, a = [v for k, v in st.items() if k < y0], [v for k, v in st.items() if k >= y0]
        if b and a:
            out.append({"id": "gpcc_stations", "before": round(sum(b) / len(b)), "after": round(sum(a) / len(a)),
                        "yearly": st, "source": "GPCC Full Data Monthly V2022, stations in the field's 1-degree box"})
    ch = (rcb or {}).get("chirps") or {}
    if bt.get("chirps_pettitt"):
        out.append({"id": "chirps_steady", "pettitt_p": round(bt["chirps_pettitt"]["p"], 4),
                    "change_after": bt["chirps_pettitt"]["change_after"], "step": ch.get("step_chirps"),
                    "source": "CHIRPS v3.0 rnl, the field's cells (an independent rain product)"})
    if bt.get("gpm_over_chirps_pettitt"):
        out.append({"id": "gpm_vs_chirps", "pettitt_p": round(bt["gpm_over_chirps_pettitt"]["p"], 4),
                    "change_after": bt["gpm_over_chirps_pettitt"]["change_after"],
                    "step": round(bt["step_gpm_over_chirps"], 2) if bt.get("step_gpm_over_chirps") else ch.get("step_gpm"),
                    "source": "GPM IMERG / CHIRPS, yearly, Pettitt 1979"})
    lc = (rcb or {}).get("late_check")
    if lc:
        out.append({"id": "imerg_late", "step_late": lc["step_late"], "step_final": lc["step_final"],
                    "years": [min(lc["years"]), max(lc["years"])],
                    "source": "IMERG Late (climatological gauge calibration) against IMERG Final"})
    if bt.get("gpm_pettitt"):
        out.append({"id": "pettitt_gpm", "p": round(bt["gpm_pettitt"]["p"], 4), "change_after": bt["gpm_pettitt"]["change_after"],
                    "source": "GPM IMERG yearly totals, Pettitt 1979"})
    return out


def build(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules = load_field(fid), load_rules()
    checks, clean = data / "checks" / fid, data / "clean" / fid
    bt = _json(checks / "break_test.json")
    if bt is None:
        raise SystemExit(f"{checks / 'break_test.json'} is missing: run scripts/run_rain_check.py --field {fid} first")
    rcb = _json(checks / "rain_check_b.json")
    gauge = pd.read_parquet(clean / "gauge_evidence.parquet") if (clean / "gauge_evidence.parquet").exists() else None
    ev = evidence(bt, rcb, gauge)
    w = pd.read_parquet(clean / "weather.parquet")
    from scripts.common import rain_kw          # the rain versions' arguments, as every runner builds them
    totals = {name: complete_year_totals(w["date"], with_rain(w, v, **rain_kw(rules, v, fid))["rain_mm"]) for name, v in VERSIONS}
    years = sorted(totals["tuned"])
    normals = (rcb or {}).get("normals_mm", {}).get("Bhaktapur")
    if normals and rcb.get("sources"):
        s = rcb["sources"]
        ev.append({"id": "dhm_normals", "station": "Bhaktapur", "normal_mm": normals["annual"],
                   "gpm_2001_2016_ratio": s["gpm_2001_2016"]["annual_ratio_to_bhaktapur"],
                   "gpm_2017_2025_ratio": s["gpm_2017_2025"]["annual_ratio_to_bhaktapur"],
                   "twin_ratio": round(sum(totals["tuned"].values()) / len(years) / normals["annual"], 2),
                   "source": "DHM 1991-2020 normal, Bhaktapur (config/dhm_normals_1991_2020.csv)"})
    level = "full" if {"gauge_weight", "imerg_late", "dhm_normals"} <= {e["id"] for e in ev} and gauge is not None else "own_break_test"
    wc = (_json(data / "cards" / fid / "weather.json") or {}).get("corrections", {}).get("rain_break") or {}
    gc = wc.get("gauge_calibration") or {}
    chirps = ((rcb or {}).get("chirps") or {}).get("chirps_mm") or {}
    card = load_scorecard(fid, field, data)
    outs = rules["labels"]["outputs"]
    return {
        "field": fid, "placeholder": bool(field.get("placeholder")),
        "made_by": "pipeline/export/build_checkup.py (rules.yaml checkup)",
        "evidence_level": level,
        "break_test": {"found": bool(bt["found"]), "year": bt.get("year"), "checks": bt.get("checks", {}),
                       "rule": "rules.yaml gpm_series.break_test", "own_run": f"data/checks/{fid}/break_test.json"},
        "evidence": ev,
        "correction": {"break": ({"from": wc["from"], "reference_years": wc["reference_years"],
                                  "factors_by_month": wc["factors_by_month"]} if wc.get("applied") else None),
                       "gauge_factors": ({**gc["factors"], "applied": True} if gc.get("applied") else None),
                       "rule": "rules.yaml gpm_series.correction and gpm_series.gauge_calibration"},
        "versions": [{"id": name, "central": name == "tuned", "mean_mm_per_year": round(sum(t.values()) / len(t), 1)}
                     for name, t in totals.items()],
        "yearly": {"years": years,
                   "gpm": [round(totals["uncorrected"][y], 1) for y in years],
                   "twin": [round(totals["tuned"][y], 1) for y in years],
                   "chirps": [chirps.get(str(y), chirps.get(y)) for y in years]},
        "depends_on_corrected_rain": [k for k, o in outs.items() if o["rain_corrected"]],
        "label": label_for("checkup_rain", field, rules, card),
        "sources": [
            {"name": "GPM IMERG", "product": "V07 Final daily (Late for Oct-Dec 2025) as published, and its monthly gauge weight "
             "(GPM_3IMERGM)", "resolution": "0.1 deg (about 10 km)", "years": f"{years[0]}-{years[-1]}", "type": "satellite"},
            {"name": "CHIRPS", "product": "v3.0 rnl daily rain (satellite and gauges), a check only",
             "resolution": "0.05 deg (about 5 km)", "years": "2001-2025", "type": "satellite"},
            {"name": "GPCC", "product": "Full Data Monthly V2022: rain gauges counted in the field's 1-degree box",
             "resolution": "1 deg", "years": "2001-2020", "type": "station"},
            {"name": "DHM (Department of Hydrology and Meteorology, Government of Nepal)",
             "product": "1991-2020 monthly normals, Bhaktapur", "resolution": "one gauge, 2.3 km away", "years": "1991-2020",
             "type": "station"}],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    doc = build(a.field)
    out = REPO / "site" / "data" / "checkup" / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out}: break found {doc['break_test']['found']} ({doc['break_test']['year']}), evidence {doc['evidence_level']} "
          f"({[e['id'] for e in doc['evidence']]}); versions {[(v['id'], v['mean_mm_per_year']) for v in doc['versions']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
