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

Plans (REVIEW_NOTES L2 and H4): crops must be in date order, each sown after the previous one ends, and
every crop must be simulatable (crops.simulatable_crops); otherwise ValueError. A season cut short by the
end of the weather record is run but gets `complete: False` and no harvest number; complete seasons get
`complete: True`.
"""
import numpy as np
import pandas as pd

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
            seg["kc"] = bare_kc
        paddy = bool(crop and lib[crop].get("paddy"))
        ponded = np.ones(b - a, dtype=bool) if (paddy and irrigated) else None   # rain-fed paddy: plain bucket
        irrigate = bool(irrigated and crop)                                      # bare soil: never
        out = sw.run_bucket(seg, taw_mm=taw, p_table=p_tab, cn=cn[crop or "bare"], dr0_mm=dr, irrigate=irrigate,
                            ponded=ponded)
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
