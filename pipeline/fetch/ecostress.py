"""ECOSTRESS LST and ESI over the field, cleaned from the box windows already on disk (no network): a CHECK on the twin
only (VALIDATION 4.2c). Never the twin's input and not shown to farmers.

    .venv/bin/python -m pipeline.fetch.ecostress --field demo

Raw: data/raw/eco_lste/<field>/*.tif (LST, QC, cloud) and data/raw/eco_esi/<field>/*.tif (ESI, cloud), 70 m, EPSG:32645,
cut by pipeline/fetch/cogwindows.py. The five traps of DATA_AUDIT 1.8 (REVIEW_2 L11), handled by the rules in
rules.yaml validation_checks.ecostress (written before the first run):
 1-2. V002 and V003 are mixed and flag cloud differently (V002 blanks LST under cloud, V003 does not): cloud = 1 is
      dropped in both, and QC and cloud are read only beside a valid value (cogwindows.layers_where_valid).
 3.   'Valid' LST ran from 14.6 K to 1,305.8 K: only QC bits 1-0 = 00 (best quality) and cloud-free pixels are kept,
      then every kept pixel of every window must lie in -98 to 70.7 C (the coldest and hottest land surface measured
      from space) or the run stops (golden rule 12c, decision D2); outside rule 12's -30 to 50 C is counted as a warning.
 4.   Overpasses with two or three product iterations: one granule per overpass, the latest build then iteration.
 5.   One 70 m pixel centre lies in the field: the field's value is that pixel (37% of it is field); the field-area-
      weighted mean of the pixels touching the field is kept beside it.
ESI is kept only where the same overpass has a kept LST at the pixel (ESI carries no QC layer of its own).
Writes data/clean/<field>/ecostress.parquet (one row per overpass) and data/cards/<field>/eco_clean.json.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch import guards as g

REPO = Path(__file__).resolve().parents[2]
LST_RANGE_C = (-98.0, 70.7)    # rules.yaml validation_checks.ecostress.clean_lst_range_c (Scambos 2018; Mildrexler 2011)
ESI_RANGE = (0.0, 1.0)         # ECOSTRESS Tiled User Guide V2, Table 11
UTC_OFFSET = pd.Timedelta(345, unit="min")      # Nepal, UTC+05:45
NAME = re.compile(r"ECOv(\d{3})_(L2T_LSTE|L4T_ESI)_(\d{5})_(\d{3})_(\w{5})_(\d{8}T\d{6})_(?:(\d{4})_)?(\d{2})$")


def parse_name(granule):
    m = NAME.match(granule)
    if not m:
        raise ValueError(f"not an ECOSTRESS tiled granule name: {granule}")
    ver, prod, orbit, scene, tile, ts, build, it = m.groups()
    return {"version": f"V{ver}", "product": prod, "orbit": orbit, "scene": scene, "tile": tile,
            "time_utc": pd.Timestamp(pd.to_datetime(ts, format="%Y%m%dT%H%M%S")), "build": build or "", "iteration": int(it)}


def overpass_key(granule):
    p = parse_name(granule)
    return p["version"], p["orbit"], p["scene"]


def latest_per_overpass(names):
    """One granule per (product, version, orbit, scene): the latest build, then the highest product iteration."""
    best = {}
    for n in names:
        p = parse_name(n)
        k = (p["product"], p["version"], p["orbit"], p["scene"])
        rank = (p["build"], p["iteration"])
        if k not in best or rank > best[k][0]:
            best[k] = (rank, n)
    return [v[1] for v in best.values()]


def qc_best(qc):
    """QC bits 1-0 = 00 (pixel produced, best quality; ECOL2 User Guide V3 Table 6). NaN is no QC (no value)."""
    q = np.asarray(qc, float)
    ok = np.isfinite(q)
    out = np.zeros(q.shape, bool)
    out[ok] = (q[ok].astype(np.int64) & 3) == 0
    return out


def clean_lst(lst_k, qc, cloud):
    """(LST in C with NaN where dropped, counts). Masks first (no value, QC not best, cloud), then fails loudly if a kept
    value lies outside LST_RANGE_C; kept values outside rule 12's -30 to 50 C are counted as warnings (D2)."""
    lst_k = np.asarray(lst_k, float)
    valid = np.isfinite(lst_k)
    from pipeline.fetch.cogwindows import layers_where_valid
    q, c = layers_where_valid(lst_k, qc, cloud, valid_range=(-np.inf, np.inf))
    best = qc_best(q)
    clear = np.isfinite(c) & (c == 0)
    keep = valid & best & clear
    out = np.where(keep, lst_k - 273.15, np.nan)
    warn = g.assert_in_range(out, "temp_c", "ecostress_lst_c", valid_range=LST_RANGE_C)
    return out, {"no_value": int((~valid).sum()), "qc_not_best": int((valid & ~best).sum()),
                 "cloud": int((valid & best & ~clear).sum()), "kept": int(keep.sum()), "rule12_warnings": int(warn)}


def clean_esi(esi, cloud, lst_kept):
    """(ESI with NaN where dropped, counts). A finite ESI outside 0 to 1 fails loudly; kept only if cloud = 0 and the same
    overpass's LST is kept at that pixel."""
    esi = np.asarray(esi, float)
    valid = np.isfinite(esi)
    bad = valid & ((esi < ESI_RANGE[0]) | (esi > ESI_RANGE[1]))
    if bad.any():
        raise g.DataGuardError(f"ESI: {int(bad.sum())} value(s) outside {ESI_RANGE} (e.g. {esi[bad][0]}). Not clipped.")
    from pipeline.fetch.cogwindows import layers_where_valid
    (c,) = layers_where_valid(esi, cloud, valid_range=ESI_RANGE)
    clear = np.isfinite(c) & (c == 0)
    lk = np.asarray(lst_kept, bool)
    keep = valid & clear & lk
    return np.where(keep, esi, np.nan), {"no_value": int((~valid).sum()), "cloud": int((valid & ~clear).sum()),
                                         "lst_not_kept": int((valid & clear & ~lk).sum()), "kept": int(keep.sum())}


def pixel_shares(geom, transform, shape, step=1.0):
    """{(row, col): share of that pixel covered by the polygon `geom` (in the grid's CRS)} for every pixel it touches,
    from a sub-grid of `step` metres."""
    from affine import Affine
    from rasterio.features import geometry_mask
    touch = ~geometry_mask([geom], out_shape=shape, transform=transform, all_touched=True)
    k = int(round(transform.a / step))
    out = {}
    for r, c in np.argwhere(touch):
        x0, y0 = transform.c + transform.a * c, transform.f + transform.e * r
        sub = Affine(step, 0, x0, 0, -step, y0)
        m = ~geometry_mask([geom], out_shape=(k, k), transform=sub, all_touched=False)
        if m.any():
            out[(int(r), int(c))] = float(m.mean())
    return out


def local_date(t_utc):
    return (pd.Timestamp(t_utc) + UTC_OFFSET).normalize()


def field_geometry(field, crs):
    from rasterio.warp import transform_geom
    ring = [list(p) for p in field["polygon"]] + [list(field["polygon"][0])]
    return transform_geom("EPSG:4326", crs, {"type": "Polygon", "coordinates": [ring]})


def _read(path):
    import rasterio
    with rasterio.open(path) as d:
        return d.read(), list(d.descriptions), d.tags(), d.crs, d.transform, d.shape


def build(field, data_dir=REPO / "data"):
    from rasterio.features import geometry_mask
    data_dir = Path(data_dir)
    sets = {s: sorted((data_dir / "raw" / s / field["id"]).glob("ECOv*.tif")) for s in ("eco_lste", "eco_esi")}
    if not sets["eco_lste"]:
        raise RuntimeError("no cached ECOSTRESS LSTE windows")
    chosen = {s: set(latest_per_overpass([f.stem for f in fs])) for s, fs in sets.items()}
    _, _, _, crs, tr, shape = _read(sets["eco_lste"][0])
    geom = field_geometry(field, crs)
    shares = pixel_shares(geom, tr, shape)
    centre = ~geometry_mask([geom], out_shape=shape, transform=tr, all_touched=False)
    cpix = [tuple(int(v) for v in rc) for rc in np.argwhere(centre)]
    if not cpix:
        raise ValueError("no 70 m pixel centre lies in the field")
    w_area = {rc: s for rc, s in shares.items()}                 # equal pixels: field area in a pixel is share x pixel area
    print(f"[ecostress] field pixel(s) {cpix}; touching pixels' field shares {({k: round(v, 3) for k, v in shares.items()})}")

    def at_field(a):
        centre_v = float(np.mean([a[rc] for rc in cpix]))
        vals = np.array([a[rc] for rc in w_area])
        wts = np.array(list(w_area.values()))
        all4 = bool(np.isfinite(vals).all())
        return centre_v, (float(np.sum(vals * wts) / wts.sum()) if all4 else np.nan)

    lst_kept_box, rows, totals = {}, {}, {"lst": {}, "esi": {}}
    dropped_iterations = {s: len(fs) - len(chosen[s]) for s, fs in sets.items()}
    for f in sets["eco_lste"]:
        if f.stem not in chosen["eco_lste"]:
            continue
        a, names, tags, c2, t2, sh2 = _read(f)
        if (str(c2), tuple(t2)[:6], sh2) != (str(crs), tuple(tr)[:6], shape):
            raise ValueError(f"{f.name}: not the box grid of the other windows")
        b = dict(zip(names, a))
        lst_c, n = clean_lst(b["LST"], b["QC"], b["cloud"])
        for k, v in n.items():
            totals["lst"][k] = totals["lst"].get(k, 0) + v
        key = overpass_key(f.stem)
        lst_kept_box[key] = np.isfinite(lst_c)
        p = parse_name(f.stem)
        fv, f4 = at_field(lst_c)
        reason = "kept" if np.isfinite(fv) else ("no value" if not np.isfinite(b["LST"][cpix[0]]) else
                                                 "qc not best" if not qc_best([b["QC"][cpix[0]]])[0] else "cloud")
        rows[key] = {"version": p["version"], "orbit": p["orbit"], "scene": p["scene"], "time_utc": p["time_utc"],
                     "local_date": local_date(p["time_utc"]),
                     "solar_hour": round((p["time_utc"].hour + p["time_utc"].minute / 60 + field["lon"] / 15) % 24, 2),
                     "lst_granule": f.stem, "lst_c": fv, "lst_c_touching": f4, "lst_reason": reason,
                     "esi_granule": None, "esi": np.nan, "esi_touching": np.nan, "esi_reason": "no ESI granule"}
    for f in sets["eco_esi"]:
        if f.stem not in chosen["eco_esi"]:
            continue
        a, names, tags, c2, t2, sh2 = _read(f)
        if (str(c2), tuple(t2)[:6], sh2) != (str(crs), tuple(tr)[:6], shape):
            raise ValueError(f"{f.name}: not the box grid of the other windows")
        b = dict(zip(names, a))
        key = overpass_key(f.stem)
        lk = lst_kept_box.get(key, np.zeros(shape, bool))
        esi, n = clean_esi(b["ESI"], b["cloud"], lk)
        for k, v in n.items():
            totals["esi"][k] = totals["esi"].get(k, 0) + v
        fv, f4 = at_field(esi)
        raw_v = b["ESI"][cpix[0]]
        reason = "kept" if np.isfinite(fv) else ("no value" if not np.isfinite(raw_v) else
                                                 "cloud" if b["cloud"][cpix[0]] == 1 else "LST not kept")
        p = parse_name(f.stem)
        row = rows.get(key) or {"version": p["version"], "orbit": p["orbit"], "scene": p["scene"], "time_utc": p["time_utc"],
                                "local_date": local_date(p["time_utc"]),
                                "solar_hour": round((p["time_utc"].hour + p["time_utc"].minute / 60 + field["lon"] / 15) % 24, 2),
                                "lst_granule": None, "lst_c": np.nan, "lst_c_touching": np.nan, "lst_reason": "no LSTE granule"}
        row.update({"esi_granule": f.stem, "esi": fv, "esi_touching": f4, "esi_reason": reason})
        rows[key] = row
    df = pd.DataFrame(list(rows.values())).sort_values("time_utc").reset_index(drop=True)
    out = data_dir / "clean" / field["id"] / "ecostress.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    kept_lst, kept_esi = int(np.isfinite(df["lst_c"]).sum()), int(np.isfinite(df["esi"]).sum())
    card = g.make_card(
        dataset="eco_clean", product="ECO_L2T_LSTE and ECO_L4T_ESI (ECOSTRESS tiled, V003 first, V002 for overpasses V003 lacks: D4)",
        version=f"V002 and V003 mixed; LSTE windows {len(sets['eco_lste'])}, ESI {len(sets['eco_esi'])}",
        variable=["LST", "QC", "cloud", "ESI"],
        units_in={"LST": "K", "QC": "bit flags", "cloud": "1 cloud, 0 clear", "ESI": "ratio 0-1"},
        units_out={"lst_c": "deg C (K - 273.15)", "esi": "ratio 0-1 (actual / potential ET, PT-JPL)"},
        scale_factor={"LST": 1.0, "ESI": 1.0},
        fill_values_removed={"LST": "NaN (file nodata)", "ESI": "NaN (file nodata)",
                             "QC and cloud": "read only beside a valid LST or ESI (they read 0 where there is no data)"},
        quality_flags_used={"LST": "QC bits 1-0 = 00 (best quality) and cloud = 0", "ESI": "cloud = 0 and the same overpass's LST kept at the pixel",
                            "box_pixel_counts": totals},
        records_dropped={"later_iteration_or_build_replaced": dropped_iterations,
                         "overpasses": int(len(df)), "field_lst_kept": kept_lst, "field_esi_kept": kept_esi,
                         "field_lst_reasons": df["lst_reason"].value_counts().to_dict(),
                         "field_esi_reasons": df["esi_reason"].value_counts().to_dict()},
        date_range=[str(df["local_date"].min().date()), str(df["local_date"].max().date())],
        time_zone="UTC times from the file names (TODO-VERIFY, DATA_AUDIT 1.8); local_date = UTC + 05:45",
        pixel_count={"centre_inside": len(cpix), "touching": len(shares),
                     "field_share_of_each_touching_pixel": {f"{r},{c}": round(v, 3) for (r, c), v in shares.items()}},
        source="NASA LP DAAC ECOSTRESS ECO_L2T_LSTE and ECO_L4T_ESI V003/V002 (cached box windows); ESI is model-based (PT-JPL)",
        resolution="70 m", raw_attrs={"from_card": "data/cards/<field>/eco_lste.json and eco_esi.json (cogwindows --card)"},
        range_warnings={"lst_c": {"rule": "temp_c -30 to 50 C (rule 12), hard limit -98 to 70.7 C", "pixels": totals["lst"].get("rule12_warnings", 0)}},
        location={"field_pixels_centre_inside": cpix, "grid": {"crs": str(crs), "transform": list(tr)[:6], "shape": list(shape)}},
        notes=("A check only (VALIDATION 4.2c). The field's value is the one 70 m pixel whose centre lies in the field: "
               f"{round(shares[cpix[0]] * 100)}% of that pixel is field, the rest is the land around it; the field is about 60 m, "
               "so 10 m sections can never differ in ECOSTRESS. Overpasses come at any hour of the day (solar_hour). "
               "After masking, no kept LST pixel anywhere in the box lies outside -98 to 70.7 C (the run would stop)."))
    card_path = g.write_card(card, data_dir / "cards" / field["id"])
    return {"table": out, "card": card_path, "overpasses": len(df), "lst_kept": kept_lst, "esi_kept": kept_esi, "totals": totals}


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    r = build(load_field(a.field))
    print(f"{r['overpasses']} overpasses; at the field pixel LST kept {r['lst_kept']}, ESI kept {r['esi_kept']}; "
          f"box counts {json.dumps(r['totals'])}\n-> {r['table']}\n-> {r['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
