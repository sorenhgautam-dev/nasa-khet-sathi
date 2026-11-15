"""Weather ahead (owner, 2026-11-14 evening; rules.yaml weather_ahead): what usually happened on this field in each
approximate Bikram Sambat month of its own record, which danger hit which crop most often, and one tip. Never a
forecast. Pure functions: the caller passes the weather table, the rain versions, the plan crops and the rules.

A block starts on the 15th of a Gregorian month and is keyed by that month ('Nov' = Mangsir, 15 Nov to 14 Dec).
A crop window is two MM-DD dates, the same every year, counted in a 365-day year.
"""
import math
from statistics import median

import numpy as np
import pandas as pd

from pipeline.diary.months import frost_band, tercile_words
from pipeline.diary.trends import hot_day_flags, mk_sen

KEYS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
KIND_ORDER = ["cold", "heat", "dry_spell", "big_rain"]
_T = pd.Timestamp("2002-01-01")   # a 365-day year for MM-DD arithmetic


def blocks(start_day):
    out = []
    for m in range(1, 13):
        nxt = m % 12 + 1
        out.append({"key": KEYS[m - 1], "from": f"{m:02d}-{start_day:02d}", "to": f"{nxt:02d}-{start_day - 1:02d}"})
    return out


def block_years(month, start_day, d0, d1, n):
    """The years (a block's year is the year it starts) of the n latest blocks lying wholly in d0..d1."""
    ok = []
    for y in range(d0.year, d1.year + 1):
        a = pd.Timestamp(y, month, start_day)
        b = pd.Timestamp(y + (month == 12), month % 12 + 1, start_day - 1)
        if a >= d0 and b <= d1:
            ok.append(y)
    return ok[-n:]


def _mmdd(ts):
    return f"{ts.month:02d}-{ts.day:02d}"


def days_after(sow, a, b):
    """(first, last) MM-DD of days a..b after the sowing day (day 0), in a 365-day year."""
    s = pd.Timestamp(f"2002-{sow}")
    return _mmdd(s + pd.Timedelta(int(a), unit="D")), _mmdd(s + pd.Timedelta(int(b), unit="D"))


def stage_window(crop, stages, stage):
    """A plan crop's FAO-56 stage window: 'season', 'initial' (days 0..ini-1), 'mid_late' (from day ini + dev to the
    crop's last day) or 'late' (the last `late` days, ending on the crop's last day, as rain_risk.harvest_window)."""
    if stage == "season":
        return crop["start"], crop["end"]
    if stage == "initial":
        return days_after(crop["start"], 0, int(stages["ini"]) - 1)
    if stage == "mid_late":
        return days_after(crop["start"], int(stages["ini"]) + int(stages["dev"]), 0)[0], crop["end"]
    end = pd.Timestamp(f"2002-{crop['end']}")
    return _mmdd(end - pd.Timedelta(int(stages["late"]) - 1, unit="D")), crop["end"]


def _doys(first, last):
    """Day numbers 1..365 of an MM-DD range in a 365-day year (it may cross 1 January)."""
    a, b = pd.Timestamp(f"2002-{first}").dayofyear, pd.Timestamp(f"2002-{last}").dayofyear
    return set(range(a, b + 1)) if a <= b else set(range(a, 366)) | set(range(1, b + 1))


def attaches(block, window):
    """The window counts in the block when the block holds at least half of the window's days, or the window covers at
    least half of the block's days (rules.yaml weather_ahead.attach)."""
    bd, wd = _doys(block["from"], block["to"]), _doys(*window)
    both = len(bd & wd)
    return 2 * both >= len(wd) or 2 * both >= len(bd)


def _md(dates):
    d = pd.DatetimeIndex(dates)
    return d.month.to_numpy() * 100 + d.day.to_numpy()


def in_window(dates, window):
    md = _md(dates)
    f, t = (int(x.replace("-", "")) for x in window)
    return (md >= f) & (md <= t) if f <= t else (md >= f) | (md <= t)


def block_of(dates, start_day):
    """(block month, block year) of every day."""
    d = pd.DatetimeIndex(dates)
    m, y = d.month.to_numpy(), d.year.to_numpy()
    early = d.day.to_numpy() < start_day
    bm = np.where(early, (m - 2) % 12 + 1, m)
    by = np.where(early & (m == 1), y - 1, y)
    return bm, by


def risky(values, rule):
    v = np.asarray(values, float)
    if "above_c" in rule:
        return v > rule["above_c"]
    if "at_or_above_c" in rule:
        return v >= rule["at_or_above_c"]
    if "below_c" in rule:
        return v < rule["below_c"]
    return v <= rule["at_or_below_c"]


def longest_run(flags):
    best = run = 0
    for f in np.asarray(flags, bool):
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def year_values(w, column, rule, kind, month, start_day, years, window, big_mm=20.0, dry_mm=1.0):
    """{year: {hit, n}} over the days of each block instance that lie in the window. cold/heat: hit when one day passes
    the rule, n = such days; dry_spell: hit when every tested day has rain under dry_mm, n = the longest dry run;
    big_rain: hit when a day has big_mm or more, n = such days."""
    bm, by = block_of(w["date"], start_day)
    inside = in_window(w["date"], window) & (bm == month)
    v = w[column].to_numpy(float)
    out = {}
    for y in years:
        x = v[inside & (by == y)]
        if np.isnan(x).any():
            raise ValueError(f"missing {column} in the {month} block of {y}")
        if kind == "dry_spell":
            dry = x < dry_mm
            out[int(y)] = {"hit": bool(len(x) and dry.all()), "n": longest_run(dry)}
        elif kind == "big_rain":
            n = int((x >= big_mm).sum())
            out[int(y)] = {"hit": n > 0, "n": n}
        else:
            n = int(risky(x, rule).sum())
            out[int(y)] = {"hit": n > 0, "n": n}
    return out


def typical_worst(by_year, worst=3):
    vals = sorted(by_year.values())
    return {"typical": int(math.floor(median(vals) + 0.5)),
            "worst": [{"year": int(y), "days": int(v)}
                      for y, v in sorted(by_year.items(), key=lambda kv: (-kv[1], -int(kv[0])))[:worst]]}


def often(n, of):
    if n <= 0:
        return None
    return "most" if 2 * n >= of else "some"


def rank(dangers, crop_order):
    keep = [d for d in dangers if d["years"] >= 1]
    pos = {c: i for i, c in enumerate(crop_order)}
    return sorted(keep, key=lambda d: (-d["years"], KIND_ORDER.index(d["kind"]), pos.get(d["crop"], len(pos))))


def change_word(values_by_year, alpha):
    v = {int(y): float(x) for y, x in values_by_year.items() if x is not None and np.isfinite(x)}
    if len(v) < 4 or len(set(v.values())) == 1:
        return "cant_tell"
    t = mk_sen(v, alpha)
    if t["p"] < alpha:
        return "more_common" if t["slope_per_year"] > 0 else "less_common" if t["slope_per_year"] < 0 else "about_same"
    return "about_same"


def clean_years(years, month, bad):
    """The block years with no day in the bad years (the December block ends in the next year)."""
    bad = set(int(b) for b in bad)
    return [y for y in years if y not in bad and not (month == 12 and y + 1 in bad)]


def words12(values12, words):
    return tercile_words(values12, words)


def drying(et0, wind, sun, words):
    """How fast the soil dries in each of the twelve blocks (rules.yaml soil_drying): the word from the thirds of the block
    means of FAO-56 ET0, and the wind and sun icons when the block's mean wind or sunshine is among the four highest."""
    top = (False, False, True)
    return [{"et0_mm_day": round(float(e), 1), "word": d, "wind": bool(a), "sun": bool(b)}
            for e, d, a, b in zip(et0, words12(et0, words), words12(wind, top), words12(sun, top))]


def _candidates(crops, lib, r):
    """[(check, kind, crop dict, window, column, rule)] for every plan crop: the sourced temperature limits of wheat and
    potato (heat_clock), and dry spells and big rain for every crop (weather_ahead.dangers)."""
    hc = r["heat_clock"]
    out = []
    for c in crops:
        st = lib[c["crop"]]["stages_days"]
        if c["crop"] == "potato":
            out.append(("potato_cold", "cold", c, stage_window(c, st, "season"), hc["potato_cold"]["temperature"], hc["potato_cold"]))
            out.append(("potato_heat", "heat", c, stage_window(c, st, "season"), hc["potato_heat"]["temperature"], hc["potato_heat"]))
        if c["crop"] == "wheat":
            fw, gw = hc["wheat_flower_window"], hc["wheat_floret_window"]
            out.append(("wheat_flower_frost", "cold", c, days_after(c["start"], fw["from_days_after_sowing"], fw["to_days_after_sowing"]),
                        hc["wheat_flower_frost"]["temperature"], hc["wheat_flower_frost"]))
            out.append(("wheat_floret_heat", "heat", c, days_after(c["start"], gw["from_days_after_sowing"], gw["to_days_after_sowing"]),
                        hc["wheat_floret_heat"]["temperature"], hc["wheat_floret_heat"]))
            out.append(("wheat_grain_heat", "heat", c, stage_window(c, st, "late"),
                        hc["wheat_grain_filling_heat"]["temperature"], hc["wheat_grain_filling_heat"]))
        out.append(("dry_spell", "dry_spell", c, stage_window(c, st, "mid_late"), "rain_mm", None))
        if c["crop"] != "rice":   # paddy is flooded at transplanting (owner, 2026-11-14 night): big rain at harvest only
            out.append(("big_rain_sowing", "big_rain", c, stage_window(c, st, "initial"), "rain_mm", None))
        out.append(("big_rain_harvest", "big_rain", c, stage_window(c, st, "late"), "rain_mm", None))
    return out


def build(w, rain_versions, crops, lib, r):
    """The 'weather' block and its per-year detail. w: date, tmax_c, tmin_c, tmin_frost_c, rain_mm (the central rain);
    rain_versions: {version: rain array on w's dates}; crops: the plan crops in plan order, each crop and sowing day once."""
    wa, tr, mo = r["weather_ahead"], r["trends"], r["months"]
    sd, n_years = int(wa["blocks"]["starts_on_day"]), 24
    w = w.sort_values("date").reset_index(drop=True)
    d0, d1 = w["date"].min(), w["date"].max()
    bm, by = block_of(w["date"], sd)
    dry_mm, big_mm, alpha = float(tr["dry_day_mm"]), float(tr["heavy_rain_mm"]), float(tr["alpha"])
    hd = tr["hot_day"]
    hot = hot_day_flags(pd.Series(w["tmax_c"].to_numpy(float), index=pd.DatetimeIndex(w["date"])),
                        hd["base_years"], hd["pct"], hd["window_days"])
    bad = r["power_rain"]["never_fill_years"]
    cands = _candidates(crops, lib, r)
    crop_order = []
    for c in crops:
        if c["crop"] not in crop_order:
            crop_order.append(c["crop"])

    out_blocks, detail = [], []
    rain_mean, temp_mean, dry_means = [], [], []
    for b in blocks(sd):
        m = KEYS.index(b["key"]) + 1
        years = block_years(m, sd, d0, d1, n_years)
        if len(years) != n_years:
            raise ValueError(f"the {b['key']} block has {len(years)} complete years, not {n_years}")
        sel = {y: (bm == m) & (by == y) for y in years}
        rain = {y: float(w["rain_mm"].to_numpy(float)[s].sum()) for y, s in sel.items()}
        vers = {k: float(median([float(np.asarray(v, float)[s].sum()) for s in sel.values()])) for k, v in rain_versions.items()}
        allm = np.any(np.vstack(list(sel.values())), axis=0)
        tmax, tmin = w["tmax_c"].to_numpy(float)[allm], w["tmin_c"].to_numpy(float)[allm]
        coldest = [float(w["tmin_frost_c"].to_numpy(float)[s].min()) for s in sel.values()]
        dry = {y: longest_run(w["rain_mm"].to_numpy(float)[s] < dry_mm) for y, s in sel.items()}
        rain_mean.append(float(np.mean(list(rain.values()))))
        temp_mean.append(float(np.mean((tmax + tmin) / 2)))
        dry_means.append([float(w[c].to_numpy(float)[allm].mean()) for c in ("et0_mm", "ws2m_ms", "rs_mj_m2_day")])
        cy = clean_years(years, m, bad)

        dangers, none, det = [], [], []
        for check, kind, c, win, col, rule in cands:
            if not attaches(b, win):
                continue
            yv = year_values(w, col, rule, kind, m, sd, years, win, big_mm, dry_mm)
            hits = [y for y in years if yv[y]["hit"]]
            d = {"check": check, "kind": kind, "crop": c["crop"], "sow": c["start"], "window": list(win),
                 "years": len(hits), "of": n_years, "often": often(len(hits), n_years), "hit_years": hits}
            if hits:
                if kind == "heat":
                    series = {y: int(hot[sel[y]].sum()) for y in cy}
                elif kind == "cold":
                    series = {y: yv[y]["n"] for y in cy}
                elif kind == "dry_spell":
                    series = dict(dry)
                else:
                    series = {y: yv[y]["n"] for y in years}
                d["change"] = change_word(series, alpha)
                d["change_basis"] = {"heat": "days above the local 90th percentile of Tmax in the block (TX90p), 2004 on",
                                     "cold": "nights past the limit in the tested days, 2004 on",
                                     "dry_spell": "the block's longest dry run",
                                     "big_rain": "days of 20 mm or more in the tested days"}[kind]
                d["tip"] = kind
                dangers.append(d)
            else:
                none.append({k: d[k] for k in ("check", "kind", "crop", "sow", "years", "of")})
            det.append({"check": check, "crop": c["crop"], "sow": c["start"], "by_year": {str(y): yv[y] for y in years}})
        ranked = rank(dangers, crop_order)
        out_blocks.append({
            "key": b["key"], "from": b["from"], "to": b["to"], "years": [years[0], years[-1]],
            "usual": {"rain_mm": {"median": round(median(rain.values()), 1), "low": round(min(rain.values()), 1),
                                  "high": round(max(rain.values()), 1),
                                  "versions": {k: round(v, 1) for k, v in vers.items()}},
                      "tmax_c": round(float(tmax.mean()), 1), "tmin_c": round(float(tmin.mean()), 1),
                      "frost": frost_band(float(median(coldest)), float(mo["frost_c"]), float(mo["frost_risk_c"]))},
            "dry_run": typical_worst(dry),
            "dangers": ranked,
            "none_seen": none,
        })
        detail.append({"key": b["key"], "rain_mm": {str(y): round(v, 1) for y, v in rain.items()},
                       "dry_run": {str(y): v for y, v in dry.items()}, "coldest_frost_c": dict(zip(map(str, years), coldest)),
                       "dangers": det})
    rw = words12(rain_mean, wa["rain_word"]["words"])
    tw = words12(temp_mean, wa["temperature_word"]["words"])
    dr = drying(*zip(*dry_means), r["soil_drying"]["word"]["words"])
    for i, blk in enumerate(out_blocks):
        blk["usual"]["rain"], blk["usual"]["temp"], blk["usual"]["drying"] = rw[i], tw[i], dr[i]
    return out_blocks, detail
