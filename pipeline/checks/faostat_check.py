"""Nepal's national yields (FAOSTAT) against the twin's harvest %, year to year (VALIDATION 4.3; rules.yaml
validation_checks.faostat, written before the first run). Pure. Both series are turned into first differences (this
year minus last year), which removes the steady rise of national yields without fitting a trend. A national number mixes
the plains and the hills, irrigation, seed and fertiliser: one 60 m placeholder field's weather is a small part of it.
"""
import pandas as pd

from pipeline.checks import corr_ci as cc
from pipeline.fetch import guards as g

TO_KG_HA = {"kg/ha": 1.0, "hg/ha": 0.1}


def parse_items(rows, items, area="149", first_year=2001):
    """Nepal (area 149) yields of the given FAOSTAT item codes ({'116': 'potato'}) from bulk-file rows, kg/ha, as
    pipeline/fetch/faostat.parse does for rice, wheat and maize (unknown unit, repeated year or a yield <= 0 fail)."""
    out = []
    for r in rows:
        if r["Area Code"] != area or r["Item Code"] not in items or r["Element"] != "Yield":
            continue
        y = int(r["Year"])
        if y < first_year or not r["Value"]:
            continue
        if r["Unit"] not in TO_KG_HA:
            raise g.DataGuardError(f"FAOSTAT yield unit '{r['Unit']}' is not one we know how to convert")
        out.append({"year": y, "crop": items[r["Item Code"]], "item": r["Item"],
                    "yield_kg_ha": float(r["Value"]) * TO_KG_HA[r["Unit"]], "flag": r.get("Flag", "")})
    df = pd.DataFrame(out, columns=["year", "crop", "item", "yield_kg_ha", "flag"])
    if df.duplicated(["year", "crop"]).any():
        raise g.DataGuardError("repeated year and crop in FAOSTAT rows")
    if (df["yield_kg_ha"] <= 0).any():
        raise g.DataGuardError("FAOSTAT yield of zero or less")
    return df.sort_values(["crop", "year"]).reset_index(drop=True)


def first_difference_check(fao, twin):
    """fao, twin: Series by year. Correlation of the first differences over consecutive shared years, and the share of
    years in which both move the same way."""
    yrs = sorted(set(fao.index) & set(twin.index))
    f, t = fao.reindex(yrs).astype(float), twin.reindex(yrs).astype(float)
    df = pd.DataFrame({"fao": f.diff(), "twin": t.diff()}, index=yrs)
    df = df[[y - 1 in yrs for y in df.index]].dropna()
    out = {"years": [int(y) for y in df.index], "holds_up": False, "correlation": None,
           "fao_diff": {int(y): round(float(v), 1) for y, v in df["fao"].items()},
           "twin_diff": {int(y): round(float(v), 2) for y, v in df["twin"].items()}}
    if cc.is_degenerate(t):
        out["status"] = "not testable: the twin's harvest is one value in more than half of the years"
        return out
    moved = (df["fao"] != 0) & (df["twin"] != 0)
    out["same_sign_share"] = round(float(((df["fao"] > 0) == (df["twin"] > 0))[moved].mean()), 3) if moved.any() else None
    out["correlation"] = cc.correlate(df["twin"], df["fao"])
    out["holds_up"] = cc.excludes_zero(out["correlation"]["spearman_ci"], +1)
    out["status"] = "holds up" if out["holds_up"] else "does not hold up (the Spearman interval reaches 0)"
    return out
