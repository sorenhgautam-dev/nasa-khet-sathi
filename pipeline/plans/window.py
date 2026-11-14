"""The 25-Year Replay (rules.yaml window_replay): a plan's coming season, run through the same window of every past
season with the existing twin. Pure functions; file I/O lives in pipeline/export/build_replay.py.

- The window: from the start day, m months (window_end). A past season Y runs the same window from the start's month and
  day of Y, on Y's weather.
- The crops: each plan crop sown on its MM-DD day of each year, for its crops.json season length (crop_seasons). A crop
  sown before the window is in the ground on its first day at its own stage (its Kc curve counted from sowing).
- The bucket: season.simulate's segments and settings (run_window), but over the window only and starting from a chosen
  depletion fraction of TAW (the dry / medium / wet starts, start_fraction). Rain-fed: nothing is irrigated.
- The result: WRSI = 100 x sum(ETa) / sum(ETc) over the window's crop days, its class (classify) and the longest run of
  dry crop days (reason).
"""
import numpy as np
import pandas as pd

from pipeline.twin import evaporation as ev
from pipeline.twin import soil_water as sw
from pipeline.twin.crops import kc_curve, season_kc, season_length
from pipeline.twin.season import carry_over

LOOK_AHEAD_DAYS = 400        # a bare spell's bucket takes the NEXT crop's Zr and p (season.simulate), even past the window


def window_end(start, months):
    """The window's last day: the day before the same day `months` later."""
    return pd.Timestamp(start) + pd.DateOffset(months=months) - pd.Timedelta(1, unit="D")


def crop_seasons(crops, lib, ws, we):
    """[(crop, sow, end)] of the plan's crops ([{crop, start: 'MM-DD'}]) whose seasons overlap ws .. we + LOOK_AHEAD_DAYS,
    in date order. Crops of a plan must not overlap (crops.json; season._segments refuses it too)."""
    ws, we = pd.Timestamp(ws), pd.Timestamp(we)
    out = []
    for c in crops:
        n = int(season_length(lib[c["crop"]]["stages_days"]))
        for y in range(ws.year - 1, we.year + 3):
            sow = pd.Timestamp(f"{y}-{c['start']}")
            end = sow + pd.Timedelta(n - 1, unit="D")
            if sow <= we + pd.Timedelta(LOOK_AHEAD_DAYS, unit="D") and end >= ws:
                out.append((c["crop"], sow, end))
    out.sort(key=lambda x: x[1])
    for (c1, _, e1), (c2, s2, _) in zip(out, out[1:]):
        if s2 <= e1:
            raise ValueError(f"crops overlap: {c1} ends {e1.date()}, {c2} sown {s2.date()}")
    return out


def in_window(seasons, ws, we):
    """The seasons that overlap the window, each with in_ground_at_start."""
    ws, we = pd.Timestamp(ws), pd.Timestamp(we)
    return [{"crop": c, "sow": s, "end": e, "in_ground_at_start": bool(s < ws)} for c, s, e in seasons if s <= we and e >= ws]


def start_fraction(start_id, p):
    """rules.yaml window_replay.starts: the middle of the probe band, as a fraction of TAW (0 = field capacity)."""
    return {"wet": 0.0, "medium": p / 2.0, "dry": (1.0 + p) / 2.0}[start_id]


def start_of(fraction, p):
    """The start whose probe band holds a depletion fraction (window_replay.start_default): good -> medium, needs water
    -> dry (the bucket never holds more than field capacity, so it is never 'too wet')."""
    return "medium" if fraction <= p else "dry"


def _segments(seasons, ws, we):
    """[(crop or None, first day, last day, Kc offset, sow)] covering ws .. we."""
    segs, cursor = [], pd.Timestamp(ws)
    for crop, sow, end in seasons:
        a, b = max(sow, cursor), min(end, we)
        if b < a:
            continue
        if a > cursor:
            segs.append((None, cursor, a - pd.Timedelta(1, unit="D"), 0, None))
        segs.append((crop, a, b, int((a - sow).days), sow))
        cursor = b + pd.Timedelta(1, unit="D")
    if cursor <= we:
        segs.append((None, cursor, pd.Timestamp(we), 0, None))
    return segs


def run_window(weather, seasons, lib, soil, cn, bare, ws, we, f0, kc_climate=False, paddy_losses=None):
    """The twin day by day over ws..we, starting at depletion f0 x TAW. weather: date, et0_mm, rain_mm (and u2_ms,
    rhmin_pct with kc_climate) over the window AND each crop's whole season (its Kc climate adjustment uses its own
    season). seasons: crop_seasons(). bare: season.simulate's bare_kc (a constant Kc or the FAO-56 surface-layer dict).
    Returns one row a day: date, crop (None = bare), eta_mm, etc_mm, dry_day, rain_mm, dr_mm, taw_mm."""
    w = weather.set_index(pd.DatetimeIndex(weather["date"]))
    surface = bare if isinstance(bare, dict) else None
    frames, dr, taw_prev = [], None, None
    for crop, a, b, offset, sow in _segments(seasons, ws, we):
        if crop:
            ref = crop
        else:
            ref = next((c for c, s, _ in seasons if s > a), None) or next(c for c, s, _ in reversed(seasons) if s < a)
        zr, p_tab = lib[ref]["zr_m"], lib[ref]["p"]
        taw = sw.taw_from_layers(soil, zr)
        dr = f0 * taw if dr is None else carry_over(dr, taw_prev, taw)
        seg = w.loc[a:b].copy()
        if len(seg) != (b - a).days + 1:
            raise ValueError(f"weather is missing days between {a.date()} and {b.date()}")
        layer, sp = None, None
        if crop:
            st, kc = lib[crop]["stages_days"], lib[crop]["kc"]
            if kc_climate:
                full = w.loc[sow: sow + pd.Timedelta(int(season_length(st)) - 1, unit="D")]
                if len(full) != season_length(st):
                    raise ValueError(f"{crop} sown {sow.date()}: its whole season is not in the weather (Kc climate)")
                kc = season_kc(kc, st, lib[crop]["height_m"], full["u2_ms"].to_numpy(), full["rhmin_pct"].to_numpy())
            seg["kc"] = kc_curve(st, kc)[offset: offset + len(seg)]
            if lib[crop].get("paddy") and paddy_losses:
                sp = paddy_losses["perc_mm_day"]
        else:
            seg["kc"] = bare if surface is None else np.nan
            if surface is not None:
                layer = {"tew_mm": surface["tew_mm"], "rew_mm": surface["rew_mm"], "kc_max": surface["kc_max"],
                         "de0_mm": ev.de_start_mm(dr, taw, surface["tew_mm"])}
        out = sw.run_bucket(seg.reset_index(drop=True)[["rain_mm", "et0_mm", "kc"]], taw_mm=taw, p_table=p_tab,
                            cn=cn[crop or "bare"], dr0_mm=dr, surface=layer, **({"sp_mm": sp} if sp else {}))
        frames.append(pd.DataFrame({"date": seg.index, "crop": crop, "eta_mm": out["eta_mm"].to_numpy(),
                                    "etc_mm": out["etc_mm"].to_numpy(), "dry_day": out["dry_day"].to_numpy(),
                                    "rain_mm": out["rain_mm"].to_numpy(), "dr_mm": out["dr_mm"].to_numpy(), "taw_mm": taw}))
        dr, taw_prev = float(out["dr_mm"].iloc[-1]), taw
    return pd.concat(frames, ignore_index=True)


def classify(score, classes):
    """worked / struggled / failed by rules.yaml window_replay.classes; None without a score."""
    if score is None:
        return None
    return "worked" if score >= classes["worked_min"] else "failed" if score < classes["failed_below"] else "struggled"


def reason(daily):
    """The longest run of consecutive dry crop days (the earliest of equal runs), or no_dry_days / no_crop_in_window."""
    crop = daily["crop"].notna().to_numpy()
    if not crop.any():
        return {"code": "no_crop_in_window"}
    dry = crop & daily["dry_day"].to_numpy(dtype=bool)
    best, best_at, run = 0, None, 0
    for i, d in enumerate(dry):
        run = run + 1 if d else 0
        if run > best:
            best, best_at = run, i - run + 1
    if best == 0:
        return {"code": "no_dry_days"}
    return {"code": "dry_spell", "month": f"{pd.Timestamp(daily['date'].iloc[best_at]).month:02d}", "days": int(best)}


def summarise(daily, until, classes):
    """One square: score (WRSI over the crop days up to `until`), result, dry_days, rain_mm and reason."""
    d = daily[daily["date"] <= pd.Timestamp(until)]
    c = d[d["crop"].notna()]
    etc = float(c["etc_mm"].sum())
    score = int(round(100.0 * float(c["eta_mm"].sum()) / etc)) if len(c) and etc > 0 else None
    return {"result": classify(score, classes), "score": score, "dry_days": int(c["dry_day"].sum()),
            "rain_mm": round(float(d["rain_mm"].sum()), 1), "reason": reason(d)}
