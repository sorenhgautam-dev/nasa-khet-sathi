"""The field's own field capacity from the team's tins (owner's item 4; notes/FIELD_CAPACITY_PROTOCOL.md; rules.yaml
field_capacity_measured). Pure functions; pipeline/fetch/field_visit.py reads the file.

Per tin: water held = (wet - dry) / tin volume (1 g of water = 1 ml), bulk density = dry soil / tin volume. Per depth:
the median over the tins. The twin's soil table takes the measured value where a layer was measured (depth-weighted
where it is partly measured) and keeps the soil map's field capacity below, and the map's wilting point everywhere."""
import pandas as pd

PARTICLE_DENSITY_G_CM3 = 2.65       # mineral soil; a bulk density cannot exceed it (pore space = 1 - bd / 2.65)


def tin_values(tins):
    """Adds water_g, dry_soil_g, theta_fc_m3m3 and bulk_density_g_cm3; stops (ValueError) on an impossible tin."""
    t = tins.copy()
    t["water_g"] = t["wet_with_tin_g"] - t["dry_with_tin_g"]
    t["dry_soil_g"] = t["dry_with_tin_g"] - t["tin_empty_g"]
    t["theta_fc_m3m3"] = t["water_g"] / t["tin_volume_ml"]
    t["bulk_density_g_cm3"] = t["dry_soil_g"] / t["tin_volume_ml"]
    bad = t[(t["tin_volume_ml"] <= 0) | (t["water_g"] < 0) | (t["dry_soil_g"] <= 0)
            | (t["bulk_density_g_cm3"] >= PARTICLE_DENSITY_G_CM3) | ~t["theta_fc_m3m3"].between(0, 0.6)
            | (t["theta_fc_m3m3"] > 1 - t["bulk_density_g_cm3"] / PARTICLE_DENSITY_G_CM3)]
    if len(bad):
        raise ValueError("impossible tins (check the weighing and the volume; water 0-0.6 m3/m3 and within the pore "
                         f"space, bulk density below {PARTICLE_DENSITY_G_CM3}): {bad['tin'].tolist()}")
    return t


def depth_medians(tins):
    """One row per depth ('0-15'): top_cm, bottom_cm, theta_fc_m3m3 (median of the tins), n_tins."""
    g = tins.groupby("depth_cm")["theta_fc_m3m3"]
    out = pd.DataFrame({"theta_fc_m3m3": g.median(), "n_tins": g.size()}).reset_index()
    out[["top_cm", "bottom_cm"]] = out["depth_cm"].str.split("-", expand=True).astype(float)
    return out.sort_values("top_cm").reset_index(drop=True)


def _measured_share(top_cm, bottom_cm, medians):
    """(measured centimetres, sum of theta x centimetres) of the layer top..bottom."""
    cm, w = 0.0, 0.0
    for _, m in medians.iterrows():
        o = min(bottom_cm, m["bottom_cm"]) - max(top_cm, m["top_cm"])
        if o > 0:
            cm, w = cm + o, w + o * m["theta_fc_m3m3"]
    return cm, w


def root_zone_fc(medians, zr_m):
    """Depth-weighted measured field capacity over 0..zr_m, and how deep the measurements reach in it."""
    cm, w = _measured_share(0.0, 100.0 * zr_m, medians)
    return {"theta_fc_m3m3": w / cm if cm else None, "measured_depth_m": cm / 100.0}


def soil_with_measured_fc(soil, medians):
    """The soil table with each layer's field capacity from the measurements (map's value on its unmeasured part)."""
    s = soil.copy()
    for i, r in s.iterrows():
        cm, w = _measured_share(r["top_cm"], r["bottom_cm"], medians)
        if cm:
            s.at[i, "theta_fc_m3m3"] = (w + (r["bottom_cm"] - r["top_cm"] - cm) * r["theta_fc_m3m3"]) / (r["bottom_cm"] - r["top_cm"])
    low = s[s["theta_fc_m3m3"] <= s["theta_wp_m3m3"]]
    if len(low):
        raise ValueError(f"measured field capacity at or below the map's wilting point in layers {low['top_cm'].tolist()} cm")
    return s
