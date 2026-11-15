"""Real water and honest words (owner's probe brief, 2026-11-14, fix 4). Pure, except load_calibration (reads a file).

- The bench calibration (config/probe_calibration.yaml, written by scripts/run_probe_bench.py from the team's real cups)
  turns the probe's settled median (its own 0-100 %, air 0, water 100) into water % (volume of water per volume of soil,
  x 100): apply_fit. Without that file there is no water % (the site says only drier or wetter than the other parts:
  relative).
- band: from the field's own soil (SoilGrids water at 33 and 1500 kPa over the top probe_depth_m) and the depletion
  fraction p of the crop growing now (crops.json, FAO-56 Table 22): 'needs water' below the point where the crop starts
  to suffer (theta_fc - p (theta_fc - theta_wp), FAO-56 eq. 84), 'good' up to field capacity, 'too wet' above it.
- For the Kalman update: water % -> the twin's root-zone wetness (wetness_from_water), and the bench's R in probe
  percent -> wetness points squared (r_twin_var). Rules: config/rules.yaml probe.band, probe.kalman.r and .z.
"""
from pathlib import Path


def apply_fit(probe_pct, fit):
    """water % = a + b x + (c x^2 for a quadratic), x the probe's percent."""
    c = fit["coef"]
    x = float(probe_pct)
    return c[0] + c[1] * x + (c[2] * x * x if fit["model"] == "quadratic" else 0.0)


def slope_at(probe_pct, fit):
    """d water % / d probe % at the reading."""
    c = fit["coef"]
    return c[1] + (2.0 * c[2] * float(probe_pct) if fit["model"] == "quadratic" else 0.0)


def depth_theta(layers, depth_m):
    """(theta_fc, theta_wp): depth-weighted means of SoilGrids layers (top_cm, bottom_cm, theta_fc_m3m3, theta_wp_m3m3)
    over 0..depth_m."""
    fc = wp = total = 0.0
    for _, r in layers.iterrows():
        top, bottom = r["top_cm"] / 100.0, min(r["bottom_cm"] / 100.0, depth_m)
        if bottom > top:
            fc += r["theta_fc_m3m3"] * (bottom - top)
            wp += r["theta_wp_m3m3"] * (bottom - top)
            total += bottom - top
    if total <= 0:
        raise ValueError(f"no soil layer inside 0..{depth_m} m")
    return fc / total, wp / total


def band(water_pct, theta_fc, theta_wp, p):
    """rules.yaml probe.band: 'needs water' below theta_fc - p (theta_fc - theta_wp), 'good' up to theta_fc, 'too wet'
    above it (all in water %)."""
    if theta_fc <= theta_wp or not 0 < p < 1:
        raise ValueError(f"impossible soil or p: fc {theta_fc}, wp {theta_wp}, p {p}")
    low = round(100.0 * (theta_fc - p * (theta_fc - theta_wp)), 2)
    high = round(100.0 * theta_fc, 2)
    w = float(water_pct)
    word = "needs water" if w < low else ("too wet" if w > high else "good")
    return {"band": word, "needs_water_below_pct": low, "too_wet_above_pct": high}


def wetness_from_water(water_pct, theta_fc, theta_wp):
    """rules.yaml probe.kalman.z: the twin's wetness (0 wilting point, 100 field capacity) of an evenly wet root zone."""
    if theta_fc <= theta_wp:
        raise ValueError(f"theta_fc {theta_fc} must be above theta_wp {theta_wp}")
    return 100.0 * (float(water_pct) / 100.0 - theta_wp) / (theta_fc - theta_wp)


def r_twin_var(r_probe_pct2, slope_water_per_probe, theta_fc, theta_wp, fit_var=0.0):
    """rules.yaml probe.kalman.r: R in the twin's wetness points squared (chain rule probe % -> water % -> wetness).
    fit_var (water-% points squared): the calibration's own error, added for the spoon method (probe.bench.spoon.use)."""
    return (r_probe_pct2 * slope_water_per_probe ** 2 + fit_var) / (theta_fc - theta_wp) ** 2


def relative(value, others, same_band):
    """rules.yaml probe.same_band_pct: 'drier' / 'wetter' than the median of the other parts, or 'about the same'."""
    others = sorted(float(o) for o in others)
    if not others:
        return None
    n = len(others)
    med = others[n // 2] if n % 2 else (others[n // 2 - 1] + others[n // 2]) / 2.0
    d = float(value) - med
    return "drier" if d < -same_band else ("wetter" if d > same_band else "about the same")


def load_calibration(path):
    """config/probe_calibration.yaml, or None when there is none yet. It must say it was made from a bench test."""
    import yaml
    path = Path(path)
    if not path.exists():
        return None
    c = yaml.safe_load(path.read_text())
    if "bench test" not in str(c.get("made_from", "")) or "fake" in str(c.get("made_from", "")).lower():
        raise ValueError(f"{path} does not say it was made from a real bench test: not used")
    for k in ("fit", "mae_water_pct", "r_probe_pct2", "cups", "date"):
        if k not in c:
            raise ValueError(f"{path} lacks '{k}'")
    return c
