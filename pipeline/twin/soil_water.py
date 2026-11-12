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


def step(dr_prev, rain_mm, runoff_mm, irrigation_mm, etc_mm, taw_mm, p):
    """One day. Ks from the start-of-day depletion; ETa limited so depletion never passes TAW."""
    raw = p * taw_mm
    k = ks(dr_prev, taw_mm, raw)
    eta = k * etc_mm
    dr = dr_prev - (rain_mm - runoff_mm) - irrigation_mm + eta
    dp = 0.0
    if dr < 0:                                            # eq. 88: water above field capacity drains
        dp, dr = -dr, 0.0
    if dr > taw_mm:                                       # eq. 86: cannot dry past wilting point
        eta -= dr - taw_mm
        dr = taw_mm
    return {"dr_mm": dr, "ks": k, "eta_mm": eta, "dp_mm": dp}


def run_bucket(df, taw_mm, p_table, cn, dr0_mm=0.0, irrigate=False, ponded=None):
    """df: rain_mm, et0_mm, kc (one row per day). cn: number or per-day array. ponded: per-day flags (irrigated
    paddy only). Returns a new frame; irrigation_mm includes the pond refill, pond_supply_mm is that part."""
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
        s = step(dr - irr, rain, q, 0.0, etc, taw_mm, p)
        rows.append({**s, "irrigation_mm": irr, "pond_supply_mm": irr if ponded[i] else 0.0})
        rows[-1].update(rain_mm=rain, runoff_mm=q, etc_mm=etc, p=p, raw_mm=p * taw_mm, ponded=bool(ponded[i]))
        dr = rows[-1]["dr_mm"]
    out = pd.DataFrame(rows, index=df.index)
    out["dry_day"] = out["ks"] < 1.0
    return out
