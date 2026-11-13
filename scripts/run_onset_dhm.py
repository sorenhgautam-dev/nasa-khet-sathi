"""DHM's official onset dates as the record of a monsoon shift, the usual rice start window and the late years
(owner, 2026-11-14; rules.yaml monsoon_onset_dhm, committed before the first run), with a cross-check: Noska & Misra
2016's record-mean onset on rain without the 2017 break (CHIRPS v3.0 daily 2001-2025; the twin's GPM 2001-2016).
Writes data/checks/<field>/onset_dhm.json, including the proposed contract fields and words. Exports nothing.

    .venv/bin/python scripts/run_onset_dhm.py --field demo
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
from pipeline.diary import onset_dhm as od  # noqa: E402
from pipeline.diary import trends as tr  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402

MONTH_KEYS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _month_names():
    """{month number: BS name} and {month number: Gregorian name in Devanagari} from pipeline/words/screens.json,
    whose month 'Jun' reads 'असार (जुन–जुलाई)': the BS month that begins in June, and June."""
    months = json.loads((REPO / "pipeline" / "words" / "screens.json").read_text())["shared"]["months"]
    bs, greg = {}, {}
    for i, k in enumerate(MONTH_KEYS, start=1):
        ne = months[k]["ne"]
        bs[i] = ne.split(" (")[0].strip()
        greg[i] = ne.split("(")[1].split("–")[0].strip()
    return bs, greg


def _cross(rain, A, t_dhm, dhm_days, alpha, label):
    o = oa.onsets(rain, "climatological", A)
    days = {int(y): d for y, d in o["calendar_day"].items()}
    t = tr.mk_sen(days, alpha)
    chg = tr.over_record(t, t["first"], t["last"])
    med = statistics.median([d for d in days.values() if d is not None])
    return {"rain": label, "dates": o["dates"], "calendar_day": o["calendar_day"],
            "reference_rate_mm_per_day": next(iter(o["reference_rate_mm_per_day"].values())),
            "median": oa.calendar_day_to_text(med), "at_edge": o["at_edge"],
            "trend": {**{k: (round(v, 3) if isinstance(v, float) else v) for k, v in t.items()},
                      "change_over_record": chg[0], "change_low": chg[1], "change_high": chg[2]},
            "agrees_with_dhm": od.agrees(t, t_dhm),
            "dhm_agreement": oa.agreement(days, dhm_days)}


def run(field, rules, data=REPO / "data"):
    D, A, alpha = rules["monsoon_onset_dhm"], rules["onset_accumulation"], rules["trends"]["alpha"]
    tab = pd.read_csv(REPO / D["record"]["file"], dtype=str)
    all_dates = dict(zip(tab["year"].astype(int), tab["onset"]))
    first, last = D["record"]["years"]
    dates = {y: d for y, d in all_dates.items() if first <= y <= last}
    days = od.record_days(all_dates, [first, last])
    if sorted(days) != list(range(first, last + 1)):
        raise ValueError(f"the DHM record lacks years in {first}-{last}")

    sh = od.shift(days, alpha)
    t_dhm = tr.mk_sen(days, alpha)
    win = od.start_window(days, D["start_window"]["percentiles"])
    late = od.late_years(dates, D["late_after"])

    w = pd.read_parquet(data / "clean" / field["id"] / "weather.parquet")
    if (w["rain_source"] != "gpm").any():
        raise ValueError("the GPM cross-check needs the twin's GPM rain on every day")
    gpm = pd.Series(w["rain_uncorrected_mm"].to_numpy(float), index=pd.DatetimeIndex(w["date"]))
    gpm = gpm[gpm.index.year <= 2016]
    if not (w.loc[w["date"].dt.year <= 2016, "rain_mm"].to_numpy() == gpm.to_numpy()).all():
        raise ValueError("before 2017 the twin's rain should equal GPM as published")
    ch = pd.read_parquet(data / "clean" / field["id"] / "chirps.parquet")
    chirps = pd.Series(ch["rain_mm"].to_numpy(float), index=pd.DatetimeIndex(ch["date"]))
    cross = {"chirps": _cross(chirps, A, t_dhm, days, alpha,
                              "CHIRPS v3.0 daily final (rnl), the field's 0.05 deg cell, UTC days, 2001-2025"),
             "gpm_2001_2016": _cross(gpm, A, t_dhm, days, alpha,
                                     "the twin's GPM IMERG V07 Final rain, 2001-2016 (before the 2017 gauge loss; equal to GPM as published)")}
    xagree = {k: v["agrees_with_dhm"] for k, v in cross.items()}
    all_agree = (not sh["clear"]) and all(xagree.values())

    bs, greg = _month_names()
    words = od.words(sh, win, late, xagree, first, bs, greg, D["bs_dates"]["month_starts_on_day"])
    source_row = {"name": "DHM (Department of Hydrology and Meteorology, Government of Nepal)",
                  "product": "Monsoon onset dates, entry into eastern Nepal (Monsoon Onset and Withdrawal date information, Table 1)",
                  "resolution": "one date a year for Nepal (eastern Nepal; Kathmandu a few days later)",
                  "years": f"{first}-{last}", "type": "station"}
    proposal = {
        "diary.shift_days": sh["shift_days"], "diary.shift_days_low": sh["shift_days_low"],
        "diary.shift_days_high": sh["shift_days_high"],
        "diary.shift_source": source_row,
        "sources[] (new row)": source_row,
        "diary.monsoon_start": {"usual_from": win["from"], "usual_to": win["to"], "median": win["median"],
                                "late_after": late["after"], "late_years": late["years"],
                                "late_share": round(late["share"], 3), "years": [first, last], "source": "DHM"},
        "diary.shift_note": words["diary_shift"],
        "next3.rice_start": words["next3_rice"],
        "method.how_we_know": words["how_we_know"],
        "method.onset_caveat": D["caveat"],
        "notes": ["'type: station' is the closest of the schema's four words (satellite, model, station, probe): DHM "
                  "declares onset from its station network. A schema change would allow 'official record'.",
                  "Nepali BS dates are approximate (each BS month taken to start on the 15th), marked 'तिर'."],
    }
    out = {"labels": {"field": field["name"],
                      "rule": "rules.yaml monsoon_onset_dhm (committed before the first run, 09c1327); DHM table config/dhm_onset_dates.csv with its NOTICE",
                      "decision": "Owner, 2026-11-14: fix the answer, not the method; DHM's official onset dates are the record of a shift",
                      "caveat": D["caveat"], "gpm_break_caveat": rules["gpm_series"]["trend_caveat"],
                      "day_numbers": "calendar day of a non-leap year (15 June = 166 in every year)",
                      "cross_check_rule": D["cross_check"], "words_rule": D["words_rule"]},
           "dhm": {"dates": {str(y): d for y, d in sorted(dates.items())},
                   "calendar_day": {str(y): d for y, d in sorted(days.items())},
                   "shift": sh, "start_window": win, "late": late},
           "cross_check": cross, "all_three_agree": all_agree,
           "export_proposal": proposal}
    path = data / "checks" / field["id"] / "onset_dhm.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

    print(f"DHM {first}-{last}: shift {sh['shift_days']} days [{sh['shift_days_low']}, {sh['shift_days_high']}], "
          f"Sen {sh['slope_per_year']:+.3f}/yr [{sh['low_per_year']:+.3f}, {sh['high_per_year']:+.3f}], p {sh['p']}: {sh['direction']}")
    print(f"usual window {win['from']} to {win['to']} (median {win['median']}); late after {late['after']}: "
          f"{late['years']} ({late['count']} of {late['of']}, {late['share']:.3f}); on the day: {late['on_the_day']}")
    for k, v in cross.items():
        t = v["trend"]
        print(f"{k}: median {v['median']}, at edge {v['at_edge']}, Sen {t['slope_per_year']:+.3f}/yr "
              f"[{t['low']:+.3f}, {t['high']:+.3f}] p {t['p']:.3f}, over record {t['change_over_record']} "
              f"[{t['change_low']}, {t['change_high']}]; agrees {v['agrees_with_dhm']}; DHM rho "
              f"{v['dhm_agreement']['spearman']:.2f} (p {v['dhm_agreement']['spearman_p']:.3f}, n {v['dhm_agreement']['n']})")
    print(f"all three agree: {all_agree}")
    for screen, wd in words.items():
        print(f"[{screen}] EN: {' '.join(wd['en'])}\n[{screen}] NE: {' '.join(wd['ne'])}")
    print(f"-> {path.relative_to(REPO)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    run(load_field(a.field), load_rules())
    return 0


if __name__ == "__main__":
    sys.exit(main())
