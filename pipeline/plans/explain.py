"""Plain words for each plan (CLAUDE.md "Plans" steps 5-6, build step 7): the five tabs and the tips, in English and
Nepali, filled from the numbers with the templates in pipeline/words (tabs.json, registry fill_registry.json).
Pure functions: the caller passes the word files, config/crops.json and the numbers.

Every template is an SI draft (SI_LOG.md); each Nepali text carries "needs native-speaker review" until a reviewer
signs it (pipeline/words/texts.py). Which lines appear is decided only by the conditions below, each defined in the
registry; nothing here writes free text.
"""
import re

from pipeline.words.texts import fill, render_tab

TAB_KEYS = ("why", "evidence", "benefits", "unknown", "check")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PLAN_KINDS = {"current": "plan_is_current", "cover_gap": "plan_is_cover_gap", "safest": "plan_is_safest",
              "follow_shift": "plan_is_follow_shift"}


def capitalize_sentences(text):
    """English only: a crop name filled in at the start of a sentence ('rice gets ...') gets its capital letter."""
    return re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def legume_option(rows, must_include, lib):
    """The legume of the best rice plan with a legume (best 10th-percentile year, ties: harvest), or None: the option
    named in the cover-the-gap plan's tabs (owner's decision 4, 2026-11-13)."""
    pool = [r for r in rows if must_include in r["crops"] and any(lib[c].get("legume") for c in r["crops"])]
    if not pool:
        return None
    best = max(pool, key=lambda r: (r["stability"], r["harvest"]))
    return next(c for c in best["crops"] if lib[c].get("legume"))


def irrigated_window(note):
    n = str(note or "").lower()
    return "irrigat" in n and "rainfed" not in n


def bare_months(spans):
    """Months the plan's calendar leaves bare on every day: [(month 1-12), ...] in calendar order, starting after
    the plan's last harvest. spans: [{crop, start 'MM-DD', end 'MM-DD'}] (a season may cross the new year)."""
    import pandas as pd
    year = pd.date_range("2001-01-01", "2001-12-31")
    covered = pd.Series(False, index=year)
    for s in spans:
        a, b = pd.Timestamp(f"2001-{s['start']}"), pd.Timestamp(f"2001-{s['end']}")
        covered |= (year >= a) & (year <= b) if a <= b else (year >= a) | (year <= b)
    bare = [m for m in range(1, 13) if not covered[year.month == m].any()]
    first = int(spans[-1]["end"][:2]) if spans else 1          # spans in sowing order: the last one ends the year
    return sorted(bare, key=lambda m: (m - first) % 12)


def conditions(plan, current, ctx, lib):
    """The registry's conditions that hold for this plan (fill_registry.json 'conditions')."""
    crops = [c["crop"] for c in plan["crops"]]
    cur_crops = [c["crop"] for c in current["crops"]]
    d = ctx["diary"]
    held = {PLAN_KINDS[plan["id"]]} if plan["id"] in PLAN_KINDS else set()
    sd = d.get("shift_days")
    if sd is not None:
        held.add("onset_earlier" if round(sd) < 0 else "onset_later" if round(sd) > 0 else "onset_same")
    held.add(f"groundwater_{d['groundwater']['direction']}")
    if any(m["frost"] != "none" for m in d["months"]):
        held.add("has_frost_risk")
    if ctx.get("water_source_unknown"):
        held.add("water_source_unknown")
    if ctx.get("station_rain_lower"):
        held.add("station_rain_lower")
    if ctx.get("placeholder"):
        held.add("field_is_placeholder")
    if any(c not in cur_crops for c in crops):
        held.add("new_crop")
    if any(lib[c].get("legume") for c in crops):
        held.add("has_legume")
    if plan.get("pest_break"):
        held.add("breaks_family")
    zr = lambda cs: max((lib[c].get("zr_m") or 0) for c in cs)   # noqa: E731
    if zr(crops) > zr(cur_crops):
        held.add("has_deeper_roots")
    if any(lib[c].get("ky_assumed") for c in crops):
        held.add("has_assumed_ky")
    if any(lib[c].get("paddy") for c in crops):
        held.add("has_rice")
    for key, cond in (("harvest", "harvest_better"), ("water", "water_better"), ("cover", "cover_better"),
                      ("soil_kept", "soil_better")):
        if round(plan["score"][key]) > round(current["score"][key]):
            held.add(cond)
    u = plan.get("score_dhm_rain")
    if u and round(u["harvest"]) != round(plan["score"]["harvest"]):
        held.add("rain_changes_harvest")
    if ctx.get("rain_corrected"):
        held.add("rain_corrected")
    if plan.get("needs_water_window"):
        held.add("needs_water_window")
    if plan.get("stability") is not None and round(plan["stability"]) > round(current.get("stability", 101)):
        held.add("bad_years_better")
    if plan["id"] == "cover_gap" and "has_legume" not in held and ctx.get("legume_option"):
        held.add("legume_option")
    # owner's answer 4 to REVIEW_2 (2026-11-13): the harvest gain as a range over FAO's root-depth ranges
    lo, hi = gain_bounds(plan)
    if plan["id"] != "current" and lo is not None:
        held.add("has_gain_range")
        if lo >= 1 and hi > lo:
            held.add("harvest_gain_range")
        elif lo >= 1:
            held.add("harvest_gain_single")
        elif hi >= 1:
            held.add("harvest_gain_maybe")
    elif "harvest_better" in held:
        held.add("harvest_gain_single")
    if plan.get("cover_days") is not None and current.get("cover_days") is not None and plan["cover_days"] > current["cover_days"]:
        held.add("cover_days_more")
    if ctx.get("rain_reads_high"):
        held.add("rain_reads_high")                           # owner's answer 8
    if ctx.get("soil_distance_m"):
        held.add("soil_cell_far")                             # owner's answer 10
    if ctx.get("winter_crop_unconfirmed"):
        held.add("winter_crop_unconfirmed")                   # owner's answer 6: the farmer has not confirmed the winter crop
    if ctx.get("profile"):
        held.add(f"profile_{ctx['profile']}")                 # owner's item 3: the field's country profile (NP, default)
    return held


def plan_name(role, crops, lib, names, no_legume_name):
    """The plan's name (rules.yaml plans.plan_names); a third plan with no legume keeps decision 5's name
    (plans.third_plan_name_no_legume), since 'Feed your soil' names a pulse crop."""
    if role == "safest" and not any(lib[c].get("legume") for c in crops):
        return no_legume_name
    return names[role]


def gain_bounds(plan):
    """(low, high) rounded harvest gain over the current plan from the plan's gain_range, or (None, None)."""
    gr = plan.get("gain_range")
    if not gr:
        return None, None
    return int(round(gr["low"])), int(round(gr["high"]))


def values(plan, current, ctx, lib, names):
    """The placeholders' values (fill_registry.json 'placeholders'); names = screens.json 'shared'."""
    crops = [c["crop"] for c in plan["crops"]]
    cur_crops = [c["crop"] for c in current["crops"]]
    crop_name = lambda c: names["crop_names"][c]                                     # noqa: E731
    years = ctx["replay"][plan["id"]]
    v = {"bare_days": ctx["diary"]["bare_days"], "harvest": int(round(plan["score"]["harvest"])),
         "harvest_gain": int(round(plan["score"]["harvest"]) - round(current["score"]["harvest"])),
         "year_first": years[0]["year"], "year_last": years[-1]["year"], "year_count": len(years),
         "drought_years": sum(1 for y in years if y["event"] == "drought"),
         "sources": [{"source_name": s["name"], "source_kind": names["source_kinds"][s["type"]],
                      "source_resolution": s["resolution"], "source_years": s["years"]} for s in ctx["plan_sources"]]}
    new = [c for c in crops if c not in cur_crops]
    if new:
        v["new_crop"] = crop_name(new[0])
    leg = [c for c in crops if lib[c].get("legume")]
    if leg:
        v["legume_crop"] = crop_name(leg[0])
    v["deep_root_crop"] = crop_name(max(crops, key=lambda c: lib[c].get("zr_m") or 0))
    assumed = [c for c in dict.fromkeys(crops) if lib[c].get("ky_assumed")]
    if assumed:
        join = names["join"]["and"]
        v["assumed_crop"] = {lang: f" {join[lang]} ".join(crop_name(c)[lang] for c in assumed) for lang in ("en", "ne")}
    if ctx["diary"].get("shift_days") is not None:
        v["shift_days_abs"] = abs(int(round(ctx["diary"]["shift_days"])))
    u = plan.get("score_dhm_rain")
    if u:
        v["harvest_dhm"] = int(round(u["harvest"]))
    if ctx.get("rain_fix_year"):
        v["rain_fix_year"] = ctx["rain_fix_year"]
    water = [c for c, w in zip(crops, plan.get("windows", [None] * len(crops))) if irrigated_window(w)]
    if water:
        v["water_crop"] = crop_name(water[0])
    if ctx.get("legume_option"):
        v["option_legume"] = crop_name(ctx["legume_option"])
    lo, hi = gain_bounds(plan)
    if lo is not None:
        v["gain_low"], v["gain_high"] = lo, hi
        if lo == hi:
            v["harvest_gain"] = lo
    if plan.get("cover_days") is not None and current.get("cover_days") is not None:
        v["cover_days_gain"] = int(plan["cover_days"] - current["cover_days"])
    if ctx.get("soil_distance_m"):
        v["soil_distance"] = int(ctx["soil_distance_m"])
    return v


def straw_month(plan, diary):
    """The month for the straw tip, or None (rules.yaml tips.straw_months; owner's answer 5 to REVIEW_2, 2026-11-13):
    the satellite's bare months (diary.months[].cover == 'bare'), the first of them for the current plan; for a
    suggested plan the first of them in which the plan's own calendar is bare too."""
    sat = [i + 1 for i, m in enumerate(diary.get("months", [])) if m.get("cover") == "bare"]
    if plan["id"] != "current":
        own = set(bare_months(plan["crops"]))
        sat = [m for m in sat if m in own]
    return sat[0] if sat else None


def tips(plan, ctx, names, templates):
    """[(en, ne)]: per crop the month it is most often thirsty in the rain-fed replay, if that is often enough
    (rules.yaml tips: a floor of dry days a year, and no rice tip for now), then the straw tip for a month the
    satellite shows bare. The slope tip waits for build step 8."""
    by_id = {t["id"]: t for t in templates}
    rule = ctx.get("tips") or {}
    floor, skip = rule.get("thirsty_min_dry_days_per_year", 0), set(rule.get("thirsty_skip_crops", []))
    out = []
    for c, t in plan.get("thirsty", {}).items():
        if c in skip or t.get("dry_days_per_year", floor) < floor:
            continue
        vals = {"crop": names["crop_names"][c], "month": names["months"][MONTHS[t["month"] - 1]]}
        out.append((capitalize_sentences(fill(by_id["tip_thirsty"], vals, "en")), fill(by_id["tip_thirsty"], vals, "ne")))
    bare = [straw_month(plan, ctx["diary"])]
    if bare[0]:
        vals = {"month": names["months"][MONTHS[bare[0] - 1]]}
        out.append((capitalize_sentences(fill(by_id["tip_straw"], vals, "en")), fill(by_id["tip_straw"], vals, "ne")))
    return out


def render(plan, current, ctx, lib, words):
    """{tabs, tabs_ne, tips, tips_ne, conditions} for one plan. words = {'tabs': tabs.json, 'shared': screens 'shared'}."""
    held = conditions(plan, current, ctx, lib)
    vals = values(plan, current, ctx, lib, words["shared"])
    T = words["tabs"]["tabs"]
    tabs = {k: capitalize_sentences(render_tab(T[k], held, vals, "en")) for k in TAB_KEYS}
    tabs_ne = {k: render_tab(T[k], held, vals, "ne") for k in TAB_KEYS}
    tp = tips(plan, ctx, words["shared"], words["tabs"]["tips"])
    return {"tabs": tabs, "tabs_ne": tabs_ne, "tips": [e for e, _ in tp], "tips_ne": [n for _, n in tp],
            "conditions": sorted(held)}
