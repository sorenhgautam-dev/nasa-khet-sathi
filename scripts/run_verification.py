"""Score every output the site shows against its yardstick (rules.yaml verification), on the locked test data only.

Writes data/checks/<field>/scorecard.json; --markdown prints the compliance table for VALIDATION.md. Run it only after
the yardsticks are committed (owner, 2026-11-14: yardsticks first, before any scoring)."""
import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import verify as v  # noqa: E402
from pipeline.diary.months import tercile_words  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _json(p):
    return json.loads(Path(p).read_text()) if Path(p).exists() else None


def _normals(station, variable):
    rows = [r for r in csv.DictReader(open(ROOT / "config/dhm_normals_1991_2020.csv"))
            if r["station"] == station and r["variable"] == variable]
    return [float(r["value"]) for r in sorted(rows, key=lambda r: int(r["month"]))]


def month_words(field, word, station, variable, words):
    ref = tercile_words(_normals(station, variable), words)
    return [m[word] == r for m, r in zip(field["diary"]["months"], ref)], dict(zip(MONTHS, ref))


def rain_months(fid, y):
    path = ROOT / "data/clean" / fid / "dhm_bulletin_months.csv"
    if not path.exists():
        return [], {}
    g = pd.read_csv(path)
    g = g[g["station"].isin(y["gauges"]) & g["rain_mm"].notna()]
    ref = g.groupby(["year", "month"])["rain_mm"].agg(["mean", "count"])
    ref = ref[(ref["count"] >= y["min_gauges"]) & (ref["mean"] >= y["min_gauge_mm"])]
    w = pd.read_parquet(ROOT / "data/clean" / fid / "weather.parquet")
    w = w.set_index(pd.to_datetime(w["date"]) if "date" in w else w.index)
    ours = w[y["rain_column"]].groupby([w.index.year, w.index.month]).sum()
    ref = ref[[i in ours.index for i in ref.index]]
    rows = {f"{a}-{b:02d}": [round(float(ours[(a, b)]), 1), round(float(m), 1)] for (a, b), m in ref["mean"].items()}
    return v.within([o for o, _ in rows.values()], [r for _, r in rows.values()], rel=y["tolerance_rel"]), rows


def events(field, kind):
    ev = yaml.safe_load(open(ROOT / "config/known_events.yaml"))
    season = lambda i: "winter" if i.startswith("winter") else "monsoon" if i.startswith("monsoon") else None  # noqa: E731
    flags = {r["year"]: (r["event"], r.get("event_season")) for r in field["replay"]["current"] if r["event"] == kind}
    valley = [(y, e["category"], season(e["id"])) for e in ev["events"] if e["category"] == kind
              and e["kathmandu_valley"] == "yes" for y in e["years"]]
    listed = {(y, e["category"]) for e in ev["events"] for y in e["years"]}
    controls = [(y, "drought", season(c["id"])) for c in ev["negative_controls"] for y in c["years"]]
    hits, alarms = v.events_skill(flags, valley, listed, controls)
    return hits, {"valley_events": [list(e) for e in valley], "flagged_years": sorted(flags),
                  "false_alarms": f"{sum(alarms)} of {len(alarms)} flagged seasons"}


def plans_robust(fid, plan, versions):
    fut = _json(ROOT / "data/checks" / fid / "future.json")
    key = fut["keys"]
    out = []
    for ver in versions:
        runs = {k: {r["run"]: r["harvest"] for r in fut["plans"][key[k]][ver]["runs"]} | {"today": fut["plans"][key[k]][ver]["baseline"]["harvest"]}
                for k in ("current", plan)}
        out += v.beats(runs[plan], runs["current"])
    return out, {"runs": len(out), "rain_versions": versions}


def score_all(fid):
    rules = load_rules()["verification"]
    common, outs = rules["common"], rules["outputs"]
    field = _json(ROOT / "site/data/fields" / f"{fid}.json")
    card = {}

    def put(key, passes, extra=None):
        o = outs[key]
        card[key] = {"shown": o["shown"], "measure": o["measure"], "reference": o["reference"],
                     "independent": o["independent"], "needs": o["needs"],
                     **v.score(passes, o["independent"], common), **(extra or {})}

    put("rain_months", *rain_months(fid, outs["rain_months"]))
    put("rain_month_words", *month_words(field, "rain", "Bhaktapur", "precip_mm", ("low", "medium", "high")))
    put("heat_month_words", *month_words(field, "heat", "Bhaktapur", "tmax_c", ("none", "some", "high")))
    put("flood_years", *events(field, "flood"))
    put("drought_years", *events(field, "drought"))
    for p in ("cover_gap", "safest"):
        put(f"plan_{p}_beats_current", *plans_robust(fid, p, outs[f"plan_{p}_beats_current"]["rain_versions"]))
    for key in outs:                       # outputs whose test data have not arrived score as no cases yet
        if key not in card:
            put(key, [])
    return card


def markdown(card):
    lines = ["| Output | What we measured | n | Share [95% CI] | Status | Reference (independent?) | What would verify it |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for k, c in card.items():
        share = "-" if c["share"] is None else f"{c['share']:.0%} [{c['ci95'][0]:.0%}, {c['ci95'][1]:.0%}]"
        ind = "yes" if c["independent"] else "no"
        lines.append(f"| {c['shown']} | {c['measure']} | {c['n']} | {share} | **{c['status']}** | {c['reference']} "
                     f"({ind}) | {c['needs']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    card = score_all(a.field)
    out = ROOT / "data/checks" / a.field / "scorecard.json"
    out.write_text(json.dumps(card, indent=1, ensure_ascii=False) + "\n")
    print(markdown(card) if a.markdown else f"wrote {out}")
