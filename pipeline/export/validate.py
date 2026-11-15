"""Validate exports against the output contract.

    python -m pipeline.export.validate                # checks site/data/
    python -m pipeline.export.validate --data-dir DIR
    python -m pipeline.export.validate --final        # the freeze check: also fails while anything is MOCK

Schema checks come from schema.json / index_schema.json. The checks below cover what JSON Schema
cannot say: order, uniqueness, cross-references and matching array lengths.
"""
import argparse
import json
import sys
from pathlib import Path

ALT_RAIN = ("dhm_rain", "untuned_rain")   # the range's other rain versions (owner, 2026-11-14)

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_schema(name):
    return json.loads((HERE / name).read_text())


def _schema_errors(doc, schema_name):
    v = Draft202012Validator(load_schema(schema_name))
    return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in v.iter_errors(doc)]


def _dupes(values):
    seen, dupes = set(), set()
    for v in values:
        (dupes if v in seen else seen).add(v)
    return sorted(dupes)


def _final_errors(doc):
    """What a file ready to freeze must also meet (REVIEW_2 M13; --final). Not part of the everyday check, because
    the mock that the site was built with does not meet it: no made-up (MOCK) numbers left, three different
    rotations, each plan's harvest score the mean of its replay (within 1 point of rounding). Blocks named in `mock`
    are allowed: they hold no numbers and the site says 'not ready yet' (owner's answer 2, 2026-11-13)."""
    errors = []
    if "MOCK" in json.dumps(doc, ensure_ascii=False):
        errors.append("final: the file still contains MOCK data")
    crops = {p["id"]: tuple(c["crop"] for c in p["crops"]) for p in doc["plans"]}
    ids = list(crops)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if crops[a] == crops[b]:
                errors.append(f"final: plans {a} and {b} grow the same crops (at least three rotations are asked for)")
    for p in doc["plans"]:
        years = doc["replay"].get(p["id"], [])
        if years:
            mean = sum(y["harvest"] for y in years) / len(years)
            if abs(p["score"]["harvest"] - mean) > 1.0:
                errors.append(f"final: plans/{p['id']}: score.harvest {p['score']['harvest']} is not the mean of its "
                              f"replay ({mean:.1f})")
    return errors


def validate_field(doc, final=False):
    """Return a list of problems; empty means the field file meets the contract. final=True adds the freeze checks."""
    errors = _schema_errors(doc, "schema.json")
    if errors:
        return errors
    section_ids = [s["id"] for s in doc["field"]["sections"]]
    if d := _dupes(section_ids):
        errors.append(f"field/sections: duplicate ids {d}")
    if [m["m"] for m in doc["diary"]["months"]] != MONTHS:
        errors.append("diary/months: must run Jan to Dec in order")
    plan_ids = [p["id"] for p in doc["plans"]]
    if d := _dupes(plan_ids):
        errors.append(f"plans: duplicate ids {d}")
    for p in doc["plans"]:
        if len(p["tips_ne"]) != len(p["tips"]):
            errors.append(f"plans/{p['id']}: tips_ne needs one Nepali tip per English tip "
                          f"({len(p['tips_ne'])} vs {len(p['tips'])})")
    for pid in plan_ids:                    # REVIEW_2 M13: a plan card with no years behind it
        if pid not in doc["replay"]:
            errors.append(f"plans/{pid}: no replay for this plan")
    for key, years in doc["replay"].items():
        if key not in plan_ids:
            errors.append(f"replay/{key}: no plan with this id")
        if d := _dupes([y["year"] for y in years]):
            errors.append(f"replay/{key}: duplicate years {d}")
        elif [y["year"] for y in years] != list(range(years[0]["year"], years[0]["year"] + len(years))):
            errors.append(f"replay/{key}: years must run year by year, in order, with no gap")
        for y in years:                     # owner's decisions 1 and 4b: the other rain versions only where they differ
            for alt in ALT_RAIN:
                u = y.get(alt)
                if u and all(u.get(k) == y.get(k) for k in ("harvest", "dry_days", "event", "irrigated")):
                    errors.append(f"replay/{key}/{y['year']}: {alt} is given but changes nothing")
    # owner's answer 9 to REVIEW_2 (2026-11-13): one weather event per year for the field, the same on every plan
    by_year = {}
    for key, years in doc["replay"].items():
        for y in years:
            for tag, row in [("", y)] + [(f" ({alt})", y.get(alt)) for alt in ALT_RAIN]:
                if row and "event_season" in row and row["event"] != "drought":
                    errors.append(f"replay/{key}/{y['year']}{tag}: event_season is only for a drought")
            by_year.setdefault(y["year"], set()).add((y["event"], y.get("event_season")))
    differ = sorted(y for y, v in by_year.items() if len(v) > 1)
    if differ:
        errors.append(f"replay: a year must carry the same event (and season) on every plan; they differ in {differ}")
    for p in doc["plans"]:
        for alt in ALT_RAIN:
            u = p.get(f"score_{alt}")
            if u and u == p["score"]:
                errors.append(f"plans/{p['id']}: score_{alt} is given but changes nothing")
    # owner's answer 2 to REVIEW_2 (2026-11-13): a block that is not computed yet is named in `mock` and holds no numbers
    not_ready = doc.get("mock", [])
    empty_sections = [s["id"] for s in doc["field"]["sections"]
                      if s["wetness"] is None and s["temp"] is None and s["status"] == "grey" and s["sure"] == 0]
    if "field.sections" in not_ready:
        if len(empty_sections) != len(doc["field"]["sections"]):
            errors.append("field.sections is named in `mock`, so every section must be grey with null wetness and temp and sure 0")
    elif any(s["wetness"] is None for s in doc["field"]["sections"]):
        errors.append("field.sections: a section without wetness needs 'field.sections' in `mock`")
    if ("future" in not_ready) != (doc["future"] is None):
        errors.append("future: it is null exactly when 'future' is named in `mock`")
    # build step 9 (2026-11-14): the outlook block, and each plan's and each current option's own series
    series_list = []
    if doc["future"] is not None:
        series_list += [(f"future/{k}", doc["future"][k]) for k in ("nothing_changes", "with_plan")]
    for p in doc["plans"]:
        series_list += [(f"plans/{p['id']}/{k}", p[k]) for k in ["future"] + [f"future_{a}" for a in ALT_RAIN] if k in p]
    for o in (doc.get("current_options") or {}).get("options", []):
        series_list += [(f"current_options/{o['id']}/{k}", o[k]) for k in ["future"] + [f"future_{a}" for a in ALT_RAIN] if k in o]
    for name, s in series_list:
        if doc["future"] is None:
            errors.append(f"{name}: a 2040 outlook needs the future block (future.years)")
            continue
        n = len(doc["future"]["years"])
        for key in ("harvest", "harvest_low", "harvest_high"):
            if len(s[key]) != n:
                errors.append(f"{name}/{key}: needs {n} values, one per year")
        for i, (lo, mid, hi) in enumerate(zip(s["harvest_low"], s["harvest"], s["harvest_high"])):
            if not lo <= mid <= hi:
                errors.append(f"{name}: year {i} needs harvest_low <= harvest <= harvest_high")
    sd = doc["method"]["season_detection"]
    by_id = {m["id"]: m for m in sd["methods"]} if sd else {}
    if sd is None:          # rules.yaml season_detection.no_dense_years: no year had enough clear images to compare
        pass
    elif sorted(by_id) != ["changepoint", "detective", "threshold"]:
        errors.append("method/season_detection/methods: needs threshold, changepoint and detective once each")
    else:
        for m in sd["methods"]:
            if sorted(y["year"] for y in m["by_year"]) != sorted(sd["held_out_years"]):
                errors.append(f"method/season_detection/{m['id']}: by_year must cover exactly the held-out years")
        base, ch = by_id["threshold"]["score"], sd["chosen"]
        best = max(by_id, key=lambda k: by_id[k]["score"])
        want = best if best == "threshold" or by_id[best]["score"] - base >= sd["margin"] - 1e-9 else "threshold"
        if ch != want:
            errors.append(f"method/season_detection/chosen: the rule fixed in advance picks '{want}', not '{ch}'")
        if by_id["detective"]["si"] is not True or by_id["threshold"]["si"] or by_id["changepoint"]["si"]:
            errors.append("method/season_detection: only the detective is the SI method")
    dy = doc["diary"]          # owner, 2026-11-14: the shift sits inside its own range
    if dy.get("shift_days") is not None and dy.get("shift_days_low") is not None and dy.get("shift_days_high") is not None:
        if not dy["shift_days_low"] <= dy["shift_days"] <= dy["shift_days_high"]:
            errors.append("diary/shift_days: needs shift_days_low <= shift_days <= shift_days_high")
    gw = doc["diary"]["groundwater"]
    if gw["direction"] == "falling" and gw["trend_cm_per_year"] >= 0:
        errors.append("diary/groundwater: 'falling' needs a negative trend")
    if gw["direction"] == "rising" and gw["trend_cm_per_year"] <= 0:
        errors.append("diary/groundwater: 'rising' needs a positive trend")
    errors += _current_options_errors(doc)
    if final:
        errors += _final_errors(doc)
    return errors


def _current_options_errors(doc):
    """Owner's answer 6 to REVIEW_2 (2026-11-13): the current plan once for each rotation the farmer may confirm."""
    co = doc.get("current_options")
    if not co:
        return []
    errors = []
    opts = {o["id"]: o for o in co["options"]}
    if len(opts) != len(co["options"]):
        errors.append("current_options: duplicate option ids")
    if co["default"] not in opts:
        return errors + [f"current_options: default '{co['default']}' is not one of the options {sorted(opts)}"]
    cur = next((p for p in doc["plans"] if p["id"] == "current"), None)
    d = opts[co["default"]]
    if cur is None or any(d[k] != cur[k] for k in ("crops", "score", "tabs", "tips", "tabs_ne", "tips_ne")) \
            or any(d.get(f"score_{a}") != cur.get(f"score_{a}") for a in ALT_RAIN) or d["replay"] != doc["replay"].get("current"):
        errors.append("current_options: the default option must be what plans (id current) and replay.current show")
    years = [y["year"] for y in doc["replay"].get("current", [])]
    suggested = sorted(p["id"] for p in doc["plans"] if p["id"] != "current")
    crops_seen = {}
    for o in co["options"]:
        if [y["year"] for y in o["replay"]] != years:
            errors.append(f"current_options/{o['id']}: its replay must cover the same years as replay.current")
        if sorted(o["compared"]) != suggested:
            errors.append(f"current_options/{o['id']}: compared must hold exactly the suggested plans {suggested}")
        if len(o["tips_ne"]) != len(o["tips"]):
            errors.append(f"current_options/{o['id']}: tips_ne needs one Nepali tip per English tip")
        key = tuple(c["crop"] for c in o["crops"])
        if key in crops_seen:
            errors.append(f"current_options: {o['id']} and {crops_seen[key]} grow the same crops")
        crops_seen[key] = o["id"]
        ev = {y["year"]: (y["event"], y.get("event_season")) for y in o["replay"]}
        ref = {y["year"]: (y["event"], y.get("event_season")) for y in doc["replay"].get("current", [])}
        if ev != ref and [y["year"] for y in o["replay"]] == years:
            errors.append(f"current_options/{o['id']}: a year must carry the same event as on every plan")
    return errors


def words_problems(doc):
    """site/data/words.json (owner's answer 16, 2026-11-13): the blocks the site reads must be there and not empty."""
    errors = [f"words: '{k}' is missing or empty" for k in ("screens", "shared", "glossary", "crop_explainers") if not doc.get(k)]
    if not errors and len(doc["screens"]) != 10:
        errors.append(f"words: ten screens are expected, found {len(doc['screens'])}")
    return errors


# The four features of the farmer's question (2026-11-14): site/data/<kind>/<field>.json, each with its own schema.
FEATURES = {"labels": "labels_schema.json", "replay": "replay_schema.json", "pulse": "pulse_schema.json",
            "checkup": "checkup_schema.json", "simple": "simple_schema.json",
            "rainrisk": "rainrisk_schema.json", "fertiliser": "fertiliser_schema.json", "heatclock": "heatclock_schema.json"}
# Made only for a field with a country profile (scripts/make_site.py PROFILE_ONLY's site files; owner's item 3,
# 2026-11-14): a field on the global defaults (index.json profile "default") has none, and the site says "not ready yet".
NOT_ON_DEFAULTS = ("replay", "simple", "rainrisk", "fertiliser", "heatclock")


def missing_feature_files(index, data_dir, kind):
    """--final: each listed field's <kind>/<id>.json, except the profile-only kinds for a field on the global defaults."""
    return [f"{f['id']}: listed in index.json but no {kind}/{f['id']}.json" for f in (index or {}).get("fields", [])
            if not (f.get("profile") == "default" and kind in NOT_ON_DEFAULTS)
            and not (Path(data_dir) / kind / f"{f['id']}.json").exists()]
LABEL_IDS = ("rain_months", "rain_month_words", "heat_month_words", "frost_month_words", "soil_month_words", "cover_months",
             "season_dates", "rotation_guess", "flood_years", "drought_years", "harvest_years", "plan_cover_gap_beats_current",
             "plan_safest_beats_current", "monsoon_start", "groundwater", "part_soil_water", "probe_water", "outlook_2040",
             "plan_scores", "bare_days", "plan_harvest", "plan_water", "plan_cover", "plan_soil_kept", "replay_year",
             "part_wetness", "part_sure", "part_status", "pulse_hls", "pulse_modis", "nearby_fields", "replay_window",
             "checkup_rain",       # the scorecard's 19 rows and the ids the brief asks for at least
             "rainrisk_harvest", "fertiliser_saver", "heatclock_today", "heatclock_2040")   # build_risks.py, 2026-11-14


def _labels_errors(doc, field_doc, labels_doc):
    errors = [f"outputs: {k} is missing" for k in LABEL_IDS if k not in doc["outputs"]]
    for k, o in doc["outputs"].items():
        if (o["sure"] == "verified") != (o["status"] == "VERIFIED"):
            errors.append(f"outputs/{k}: sure is 'verified' exactly when status is VERIFIED")
        if o["k"] > o["n"]:
            errors.append(f"outputs/{k}: k above n")
        if missing := [s for s in o["sources"] if s not in doc["sources"]]:
            errors.append(f"outputs/{k}: sources {missing} are not described in sources")
    return errors


def _replay_errors(doc, field_doc, labels_doc):
    errors, n, th = [], doc["year_count"], doc["thresholds"]
    if len(doc["seasons"]) != n:
        errors.append("seasons: one per past season (year_count)")
    if field_doc is not None:
        want = {p["id"] for p in field_doc["plans"]} | {o["id"] for o in (field_doc.get("current_options") or {}).get("options", [])}
        if {p["id"] for p in doc["plans"]} != want:
            errors.append(f"plans: must be the field file's plans and current options {sorted(want)}")
    wins = [w["id"] for w in doc["windows"]]
    if d := _dupes(wins):
        errors.append(f"windows: duplicate ids {d}")
    for p in doc["plans"]:
        if sorted(p["results"]) != sorted(wins) or sorted(p["summary"]) != sorted(wins):
            errors.append(f"plans/{p['id']}: results and summary need every window {wins}")
            continue
        for k, by_start in p["results"].items():
            for s, rows in by_start.items():
                where = f"plans/{p['id']}/{k}/{s}"
                if [r["season"] for r in rows] != doc["seasons"]:
                    errors.append(f"{where}: one result per past season, in order")
                for r in rows:
                    want = (None if r["score"] is None else "worked" if r["score"] >= th["worked_min"]
                            else "failed" if r["score"] < th["failed_below"] else "struggled")
                    if r["result"] != want:
                        errors.append(f"{where}/{r['season']}: result {r['result']} does not follow its score {r['score']}")
                    if r["sensitive"] != any(o["result"] != r["result"] for o in r["other_versions"].values()):
                        errors.append(f"{where}/{r['season']}: sensitive must say whether another rain version's result differs")
                    if r["enso"] != (doc["enso"]["by_season"].get(r["season"]) or {}).get("state"):
                        errors.append(f"{where}/{r['season']}: enso differs from enso.by_season")
                cnt = p["summary"][k][s]
                if (cnt["worked"], cnt["struggled"], cnt["failed"], cnt["no_crop"], cnt["sensitive"]) != (
                        *(sum(r["result"] == w for r in rows) for w in ("worked", "struggled", "failed")),
                        sum(r["result"] is None for r in rows), sum(r["sensitive"] for r in rows)):
                    errors.append(f"{where}: summary does not count its results")
    same = [k for k, v in doc["enso"]["by_season"].items() if v["state"] == doc["enso"]["now"]["state"]]
    if sorted(same) != sorted(doc["enso"]["same_as_now"]):
        errors.append("enso/same_as_now: must list the past seasons in the same state as now")
    return errors


def _pulse_errors(doc, field_doc, labels_doc):
    errors = []
    for src, pts in doc["points"].items():
        if [p[0] for p in pts] != sorted(p[0] for p in pts):
            errors.append(f"points/{src}: dates must run in order")
    for s in doc["seasons"]:
        if not s["greenup"] <= s["peak"] <= s["end"]:
            errors.append(f"seasons/{s['year']}/{s['slot']}: needs greenup <= peak <= end")
    return errors


def _checkup_errors(doc, field_doc, labels_doc):
    errors, y = [], doc["yearly"]
    if not len(y["years"]) == len(y["gpm"]) == len(y["twin"]) == len(y["chirps"]):
        errors.append("yearly: years, gpm, twin and chirps need one value per year")
    if [v["id"] for v in doc["versions"] if v["central"]] != ["tuned"]:
        errors.append("versions: exactly one central version, 'tuned'")
    if labels_doc is not None and (bad := [k for k in doc["depends_on_corrected_rain"] if k not in labels_doc["outputs"]]):
        errors.append(f"depends_on_corrected_rain: {bad} are not output ids of labels")
    return errors


def _simple_errors(doc, field_doc, labels_doc):
    """The farmer cards: the faces add up to 10 and the counts to the winters, for every answer."""
    errors = []
    for crop, c in doc["replay_card"].items():
        for w, card in c.items():
            if sum(card["per_ten"].values()) != 10:
                errors.append(f"replay_card/{crop}/{w}: per_ten must add up to 10")
            if sum(card["counts"].values()) != doc["winters"]:
                errors.append(f"replay_card/{crop}/{w}: counts must add up to winters")
    if set(doc["trial_card"]) != set(doc["replay_card"]) or doc["answers"]["default_winter"] not in doc["replay_card"]:
        errors.append("answers, replay_card and trial_card must cover the same winter crops")
    return errors


def _risk_common(doc, label_ids):
    """build_risks.py files (2026-11-14): their labels, and a Nepali line for every English Why? line."""
    errors = [f"labels: {k} is missing" for k in label_ids if k not in doc["labels"]]
    if len(doc["why"]["en"]) != len(doc["why"]["ne"]):
        errors.append("why: one Nepali line per English line")
    return errors


def _plan_ids(field_doc):
    return [p["id"] for p in field_doc["plans"]] + [o["id"] for o in (field_doc.get("current_options") or {}).get("options", [])]


def _rainrisk_errors(doc, field_doc, labels_doc):
    from pipeline.plans.risk import typical_worst
    errors = _risk_common(doc, ["rainrisk_harvest"])
    if len(doc["years"]) != doc["year_count"]:
        errors.append("years: year_count of them")
    if field_doc is not None:
        if [p["id"] for p in doc["plans"]] != _plan_ids(field_doc):
            errors.append(f"plans: must be the field file's plans and current options {_plan_ids(field_doc)}")
        if doc["years"] != [y["year"] for y in field_doc["replay"]["current"]]:
            errors.append("years: must be the replay's complete years")
    for p in doc["plans"]:
        for c in p["crops"]:
            where = f"plans/{p['id']}/{c['crop']}"
            if [y["year"] for y in c["years"]] != doc["years"]:
                errors.append(f"{where}: one square per year, in order")
            if c["count"] != sum(y["days"] > 0 for y in c["years"]):
                errors.append(f"{where}: count does not count the years with a heavy-rain day")
            if any(y["days"] and y["max_mm"] < doc["threshold_mm"] for y in c["years"]):
                errors.append(f"{where}: a heavy-rain year's largest day is below the threshold")
            counts = [c["count"]] + [v["count"] for v in c["other_versions"].values()]
            if (c["count_low"], c["count_high"]) != (min(counts), max(counts)):
                errors.append(f"{where}: count_low and count_high must be the lowest and highest count over the rain versions")
            if any(v["count"] != len(v["heavy_years"]) or not set(v["heavy_years"]) <= set(doc["years"])
                   for v in c["other_versions"].values()):
                errors.append(f"{where}: other_versions counts must count their heavy_years")
            if c["good_news"] != (c["count"] == 0):
                errors.append(f"{where}: good_news exactly when count is 0")
            d = c["dry_run"]          # rules.yaml rain_risk.dry_spells
            if [y["year"] for y in d["years"]] != doc["years"] or (d["window"]["from"], d["window"]["to"]) != (c["sow"], c["end"]):
                errors.append(f"{where}: dry_run needs one value per year, from the sowing day to the last day")
            elif {k: d[k] for k in ("typical", "worst")} != typical_worst({y["year"]: y["days"] for y in d["years"]}):
                errors.append(f"{where}: dry_run typical and worst must be the median (half up) and the three longest years")
            typ = [d["typical"]] + [v["typical"] for v in d["other_versions"].values()]
            if (d["typical_low"], d["typical_high"]) != (min(typ), max(typ)):
                errors.append(f"{where}: dry_run typical_low and typical_high must span the four rain versions")
    return errors


def _fertiliser_errors(doc, field_doc, labels_doc):
    errors = _risk_common(doc, ["fertiliser_saver"])
    if field_doc is not None and not any(p["id"] == doc["plan"] for p in field_doc["plans"]):
        errors.append(f"plan: the field file has no plan {doc['plan']}")
    if doc["applies"]:
        share, bag = doc["urea_n_share"], doc["bag_kg"]
        for i in (0, 1):
            u = doc["n_kg_ha"][i] / share
            if (doc["urea_kg_ha"][i], doc["bags_ha"][i], doc["bags_ha_whole"][i]) != (round(u), round(u / bag, 1), round(u / bag)):
                errors.append(f"urea_kg_ha / bags_ha [{i}]: not n_kg_ha / urea_n_share (and / bag_kg)")
        if not doc["n_kg_ha"][0] <= doc["n_kg_ha"][1]:
            errors.append("n_kg_ha: low first")
        if field_doc is not None:
            crops = [c["crop"] for p in field_doc["plans"] if p["id"] == doc["plan"] for c in p["crops"]]
            if doc["legume"] not in crops or doc["next_crop"] not in crops:
                errors.append(f"legume and next_crop must be crops of plan {doc['plan']}: {crops}")
    return errors


def _heatclock_errors(doc, field_doc, labels_doc):
    errors = _risk_common(doc, ["heatclock_today", "heatclock_2040"])
    if len(doc["years"]) != doc["year_count"]:
        errors.append("years: year_count of them")
    if d := _dupes([c["id"] for c in doc["checks"]]):
        errors.append(f"checks: duplicate ids {d}")
    known = set(_plan_ids(field_doc)) if field_doc is not None else None
    for c in doc["checks"]:
        t, where = c["today"], f"checks/{c['id']}"
        if [y["year"] for y in t["years"]] != doc["years"]:
            errors.append(f"{where}: one square per year, in order")
        if t["years_with"] != sum(y["days"] > 0 for y in t["years"]) or t["good_news"] != (t["years_with"] == 0):
            errors.append(f"{where}: years_with and good_news must follow the squares")
        if abs(t["mean_days"] - sum(y["days"] for y in t["years"]) / len(t["years"])) > 0.006:
            errors.append(f"{where}: mean_days is not the mean of the squares")
        if known is not None and not set(c["plans"]) <= known:
            errors.append(f"{where}: plans {sorted(set(c['plans']) - known)} are not in the field file")
        f = c["future"]
        if f is not None:
            for s, v in f["scenarios"].items():
                fut = [m["future"] for m in v["models"]]
                if not (v["low"] == min(fut) <= v["median"] <= max(fut) == v["high"]) or len(fut) != f["models"]:
                    errors.append(f"{where}/{s}: median, low and high must come from the models' own values")
            if f["good_news"] != all(m["future"] < 1 for v in f["scenarios"].values() for m in v["models"]):
                errors.append(f"{where}: future good_news exactly when every model is below 1 day a season")
        if (c["stage"] in ("floret_formation", "flowering")) != all(k in c for k in ("sure", "conditions", "days_after_sowing")):
            errors.append(f"{where}: the wheat-book rows, and only they, say 'estimate' and carry their conditions")
    return errors


def validate_feature(kind, doc, field_doc=None, labels_doc=None):
    """One feature file (FEATURES): its schema, then what a schema cannot say."""
    errors = _schema_errors(doc, FEATURES[kind])
    if errors:
        return errors
    return {"labels": _labels_errors, "replay": _replay_errors, "pulse": _pulse_errors,
            "checkup": _checkup_errors, "simple": _simple_errors, "rainrisk": _rainrisk_errors,
            "fertiliser": _fertiliser_errors, "heatclock": _heatclock_errors}[kind](doc, field_doc, labels_doc)


def _inside(bbox, lon, lat):
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def validate_index(doc):
    errors = _schema_errors(doc, "index_schema.json")
    if errors:
        return errors
    if d := _dupes([f["id"] for f in doc["fields"]]):
        errors.append(f"fields: duplicate ids {d}")
    for f in doc["fields"]:
        b = f["bbox"]
        if not (b[0] < b[2] and b[1] < b[3]):
            errors.append(f"fields/{f['id']}/bbox: min must be below max")
        elif not _inside(b, f["lon"], f["lat"]):
            errors.append(f"fields/{f['id']}: lat/lon outside its bbox")
    areas = {a["id"]: a for a in doc.get("areas", [])}           # REVIEW_2 H6: areas from build_index.py
    if d := _dupes([a["id"] for a in doc.get("areas", [])]):
        errors.append(f"areas: duplicate ids {d}")
    listed = {f["id"]: f for f in doc["fields"]}
    for a in areas.values():
        for fid in a["fields"]:
            if fid not in listed:
                errors.append(f"areas/{a['id']}: field {fid} is not listed in fields")
            elif listed[fid]["area"] != a["id"]:
                errors.append(f"areas/{a['id']}: field {fid} names area {listed[fid]['area']}")
            elif not _inside(a["bbox"], listed[fid]["lon"], listed[fid]["lat"]):
                errors.append(f"areas/{a['id']}: field {fid} lies outside the area's bbox")
    for f in doc["fields"]:
        if f.get("area") is not None and f["area"] not in areas:
            errors.append(f"fields/{f['id']}: area {f['area']} is not in areas")
    return errors


def probe_log_problems(doc, index=None, field_doc=None):
    """site/data/probe_log.json (CLAUDE.md "How judges will see it" 4): real sessions only (the schema), a listed field,
    its own parts, the dates it says, and each reading's own lines (owner's launch brief, 2026-11-14)."""
    errors = _schema_errors(doc, "probe_log_schema.json")
    if errors:
        return errors
    if index is not None and doc["field"] not in {f["id"] for f in index["fields"]}:
        errors.append(f"field {doc['field']} is not listed in index.json")
    sections = {s["id"] for s in field_doc["field"]["sections"]} if field_doc else None
    dates = sorted({p["time"][:10] for s in doc["sessions"] for p in s["parts"]})
    if doc["recorded_on"] != dates:
        errors.append(f"recorded_on {doc['recorded_on']} must list the readings' dates {dates}")
    for s in doc["sessions"]:
        for p in s["parts"]:
            where = f"sessions/{s['id']}/{p['section']}"
            if sections is not None and p["section"] not in sections:
                errors.append(f"{where}: the field has no part {p['section']}")
            measured = sum(x["phase"] == "measure" for x in p["lines"])
            if p["lines"] and measured != p["n"]:
                errors.append(f"{where}: {measured} measure lines, but n is {p['n']}")
            if any(x["time"] > p["time"] for x in p["lines"]):
                errors.append(f"{where}: a line is timed after the part's reading")
    return errors


def version_problems(doc):
    """site/data/version.json, written by scripts/final_check.py."""
    errors = _schema_errors(doc, "version_schema.json")
    if not errors and not doc["commit"].startswith(doc["commit_short"]):
        errors.append("commit_short is not the start of commit")
    return errors


def basemap_problems(doc, path, data_dir, index):
    """site/data/basemap/<id>.json and its picture (pipeline/fetch/basemap.py): small, a JPEG, around its field."""
    from pipeline.fetch.basemap import MAX_FIELD_BYTES, MAX_WORLD_BYTES
    errors = _schema_errors(doc, "basemap_schema.json")
    if errors:
        return errors
    if doc["id"] != Path(path).stem:
        errors.append(f"id {doc['id']} is not the file's name")
    (s, w), (n, e) = doc["bounds"]
    if not (s < n and w < e):
        errors.append("bounds must be [[south, west], [north, east]]")
    img = Path(data_dir) / doc["image"][len("data/"):]
    limit = MAX_WORLD_BYTES if doc["id"] == "world" else MAX_FIELD_BYTES
    if not img.exists():
        errors.append(f"{doc['image']} does not exist")
    elif img.read_bytes()[:3] != b"\xff\xd8\xff":
        errors.append(f"{doc['image']} is not a JPEG")
    elif img.stat().st_size > limit:
        errors.append(f"{doc['image']} is {img.stat().st_size} bytes, over the {limit // 1000} KB limit")
    if doc["id"] != "world" and index is not None:
        entry = next((f for f in index["fields"] if f["id"] == doc["id"]), None)
        if entry is None:
            errors.append(f"{doc['id']} is not listed in index.json")
        elif not (s <= entry["lat"] <= n and w <= entry["lon"] <= e):
            errors.append(f"field {doc['id']} lies outside the picture's bounds")
    return errors


def _hidden_fields():
    from pipeline.fetch.rules import load_rules
    return set(load_rules().get("site_hidden_fields") or ())


def launch_problems(data_dir, index, final=False):
    """{path: problems} for the launch files (owner's launch brief, 2026-11-14): probe_log.json and version.json when
    they exist (no probe_log until real readings exist: the site says 'not ready yet'), and every basemap/*.json;
    --final also wants a basemap for every listed field (but one on the global defaults) and the world."""
    from pipeline.fetch.rules import load_rules
    # a field hidden from the app keeps its files (owner, 2026-11-15 afternoon): they need not be listed
    hidden = set(load_rules().get("site_hidden_fields") or ()) - {f["id"] for f in (index or {}).get("fields", [])}
    data_dir, out = Path(data_dir), {}
    log_path = data_dir / "probe_log.json"
    if log_path.exists():
        doc = json.loads(log_path.read_text())
        fpath = data_dir / "fields" / f"{doc.get('field')}.json"
        field_doc = json.loads(fpath.read_text()) if fpath.exists() else None
        if errs := probe_log_problems(doc, None if doc.get("field") in hidden else index, field_doc):
            out[str(log_path)] = errs
    ver = data_dir / "version.json"
    if ver.exists() and (errs := version_problems(json.loads(ver.read_text()))):
        out[str(ver)] = errs
    for path in sorted((data_dir / "basemap").glob("*.json")):
        if errs := basemap_problems(json.loads(path.read_text()), path, data_dir, None if path.stem in hidden else index):
            out[str(path)] = errs
    if final:
        # a field on the global defaults has no picture yet (basemap.py rebuilds every field's at once): the world's
        for fid in [f["id"] for f in (index or {}).get("fields", []) if f.get("profile") != "default"] + ["world"]:
            p = data_dir / "basemap" / f"{fid}.json"
            if not p.exists():
                out.setdefault(str(p), []).append("missing (python -m pipeline.fetch.basemap)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=str(REPO / "site" / "data"))
    ap.add_argument("--final", action="store_true",
                    help="the freeze check before submission: MOCK data and the other final checks are failures")
    args = ap.parse_args(argv)
    data_dir = Path(args.data_dir)
    problems = {}

    index_path = data_dir / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else None
    if index is None:
        problems[str(index_path)] = ["missing"]
    elif errs := validate_index(index):
        problems[str(index_path)] = errs

    field_files = sorted((data_dir / "fields").glob("*.json"))
    for path in field_files:
        doc = json.loads(path.read_text())
        errs = validate_field(doc, final=args.final)
        entry = next((f for f in (index or {}).get("fields", []) if f["id"] == path.stem), None)
        if index is not None and entry is None and path.stem not in _hidden_fields():
            errs.append("not listed in index.json")   # a hidden field keeps its file (owner, 2026-11-15 afternoon)
        elif entry and not errs and not _inside(entry["bbox"], doc["field"]["lon"], doc["field"]["lat"]):
            errs.append("field lat/lon outside its bbox in index.json")
        if errs:
            problems[str(path)] = errs
        if "MOCK" in path.read_text() and not args.final:
            print(f"WARNING {path}: contains MOCK data, must be replaced before submission (--final makes this a failure)")
        if doc.get("mock"):
            print(f"NOTE {path}: not ready yet (the site must say so): {', '.join(doc['mock'])}")

    for f in (index or {}).get("fields", []):
        if not (data_dir / "fields" / f"{f['id']}.json").exists():
            problems.setdefault(str(index_path), []).append(f"{f['id']}: listed but no fields/{f['id']}.json")
    for a in (index or {}).get("areas", []):
        if not (data_dir / a["map"][len("data/"):]).exists():          # map is relative to the site: data/area/<id>.json
            problems.setdefault(str(index_path), []).append(f"areas/{a['id']}: map {a['map']} does not exist")

    words_path = data_dir / "words.json"
    if words_path.exists():
        if errs := words_problems(json.loads(words_path.read_text())):
            problems[str(words_path)] = errs
    elif args.final:
        problems[str(words_path)] = ["missing (python -m pipeline.export.build_words)"]
    problems.update(launch_problems(data_dir, index, final=args.final))     # probe_log, version, basemap (2026-11-14)

    feature_files = 0
    for kind in FEATURES:                     # the four features (2026-11-14); --final wants one per listed field
        for path in sorted((data_dir / kind).glob("*.json")):
            feature_files += 1
            doc = json.loads(path.read_text())
            fp, lp = data_dir / "fields" / f"{path.stem}.json", data_dir / "labels" / f"{path.stem}.json"
            errs = validate_feature(kind, doc, json.loads(fp.read_text()) if fp.exists() else None,
                                    json.loads(lp.read_text()) if lp.exists() else None)
            if doc.get("field") != path.stem:
                errs.append(f"field '{doc.get('field')}' is not the file's name")
            if kind == "pulse" and doc.get("nearby") and not (data_dir / doc["nearby"]["map"][len("data/"):]).exists():
                errs.append(f"nearby/map: {doc['nearby']['map']} does not exist")
            if errs:
                problems[str(path)] = errs
        if args.final and (gone := missing_feature_files(index, data_dir, kind)):
            problems.setdefault(str(data_dir / kind), []).extend(gone)

    for path, errs in problems.items():
        for e in errs:
            print(f"FAIL {path}: {e}")
    checked = len(field_files) + (index is not None) + words_path.exists() + feature_files
    print(f"{checked} file(s) checked, {len(problems)} with problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
