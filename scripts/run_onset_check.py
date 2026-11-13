"""A second monsoon-onset measure beside the kept rule: the anomalous accumulation (rules.yaml onset_accumulation,
committed before its first run; pipeline/diary/onset_accumulation.py). Writes data/checks/<field>/onset_accumulation.json.

    .venv/bin/python scripts/run_onset_check.py --field demo

Both variants (climatological = Noska & Misra 2016 exactly; own_year = Claude's level-proof variant) on both rain
versions (the twin's corrected rain_mm and GPM as published, rain_uncorrected_mm), 2001-2025, UTC days. The kept
rule's dates (scripts/run_diary.py -> diary_onset.json) are copied beside them. The trust test decides whether the
variant that feeds shift_days (own_year on the corrected rain, fixed in advance) may be exported; it never chooses a
variant. This script exports nothing to site/: it proposes the contract fields for the integrator.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.diary import onset_accumulation as oa  # noqa: E402
from pipeline.diary import trends as tr  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402

VARIANTS = ("climatological", "own_year")
VERSIONS = {"corrected": "rain_mm", "uncorrected": "rain_uncorrected_mm"}
FEEDS = ("own_year", "corrected")       # rules.yaml onset_accumulation.feeds_shift_days (checked below)


def _rounded(t):
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in t.items()}


def _kept_rule(out_dir):
    """The kept rule's dates (10-day dry spells) per rain version, as run_diary.py wrote them."""
    res = {}
    for version, path in (("corrected", out_dir / "diary_onset.json"),
                          ("uncorrected", out_dir / "rain_uncorrected" / "diary_onset.json")):
        d = json.loads(path.read_text())
        dates = d["by_dry_spell_days"]["10"]
        days = [oa.calendar_day(pd.Timestamp(v)) for v in dates.values() if v]
        res[version] = {"dates": dates, "median": oa.calendar_day_to_text(statistics.median(days)),
                        "source_file": str(path.relative_to(REPO))}
    return res


def run(field, rules, data=REPO / "data"):
    A, alpha = rules["onset_accumulation"], rules["trends"]["alpha"]
    if not A["feeds_shift_days"].startswith(f"{FEEDS[0]} variant on the twin's rain"):
        raise ValueError("rules.yaml onset_accumulation.feeds_shift_days changed: update FEEDS in this script")
    w = pd.read_parquet(data / "clean" / field["id"] / "weather.parquet")
    if (w["rain_source"] != "gpm").any():
        raise ValueError("onset needs the twin's GPM rain on every day (D6); the weather table has other sources")
    idx = pd.DatetimeIndex(w["date"])
    rain = {v: pd.Series(w[col].to_numpy(float), index=idx) for v, col in VERSIONS.items()}
    first, last = idx.min().year, idx.max().year

    runs, trends = {}, {}
    for variant in VARIANTS:
        runs[variant], trends[variant] = {}, {}
        for version, r in rain.items():
            o = oa.onsets(r, variant, A)
            days = [d for d in o["calendar_day"].values() if d is not None]
            med = statistics.median(days) if days else None
            o["median_calendar_day"] = med
            o["median"] = oa.calendar_day_to_text(med) if med is not None else None
            o["years_without_onset"] = [int(y) for y, d in o["dates"].items() if d is None]
            runs[variant][version] = o
            t = tr.mk_sen({int(y): d for y, d in o["calendar_day"].items()}, alpha)
            chg = tr.over_record(t, first, last)
            trends[variant][version] = {**_rounded(t), "change_over_record": chg[0], "change_low": chg[1],
                                        "change_high": chg[2]}

    verdicts = {}
    for variant in VARIANTS:
        v = oa.trust(runs[variant]["corrected"]["median_calendar_day"], A["sanity_window"],
                     {ver: runs[variant][ver]["at_edge"] for ver in VERSIONS},
                     trends[variant]["corrected"], trends[variant]["uncorrected"], alpha)
        verdicts[variant] = {**v, "feeds_shift_days": variant == FEEDS[0]}

    dhm = {int(y): oa.calendar_day(pd.Timestamp(f"{y}-{md}")) for y, md in A["dhm_onset_dates"].items()}
    dhm_trend = tr.mk_sen(dhm, alpha)
    dhm_chg = tr.over_record(dhm_trend, min(dhm), max(dhm))
    agree = {variant: {ver: oa.agreement({int(y): d for y, d in runs[variant][ver]["calendar_day"].items()}, dhm)
                       for ver in VERSIONS} for variant in VARIANTS}
    kept = _kept_rule(data / "checks" / field["id"])
    agree["kept_rule"] = {ver: oa.agreement({int(y): oa.calendar_day(pd.Timestamp(d)) if d else None
                                             for y, d in kept[ver]["dates"].items()}, dhm) for ver in VERSIONS}

    feed_v, feed_r = FEEDS
    fv = verdicts[feed_v]
    t_feed = trends[feed_v][feed_r]
    shift = oa.shift_export(fv["trusted"], t_feed)
    med_feed = runs[feed_v][feed_r]["median_calendar_day"]
    med_words = (pd.Timestamp("2001-01-01") + pd.Timedelta(int(round(med_feed)) - 1, unit="D")).strftime("%d %B").lstrip("0")
    why_not = [k for k in ("sanity", "not_pinned", "robust_to_rain") if not fv[k]]
    proposal = {
        "diary.shift_days": shift["shift_days"],
        "diary.shift_days_low": shift["shift_days_low"],
        "diary.shift_days_high": shift["shift_days_high"],
        "diary.shift_note": oa.plain_words(fv["trusted"], fv["clear_shift"], shift["shift_days"], med_words),
        "method.onset": (
            "Monsoon start, second measure (anomalous accumulation, Noska & Misra 2016, after Liebmann & Marengo 2001): "
            "from 1 January, add up each day's rain minus that year's own mean daily rain; the monsoon starts the day "
            "after this running total is lowest (searched to 30 September). It has no rain threshold, and a change in "
            "the amount of rain, such as GPM's 2017 gauge loss, cannot move it. "
            f"Median start {runs[feed_v][feed_r]['median']} (twin's rain, {first}-{last}); DHM's normal is 13 June in "
            "eastern Nepal, about 2 days later in Kathmandu. The first rule (2 wet days and 10 mm in 5 days from "
            f"15 May) stays shown as failing: median {kept['corrected']['median']}. "
            + ("The trend passed every check fixed in advance." if fv["trusted"] else
               "The trend is not shown: it failed the check(s) fixed in advance: " + ", ".join(why_not) + ".")),
    }
    out = {
        "labels": {
            "field": field["name"],
            "rule": "rules.yaml onset_accumulation (committed before the first run, 636a5c8); the kept rule is rules.yaml monsoon_onset, unchanged",
            "rain": {"corrected": "GPM IMERG V07 (Final to 2025-09-30, Late after), 0.1 deg cell, UTC days; scaled from 2017 to GPM's own 2001-2016 level (gpm_series.correction)",
                     "uncorrected": "the same GPM IMERG V07 rain as published (rain_uncorrected_mm)"},
            "variants": {"climatological": "Dbar = the record's mean daily rain (Noska & Misra 2016 eq. 2, exactly)",
                         "own_year": "Dbar = the year's own mean daily rain (Claude's variant, immune to a change of rain level)"},
            "feeds_shift_days": A["feeds_shift_days"],
            "day_numbers": "calendar day of a non-leap year (15 June = 166 in every year), so leap years add no false shift",
            "gpm_break_caveat": rules["gpm_series"]["trend_caveat"],
            "dhm": "DHM Climate Division, Monsoon Onset and Withdrawal date information, Table 1 (monsoon entering eastern Nepal, a regional date): information only, not part of the verdict",
            "short_record": f"{last - first + 1} years: every trend has its 95% range (Sen) and Mann-Kendall p; a range holding 0 means no clear shift",
        },
        "years": [first, last],
        "onsets": runs,
        "kept_rule": kept,
        "trends": trends,
        "trust": verdicts,
        "dhm": {"onset_calendar_day": {str(y): d for y, d in sorted(dhm.items())},
                "trend_2001_2024": {**_rounded(dhm_trend), "change_over_record": dhm_chg[0], "change_low": dhm_chg[1],
                                    "change_high": dhm_chg[2]},
                "agreement": agree},
        "export_proposal": proposal,
    }
    path = data / "checks" / field["id"] / "onset_accumulation.json"
    path.write_text(json.dumps(out, indent=1) + "\n")

    yrs = sorted(runs["own_year"]["corrected"]["dates"])
    print("year   kept(corr)  clim(corr)  clim(unc)   own(corr)   own(unc)    DHM")
    for y in yrs:
        row = [kept["corrected"]["dates"].get(y), runs["climatological"]["corrected"]["dates"][y],
               runs["climatological"]["uncorrected"]["dates"][y], runs["own_year"]["corrected"]["dates"][y],
               runs["own_year"]["uncorrected"]["dates"][y]]
        d = A["dhm_onset_dates"].get(int(y))
        print(f"{y}  " + "  ".join(f"{(x or 'none')[5:]:>10}" for x in row) + f"  {d or '':>8}")
    for variant in VARIANTS:
        for ver in VERSIONS:
            o, t = runs[variant][ver], trends[variant][ver]
            print(f"{variant:15s} {ver:11s} median {o['median']}, at edge {o['at_edge']}, none {o['years_without_onset']}; "
                  f"Sen {t['slope_per_year']:+.3f}/yr [{t['low']:+.3f}, {t['high']:+.3f}] p {t['p']:.3f}; "
                  f"over record {t['change_over_record']} [{t['change_low']}, {t['change_high']}]; "
                  f"DHM rho {agree[variant][ver]['spearman']:.2f} (p {agree[variant][ver]['spearman_p']:.3f}), "
                  f"median diff {agree[variant][ver]['median_difference_days']}")
        print(f"  trust {variant}: {verdicts[variant]}")
    print(f"kept rule: median {kept['corrected']['median']} / {kept['uncorrected']['median']}; DHM rho "
          f"{agree['kept_rule']['corrected']['spearman']}")
    print(f"DHM 2001-2024: Sen {dhm_trend['slope_per_year']:+.3f}/yr [{dhm_trend['low']:+.3f}, {dhm_trend['high']:+.3f}] "
          f"p {dhm_trend['p']:.3f}; over its record {dhm_chg}")
    print(f"proposal: {json.dumps(proposal, indent=1)}\n-> {path.relative_to(REPO)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    run(load_field(a.field), load_rules())
    return 0


if __name__ == "__main__":
    sys.exit(main())
