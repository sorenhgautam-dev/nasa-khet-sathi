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


def frost_words(field, o, months_rules):
    """verification.outputs.frost_month_words: the frost words in the order of DHM's normal night temperatures."""
    normals = _normals(o["station"], o["variable"])
    passes = v.frost_order_passes([m["frost"] for m in field["diary"]["months"]], normals,
                                  months_rules["frost_c"], months_rules["frost_risk_c"])
    return passes, {"normals_c": dict(zip(MONTHS, normals)), "months_out_of_order": [MONTHS[i] for i, p in enumerate(passes) if not p]}


def soil_words(fid, field, o):
    """verification.outputs.soil_month_words: the soil words against each model's monthly terciles (models, not soil)."""
    ours, passes, extra = [m["soil"] for m in field["diary"]["months"]], [], {}
    for name, m in o["models"].items():
        x = pd.read_parquet(ROOT / "data/clean" / fid / m["file"])
        means = x[m["column"]].groupby(pd.to_datetime(x[m["date"]]).dt.month).mean().reindex(range(1, 13))
        ref = tercile_words(means.to_numpy(), ("dry", "medium", "wet"))
        p = [a == b for a, b in zip(ours, ref)]
        passes += p
        extra[name] = {"k": sum(p), "n": len(p), "words": dict(zip(MONTHS, ref))}
    return passes, extra


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
           "pdf_onsets": {str(y): pdf[y][0] for y in sorted(pdf)},
           "onset_compared_2001_2024": len(span), "onset_equal_2001_2024": sum(pdf.get(y, ("",))[0] == ours[y][0] for y in span)}
    (ROOT / "data/checks" / fid / "onset_dhm_second_read.json").write_text(json.dumps(rec, indent=1) + "\n")


def onset_copy(fid):
    r = _json(ROOT / "data/checks" / fid / "onset_dhm_second_read.json")
    if not r:
        return [], {}
    k, n = r["onset_equal_2001_2024"], r["onset_compared_2001_2024"]
    return [True] * k + [False] * (n - k), {"years": "2001-2024", "all_57_years_equal": r["all_equal"]}


def shift_check(fid, field, o, alpha):
    """verification.outputs.monsoon_shift: the sentence shown, recomputed from the second reading by a second
    implementation; each year passes when its date is copied right and the sentence is the same."""
    from datetime import date
    r = _json(ROOT / "data/checks" / fid / "onset_dhm_second_read.json")
    if not r or "pdf_onsets" not in r:
        return [], {}
    a, b = o["years"]
    ours = {int(x["year"]): x["onset"] for x in csv.DictReader(open(ROOT / "config/dhm_onset_dates.csv"))}
    pdf = {int(k): d for k, d in r["pdf_onsets"].items()}
    yrs = [y for y in range(a, b + 1) if y in pdf]
    day = lambda s: date(2001, int(s[5:7]), int(s[8:10])).timetuple().tm_yday  # noqa: E731  (calendar day, non-leap)
    kind = v.shift_kind(yrs, [day(pdf[y]) for y in yrs], alpha)
    shown = field["diary"]["shift_note"]["en"][0]
    said = ("no clear change" if shown.startswith("No clear change") else
            "earlier" if "earlier" in shown else "later" if "later" in shown else None)
    same = kind == said
    return ([pdf.get(y) == ours.get(y) and same for y in range(a, b + 1)],
            {"recomputed": kind, "sentence_shown": shown, "sentence_matches": same, "years": f"{a}-{b}"})


def district_years(fid, field, o):
    """verification.outputs.harvest_years.district: good and bad years against Bhaktapur's district yields."""
    from datetime import date
    d = o["district"]
    path = ROOT / d["file"]
    if fid not in d.get("fields", [d["file"].split("/")[2]]) or not path.exists():   # Bhaktapur district's fields
        return [], {}
    rows = list(csv.DictReader(open(path)))
    rep = _json(ROOT / "data/checks" / fid / "replay.json")
    from pipeline.plans.simulate import export_case
    case = export_case(field["field"]["water_source"])

    def ours(c, crop):
        out = {}
        for s in rep[c]["seasons"]:
            if s["crop"] == crop and s.get("harvest_pct") is not None:
                y = int(v.fiscal_year(date.fromisoformat(s["end"]), d["fiscal_year_starts"])[:4])
                if y in out:
                    raise SystemExit(f"two {crop} seasons in fiscal year {y}: the district check cannot match them")
                out[y] = s["harvest_pct"]
        return out
    passes, per = [], {}
    for dcrop, crop in d["crops"].items():
        ref = {int(r["fiscal_year_ad"][:4]): float(r["yield_kg_ha"]) for r in rows if r["crop"] == dcrop and r["yield_kg_ha"]}
        mine, wet = ours(case, crop), ours("irrigated", crop)
        p = v.residual_sign_matches({y: mine[y] for y in ref if y in mine}, ref)
        pw = v.residual_sign_matches({y: wet[y] for y in ref if y in wet}, ref)
        dr = v.same_direction({y: mine[y] for y in ref if y in mine}, ref)
        passes += p
        per[dcrop] = {"our_crop": crop, "fiscal_years": [f"{y}/{(y + 1) % 100:02d}" for y in sorted(ref)], "k": sum(p), "n": len(p),
                      "watered_case": {"k": sum(pw), "n": len(pw)}, "year_to_year_direction": {"k": sum(dr), "n": len(dr)}}
    return passes, {"water_case": case, "crops": per, "not_scored": d["not_scored"]}


def consistency(fid, field, outs):
    """Job D (owner, 2026-11-15): the consistency checks of rotation_guess, cover_months, season_dates (the drone photo of
    5 May 2026 on its own field; the field's FAO crop calendar; Bhaktapur's district crop statistics on Bhaktapur's
    fields), probe_water (the spoon cups), groundwater (published valley studies) and outlook_2040 (MoFE 2019).
    -> {output: (passes, rows)}."""
    from pipeline.export.build_simple import calendars_of
    guess, cal, out = field["diary"]["guess"], calendars_of(fid), {}
    rg = outs["rotation_guess"]
    drone = rg["drone"] if rg["drone"]["field"] == fid else None
    areas = None
    if fid in outs["harvest_years"]["district"].get("fields", []):
        rows = list(csv.DictReader(open(ROOT / rg["district"]["file"])))
        dmap = rg["district"]["crops"]
        areas = {c: [float(r["area_ha"]) for r in rows if r["crop"] == dmap[c] and r["area_ha"]] for c in guess if c in dmap}
    out["rotation_guess"] = v.guess_consistency(guess, cal, areas, drone and drone["seen"], rg["cereals"])
    cover = {m["m"]: m["cover"] for m in field["diary"]["months"]}
    out["cover_months"] = v.cover_consistency(cover, guess, cal, MONTHS[int(drone["date"][5:7]) - 1] if drone else None)
    ds = _json(ROOT / "data/checks" / fid / "diary_seasons.json")
    seasons = [s for y, ss in ds["chosen"]["seasons_by_year"].items() if 2014 <= int(y) <= 2025
               for s in ss if s.get("source") != "modis"]
    out["season_dates"] = v.season_consistency(seasons, guess, cal, drone and drone["date"][5:],
                                                outs["season_dates"]["tolerance_days"])
    bench = ROOT / "data/checks/probe/bench.json"
    b = _json(bench) if bench.exists() else None
    if b and not b.get("made_up") and b.get("cups"):
        gone = {x if isinstance(x, str) else x.get("cup_id") for x in b.get("excluded") or []}
        out["probe_water"] = v.spoon_cases([c for c in b["cups"] if c["cup_id"] not in gone], outs["probe_water"]["tolerance_m3m3"])
    gw = (field["diary"].get("groundwater") or {}).get("direction")
    if gw:
        out["groundwater"] = v.direction_cases(gw, outs["groundwater"]["studies"])
    fut = ROOT / "data/checks" / fid / "future.json"
    if fut.exists() and _json(fut).get("plausibility"):
        out["outlook_2040"] = v.sign_cases(_json(fut)["plausibility"], outs["outlook_2040"]["mofe_2019"])
    return out


FARMER = ROOT / "data/field_visit"           # the farmer's locked answers (notes/FARMER_SCORING.md)


def _locked_csv(fid, name, columns):
    """The farmer's file as rows, or None while it does not exist. Its SHA-256 must be in config/locked_test.yaml first
    (verification.locked_test.farmer): a file that is not locked, or changed since, stops the scoring."""
    import hashlib
    path = FARMER / fid / name
    if not path.exists():
        return None
    lock = ROOT / "config/locked_test.yaml"
    want = ((yaml.safe_load(lock.read_text()) or {}) if lock.exists() else {}).get(f"data/field_visit/{fid}/{name}")
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if want != got:
        raise SystemExit(f"{path} is not locked: write 'data/field_visit/{fid}/{name}: {got}' into config/locked_test.yaml "
                         "before any score uses it (rules.yaml verification.locked_test.farmer)" if want is None
                         else f"{path} changed after it was locked (config/locked_test.yaml): locked test data never change")
    rows = list(csv.DictReader(open(path)))
    if rows and (missing := [c for c in columns if c not in rows[0]]):
        raise SystemExit(f"{path}: missing columns {missing} (notes/FARMER_SCORING.md)")
    return rows


def pulse_dates(fid, rows, tol):
    """rules.yaml pulse.farmer_scoring: the Pulse's season dates against the farmer's (season_dates row)."""
    from datetime import date
    from pipeline.fetch.cropslib import load_crops
    lib, pulse = load_crops(), _json(ROOT / "site/data/pulse" / f"{fid}.json")
    farmer = []
    for r in rows:
        planted, harvested = date.fromisoformat(r["planted"]), date.fromisoformat(r["harvested"])
        if int(r["year"]) != harvested.year:
            raise SystemExit(f"farmer_dates.csv: year {r['year']} must be the year the {r['crop']} was harvested ({harvested})")
        farmer.append((r["crop"], int(r["year"]), planted, harvested))
    passes = v.season_date_passes(farmer, pulse["seasons"], {c: lib[c]["stages_days"]["ini"] for c, *_ in farmer}, tol)
    return passes, {"rows": len(farmer), "dates": len(passes), "from": "site/data/pulse seasons, HLS years"}


def farmer_year_lists(rows):
    worst = [int(r["year"]) for r in rows if r["kind"] == "worst"]
    return worst, [int(r["year"]) for r in rows if r["kind"] == "best"]


def harvest_years(field, rows):
    """verification.outputs.harvest_years: the farmer's worst and best years against the replay's thirds (field's water case)."""
    worst, best = farmer_year_lists(rows)
    harvest = {r["year"]: r["harvest"] for r in field["replay"]["current"]}
    return v.year_matches(harvest, worst, best), {"worst": worst, "best": best}


def replay_window(fid, rows, common):
    """rules.yaml window_replay.farmer_scoring: the 25-Year Replay's current plan, m6 window, default start, against the
    farmer's rows whose crop grows in that window."""
    rp = _json(ROOT / "site/data/replay" / f"{fid}.json")
    cur = next(p for p in rp["plans"] if p["id"] == "current")
    crops = {c["crop"] for c in cur["crops_in_window"]["m6"]}
    worst, best = farmer_year_lists([r for r in rows if r["crop"] in crops])
    res = cur["results"]["m6"][rp["start_default"]]
    passes = v.year_matches({r["year"]: r["score"] for r in res if r["score"] is not None}, worst, best)
    return {**v.score(passes, True, common), "window": "m6", "start": rp["start_default"], "crops": sorted(crops)}


def score_all(fid):
    rules = load_rules()["verification"]
    common, outs = rules["common"], rules["outputs"]
    field = _json(ROOT / "site/data/fields" / f"{fid}.json")
    card = {}

    def put(key, passes, extra=None):
        o = outs[key]
        card[key] = {"shown": o["shown"], "measure": o["measure"], "reference": o["reference"],
                     "independent": o["independent"], "needs": o["needs"], "verify_by": o["verify_by"],
                     **v.score(passes, o["independent"], common), **(extra or {})}

    put("rain_months", *rain_months(fid, outs["rain_months"]))
    put("rain_month_words", *month_words(field, "rain", "Bhaktapur", "precip_mm", ("low", "medium", "high")))
    put("heat_month_words", *month_words(field, "heat", "Bhaktapur", "tmax_c", ("none", "some", "high")))
    put("frost_month_words", *frost_words(field, outs["frost_month_words"], load_rules()["months"]))
    put("soil_month_words", *soil_words(fid, field, outs["soil_month_words"]))
    put("flood_years", *events(field, "flood"))
    put("drought_years", *events(field, "drought"))
    if ONSET_PDF.exists():
        second_read_onset(fid)
    put("monsoon_start", *onset_copy(fid))
    put("monsoon_shift", *shift_check(fid, field, outs["monsoon_shift"], load_rules()["trends"]["alpha"]))
    for p in ("cover_gap", "safest"):
        put(f"plan_{p}_beats_current", *plans_robust(fid, p, outs[f"plan_{p}_beats_current"]["rain_versions"]))
    dates = _locked_csv(fid, "farmer_dates.csv", ["crop", "year", "planted", "harvested"])
    if dates is not None:                  # the farmer's dates: the Field Pulse's seasons (rules.yaml pulse.farmer_scoring)
        put("season_dates", *pulse_dates(fid, dates, outs["season_dates"]["tolerance_days"]))
    years = _locked_csv(fid, "farmer_years.csv", ["kind", "year", "crop"])
    dist, dist_x = district_years(fid, field, outs["harvest_years"])   # Bhaktapur's district yields (owner, 2026-11-15)
    if years is not None or dist:          # the farmer's worst and best years: the replay and the 25-Year Replay
        fp, fx = harvest_years(field, years) if years is not None else ([], {})
        put("harvest_years", fp + dist, {**fx, "district": dist_x})
        if years is not None:
            card["harvest_years"]["replay_window"] = replay_window(fid, years, common)
    for key, (passes, rows) in consistency(fid, field, outs).items():   # job D: consistency, where no farmer test ran
        if key not in card:
            put(key, passes, {"cases": rows})
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
        by = "-" if c["status"] == "VERIFIED" else c["verify_by"]   # owner, 2026-11-15 (item 6): one plain line
        lines.append(f"| {c['shown']} | {c['measure']} | {c['n']} | {share} | **{c['status']}** | {c['reference']} "
                     f"({ind}) | {by} |")
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
