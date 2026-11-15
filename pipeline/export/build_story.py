"""Build site/data/story.json: the "How we know" page as a visual data story (2026-11-14).

    .venv/bin/python -m pipeline.export.build_story [--field demo] [--out site/data/story.json]
    .venv/bin/python -m pipeline.export.build_story --markdown      # the report card, satellites and resources as tables

Reads only finished outputs (data/clean/<field>/, data/checks/<field>/, data/cards/<field>/, site/data/fields/<field>.json,
site/data/area/<field>.json, site/data/words.json, config/). It reruns nothing, so it can be run again after the last
export and gives the page the final numbers. Every chart names its sources and the files it was read from (`inputs`).
Every number in a caption or a report-card line is computed here from those files; the words around it follow the data
(for example "stayed level" only when the step is small).

Licences: DHM's 2025 bulletin values are (c) DHM and stay under data/: only ratios to them are written. Station values
from Kathmandu Airport (GHCN-Daily, GSOD-derived) are not written at all. Every Nepali text is an SI draft: the file says
"needs native-speaker review".
"""
import argparse
import calendar
import json
import math
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).with_name("story_schema.json")
NE_REVIEW = "needs native-speaker review"
SAME_LEVEL = (0.9, 1.1)            # a step inside this ratio is "stayed level" (plain-words threshold, METHOD_NOTES 98)

_DEVANAGARI = str.maketrans("0123456789", "०१२३४५६७८९")
_NE_MONTHS = {1: "जनवरी", 2: "फेब्रुअरी", 3: "मार्च", 4: "अप्रिल", 5: "मे", 6: "जुन", 7: "जुलाई", 8: "अगस्ट",
              9: "सेप्टेम्बर", 10: "अक्टोबर", 11: "नोभेम्बर", 12: "डिसेम्बर"}


# --- small helpers ---------------------------------------------------------------------------------------------------

def ne_digits(s):
    """ASCII digits to Devanagari digits, except inside names that start with a letter (FAO-56, L4, SSP2-4.5)."""
    return re.sub(r"[A-Za-z][A-Za-z0-9.\-]*|\d",
                  lambda m: m.group(0) if m.group(0)[0].isalpha() else m.group(0).translate(_DEVANAGARI), str(s))


def T(en, ne):
    """A text in English and Nepali (Nepali digits are Devanagari)."""
    return {"en": en, "ne": ne_digits(ne)}


def sentences(text, lang):
    """Split a text into sentences (English on . ! ? followed by a space or the end; Nepali on । ? !)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip()) if lang == "en" else re.split(r"[।?!]", text)
    out = []
    for p in parts:
        p = p.strip().rstrip(".!?").strip()
        if p:
            out.append(p)
    return out


def long_sentences(text, lang, limit):
    """Sentences with more than `limit` words (the site's plain-words rule)."""
    return [s for s in sentences(text, lang) if len(s.split()) > limit]


def fmt(x, nd=0):
    """1842.3 -> '1,842'; 0.876 with nd=2 -> '0.88'."""
    return f"{x:,.{nd}f}"


def join_en(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def S(name, role, points):
    return {"name": name, "role": role, "points": points}


def axis_x(label, kind, categories=None):
    out = {"label": label, "type": kind}
    if categories is not None:
        out["categories"] = categories
    return out


def axis_y(label, unit, ref=None, ref_label=None, kind=None, categories=None):
    out = {"label": label, "unit": unit}
    if kind:
        out["type"] = kind
    if categories is not None:
        out["categories"] = categories
    if ref is not None:
        out["ref"] = ref
        out["ref_label"] = ref_label
    return out


def cat(cid, en, ne):
    return {"id": cid, "en": en, "ne": ne_digits(ne)}


def chart(cid, section, title, caption, sources, kind, x=None, y=None, series=(), bands=(), markers=(), rows=(),
          status="ready", **extra):
    out = {"id": cid, "section": section, "status": status, "title": title, "caption": caption,
           "sources": list(sources), "kind": kind, "x": x, "y": y, "series": list(series), "bands": list(bands),
           "markers": list(markers), "rows": list(rows)}
    out.update(extra)
    return out


def _round(x, nd):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), nd)


# --- yearly and monthly summaries (pure) -----------------------------------------------------------------------------

def yearly_gauge_weight(gauge):
    """IMERG monthly gauge weight at the field's cell -> {year: {mean, low, high, months}}."""
    df = gauge.dropna(subset=["imerg_gauge_weight_pct"]).copy()
    df["year"] = df["month"].str[:4].astype(int)
    out = {}
    for year, g in df.groupby("year"):
        v = g["imerg_gauge_weight_pct"]
        out[int(year)] = {"mean": round(float(v.mean()), 1), "low": float(v.min()), "high": float(v.max()),
                          "months": int(len(v))}
    return out


def yearly_station_counts(gauge):
    """GPCC rain gauges in the field's 1-degree box, mean per month -> {year: count}; years without counts left out."""
    df = gauge.copy()
    df["year"] = df["month"].str[:4].astype(int)
    out = {}
    for year, g in df.groupby("year"):
        v = g["gpcc_stations"].dropna()
        if len(v):
            out[int(year)] = round(float(v.mean()), 1)
    return out


def yearly_gpcc_totals(gauge):
    """GPCC's own box rain, summed over years with all 12 months -> {year: mm}."""
    df = gauge.copy()
    df["year"] = df["month"].str[:4].astype(int)
    out = {}
    for year, g in df.groupby("year"):
        v = g["gpcc_rain_mm"].dropna()
        if len(v) == 12:
            out[int(year)] = float(v.sum())
    return out


def break_year(weights, below_pct):
    """The first year whose mean gauge weight falls below `below_pct`."""
    for year in sorted(weights):
        if weights[year]["mean"] < below_pct:
            return year
    return None


def yearly_totals(dates, values):
    """Daily values summed by calendar year, complete years only -> {year: total}."""
    s = pd.Series(list(values), index=pd.DatetimeIndex(dates)).dropna()
    out = {}
    for year, g in s.groupby(s.index.year):
        if len(g) == (366 if calendar.isleap(int(year)) else 365):
            out[int(year)] = float(g.sum())
    return out


def mean_of(d, years):
    v = [d[y] for y in years if y in d]
    return float(np.mean(v)) if v else None


def monthly_mean_ndvi(greenness, first_year, last_year):
    """HLS observations that passed the clear-sky rule, averaged by month -> [["YYYY-MM-15", ndvi], ...]."""
    df = greenness[greenness["source"].str.startswith("hls") & greenness["ndvi"].notna()].copy()
    df = df[(df["date"].dt.year >= first_year) & (df["date"].dt.year <= last_year)]
    out = []
    for (y, m), g in df.groupby([df["date"].dt.year, df["date"].dt.month]):
        out.append([f"{int(y):04d}-{int(m):02d}-15", round(float(g["ndvi"].mean()), 3)])
    return out


def sen_line(t, y, slope):
    """Intercept of a line with a given (Sen) slope through the median residual: (intercept, slope)."""
    t = np.asarray(t, float)
    y = np.asarray(y, float)
    return float(np.median(y - slope * t)), float(slope)


def decimal_year(ts):
    ts = pd.Timestamp(ts)
    days = 366 if ts.is_leap_year else 365
    return ts.year + (ts.dayofyear - 0.5) / days


# --- events: the model's year against the written record (pure) ------------------------------------------------------

def match_events(replay, known):
    """Each documented flood or drought of a replay year against the model's one event for that year.

    A record is 'found' when the model's event is the same kind; 'quiet' when the model does not show it and the record
    lies outside the valley (kathmandu_valley 'no' or 'indirect'), which is right; otherwise 'missed'. Frost is never a
    yearly event (CLAUDE.md), so frost records are left out. A negative control (a normal or wet monsoon) passes unless
    the model calls that year's monsoon dry (a drought with no season, which is both, or the monsoon's).
    """
    by_year = defaultdict(list)
    for e in known.get("events", []):
        if e["category"] in ("flood", "drought"):
            for y in e["years"]:
                by_year[int(y)].append(e)
    rows, flagged = [], {}
    valley = {"flood": [0, 0], "drought": [0, 0]}
    unrecorded = {"flood": [], "drought": []}
    for r in replay:
        year, model = int(r["year"]), r["event"]
        flagged[year] = (model, r.get("event_season"))
        recs = []
        for e in by_year.get(year, []):
            where = e.get("kathmandu_valley")
            if model == e["category"]:
                result = "found"
            elif where in ("no", "indirect"):
                result = "quiet"
            else:
                result = "missed"
            if where == "yes":
                valley[e["category"]][1] += 1
                valley[e["category"]][0] += result == "found"
            recs.append({"id": e["id"], "category": e["category"], "valley": where, "months": e.get("months", ""),
                         "result": result})
        if model in ("flood", "drought") and not any(e["category"] == model for e in by_year.get(year, [])):
            unrecorded[model].append(year)
        if not recs:
            result = "no record" if model != "none" else "none"
        elif any(x["result"] == "found" for x in recs):
            result = "found"
        elif any(x["result"] == "missed" for x in recs):
            result = "missed"
        else:
            result = "quiet"
        row = {"year": year, "model": model, "records": recs, "result": result}
        if r.get("event_season"):
            row["model_season"] = r["event_season"]
        if isinstance(r.get("uncorrected_rain"), dict):
            row["model_uncorrected_rain"] = r["uncorrected_rain"].get("event")
        rows.append(row)
    controls = []
    for c in known.get("negative_controls", []):
        for y in c["years"]:
            if int(y) in flagged:
                model, season = flagged[int(y)]
                passes = not (model == "drought" and season in (None, "monsoon"))
                controls.append({"id": c["id"], "year": int(y), "passes": passes})
    summary = {"valley_floods": valley["flood"], "valley_droughts": valley["drought"],
               "unrecorded_flood_years": unrecorded["flood"], "unrecorded_drought_years": unrecorded["drought"],
               "negative_controls": controls}
    return rows, summary


# --- the charts ------------------------------------------------------------------------------------------------------

SRC_IMERG_M = ("NASA GPM IMERG V07 Final, monthly (GPM_3IMERGM): gauge weight in the field's 0.1° cell (about 10 km), "
               "2001 to September 2025; satellites with rain gauges")
SRC_GPCC = "GPCC Full Data Monthly Product V2022 (DWD), the 1.0° box holding the field (about 100 km), 2001-2020: rain gauges"
SRC_IMERG_D = ("NASA GPM IMERG V07 daily: Final (GPM_3IMERGDF) to September 2025, Late (GPM_3IMERGDL) for October-December "
               "2025; the field's 0.1° cell, UTC days, 2001-2025; satellites")
SRC_CHIRPS = "CHIRPS v3.0 daily, rnl (Climate Hazards Center, UC Santa Barbara), the field's 0.05° cell, 2001-2025; satellites and gauges"
SRC_DHM_NORMAL = ("DHM (Government of Nepal) 1991-2020 normal, Bhaktapur station (1,315 m, about 2.3 km from the field); "
                  "a rain gauge")
SRC_TWIN_RAIN = ("The model's rain: GPM IMERG with each month from January 2017 scaled back to its own 2001-2016 level "
                 "(config/rules.yaml gpm_series.correction); model-based")
SRC_HLS = ("NASA HLS-VI v2.0 greenness (NDVI): HLSL30_VI (Landsat 8 and 9) and HLSS30_VI (Sentinel-2), 30 m, the field's "
           "4 pixels, clouds masked with Fmask, 2014-2025; satellites")
SRC_TWIN = "Khet Sathi field twin (FAO-56 soil water, FAO-33 harvest), 2002-2025; model-based"


def chart_gauge_weight(gauge):
    w = yearly_gauge_weight(gauge)
    by = break_year(w, 90)
    before = round(mean_of({y: v["mean"] for y, v in w.items()}, [y for y in w if y < by]))
    after = round(mean_of({y: v["mean"] for y, v in w.items()}, [y for y in w if y >= by]))
    cap = T(f"Before {by}, gauges set about {before}% of it. After, only about {after}%.",
            f"{by} अघि यसको करिब {before}% मापकले मिलाउँथे। त्यसपछि करिब {after}% मात्र।")
    return chart(
        "gauge_weight", "rain",
        T("How much rain gauges shaped NASA's rain map", "नासाको वर्षा नक्सामा वर्षा मापकको भूमिका"), cap,
        [SRC_IMERG_M], "line",
        x=axis_x(T("Year", "वर्ष"), "year"),
        y=axis_y(T("Share set by rain gauges", "मापकले मिलाएको भाग"), "%"),
        series=[S(T("Field's cell, mean of the year", "खेत पर्ने ग्रिड कोठा, वर्षको औसत"), "main",
                  [[y, v["mean"]] for y, v in sorted(w.items())]),
                S(T("Lowest to highest month", "सबैभन्दा कम देखि बढी महिना"), "range",
                  [[y, [v["low"], v["high"]]] for y, v in sorted(w.items())])],
        markers=[{"x": by, "label": T("Gauge reports stop", "मापकका खबर रोकिए")}],
        rows=[{"year": y, **v} for y, v in sorted(w.items())],
        note=T("2025 counts January to September only.", "२०२५ मा जनवरी देखि सेप्टेम्बर मात्र।")), by


def chart_gauge_stations(gauge, by):
    c = yearly_station_counts(gauge)
    before = round(mean_of(c, [y for y in c if y < by]))
    after = round(mean_of(c, [y for y in c if y >= by]))
    cap = T(f"About {before} gauges reported each month. From {by}, about {after}.",
            f"हरेक महिना करिब {before} मापकले खबर पठाए। {by} देखि करिब {after} मात्र।")
    return chart(
        "gauge_stations", "rain", T("Rain gauges reporting near the field", "खेत नजिक खबर पठाउने वर्षा मापक"), cap,
        [SRC_GPCC], "bars",
        x=axis_x(T("Year", "वर्ष"), "year"),
        y=axis_y(T("Gauges reporting, each month", "हरेक महिना खबर पठाउने मापक"), "gauges"),
        series=[S(T("Gauges in the 1° box (about 100 km)", "१° कोठामा (करिब १०० किमी) मापक"), "main",
                  [[y, v] for y, v in sorted(c.items())])],
        markers=[{"x": by, "label": T("Gauge reports stop", "मापकका खबर रोकिए")}],
        note=T("This gauge archive ends in 2020.", "मापकको यो अभिलेख २०२० मा सकिन्छ।"))


def bhaktapur_normal(normals):
    n = normals[(normals["station"] == "Bhaktapur") & (normals["variable"] == "precip_mm")]
    n = n[pd.to_numeric(n["month"], errors="coerce").between(1, 12)]
    if len(n) != 12:
        raise ValueError(f"Bhaktapur's rain normal needs 12 months, found {len(n)}")
    return float(n["value"].sum())


def chart_rain_jump(gpm, chirps, gauge, normals, by):
    g = yearly_totals(gpm["date"], gpm["rain_mm"])
    c = yearly_totals(chirps["date"], chirps["rain_mm"])
    gp = yearly_gpcc_totals(gauge)
    normal = bhaktapur_normal(normals)
    years = sorted(g)
    step_gpm = mean_of(g, [y for y in g if y >= by]) / mean_of(g, [y for y in g if y < by])
    step_chirps = mean_of(c, [y for y in c if y >= by]) / mean_of(c, [y for y in c if y < by])
    jump = round((step_gpm - 1) * 100)
    level = SAME_LEVEL[0] <= step_chirps <= SAME_LEVEL[1]
    cap_en = f"From {by}, NASA's rain map jumped {jump}%."
    cap_ne = f"{by} देखि नासाको वर्षा नक्सा {jump}% ले उफ्रियो।"
    if level:
        cap_en += " CHIRPS stayed level."
        cap_ne += " चिर्प्स उस्तै रह्यो।"
    else:
        cap_en += f" CHIRPS moved {round((step_chirps - 1) * 100)}%."
        cap_ne += f" चिर्प्स {round((step_chirps - 1) * 100)}% ले फेरियो।"
    return chart(
        "rain_jump", "rain", T("Yearly rain at the field: four records", "खेतको वार्षिक वर्षा: चार अभिलेख"),
        T(cap_en, cap_ne), [SRC_IMERG_D, SRC_CHIRPS, SRC_GPCC, SRC_DHM_NORMAL], "line",
        x=axis_x(T("Year", "वर्ष"), "year"),
        y=axis_y(T("Rain in a year", "वर्षभरिको वर्षा"), "mm"),
        series=[S(T("NASA rain map (IMERG), as published", "नासाको वर्षा नक्सा (IMERG), जस्ताको तस्तै"), "main",
                  [[y, round(g[y])] for y in years]),
                S(T("CHIRPS (satellites and gauges)", "चिर्प्स (भू-उपग्रह र मापक)"), "compare",
                  [[y, round(c[y])] for y in sorted(c)]),
                S(T("Rain gauges in the 1° box (GPCC)", "१° कोठाका मापक (GPCC)"), "compare",
                  [[y, round(gp[y])] for y in sorted(gp)]),
                S(T("Bhaktapur gauge, usual year (DHM)", "भक्तपुर मापक, सामान्य वर्ष (DHM)"), "compare",
                  [[years[0], round(normal)], [years[-1], round(normal)]])],
        markers=[{"x": by, "label": T("Gauge reports stop", "मापकका खबर रोकिए")}],
        rows=[{"step_after_break": {"gpm": round(step_gpm, 2), "chirps": round(step_chirps, 2)},
               "means_mm": {"gpm_before": round(mean_of(g, [y for y in g if y < by])),
                            "gpm_after": round(mean_of(g, [y for y in g if y >= by])),
                            "chirps_before": round(mean_of(c, [y for y in c if y < by])),
                            "chirps_after": round(mean_of(c, [y for y in c if y >= by]))}}],
        note=T("The gauge box is wider and includes hills.", "मापकको कोठा फराकिलो छ, पहाड पनि पर्छ।")), normal


def chart_rain_fixed(weather, normal, by):
    fixed = yearly_totals(weather["date"], weather["rain_mm"])
    raw = yearly_totals(weather["date"], weather["rain_uncorrected_mm"])
    years = sorted(fixed)
    step = mean_of(fixed, [y for y in years if y >= by]) / mean_of(fixed, [y for y in years if y < by])
    ratio = mean_of(fixed, years) / normal
    en = [f"We scaled each month from {by} back down."]
    ne = [f"हामीले {by} देखि हरेक महिना घटायौं"]
    if SAME_LEVEL[0] <= step <= SAME_LEVEL[1]:
        en.append("Now it matches its own earlier years.")
        ne.append("अब यो आफ्नै पहिलेका वर्षसँग मिल्छ")
    if ratio > SAME_LEVEL[1]:
        en.append(f"Still {fmt(ratio, 2)} times the town gauge's usual rain.")
        ne.append(f"तर सहरको मापकको सामान्यको {fmt(ratio, 2)} गुणा छ")
    return chart(
        "rain_fixed", "rain", T(f"The rain our model uses, fixed from {by}", f"हाम्रो मोडेलको वर्षा, {by} देखि सच्याइएको"),
        T(" ".join(en), "। ".join(ne) + "।"), [SRC_TWIN_RAIN, SRC_IMERG_D, SRC_DHM_NORMAL], "line",
        x=axis_x(T("Year", "वर्ष"), "year"),
        y=axis_y(T("Rain in a year", "वर्षभरिको वर्षा"), "mm"),
        series=[S(T("Rain the model uses (fixed)", "मोडेलले प्रयोग गर्ने वर्षा (सच्याइएको)"), "main",
                  [[y, round(fixed[y])] for y in years]),
                S(T("As published", "जस्ताको तस्तै"), "compare", [[y, round(raw[y])] for y in sorted(raw)]),
                S(T("Bhaktapur gauge, usual year (DHM)", "भक्तपुर मापक, सामान्य वर्ष (DHM)"), "compare",
                  [[years[0], round(normal)], [years[-1], round(normal)]])],
        markers=[{"x": by, "label": T("Our fix starts", "हाम्रो सुधार सुरु")}],
        rows=[{"mean_mm": {"fixed": round(mean_of(fixed, years)), "as_published": round(mean_of(raw, years)),
                           "bhaktapur_normal": round(normal)},
               "times_normal": round(ratio, 2), "step_after_break": round(step, 2)}]), ratio


def hls_seasons(diary_seasons, first_year, last_year):
    """The chosen method's seasons in HLS years: [{start, peak, end, slot, peak_ndvi}]."""
    out = []
    for year, seasons in sorted(diary_seasons["chosen"]["seasons_by_year"].items()):
        if not first_year <= int(year) <= last_year:
            continue
        for s in seasons:
            if s.get("source") == "modis":
                continue
            slot = "winter" if int(s["peak"][5:7]) <= 5 else "monsoon"
            out.append({"year": int(year), "start": s["start"], "peak": s["peak"], "end": s["end"], "slot": slot,
                        "peak_ndvi": s["peak_ndvi"]})
    return out


def chart_seasons(greenness, diary_seasons, first_year=2014, last_year=2025):
    seasons = hls_seasons(diary_seasons, first_year, last_year)
    per_year = defaultdict(int)
    for s in seasons:
        per_year[s["year"]] += 1
    n = last_year - first_year + 1
    two = sum(1 for y in range(first_year, last_year + 1) if per_year.get(y) == 2)
    if two == n:
        c1 = (f"Two green seasons in each of {n} years.", f"{n} वटै वर्षमा, हरेक वर्ष दुई हरिया याम।")
    else:
        c1 = (f"{two} of {n} years had two green seasons.", f"{n} मध्ये {two} वर्ष दुई हरिया याम।")
    label = {"monsoon": T("Rainy-season crop", "बर्खे बाली"), "winter": T("Winter crop", "हिउँदे बाली")}
    return chart(
        "seasons_from_space", "seasons",
        T(f"Green seasons seen from space, {first_year}-{last_year}",
          f"अन्तरिक्षबाट देखिएका हरिया याम, {first_year}–{last_year}"),
        T(c1[0] + " Greenness shows a crop, not which crop.", c1[1] + " हरियालीले बाली देखाउँछ, कुन बाली होइन।"),
        [SRC_HLS, "Seasons: the threshold method (config/rules.yaml season_detection), chosen over two others"], "line",
        x=axis_x(T("Date", "मिति"), "date"),
        y=axis_y(T("Greenness (NDVI)", "हरियाली (NDVI)"), "NDVI"),
        series=[S(T("Field greenness, monthly mean (30 m)", "खेतको हरियाली, मासिक औसत (३० मि)"), "main",
                  monthly_mean_ndvi(greenness, first_year, last_year))],
        bands=[{"from": s["start"], "to": s["end"], "label": label[s["slot"]]} for s in seasons],
        rows=seasons), seasons


def chart_crop_months(fj, calendars, diary_seasons, bs_names):
    """Fix A4 (owner, 2026-11-15; rules.yaml farmer_answers.actions_calendar_months): each crop's harvest month in our model
    (the plan's last day) against the FAO crop calendar's (the month the farmer cards now show), one row per crop and
    sowing month among the plans and the farmer's options, and the field's own seasons from space (HLS, median end).
    bs_names: words.json shared.bs_months ({key: {en, ne}}). Pure."""
    from statistics import median
    from pipeline.export.build_simple import bs_key, calendar_end
    name = lambda k: bs_names[k]                                       # noqa: E731
    crop_ne = {"rice": "धान", "wheat": "गहुँ", "potato": "आलु", "lentil": "मसुरो", "maize": "मकै", "mustard": "तोरी",
               "buckwheat": "फापर", "finger_millet": "कोदो"}
    seen, rows = set(), []
    plans = list(fj.get("plans") or []) + list((fj.get("current_options") or {}).get("options") or [])
    for p in plans:
        for c in p["crops"]:
            key = (c["crop"], bs_key(c["start"]))
            if key in seen:
                continue
            seen.add(key)
            day = calendar_end(c["crop"], c["start"], calendars)
            model, cal = bs_key(c["end"]), bs_key(day) if day else None
            sown, m, k = name(key[1]), name(model), name(cal) if cal else None
            verb_en, verb_ne = ("planted", "रोपेको") if c["crop"] == "rice" else ("sown", "छरेको")
            head = T(f"{c['crop'].replace('_', ' ').capitalize()}, {verb_en} in {sown['en']}",
                     f"{sown['ne']}मा {verb_ne} {crop_ne.get(c['crop'], c['crop'])}")
            if cal is None:
                text = T(f"Our model ends it in {m['en']}. The calendar has no window for this sowing.",
                         f"हाम्रो मोडेलमा {m['ne']}मा सकिन्छ। पात्रोमा यो छराइको समय छैन।")
            elif cal == model:
                text = T(f"Harvested in {m['en']}: our model and FAO's calendar agree.",
                         f"{m['ne']}मा काटिन्छ: हाम्रो मोडेल र FAO को पात्रो मिल्छन्।")
            else:
                text = T(f"Our model ends it in {m['en']}. FAO's calendar says {k['en']}. The cards show {k['en']}.",
                         f"हाम्रो मोडेलमा {m['ne']}मा सकिन्छ। FAO को पात्रोमा {k['ne']}। कार्डमा {k['ne']} देखाइन्छ।")
            rows.append({"crop": c["crop"], "sown": key[1], "model": model, "calendar": cal, "head": head, "text": text})
    win = [s for s in hls_seasons(diary_seasons, 2014, 2025) if s["slot"] == "winter"]   # chart_seasons' HLS years
    if win:
        doy = lambda d: date.fromisoformat(d).timetuple().tm_yday         # noqa: E731
        end = date(2001, 1, 1) + timedelta(days=int(median(doy(s["end"]) for s in win)) - 1)
        e = name(bs_key(end.strftime("%m-%d")))
        rows.append({"from_space": True, "winter_seasons": len(win), "winter_end": end.strftime("%m-%d"),
                     "head": T("This field from space", "अन्तरिक्षबाट यो खेत"),
                     "text": T(f"Its winter crop usually ends in {e['en']} ({len(win)} winters).",
                               f"यसको हिउँदे बाली प्रायः {e['ne']}मा सकिन्छ ({len(win)} हिउँद)।")})
    return chart(
        "crop_months", "seasons", T("Sowing and harvest months", "छर्ने र काट्ने महिना"),
        T("The cards show FAO's calendar months. Our model's wheat ends too early. The model is unchanged for now.",
          "कार्डले FAO को पात्रोका महिना देखाउँछन्। हाम्रो मोडेलको गहुँ चाँडै सकिन्छ। मोडेल अहिलेलाई उस्तै छ।"),
        ["FAO Crop Calendar, Nepal, B. Hill Agro-ecological Zone (crops.json calendar windows)", SRC_TWIN, SRC_HLS,
         "config/rules.yaml farmer_answers.actions_calendar_months"], "table", rows=rows)


def chart_offline():
    """Part 2 (owner, 2026-11-15): what works with no internet (site/sw.js, scripts/build_offline.py). Pure."""
    rows = [{"head": T("First time", "पहिलो पटक"), "text": T("Open it once with internet.", "एक पटक इन्टरनेटसहित खोल्नुहोस्।")},
            {"head": T("After that", "त्यसपछि"), "text": T("It opens with no internet, on that phone.", "त्यही फोनमा इन्टरनेट बिना खुल्छ।")},
            {"head": T("New data", "नयाँ तथ्याङ्क"), "text": T("It comes when you are online again.", "फेरि इन्टरनेट हुँदा आउँछ।")},
            {"head": T("Live soil readings", "प्रत्यक्ष माटो रिडिङ"),
             "text": T("These always need our laptop nearby.", "यसका लागि सधैं हाम्रो ल्यापटप नजिकै चाहिन्छ।")}]
    return chart("offline_use", "offline", T("What works with no internet", "इन्टरनेट बिना के चल्छ"),
                 T("The phone keeps a copy of your field.", "फोनले तपाईंको खेतको प्रति राख्छ।"),
                 ["site/sw.js (a service worker) and scripts/build_offline.py: the files a first visit saves"], "table", rows=rows)


def chart_cover_sure(months, month_words):
    low = min(months, key=lambda m: m["cover_sure"])
    name_ne = month_words[low["m"]]["ne"]
    name_en = month_words[low["m"]]["en"]
    cap = T(f"We are least sure about {name_en}. The two methods differ most then.",
            f"{name_ne} महिनाबारे हामी सबैभन्दा कम निश्चित छौं। त्यतिबेला दुई तरिका सबैभन्दा धेरै फरक पर्छन्।")
    return chart(
        "cover_sure", "seasons", T("How sure we are, month by month", "महिनैपिच्छे हामी कति निश्चित छौं"), cap,
        [SRC_HLS, "The threshold method against the SI season detective (a random forest), HLS years 2014-2025"],
        "bars",
        x=axis_x(T("Month", "महिना"), "month"),
        y=axis_y(T("Days the two methods agree", "दुई तरिका मिल्ने दिन"), "share (0-1)"),
        series=[S(T("Share of days that agree", "मिल्ने दिनको भाग"), "main",
                  [[m["m"], m["cover_sure"]] for m in months])],
        rows=[{"m": m["m"], "cover": m["cover"], "cover_sure": m["cover_sure"]} for m in months])


EVENT_CATS = [cat("none", "No event", "कुनै घटना छैन"), cat("drought", "Dry", "सुक्खा"), cat("flood", "Flood", "बाढी")]


def unconfirmed(card, kind):
    """The scorecard's false alarms for flood_years or drought_years (scripts/run_verification.py events): sentences
    for every page that shows them, so the events chart, the report card and the compliance table give one count."""
    c = (card or {}).get(f"{kind}_years") or {}
    if not c.get("flagged_seasons"):
        return [], []
    fa, fan = c["false_alarms"], c["flagged_seasons"]
    return [f"{fa} of {fan} flagged seasons were not confirmed."], [f"{fan} सङ्केतमध्ये {fa} पुष्टि भएनन्"]


def chart_events(replay, known, card=None):
    rows, summary = match_events(replay, known)
    kf, nf = summary["valley_floods"]
    kd, nd = summary["valley_droughts"]
    failed = sum(1 for c in summary["negative_controls"] if not c["passes"])
    en = [f"It found {kf} of {nf} valley floods.", f"It found {kd} of {nd} valley dry spells."]
    ne = [f"उपत्यकाका {nf} मध्ये {kf} बाढी भेट्टायो", f"उपत्यकाका {nd} मध्ये {kd} सुक्खा याम भेट्टायो"]
    if failed:
        en.append(f"It called {failed} normal or wet {'monsoon' if failed == 1 else 'monsoons'} dry.")
        ne.append(f"सामान्य वा बढी पानीका {failed} बर्खालाई सुक्खा भन्यो")
    en, ne = en + unconfirmed(card, "drought")[0], ne + unconfirmed(card, "drought")[1]
    records = sorted(((r["year"], rec["category"]) for r in rows for rec in r["records"]))
    return chart(
        "events", "checks", T("Floods and dry years: our model against records", "बाढी र सुक्खा वर्ष: मोडेल र अभिलेख"),
        T(" ".join(en), "। ".join(ne) + "।"),
        [SRC_TWIN + ": one weather event a year from the field's rain (GPM IMERG, fixed from 2017)",
         "Written records of floods and droughts: config/known_events.yaml (DHM, Ministry of Home Affairs, FAO/WFP, "
         "FAO GIEWS, Dahal et al. 2016 and others; each with its source)"], "timeline",
        x=axis_x(T("Year", "वर्ष"), "year"),
        y=axis_y(T("Event", "घटना"), "", kind="category", categories=EVENT_CATS),
        series=[S(T("Our model: one event a year", "हाम्रो मोडेल: वर्षमा एउटा घटना"), "main",
                  [[r["year"], r["model"]] for r in rows]),
                S(T("Written records", "लिखित अभिलेख"), "compare", [[y, c] for y, c in records])],
        rows=rows, summary=summary), summary


def _month_names(months):
    nums = [int(m[5:7]) for m in months]
    return join_en([calendar.month_name[n] for n in nums]), ", ".join(_NE_MONTHS[n] for n in nums)


def rain_is_tuned(field):
    """rules.yaml gpm_series.gauge_calibration: the field's central rain carries gauge factors fitted on DHM's 2023-2025 months."""
    from pipeline.fetch.rules import load_rules
    g = load_rules()["gpm_series"]["gauge_calibration"]
    return bool(g["apply"]) and field in g["fields"]


TUNED = ("Our rain was tuned on these gauges.", "हाम्रो वर्षा यिनै मापकमा मिलाइएको थियो")


def chart_dhm_2025(rain_vs_dhm, tuned=False):
    lab = rain_vs_dhm["labels"]
    data = rain_vs_dhm["against_three_gauges"]
    fin_en, fin_ne = _month_names(lab["imerg_final_months"])
    late_en, late_ne = _month_names(lab["imerg_late_months"])
    cats = [cat("imerg_final_months", fin_en, fin_ne), cat("imerg_late_months", late_en, late_ne)]
    names = {"gpm_as_published": T("NASA rain map, as published", "नासाको वर्षा नक्सा, जस्ताको तस्तै"),
             "twin_rain": T("Our model's rain (fixed)", "हाम्रो मोडेलको वर्षा (सच्याइएको)"),
             "chirps": T("CHIRPS", "चिर्प्स"),
             "power": T("NASA POWER (model)", "नासा पावर (मोडेल)")}
    series = [S(names[k], "main" if k == "twin_rain" else "compare",
                [[cid, data[cid][k]["ratio"]] for cid in ("imerg_final_months", "imerg_late_months")])
              for k in ("gpm_as_published", "twin_rain", "chirps", "power")]
    fin = {k: abs(data["imerg_final_months"][k]["ratio"] - 1) for k in names}
    en = ["1 means the same as Nepal's gauges."]
    ne = ["१ भनेको नेपालका मापकजत्तिकै"]
    if min(fin, key=fin.get) == "twin_rain":
        en.append(f"Ours is closest in {fin_en}.")
        ne.append(f"{fin_ne}मा हाम्रो सबैभन्दा नजिक")
    late_twin = data["imerg_late_months"]["twin_rain"]["ratio"]
    if late_twin > SAME_LEVEL[1]:
        en.append(f"{late_en}: still too wet.")
        ne.append(f"{late_ne}: अझै धेरै बढी वर्षा")
    if tuned:                                # in-sample: the gauge factors were fitted on these months (VALIDATION 3.9c)
        en.append(TUNED[0])
        ne.append(TUNED[1])
    rows = [{"months": cid, **{k: data[cid][k]["ratio"] for k in names}} for cid in ("imerg_final_months",
                                                                                    "imerg_late_months")]
    return chart(
        "dhm_2025", "checks", T("2025: our rain against Nepal's own gauges", "२०२५: हाम्रो वर्षा र नेपालकै मापक"),
        T(" ".join(en), "। ".join(ne) + "।"),
        ["DHM (Government of Nepal) monthly bulletins, 2025, preliminary: Bhaktapur, Changu Narayan and Kathmandu "
         "Airport rain gauges; months summed before dividing",
         SRC_IMERG_D, SRC_TWIN_RAIN, SRC_CHIRPS, "NASA POWER daily API, PRECTOTCORR, 0.5 x 0.625° (model-based)"],
        "bars",
        x=axis_x(T("Months of 2025", "२०२५ का महिना"), "category", cats),
        y=axis_y(T("Times the gauges' rain", "मापकको वर्षाको गुणा"), "x", ref=1,
                 ref_label=T("Same as the gauges", "मापकजत्तिकै")),
        series=series, rows=rows,
        note=T("Ratios only: DHM's own numbers stay with DHM.", "अनुपात मात्र: DHM का अङ्क DHM सँगै रहन्छन्।"))


def _corr(c):
    """(r, [low, high] or None) from a check file's correlation block (Pearson)."""
    if not c:
        return None, None
    ci = c.get("pearson_ci")
    return round(c["pearson"], 2), ([round(ci[0], 2), round(ci[1], 2)] if ci else None)


def chart_other_checks(smap, gldas, hls, fao, eco):
    sm = smap["rain"]["corrected"]
    gl = gldas["rain"]["corrected"]
    hv = hls["rain"]["corrected"]
    fa = fao["rain"]["corrected"]
    ev = eco["rain"]["corrected"] if eco else None     # None: no 70 m ECOSTRESS pixel centre lies in the field
    items = [
        ("smap", "Soil water vs NASA SMAP", "माटोको पानी र नासा SMAP", (round(sm["pearson"], 2), None), "4.2b"),
        ("gldas_soil", "Soil water vs NASA GLDAS", "माटोको पानी र नासा GLDAS", _corr(gl["soil"]), "4.2d"),
        ("gldas_et", "Water use vs NASA GLDAS", "पानीको खपत र नासा GLDAS", _corr(gl["et"]), "4.2d"),
        ("hls_potato", "Dry winters vs greenness (potato)", "सुक्खा हिउँद र हरियाली (आलु)",
         _corr(hv["winter"]["primary"]["correlation"]), "4.2"),
        ("hls_wheat", "Dry winters vs greenness (wheat option)", "सुक्खा हिउँद र हरियाली (गहुँ विकल्प)",
         _corr(hv["winter_rice_then_wheat"]["eta_over_etc"]["correlation"]), "4.2"),
        ("fao_wheat", "Wheat years vs Nepal's yields", "गहुँका वर्ष र नेपालको उब्जनी",
         _corr(fa["wheat"]["correlation"]), "4.3"),
        ("fao_potato", "Potato years vs Nepal's yields", "आलुका वर्ष र नेपालको उब्जनी",
         _corr(fa["potato"]["correlation"]), "4.3"),
        ("fao_rice", "Rice years vs Nepal's yields", "धानका वर्ष र नेपालको उब्जनी",
         _corr(fa["rice"]["correlation"]), "4.3"),
        ("hls_rice", "Rainy seasons vs greenness (rice)", "बर्खा र हरियाली (धान)",
         _corr(hv["monsoon"]["primary"]["correlation"]), "4.2"),
    ]
    statuses = {"fao_wheat": fa["wheat"]["status"], "fao_potato": fa["potato"]["status"],
                "fao_rice": fa["rice"]["status"], "hls_potato": hv["winter"]["primary"]["status"],
                "hls_wheat": hv["winter_rice_then_wheat"]["eta_over_etc"].get("status", ""),
                "hls_rice": hv["monsoon"]["primary"]["status"]}
    shown = [i for i in items if i[3][0] is not None]
    rows = [{"id": cid, "check": T(en, ne), "r": r, "low": ci[0] if ci else None, "high": ci[1] if ci else None,
             "status": statuses.get(cid, ""), "validation_row": vrow} for cid, en, ne, (r, ci), vrow in items]
    rows.append({"id": "ecostress", "check": T("Crop stress vs NASA ECOSTRESS", "बालीको तनाव र नासा ECOSTRESS"),
                 "r": None, "low": None, "high": None, "validation_row": "4.2e",
                 "status": "not possible: no 70 m pixel centre lies in the farm" if ev is None else
                 "not testable: too few clear overpasses a season" if not ev["holds_up_any_slot"] else "holds up"})
    untestable = [cid for cid, *_ in items if cid not in {s[0] for s in shown}]
    en = ["1 means they rise and fall together."]
    ne = ["१ भनेको सँगै बढ्छन् र घट्छन्"]
    crops = {"wheat": ("Wheat", "गहुँका"), "potato": ("Potato", "आलुका"), "rice": ("Rice", "धानका")}
    for row in rows:                        # a clear opposite movement gets words, not just a bar (TRACEABILITY gap)
        crop = row["id"][4:] if row["id"].startswith("fao_") else None
        if crop and row["high"] is not None and row["high"] < 0:
            en += [f"{crops[crop][0]} years move against Nepal's yields.", "So this check does not hold up."]
            ne += [f"{crops[crop][1]} वर्ष नेपालको उब्जनीको उल्टो चल्छन्", "त्यसैले यो जाँच मिलेन"]
    if "fao_rice" in untestable and "hls_rice" in untestable:
        en.append("Rice cannot be tested: it never runs short.")
        ne.append("धान जाँच्न मिल्दैन: यसमा पानी कहिल्यै कम हुँदैन")
    return chart(
        "other_checks", "checks", T("Does the model move with other data?", "मोडेल अरू तथ्याङ्कसँग मेल खान्छ?"),
        T(" ".join(en), "। ".join(ne) + "।"),
        ["NASA SMAP L4 root-zone soil moisture SPL4SMGP v008, 9 km, 2015-2025 (model-assisted)",
         "NASA GLDAS-2.1 Noah GLDAS_NOAH025_M, 0.25°, monthly, 2001-2025 (model-based)",
         SRC_HLS + ": each season's peak",
         "FAOSTAT QCL, Nepal's national yields of wheat, potato and rice, 2002-2024 (changes from year to year)",
         "NASA ECOSTRESS ESI (ECO_L4T_ESI V002/V003), 70 m, 2018-2025", SRC_TWIN],
        "bars",
        x=axis_x(T("Check", "जाँच"), "category", [cat(cid, en_, ne_) for cid, en_, ne_, *_ in shown]),
        y=axis_y(T("Agreement (correlation)", "मेल (सहसम्बन्ध)"), "r", ref=0,
                 ref_label=T("No link", "कुनै सम्बन्ध छैन")),
        series=[S(T("Agreement", "मेल"), "main", [[cid, v[0]] for cid, _, _, v, _ in shown]),
                S(T("Likely range (95%)", "सम्भावित दायरा (९५%)"), "range",
                  [[cid, v[1]] for cid, _, _, v, _ in shown if v[1]])],
        rows=rows), untestable


def chart_best_worst():
    return chart(
        "best_worst_years", "checks", T("Your best and worst years", "तपाईंका सबैभन्दा राम्रा र नराम्रा वर्ष"),
        T("Coming soon. We will ask the farmer.", "छिट्टै आउँदैछ। हामी किसानलाई सोध्नेछौं।"),
        ["The farmer's own memory of good and bad years (interview not done yet)"], "table", status="coming")


def chart_groundwater(grace, groundwater, region_km):
    df = grace.dropna(subset=["lwe_thickness_cm"]).sort_values("date")
    slope = float(groundwater["trend_cm_per_year"])
    t = [decimal_year(d) for d in df["date"]]
    a, b = sen_line(t, df["lwe_thickness_cm"], slope)
    ends = [df["date"].iloc[0], df["date"].iloc[-1]]
    trend = [[d.strftime("%Y-%m-%d"), round(a + b * decimal_year(d), 1)] for d in ends]
    s = fmt(abs(slope), 1)
    verb = {"falling": ("loses", "गुमाउँछ"), "rising": ("gains", "थप्छ")}.get(groundwater["direction"])
    if verb:
        c1 = (f"The region {verb[0]} about {s} cm a year.", f"यो क्षेत्रले वर्षमा करिब {s} सेमी पानी {verb[1]}।")
    else:
        c1 = ("The region's water stays about the same.", "यो क्षेत्रको पानी करिब उस्तै छ।")
    return chart(
        "groundwater", "groundwater",
        T("Water stored across the whole region (GRACE)", "पूरै क्षेत्रमा सञ्चित पानी (GRACE)"),
        T(c1[0] + " A huge region, not your own well.", c1[1] + " ठूलो क्षेत्र हो, तपाईंको आफ्नै इनार होइन।"),
        [f"NASA/JPL GRACE and GRACE-FO mascon CRI RL06.3 v04, about {region_km} km (regional), "
         f"{df['date'].iloc[0].year}-{df['date'].iloc[-1].year}; satellites",
         "Trend: seasonal Sen slope (diary.groundwater), drawn through the median residual"], "line",
        x=axis_x(T("Date", "मिति"), "date"),
        y=axis_y(T("Water stored, against the average", "औसतको तुलनामा सञ्चित पानी"), "cm"),
        series=[S(T("Each month (GRACE and GRACE-FO)", "हरेक महिना (GRACE र GRACE-FO)"), "main",
                  [[d.strftime("%Y-%m-%d"), round(float(v), 1)] for d, v in zip(df["date"], df["lwe_thickness_cm"])]),
                S(T(f"Trend: {fmt(slope, 2)} cm a year", f"प्रवृत्ति: वर्षमा {fmt(slope, 2)} सेमी"), "compare", trend)],
        rows=[{"trend_cm_per_year": slope, "direction": groundwater["direction"],
               "confidence": groundwater["confidence"]}],
        note=T("It includes glaciers, snow and the plains.", "यसमा हिमनदी, हिउँ र तराई पनि पर्छन्।"))


def bench_is_real(bench):
    if not bench:
        return False
    label = str(bench.get("label", "")).upper()
    return not bench.get("made_up", True) and "REHEARSAL" not in label and "fake_probe" not in bench.get("sources", [])


def chart_probe(bench):
    title = T("The probe, tested in cups", "कपमा जाँचिएको माटो जाँच्ने यन्त्र")
    src = ["Khet Sathi soil probe, bench test in cups of the field's soil (robot/CUPS_PROTOCOL.md; "
           "config/rules.yaml probe.bench)"]
    if not bench_is_real(bench):
        return chart("probe_bench", "probe", title,
                     T("Not ready yet. The cup test comes first.", "अझै तयार छैन। पहिले कपमा जाँच हुन्छ।"),
                     src, "line", status="not_ready")
    excluded = {e["cup_id"] for e in bench.get("excluded", [])}
    cups = [c for c in bench["cups"] if c["cup_id"] not in excluded and c.get("value_pct") is not None]
    acc = bench.get("accurate") or {}
    series = [S(T("Each cup", "हरेक कप"), "main", [[c["water_pct"], c["value_pct"]] for c in cups])]
    rows = [{"cup": c["cup_id"], "water_pct": c["water_pct"], "probe_pct": c["value_pct"]} for c in cups]
    en, ne = ["Each dot is one cup of soil."], ["हरेक थोप्लो माटोको एउटा कप हो"]
    if acc.get("model") == "line" and acc.get("coef") and acc.get("range_probe_pct"):
        a, b = acc["coef"][0], acc["coef"][1]
        series.append(S(T("Fitted line", "मिलाइएको रेखा"), "compare",
                        [[round(a + b * p, 1), p] for p in acc["range_probe_pct"]]))
    mae = acc.get("loo_mae_water_pct")
    if mae is not None:
        en.append(f"Give or take {fmt(mae, 1)} points of water.")
        ne.append(f"पानीमा करिब {fmt(mae, 1)} अङ्क तलमाथि")
    return chart("probe_bench", "probe", title, T(" ".join(en), "। ".join(ne) + "।"), src, "line",
                 x=axis_x(T("Water added (% of the cup)", "थपिएको पानी (कपको %)"), "number"),
                 y=axis_y(T("Probe reading", "यन्त्रको नाप"), "%"),
                 series=series, rows=rows, summary={"proofs": bench.get("proofs", {}), "date": bench.get("date")})


def chart_area(area_site, area_check, field):
    crop = area_check["cropland"]
    ha = int(round(crop["area_ha"], -2))
    rows = [{"id": "cropland_ha", "value": crop["area_ha"], "unit": "hectares", "pixels": crop["pixels"],
             "share_of_box": crop["share_of_box"]}]
    rows += [{k: n[k] for k in ("id", "value", "low", "high", "unit", "en", "ne") if k in n} for n in area_site["numbers"]]
    return chart(
        "area_map", "area", T("Farmland around the field, seen from space", "अन्तरिक्षबाट देखिएको खेत वरिपरिको खेतीयोग्य जमिन"),
        T(f"About {fmt(ha)} hectares of farmland around it. Colours show bare days and crop seasons.",
          f"यसको वरिपरि करिब {fmt(ha)} हेक्टर खेतीयोग्य जमिन। रङले खाली दिन र बाली याम देखाउँछ।"),
        [f"{s['name']}: {s['product']}, {s['resolution']}, {s['years']}" for s in area_site["sources"]], "map",
        rows=rows, link=f"data/area/{field}.json",
        note=T("A sample area: no pixel is a known farm.", "नमुना क्षेत्र: कुनै पिक्सेल चिनिएको खेत होइन।"))


def rain_alts(o, base):
    """The other rain versions a range spans, as the site's alts() (app.js): dhm and untuned; uncorrected only when
    neither is there."""
    a = [o[base + k] for k in ("dhm_rain", "untuned_rain") if o.get(base + k)]
    return a or ([o[base + "uncorrected_rain"]] if o.get(base + "uncorrected_rain") else [])


def future_range(p):
    """The 2040 range over every model and every rain version, the same numbers as the 2040 dial (how.js future)."""
    fs = [p["future"]] + rain_alts(p, "future_")
    return min(f["harvest_low"][-1] for f in fs), max(f["harvest_high"][-1] for f in fs)


def chart_outlook(field_json, plan_names):
    fut = field_json["future"]
    plans = field_json["plans"]
    cats = [cat(p["id"], plan_names[p["id"]]["en"], plan_names[p["id"]]["ne"]) for p in plans]
    today = [[p["id"], p["score"]["harvest"]] for p in plans]
    mid = [[p["id"], p["future"]["harvest"][-1]] for p in plans]
    rng = [[p["id"], list(future_range(p))] for p in plans]
    inside = all(lo <= t[1] <= hi for t, (_, (lo, hi)) in zip(today, rng))
    year = fut["years"][-1]
    n = len(fut.get("models", []))
    c1 = (f"By {year}, each plan stays about the same.", f"{year} सम्म हरेक योजना करिब उस्तै रहन्छ।") if inside else \
        (f"By {year}, some plans change.", f"{year} सम्म केही योजना फेरिन्छन्।")
    rows = []
    for p in plans:
        lo, hi = future_range(p)
        row = {"plan": p["id"], "today": p["score"]["harvest"], "by": year, "middle": p["future"]["harvest"][-1],
               "low": lo, "high": hi, "range_spans": "every climate model and every rain version (as the 2040 dial)"}
        if p.get("future_uncorrected_rain"):
            u = p["future_uncorrected_rain"]
            row["uncorrected_rain"] = {"middle": u["harvest"][-1], "low": u["harvest_low"][-1],
                                       "high": u["harvest_high"][-1]}
        rows.append(row)
    for o in (field_json.get("current_options") or {}).get("options", []):
        if o.get("future"):
            lo, hi = future_range(o)
            rows.append({"plan": "current", "option": o["id"], "today": o["score"]["harvest"], "by": year,
                         "middle": o["future"]["harvest"][-1], "low": lo, "high": hi})
    scen = " and ".join(s.upper().replace("245", "2-4.5").replace("585", "5-8.5") for s in fut.get("scenarios", []))
    return chart(
        "outlook_2040", "future", T(f"Harvest today and by {year}", f"आज र {year} सम्मको उब्जनी"),
        T(c1[0] + f" {n} climate models, two possible futures.",
          c1[1] + f" {n} जलवायु मोडेल, दुई सम्भावित भविष्य।"),
        [f"NEX-GDDP-CMIP6 v2.0 daily, {n} climate models, {scen}, 0.25°; change from 1995-2014 to "
         f"{fut.get('period', year)} applied to the field's 2001-2025 weather (model-based)", SRC_TWIN], "bars",
        x=axis_x(T("Plan", "योजना"), "category", cats),
        y=axis_y(T("Harvest, out of 100", "उब्जनी, १०० मध्ये"), "% of the field's best"),
        series=[S(T("Today (weather of 2002-2025)", "आज (२००२–२०२५ को मौसम)"), "main", today),
                S(T(f"By {year}, middle of the models", f"{year} सम्म, मोडेलहरूको बीच"), "compare", mid),
                S(T(f"By {year}, lowest to highest (models and rain)", f"{year} सम्म, सबैभन्दा कम देखि बढी (मोडेल र वर्षा)"), "range", rng)],
        rows=rows, words=fut.get("words")), inside


def chart_season_methods(method):
    sd = method["season_detection"]
    names = {"threshold": ("Simple threshold", "सरल सीमा"), "changepoint": ("Change points", "परिवर्तन बिन्दु"),
             "detective": ("Computer detective (SI)", "कम्प्युटर जासुस (SI)")}
    ms = sd["methods"]
    best = max(ms, key=lambda m: m["score"])["id"]
    if best != sd["chosen"]:
        cap = T("The computer scored a little higher. Too little to switch; we kept the simplest.",
                "कम्प्युटरले अलि बढी अङ्क ल्यायो। फेर्न पुग्दैनथ्यो; हामीले सरल तरिका राख्यौं।")
    else:
        cap = T("The method we use scored best.", "हामीले प्रयोग गर्ने तरिकाले सबैभन्दा राम्रो अङ्क ल्यायो।")
    return chart(
        "season_methods", "computer", T("Three ways to find the seasons", "बाली याम पत्ता लगाउने तीन तरिका"), cap,
        [SRC_HLS + f"; held-out years {', '.join(str(y) for y in sd['held_out_years'])}, thinned to one picture in "
         f"{sd['thin_days']} days", "SI season detective: a random forest (scikit-learn) trained on this field"],
        "bars",
        x=axis_x(T("Method", "तरिका"), "category", [cat(m["id"], *names.get(m["id"], (m["id"], m["id"]))) for m in ms]),
        y=axis_y(T("Days labelled the same", "उस्तै छुट्याइएका दिन"), "share (0-1)"),
        series=[S(T("Score on years kept aside", "छुट्याएर राखिएका वर्षको अङ्क"), "main",
                  [[m["id"], m["score"]] for m in ms])],
        rows=[{"method": m["id"], "si": m["si"], "score": m["score"], "by_year": m["by_year"]} for m in ms],
        summary={"chosen": sd["chosen"], "margin": sd["margin"]})


def chart_field_memory(memory):
    res = memory["result"]
    rmse = res["rmse"]
    cats = [cat("no_anomaly", "Guess: an ordinary season", "अनुमान: सामान्य याम"),
            cat("physics_only", "Our water count", "हाम्रो पानीको हिसाब"),
            cat("memory", "Learned from past seasons (SI)", "पुराना यामबाट सिकेको (SI)")]
    if res["kept"]:
        cap = T("The learned model did best. We use it.", "सिकेको मोडेल सबैभन्दा राम्रो भयो। हामी यसलाई प्रयोग गर्छौं।")
    else:
        cap = T("The learned model made bigger errors. So we left it out.",
                "सिकेको मोडेलले बढी गल्ती गर्‍यो। त्यसैले हामीले यसलाई छाड्यौं।")
    return chart(
        "field_memory", "computer", T("Teaching the computer this field's habits", "कम्प्युटरलाई खेतको बानी सिकाउँदा"),
        cap,
        [f"{SRC_HLS}: peak greenness of {res['n_seasons']} seasons in {res['n_years']} years",
         SRC_TWIN + ": water shortfall", "Ridge regression (scikit-learn), each year left out in turn"], "bars",
        x=axis_x(T("Way of guessing", "अनुमानको तरिका"), "category", cats),
        y=axis_y(T("Error (smaller is better)", "गल्ती (सानो भए राम्रो)"), "NDVI"),
        series=[S(T("Error on years it never saw", "नदेखेका वर्षमा गल्ती"), "main",
                  [[c["id"], round(rmse[c["id"]], 4)] for c in cats])],
        rows=[{"kept": res["kept"], "decision": res["decision"], "seasons": res["n_seasons"], "years": res["n_years"]}])


def words_review_counts(words):
    pairs, reviewed = 0, 0

    def walk(o):
        nonlocal pairs, reviewed
        if isinstance(o, dict):
            if "en" in o and "ne" in o and "ne_review" in o:
                pairs += 1
                reviewed += str(o["ne_review"]).startswith("reviewed by")
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(words.get("screens", []))
    walk(words.get("glossary", {}))
    walk(words.get("crop_explainers", {}))
    walk(words.get("shared", {}))
    drafts = [lang["code"] for lang in words.get("languages", []) if lang.get("draft")]
    return pairs, reviewed, drafts


def chart_ai_words(words, field_json):
    pairs, reviewed, drafts = words_review_counts(words)
    plan_texts = sum(len(p.get("tabs", {})) + len(p.get("tips", [])) for p in field_json["plans"])
    rows = [
        {"what": T("Screen words, glossary and crop notes", "स्क्रिनका शब्द, शब्दकोश र बाली टिप्पणी"),
         "texts": pairs, "drafted_by": "SI (Claude)", "nepali_reviewed": reviewed,
         "status": T(f"{reviewed} of {pairs} Nepali texts reviewed.", f"{pairs} मध्ये {reviewed} नेपाली पाठ जाँचिएका।")},
        {"what": T("Each plan's five tabs and tips", "हरेक योजनाका पाँच ट्याब र सुझाव"), "texts": plan_texts,
         "drafted_by": "SI templates filled from the numbers",
         "status": T("Nepali awaits a native speaker.", "नेपाली पाठले मातृभाषीको जाँच पर्खिरहेछ।")},
        {"what": T(f"Draft translations into {len(drafts)} more languages", f"थप {len(drafts)} भाषामा मस्यौदा अनुवाद"),
         "texts": pairs * len(drafts), "languages": drafts, "drafted_by": "SI machine translation",
         "status": T("Marked as drafts; not reviewed.", "मस्यौदा भनी चिनो लगाइएको; जाँचिएको छैन।")},
    ]
    return chart(
        "ai_words", "computer", T("Words drafted by a computer, checked by people", "कम्प्युटरले लेखेका, मानिसले जाँच्ने शब्द"),
        T(f"A computer drafted these words. {reviewed} of {pairs} Nepali texts checked so far.",
          f"यी शब्द कम्प्युटरले लेखेका हुन्। अहिलेसम्म {pairs} मध्ये {reviewed} नेपाली पाठ जाँचिएका छन्।"),
        ["Khet Sathi texts drafted by SI (Claude) in pipeline/words/, with the review mark of every Nepali text in "
         "site/data/words.json; SI_LOG.md records what a person reviewed"], "table", rows=rows)


# --- report card -----------------------------------------------------------------------------------------------------

STATUS_WORDS = {"VERIFIED": T("Verified", "प्रमाणित"), "ESTIMATE": T("Estimate", "अनुमान"),
                "NOT YET VERIFIABLE": T("Not yet checkable", "अझै जाँच्न मिल्दैन")}
# owner's item 4 (2026-11-14): what we measured, with its number; the yardsticks are rules.yaml verification
COMPLIANCE = {
    "rain_months": (("Rain on the field", "खेतमा परेको वर्षा"),
                    ["We checked our rain against Nepal's rain gauges.", "It was within {tol}% in {k} of {n} months.",
                     "Our rain was tuned on these months."],
                    ["हामीले हाम्रो वर्षा नेपालका वर्षा मापकसँग जाँच्यौं", "{n} मध्ये {k} महिना {tol}% भित्र मिल्यो",
                     "हाम्रो वर्षा यिनै महिनामा मिलाइएको थियो"]),
    "rain_month_words": (("Rainy and dry months", "वर्षा हुने र सुक्खा महिना"),
                         ["They match Nepal's weather office.", "{k} of {n} months match."],
                         ["नेपालको मौसम कार्यालयसँग मिल्छन्", "{n} मध्ये {k} महिना मिल्छन्"]),
    "heat_month_words": (("Warm and cool months", "तातो र चिसो महिना"),
                         ["They match Nepal's weather office.", "{k} of {n} months match."],
                         ["नेपालको मौसम कार्यालयसँग मिल्छन्", "{n} मध्ये {k} महिना मिल्छन्"]),
    "frost_month_words": (("Frost months", "तुषारो पर्ने महिना"),   # owner, 2026-11-15 (item 1)
                          ["We checked the cold months against Nepal's weather office.", "{k} of {n} months fit its night temperatures.",
                           "It cannot check the coldest nights yet."],
                          ["चिसो महिना नेपालको मौसम कार्यालयसँग जाँच्यौं", "{n} मध्ये {k} महिना रातको तापक्रमसँग मिल्छन्",
                           "सबैभन्दा चिसो रात अझै जाँच्न सकिँदैन"]),
    "soil_month_words": (("Dry and wet soil months", "सुक्खा र ओसिलो माटोका महिना"),   # owner, 2026-11-15 (item 2)
                         ["Checked against two NASA computer models.", "{k} of {n} months match.", "Models are not measured soil."],
                         ["नासाका दुई कम्प्युटर मोडेलसँग जाँचिएको", "{n} मध्ये {k} महिना मिल्छन्", "मोडेल भनेको नापिएको माटो होइन"]),
    "cover_months": (("Bare and growing months", "खाली र बाली भएका महिना"),
                     ["Checked against the drone photo and FAO's calendar.", "{k} of {n} checks match.", "Still waiting for the farmer's calendar."],
                     ["ड्रोन तस्बिर र FAO को बाली पात्रोसँग जाँचिएको", "{n} मध्ये {k} जाँच मिल्छन्", "किसानको बाली पात्रो अझै पर्खिरहेका छौं"]),
    "season_dates": (("Planting and harvest dates", "रोप्ने र काट्ने मिति"),
                     ["Checked against the drone photo and FAO's calendar.", "{k} of {n} checks match.", "Still waiting for the farmer's dates."],
                     ["ड्रोन तस्बिर र FAO को बाली पात्रोसँग जाँचिएको", "{n} मध्ये {k} जाँच मिल्छन्", "किसानका मिति अझै पर्खिरहेका छौं"]),
    "rotation_guess": (("Our guess of your crops", "तपाईंका बालीको हाम्रो अनुमान"),
                       ["Checked against a drone photo, calendar and district crops.", "{k} of {n} checks match.",
                        "Needs answers from at least {nmin} farmers."],
                       ["ड्रोन तस्बिर, बाली पात्रो र जिल्लाका बालीसँग जाँचिएको", "{n} मध्ये {k} जाँच मिल्छन्",
                        "कम्तीमा {nmin} किसानको उत्तर चाहिन्छ"]),
    "flood_years": (("Flood years", "बाढी आएका वर्ष"),
                    ["Found {k} of {n} valley floods.", "{fa} of {fan} flags had no recorded flood.",
                     "We knew these floods before setting the rule."],
                    ["उपत्यकाका {n} मध्ये {k} बाढी भेटियो", "{fan} सङ्केतमध्ये {fa} मा बाढीको अभिलेख छैन",
                     "नियम बनाउनुअघि नै यी बाढी थाहा थिए"]),
    "drought_years": (("Dry years", "सुक्खा वर्ष"),
                      ["Found {k} of {n} valley dry seasons.", "{fa} of {fan} flagged seasons were not confirmed.",
                       "The rule was chosen after seeing some of them."],
                      ["उपत्यकाका {n} मध्ये {k} सुक्खा याम भेटियो", "{fan} सङ्केतमध्ये {fa} पुष्टि भएनन्",
                       "केही देखिसकेपछि नियम छानिएको हो"]),
    "harvest_years": (("Good and bad harvest years", "राम्रो र नराम्रो उब्जनीका वर्ष"),   # owner, 2026-11-15 (item 4)
                      ["{k} of {n} good or bad years match Bhaktapur's district harvests.",
                       "Still waiting for the farmer's best and worst years."],
                      ["{n} मध्ये {k} राम्रा वा नराम्रा वर्ष भक्तपुर जिल्लाको उब्जनीसँग मिल्छन्",
                       "किसानका राम्रा र नराम्रा वर्ष अझै पर्खिरहेका छौं"]),
    "plan_cover_gap_beats_current": (("'Fill the empty months' grows more", "'खाली महिनामा पनि बाली' ले बढी उब्जाउँछ"),
                                     ["It beats today's plan in {k} of {n} computer runs.", "All runs use our one crop model.",
                                      "Only a season of Safe Trial can verify it."],
                                     ["{n} कम्प्युटर गणनामध्ये {k} मा अहिलेको योजनाभन्दा राम्रो",
                                      "सबै गणनाले एउटै बाली मोडेल प्रयोग गर्छन्", "सुरक्षित परीक्षणको एक यामले मात्र प्रमाणित गर्न सक्छ"]),
    "plan_safest_beats_current": (("'Feed your soil' grows more", "'माटोलाई मलिलो बनाउने' ले बढी उब्जाउँछ"),
                                  ["It beats today's plan in {k} of {n} computer runs.", "All runs use our one crop model.",
                                   "Only a season of Safe Trial can verify it."],
                                  ["{n} कम्प्युटर गणनामध्ये {k} मा अहिलेको योजनाभन्दा राम्रो",
                                   "सबै गणनाले एउटै बाली मोडेल प्रयोग गर्छन्", "सुरक्षित परीक्षणको एक यामले मात्र प्रमाणित गर्न सक्छ"]),
    "monsoon_start": (("When the monsoon starts", "मनसुन कहिले सुरु हुन्छ"),
                      ["These are Nepal's weather office's own dates.", "We checked our copy twice: {k} of {n} match."],
                      ["यी नेपालको मौसम कार्यालयकै मिति हुन्", "हाम्रो प्रतिलिपि दुई पटक जाँच्यौं: {n} मध्ये {k} मिल्छन्"]),
    "monsoon_shift": (("Has the monsoon start shifted?", "मनसुन सुरु हुने समय सरेको छ?"),   # owner, 2026-11-15 (item 3)
                      ["The answer comes from Nepal's weather office dates.", "We checked it a second way: {k} of {n} years match."],
                      ["उत्तर नेपालको मौसम कार्यालयका मितिबाट आउँछ", "दोस्रो तरिकाले जाँच्यौं: {n} मध्ये {k} वर्ष मिल्छन्"]),
    "groundwater": (("Water under the ground", "जमिनमुनिको पानी"),
                    ["Falling, as published valley well studies say.", "{k} of {n} studies agree.", "Needs well records from the valley."],
                    ["उपत्यकाका इनारका प्रकाशित अध्ययनले भनेझैं घट्दो", "{n} मध्ये {k} अध्ययन मिल्छन्", "उपत्यकाका इनारको अभिलेख चाहिन्छ"]),
    "part_soil_water": (("How wet each part is", "हरेक भाग कति ओसिलो छ"),
                        ["Waiting for soil readings at the field."], ["खेतमा माटोको नाप पर्खिरहेका छौं"]),
    "probe_water": (("The soil stick's reading", "माटो जाँच्ने यन्त्रको नाप"),
                    ["{k} of {n} spoon cups read within 4 points.", "At least {nmin} cups are needed to verify it."],
                    ["{n} मध्ये {k} चम्चा-कप ४ अङ्कभित्र मिले", "प्रमाणित गर्न कम्तीमा {nmin} कप चाहिन्छ"]),
    "outlook_2040": (("Harvest by 2040", "२०४० सम्मको उब्जनी"),
                     ["A look ahead from many climate models.", "Same direction as Nepal's 2019 projections.",
                      "It can only be checked in 2040."],
                     ["धेरै जलवायु मोडेलबाट अगाडिको अनुमान", "नेपालको २०१९ को प्रक्षेपणसँग एउटै दिशा", "यो २०४० मा मात्र जाँच्न सकिन्छ"]),
    "plan_scores": (("Water, cover and soil scores", "पानी, ढाकिएको जमिन र माटोका अङ्क"),
                    ["Worked out by computer.", "Only a season of Safe Trial can verify them."],
                    ["कम्प्युटरले निकालेको", "सुरक्षित परीक्षणको एक यामले मात्र प्रमाणित गर्न सक्छ"]),
}


# owner, 2026-11-15 (item 6): one plain line per row that is not VERIFIED, saying what would verify it. The English is
# rules.yaml verification.outputs.<id>.verify_by (carried in the scorecard); the Nepali drafts are here (native review)
VERIFY_BY_NE = {
    "rain_months": "नेपालको मौसम कार्यालयका २०२६ का वर्षा नाप, जुन मिलाउन कहिल्यै प्रयोग गरिएन।",
    "frost_month_words": "तुषारो परेका रातको किसानको अभिलेख, वा एक जाडो खेतमा थर्मामिटर।",
    "soil_month_words": "वास्तविक खेतमा माटो जाँच्ने यन्त्र, एक वर्ष हरेक महिना।",
    "cover_months": "किसानको अभिलेख: खेत कुन महिना खाली रहन्छ।",
    "season_dates": "किसानको अभिलेख: ३ वर्ष कहिले रोपे र कहिले काटे।",
    "rotation_guess": "कम्तीमा १० खेतका किसानले के लगाए भन्ने अभिलेख।",
    "flood_years": "बाढी आएका वर्षको किसानको अभिलेख, र उपत्यकाका थप लिखित अभिलेख।",
    "drought_years": "सुक्खा वर्षको किसानको अभिलेख, र उपत्यकाका थप लिखित अभिलेख।",
    "harvest_years": "किसानको अभिलेख: उनका सबैभन्दा राम्रा र नराम्रा उब्जनीका वर्ष।",
    "plan_cover_gap_beats_current": "सुरक्षित परीक्षणको एक याम: खेतको एउटा भागमा प्रयोग।",
    "plan_safest_beats_current": "सुरक्षित परीक्षणको एक याम: खेतको एउटा भागमा प्रयोग।",
    "monsoon_start": "नेपालको मौसम कार्यालयकै मनसुन सुरु मिति, अर्को तरिकाले पढिएको।",
    "monsoon_shift": "नेपालको मौसम कार्यालयकै मनसुन सुरु मिति, अर्को तरिकाले पढिएको।",
    "groundwater": "नेपालको भूमिगत जल कार्यालयले उपत्यकामा नापेको इनारको पानीको सतह।",
    "part_soil_water": "वास्तविक खेतका भाग-भागमा माटो जाँच्ने यन्त्रको जाँच।",
    "probe_water": "कप परीक्षण: तौलिएको पानी भएका कपमा माटो जाँच्ने यन्त्र, नाप लेखिएको।",
    "outlook_2040": "भविष्यको अनुमान: प्रकाशित प्रक्षेपणसँग मात्र जाँचिएको, कहिल्यै प्रमाणित होइन।",
    "plan_scores": "सुरक्षित परीक्षणको एक याम, प्रयोग भएको पानी र बगेको माटो नापेर।",
}


def verify_by(cid, c):
    """'What would verify it' for a row that is not VERIFIED (None for a VERIFIED row, or one with no line)."""
    en = c.get("verify_by") or "-"
    if c["status"] == "VERIFIED" or en == "-":
        return None
    return T("What would verify it: " + en, "यसलाई प्रमाणित गर्न: " + VERIFY_BY_NE[cid])


def verify_how(rows, ys):
    """owner, 2026-11-15: 'How each answer becomes verified' (How we know): the three words, today's count and the four
    ways the rest can be checked."""
    n = {s: sum(r["status"] == s for r in rows) for s in ("VERIFIED", "ESTIMATE", "NOT YET VERIFIABLE")}
    return {"title": T("How each answer becomes verified", "हरेक उत्तर कसरी प्रमाणित हुन्छ"),
            "lines": [T(f"Verified: checked against a record we did not use to make it. Right at least {ys['pct']} times "
                        f"in 100, on {ys['nmin']} or more checks.",
                        f"प्रमाणित: बनाउँदा प्रयोग नगरिएको अभिलेखसँग जाँचिएको। कम्तीमा {ys['nmin']} जाँचमा १०० मा {ys['pct']} पटक सही।"),
                      T("Estimate: checked only against models or our own runs, or right fewer times. Shown with its range, "
                        "never as a promise.",
                        "अनुमान: मोडेल वा हाम्रै गणनासँग मात्र जाँचिएको, वा कम पटक सही। दायरासहित देखाइन्छ, वाचा होइन।"),
                      T("Not yet checkable: the record that would check it does not exist yet.",
                        "अझै जाँच्न मिल्दैन: जाँच्ने अभिलेख अझै छैन।"),
                      T(f"Today: {n['VERIFIED']} verified, {n['ESTIMATE']} estimates, {n['NOT YET VERIFIABLE']} not yet checkable.",
                        f"आज: {n['VERIFIED']} प्रमाणित, {n['ESTIMATE']} अनुमान, {n['NOT YET VERIFIABLE']} अझै जाँच्न नमिल्ने।"),
                      T("Four things will check the rest:", "बाँकी यी चार कुराले जाँच्छन्:"),
                      T("The farmer's records: sowing and harvest dates, best and worst years, bare months.",
                        "किसानको अभिलेख: रोप्ने र काट्ने मिति, राम्रा र नराम्रा वर्ष, खाली महिना।"),
                      T("A probe walk on the real field: each part's soil water, measured.",
                        "वास्तविक खेतमा माटो जाँच्ने यन्त्र: हरेक भागको माटोको पानी नापेर।"),
                      T("A season of Safe Trial: one part of the field tries a plan.",
                        "सुरक्षित परीक्षणको एक याम: खेतको एउटा भागमा योजना प्रयोग।"),
                      T("Projections, like 2040: checked against published ranges only.",
                        "२०४० जस्ता भविष्यका अनुमान: प्रकाशित दायरासँग मात्र जाँचिन्छन्।")]}


def yardsticks():
    """The numbers the words quote, from rules.yaml verification (never typed into a sentence)."""
    from pipeline.fetch.rules import load_rules
    v = load_rules()["verification"]
    return {"pct": round(v["common"]["threshold"] * 100), "nmin": v["common"]["n_min"],
            "tol": round(v["outputs"]["rain_months"]["tolerance_rel"] * 100)}


def _fill(xs, vals):
    """Format each sentence; with no cases yet, sentences that need a count are left out."""
    out = []
    for x in xs:
        try:
            out.append(x.format(**vals))
        except KeyError:
            pass
    return out


def limits_block(rows):
    """'What this tool can and cannot tell you' (owner's plan, part A2, 2026-11-15), for Home and How we know: four plain
    lines, then the compliance table's things split into checked (VERIFIED) and estimates (ESTIMATE and NOT YET
    VERIFIABLE, which rules.yaml farmer_answers.wording treats as estimates). Words only, no number. Pure."""
    return {
        "title": T("What this tool can and cannot tell you", "यो साधनले के भन्न सक्छ, के सक्दैन"),
        "lines": [T("It shows a real farm and sample fields.", "यसले एउटा साँचो खेत र नमुना खेत देखाउँछ।"),
                  T("No farmer has answered our questions yet.", "कुनै किसानले अझै हाम्रा प्रश्नको जवाफ दिनुभएको छैन।"),
                  T("Our advice is only a starting point.", "हाम्रो सल्लाह सुरुआत मात्र हो।"),
                  T("Check with your local agriculture office.", "आफ्नो स्थानीय कृषि कार्यालयसँग सोध्नुहोस्।")],
        "checked": {"title": T("Checked against real records:", "साँचो अभिलेखसँग जाँचिएको:"),
                    "items": [r["thing"] for r in rows if r["status"] == "VERIFIED"]},
        "estimates": {"title": T("Estimates, not checked yet:", "अनुमान, अझै नजाँचिएको:"),
                      "items": [r["thing"] for r in rows if r["status"] != "VERIFIED"]},
        "source": "the compliance table (story.json compliance; VALIDATION.md 'Compliance table')",
    }


def compliance(card, ys=None):
    """The compliance table (owner's item 4): one line per shown output from data/checks/<field>/scorecard.json."""
    out, ys = [], ys or yardsticks()
    for cid, c in (card or {}).items():
        (thing_en, thing_ne), en, ne = COMPLIANCE[cid]
        vals = ys | ({"k": c["k"], "n": c["n"], "fa": c.get("false_alarms", 0), "fan": c.get("flagged_seasons", 0)}
                     if c["n"] else {})
        out.append({"id": cid, "thing": T(thing_en, thing_ne), "status": c["status"], "status_words": STATUS_WORDS[c["status"]],
                    "k": c["k"], "n": c["n"], "share": c["share"], "ci95": c["ci95"], "independent": c["independent"],
                    "said": T(" ".join(_fill(en, vals)), "। ".join(_fill(ne, vals)) + "।"),
                    **({"verify_by": vb} if (vb := verify_by(cid, c)) else {})})
    order = {"VERIFIED": 0, "ESTIMATE": 1, "NOT YET VERIFIABLE": 2}
    return sorted(out, key=lambda r: order[r["status"]])


def _line(cid, thing, confidence, en, ne, refs):
    return {"id": cid, "thing": thing, "confidence": confidence,
            "why": T(" ".join(en), "। ".join(ne) + "।"), "refs": refs}


def report_card(ctx):
    """One line per thing shown, each with a confidence and why. The rules are in METHOD_NOTES 98."""
    out = []
    # seasons
    n, d = ctx["season_matches"], ctx["season_start_diff_days"]
    out.append(_line("seasons", T("When the field is green", "खेत कहिले हरियो हुन्छ"), "high",
                     [f"Three methods find the same {n} seasons.", f"Start dates typically differ by {d} days.",
                      "It cannot tell which crop it is.", "The model now starts crops on these dates.",
                      "So the two no longer check each other."],
                     [f"तीन तरिकाले उही {n} बाली याम भेट्टाए", f"सुरुका मिति प्रायः {d} दिन फरक पर्छन्",
                      "यो कुन बाली हो भन्न सक्दैन", "मोडेलले अब यिनै मितिमा बाली सुरु गर्छ",
                      "त्यसैले यी दुईले एकअर्कालाई जाँच्दैनन्"],
                     ["3.6", "3.10", "3.15", "3.18", "3.23", "4.2c"]))
    # bare days
    bd, lo, hi = ctx["bare_days"], ctx["bare_lo"], ctx["bare_hi"]
    out.append(_line("bare_days", T("Days the field lies bare", "खेत खाली रहने दिन"), "low",
                     [f"This field: about {bd} bare days a year.", "Our bare line is not tuned yet.",
                      f"Nudged a little, nearby fields read {lo}-{hi} days.", "Older satellite years are not comparable."],
                     [f"यो खेत: वर्षमा करिब {bd} दिन खाली", "खाली छुट्याउने रेखा अझै मिलाइएको छैन",
                      f"अलिकति सार्दा नजिकका खेत {lo}–{hi} दिन देखिन्छन्", "पुराना भू-उपग्रह वर्ष तुलना गर्न मिल्दैन"],
                     ["3.10", "3.23"]))
    # rain
    rf, rl, lvl, by = ctx["rain_final_ratio"], ctx["rain_late_ratio"], ctx["rain_level_ratio"], ctx["break_year"]
    conf = "medium" if 0.8 <= rf <= 1.25 else "low"
    nf, nl = ctx["n_final_months"], ctx["n_late_months"]
    en = [f"NASA's rain lost its gauges in {by}.", "We found the break and fixed it.",
          f"We checked {nf + nl} months of 2025 against gauges.", f"{nf} months read {fmt(rf, 2)} times the gauges."]
    ne = [f"सन् {by} मा नासाको वर्षाले मापक गुमायो", "हामीले त्यो त्रुटि भेटेर सच्यायौं",
          f"हामीले २०२५ का {nf + nl} महिना मापकसँग जाँच्यौं", f"{nf} महिना मापकको {fmt(rf, 2)} गुणा थिए"]
    if rl > SAME_LEVEL[1]:
        en.append(f"The last {nl} still read too wet.")
        ne.append(f"अन्तिम {nl} महिना अझै धेरै बढी वर्षा देखाउँथे")
    if ctx.get("rain_tuned"):
        en.append(TUNED[0])
        ne.append(TUNED[1])
    en.append(f"Yearly rain: {fmt(lvl, 2)} times the town's usual.")
    ne.append(f"वार्षिक वर्षा सहरको सामान्यको {fmt(lvl, 2)} गुणा")
    out.append(_line("rain", T("Rain on the field", "खेतमा परेको वर्षा"), conf, en, ne,
                     ["3.1", "3.9", "3.9b", "3.9c", "3.9d", "4.2d"]))
    # harvest numbers
    fao = ctx["fao"]
    en, ne = ["These come from a computer model."], ["यी अङ्क कम्प्युटर मोडेलबाट आउँछन्"]
    names = {"wheat": ("Wheat", "गहुँका"), "potato": ("Potato", "आलुका"), "rice": ("Rice", "धानका")}
    for crop in ("wheat", "potato", "rice"):
        c = fao[crop]
        if str(c["status"]).startswith("not testable"):
            en.append(f"{names[crop][0]} years cannot be tested.")
            ne.append(f"{names[crop][1]} वर्ष जाँच्न मिल्दैन")
        elif c["holds_up"]:
            en.append(f"{names[crop][0]} years follow Nepal's yields (r {fmt(c['correlation']['pearson'], 2)}).")
            ne.append(f"{names[crop][1]} वर्ष नेपालको उब्जनीसँग मिल्छन् (r {fmt(c['correlation']['pearson'], 2)})")
        else:
            en.append(f"{names[crop][0]} years do not follow Nepal's yields.")
            ne.append(f"{names[crop][1]} वर्ष नेपालको उब्जनीसँग मिल्दैनन्")
    en.append("Root depth and soil change them a lot.")
    ne.append("जराको गहिराइ र माटोले अङ्क धेरै फेर्छन्")
    out.append(_line("harvest", T("Harvest numbers (out of 100)", "उब्जनीका अङ्क (१०० मध्ये)"), "low", en, ne,
                     ["4.2", "4.3", "4.4", "4.4c", "3.21"]))
    # plan ranking
    en = ["The same plans won when we changed inputs.", "How much better they are is unsure."]
    ne = ["इनपुट फेर्दा पनि उही योजना अगाडि आए", "कति राम्रो भन्ने कुरा निश्चित छैन"]
    if ctx["placeholder"]:
        en.append("Your real crops are not known yet.")
        ne.append("तपाईंका साँचो बाली अझै थाहा छैन")
    out.append(_line("plan_ranking", T("Which plan comes first", "कुन योजना पहिलो आउँछ"), "medium", en, ne,
                     ["3.19", "3.21", "4.4", "4.4b"]))
    # floods and dry years
    ev = ctx["events"]
    kf, nf = ev["valley_floods"]
    m = len(ev["unrecorded_flood_years"])
    en = [f"It found {kf} of {nf} valley floods."]
    ne = [f"उपत्यकाका {nf} मध्ये {kf} बाढी भेट्टायो"]
    if m:
        en.append(f"It also flagged {m} unrecorded flood {'year' if m == 1 else 'years'}.")
        ne.append(f"बाढीको अभिलेख नभएको {m} वर्षलाई पनि बाढी भन्यो")
    en.append("We knew these floods before setting the rule.")
    ne.append("नियम बनाउनुअघि यी बाढी हामीलाई थाहा थिए")
    out.append(_line("floods", T("Flood years", "बाढीका वर्ष"), "medium" if nf and kf == nf else "low", en, ne,
                     ["4.1", "3.9b"]))
    kd, nd = ev["valley_droughts"]
    failed = sum(1 for c in ev["negative_controls"] if not c["passes"])
    en = [f"It found {kd} of {nd} valley dry spells."]
    ne = [f"उपत्यकाका {nd} मध्ये {kd} सुक्खा याम भेट्टायो"]
    if failed:
        en.append(f"It called {failed} normal or wet {'monsoon' if failed == 1 else 'monsoons'} dry.")
        ne.append(f"सामान्य वा बढी पानीका {failed} बर्खालाई सुक्खा भन्यो")
    en, ne = en + unconfirmed(ctx.get("scorecard"), "drought")[0], ne + unconfirmed(ctx.get("scorecard"), "drought")[1]
    en.append("The rain fix cannot reorder the years.")
    ne.append("वर्षा सच्याउँदा वर्षहरूको क्रम फेरिँदैन")
    good = nd and kd / nd >= 0.75 and failed == 0
    out.append(_line("dry_years", T("Dry years", "सुक्खा वर्ष"), "medium" if good else "low", en, ne,
                     ["4.1", "3.9b", "3.9d"]))
    # frost
    out.append(_line("frost", T("Frost risk", "तुषारोको जोखिम"), "low",
                     ["We show risk by month, never counts.", "Our cold nights outnumber the airport's.",
                      "The recorded frost night itself was missed.", "Bhaktapur's winter nights are colder still."],
                     ["हामी महिनाअनुसार जोखिम देखाउँछौं, सङ्ख्या होइन", "हाम्रा चिसा रात विमानस्थलभन्दा धेरै छन्",
                      "अभिलेख भएको तुषारो रात नै छुट्यो", "भक्तपुरका जाडोका रात अझ चिसा हुन्छन्"],
                     ["3.14", "4.1b", "4.1c", "3.11b"]))
    # weather ahead (owner, 2026-11-14 evening): low while its dangers rest on the frost temperatures (the frost line above);
    # the word was fixed after its checks were seen, so it takes the more cautious one (METHOD_NOTES 98)
    wc = ctx.get("weather_ahead")
    if wc:
        k, fl = wc["rain_words"]["calendar_months"]["agree"], wc["floods"]
        out.append(_line("weather_ahead", T("Weather ahead (each month)", "आउँदो मौसम (हरेक महिना)"), "low",
                         [f"Rain words match DHM's normals: {k} of 12.",
                          f"Big rain on {fl['hit']} of {fl['of']} flood dates.",
                          "The dangers use our cold-night numbers.", "Those count too many cold nights.",
                          "Past years only, not a forecast."],
                         [f"वर्षाका शब्द DHM सँग मिल्छन्: १२ मध्ये {k}",
                          f"बाढीका {fl['of']} मध्ये {fl['hit']} मितिमा ठूलो पानी",
                          "खतराहरू हाम्रा चिसो रातका अङ्कमा आधारित छन्", "ती अङ्कले चिसो रात धेरै गन्छन्",
                          "विगतका वर्ष मात्र, पूर्वानुमान होइन"],
                         ["4.10", "3.14", "4.1c"]))
    # groundwater
    gw = ctx["groundwater"]
    s = fmt(abs(gw["trend_cm_per_year"]), 1)
    if gw["direction"] == "falling":
        en, ne = [f"The region loses about {s} cm a year."], [f"यो क्षेत्रले वर्षमा करिब {s} सेमी पानी गुमाउँछ"]
    elif gw["direction"] == "rising":
        en, ne = [f"The region gains about {s} cm a year."], [f"यो क्षेत्रले वर्षमा करिब {s} सेमी पानी थप्छ"]
    else:
        en, ne = ["The region's water stays about the same."], ["यो क्षेत्रको पानी करिब उस्तै छ"]
    if gw["confidence"] >= 0.95:
        en.append("This trend is clear.")
        ne.append("यो प्रवृत्ति स्पष्ट छ")
    en += [f"The region is about {ctx['region_km']} km wide.", "It includes glaciers and snow, not your well.",
           "No well readings have checked it."]
    ne += [f"क्षेत्र करिब {ctx['region_km']} किमी चौडा छ", "यसमा हिमनदी र हिउँ पर्छ, तपाईंको इनार होइन",
           "कुनै इनारको नापले यसलाई जाँचेको छैन"]
    out.append(_line("groundwater", T("Water under the ground", "जमिनमुनिको पानी"), "medium", en, ne, ["3.16"]))
    # monsoon onset
    ms = ctx["monsoon_start"]
    a, b = int(ms["usual_from"][3:]), int(ms["usual_to"][3:])
    en = [f"Nepal's weather office: usually {a}-{b} June.", "It reaches here a few days later."]
    ne = [f"नेपालको मौसम कार्यालय: प्रायः जुन {a}–{b}", "यहाँ केही दिनपछि आइपुग्छ"]
    lo_, hi_ = ctx["shift_low"], ctx["shift_high"]
    if lo_ is not None and hi_ is not None and lo_ < 0 < hi_:
        en.append(f"No clear change since {ms['years'][0]}.")
        ne.append(f"सन् {ms['years'][0]} यता स्पष्ट फरक छैन")
    en.append("Our own satellite methods failed this check.")
    ne.append("हाम्रा भू-उपग्रह तरिका यो जाँचमा असफल भए")
    out.append(_line("onset", T("When the monsoon starts", "मनसुन कहिले सुरु हुन्छ"), "medium", en, ne,
                     ["3.3", "4.1d", "4.1e", "4.1f", "3.22", "3.22b"]))
    # probe
    bench = ctx["bench"]
    if bench_is_real(bench):
        proofs = bench.get("proofs", {})
        passed = all(proofs.get(k) is True for k in ("steady", "order", "temperature"))
        mae = (bench.get("accurate") or {}).get("loo_mae_water_pct")
        en = [f"In cups, off by about {fmt(mae, 1)} points."] if mae is not None else []
        ne = [f"कपमा करिब {fmt(mae, 1)} अङ्क फरक पर्‍यो"] if mae is not None else []
        if bench.get("hand_copied"):     # rules.yaml probe.bench.spoon.hand_copied: some proofs were not possible, not failed
            en += ["A rough test, copied by hand.", "Some cup checks were not possible."]
            ne += ["हातले सारिएको मोटामोटी जाँच", "कप जाँचका केही भाग गर्न सकिएन"]
        elif not passed:
            en.append("It failed part of the cup test.")
            ne.append("कप जाँचको केही भागमा असफल भयो")
        en.append("It reads only the top few centimetres.")
        ne.append("यसले माथिका केही सेन्टिमिटर मात्र नाप्छ")
        conf = "medium" if passed else "low"
    else:
        en = ["Not tested in cups yet.", "It reads only the top few centimetres.", "No water number until that test."]
        ne = ["अझै कपमा जाँचिएको छैन", "यसले माथिका केही सेन्टिमिटर मात्र नाप्छ", "त्यो जाँचअघि पानीको अङ्क दिँदैन"]
        conf = "low"
    out.append(_line("probe", T("The soil probe", "माटो जाँच्ने यन्त्र"), conf, en, ne, ["5.1", "5.2", "5.3", "5.4"]))
    # 2040
    n_models, inside = ctx["n_models"], ctx["plausible"]
    en = [f"{n_models} climate models, two possible futures."]
    ne = [f"{n_models} जलवायु मोडेल, दुई सम्भावित भविष्य"]
    if inside:
        en.append("Their changes fit published ranges for Nepal.")
        ne.append("तिनका परिवर्तन नेपालका प्रकाशित दायराभित्र पर्छन्")
    en += ["Only averages change; extremes stay as observed.", "It rests on the same harvest model."]
    ne += ["औसत मात्र फेरिन्छ; चरम मौसम उस्तै राखिन्छ", "यो उही उब्जनी मोडेलमा आधारित छ"]
    out.append(_line("outlook_2040", T(f"Harvest by {ctx['future_year']}", f"{ctx['future_year']} सम्मको उब्जनी"),
                     "low", en, ne, ["4.7"]))
    return out


# --- satellite inventory and the challenge's resource list (checked against DATA_AUDIT and CREDITS, 2026-11-14) ------

SATELLITES = [
    {"id": "gpm", "mission": "GPM Core Observatory and the GPM constellation (partner microwave satellites, "
                             "geostationary infrared)",
     "instrument": "GMI radiometer and DPR radar on the core; partner passive-microwave sensors; geostationary infrared",
     "dataset": "GPM IMERG V07: Final daily (GPM_3IMERGDF), Late daily (GPM_3IMERGDL), Final monthly (GPM_3IMERGM), 0.1°",
     "kind": "satellites and gauges",
     "job": T("The model's daily rain.", "मोडेलको दैनिक वर्षा।"),
     "checked": T("Its 2017 gauge loss was found and fixed. Checked against CHIRPS and Nepal's gauges.",
                  "२०१७ मा मापक हराएको भेटेर सच्यायौं। चिर्प्स र नेपालका मापकसँग जाँच्यौं।"),
     "refs": ["3.9", "3.9b", "3.9c", "3.9d"]},
    {"id": "landsat", "mission": "Landsat 8 and Landsat 9 (NASA/USGS)", "instrument": "OLI and OLI-2",
     "dataset": "HLS-VI v2.0, HLSL30_VI (30 m)", "kind": "satellite",
     "job": T("Greenness: seasons, bare days and crop cover.", "हरियाली: बाली याम, खाली दिन, ढाकिएको जमिन।"),
     "checked": T("Three season methods agree. It matches MODIS.", "तीन तरिका मिल्छन्। मोडिससँग मिल्छ।"),
     "refs": ["3.6", "3.10", "3.15", "3.23"]},
    {"id": "sentinel2", "mission": "Sentinel-2 (ESA Copernicus)", "instrument": "MSI",
     "dataset": "HLS-VI v2.0, HLSS30_VI (30 m)", "kind": "satellite",
     "job": T("Greenness, more often than Landsat alone.", "हरियाली, ल्यान्डस्याटभन्दा धेरै पटक।"),
     "checked": T("Same checks as Landsat: one shared series.", "ल्यान्डस्याटकै जाँच: एउटै साझा शृङ्खला।"),
     "refs": ["3.10", "3.15", "3.23"]},
    {"id": "modis", "mission": "Terra (NASA)", "instrument": "MODIS", "dataset": "MOD13Q1 v061 NDVI (250 m, 16 days)",
     "kind": "satellite",
     "job": T("Older greenness, compared with HLS only.", "पुरानो हरियाली, HLS सँग तुलना मात्र।"),
     "checked": T("Agrees with HLS. It misses short bare spells.", "HLS सँग मिल्छ। छोटो खाली समय छुटाउँछ।"),
     "refs": ["3.10"]},
    {"id": "smap", "mission": "SMAP (NASA)", "instrument": "L-band radiometer (its radar failed in 2015)",
     "dataset": "SPL4SMGP v008 (L4 root zone, model-assisted, 9 km); SPL3SMP_E v006 (L3)", "kind": "satellite",
     "job": T("Checks the model's soil water. Sets how sure the model is.",
              "मोडेलको माटोको पानी जाँच्छ। मोडेल कति निश्चित छ भनी तय गर्छ।"),
     "checked": T("Its L3 had no good value here. L4 agrees moderately.",
                  "यहाँ L3 मा राम्रो मान थिएन। L4 मध्यम मिल्छ।"),
     "refs": ["4.2b", "5.4"]},
    {"id": "grace", "mission": "GRACE and GRACE-FO (NASA/DLR, NASA/GFZ)",
     "instrument": "twin satellites measuring Earth's gravity (microwave ranging; a laser ranging test on GRACE-FO)",
     "dataset": "JPL mascon CRI RL06.3 v04 (about 300 km)", "kind": "satellite",
     "job": T("The region's stored-water trend.", "क्षेत्रमा सञ्चित पानीको प्रवृत्ति।"),
     "checked": T("The trend is clear. No well data checked it.", "प्रवृत्ति स्पष्ट छ। इनारको नापले जाँचेको छैन।"),
     "refs": ["3.16"]},
    {"id": "ecostress", "mission": "ECOSTRESS on the International Space Station (NASA)",
     "instrument": "PHyTIR thermal infrared radiometer",
     "dataset": "ECO_L2T_LSTE and ECO_L4T_ESI, V003 first, V002 where V003 lacks a pass (70 m)", "kind": "satellite",
     "job": T("A check on crop water stress.", "बालीको पानी तनावको जाँच।"),
     "checked": T("Too few clear passes to decide.", "निर्णय गर्न बादलरहित तस्बिर पर्याप्त छैनन्।"),
     "refs": ["4.2e"]},
    {"id": "srtm", "mission": "SRTM on Space Shuttle Endeavour (NASA/NGA, 2000)", "instrument": "C-band radar interferometry",
     "dataset": "NASADEM_HGT v001 (SRTM reprocessed, 30 m)", "kind": "satellite",
     "job": T("Field height and slope; low ground.", "खेतको उचाइ र भिरालोपन; होचो जमिन।"),
     "checked": T("Low ground is below its error. We say can't tell.",
                  "जमिनको होचोपन यसको त्रुटिभन्दा सानो छ। त्यसैले 'भन्न सकिँदैन' भन्छौं।"),
     "refs": ["3.20"]},
    {"id": "ceres", "mission": "CERES on Terra, Aqua, Suomi NPP and NOAA-20 (NASA), via NASA POWER",
     "instrument": "CERES broadband radiometers (with geostationary imagers in SYN1deg)",
     "dataset": "CERES SYN1deg Ed4.2 sunshine in NASA POWER (1°); FLASHFlux for the latest months", "kind": "satellite",
     "job": T("Sunshine for the water the field loses.", "खेतले गुमाउने पानीका लागि घाम।"),
     "checked": T("Our evaporation matches FAO-56's worked examples.", "हाम्रो वाष्पीकरण FAO-56 का उदाहरणसँग मिल्छ।"),
     "refs": ["2.1b", "4.2d"]},
    {"id": "merra2", "mission": "MERRA-2 and GEOS-IT (NASA GMAO), via NASA POWER",
     "instrument": "a weather model that assimilates many satellites (reanalysis), not one instrument",
     "dataset": "NASA POWER daily API v2.10.3, community AG (0.5 x 0.625°)", "kind": "model",
     "job": T("Temperature, humidity and wind.", "तापक्रम, आर्द्रता र हावा।"),
     "checked": T("Temperatures corrected to Kathmandu Airport. Tested on years kept aside.",
                  "तापक्रम काठमाडौं विमानस्थलसँग मिलाइयो। छुट्याइएका वर्षमा जाँचियो।"),
     "refs": ["3.8", "3.11", "3.11b"]},
    {"id": "worldcover", "mission": "Sentinel-1 and Sentinel-2 (ESA Copernicus), behind ESA WorldCover",
     "instrument": "C-SAR radar and MSI", "dataset": "ESA WorldCover 10 m 2021 v200, cropland class", "kind": "satellite",
     "job": T("Finds farmland. It picked the sample field.", "खेतीयोग्य जमिन भेट्छ। नमुना खेत यसैले छान्यो।"),
     "checked": T("Its first pick was a building site.", "यसको पहिलो छनोट निर्माणस्थल थियो।"),
     "refs": ["1.4", "3.23"]},
    {"id": "chirps", "mission": "CHIRPS v3.0 (Climate Hazards Center, UC Santa Barbara)",
     "instrument": "geostationary thermal infrared (cold-cloud time) blended with rain gauges; days split with ERA5",
     "dataset": "CHIRPS v3.0 daily, rnl (0.05°)", "kind": "satellites and gauges",
     "job": T("Checks NASA's rain. Never the model's rain.", "नासाको वर्षा जाँच्छ। मोडेलको वर्षा होइन।"),
     "checked": T("It shows no 2017 jump.", "यसमा २०१७ को उफ्राइ छैन।"),
     "refs": ["3.9b", "3.22b"]},
    {"id": "gldas", "mission": "GLDAS-2.1 (NASA GSFC)",
     "instrument": "Noah land model driven by GDAS weather, AGRMET satellite radiation and GPCP v1.3 rain "
                   "(satellites and gauges)",
     "dataset": "GLDAS_NOAH025_M v2.1 (0.25°, monthly)", "kind": "model",
     "job": T("Checks the model's soil water and water use.", "मोडेलको माटोको पानी र पानी खपत जाँच्छ।"),
     "checked": T("Weak agreement. Its rain backs our fix.", "कमजोर मेल। यसको वर्षाले हाम्रो सुधारलाई साथ दिन्छ।"),
     "refs": ["4.2d"]},
    {"id": "nexgddp", "mission": "NEX-GDDP-CMIP6 (NASA), climate models, not satellites",
     "instrument": "CMIP6 global climate models, bias-corrected and downscaled to observations",
     "dataset": "NEX-GDDP-CMIP6 v2.0 daily (0.25°), SSP2-4.5 and SSP5-8.5", "kind": "model",
     "job": T("Climate change by 2040.", "२०४० सम्मको जलवायु परिवर्तन।"),
     "checked": T("Changes fit published ranges for Nepal.", "परिवर्तन नेपालका प्रकाशित दायराभित्र पर्छन्।"),
     "refs": ["4.7"]},
]

GAEZ_LINK = "https://gaez.fao.org/"
RESOURCES = [
    {"name": "SMAP", "status": "used",
     "how": T("Checks the model's soil water. Sets the model's starting doubt.",
              "मोडेलको माटोको पानी जाँच्छ। मोडेलको सुरुको शङ्का तय गर्छ।")},
    {"name": "GPM IMERG", "status": "used",
     "how": T("The model's daily rain, fixed from 2017.", "मोडेलको दैनिक वर्षा, २०१७ देखि सच्याइएको।")},
    {"name": "Landsat and MODIS/VIIRS (reflectance, NDVI, vegetation indices)", "status": "used",
     "how": T("Landsat, in HLS: field greenness. MODIS: compared only. VIIRS: not used.",
              "ल्यान्डस्याट, HLS मा: खेतको हरियाली। मोडिस: तुलना मात्र। VIIRS: प्रयोग भएन।")},
    {"name": "NASA POWER", "status": "used",
     "how": T("Temperature, humidity, wind and sunshine. Its rain is for checks only.",
              "तापक्रम, आर्द्रता, हावा र घाम। यसको वर्षा जाँचका लागि मात्र।")},
    {"name": "SRTM", "status": "used",
     "how": T("Field height and slope, through NASADEM.", "खेतको उचाइ र भिरालोपन, NASADEM बाट।")},
    {"name": "ECOSTRESS", "status": "used",
     "how": T("A check on crop stress. Too few clear passes.", "बालीको तनावको जाँच। बादलरहित तस्बिर धेरै कम।")},
    {"name": "USDA Ag Data Commons", "status": "not used",
     "how": T("Its data cover the United States, not Nepal.", "यसको तथ्याङ्क अमेरिकाको हो, नेपालको होइन।")},
    {"name": "Web Soil Survey", "status": "equivalent", "instead": "ISRIC SoilGrids 2.0 (250 m, world)",
     "how": T("United States only. We use SoilGrids, a world soil map.",
              "अमेरिका मात्र। हामी विश्वको माटो नक्सा SoilGrids प्रयोग गर्छौं।")},
    {"name": "Cropland Data Layer (CropScape)", "status": "equivalent", "instead": "ESA WorldCover 10 m 2021 v200",
     "how": T("United States only. We use ESA WorldCover cropland.",
              "अमेरिका मात्र। हामी ESA WorldCover को खेतीयोग्य जमिन प्रयोग गर्छौं।")},
    {"name": "PRISM", "status": "equivalent",
     "instead": "DHM (Government of Nepal) 1991-2020 normals and 2025 monthly bulletins",
     "how": T("United States only. We use Nepal's DHM rain records.",
              "अमेरिका मात्र। हामी नेपालको DHM वर्षा अभिलेख प्रयोग गर्छौं।")},
    {"name": "USDA NRCS SSURGO/STATSGO2", "status": "equivalent", "instead": "ISRIC SoilGrids 2.0 (250 m, world)",
     "how": T("United States only. We use SoilGrids instead.", "अमेरिका मात्र। सट्टामा हामी SoilGrids प्रयोग गर्छौं।")},
    {"name": "NAIP", "status": "not used",
     "how": T("Aerial photos of the United States only.", "अमेरिकाका हवाई तस्बिर मात्र।")},
    {"name": "USGS NLCD", "status": "equivalent", "instead": "ESA WorldCover 10 m 2021 v200",
     "how": T("United States only. We use ESA WorldCover instead.",
              "अमेरिका मात्र। सट्टामा हामी ESA WorldCover प्रयोग गर्छौं।")},
    {"name": "NLDAS/GLDAS", "status": "used",
     "how": T("GLDAS checks soil water and water use. NLDAS covers North America only.",
              "GLDAS ले माटोको पानी र खपत जाँच्छ। NLDAS उत्तर अमेरिका मात्र।")},
    {"name": "FAO GAEZ", "status": "not used", "label": "linked as a reference, data not used", "link": GAEZ_LINK,
     "how": T("Its licence is non-commercial and share-alike. So we only link it, for checking locally.",
              "यसको इजाजतपत्र गैर-व्यावसायिक र सेयर-अलाइक छ। त्यसैले स्थानीय जाँचका लागि लिङ्क मात्र।")},
    {"name": "CoCoRaHS", "status": "equivalent", "instead": "DHM (Government of Nepal) monthly bulletins, 2025",
     "how": T("Volunteer gauges in North America. We use DHM's gauges.",
              "उत्तर अमेरिकाका स्वयंसेवी मापक। हामी DHM का मापक प्रयोग गर्छौं।")},
    {"name": "USGS NWIS", "status": "not used",
     "how": T("United States water data only. We have no Nepal well records yet.",
              "अमेरिकाको पानी तथ्याङ्क मात्र। हामीसँग नेपालका इनारको अभिलेख अझै छैन।")},
    {"name": "USDA AMS Market News", "status": "not used",
     "how": T("United States prices. We show no money figures.", "अमेरिकी मूल्य। हामी पैसाको अङ्क देखाउँदैनौं।")},
    {"name": "USDA NASS QuickStats", "status": "equivalent", "instead": "FAOSTAT QCL, Nepal's national yields",
     "how": T("United States yields. We use FAOSTAT for Nepal.",
              "अमेरिकाको उब्जनी। नेपालका लागि हामी FAOSTAT प्रयोग गर्छौं।")},
    {"name": "OpenET", "status": "not used",
     "how": T("It covers the United States. We compute water use with FAO-56.",
              "यसले अमेरिका समेट्छ। हामी FAO-56 ले पानी खपत निकाल्छौं।")},
    {"name": "USFS LANDFIRE", "status": "not used",
     "how": T("United States fire and vegetation maps only.", "अमेरिकाका आगो र वनस्पति नक्सा मात्र।")},
    {"name": "GEDI", "status": "not used",
     "how": T("It measures forest height, not low crops.", "यसले वनको उचाइ नाप्छ, होचो बाली होइन।")},
    {"name": "Copernicus Sentinel-2 (ESA)", "status": "used",
     "how": T("Inside HLS greenness and ESA WorldCover.", "HLS हरियाली र ESA WorldCover भित्र।")},
    {"name": "ERA5 (ECMWF reanalysis)", "status": "not used",
     "how": T("Not fetched. It only splits CHIRPS's days, a check.",
              "ल्याइएन। यसले चिर्प्सका दिन मात्र छुट्याउँछ, जाँचका लागि।")},
]


# --- assembling the page ---------------------------------------------------------------------------------------------

SECTIONS = [
    ("rain", T("The rain gauges that vanished", "हराएका वर्षा मापक"),
     ["gauge_weight", "gauge_stations", "rain_jump", "rain_fixed"]),
    ("seasons", T("Your field's seasons from space", "अन्तरिक्षबाट खेतका बाली याम"), ["seasons_from_space", "cover_sure", "crop_months"]),
    ("checks", T("Our model against real records", "हाम्रो मोडेल र साँचो अभिलेख"),
     ["events", "dhm_2025", "other_checks", "best_worst_years"]),
    ("groundwater", T("Water under the whole region", "पूरै क्षेत्रको जमिनमुनिको पानी"), ["groundwater"]),
    ("probe", T("The soil probe", "माटो जाँच्ने यन्त्र"), ["probe_bench"]),
    ("area", T("Farms around the field", "खेत वरिपरिका खेत"), ["area_map"]),
    ("future", T("Harvests by 2040", "२०४० सम्मको उब्जनी"), ["outlook_2040"]),
    ("computer", T("How the computer helped", "कम्प्युटरले कसरी सघायो"),
     ["season_methods", "cover_sure", "field_memory", "ai_words"]),
    ("offline", T("Using it with no internet", "इन्टरनेट बिना चलाउने"), ["offline_use"]),
]


def input_paths(field):
    c, k = f"data/clean/{field}", f"data/checks/{field}"
    return {
        "gauge": f"{c}/gauge_evidence.parquet", "gpm": f"{c}/gpm.parquet", "chirps": f"{c}/chirps.parquet",
        "weather": f"{c}/weather.parquet", "grace": f"{c}/grace.parquet", "greenness": f"{c}/greenness_field.parquet",
        "normals": "config/dhm_normals_1991_2020.csv", "known_events": "config/known_events.yaml",
        "diary_seasons": f"{k}/diary_seasons.json", "rain_vs_dhm": f"{k}/rain_vs_dhm_2025.json",
        "smap": f"{k}/smap_vs_twin.json", "gldas": f"{k}/gldas_check.json", "hls": f"{k}/twin_vs_hls.json",
        "fao": f"{k}/faostat_check.json", "eco": f"{k}/ecostress_check.json", "memory": f"{k}/field_memory.json",
        "future": f"{k}/future.json", "area_check": f"{k}/area_map.json",
        "field_json": f"site/data/fields/{field}.json", "area_site": f"site/data/area/{field}.json",
        "words": "site/data/words.json", "field_config": f"config/fields/{field}.yaml",
        "bench": "data/checks/probe/bench.json", "scorecard": f"{k}/scorecard.json",
        "weather_ahead": f"{k}/weather.json",
    }


def load_inputs(repo, field):
    """Read every input (I/O). The probe's bench file is optional; everything else must exist."""
    repo = Path(repo)
    paths = input_paths(field)
    out = {"field": field, "paths": paths}
    for key, rel in paths.items():
        p = repo / rel
        if key in ("bench", "scorecard", "weather_ahead", "eco"):   # eco: not possible on a farm smaller than 70 m
            out[key] = json.loads(p.read_text()) if p.exists() else None
            continue
        if not p.exists():
            raise FileNotFoundError(rel)
        if rel.endswith(".parquet"):
            out[key] = pd.read_parquet(p)
        elif rel.endswith(".csv"):
            out[key] = pd.read_csv(p)
        elif rel.endswith(".yaml"):
            out[key] = yaml.safe_load(p.read_text())
        else:
            out[key] = json.loads(p.read_text())
    from pipeline.export.build_simple import calendars_of
    out["calendars"] = calendars_of(field)          # the field's crop calendars (fix A4: crop_months)
    return out


def _region_km(field_json):
    for s in field_json.get("sources", []):
        if s["name"].startswith("GRACE"):
            m = re.search(r"(\d[\d,]*)\s*km", s.get("resolution", ""))
            if m:
                return m.group(1)
    return "300"


def build_story(inp, generated):
    """The whole page from loaded inputs (pure)."""
    field = inp["field"]
    p = inp["paths"]
    fj = inp["field_json"]
    words = inp["words"]
    month_words = words["shared"]["months"]
    plan_names = next(s for s in words["screens"] if "plan" in s.get("labels", {}))["labels"]["plan"]["items"]

    c_weight, by = chart_gauge_weight(inp["gauge"])
    c_stations = chart_gauge_stations(inp["gauge"], by)
    c_jump, normal = chart_rain_jump(inp["gpm"], inp["chirps"], inp["gauge"], inp["normals"], by)
    c_fixed, level_ratio = chart_rain_fixed(inp["weather"], normal, by)
    c_seasons, _ = chart_seasons(inp["greenness"], inp["diary_seasons"])
    c_sure = chart_cover_sure(fj["diary"]["months"], month_words)
    c_months = chart_crop_months(fj, inp["calendars"], inp["diary_seasons"], words["shared"]["bs_months"])
    c_events, ev_summary = chart_events(fj["replay"]["current"], inp["known_events"], inp.get("scorecard"))
    c_dhm = chart_dhm_2025(inp["rain_vs_dhm"], rain_is_tuned(field))
    c_other, _ = chart_other_checks(inp["smap"], inp["gldas"], inp["hls"], inp["fao"], inp["eco"])
    c_best = chart_best_worst()
    region_km = _region_km(fj)
    c_gw = chart_groundwater(inp["grace"], fj["diary"]["groundwater"], region_km)
    c_probe = chart_probe(inp["bench"])
    c_area = chart_area(inp["area_site"], inp["area_check"], field)
    c_future, _ = chart_outlook(fj, plan_names)
    c_methods = chart_season_methods(fj["method"])
    c_memory = chart_field_memory(inp["memory"])
    c_words = chart_ai_words(words, fj)
    charts = [c_weight, c_stations, c_jump, c_fixed, c_seasons, c_sure, c_months, c_events, c_dhm, c_other, c_best, c_gw,
              c_probe, c_area, c_future, c_methods, c_memory, c_words, chart_offline()]

    bench_used = [p["bench"]] if bench_is_real(inp["bench"]) else ["robot/CUPS_PROTOCOL.md", "config/rules.yaml"]
    inputs = {
        "gauge_weight": [p["gauge"]], "gauge_stations": [p["gauge"]],
        "rain_jump": [p["gpm"], p["chirps"], p["gauge"], p["normals"]],
        "rain_fixed": [p["weather"], p["normals"]],
        "seasons_from_space": [p["greenness"], p["diary_seasons"]],
        "cover_sure": [p["field_json"], p["words"]],
        "crop_months": [p["field_json"], p["diary_seasons"], "config/crops.json", "config/rules.yaml"],
        "events": [p["field_json"], p["known_events"]],
        "dhm_2025": [p["rain_vs_dhm"]],
        "other_checks": [p["smap"], p["gldas"], p["hls"], p["fao"], p["eco"]],
        "best_worst_years": [f"config/fields/{field}.yaml"],
        "groundwater": [p["grace"], p["field_json"]],
        "probe_bench": bench_used,
        "area_map": [p["area_site"], p["area_check"]],
        "outlook_2040": [p["field_json"], p["words"]],
        "season_methods": [p["field_json"]],
        "field_memory": [p["memory"]],
        "ai_words": [p["words"], p["field_json"], "SI_LOG.md"],
        "offline_use": ["site/sw.js", "scripts/build_offline.py"],
        "compliance": [p["scorecard"], "config/rules.yaml"],
        "report_card": [p["field_json"], p["diary_seasons"], p["area_check"], p["rain_vs_dhm"], p["weather"],
                        p["normals"], p["fao"], p["known_events"], p["future"], "VALIDATION.md"] + bench_used[:1],
        "satellites": ["DATA_AUDIT.md", "CREDITS.md", "VALIDATION.md"],
        "resources": ["DATA_AUDIT.md", "CREDITS.md"],
    }

    sd = inp["diary_seasons"]["season_date_differences_days"]
    thresholds = inp["area_check"]["all_numbers_by_threshold"]
    lab = inp["rain_vs_dhm"]["labels"]
    rv = inp["rain_vs_dhm"]["against_three_gauges"]
    diary = fj["diary"]
    ctx = {
        "season_matches": min(v["matched"] for v in sd.values()),
        # the largest median start-date difference between a method and the chosen one, rounded half up
        "season_start_diff_days": int(math.floor(max(v["start"] for v in sd.values()) + 0.5)),
        "bare_days": diary["bare_days"],
        "bare_lo": int(round(min(t["median_bare_days"] for t in thresholds.values()))),
        "bare_hi": int(round(max(t["median_bare_days"] for t in thresholds.values()))),
        "rain_final_ratio": rv["imerg_final_months"]["twin_rain"]["ratio"],
        "rain_late_ratio": rv["imerg_late_months"]["twin_rain"]["ratio"],
        "rain_level_ratio": level_ratio, "break_year": by,
        "n_final_months": len(lab["imerg_final_months"]), "n_late_months": len(lab["imerg_late_months"]),
        "fao": inp["fao"]["rain"]["corrected"],
        "placeholder": bool(inp["field_config"].get("placeholder", False)),
        "events": ev_summary, "scorecard": inp.get("scorecard"), "rain_tuned": rain_is_tuned(field), "groundwater": diary["groundwater"], "region_km": region_km,
        "monsoon_start": diary["monsoon_start"], "shift_low": diary.get("shift_days_low"),
        "shift_high": diary.get("shift_days_high"), "bench": inp["bench"],
        "n_models": len(fj["future"].get("models", [])), "plausible": inp["future"]["plausibility"]["all_inside"],
        "future_year": fj["future"]["years"][-1],
        "weather_ahead": (inp.get("weather_ahead") or {}).get("checks"),
    }
    ys = yardsticks()
    order = [c["id"] for c in charts]
    for _, _, ids in SECTIONS:
        assert set(ids) <= set(order), ids
    return {
        "generated": generated, "field": field, "placeholder": ctx["placeholder"], "ne_review": NE_REVIEW,
        "sections": [{"id": sid, "title": title, "charts": ids} for sid, title, ids in SECTIONS],
        "inputs": inputs, "charts": charts, "report_card": report_card(ctx),
        "compliance": (rows := compliance(inp.get("scorecard"), ys)),
        "limits": limits_block(rows),
        "verify_how": verify_how(rows, ys),
        "compliance_note": T(f"Verified means right at least {ys['pct']} times in 100, on {ys['nmin']} or more checks. "
                             "The range shows how sure that number is.",
                             f"प्रमाणित भनेको कम्तीमा {ys['nmin']} जाँचमा १०० मा {ys['pct']} पटक सही। दायराले त्यो अङ्क कति पक्का छ देखाउँछ।"),
        "satellites": satellites_for(field, inp["eco"]), "resources": RESOURCES,
    }


# cards whose 'checked' line was tested on the Bhaktapur demo field only: what they say for another field (2026-11-15,
# Kharipati: its own three season methods agree, VALIDATION 3.36), and ECOSTRESS where no 70 m pixel centre is in the field
ELSEWHERE = {"landsat": T("Three season methods agree here too.", "यहाँ पनि तीन तरिका मिल्छन्।"),
             "modis": T("Checked against HLS on the Bhaktapur field.", "भक्तपुरको खेतमा HLS सँग जाँचिएको।"),
             "worldcover": T("It maps the farmland around this farm.", "यसले यो खेत वरिपरिको खेतीयोग्य जमिन देखाउँछ।")}
NO_ECOSTRESS = T("Not possible: the farm is too small.", "सम्भव छैन: खेत धेरै सानो छ।")


def satellites_for(field, eco):
    return [{**s, "checked": NO_ECOSTRESS} if s["id"] == "ecostress" and eco is None else
            {**s, "checked": ELSEWHERE[s["id"]]} if field != "demo" and s["id"] in ELSEWHERE else s for s in SATELLITES]


def load_schema():
    return json.loads(SCHEMA.read_text())


def validate_story(story):
    """Problems as strings; [] when the page matches story_schema.json."""
    v = Draft202012Validator(load_schema())
    return [f"{'/'.join(str(x) for x in e.absolute_path)}: {e.message}" for e in v.iter_errors(story)]


def markdown_tables(story):
    """The report card, the satellite inventory and the resource list as Markdown (for VALIDATION and DATA_AUDIT)."""
    out = ["| Thing | Confidence | Why | VALIDATION rows |", "| --- | --- | --- | --- |"]
    for r in story["report_card"]:
        out.append(f"| {r['thing']['en']} | **{r['confidence']}** | {r['why']['en']} | {', '.join(r['refs'])} |")
    out += ["", "| Mission | Instrument | Dataset | Job | How we checked it | Rows |", "| --- | --- | --- | --- | --- | --- |"]
    for s in story["satellites"]:
        out.append(f"| {s['mission']} | {s['instrument']} | {s['dataset']} | {s['job']['en']} | {s['checked']['en']} | "
                   f"{', '.join(s['refs'])} |")
    out += ["", "| Resource | Status | How | Instead |", "| --- | --- | --- | --- |"]
    for r in story["resources"]:
        status = r["status"] + (f" ({r['label']}: {r['link']})" if r.get("label") else "")
        out.append(f"| {r['name']} | {status} | {r['how']['en']} | {r.get('instead', '')} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--field", default=None, help="default: rules.yaml site_main_field (the field the site opens first)")
    ap.add_argument("--out", default=None, help="default site/data/story.json")
    ap.add_argument("--generated", default=date.today().isoformat())
    ap.add_argument("--markdown", action="store_true", help="print the report card and inventories as Markdown")
    a = ap.parse_args(argv)
    if a.field is None:
        from pipeline.fetch.rules import load_rules
        a.field = load_rules()["site_main_field"]
    story = build_story(load_inputs(REPO, a.field), a.generated)
    problems = validate_story(story)
    if problems:
        print("story.json does not match story_schema.json:\n  " + "\n  ".join(problems[:20]), file=sys.stderr)
        return 1
    if a.markdown:
        print(markdown_tables(story))
        return 0
    out = Path(a.out) if a.out else REPO / "site" / "data" / "story.json"
    text = json.dumps(story, ensure_ascii=False, separators=(",", ":")) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(text)
    tmp.replace(out)
    print(f"wrote {out.relative_to(REPO) if out.is_relative_to(REPO) else out}: {len(story['charts'])} charts, "
          f"{len(text.encode()) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
