"""Choosing the central rain version on DHM gauges and months it never saw (rules.yaml verification.rain_selection), and
whether our wet and dry monsoons come in DHM's order (verification.year_order). Pure; the runner is
scripts/run_rain_selection.py."""
import numpy as np
import pandas as pd

from pipeline.checks import corr_ci, verify

JJAS = (6, 7, 8, 9)
CANDIDATES = ("published", "corrected", "dhm_scaled", "gauge_calibrated")


def season_factors(month, gauge_mm, corrected_mm):
    """{'jjas', 'other'}: ratio of sums gauge / corrected over the months with a gauge value, June-September and the rest."""
    t = pd.DataFrame({"m": month, "g": gauge_mm, "c": corrected_mm}).dropna()
    wet = t["m"].isin(JJAS)
    return {k: float(t.loc[s, "g"].sum() / t.loc[s, "c"].sum()) for k, s in (("jjas", wet), ("other", ~wet))}


def calibrate(month, corrected_mm, factors):
    """The corrected rain times the June-September factor in those months and the other factor elsewhere."""
    wet = np.isin(np.asarray(month), JJAS)
    return np.asarray(corrected_mm, float) * np.where(wet, factors["jjas"], factors["other"])


def judged(ours, gauge, tol, min_mm):
    """(within tol of the gauge, |ln(ours / gauge)|) for the months the gauge reads at least min_mm (fewer: listed only)."""
    o, g = np.asarray(ours, float), np.asarray(gauge, float)
    s = np.isfinite(o) & np.isfinite(g) & (g >= min_mm)
    with np.errstate(divide="ignore"):
        return np.array(verify.within(o[s], g[s], rel=tol), bool), np.abs(np.log(o[s] / g[s]))


def summary(hit, abslog):
    k, n = int(np.sum(hit)), len(hit)
    return {"n": n, "k": k, "share": round(k / n, 4) if n else None, "ci95": verify.wilson(k, n),
            "median_abs_log": round(float(np.median(abslog)), 4) if n else None}


def leave_one_gauge_out(t, tol, min_mm):
    """(per gauge, pooled) scores of every candidate. t: one row per gauge and month with station, month, gauge_mm,
    corrected, published and dhm_scaled; gauge_calibrated is fitted, for each held-out gauge, on the other gauges only."""
    per, pool = {}, {c: ([], []) for c in CANDIDATES}
    for st, test in t.groupby("station", sort=False):
        train = t[t["station"] != st]
        f = season_factors(train["month"], train["gauge_mm"], train["corrected"])
        test = test.assign(gauge_calibrated=calibrate(test["month"], test["corrected"], f))
        per[st] = {"factors": {k: round(v, 4) for k, v in f.items()}}
        for c in CANDIDATES:
            hit, al = judged(test[c], test["gauge_mm"], tol, min_mm)
            per[st][c] = summary(hit, al)
            pool[c][0].extend(hit)
            pool[c][1].extend(al)
    return per, {c: summary(*pool[c]) for c in CANDIDATES}


def winner(pooled):
    """Highest pooled share, a tie to the lower median |log ratio|; gauge_calibrated only if it beats the best other."""
    key = lambda c: (-pooled[c]["share"], pooled[c]["median_abs_log"])  # noqa: E731
    best = min((c for c in CANDIDATES if c != "gauge_calibrated"), key=key)
    return "gauge_calibrated" if key("gauge_calibrated") < key(best) else best


def dhm_class(pct):
    """DHM's bands (Monsoon 2025 summary, p. 2): below normal under 90%, near normal 90-110%, above normal over 110%."""
    return None if not np.isfinite(pct) else "below" if pct < 90 else "above" if pct > 110 else "near"


def year_order(ours_mm, ref_pct, year=2023, n_boot=corr_ci.N_BOOT):
    """One rain version's June-September totals (mm by year, the whole record: its % is of the record's mean) against
    DHM's % of normal by year: Spearman with its bootstrap interval, the share of shared years in the same DHM class,
    and `year`'s rank (1 = wettest of the shared years), % and class in each."""
    pct = 100 * ours_mm / ours_mm.mean()
    yrs = sorted(set(pct.dropna().index) & set(ref_pct.dropna().index))
    a, b = pct[yrs].astype(float), ref_pct[yrs].astype(float)
    c = corr_ci.correlate(a.to_numpy(), b.to_numpy(), n_boot=n_boot)
    same = [dhm_class(x) == dhm_class(y) for x, y in zip(a, b)]
    one = lambda s: {"rank": int(s.rank(ascending=False)[year]), "of": len(s), "pct": round(float(s[year]), 1),  # noqa: E731
                     "class": dhm_class(s[year])} if year in s.index else None
    return {"years": yrs, "n": c["n"], "spearman": c["spearman"], "spearman_ci": c["spearman_ci"],
            "holds_up": bool(c["spearman_ci"] and c["spearman_ci"][0] > 0),
            "class_agreement": {"k": sum(same), "n": len(same), "share": round(sum(same) / len(same), 4) if same else None,
                                "ci95": verify.wilson(sum(same), len(same))},
            str(year): {"ours": one(a), "dhm": one(b)}}
