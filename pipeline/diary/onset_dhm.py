"""DHM's official monsoon onset dates as the record of a shift (owner, 2026-11-14; rules.yaml monsoon_onset_dhm).
Pure functions: the dates come in as {year: 'YYYY-MM-DD'} (scripts/run_onset_dhm.py reads config/dhm_onset_dates.csv).

- shift: Sen's slope of the onset's calendar day on the year x (last - first), with its 95% range and the Mann-Kendall
  p, as pipeline/diary/trends.py; 'no clear shift' when the range holds 0 or p >= alpha.
- start_window: the middle half of the years (25th-75th percentile, numpy linear, rounded to the day).
- late_years: onset strictly after the owner's 20 June.
- agrees: a cross-check record agrees with DHM ('no clear shift') when its slope range holds 0 and overlaps DHM's.
- words: plain English (at most 8 words a sentence) and Nepali drafts (Bikram Sambat first, approximate, marked 'तिर',
  Gregorian beside), every Nepali line for native-speaker review.
DHM's date is the monsoon entering eastern Nepal; it reaches Kathmandu a few days later.
"""
import numpy as np
import pandas as pd

from pipeline.diary import trends as tr
from pipeline.diary.onset_accumulation import calendar_day

NE_REVIEW = "needs native-speaker review"
_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
_MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]


def _mmdd(n):
    """Calendar day of a non-leap year -> 'MM-DD'."""
    return (pd.Timestamp("2001-01-01") + pd.Timedelta(int(n) - 1, unit="D")).strftime("%m-%d")


def record_days(dates, years):
    """{year: calendar day} for the years first..last of `years` that have a date."""
    first, last = years
    return {int(y): calendar_day(pd.Timestamp(d)) for y, d in dates.items() if d and first <= int(y) <= last}


def shift(days, alpha):
    """Sen's slope and range x (last - first year), Mann-Kendall p; clear only when the range excludes 0 and p < alpha."""
    t = tr.mk_sen(days, alpha)
    chg, low, high = tr.over_record(t, t["first"], t["last"])
    clear = bool((t["low"] > 0 or t["high"] < 0) and t["p"] < alpha)
    return {"shift_days": chg, "shift_days_low": low, "shift_days_high": high,
            "slope_per_year": round(t["slope_per_year"], 3), "low_per_year": round(t["low"], 3),
            "high_per_year": round(t["high"], 3), "p": round(t["p"], 3), "n": t["n"], "years": [t["first"], t["last"]],
            "clear": clear, "direction": ("earlier" if t["slope_per_year"] < 0 else "later") if clear else "no clear shift"}


def start_window(days, percentiles):
    """The usual start window: the percentiles of the calendar days, each rounded to the nearest day."""
    v = np.array(sorted(days.values()), float)
    lo, hi = (int(round(float(np.percentile(v, p)))) for p in percentiles)
    med = int(round(float(np.median(v))))
    return {"from_day": lo, "to_day": hi, "from": _mmdd(lo), "to": _mmdd(hi), "median": _mmdd(med),
            "percentiles": list(percentiles), "n": len(v)}


def late_years(dates, after):
    """Years whose onset falls strictly after `after` ('MM-DD'); years on that day itself are listed beside."""
    late, on = [], []
    for y, d in sorted(dates.items()):
        md = pd.Timestamp(d).strftime("%m-%d")
        if md > after:
            late.append(int(y))
        elif md == after:
            on.append(int(y))
    return {"after": after, "years": late, "count": len(late), "of": len(dates),
            "share": len(late) / len(dates) if dates else None, "on_the_day": on}


def agrees(t, t_dhm):
    """'No clear shift', as DHM: the record's slope range holds 0 and overlaps DHM's (days per year)."""
    return bool(t["low"] <= 0 <= t["high"] and max(t["low"], t_dhm["low"]) <= min(t["high"], t_dhm["high"]))


def bs_date(month, day, bs_names, start_day=15):
    """Approximate Bikram Sambat (month name, day) for a Gregorian month and day, each BS month taken to start on
    `start_day` of the Gregorian month it is named for in bs_names ({gregorian month number: BS name})."""
    if day >= start_day:
        return bs_names[month], day - start_day + 1
    prev = 12 if month == 1 else month - 1
    return bs_names[prev], day + _MONTH_DAYS[prev - 1] - start_day + 1


def ne_digits(text):
    return str(text).translate(_DIGITS)


def _en_range(a, b):
    (ma, da), (mb, db) = (map(int, x.split("-")) for x in (a, b))
    if ma == mb:
        return f"{da}–{db} {_EN_MONTHS[ma - 1]}"
    return f"{da} {_EN_MONTHS[ma - 1]}–{db} {_EN_MONTHS[mb - 1]}"


def _en_day(md):
    m, d = map(int, md.split("-"))
    return f"{d} {_EN_MONTHS[m - 1]}"


def _bs(md, bs_names, start_day):
    m, d = map(int, md.split("-"))
    name, n = bs_date(m, d, bs_names, start_day)
    return f"{name} {ne_digits(n)}"


def _greg_ne(md, greg_names):
    m, d = map(int, md.split("-"))
    return f"{greg_names[m]} {ne_digits(d)}"


def words(shift_res, window, late, xcheck, first_year, bs_names, greg_names, start_day=15):
    """Draft plain words for the diary ('diary_shift'), the 'Next 3 months' screen ('next3_rice') and the
    'How we know' page ('how_we_know'): {'en': [...], 'ne': [...], 'ne_review': ...} each."""
    all_agree = (not shift_res["clear"]) and all(xcheck.values())
    n_bad = sum(1 for ok in xcheck.values() if not ok)
    if all_agree:
        agree_en, agree_ne = ("Both satellite rain checks show no clear change.",
                              "भू-उपग्रहका दुवै वर्षा जाँचमा पनि स्पष्ट फरक देखिँदैन।")
    elif n_bad == 1:
        agree_en, agree_ne = "One satellite rain check does not agree.", "भू-उपग्रहको एउटा वर्षा जाँच मिल्दैन।"
    elif n_bad >= 2:
        agree_en, agree_ne = "The two satellite rain checks do not agree.", "भू-उपग्रहका दुवै वर्षा जाँच मिल्दैनन्।"
    else:
        agree_en, agree_ne = "The satellite rain checks show no change.", "भू-उपग्रहका वर्षा जाँचमा फरक देखिँदैन।"
    fy = ne_digits(first_year)
    if shift_res["clear"]:
        n = abs(round(shift_res["shift_days"]))
        way_en = shift_res["direction"]
        way_ne = "चाँडो" if way_en == "earlier" else "ढिलो"
        result_en = [f"The rains now start about {n} days {way_en}.",
                     f"Measured since {first_year}, in Nepal's weather office records."]
        result_ne = [f"मनसुन अहिले करिब {ne_digits(n)} दिन {way_ne} सुरु हुन्छ।",
                     f"नेपालको मौसम कार्यालयको अभिलेखमा सन् {fy} देखिको नाप।"]
    else:
        # owner, 2026-11-14 afternoon: exactly this sentence (rules.yaml monsoon_onset_dhm.words_rule)
        result_en = [f"No clear change since {first_year}, in Nepal's weather office records."]
        result_ne = [f"नेपालको मौसम कार्यालयको अभिलेखमा सन् {fy} यता स्पष्ट फरक छैन।"]
    diary = {"en": list(result_en), "ne": list(result_ne), "ne_review": NE_REVIEW}

    bs_from, bs_to = _bs(window["from"], bs_names, start_day), _bs(window["to"], bs_names, start_day)
    gf, gt = window["from"], window["to"]
    greg = (f"({_greg_ne(gf, greg_names)}–{ne_digits(int(gt[3:]))})" if gf[:2] == gt[:2]
            else f"({_greg_ne(gf, greg_names)}–{_greg_ne(gt, greg_names)})")
    when_ne = f"{bs_from} देखि {bs_to} तिर {greg}।"
    when_ne = [when_ne] if len(when_ne.split()) <= 8 else [f"{bs_from} देखि {bs_to} तिर।", f"अंग्रेजी मितिमा {greg.strip('()')}।"]
    after = late["after"]
    late_en = (f"In {late['of']} years, none came after {_en_day(after)}." if late["count"] == 0 else
               f"In {late['of']} years, {late['count']} came after {_en_day(after)}.")
    late_ne = (f"{ne_digits(late['of'])} वर्षमा एक पटक पनि ढिलो आएन।" if late["count"] == 0 else
               f"{ne_digits(late['of'])} वर्षमा {ne_digits(late['count'])} पटक ढिलो आयो।")
    next3_en = [f"Rains usually reach Nepal {_en_range(gf, gt)}.", "Here, they come a few days later.", late_en]
    next3_ne = ["मनसुन प्रायः यो बेला नेपाल आइपुग्छ।", *when_ne, "यहाँ केही दिनपछि आइपुग्छ।", late_ne,
                f"ढिलो भनेको {_bs(after, bs_names, start_day)} तिर ({_greg_ne(after, greg_names)}) पछि।"]
    if late["count"]:
        yrs = late["years"][:5]
        label = "Late year" if len(yrs) == 1 else "Late years"
        next3_en.append(f"{label}: {', '.join(str(y) for y in yrs)}.")
        next3_ne.append(f"ढिलो वर्ष: {', '.join(ne_digits(y) for y in yrs)}।")
    next3 = {"en": next3_en, "ne": next3_ne, "ne_review": NE_REVIEW}

    how_en = ["We tested two ways with satellite rain.", "Neither could show a change in timing.",
              "In 2017, rain gauges stopped feeding it.", "After that, its rain is not steady.",
              "So we use Nepal's official monsoon record.", *result_en,
              agree_en, "These records share some rain gauges."]
    how_ne = ["हामीले भू-उपग्रहको वर्षाबाट दुई तरिका जाँच्यौं।", "कुनैले पनि समयको फरक देखाउन सकेन।",
              "सन् २०१७ मा वर्षा मापन केन्द्रको जानकारी रोकियो।", "त्यसपछि भू-उपग्रहको वर्षा भरपर्दो रहेन।",
              "त्यसैले हामी नेपाल सरकारको आधिकारिक मनसुन अभिलेख हेर्छौं।",
              *result_ne, agree_ne,
              "यी अभिलेखले केही वर्षा मापन केन्द्र साझा गर्छन्।"]
    return {"diary_shift": diary, "next3_rice": next3,
            "how_we_know": {"en": how_en, "ne": how_ne, "ne_review": NE_REVIEW}}
