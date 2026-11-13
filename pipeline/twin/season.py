"""Run a crop plan (e.g. wheat then rice) day by day through the soil-water bucket. Pure functions.

Segments: bare soil before, between and after the crops (Kc = bare_kc, CLAUDE.md "start with 0.3"),
and each crop season (Kc curve from crops.json, FAO-56 eq. 66). Each segment's bucket depth is its
crop's rooting depth Zr; a bare segment uses the next crop's Zr and p (the previous crop's if none
follows). Depletion carries over between segments as a fraction of TAW, so each segment's balance
closes exactly and the hand-over is a stated simplification.

Paddy rice (REVIEW_NOTES H1, owner 2026-11-12): only an IRRIGATED paddy is ponded, every day of its
season; each ponded day the root zone is refilled to field capacity at the start of the day, so there is no
water stress, and that refill is irrigation water (`irrigation_mm`; `pond_supply_mm` is the paddy part of
it). A RAIN-FED paddy gets no water from outside: it is not ponded and runs as the ordinary bucket with
rice's Zr and p, so a weak or broken monsoon shows as stress. Each segment's balance counts irrigation_mm
once (pond_supply_mm is inside it).

Kc climate adjustment (REVIEW_NOTES M7, owner review of d34fa93): with kc_climate=True each crop season's
Kc mid and Kc end are adjusted for that season's own climate (FAO-56 eqs. 62 and 65, crops.season_kc), from the
weather columns u2_ms and rhmin_pct averaged over the mid-season and late-season days; the season record keeps
the Kc values used and the stage means. Bare soil keeps bare_kc.

Irrigated fields: other crops are refilled whenever Dr passes RAW (soil_water.run_bucket); bare soil is
never irrigated. Crops with no published seasonal Ky use the owner-assumed 1.0, labelled "assumed".

Bare soil (build step 2a, rules.yaml bare_soil): `bare_kc` is either a number, the constant Kc of bare days (the
method while bare_soil.apply is off), or a setting dict from evaporation.bare_soil_setting for FAO-56's surface layer
(eqs. 71-79): evaporation then comes from the top Ze of the root zone only and stops near TEW, and each bare spell
starts its surface layer at De = TEW x Dr / TAW of the depletion handed over (soil_water._run_bare_surface).

Plans (REVIEW_NOTES L2 and H4): crops must be in date order, each sown after the previous one ends, and
every crop must be simulatable (crops.simulatable_crops); otherwise ValueError. A season cut short by the
end of the weather record is run but gets `complete: False` and no harvest number; complete seasons get
`complete: True`.
"""
import numpy as np
import pandas as pd

from pipeline.twin import evaporation as ev
from pipeline.twin import soil_water as sw
from pipeline.twin.crops import kc_curve, require_simulatable, season_kc, season_length
from pipeline.twin.yield_ import harvest_pct


def check_daily_inputs(weather):
    """Fail loudly (golden rule 12): consecutive days, no missing ET0 or rain."""
    d = pd.DatetimeIndex(weather["date"])
    if len(d) > 1 and not (d[1:] - d[:-1] == pd.Timedelta(1, unit="D")).all():
        raise ValueError("weather dates must be consecutive days with no gaps or repeats")
    for col in ("et0_mm", "rain_mm"):
        bad = ~np.isfinite(weather[col].to_numpy(dtype=float))
        if bad.any():
            raise ValueError(f"{col} is missing or not finite on {int(bad.sum())} day(s), "
                             f"first {d[bad.argmax()].date()}")


def check_climate_inputs(weather):
    """Kc climate adjustment needs daily u2_ms and rhmin_pct on every day; fail loudly otherwise."""
    for col in ("u2_ms", "rhmin_pct"):
        if col not in weather:
            raise ValueError(f"kc_climate needs a daily {col} column in the weather table")
        bad = ~np.isfinite(weather[col].to_numpy(dtype=float))
        if bad.any():
            raise ValueError(f"{col} is missing or not finite on {int(bad.sum())} day(s)")


def carry_over(dr_mm, taw_from, taw_to):
    return 0.0 if taw_from <= 0 else dr_mm / taw_from * taw_to


def _segments(dates, plan, lib):
    dates = pd.DatetimeIndex(dates)
    segs, cursor, prev = [], 0, None
    for crop, start in plan:
        s = dates.get_loc(pd.Timestamp(start))
        e = s + season_length(lib[crop]["stages_days"])
        if s < cursor:
            raise ValueError(f"{crop} is sown {pd.Timestamp(start).date()}, before the previous crop ({prev}) ends "
                             f"on {dates[cursor - 1].date()}: crops in a plan must not overlap")
        prev = crop
        if s > cursor:
            segs.append(("bare", None, cursor, s))
        segs.append((crop, crop, s, min(e, len(dates))))
        cursor = min(e, len(dates))
    if cursor < len(dates):
        segs.append(("bare", None, cursor, len(dates)))
    return segs


def simulate(weather, plan, lib, soil, cn, bare_kc, irrigated, kc_climate=False):
    """weather: date, et0_mm, rain_mm (one row per day), plus u2_ms and rhmin_pct when kc_climate is True.
    plan: [(crop, 'YYYY-MM-DD'), ...] in date order."""
    weather = weather.reset_index(drop=True)
    check_daily_inputs(weather)
    if kc_climate:
        check_climate_inputs(weather)
    require_simulatable(lib, [c for c, _ in plan])
    surface = bare_kc if isinstance(bare_kc, dict) else None                 # build step 2a: FAO-56 surface layer
    if surface is not None and surface.get("method") != "fao56_surface_layer":
        raise ValueError(f"unknown bare-soil method {surface.get('method')!r}")
    segs = _segments(weather["date"], plan, lib)
    crops_in_plan = [c for c, _ in plan]
    frames, summary, seg_info, seasons, dr, taw_prev = [], {}, {}, [], 0.0, None
    for n, (name, crop, a, b) in enumerate(segs):
        ref = crop or next((c for _, c, i, _ in segs[n:] if c), crops_in_plan[-1])
        zr, p_tab = lib[ref]["zr_m"], lib[ref]["p"]
        taw = sw.taw_from_layers(soil, zr)
        if not np.isfinite(taw) or taw <= 0:
            raise ValueError(f"TAW for {ref} is {taw} mm: the soil table holds no plant-available water")
        if taw_prev is not None:
            dr = carry_over(dr, taw_prev, taw)
        seg = weather.iloc[a:b].copy()
        kc_used = None
        if crop:
            st = lib[crop]["stages_days"]
            kc_used = (season_kc(lib[crop]["kc"], st, lib[crop]["height_m"], seg["u2_ms"].to_numpy(),
                                 seg["rhmin_pct"].to_numpy()) if kc_climate
                       else {**lib[crop]["kc"], "u2_mid_ms": None, "rhmin_mid_pct": None,
                             "u2_late_ms": None, "rhmin_late_pct": None})
            seg["kc"] = kc_curve(st, kc_used)[: b - a]
        else:
            seg["kc"] = bare_kc if surface is None else np.nan
        paddy = bool(crop and lib[crop].get("paddy"))
        ponded = np.ones(b - a, dtype=bool) if (paddy and irrigated) else None   # rain-fed paddy: plain bucket
        irrigate = bool(irrigated and crop)                                      # bare soil: never
        layer = None
        if surface is not None and not crop:
            layer = {"tew_mm": surface["tew_mm"], "rew_mm": surface["rew_mm"], "kc_max": surface["kc_max"],
                     "de0_mm": ev.de_start_mm(dr, taw, surface["tew_mm"])}
        out = sw.run_bucket(seg, taw_mm=taw, p_table=p_tab, cn=cn[crop or "bare"], dr0_mm=dr, irrigate=irrigate,
                            ponded=ponded, surface=layer)
        out.insert(0, "date", seg["date"].to_numpy())
        out["segment"], out["crop"], out["taw_mm"] = name, crop, taw
        inflow = (out["rain_mm"] - out["runoff_mm"] + out["irrigation_mm"]).sum()   # pond water is inside irrigation
        outflow = (out["eta_mm"] + out["dp_mm"]).sum()
        residual = float(inflow - outflow - (dr - out["dr_mm"].iloc[-1]))
        if crop:                                   # a crop grown more than once is keyed by its start date
            key = name if crops_in_plan.count(crop) == 1 else f"{name}_{seg['date'].iloc[0].date()}"
        else:
            key = f"bare_{sum(1 for k in seg_info if k.startswith('bare')) + 1}"
        seg_info[key] = {"start": str(seg["date"].iloc[0].date()), "end": str(seg["date"].iloc[-1].date()),
                         "taw_mm": round(taw, 1), "zr_m": zr, "balance_residual_mm": residual}
        if layer is not None:
            seg_info[key].update(bare_method=surface["method"], tew_mm=surface["tew_mm"], rew_mm=surface["rew_mm"],
                                 de_start_mm=layer["de0_mm"], evaporation_mm=float(out["eta_mm"].sum()))
        if crop:
            etc, eta, ky = out["etc_mm"].sum(), out["eta_mm"].sum(), lib[crop]["ky"]
            full = season_length(lib[crop]["stages_days"])
            complete = (b - a) == full
            if not complete:
                note = (f"no harvest number: season cut short by the end of the weather record on "
                        f"{seg['date'].iloc[-1].date()} ({b - a} of {full} days)")
            elif lib[crop].get("ky_assumed"):
                note = f"Ky {ky}, assumed (owner decision 2026-11-12; no published seasonal Ky)"
            else:
                note = f"Ky {ky} ({lib[crop]['sources']['ky']})"
            seasons.append({
                "crop": crop, "start": str(seg["date"].iloc[0].date()), "end": str(seg["date"].iloc[-1].date()), "days": int(b - a),
                "sum_etc_mm": float(etc), "sum_eta_mm": float(eta), "eta_over_etc": float(eta / etc) if etc else None,
                "dry_days": int(out["dry_day"].sum()), "ponded_days": int(out["ponded"].sum()),
                "rain_mm": float(out["rain_mm"].sum()), "runoff_mm": float(out["runoff_mm"].sum()),
                "deep_percolation_mm": float(out["dp_mm"].sum()), "pond_supply_mm": float(out["pond_supply_mm"].sum()),
                "irrigation_mm": float(out["irrigation_mm"].sum()), "taw_mm": round(taw, 1), "zr_m": zr,
                "complete": complete, "harvest_pct": harvest_pct(eta, etc, ky) if complete else None,
                "ky": ky, "ky_assumed": bool(lib[crop].get("ky_assumed")), "harvest_note": note,
                "kc_climate_adjusted": bool(kc_climate), "kc_mid_used": kc_used["mid"], "kc_end_used": kc_used["end"],
                **{k: kc_used[k] for k in ("u2_mid_ms", "rhmin_mid_pct", "u2_late_ms", "rhmin_late_pct")}})
            if crops_in_plan.count(crop) == 1:
                summary[crop] = seasons[-1]
        dr, taw_prev = out["dr_mm"].iloc[-1], taw
        frames.append(out)
    summary["segments"], summary["seasons"] = seg_info, seasons
    return pd.concat(frames, ignore_index=True), summary


# ---------- proposal 2c (rules.yaml paddy_rainfed: PROPOSED, apply false, waiting for the owner) ----------

def paddy_transplant(plan, dates, rain_mm, lib, rule):
    """When a RAIN-FED paddy can be transplanted (proposal 2c). Land preparation (soaking and puddling) needs
    rule['prep_mm'] of rain counted from rule['prep_days'] days before the planned day; the paddy is transplanted on the
    first day, on or after the planned day, by which that total is reached. More than rule['max_delay_days'] late, the
    season fails: it stays at its planned day (so the year keeps its crops) and paddy_outcome() sets its harvest to 0.
    A later crop that would overlap a moved paddy moves to the day after it ends (and so on down the plan); a crop pushed
    past the end of the record is dropped, so its year is incomplete. Irrigated paddy is not passed here.
    Returns (plan, info): info has one entry per paddy season (planned, transplanted, delay_days, prep_rain_mm, failed,
    dropped_after)."""
    dates = pd.DatetimeIndex(dates)
    rain = pd.Series(np.asarray(rain_mm, dtype=float), index=dates)
    out, info, cursor = [], [], None                     # cursor: first free day after the previous crop
    for crop, start in plan:
        day = pd.Timestamp(start)
        if cursor is not None and day < cursor:
            day = cursor
        if lib[crop].get("paddy"):
            planned = pd.Timestamp(start)
            first = planned - pd.Timedelta(int(rule["prep_days"]), unit="D")
            latest = planned + pd.Timedelta(int(rule["max_delay_days"]), unit="D")
            cum = rain.loc[first:].cumsum()
            ok = cum[(cum.index >= day) & (cum >= rule["prep_mm"] - 1e-9)]
            when = ok.index[0] if len(ok) else None
            failed = when is None or when > latest
            prep = float(rain.loc[first:(latest if failed else when)].sum())
            info.append({"crop": crop, "planned": str(planned.date()), "transplanted": None if failed else str(when.date()),
                         "delay_days": None if failed else int((when - planned).days), "prep_rain_mm": prep,
                         "failed": bool(failed), "dropped_after": []})
            if not failed:
                day = when
            info[-1]["start"] = str(day.date())          # the day the season is simulated from
        end = day + pd.Timedelta(season_length(lib[crop]["stages_days"]) - 1, unit="D")
        if end > dates[-1]:
            if info:
                info[-1]["dropped_after"].append(crop)
            continue
        out.append((crop, str(day.date())))
        cursor = end + pd.Timedelta(1, unit="D")
    return out, info


def paddy_outcome(seasons, info):
    """The seasons with proposal 2c's outcome: a paddy that could not be transplanted in time gets harvest 0 (with a
    note); every paddy season carries its transplanting delay. Matched by crop and start day."""
    by_day = {}
    for x in info:
        by_day[(x["crop"], x["start"])] = x
    out = []
    for s_ in seasons:
        x = by_day.get((s_["crop"], s_["start"]))
        if x is None:
            out.append(s_)
            continue
        s2 = {**s_, "transplant_planned": x["planned"], "transplant_delay_days": x["delay_days"],
              "land_prep_rain_mm": x["prep_rain_mm"], "transplant_failed": x["failed"]}
        if x["failed"]:
            s2["harvest_pct"] = 0.0
            s2["harvest_note"] = (f"not transplanted: {x['prep_rain_mm']:.0f} mm of land-preparation rain by the latest day, "
                                  "short of the proposal's need (rules.yaml paddy_rainfed, PROPOSED)")
        out.append(s2)
    return out



# ---------- item 4a (rules.yaml season_dates, apply false): the farmer's sowing dates from the satellite's seasons ----------
SLOTS = {"monsoon": (6, 7, 8, 9, 10, 11), "winter": (12, 1, 2, 3, 4, 5)}      # rules.yaml rotation_guess (diary/guess.py)


def _slot(day):
    m = pd.Timestamp(day).month
    return next(k for k, months in SLOTS.items() if m in months)


def crop_slot(crop, sow, lib):
    """The slot (monsoon or winter) of a crop's season: the slot of its middle day."""
    n = season_length(lib[crop]["stages_days"])
    return _slot(pd.Timestamp(sow) + pd.Timedelta(n // 2, unit="D"))


def plan_from_seasons(plan, detected, lib, last_day):
    """Item 4a. plan: [(crop, 'YYYY-MM-DD')] from the calendar; detected: the satellite's seasons [{start, peak, end}].
    Each planned season takes the detected season of its own slot whose peak falls in the year the planned season ends;
    sowing = that season's start minus the crop's initial stage (green-up read as the end of FAO-56's initial stage);
    the crop keeps its own length. Then, in order of sowing, a crop that would start before the previous one ends starts
    the day after it, and a season pushed past last_day is dropped. Returns (plan, info) with one info per planned
    season: crop, calendar, sow, source ('hls' or 'calendar'), detected_minus_crop_days, moved_by_overlap, dropped."""
    seasons = [{k: pd.Timestamp(v) for k, v in d.items() if k in ("start", "peak", "end")} for d in detected]
    last_day = pd.Timestamp(last_day)
    rows = []
    for crop, sow in plan:
        sow = pd.Timestamp(sow)
        n = season_length(lib[crop]["stages_days"])
        year, slot = (sow + pd.Timedelta(n - 1, unit="D")).year, crop_slot(crop, sow, lib)
        mid = sow + pd.Timedelta(n // 2, unit="D")
        cands = [d for d in seasons if _slot(d["peak"]) == slot and d["peak"].year == year]
        d = min(cands, key=lambda x: abs((x["peak"] - mid).days)) if cands else None
        new = d["start"] - pd.Timedelta(int(lib[crop]["stages_days"]["ini"]), unit="D") if d is not None else sow
        rows.append({"crop": crop, "calendar": str(sow.date()), "sow": new, "n": n, "source": "hls" if d is not None else "calendar",
                     "detected_minus_crop_days": None if d is None else int((d["end"] - d["start"]).days + 1 - n),
                     "moved_by_overlap": False, "dropped": False})
    out, cursor = [], None
    for r in sorted(rows, key=lambda x: x["sow"]):
        if cursor is not None and r["sow"] < cursor:
            r["sow"], r["moved_by_overlap"] = cursor, True
        end = r["sow"] + pd.Timedelta(r["n"] - 1, unit="D")
        if end > last_day:
            r["dropped"] = True
            continue
        out.append((r["crop"], str(r["sow"].date())))
        cursor = end + pd.Timedelta(1, unit="D")
    info = [{**{k: v for k, v in r.items() if k != "n"}, "sow": str(r["sow"].date())} for r in rows]
    return out, info
