"""Owner decision B (2026-11-11): cross-source rain spike check. Range guards cannot catch a value that
is physically possible but wrong (POWER: 233.7 mm on 2025-03-01, station 3.8 mm). Flag any day where
one source exceeds min_mm and is more than `ratio` times another source. Flags are reported in the data
cards; nothing is deleted. Thresholds live in config/rules.yaml. Pure function.
"""
from itertools import permutations

import pandas as pd


def spike_days(sources, min_mm, ratio):
    """sources: {name: DataFrame(date, rain_mm)}. Returns a list of flags, one per (day, high, low) pair."""
    flags = []
    for hi_name, lo_name in permutations(sorted(sources), 2):
        j = sources[hi_name][["date", "rain_mm"]].merge(sources[lo_name][["date", "rain_mm"]], on="date",
                                                         suffixes=("_hi", "_lo")).dropna()
        hit = (j["rain_mm_hi"] > min_mm) & (j["rain_mm_hi"] > ratio * j["rain_mm_lo"])
        for _, r in j[hit].iterrows():
            lo = float(r["rain_mm_lo"])
            flags.append({"date": pd.Timestamp(r["date"]).strftime("%Y-%m-%d"), "high_source": hi_name,
                          "high_mm": float(r["rain_mm_hi"]), "low_source": lo_name, "low_mm": lo,
                          "ratio": float(r["rain_mm_hi"] / lo) if lo > 0 else None})
    return sorted(flags, key=lambda f: (f["date"], f["high_source"], f["low_source"]))


def _agree(a, b, min_mm, ratio):
    """Two values agree when neither would be flagged against the other by the spike rule."""
    return not (a > min_mm and a > ratio * b) and not (b > min_mm and b > ratio * a)


def vote(flags, sources, min_mm, ratio):
    """Owner, 2026-11-12: when a third source exists, let the three vote on each flagged day.
    The source the other two outvote is the odd one out. A high station outvoting POWER (with GPM on the
    station's side) is a real local storm; a high POWER outvoted is a POWER spike; an outvoted station is
    suspect. Returns new flag dicts with a `vote` entry; nothing is deleted or changed."""
    out = []
    for f in flags:
        f = dict(f)
        hi, lo = f["high_source"], f["low_source"]
        third = [n for n in sorted(sources) if n not in (hi, lo)]
        verdict = {"label": "no third source yet", "by": None}
        for t in third:
            s = sources[t]
            v = s.loc[s["date"] == pd.Timestamp(f["date"]), "rain_mm"]
            if v.empty or pd.isna(v.iloc[0]):
                continue
            v = float(v.iloc[0])
            with_hi, with_lo = _agree(v, f["high_mm"], min_mm, ratio), _agree(v, f["low_mm"], min_mm, ratio)
            if with_hi and not with_lo:
                odd = lo
            elif with_lo and not with_hi:
                odd = hi
            else:
                verdict = {"label": "undecided", "by": t, "value_mm": v}
                continue
            if odd == "station":
                label = "station value suspect"
            elif odd == "power" and hi == "power":
                label = "POWER spike"
            elif odd == "power":
                label = "real local storm"
            else:
                label = f"{odd} disagrees with the other two"
            verdict = {"label": label, "by": t, "value_mm": v, "odd_one_out": odd}
        f["vote"] = verdict
        out.append(f)
    return out
