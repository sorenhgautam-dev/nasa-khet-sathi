"""Monsoon onset per year (CLAUDE.md "Field diary", build step 6a). Pure: a daily rain series in, dates out.

Rule (rules.yaml monsoon_onset, from CLAUDE.md with Claude's readings marked there): searching from 15 May to
30 September, the onset is the first day d that
  - is wet (>= wet_day_mm),
  - starts a window of window_days days holding at least wet_days_min wet days and at least total_mm in all,
  - and is not followed, in the lookahead_days days after d, by a run of dry_spell_days days each under
    wet_day_mm.
A start whose window or look-ahead runs past the record is not confirmed. A missing day or date in the
searched part of the record fails loudly (golden rule 12c): the rain is never filled here.

GPM caveat (owner, 2026-11-12, rules.yaml gpm_series): GPM's rain jumps from 2017 against both the station and
POWER. Any onset trend must say that the break may explain it until rain check B settles it.
"""
import pandas as pd


def _dry_run_max(values, wet_mm):
    longest = run = 0
    for v in values:
        run = run + 1 if v < wet_mm else 0
        longest = max(longest, run)
    return longest


def onset_date(rain, rules, year=None):
    """The onset Timestamp in `year` (default: the series' first year), or None."""
    rain = rain.sort_index()
    year = rain.index[0].year if year is None else year
    start = pd.Timestamp(f"{year}-{rules['search_from']}")
    end = pd.Timestamp(f"{year}-{rules['search_until']}")
    reach = max(rules["window_days"] - 1, rules["lookahead_days"])
    span = rain.loc[start: end + pd.Timedelta(reach, unit="D")]
    want = pd.date_range(start, min(end + pd.Timedelta(reach, unit="D"), rain.index[-1]))
    if len(span) != len(want) or not span.index.equals(want):
        raise ValueError(f"onset {year}: missing dates in the rain record between {start.date()} and {want[-1].date()}")
    if span.isna().any():
        raise ValueError(f"onset {year}: {int(span.isna().sum())} missing rain value(s), e.g. {span[span.isna()].index[0].date()}")
    wet, n_win, n_look = rules["wet_day_mm"], rules["window_days"], rules["lookahead_days"]
    v, days = span.to_numpy(), span.index
    for i, d in enumerate(days):
        if d > end:
            break
        if v[i] < wet:
            continue
        win = v[i:i + n_win]
        if len(win) < n_win or (win >= wet).sum() < rules["wet_days_min"] or win.sum() < rules["total_mm"]:
            continue
        look = v[i + 1:i + 1 + n_look]
        if len(look) < n_look:
            continue                                  # cannot confirm: the record ends first
        if _dry_run_max(look, wet) >= rules["dry_spell_days"]:
            continue
        return d
    return None


def onsets(rain, rules):
    """Onset per year for the main rule and each robustness dry-spell length.
    {'by_dry_spell_days': {'10': {'2001': '2001-06-12' | None, ...}, '15': ..., '20': ...},
     'day_of_year': {'2001': 163 | None, ...}}  (day_of_year for the main rule)."""
    rain = rain.sort_index()
    years = sorted({d.year for d in rain.index
                    if pd.Timestamp(f"{d.year}-{rules['search_from']}") >= rain.index[0]})
    out = {"by_dry_spell_days": {}, "day_of_year": {}}
    for spell in [rules["dry_spell_days"], *rules["robustness_dry_spell_days"]]:
        r = {**rules, "dry_spell_days": spell}
        res = {}
        for y in years:
            d = onset_date(rain, r, year=y)
            res[str(y)] = None if d is None else d.strftime("%Y-%m-%d")
            if spell == rules["dry_spell_days"]:
                out["day_of_year"][str(y)] = None if d is None else int(d.dayofyear)
        out["by_dry_spell_days"][str(spell)] = res
    return out
