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
            if r["station"] == station and r["variable"] == variable and r["month"].isdigit()]
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
                  "false_alarms": sum(alarms), "flagged_seasons": len(alarms)}


def plans_robust(fid, plan, versions):
    fut = _json(ROOT / "data/checks" / fid / "future.json")
    key = fut["keys"]
    out = []
    for ver in versions:
        runs = {k: {r["run"]: r["harvest"] for r in fut["plans"][key[k]][ver]["runs"]} | {"today": fut["plans"][key[k]][ver]["baseline"]["harvest"]}
                for k in ("current", plan)}
        out += v.beats(runs[plan], runs["current"])
    return out, {"runs": len(out), "rain_versions": versions}


ONSET_PDF = ROOT / "data/raw/dhm_onset/monsoon_onset_and_withdrawal_dates_english3.pdf"


def second_read_onset(fid):
    """Read DHM's onset table (Table 1, p. 3; config/dhm_onset_dates.NOTICE.md) a second way, with pdftotext and a
    regular expression, and compare every date with config/dhm_onset_dates.csv."""
    import re
    import subprocess
    txt = subprocess.run(["pdftotext", "-f", "3", "-l", "3", "-layout", str(ONSET_PDF), "-"], capture_output=True,
                         text=True, check=True).stdout
    mon = {m: i for i, m in enumerate(["May", "June", "July", "August", "September", "October"], 5)}
    pdf = {int(y): (f"{y}-{mon[m]:02d}-{int(d):02d}", f"{y}-{mon[wm]:02d}-{int(wd):02d}" if wd else "")
           for y, d, m, wd, wm in re.findall(r"\b((?:19|20)\d\d)\s+(\d{1,2})-(May|June|July)\s+(?:(\d{1,2})-(September|October)|--)", txt)}
    ours = {int(r["year"]): (r["onset"], r["withdrawal"]) for r in csv.DictReader(open(ROOT / "config/dhm_onset_dates.csv"))}
    mism = [[y, list(ours[y]), list(pdf.get(y, ()))] for y in sorted(ours) if pdf.get(y) != ours[y]]
    span = [y for y in ours if 2001 <= y <= 2024]
    rec = {"what": "second reading of DHM's onset table by pdftotext and a regular expression, against config/dhm_onset_dates.csv",
           "document": ONSET_PDF.name, "years_compared": len(ours), "all_equal": not mism, "mismatches": mism,
           "onset_compared_2001_2024": len(span), "onset_equal_2001_2024": sum(pdf.get(y, ("",))[0] == ours[y][0] for y in span)}
    (ROOT / "data/checks" / fid / "onset_dhm_second_read.json").write_text(json.dumps(rec, indent=1) + "\n")


def onset_copy(fid):
    r = _json(ROOT / "data/checks" / fid / "onset_dhm_second_read.json")
    if not r:
        return [], {}
    k, n = r["onset_equal_2001_2024"], r["onset_compared_2001_2024"]
    return [True] * k + [False] * (n - k), {"years": "2001-2024", "all_57_years_equal": r["all_equal"]}


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
    if ONSET_PDF.exists():
        second_read_onset(fid)
    put("monsoon_start", *onset_copy(fid))
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
