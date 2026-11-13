"""A section's status and wetness from the twin's state (build step 8; rules.yaml sections.status_red_ks_below).
Pure functions.

FAO-56 eq. 84: Ks = (TAW - Dr) / ((1 - p) TAW) = (TAW - Dr) / (TAW - RAW) once Dr > RAW, else 1.
- green: Dr <= RAW (Ks = 1, no water stress);
- red: Ks < status_red_ks_below (0.5: the crop gets less than half the water it would use unstressed);
- yellow: in between;
- grey: no twin state (unknown).
wetness_pct = 100 x (1 - Dr / TAW). Every section shares the one twin state (one soil cell, one weather cell, one crop
calendar): until the probe reads a part, all parts show the same status and wetness.
"""
import math


def _num(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def _check(dr_mm, taw_mm, raw_mm):
    if not taw_mm > 0:
        raise ValueError(f"TAW must be positive, got {taw_mm}")
    if not 0 <= raw_mm <= taw_mm:
        raise ValueError(f"RAW {raw_mm} must lie between 0 and TAW {taw_mm}")
    if not 0 <= dr_mm <= taw_mm:
        raise ValueError(f"root-zone depletion {dr_mm} mm must lie between 0 and TAW {taw_mm} mm")


def ks(dr_mm, taw_mm, raw_mm):
    _check(dr_mm, taw_mm, raw_mm)
    if dr_mm <= raw_mm:
        return 1.0
    return (taw_mm - dr_mm) / (taw_mm - raw_mm)


def wetness_pct(dr_mm, taw_mm):
    if not taw_mm > 0 or not 0 <= dr_mm <= taw_mm:
        raise ValueError(f"depletion {dr_mm} mm outside 0..TAW {taw_mm} mm")
    return 100.0 * (1.0 - dr_mm / taw_mm)


def status(dr_mm, taw_mm, raw_mm, red_ks_below):
    if not (_num(dr_mm) and _num(taw_mm) and _num(raw_mm)):
        return "grey"
    k = ks(dr_mm, taw_mm, raw_mm)
    if dr_mm <= raw_mm:
        return "green"
    return "red" if k < red_ks_below else "yellow"


def from_twin_state(state, red_ks_below, ks_tol=0.01, wetness_tol=0.5):
    """{'status', 'wetness_pct', 'ks'} from data/clean/<field>/twin_state.json (None: grey, no wetness). The file's
    own ks and wetness_pct must agree with its dr_mm, taw_mm and raw_mm (to rounding), or this fails loudly."""
    if state is None:
        return {"status": "grey", "wetness_pct": None, "ks": None}
    dr, taw, raw = (state.get(k) for k in ("dr_mm", "taw_mm", "raw_mm"))
    if not (_num(dr) and _num(taw) and _num(raw)):
        return {"status": "grey", "wetness_pct": None, "ks": None}
    k, w = ks(dr, taw, raw), wetness_pct(dr, taw)
    if _num(state.get("ks")) and abs(state["ks"] - k) > ks_tol:
        raise ValueError(f"twin state ks {state['ks']} disagrees with its bucket ({k:.4f})")
    if _num(state.get("wetness_pct")) and abs(state["wetness_pct"] - w) > wetness_tol:
        raise ValueError(f"twin state wetness_pct {state['wetness_pct']} disagrees with its bucket ({w:.2f})")
    return {"status": status(dr, taw, raw, red_ks_below), "wetness_pct": w, "ks": k}
