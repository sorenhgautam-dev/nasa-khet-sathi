"""Feature 2, the 25-Year Replay (rules.yaml window_replay): each exported plan's coming season run through the same
window of every past season, from a dry, medium and wet start, on every rain version -> site/data/replay/<field>.json.

    .venv/bin/python -m pipeline.export.build_replay --field demo

Reads the exported field file (its plans and current_options), data/clean/<field>/{weather,soilgrids,oni}.parquet and
the twin's state (data/clean/<field or its sample_of>/twin_state.json). The runs are pipeline/plans/window.py.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline.export.build_labels import label_for, load_scorecard
from pipeline.fetch import oni as oni_mod
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules
from pipeline.plans import twin_options as to
from pipeline.plans import window as win
from pipeline.twin.crops import rhmin_pct
from pipeline.twin.inputs import with_rain

REPO = Path(__file__).resolve().parents[2]
OTHER_RAIN = ("untuned", "dhm", "uncorrected")          # scripts/common.RAIN_DIRS without the central 'corrected'
STARTS = ("dry", "medium", "wet")
TWIN_SOURCES = ("GPM IMERG", "NASA POWER", "Kathmandu Airport station", "ISRIC SoilGrids", "Khet Sathi field twin")
WATERING_EN = ("If you can water whenever the soil runs low, the crop is never short of water: watering removes the "
               "dry stress counted here.")


def plans_of(doc):
    """[(id, role, crops)]: the field file's plans, then each current option."""
    out = [(p["id"], "current" if p["id"] == "current" else "suggested", p["crops"]) for p in doc["plans"]]
    out += [(o["id"], "current_option", o["crops"]) for o in (doc.get("current_options") or {}).get("options", [])]
    return out


def mmdd(t):
    return f"{t.month:02d}-{t.day:02d}"


def past_years(plans, lib, start, first_day, last_day, months):
    """window_replay.past_seasons: the years Y whose longest window ends by last_day and whose crops (all plans) lie in
    the record (sown on or after first_day; their whole season by last_day, for the Kc climate adjustment)."""
    years = []
    for y in range(first_day.year - 1, last_day.year + 1):
        ws = pd.Timestamp(f"{y}-{mmdd(start)}")
        we = win.window_end(ws, months)
        if ws < first_day or we > last_day:
            continue
        held = [x for _, _, crops in plans for x in win.in_window(win.crop_seasons(crops, lib, ws, we), ws, we)]
        if all(x["sow"] >= first_day and x["end"] <= last_day for x in held):
            years.append(y)
    return years


def band_p(crops, lib, start):
    """p of the current plan's crop in the ground on the start day, else of the next crop (window_replay.starts)."""
    seasons = win.crop_seasons(crops, lib, start, start)
    now = [c for c, s, e in seasons if s <= start <= e]
    return lib[now[0] if now else next(c for c, s, _ in seasons if s > start)]["p"], (now[0] if now else None)


def build(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules, lib = load_field(fid), load_rules(), load_crops()
    R = rules["window_replay"]
    doc = json.loads((site / "fields" / f"{fid}.json").read_text())
    src = field.get("sample_of") or fid
    state_path = next(p for p in (data / "clean" / fid / "twin_state.json", data / "clean" / src / "twin_state.json")
                      if p.exists())
    state = json.loads(state_path.read_text())
    start = pd.Timestamp(state["date"]) + pd.Timedelta(1, unit="D")
    clean = data / "clean" / fid
    w = pd.read_parquet(clean / "weather.parquet")
    w["date"] = pd.to_datetime(w["date"])
    if rules["kc_climate"]["apply"]:
        w = w.assign(u2_ms=w["ws2m_ms"], rhmin_pct=rhmin_pct(w["ea_kpa"], w["tmax_c"]))
    soil = pd.read_parquet(clean / "soilgrids.parquet")
    from scripts.common import rain_kw           # the rain versions' arguments, as every runner builds them
    rains = {"central": w, **{v: with_rain(w, v, **rain_kw(rules, v, fid)) for v in OTHER_RAIN}}
    cover, by_cover = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by_cover["bare"], **{c: by_cover[cover[c]] for c in cover if c in lib}}
    bare, losses, kc_climate = to.bare_setting(rules, soil), to.paddy_losses(rules), rules["kc_climate"]["apply"]
    plans = plans_of(doc)
    months = {k: int(v) for k, v in R["windows"].items()}
    longest = max(months, key=months.get)
    first_day, last_day = w["date"].min(), w["date"].max()
    years = past_years(plans, lib, start, first_day, last_day, months[longest])

    current = next(c for i, _, c in plans if i == "current")
    p, crop_now = band_p(current, lib, start)
    fractions = {s: win.start_fraction(s, p) for s in STARTS}
    own_state = state_path.parent.name == fid
    default = win.start_of(state["dr_mm"] / state["taw_mm"], p) if own_state else "medium"

    table = pd.read_parquet(clean / "oni.parquet")
    now = oni_mod.last_season_before(table, start)
    thr = R["enso"]["threshold_c"]
    by_oni = {(r.season, r.year): r.anom_c for r in table.itertuples()}
    name = {y: f"{y}-{str(y + 1)[2:]}" for y in years}
    enso = {}
    for y in years:
        oy = y + int(now["year"]) - start.year
        a = by_oni.get((now["season"], oy))
        enso[name[y]] = {"season": now["season"], "year": oy, "oni": a, "state": None if a is None else oni_mod.state(a, thr)}
    now_state = oni_mod.state(float(now["anom_c"]), thr)

    out_plans = []
    for pid, role, crops in plans:
        res = {k: {s: [] for s in STARTS} for k in months}
        for y in years:
            ws = pd.Timestamp(f"{y}-{mmdd(start)}")
            ends = {k: win.window_end(ws, m) for k, m in months.items()}
            seasons = win.crop_seasons(crops, lib, ws, ends[longest])
            for s in STARTS:
                sq = {}
                for v, wv in rains.items():
                    daily = win.run_window(wv, seasons, lib, soil, cn, bare, ws, ends[longest], fractions[s],
                                           kc_climate=kc_climate, paddy_losses=losses)
                    sq[v] = {k: win.summarise(daily, ends[k], R["classes"]) for k in months}
                for k in months:
                    c = sq["central"][k]
                    other = {v: {"result": sq[v][k]["result"], "score": sq[v][k]["score"]} for v in OTHER_RAIN}
                    res[k][s].append({"season": name[y], "year": int(ends[k].year), **c, "enso": enso[name[y]]["state"],
                                      "sensitive": any(o["result"] != c["result"] for o in other.values()),
                                      "other_versions": other})
        ws0 = start
        in_win = {k: [{"crop": x["crop"], "start": mmdd(x["sow"]), "end": mmdd(x["end"]),
                       "in_ground_at_start": x["in_ground_at_start"]}
                      for x in win.in_window(win.crop_seasons(crops, lib, ws0, win.window_end(ws0, m)), ws0,
                                             win.window_end(ws0, m))] for k, m in months.items()}
        summary = {k: {s: {r: sum(x["result"] == r for x in res[k][s]) for r in ("worked", "struggled", "failed")}
                       | {"no_crop": sum(x["result"] is None for x in res[k][s]),
                          "sensitive": sum(x["sensitive"] for x in res[k][s])} for s in STARTS} for k in months}
        out_plans.append({"id": pid, "role": role, "crops_in_window": in_win, "results": res, "summary": summary})

    srcs = [x for x in doc["sources"] if x["name"] in TWIN_SOURCES]
    srcs.append({"name": "NOAA CPC Oceanic Nino Index (ONI)", "product": "ERSST.v5 sea-surface temperature anomalies, "
                 "3-month means; El Nino / La Nina highlight only", "resolution": "Nino-3.4 region of the Pacific",
                 "years": f"{table['year'].min()}-{table['year'].max()}", "type": "model"})
    card = load_scorecard(fid, field, data)
    return {
        "field": fid, "placeholder": bool(field.get("placeholder")),
        "made_by": "pipeline/export/build_replay.py (rules.yaml window_replay)",
        "start": str(start.date()),
        "start_rule": f"the day after the twin's state day ({state['date']}, {state_path.relative_to(REPO)})",
        "windows": [{"id": k, "months": m, "from": mmdd(start), "to": mmdd(win.window_end(start, m))} for k, m in months.items()],
        "year_count": len(years), "seasons": [name[y] for y in years],
        "water_case": "rain-fed",
        "watering": {"removes_dry_stress": True, "en": WATERING_EN},
        "starts": [{"id": s, "probe_band": {"dry": "needs water", "medium": "good", "wet": "too wet"}[s],
                    "depletion_fraction": round(fractions[s], 4), "wetness_pct": round(100 * (1 - fractions[s]), 1)}
                   for s in STARTS],
        "start_band_crop": {"crop": crop_now or next(c for c, s, _ in win.crop_seasons(current, lib, start, start) if s > start), "p": p},
        "start_default": default,
        "twin_today": ({"date": state["date"], "wetness_pct": round(100 * (1 - state["dr_mm"] / state["taw_mm"]), 1),
                        "band": "good" if default == "medium" else "needs water", "crop": state.get("crop")}
                       if own_state else None),
        "enso": {"now": {"season": now["season"], "year": int(now["year"]), "oni": float(now["anom_c"]), "state": now_state},
                 "by_season": enso, "same_as_now": [k for k, v in enso.items() if v["state"] == now_state],
                 "rule": ("NOAA CPC: El Nino when the ONI is +0.5 C or more, La Nina when -0.5 C or less, else neutral; "
                          f"one 3-month season a year ({now['season']}, the last that ends before the start)"),
                 "source": srcs[-1]},
        "thresholds": {"score": "water need met over the window's crop days, 100 x sum(ETa) / sum(ETc) (WRSI)",
                       "worked_min": R["classes"]["worked_min"], "failed_below": R["classes"]["failed_below"],
                       "sensitive": "the result word differs under another rain version (untuned, dhm, uncorrected)",
                       "source": "FEWS NET WRSI classes (rules.yaml window_replay.classes)"},
        "plans": out_plans,
        "label": label_for("replay_window", field, rules, card),
        "sources": srcs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    doc = build(a.field)
    out = REPO / "site" / "data" / "replay" / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n")
    s = doc["plans"][0]["summary"]
    print(f"wrote {out} ({out.stat().st_size // 1024} KB): {doc['year_count']} seasons, start {doc['start']}, default "
          f"{doc['start_default']}; current m6 {doc['start_default']}: {s['m6'][doc['start_default']]}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    sys.exit(main())
