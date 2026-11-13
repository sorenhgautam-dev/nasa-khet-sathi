"""Build steps 5 and 6b export: write the real replay and the method page's season-detection comparison into
site/data/fields/<id>.json, changing nothing else.

    .venv/bin/python -m pipeline.export.build_field_json --field demo

Reads data/checks/<field>/replay.json (written by scripts/run_replay.py) and the field file as it stands
(still MOCK elsewhere until later steps). Refuses, and leaves the file untouched, when the replay was not
made with GPM rain (D6: POWER never stands in for the whole series; temporary station rain is for checks
only), when its years are not one unbroken run ending in 2025, when a year after the first misses a crop
of the rotation, or when a year has no event. Only complete years are exported: a first year that lacks a
crop of the rotation (2001 has rice only) is left out (owner's batch decisions item 14, 2026-11-12). It also
sets field.water_source from the replay ('unknown' while the field's water is not known: the site shows the
rain-fed and irrigated cases side by side, item 8). The result must validate against schema.json before it
is written.

Build step 7 (2026-11-13): with data/checks/<field>/plans.json (scripts/run_plans.py) it also writes the three plans
(current, cover_gap, safest; rules.yaml plans), each with its replay, its five tabs and tips in English and Nepali
(pipeline/plans/explain.py), the sources, and the method page's rain correction and stated choices. Owner's decision 1
(2026-11-13): every result the 2017 rain correction changes carries the uncorrected run beside it (replay years'
uncorrected_rain, plans' score_uncorrected_rain), from data/checks/<field>/rain_uncorrected/.
"""
from collections import Counter
import argparse
import copy
import json
import sys
from pathlib import Path

from pipeline.export.validate import validate_field

REPO = Path(__file__).resolve().parents[2]
FIRST_YEAR, LAST_YEAR = 2001, 2025


def complete_years(years, rotation):
    """The years to export: an unbroken run ending in LAST_YEAR, each holding every crop of the rotation. Only
    the first year may be incomplete (its winter crop was sown before the weather record) and it is dropped."""
    got = [y["year"] for y in years]
    if not got or got[0] < FIRST_YEAR or got[-1] != LAST_YEAR or got != list(range(got[0], LAST_YEAR + 1)):
        gaps = sorted(set(range(FIRST_YEAR, LAST_YEAR + 1)) - set(got))
        raise ValueError(f"replay years must run unbroken to {LAST_YEAR}; got {got[:2]}...{got[-2:]}, missing {gaps}")
    want = Counter(rotation)
    bad = [y["year"] for y in years if Counter(y["crops"]) != want]
    if bad and bad[0] == got[0]:
        bad = bad[1:]
    if bad:
        raise ValueError(f"year(s) {bad} miss a crop of the rotation {list(rotation)}: only the first year may")
    return [y["year"] for y in years if Counter(y["crops"]) == want]


def replay_rows(replay, doc=None):
    """[{year, harvest, dry_days, event, irrigated}] of a replay export (run_replay or run_plans), complete years only,
    after the checks of apply_replay."""
    if replay["labels"].get("rain_source") != "gpm":
        raise ValueError(f"replay rain is '{replay['labels'].get('rain_source')}', not GPM (D6): not exported")
    keep = complete_years(replay["years"], replay["labels"]["rotation"])
    if not replay.get("events"):
        raise ValueError("no events computed for this replay yet (rules.yaml events)")
    if doc is not None and "placeholder" in str(replay["labels"].get("rotation_source", "")).lower() \
            and "placeholder" not in doc["field"]["name"].lower():
        raise ValueError("the replay uses a placeholder rotation but the field file is not labelled placeholder")
    missing = [y for y in keep if str(y) not in replay["events"]]
    if missing:
        raise ValueError(f"no event for year(s) {missing}")
    irr = {y["year"]: y for y in replay.get("irrigated_years") or []}
    if sorted(irr) != [y["year"] for y in replay["years"]]:
        raise ValueError("the irrigated case must cover the same years as the field's own case (owner's go, 2026-11-12)")
    seasons = replay.get("event_seasons") or {}            # owner's answer 9 (2026-11-13): "dry winter", "dry monsoon"
    rows = []
    for y in replay["years"]:
        if y["year"] not in keep:
            continue
        row = {"year": y["year"], "harvest": int(round(y["harvest"])), "dry_days": int(y["dry_days"]),
               "event": replay["events"][str(y["year"])]}
        if row["event"] == "drought" and str(y["year"]) in seasons:
            row["event_season"] = seasons[str(y["year"])]
        row["irrigated"] = {"harvest": int(round(irr[y["year"]]["harvest"])), "dry_days": int(irr[y["year"]]["dry_days"])}
        rows.append(row)
    return rows


def with_uncorrected(rows, rows_unc):
    """Owner's decision 1 (2026-11-13): each year whose uncorrected-rain run differs (harvest, dry days, event or the
    watered case) carries it as uncorrected_rain; other years are left as they are."""
    unc = {r["year"]: r for r in rows_unc}
    if sorted(unc) != [r["year"] for r in rows]:
        raise ValueError("the uncorrected run must cover the same years")
    out = []
    for r in rows:
        u = {k: unc[r["year"]][k] for k in ("harvest", "dry_days", "event", "event_season", "irrigated") if k in unc[r["year"]]}
        differs = any(u.get(k) != r.get(k) for k in ("harvest", "dry_days", "event", "event_season", "irrigated"))
        out.append({**r, "uncorrected_rain": u} if differs else dict(r))
    return out


def apply_replay(doc, replay, plan_id="current"):
    """Return a copy of `doc` with replay[plan_id] = [{year, harvest, dry_days, event}, ...]."""
    rows = replay_rows(replay, doc)
    out = copy.deepcopy(doc)
    out["field"]["water_source"] = replay["labels"].get("water_source") or "unknown"
    out["replay"][plan_id] = rows
    # the event belongs to the field's year, not to a plan (owner's answer 9, 2026-11-13): the other plans' same years take it
    by_year = {r["year"]: r for r in rows}
    for pid, other in out["replay"].items():
        for y in other if pid != plan_id else []:
            if y["year"] in by_year:
                y["event"] = by_year[y["year"]]["event"]
                y.pop("event_season", None)
                if "event_season" in by_year[y["year"]]:
                    y["event_season"] = by_year[y["year"]]["event_season"]
    errs = validate_field(out)
    if errs:
        raise ValueError(f"field file would break the contract: {errs}")
    return out


def method_from_seasons(seasons):
    """The method page's season_detection block from data/checks/<field>/diary_seasons.json (step 6b)."""
    h, dd = seasons["held_out"], seasons["season_date_differences_days"]
    diffs = {"threshold": {"start": None, "peak": None, "end": None},
             "changepoint": dd["changepoint_vs_threshold"], "detective": dd["detective_vs_threshold"]}
    methods = []
    for mid in ("threshold", "changepoint", "detective"):
        methods.append({"id": mid, "si": mid == "detective", "score": round(h["mean_score"][mid], 3),
                        "by_year": [{"year": int(y), "score": round(v["thinned"][mid], 3)} for y, v in h["per_year"].items()],
                        **{f"{k}_diff_days": diffs[mid][k] for k in ("start", "peak", "end")}})
    return {"chosen": h["best"], "margin": h["best_margin"], "held_out_years": [int(y) for y in h["years"]],
            "thin_days": h["thin_days"], "rule_methods_agree": round(h["threshold_vs_changepoint_all_obs"], 3),
            "methods": methods}


def apply_method(doc, seasons, check=True):
    """Return a copy of `doc` with method.season_detection from the step-6b comparison; it must validate (check=False
    when a later step of the same export replaces the rest of the file and validates the whole)."""
    out = copy.deepcopy(doc)
    out.setdefault("method", {})["season_detection"] = method_from_seasons(seasons)
    errs = validate_field(out) if check else []
    if errs:
        raise ValueError(f"field file would break the contract: {errs}")
    return out


def apply_diary(doc, diary, check=True):
    """Return a copy of `doc` with the real diary (data/checks/<field>/diary.json 'export', step 6c); it must validate
    (check=False as for apply_method)."""
    d = diary["export"]
    if not d.get("months") or len(d["months"]) != 12:
        raise ValueError("the diary needs twelve months")
    out = copy.deepcopy(doc)
    out["diary"] = {"shift_days": d["shift_days"], "bare_days": int(d["bare_days"]), "guess": list(d["guess"]),
                    "groundwater": dict(d["groundwater"]), "months": [dict(m) for m in d["months"]]}
    errs = validate_field(out) if check else []
    if errs:
        raise ValueError(f"field file would break the contract: {errs}")
    return out


# ---------- build step 7: plans, sources, method page ----------

SCORE_KEYS = ("harvest", "water", "cover", "soil_kept")
MONTH_KEYS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def score_block(scores):
    return {k: int(round(scores[k])) for k in SCORE_KEYS}


def stated_choices(rules):
    """The method page's list (owner, 2026-11-13: keep the stated choices listed there): every rules.yaml entry whose
    source says it is Claude's choice, reading, rule, mapping or proposal, with its approval as written there."""
    import re
    out = []

    def walk(node, path):
        if isinstance(node, dict) and "value" in node and "source" in node:
            src = str(node["source"])
            # REVIEW_2 M7: also "is Claude's" and "by Claude" (a rule Claude added or proposed), and the approval
            # however it is capitalised ("Owner-approved 2026-11-13 ..." was exported as plain "Claude's choice")
            if re.search(r"Claude's (choice|choices|reading|rule|mapping|proposal)|\bis Claude's|\bby Claude\b", src):
                m = re.search(r"(?i)owner-approved (\d{4}-\d{2}-\d{2})", src)
                status = (f"Claude's choice, owner-approved {m.group(1)}" if m else
                          "Claude's choice, put to the owner" if re.search(r"(?i)put (back )?to the owner", src)
                          else "Claude's choice")
                out.append({"id": path, "choice": src, "value": str(node["value"]), "status": status})
            return
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)

    walk(rules, "")
    return out


def sources_block(soil_distance_m=None, soil_around=None):
    """Every dataset behind a number on the site (golden rule 8: model-based data labelled model).

    REVIEW_2 M5, M6 (2026-11-13): the soil row names what the twin reads (the two water contents) and, when the
    cell used is not the field's own, how far away it is (soil_distance_m, from the soil data card); the MODIS row
    says that no number shown uses it (bare days, cover months, the guess and the method page are HLS years only)."""
    soil_where = (f"; nearest cell with values, {soil_distance_m:.0f} m from the field" if soil_distance_m else "")
    if soil_around and soil_around.get("cells", 0) > 1:      # owner's answer 10 (2026-11-13): the neighbourhood range
        a = soil_around
        soil_where += (f". Water it holds for plants in the top {a['depth_m']:g} m: {a['used_mm']:.0f} mm; the {a['cells']} cells "
                       f"within {a['radius_m'] / 1000:g} km of the field hold {a['min_mm']:.0f} to {a['max_mm']:.0f} mm")
    return [
        {"name": "GPM IMERG", "product": "V07 Final daily (Late for Oct-Dec 2025); days from 2017 scaled back, month by "
         "month, to its own 2001-2016 level (the rain gauges behind it stopped reporting here)", "resolution": "0.1 deg (about 10 km)",
         "years": "2001-2025", "type": "satellite"},
        {"name": "NASA POWER", "product": "Daily API v2.10.3 (MERRA-2 weather, CERES sunshine); temperatures corrected "
         "to Kathmandu Airport", "resolution": "0.5 x 0.625 deg (about 55 km)", "years": "2001-2025", "type": "model"},
        {"name": "Kathmandu Airport station", "product": "NOAA GHCN-Daily NP000444540 (temperature correction, checks)",
         "resolution": "one point, 7 km west", "years": "2001-2025", "type": "station"},
        {"name": "Harmonized Landsat Sentinel-2", "product": "HLS-VI v2.0 greenness (NDVI)", "resolution": "30 m",
         "years": "2013-2025", "type": "satellite"},
        {"name": "MODIS Terra", "product": "MOD13Q1 v061 greenness (NDVI), before HLS: compared with HLS only; "
         "no number shown uses it", "resolution": "250 m", "years": "2001-2013", "type": "satellite"},
        {"name": "GRACE and GRACE-FO", "product": "JPL mascon CRI RL06.3 v04: water stored across the region",
         "resolution": "about 300 km", "years": "2002-2026", "type": "satellite"},
        {"name": "ISRIC SoilGrids", "product": "2.0: water the soil holds at field capacity and wilting point "
         f"(machine-learning map){soil_where}", "resolution": "250 m", "years": "one map", "type": "model"},
        {"name": "NASADEM", "product": "v001 elevation", "resolution": "30 m", "years": "2000", "type": "satellite"},
        {"name": "Khet Sathi field twin", "product": "FAO-56 soil water, FAO-33 harvest, from the data above",
         "resolution": "the field", "years": "2001-2025", "type": "model"},
    ]


NOT_READY = ("field.sections", "future")     # build steps 8 and 9


GREENER_WORD = {"greener": "more", "less green": "less", "same": "same", "can't tell": "unknown"}


def not_ready_blocks(doc, field, sections=None, twin_state=None):
    """Owner's answer 2 to REVIEW_2 (2026-11-13): no made-up number is exported. A block not computed yet holds no
    numbers and is named in `mock` so the site can say 'not ready yet'. The field's name, lat and lon come from its
    config (no '(MOCK data)').

    Sections (owner's group 2a, 2026-11-14): with data/checks/<field>/sections.json (scripts/run_sections.py: the parts
    that tile the real field, each about one HLS pixel) AND the twin's state (data/clean/<field>/twin_state.json), each
    part gets the twin's wetness (one bucket for the whole field: every part shares it), its status (rules.yaml
    sections), the twin's own sureness before any probe reading (sure_prior), its own greenness word and its
    low-ground flag. Without the twin's state the parts keep their outlines and say nothing. The 2040 outlook is
    filled later in the export (build step 9); here it is null and named."""
    from pipeline.sections.grid import grid_sections
    out = copy.deepcopy(doc)
    out["field"]["name"], out["field"]["lat"], out["field"]["lon"] = field["name"], field["lat"], field["lon"]
    out["field"].pop("status_date", None)
    mock = list(NOT_READY)
    parts = sections["sections"] if sections else grid_sections(field["polygon"])
    if sections and twin_state:
        out["field"]["sections"] = [{
            "id": s["id"], "polygon": s["polygon"], "status": s["status"], "wetness": int(round(s["wetness_pct"])),
            "temp": None, "sure": round(float(twin_state["sure_prior"]), 2), "low_ground": s.get("low_ground"),
            "greener": GREENER_WORD[s["greenness"]["usually"]]} for s in parts]
        out["field"]["status_date"] = twin_state["date"]
        mock.remove("field.sections")
    else:
        out["field"]["sections"] = [{"id": s["id"], "polygon": s["polygon"], "status": "grey", "wetness": None,
                                     "temp": None, "sure": 0} for s in parts]
    out["future"] = None
    out["mock"] = mock
    return out


def apply_onset_dhm(doc, onset):
    """Owner, 2026-11-14 ("fix the answer, not the method"): the monsoon's shift and usual start come from DHM's official
    onset dates (data/checks/<field>/onset_dhm.json, scripts/run_onset_dhm.py; rules.yaml monsoon_onset_dhm), credited
    to DHM, with the caveat that DHM's date is the monsoon's entry into eastern Nepal. The two satellite-rain onset
    methods stay recorded as failed checks (VALIDATION 4.1d, 4.1e, 3.22)."""
    out = copy.deepcopy(doc)
    e = onset["export_proposal"]
    dy = out["diary"]
    dy["shift_days"], dy["shift_days_low"], dy["shift_days_high"] = (e["diary.shift_days"], e["diary.shift_days_low"],
                                                                     e["diary.shift_days_high"])
    dy["shift_source"] = dict(e["diary.shift_source"])
    dy["shift_note"] = {k: list(e["diary.shift_note"][k]) for k in ("en", "ne")}
    dy["monsoon_start"] = {**e["diary.monsoon_start"], "words": {k: list(e["next3.rice_start"][k]) for k in ("en", "ne")}}
    out["method"]["onset"] = {"words": {k: list(e["method.how_we_know"][k]) for k in ("en", "ne")},
                              "caveat": e["method.onset_caveat"]}
    row = dict(e["sources[] (new row)"])
    out["sources"] = [s for s in out["sources"] if s["name"] != row["name"]] + [row]
    return out


FUTURE_WORDS = {   # what the range means (owner's group 2e, 2026-11-14); Nepali needs native-speaker review
    "en": ["Climate models show the years to 2040.", "Each model shows a slightly different future.",
           "The range spans the lowest to highest.", "The real future could still fall outside."],
    "ne": ["जलवायु मोडेलहरूले सन् २०४० सम्मका वर्ष देखाउँछन्।", "हरेक मोडेलले अलि फरक भविष्य देखाउँछ।",
           "दायरा सबैभन्दा कमदेखि सबैभन्दा बढीसम्म हो।", "साँचो भविष्य यो दायराबाहिर पनि पर्न सक्छ।"]}


def apply_future(doc, future, plan_ids, option_ids):
    """Build step 9 (owner's group 2e, 2026-11-14): the 2040 outlook from data/checks/<field>/future.json
    (scripts/run_future.py: NEX-GDDP-CMIP6 delta change onto the field's corrected 2001-2025 weather; rules.yaml future).
    plan_ids: {role: plan id}; option_ids: {option id: plan id}. Each series is the median run with the lowest and
    highest model-scenario run as its range, in whole points; `years` [2040] stands for the period 2026-2040. The
    uncorrected-rain version is added only where it differs. Removes 'future' from `mock`."""
    out = copy.deepcopy(doc)

    def series(pid, version):
        o = future["plans"][pid][version]["outlook"]
        return {"harvest": [int(round(o["harvest"]))], "harvest_low": [int(round(o["harvest_low"]))],
                "harvest_high": [int(round(o["harvest_high"]))]}

    per = future["labels"]["periods"]["future"]
    out["future"] = {"years": [per[1]], "period": f"{per[0]}-{per[1]}", "models": list(future["models"]),
                     "scenarios": list(future["labels"]["scenarios"]),
                     "nothing_changes": series(plan_ids["current"], "corrected"),
                     "with_plan": series(plan_ids["cover_gap"], "corrected"), "words": FUTURE_WORDS}
    for p in out["plans"]:
        p["future"] = series(plan_ids[p["id"]], "corrected")
        u = series(plan_ids[p["id"]], "uncorrected")
        if u != p["future"]:
            p["future_uncorrected_rain"] = u
    for o in (out.get("current_options") or {}).get("options", []):
        o["future"] = series(option_ids[o["id"]], "corrected")
        u = series(option_ids[o["id"]], "uncorrected")
        if u != o["future"]:
            o["future_uncorrected_rain"] = u
    out["mock"] = [m for m in out.get("mock", []) if m != "future"]
    return out


PLAN_SOURCES = ("GPM IMERG", "NASA POWER", "ISRIC SoilGrids", "GRACE and GRACE-FO")


def field_memory_block(memory, words_tabs):
    """The method page's field-memory block from data/checks/<field>/field_memory.json (build step 7b): the test's
    numbers and plain words, whichever way it went (CLAUDE.md: 'report the result either way')."""
    from pipeline.words.texts import render_tab
    r = memory["result"]
    held = {"memory_kept" if r["kept"] else "memory_not_kept"}
    vals = {"memory_seasons": int(r["n_seasons"])}
    lines = words_tabs["method_page"]["field_memory"]
    return {"kept": bool(r["kept"]), "seasons": int(r["n_seasons"]), "years": int(r["n_years"]),
            "error": {k: round(float(r["rmse"][k]), 3) for k in ("no_anomaly", "physics_only", "memory")},
            "words": {lang: render_tab(lines, held, vals, lang) for lang in ("en", "ne")}}


def rain_correction_block(rain_break, rain_check, evidence, words_tabs, shared):
    """method.rain_correction (owner's decision 1, 2026-11-13): the numbers, and the plain words from
    pipeline/words/tabs.json method_page.rain_correction in English and Nepali."""
    from pipeline.words.texts import render_tab
    bc, h = rain_check["break_correction"], rain_check["break_correction"]["held_out"]
    gpm_pre = rain_check["sources"]["gpm_2001_2016"]["annual_mm"]
    gpm_post = rain_check["sources"]["gpm_2017_2025"]["annual_mm"]
    block = {"applied": True, "from": rain_break["from"], "reference_years": list(rain_break["reference_years"]),
             "factors": {m: rain_break["factors_by_month"][m] for m in MONTH_KEYS},
             "held_out": {"months": h["months"], "error_before_mm": round(h["mae_raw_mm"], 1),
                          "error_after_mm": round(h["mae_corrected_mm"], 1), "ratio_before": round(h["ratio_raw"], 2),
                          "ratio_after": round(h["ratio_corrected"], 2)},
             "rain_mm_per_year": {"reference": round(gpm_pre), "after_uncorrected": round(gpm_post),
                                  "after_corrected": round(bc["twin_rain_2017_2025_annual_mm"]),
                                  "station_normal": round(rain_check["normals_mm"]["Bhaktapur"]["annual"])},
             "gauges": {"weight_before_pct": evidence["gauge_weight_before_pct"],
                        "weight_after_pct": evidence["gauge_weight_after_pct"],
                        "stations_before": evidence["gpcc_stations_before"], "stations_after": evidence["gpcc_stations_after"]}}
    r10 = lambda x: int(round(x, -1))                                                     # noqa: E731
    vals = {"rain_fix_year": int(rain_break["from"][:4]), "rain_before": r10(gpm_pre), "rain_after": r10(gpm_post),
            "rain_normal": r10(block["rain_mm_per_year"]["station_normal"]),
            "err_before": int(round(h["mae_raw_mm"])), "err_after": int(round(h["mae_corrected_mm"]))}
    lines = words_tabs["method_page"]["rain_correction"]
    block["words"] = {lang: render_tab(lines, set(), vals, lang) for lang in ("en", "ne")}
    return block


def _window_notes(plan_id, lib):
    out = []
    for part in plan_id.split("+"):
        crop, w, _ = part.split(".")
        out.append(lib[crop]["calendar"]["windows"][int(w[1:])].get("note"))
    return out


def apply_plans(doc, plans, plans_unc, lib, words, ctx):
    """doc with the three plans and their replays (build step 7). plans / plans_unc: plans.json of the corrected and
    the uncorrected run; ctx: diary-independent context for the words (explain.render). Validated before return."""
    from pipeline.plans import explain as ex
    out = copy.deepcopy(doc)
    roles = ("current", "cover_gap", "safest")
    if plans_unc is not None and [plans_unc["export"][r]["plan"] for r in roles] != [plans["export"][r]["plan"] for r in roles]:
        raise ValueError("the uncorrected run must export the same plans as the corrected one")
    replay = {}
    for r in roles:
        rows = replay_rows(plans["export"][r]["replay"], out)
        if plans_unc is not None:
            rows = with_uncorrected(rows, replay_rows(plans_unc["export"][r]["replay"], out))
        replay[r] = rows
    out["field"]["water_source"] = plans["export"]["current"]["replay"]["labels"].get("water_source") or "unknown"
    contract, info = [], {}
    for r in roles:
        e = plans["export"][r]
        p = {"id": r, "name": e["name"], "crops": [dict(s) for s in e["spans"]], "score": score_block(e["score"])}
        if plans_unc is not None:
            u = score_block(plans_unc["export"][r]["score"])
            if u != p["score"]:
                p["score_uncorrected_rain"] = u
        info[r] = {**p, "stability": e["stability"], "pest_break": e["pest_break"],
                   "needs_water_window": e["needs_water_window"], "windows": _window_notes(e["plan"], lib),
                   "thirsty": e["replay"].get("thirsty", {}), "gain_range": e.get("gain_range"),
                   "cover_days": round(e["score"]["cover"] / 100.0 * 365)}
        contract.append(p)
    options = plans.get("current_options") or []
    c = {**ctx, "diary": out["diary"], "replay": replay, "winter_crop_unconfirmed": len(options) > 1,
         "plan_sources": [s for s in out["sources"] if s["name"] in PLAN_SOURCES]}
    for p in contract:
        w = ex.render(info[p["id"]], info["current"], c, lib, words)
        p.update(tabs=w["tabs"], tips=w["tips"], tabs_ne=w["tabs_ne"], tips_ne=w["tips_ne"])
    out["plans"], out["replay"] = contract, replay
    # owner's answer 6 to REVIEW_2 (2026-11-13): the current plan once for each rotation the farmer may confirm
    if len(options) > 1:
        unc_by_id = {o["id"]: o for o in (plans_unc.get("current_options") or [])} if plans_unc is not None else {}
        blocks = []
        for k, o in enumerate(options):
            if k == 0:                                   # the default is what plans[0] and replay.current hold
                cur_p, cur_info, rows = contract[0], info["current"], replay["current"]
            else:
                rows = replay_rows(o["replay"], out)
                cur_p = {"id": "current", "name": contract[0]["name"], "crops": [dict(s) for s in o["spans"]],
                         "score": score_block(o["score"])}
                if o["id"] in unc_by_id:
                    rows = with_uncorrected(rows, replay_rows(unc_by_id[o["id"]]["replay"], out))
                    u = score_block(unc_by_id[o["id"]]["score"])
                    if u != cur_p["score"]:
                        cur_p["score_uncorrected_rain"] = u
                cur_info = {**cur_p, "stability": o["stability"], "pest_break": o["pest_break"],
                            "needs_water_window": o["needs_water_window"], "windows": _window_notes(o["plan"], lib),
                            "thirsty": o["replay"].get("thirsty", {}), "gain_range": None,
                            "cover_days": round(o["score"]["cover"] / 100.0 * 365)}
            ck = {**c, "replay": {**replay, "current": rows}}
            block = {"id": o["id"], "crops": cur_p["crops"], "score": cur_p["score"]}
            if "score_uncorrected_rain" in cur_p:
                block["score_uncorrected_rain"] = cur_p["score_uncorrected_rain"]
            w = ex.render(cur_info, cur_info, ck, lib, words) if k else contract[0]
            block.update(tabs=w["tabs"], tips=w["tips"], tabs_ne=w["tabs_ne"], tips_ne=w["tips_ne"], replay=rows, compared={})
            for r in roles[1:]:
                other = {**info[r], "gain_range": o["gain_range"][r]}
                wr = ex.render(other, cur_info, ck, lib, words)
                block["compared"][r] = {"tabs": wr["tabs"], "tabs_ne": wr["tabs_ne"]}
            blocks.append(block)
        out["current_options"] = {"default": options[0]["id"], "options": blocks}
    else:
        out.pop("current_options", None)
    errs = validate_field(out)
    if errs:
        raise ValueError(f"field file would break the contract: {errs}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    src = REPO / "data" / "checks" / a.field / "replay.json"
    dest = REPO / "site" / "data" / "fields" / f"{a.field}.json"
    if not src.exists():
        print(f"NOT YET POSSIBLE: {src.relative_to(REPO)} does not exist (scripts/run_replay.py needs GPM rain). "
              f"{dest.relative_to(REPO)} left unchanged.")
        return 2
    replay = json.loads(src.read_text())
    seasons_path = REPO / "data" / "checks" / a.field / "diary_seasons.json"
    try:
        doc = json.loads(dest.read_text())
        doc.setdefault("method", {"season_detection": None})
        plans_path = REPO / "data" / "checks" / a.field / "plans.json"
        whole = not plans_path.exists()      # with plans.json the last step replaces plans and replays and validates the whole
        if seasons_path.exists():
            doc = apply_method(doc, json.loads(seasons_path.read_text()), check=whole)
        diary_path = REPO / "data" / "checks" / a.field / "diary.json"
        if diary_path.exists():
            doc = apply_diary(doc, json.loads(diary_path.read_text()), check=whole)
        if plans_path.exists():
            doc = export_step7(doc, a.field, json.loads(plans_path.read_text()))
        else:
            doc = apply_replay(doc, replay["export"], plan_id="current")
    except ValueError as e:
        print(f"REFUSED: {e}. {dest.relative_to(REPO)} left unchanged.")
        return 1
    dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote the plans {[p['id'] for p in doc['plans']]} with their replays ({len(doc['replay']['current'])} years), "
          f"the diary, the sources and the method page (season detection: {doc['method']['season_detection']['chosen']}"
          f"{'; rain correction' if 'rain_correction' in doc['method'] else ''}) into {dest.relative_to(REPO)}")
    return 0


def export_step7(doc, field_id, plans):
    """Build step 7's part of main: sources, method page, the three plans (and their uncorrected-rain ranges)."""
    from pipeline.fetch.cropslib import load_crops
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.rules import load_rules
    from pipeline.plans import explain as ex
    from pipeline.words import texts
    field, rules, lib = load_field(field_id), load_rules(), load_crops()
    checks = REPO / "data" / "checks" / field_id
    unc_path = checks / "rain_uncorrected" / "plans.json"
    plans_unc = json.loads(unc_path.read_text()) if unc_path.exists() else None
    if plans["labels"].get("rain_version") != "corrected" or (plans_unc and plans_unc["labels"].get("rain_version") != "uncorrected"):
        raise ValueError("plans.json must be the corrected-rain run and rain_uncorrected/plans.json the uncorrected one")
    sec_path, state_path = checks / "sections.json", REPO / "data" / "clean" / field_id / "twin_state.json"
    out = not_ready_blocks(doc, field, sections=json.loads(sec_path.read_text()) if sec_path.exists() else None,
                           twin_state=json.loads(state_path.read_text()) if state_path.exists() else None)
    soil_card_path = REPO / "data" / "cards" / field_id / "soilgrids.json"
    soil_card = json.loads(soil_card_path.read_text()) if soil_card_path.exists() else {}
    soil_loc = soil_card.get("location", {})
    out["sources"] = sources_block(soil_distance_m=soil_loc.get("distance_m") if isinstance(soil_loc, dict) else None,
                                   soil_around=(soil_card.get("summary") or {}).get("water_held_for_plants"))
    onset_path = checks / "onset_dhm.json"
    if onset_path.exists():
        out = apply_onset_dhm(out, json.loads(onset_path.read_text()))
    card = json.loads((REPO / "data" / "cards" / field_id / "weather.json").read_text())
    rain_break = card["corrections"].get("rain_break", {})
    rain_check = json.loads((checks / "rain_check_b.json").read_text())
    words = {"tabs": texts.load("tabs"), "shared": texts.load("screens")["shared"]}
    if rain_break.get("applied"):
        if plans_unc is None:
            raise ValueError("the rain was corrected but the uncorrected run is missing (owner's decision 1: show both)")
        out["method"]["rain_correction"] = rain_correction_block(rain_break, rain_check, rules["gpm_series"]["break_evidence"],
                                                                 words["tabs"], words["shared"])
    memory_path = checks / "field_memory.json"
    if memory_path.exists():
        out["method"]["field_memory"] = field_memory_block(json.loads(memory_path.read_text()), words["tabs"])
    import yaml
    out["method"]["choices"] = stated_choices(yaml.safe_load((REPO / "config" / "rules.yaml").read_text()))
    ratio = rain_check["break_correction"]["twin_rain_vs_station_all_shared_months"]["ratio"]
    station_less = 1 - 1 / ratio                                  # share less rain at the station than in the twin
    import pandas as pd
    wx = pd.read_parquet(REPO / "data" / "clean" / field_id / "weather.parquet")
    twin_mm = float(wx.groupby(pd.DatetimeIndex(wx["date"]).year)["rain_mm"].sum().mean())
    normal_mm = float(rain_check["normals_mm"]["Bhaktapur"]["annual"])
    soil_far = (isinstance(soil_loc, dict) and soil_loc.get("distance_m") is not None
                and float(soil_loc["distance_m"]) > float(rules["soilgrids"]["nearest_cell_step_m"]))
    ctx = {"tips": rules["tips"], "rain_reads_high": twin_mm / normal_mm >= rules["gpm_series"]["level_caveat_ratio"],
           "rain_level": {"twin_mm_per_year": round(twin_mm, 1), "station_normal_mm": round(normal_mm, 1),
                          "ratio": round(twin_mm / normal_mm, 2)},
           "soil_distance_m": int(round(float(soil_loc["distance_m"]))) if soil_far else None,
           "water_source_unknown": field.get("water_source") is None, "placeholder": bool(field.get("placeholder")),
           "station_rain_lower": 0.25 <= station_less <= 0.40, "rain_corrected": bool(rain_break.get("applied")),
           "rain_fix_year": int(rain_break["from"][:4]) if rain_break.get("applied") else None,
           "legume_option": ex.legume_option(plans["plans"], rules["plans"]["suggested_must_include"], lib)}
    out = apply_plans(out, plans, plans_unc, lib, words, ctx)
    future_path = checks / "future.json"
    if future_path.exists():
        fut = json.loads(future_path.read_text())
        plan_ids = {r: plans["export"][r]["plan"] for r in ("current", "cover_gap", "safest")}
        option_ids = {o["id"]: o["plan"] for o in plans.get("current_options") or []}
        missing = [p for p in list(plan_ids.values()) + list(option_ids.values()) if p not in fut["plans"]]
        if missing:
            raise ValueError(f"future.json lacks the plans {missing}: rerun scripts/run_future.py after run_plans.py")
        out = apply_future(out, fut, plan_ids, option_ids)
        src = dict(fut["words_proposed"]["source_entry"])
        out["sources"] = [s for s in out["sources"] if s["name"] != src["name"]] + [src]
        errs = validate_field(out)
        if errs:
            raise ValueError(f"field file would break the contract: {errs}")
    return out


if __name__ == "__main__":
    sys.exit(main())
