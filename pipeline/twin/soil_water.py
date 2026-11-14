"""Root-zone soil-water bucket, FAO-56 Chapter 8 (Allen et al. 1998): TAW (eq. 82), RAW (eq. 83),
Ks (eq. 84), the daily depletion balance (eq. 85, limits eq. 86, deep percolation eq. 88), and p
adjusted for ETc (Table 22 note, limited to 0.1..0.8). Ks uses the depletion at the start of the day,
as in FAO-56 Example 37. Pure functions.

Irrigation (CLAUDE.md "refill when Dr > RAW"): when `irrigate` is on and yesterday's depletion is past
RAW, the root zone is refilled to field capacity at the start of the day, so the crop is never stressed.
Water is assumed to be there whenever it is needed: an upper bound on what irrigation changes.

Ponded paddy (REVIEW_NOTES H1 and L1, 2026-11-12): only an IRRIGATED paddy is ponded (the caller,
twin/season.py, flags its days). On a ponded day the root zone is refilled to field capacity at the start
of the day, exactly like the irrigation refill but every day whatever the depletion, so Ks is taken after
the refill and is honestly 1. That refill is irrigation water: it is booked in `irrigation_mm`, and
`pond_supply_mm` reports the paddy part of it (pond_supply_mm is part of irrigation_mm, never extra). The
balance counts irrigation_mm once: rain - runoff + irrigation = ETa + deep percolation + change in storage.
A rain-fed paddy gets no water from outside: it is not ponded and runs as this ordinary bucket with rice's
Zr and p. FAO-56 gives no paddy water-balance procedure, so both are stated simplifications.
"""
import numpy as np
import pandas as pd

from pipeline.twin.runoff import scs_runoff_mm


def taw_mm(theta_fc, theta_wp, zr_m):                     # eq. 82
    return 1000.0 * (theta_fc - theta_wp) * zr_m


def taw_from_layers(layers, zr_m):
    """TAW over 0..zr_m from SoilGrids-style layers (top_cm, bottom_cm, theta_fc_m3m3, theta_wp_m3m3)."""
    total = 0.0
    for _, r in layers.iterrows():
        top, bottom = r["top_cm"] / 100.0, min(r["bottom_cm"] / 100.0, zr_m)
        if bottom > top:
            total += taw_mm(r["theta_fc_m3m3"], r["theta_wp_m3m3"], bottom - top)
    return total


def adjust_p(p_table, etc_mm):                            # Table 22 note
    return float(np.clip(p_table + 0.04 * (5.0 - etc_mm), 0.1, 0.8))


def ks(dr_mm, taw, raw):                                  # eq. 84
    if dr_mm <= raw:
        return 1.0
    return max(0.0, (taw - dr_mm) / (taw - raw))


def step(dr_prev, rain_mm, runoff_mm, irrigation_mm, etc_mm, taw_mm, p, loss_mm=None):
    """One day. Ks from the start-of-day depletion; ETa limited so depletion never passes TAW.
    loss_mm: a paddy's seepage and percolation that day (rules.yaml paddy_losses): taken first out of the water above
    field capacity, which drains anyway (eq. 88), then out of the root zone; at the wilting point it gives way first."""
    raw = p * taw_mm
    k = ks(dr_prev, taw_mm, raw)
    eta = k * etc_mm
    dr = dr_prev - (rain_mm - runoff_mm) - irrigation_mm + eta
    if loss_mm is not None:
        dr += loss_mm
    dp = 0.0
    if dr < 0:                                            # eq. 88: water above field capacity drains
        dp, dr = -dr, 0.0
    if dr > taw_mm:                                       # eq. 86: cannot dry past wilting point
        over = dr - taw_mm
        if loss_mm is not None:
            cut = min(over, loss_mm)
            loss_mm, over = loss_mm - cut, over - cut
        eta -= over
        dr = taw_mm
    out = {"dr_mm": dr, "ks": k, "eta_mm": eta, "dp_mm": dp}
    if loss_mm is not None:
        out["sp_mm"] = loss_mm
    return out


def run_bucket(df, taw_mm, p_table, cn, dr0_mm=0.0, irrigate=False, ponded=None, surface=None, sp_mm=None):
    """df: rain_mm, et0_mm, kc (one row per day). cn: number or per-day array. ponded: per-day flags (irrigated
    paddy only). Returns a new frame; irrigation_mm includes the pond refill, pond_supply_mm is that part.
    surface: bare soil only, FAO-56's surface layer (build step 2a; rules.yaml bare_soil): {tew_mm, rew_mm, kc_max,
    de0_mm}; then df's kc is not used (see _run_bare_surface).
    sp_mm: a paddy's daily seepage and percolation (rules.yaml paddy_losses), lost on its wet days: a day that starts
    at field capacity (every ponded day, after the morning refill) or that the day's rain brings back to it; column
    sp_mm then holds the day's loss."""
    if surface is not None:
        if irrigate or (ponded is not None and np.asarray(ponded, dtype=bool).any()):
            raise ValueError("the FAO-56 surface layer is for bare soil, which is never irrigated or ponded")
        return _run_bare_surface(df, taw_mm, p_table, cn, dr0_mm, surface)
    n = len(df)
    cn = np.broadcast_to(np.asarray(cn, dtype=float), (n,))
    ponded = np.zeros(n, dtype=bool) if ponded is None else np.asarray(ponded, dtype=bool)
    rows, dr = [], dr0_mm
    for i, (rain, et0, kc) in enumerate(df[["rain_mm", "et0_mm", "kc"]].itertuples(index=False)):
        etc = kc * et0
        p = adjust_p(p_table, etc)
        q = scs_runoff_mm(rain, cn[i])
        if ponded[i]:                             # irrigated paddy: the pond refills the root zone every day
            irr = dr
        elif irrigate and dr > p * taw_mm:        # refill when Dr > RAW
            irr = dr
        else:
            irr = 0.0
        # the refill comes at the start of the day, before the day's water use, so Ks is taken after it
        if sp_mm is None:
            s = step(dr - irr, rain, q, 0.0, etc, taw_mm, p)
        else:
            start = dr - irr
            wet = start <= 0.0 or start - (rain - q) <= 0.0
            s = step(start, rain, q, 0.0, etc, taw_mm, p, loss_mm=float(sp_mm) if wet else 0.0)
        rows.append({**s, "irrigation_mm": irr, "pond_supply_mm": irr if ponded[i] else 0.0})
        rows[-1].update(rain_mm=rain, runoff_mm=q, etc_mm=etc, p=p, raw_mm=p * taw_mm, ponded=bool(ponded[i]))
        dr = rows[-1]["dr_mm"]
    out = pd.DataFrame(rows, index=df.index)
    out["dry_day"] = out["ks"] < 1.0
    return out


def _run_bare_surface(df, taw_mm, p_table, cn, dr0_mm, surface):
    """Bare soil, FAO-56 Chapter 7 (twin/evaporation.py): the day's evaporation E = Ke ETo (Kcb 0, few 1; Kr from the
    surface layer's depletion of the previous day) leaves the surface layer AND the root zone, which holds it (the
    layer is the top of the root zone). No Ks: bare soil has no transpiration and no water stress, so ETc = ETa = E
    (FAO-56 Example 31, column 8) unless the root zone reaches the wilting point (eq. 86), where E stops and the layer
    loses only what the bucket gave. Rain minus the same SCS runoff wets both; the root zone's balance is eq. 85."""
    from pipeline.twin import evaporation as ev

    n = len(df)
    cn = np.broadcast_to(np.asarray(cn, dtype=float), (n,))
    rows, dr, de = [], dr0_mm, float(surface["de0_mm"])
    for i, (rain, et0) in enumerate(df[["rain_mm", "et0_mm"]].itertuples(index=False)):
        q = scs_runoff_mm(rain, cn[i])
        d = ev.surface_day(de, et0, rain - q, surface["tew_mm"], surface["rew_mm"], surface["kc_max"])
        e_pot = e = d["e_mm"]
        dr_new, dp = dr - (rain - q) + e, 0.0
        if dr_new < 0:                                    # eq. 88
            dp, dr_new = -dr_new, 0.0
        if dr_new > taw_mm:                               # eq. 86
            e -= dr_new - taw_mm
            dr_new = taw_mm
            d["de_mm"] = max(de - (rain - q), 0.0) + e
        p = adjust_p(p_table, e_pot)
        rows.append({"dr_mm": dr_new, "ks": 1.0, "eta_mm": e, "dp_mm": dp, "irrigation_mm": 0.0, "pond_supply_mm": 0.0,
                     "rain_mm": rain, "runoff_mm": q, "etc_mm": e_pot, "p": p, "raw_mm": p * taw_mm, "ponded": False,
                     "ke": d["ke"], "kr": d["kr"], "de_start_mm": d["de_start_mm"], "de_mm": d["de_mm"],
                     "dpe_mm": d["dpe_mm"]})
        dr, de = dr_new, d["de_mm"]
    out = pd.DataFrame(rows, index=df.index)
    out["dry_day"] = out["ks"] < 1.0
    return out
