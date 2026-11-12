"""Build step 5: replay a rotation through every season of the weather record (CLAUDE.md "Plans", 2.
Simulate). Pure functions; file I/O lives in scripts/run_replay.py.

- Sowing: each crop at the middle of its default window (rules.yaml crop_calendar), every year; only
  seasons that lie wholly inside the weather record are run (wheat sown in Nov 2000 has no weather).
- Year rule (rules.yaml replay): a season belongs to the year it is harvested (its last day). A year's
  harvest is the mean of its crops' harvest percentages; its dry days, irrigation_mm and pond_supply_mm are
  their sums.
- Both water cases (owner, step-4 review item 3): call replay() with irrigated False and True. A rain-fed
  paddy gets no outside water (plain bucket); an irrigated paddy is ponded and its pond water is irrigation
  (twin/season.py, REVIEW_NOTES H1). irrigation_mm includes the paddy's pond water; pond_supply_mm is that part.
- Ky sensitivity (owner, step-4 review item 4): crops whose Ky is assumed are re-scored with other Ky
  values from the same seasonal ETa and ETc; nothing else changes, so no rerun is needed.
- Event indicator per season (wettest day) is reported for the event rule. Frost is not a replay event
  (owner, 2026-11-12, REVIEW_NOTES M1), so no frost indicator is carried.
"""
import pandas as pd

from pipeline.twin import season
from pipeline.twin.crops import require_simulatable, season_length, sow_date
from pipeline.twin.yield_ import harvest_pct


WATER_CASES = {"rain-only": "rain-fed", "canal": "irrigated", "well": "irrigated", "irrigated": "irrigated"}


class NoSeasonError(ValueError):
    """The weather record is too short for any season of the rotation."""


def export_case(water_source):
    """The field's water source (config/fields/<id>.yaml) -> the replay case it exports."""
    if water_source not in WATER_CASES:
        raise ValueError(f"water_source '{water_source}' is not one of {sorted(WATER_CASES)}")
    return WATER_CASES[water_source]


def rain_record_problems(weather):
    """Decision D: POWER only fills days GPM lacks. Missing days, or fill outside GPM's own date range
    (a truncated GPM record), are problems."""
    src, d = weather["rain_source"].astype(str), pd.DatetimeIndex(weather["date"])
    problems = []
    if (src == "missing").any():
        problems.append(f"{int((src == 'missing').sum())} day(s) have no rain at all (rain_source missing)")
    gpm = d[(src == "gpm").to_numpy()]
    if len(gpm) == 0:
        problems.append("no GPM rain at all")
        return problems
    other = (src != "gpm").to_numpy() & (src != "missing").to_numpy()
    outside = other & ((d < gpm.min()) | (d > gpm.max()))
    if outside.any():
        problems.append(f"{int(outside.sum())} filled day(s) lie outside the GPM record ({gpm.min().date()} to "
                        f"{gpm.max().date()}): POWER would stand in for GPM, not fill its gaps")
    return problems


def rotation_plan(rotation, lib, start, end):
    """[(crop, 'YYYY-MM-DD'), ...] for every season of `rotation` inside [start, end], in date order."""
    require_simulatable(lib, rotation)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    plan = []
    for year in range(start.year - 1, end.year + 1):
        for crop in rotation:
            s = sow_date(lib[crop]["calendar"], year)
            e = s + pd.Timedelta(season_length(lib[crop]["stages_days"]) - 1, unit="D")
            if s >= start and e <= end:
                plan.append((crop, s, e))
    if not plan:
        raise NoSeasonError(f"no season of {rotation} fits between {start.date()} and {end.date()}")
    plan.sort(key=lambda x: x[1])
    for (c1, s1, e1), (c2, s2, _) in zip(plan, plan[1:]):
        if s2 <= e1:
            raise ValueError(f"crops overlap: {c1} {s1.date()} to {e1.date()} and {c2} sown {s2.date()}")
    return [(c, str(s.date())) for c, s, _ in plan]


def yearly(seasons):
    """One row per harvest year: mean harvest of its crops; summed dry days, irrigation_mm (which includes a
    paddy's pond water) and pond_supply_mm."""
    out = {}
    for s in seasons:
        if s["harvest_pct"] is None:
            raise ValueError(f"{s['crop']} sown {s.get('start')} has no harvest number ({s.get('harvest_note')}): "
                             "a year cannot be scored without it")
        y = out.setdefault(s["year"], {"year": s["year"], "h": [], "dry_days": 0, "crops": [], "ky_assumed": False,
                                       "irrigation_mm": 0.0, "pond_supply_mm": 0.0})
        y["h"].append(s["harvest_pct"])
        y["dry_days"] += int(s["dry_days"])
        y["crops"].append(s["crop"])
        y["ky_assumed"] = y["ky_assumed"] or bool(s.get("ky_assumed"))
        y["irrigation_mm"] += float(s["irrigation_mm"])
        y["pond_supply_mm"] += float(s["pond_supply_mm"])
    return [{"year": y["year"], "harvest": float(sum(y["h"]) / len(y["h"])), "dry_days": y["dry_days"],
             "crops": y["crops"], "ky_assumed": y["ky_assumed"], "irrigation_mm": y["irrigation_mm"],
             "pond_supply_mm": y["pond_supply_mm"]} for y in sorted(out.values(), key=lambda r: r["year"])]


def seasons_with_ky(seasons, lib, ky_value):
    """The same seasons, with crops whose Ky is assumed re-scored at `ky_value`."""
    out = []
    for s in seasons:
        ky = ky_value if lib[s["crop"]].get("ky_assumed") else lib[s["crop"]]["ky"]
        out.append({**s, "ky_assumed": bool(lib[s["crop"]].get("ky_assumed")),
                    "harvest_pct": harvest_pct(s["sum_eta_mm"], s["sum_etc_mm"], ky)})
    return out


def ky_sensitivity(seasons, lib, values):
    """{ky_value: {crop: [harvest_pct per season, in order]}}."""
    res = {}
    for v in values:
        by_crop = {}
        for s in seasons_with_ky(seasons, lib, v):
            by_crop.setdefault(s["crop"], []).append(s["harvest_pct"])
        res[v] = by_crop
    return res


def replay(weather, rotation, lib, soil, cn, bare_kc, irrigated):
    """weather: date, et0_mm, rain_mm, one row per day, no gaps (other columns are ignored)."""
    w = weather.reset_index(drop=True)
    plan = rotation_plan(rotation, lib, w["date"].min(), w["date"].max())
    daily, summary = season.simulate(w[["date", "et0_mm", "rain_mm"]], plan, lib, soil, cn, bare_kc, irrigated)
    idx = w.set_index("date")
    seasons = []
    for s in summary["seasons"]:
        win = idx.loc[s["start"]:s["end"]]
        seasons.append({**s, "year": pd.Timestamp(s["end"]).year, "rain_max_day_mm": float(win["rain_mm"].max())})
    years = yearly(seasons)
    partial = {str(y["year"]): y["crops"] for y in years if sorted(y["crops"]) != sorted(rotation)}
    return {"plan": plan, "irrigated": bool(irrigated), "seasons": seasons, "years": years,
            "partial_years": partial, "segments": summary["segments"], "daily": daily}
