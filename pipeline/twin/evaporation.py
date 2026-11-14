"""Bare-soil evaporation from the surface layer only, FAO-56 Chapter 7 (Allen et al. 1998; eqs. 71-79,
https://www.fao.org/4/x0490e/x0490e0c.htm, read 2026-11-14). Pure functions.

Build step 2a (2026-11-13, night; REVIEW_NOTES M7, METHOD_NOTES 18): replaces the constant bare-soil Kc 0.3, which
drew water from the next crop's whole root zone, once rules.yaml bare_soil.apply is switched on. On a bare day
(Kcb = 0, few = 1, fw = 1 for rain, no irrigation, no transpiration; FAO-56 Example 31):
  Kc max = 1.20 (eq. 72 with h = 0 and Kcb = 0),  Kr = 1 while De <= REW, else (TEW - De) / (TEW - REW)  (eq. 74),
  Ke = min(Kr (Kc max - Kcb), few Kc max)  (eq. 71),  E = Ke ET0,
  De = De_prev - (P - RO) - I/fw + E/few + DPe, DPe = max(0, (P - RO) + I/fw - De_prev), 0 <= De <= TEW  (eqs. 77-79),
  TEW = 1000 (theta_fc - 0.5 theta_wp) Ze  (eq. 73),  REW from Table 19 by USDA texture class.
The day's wetting comes after the day's evaporation (Kr from the previous day's depletion, eq. 74 as printed) unless
`wetting_first` (FAO-56 Example 35, note 9: rain or irrigation early in the day). The twin couples E to its root-zone
bucket in soil_water.run_bucket (surface layer = the top of the root zone)."""
import math

# FAO-56 eq. 72: Kc max = max({1.2 + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h / 3)^0.3}, {Kcb + 0.05})


def kc_max(u2_ms, rhmin_pct, h_m, kcb):
    """FAO-56 eq. 72. h: mean maximum plant height in the period (m); bare soil h = 0 gives 1.2 in any climate."""
    return float(max(1.2 + (0.04 * (u2_ms - 2.0) - 0.004 * (rhmin_pct - 45.0)) * (max(h_m, 0.0) / 3.0) ** 0.3,
                     kcb + 0.05))


def tew_mm(theta_fc, theta_wp, ze_m):                                       # eq. 73
    return 1000.0 * (theta_fc - 0.5 * theta_wp) * ze_m


def tew_from_layers(layers, ze_m):
    """TEW (eq. 73) over 0..ze_m from SoilGrids-style layers (top_cm, bottom_cm, theta_fc_m3m3, theta_wp_m3m3),
    each layer weighted by its depth inside 0..Ze."""
    total = 0.0
    for _, r in layers.iterrows():
        top, bottom = r["top_cm"] / 100.0, min(r["bottom_cm"] / 100.0, ze_m)
        if bottom > top:
            total += tew_mm(r["theta_fc_m3m3"], r["theta_wp_m3m3"], bottom - top)
    if not total > 0:
        raise ValueError(f"TEW over 0..{ze_m} m is {total} mm: the soil table has no water contents near the surface")
    return total


def kr(de_mm, tew, rew):                                                    # eq. 74
    if de_mm <= rew:
        return 1.0
    return max(0.0, (tew - de_mm) / (tew - rew))


def ke(kr_value, kc_max_value, kcb, few):                                   # eq. 71
    return min(kr_value * (kc_max_value - kcb), few * kc_max_value)


def surface_day(de_prev_mm, et0_mm, p_minus_ro_mm, tew_mm, rew_mm, kc_max, kcb=0.0, few=1.0, irrigation_mm=0.0, fw=1.0,
                wetting_first=False):
    """One day of the surface layer (eqs. 71, 74, 77-79; transpiration from the layer Tew = 0). Returns de_start_mm (the
    depletion Kr is taken from), kr, ke, e_mm (= Ke ET0, over the whole field), dpe_mm, de_mm (end of day)."""
    if not 0.0 < rew_mm < tew_mm:
        raise ValueError(f"REW ({rew_mm} mm) must be above 0 and below TEW ({tew_mm} mm)")
    wet = p_minus_ro_mm + (irrigation_mm / fw if irrigation_mm else 0.0)
    dpe = max(0.0, wet - de_prev_mm)                                         # eq. 79
    after_wetting = max(de_prev_mm - wet, 0.0)
    de0 = after_wetting if wetting_first else de_prev_mm
    k = kr(de0, tew_mm, rew_mm)
    e = ke(k, kc_max, kcb, few) * et0_mm
    de = after_wetting + e / few                                             # eq. 77
    if de > tew_mm:                                                          # eq. 78: no more water to evaporate
        e = (tew_mm - after_wetting) * few
        de = tew_mm
    return {"de_start_mm": de0, "kr": k, "ke": e / et0_mm if et0_mm > 0 else 0.0, "e_mm": e, "dpe_mm": dpe, "de_mm": de}


def de_start_mm(dr_mm, taw_mm, tew):
    """rules.yaml bare_soil.de_start: De at the first day of a bare spell = TEW x Dr / TAW (FAO-56's two stated starts,
    0 after heavy wetting and TEW after a long dry period, at the two ends; the twin's hand-over fraction between)."""
    if taw_mm <= 0:
        raise ValueError(f"TAW is {taw_mm} mm")
    return float(min(max(dr_mm / taw_mm, 0.0), 1.0) * tew)


def usda_texture(sand_pct, silt_pct, clay_pct):
    """USDA texture class from the three fractions (SSSA Glossary of Soil Science Terms 2022, 'soil texture'; USDA
    Soil Survey Manual), in the order of the NRCS texture calculator."""
    sand, silt, clay = float(sand_pct), float(silt_pct), float(clay_pct)
    if not math.isclose(sand + silt + clay, 100.0, abs_tol=1.0):
        raise ValueError(f"sand + silt + clay = {sand + silt + clay:.1f} %, not 100")
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52) or (clay < 7 and silt < 50):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def rew_mm(texture, table_19, no_row=None):
    """The midpoint of FAO-56 Table 19's REW range for the texture class (rules.yaml bare_soil.table_19_rew_mm); for a
    class with no row, the midpoint of FAO-56's general range `no_row` (rules.yaml bare_soil.rew_no_row_mm, 5-12 mm)."""
    if texture not in table_19:
        if no_row is None:
            raise ValueError(f"FAO-56 Table 19 has no REW row for '{texture}': set REW for this field by hand")
        lo, hi = no_row
        return (lo + hi) / 2.0
    lo, hi = table_19[texture]
    return (lo + hi) / 2.0


def bare_soil_setting(rules_bare, soil, method="rules"):
    """The twin's bare-soil argument (season.simulate `bare_kc`): the constant Kc (old method, a number) or, for
    FAO-56's surface layer, a dict with TEW from the soil table over 0..Ze and REW from the top layer's texture class.
    rules_bare: the loaded rules.yaml bare_soil block. method: 'rules' (apply on: FAO-56; off: the constant Kc),
    'kc' or 'fao56'."""
    if method not in ("rules", "kc", "fao56"):
        raise ValueError(f"bare-soil method '{method}' is not one of rules, kc, fao56")
    if method == "kc" or (method == "rules" and not rules_bare.get("apply")):
        return rules_bare["kc"]
    top = soil.sort_values("top_cm").iloc[0]
    sand, clay = float(top["sand_pct"]), float(top["clay_pct"])
    texture = usda_texture(sand, 100.0 - sand - clay, clay)
    ze = float(rules_bare["ze_m"])
    out = {"method": "fao56_surface_layer", "ze_m": ze, "tew_mm": float(tew_from_layers(soil, ze)),
           "rew_mm": float(rew_mm(texture, rules_bare["table_19_rew_mm"], rules_bare.get("rew_no_row_mm"))),
           "kc_max": float(rules_bare["kc_max"]),
           "texture": texture, "top_layer_pct": {"sand": sand, "silt": round(100.0 - sand - clay, 1), "clay": clay}}
    if texture not in rules_bare["table_19_rew_mm"]:     # only then, so a field with a Table 19 row is labelled as before
        out["rew_from"] = "FAO-56 ch. 7 general range 5-12 mm (no Table 19 row for this texture; rules.yaml bare_soil.rew_no_row_mm)"
    return out
