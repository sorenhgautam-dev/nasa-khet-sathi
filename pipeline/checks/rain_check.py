"""Rain check B (owner's upgrade list item 1, 2026-11-13). Pure functions apart from reading the DHM normals table.

- DHM 1991-2020 normals (config/dhm_normals_1991_2020.csv): Kathmandu Airport from DHM's official 'Climate Normals'
  table (precipitation, maximum and minimum temperature); Bhaktapur, Changu Narayan and Nagarkot from the 'Normal'
  columns of Annex 1 of DHM's monthly bulletins (an asterisk there marks temperature normals averaged over the
  available years). Every number carries its document and page; transcribed by a research sub-agent, the airport
  row checked by Claude against the PDF image.
- Monthly climatology: the mean total of each calendar month over complete months only (every day has a value).
- Pettitt (1979, Applied Statistics 28:126-135) change-point test: U_t = sum over i <= t < j of sign(x_j - x_i),
  K = max |U_t|, p ~ 2 exp(-6 K^2 / (n^3 + n^2)).
"""
from pathlib import Path

import numpy as np
import pandas as pd

NORMALS = Path(__file__).resolve().parents[2] / "config" / "dhm_normals_1991_2020.csv"


def load_normals(path=NORMALS):
    return pd.read_csv(path)


def station_months(normals, station, variable):
    """{month: value} of one station's normals for one variable (months 1-12)."""
    g = normals[(normals["station"] == station) & (normals["variable"] == variable) & (normals["month"] != "annual")]
    return {int(m): float(v) for m, v in zip(g["month"], g["value"])}


def monthly_climatology(daily):
    """DataFrame indexed 1-12: mean_mm (mean of complete monthly totals) and years (complete months used)."""
    s = daily.sort_index()
    key = [s.index.year, s.index.month]
    total, have = s.groupby(key).sum(min_count=1), s.groupby(key).count()
    days = pd.Series([pd.Period(f"{y}-{m:02d}").days_in_month for y, m in total.index], index=total.index)
    ok = total[have == days]
    out = pd.DataFrame(index=pd.Index(range(1, 13), name="month"))
    out["mean_mm"] = ok.groupby(level=1).mean().reindex(out.index)
    out["years"] = ok.groupby(level=1).size().reindex(out.index).fillna(0).astype(int)
    return out


def pettitt(years, values):
    x = np.asarray(values, float)
    n = len(x)
    sgn = np.sign(x[None, :] - x[:, None])                       # sgn[i, j] = sign(x_j - x_i)
    u = np.array([sgn[: t + 1, t + 1:].sum() for t in range(n - 1)])
    t = int(np.argmax(np.abs(u)))
    k = float(np.abs(u[t]))
    p = float(min(1.0, 2 * np.exp(-6 * k ** 2 / (n ** 3 + n ** 2))))
    return {"k": k, "change_after": int(years[t]), "p": p, "n": n}


def complete_month_totals(daily):
    """Totals of calendar months whose every day has a value, indexed by (year, month)."""
    from pipeline.twin.inputs import complete_month_totals as cmt
    return cmt(daily)


def holdout_break_correction(gpm_months, station_months, ref_years, from_year):
    """Held-out test of the break correction (VALIDATION 3.9b): fit the monthly factors on the odd years from
    from_year and test on the even ones against the station, then the reverse; pooled over both halves.
    gpm_months, station_months: complete-month totals indexed by (year, month)."""
    pre = gpm_months[[ref_years[0] <= y <= ref_years[1] for y, _ in gpm_months.index]].groupby(level=1).mean()
    both = [i for i in gpm_months.index.intersection(station_months.index) if i[0] >= from_year]
    raw, cor, obs = [], [], []
    for fit_odd in (1, 0):
        fit = gpm_months[[y >= from_year and y % 2 == fit_odd for y, _ in gpm_months.index]]
        post = fit.groupby(level=1).mean()
        for y, m in both:
            if y % 2 != fit_odd:
                raw.append(gpm_months[(y, m)])
                cor.append(gpm_months[(y, m)] * pre[m] / post[m])
                obs.append(station_months[(y, m)])
    raw, cor, obs = np.array(raw), np.array(cor), np.array(obs)
    return {"months": int(len(obs)), "mae_raw_mm": float(np.mean(np.abs(raw - obs))),
            "mae_corrected_mm": float(np.mean(np.abs(cor - obs))),
            "ratio_raw": float(raw.sum() / obs.sum()), "ratio_corrected": float(cor.sum() / obs.sum())}


def step_ratio(yearly, from_year):
    """Mean yearly total from from_year on over the mean before it ({year: mm}): how big the step is."""
    after = [v for y, v in yearly.items() if y >= from_year]
    before = [v for y, v in yearly.items() if y < from_year]
    return float(np.mean(after) / np.mean(before))


def ratio_to_gauges(rain_by_month, gauges_by_month):
    """A rain series against the mean of nearby gauges over the months the gauges cover: totals are summed over
    the months before dividing (a dry month's own ratio means little). {month: mm}, {month: [mm per gauge]}."""
    months = sorted(m for m in gauges_by_month if m in rain_by_month)
    by_month, rain_sum, gauge_sum = {}, 0.0, 0.0
    for m in months:
        gm = float(np.mean(gauges_by_month[m]))
        r = float(rain_by_month[m])
        by_month[m] = {"rain_mm": round(r, 1), "gauge_mean_mm": round(gm, 1), "ratio": round(r / gm, 2) if gm > 0 else None}
        rain_sum, gauge_sum = rain_sum + r, gauge_sum + gm
    return {"months": months, "rain_mm": round(rain_sum, 1), "gauge_mean_mm": round(gauge_sum, 1),
            "ratio": round(rain_sum / gauge_sum, 2) if gauge_sum > 0 else None, "by_month": by_month}


def gauge_loss_year(table, drop_pct_points, min_months, min_years_before):
    """Rule (1) of rules.yaml gpm_series.break_test: the first year Y whose yearly mean IMERG gauge weight (at the
    field's cell) is at least drop_pct_points below the mean of all the years before it, and stays that far below in
    every later year. table: rows of 'month' ('YYYY-MM') and 'imerg_gauge_weight_pct'; a year counts with at least
    min_months values, and Y needs at least min_years_before counted years before it. Pure."""
    t = table.dropna(subset=["imerg_gauge_weight_pct"])
    g = t.groupby(t["month"].str[:4].astype(int))["imerg_gauge_weight_pct"]
    yearly = g.mean()[g.count() >= min_months]
    years = [int(y) for y in yearly.index]
    out = {"year": None, "yearly_mean_pct": {y: round(float(yearly[y]), 2) for y in years}}
    for k, y in enumerate(years):
        if k < min_years_before:
            continue
        before = float(yearly[years[:k]].mean())
        line = before - drop_pct_points
        if all(float(yearly[z]) <= line for z in years[k:]):
            below = t[(t["month"].str[:4].astype(int) == y) & (t["imerg_gauge_weight_pct"] <= line)]["month"]
            out.update(year=y, before_mean_pct=before, drop_pct_points=before - float(yearly[y]),
                       first_month_below=str(below.min()) if len(below) else None)
            return out
    return out


def break_test(gauge_table, gpm_yearly, chirps_yearly, rule):
    """rules.yaml gpm_series.break_test (committed 6d2919c before any run on the field abroad): the break is found only
    when (1) the gauge input is lost (gauge_loss_year), (2) Pettitt finds a change in the yearly GPM / CHIRPS ratio at
    p < pettitt_p_max within change_year_tolerance years of the loss, and (3) CHIRPS's own yearly totals do not change
    then. gpm_yearly, chirps_yearly: {year: mm}. Pure."""
    why = []
    if gauge_table is None or len(gauge_table) == 0:
        why.append("no gauge-weight series (IMERG monthly gaugeRelativeWeighting)")
    if not chirps_yearly:
        why.append("no CHIRPS yearly totals")
    if why:
        return {"found": False, "why_not": why}
    pmax, tol = rule["pettitt_p_max"], rule["change_year_tolerance"]
    loss = gauge_loss_year(gauge_table, rule["gauge_drop_pct_points"], rule["min_months_per_year"], rule["min_years_before"])
    y0 = loss["year"]
    years = sorted(set(gpm_yearly) & set(chirps_yearly))
    ratio = [gpm_yearly[y] / chirps_yearly[y] for y in years]
    pr = pettitt(years, ratio)
    pc = pettitt(years, [chirps_yearly[y] for y in years])
    pg = pettitt(years, [gpm_yearly[y] for y in years])

    def near(p):
        return y0 is not None and abs(p["change_after"] + 1 - y0) <= tol
    checks = {"gauge_loss": y0 is not None,
              "gpm_steps_against_chirps": bool(pr["p"] < pmax and near(pr)),
              "chirps_steady": bool(pc["p"] >= pmax or not near(pc))}
    texts = {"gauge_loss": f"no sustained gauge-weight fall of {rule['gauge_drop_pct_points']} points",
             "gpm_steps_against_chirps": "no significant change in GPM / CHIRPS at the gauge loss",
             "chirps_steady": "CHIRPS itself changes at the same time"}
    step = None
    if y0 is not None and any(y < y0 for y in years) and any(y >= y0 for y in years):
        step = float(np.mean([r for y, r in zip(years, ratio) if y >= y0]) / np.mean([r for y, r in zip(years, ratio) if y < y0]))
    return {"found": all(checks.values()), "year": y0, "checks": checks,
            "why_not": [texts[k] for k, v in checks.items() if not v], "gauge_loss": loss,
            "gpm_over_chirps_pettitt": pr, "chirps_pettitt": pc, "gpm_pettitt": pg, "years": years,
            "gpm_over_chirps": {y: round(float(r), 3) for y, r in zip(years, ratio)}, "step_gpm_over_chirps": step}
