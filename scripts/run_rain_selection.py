"""Choose the central rain version on DHM gauge months it never saw, test the winner once on the locked 2026 months, and
check whether our wet and dry monsoons come in DHM's order (rules.yaml verification.rain_selection, year_order). A check:
it switches nothing and exports nothing (owner, 2026-11-14: 'Show me the result before switching').

Writes data/checks/<field>/rain_selection/selection.json and year_order.json. The 2026 rain is IMERG fetched by
pipeline/fetch/gpm.py into data/rain2026/ (never data/clean/<field>/gpm.parquet); until it exists the test is skipped."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.checks import rain_selection as rs  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.twin import inputs  # noqa: E402
from scripts.common import dhm_rain, write_json  # noqa: E402

FIXED = ("published", "corrected", "dhm_scaled")
TEST = ("2026-01-01", "2026-07-31")


def monthly(daily):
    """Complete-month totals of every column of a daily table: one row per (year, month)."""
    return pd.DataFrame({c: inputs.complete_month_totals(daily[c]) for c in daily})


def versions(published, products, bf, df, corr):
    """The three fixed versions of a daily IMERG series: as published, break-corrected (products in correction_products
    scaled by the record's factors bf) and DHM-scaled (the corrected rain times the record's DHM factors df)."""
    scale = products.isin(corr["correction_products"])
    cor, _ = inputs.apply_break_correction(published, bf, corr["correction_from"], scale)
    return pd.DataFrame({"published": published, "corrected": cor,
                         "dhm_scaled": cor * np.array([df[m] for m in cor.index.month])})


def record(clean, rules):
    """The record's daily versions (2001-2025) and the factors, refitted exactly as the weather table was built
    (pipeline/fetch/weather.correct_gpm_break, twin/inputs.with_rain) and checked against it."""
    corr = rules["gpm_series"]
    w = pd.read_parquet(clean / "weather.parquet")
    d = pd.DatetimeIndex(w["date"])
    prod = pd.read_parquet(clean / "gpm.parquet").set_index("date")["product"].reindex(d).astype(str)
    pub = pd.Series(w["rain_uncorrected_mm"].to_numpy(float), index=d)
    gpm_day = w["rain_source"].astype(str).to_numpy() == "gpm"
    fit = gpm_day & prod.isin(corr["correction_factor_products"]).to_numpy()
    bf = inputs.break_factors(pub.where(fit), tuple(corr["correction_reference_years"]), corr["correction_from"])
    cor, cal = pd.Series(w["rain_mm"].to_numpy(float), index=d), corr.get("gauge_calibration") or {}
    if cal.get("apply") and clean.name in cal.get("fields", []):     # central rain gauge-calibrated: back to break-corrected
        cor = cor / rs.calibrate(d.month, np.ones(len(d)), cal["factors"])
    dh = dhm_rain(rules)
    df = inputs.dhm_factors(cor, dh["normals_mm"], dh["years"])
    v = versions(pub, prod.where(gpm_day, "none"), bf, df, corr)
    gap = {c: float(np.max(np.abs(v[c].to_numpy() - x)))
           for c, x in (("corrected", cor.to_numpy()), ("dhm_scaled", inputs.with_rain(w, "dhm", dh)["rain_mm"].to_numpy()))}
    if max(gap.values()) > 1e-9:
        raise ValueError(f"the refitted versions differ from the weather table: {gap}")
    return v, bf, df


def rain_2026(field, bf, df, corr):
    """The 2026 test days' versions and a note on the fetch (products, missing days, the refetched Oct-Dec 2025 against
    the record), or (None, reason)."""
    p = ROOT / "data" / "rain2026" / "clean" / field / "gpm.parquet"
    if not p.exists():
        return None, f"not yet: no {p.relative_to(ROOT)}"
    g = pd.read_parquet(p).set_index("date")
    new = g.loc[TEST[0]:TEST[1]]
    old = pd.read_parquet(ROOT / "data" / "clean" / field / "gpm.parquet").set_index("date")["rain_mm"]
    both = g["rain_mm"].reindex(old.index).dropna()
    note = {"file": str(p.relative_to(ROOT)), "products": new["product"].value_counts().to_dict(),
            "days": len(new), "days_missing": int(new["rain_mm"].isna().sum()),
            "refetched_days_also_in_record": len(both),
            "refetched_max_abs_diff_mm": round(float((both - old[both.index]).abs().max()), 6) if len(both) else None}
    return versions(new["rain_mm"].astype(float), new["product"].astype(str), bf, df, corr), note


def wettest(b, daily, f_all, months):
    """Each candidate's wettest day of the month over the gauge's printed wettest day (rain_selection.wettest_day)."""
    if "max_24h_mm" not in b:
        return "no wettest-day column (max_24h_mm) in the bulletin table yet"
    daily = daily.assign(gauge_calibrated=rs.calibrate(daily.index.month, daily["corrected"], f_all))
    top = daily.groupby([daily.index.year, daily.index.month]).max()
    out = {}
    for part, ok in months.items():
        x = b[ok(b) & (b["max_24h_mm"] > 0)]
        x = x[[k in top.index for k in zip(x["year"], x["month"])]]
        r = {c: top.loc[list(zip(x["year"], x["month"])), c].to_numpy() / x["max_24h_mm"].to_numpy() for c in rs.CANDIDATES}
        out[part] = {"n": len(x), **{c: {"median": round(float(np.median(v)), 2), "min": round(float(v.min()), 2),
                                         "max": round(float(v.max()), 2)} for c, v in r.items() if len(v)},
                     "by_gauge_median": {st: {c: round(float(np.median(r[c][(x["station"] == st).to_numpy()])), 2)
                                              for c in rs.CANDIDATES} for st in x["station"].unique()}}
    return out


def year_orders(field, daily, f_all, stations):
    """year_order.json: each version's June-September totals (2001-2025) against DHM's yearly monsoon reports."""
    p = ROOT / "data" / "clean" / field / "dhm_monsoon_years.csv"
    if not p.exists():
        return {"status": f"not yet: no {p.relative_to(ROOT)}"}
    y = pd.read_csv(p)
    y = y[y["station"].isin(stations)]
    pct = y.pivot_table(index="year", columns="station", values="pct_of_normal", aggfunc="first")
    ref = {"mean_of_stations": pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 2),
           **{st: pct[st] for st in pct.columns}}
    jjas = daily[daily.index.month.isin(rs.JJAS) & (daily.index.year <= 2025)]
    jjas = jjas.assign(gauge_calibrated=jjas["corrected"] * f_all["jjas"]).groupby(jjas.index.year).sum()
    by_year = lambda s: {int(k): round(float(v), 1) for k, v in s.dropna().items()}  # noqa: E731
    return {"stations_pct_of_normal": {st: by_year(s) for st, s in ref.items()},
            "ours_jjas_mm": {c: by_year(jjas[c]) for c in rs.CANDIDATES},
            "versions": {c: {st: rs.year_order(jjas[c], s) for st, s in ref.items()} for c in rs.CANDIDATES}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    rules = load_rules()
    sel, corr = rules["verification"]["rain_selection"], rules["gpm_series"]
    tol, min_mm = rules["verification"]["outputs"]["rain_months"]["tolerance_rel"], sel["months"]["min_gauge_mm"]
    clean = ROOT / "data" / "clean" / a.field
    daily, bf, df = record(clean, rules)
    b = pd.read_csv(clean / "dhm_bulletin_months.csv")
    b = b[b["station"].isin(sel["gauges"])].rename(columns={"rain_mm": "gauge_mm"})
    is_sel = lambda x: x["year"] * 100 + x["month"] <= 202512  # noqa: E731
    is_test = lambda x: (x["year"] == 2026) & (x["month"] <= 7)  # noqa: E731
    keep = ["station", "year", "month", "gauge_mm", "note"]

    def table(part, m):
        t = b[part(b)][keep].merge(m.rename_axis(["year", "month"]).reset_index(), on=["year", "month"], how="left")
        return t.assign(note=t["note"].fillna(""))

    t = table(is_sel, monthly(daily))
    per, pooled = rs.leave_one_gauge_out(t, tol, min_mm)
    win = rs.winner(pooled)
    f_all = rs.season_factors(t["month"], t["gauge_mm"], t["corrected"])
    scored = t[t["gauge_mm"] >= min_mm]
    out = {"rules": "config/rules.yaml verification.rain_selection (committed eb3a57d before this run)",
           "tolerance_rel": tol, "min_gauge_mm": min_mm, "gauges": sel["gauges"],
           "factors": {"break_by_month": {inputs.MONTH_NAMES[m - 1]: round(f, 4) for m, f in bf.items()},
                       "dhm_by_month": {inputs.MONTH_NAMES[m - 1]: round(f, 4) for m, f in df.items()},
                       "gauge_calibrated_all_four_gauges": {k: round(v, 4) for k, v in f_all.items()},
                       "gauge_calibrated_fit": "ratio of sums over every selection month with a gauge value (months under "
                                               "min_gauge_mm included: they are not scored, but they are selection months)"},
           "selection": {"months": f"{t['year'].min()}-{t.loc[t['year'] == t['year'].min(), 'month'].min():02d} to 2025-12",
                         "per_gauge": per, "pooled": pooled, "winner": win,
                         "corrected_over_gauge_sum_ratio": {st: round(float(x["corrected"].sum() / x["gauge_mm"].sum()), 3)
                                                            for st, x in scored.groupby("station", sort=False)},
                         "listed_not_scored": t.loc[t["gauge_mm"] < min_mm, keep[:4]].values.tolist(),
                         "missing": t.loc[t["gauge_mm"].isna(), ["station", "year", "month", "note"]].values.tolist()},
           "months": t.round(1).values.tolist(), "months_columns": list(t.columns)}
    d26, note = rain_2026(a.field, bf, df, corr)
    out["rain_2026"] = note
    if d26 is not None:
        u = table(is_test, monthly(d26))
        u = u.assign(gauge_calibrated=rs.calibrate(u["month"], u["corrected"], f_all))
        res = {c: rs.summary(*rs.judged(u[c], u["gauge_mm"], tol, min_mm)) for c in rs.CANDIDATES}
        by_gauge = {st: {c: rs.summary(*rs.judged(x[c], x["gauge_mm"], tol, min_mm)) for c in rs.CANDIDATES}
                    for st, x in u.groupby("station", sort=False)}
        sus = u[u["note"].str.contains("SUSPECT")]
        out["test_2026"] = {"winner": win, "result": res[win], "every_candidate": res, "per_gauge": by_gauge,
                            "listed_not_scored": u.loc[u["gauge_mm"] < min_mm, keep[:4]].values.tolist(),
                            "missing": u.loc[u["gauge_mm"].isna(), ["station", "year", "month"]].values.tolist(),
                            "suspect": sus.drop(columns="note").round(1).to_dict("records"),
                            "suspect_handling": "scored as printed: the gauge reads under min_gauge_mm, so the month is "
                                                "listed, not scored, by the rule every month follows",
                            "months": u.round(1).values.tolist(), "months_columns": list(u.columns)}
        daily = pd.concat([daily, d26])
    out["wettest_day"] = wettest(b, daily, f_all, {"selection": is_sel, "test_2026": is_test})
    dest = ROOT / "data" / "checks" / a.field / "rain_selection"
    print(f"winner: {win}; pooled: " + ", ".join(f"{c} {p['k']}/{p['n']}" for c, p in pooled.items()))
    print("->", write_json(dest / "selection.json", out))
    print("->", write_json(dest / "year_order.json", year_orders(a.field, daily, f_all, sel["gauges"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
