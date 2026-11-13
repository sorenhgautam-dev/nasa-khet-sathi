"""The twin's water stress against HLS peak greenness, season by season (VALIDATION 4.2; rules.yaml
validation_checks.twin_vs_hls, written before the first run). Pure.

Monsoon: the twin's rice season of year Y with the satellite's monsoon season whose peak is in Y; winter: the twin's
winter crop harvested in Y with the satellite's winter season whose peak is in Y. HLS years only (MODIS seasons are not
comparable). The satellite's anomaly is a season's peak NDVI minus its slot's mean peak. Peak NDVI is green cover, not
harvest.
"""
import pandas as pd

from pipeline.checks import corr_ci as cc
from pipeline.checks.ecostress_check import slot_of_crop_season
from pipeline.diary.guess import slot_of

TWIN_COLS = ["eta_over_etc", "dry_days", "harvest_pct"]


def pair(twin_seasons, hls_by_year, source="hls"):
    sat = {}
    for rows in hls_by_year.values():
        for s in rows:
            if s.get("source") != source:
                continue
            t = {k: pd.Timestamp(s[k]) for k in ("start", "peak", "end")}
            sat[(t["peak"].year, slot_of(t))] = {"sat_start": str(t["start"].date()), "sat_peak": str(t["peak"].date()),
                                                 "sat_end": str(t["end"].date()), "peak_ndvi": float(s["peak_ndvi"])}
    rows = []
    for s in twin_seasons:
        slot = slot_of_crop_season(s["start"], s["end"])
        hit = sat.get((int(s["year"]), slot))
        if hit is None:
            continue
        rows.append({"year": int(s["year"]), "slot": slot, "crop": s["crop"], "twin_start": s["start"], "twin_end": s["end"],
                     **{c: float(s[c]) for c in TWIN_COLS}, **hit})
    df = pd.DataFrame(rows)
    if len(df):
        df["peak_anomaly"] = df["peak_ndvi"] - df.groupby("slot")["peak_ndvi"].transform("mean")
    return df


def metric_result(df, metric, sign, min_seasons):
    """One slot's correlation of a twin metric with the peak-NDVI anomaly; 'agrees' when the Spearman interval excludes 0
    on the expected side (sign +1 or -1)."""
    out = {"metric": metric, "expected_sign": "+" if sign > 0 else "-", "n": int(len(df)), "agrees": False, "correlation": None}
    if len(df) < min_seasons:
        out["status"] = f"not testable: {len(df)} seasons, fewer than {min_seasons}"
        return out
    if cc.is_degenerate(df[metric]):
        out["status"] = "not testable: the twin's series is degenerate (more than half the seasons share one value)"
        return out
    r = cc.correlate(df[metric], df["peak_anomaly"])
    out["correlation"] = r
    out["agrees"] = cc.excludes_zero(r["spearman_ci"], sign)
    out["status"] = "agrees" if out["agrees"] else "no agreement shown (the Spearman interval reaches 0)"
    return out
