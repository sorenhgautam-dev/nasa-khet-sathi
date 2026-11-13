"""ISRIC SoilGrids 2.0 for the fetch box through the WCS (maps.isric.org), and the field's soil profile.
This module writes data/clean/<field>/soilgrids.parquet, the table the twin reads.

    .venv/bin/python -m pipeline.fetch.soilgrids_wcs --field demo [--offline]

The REST point service (rest.isric.org) stopped answering on 2026-11-12 and covers one point per call;
the WCS returns each property and depth for the whole box in one call (6 properties x 6 depths). The
maps are requested in EPSG:4326 (the server resamples from its native Homolosine grid; about 250 m
cells).

No prediction (REVIEW_NOTES M5): each map's own nodata value is read. The WCS maps cached on 2026-11-12
declare none, and cells outside SoilGrids' prediction mask come back as 0; without a declared nodata a 0
is ambiguous, so it is never taken as a value (a real 0 g/kg would be lost as "unknown", never invented).
A cell has a prediction only where EVERY map used here (sand, clay, soc, bdod, wv0033, wv1500, all six
depths) is valid.

Units: the GeoTIFFs carry no unit tags. SoilGrids stores mapped units; the conversion uses the d_factor
table in DOCUMENTED_UNITS (ISRIC's REST `unit_measure` blocks, copied 2026-11-12; the same factors as ISRIC's
"SoilGrids layers" table, https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html, verified 2026-11-12). When REST answers for this field are cached in
data/raw/soilgrids/<field>/*.json, their unit blocks are checked against the table and their values against
the maps at the same points (fail loudly on a unit change).

The field's profile comes from the cell holding the field centre (a point outside the maps fails loudly),
or, if that cell has no prediction, the nearest cell with one within rules.yaml
soilgrids.nearest_cell_max_m, with the caveat and the distance in the card.
Writes data/raw/soilgrids/<field>/wcs/*.tif, data/clean/<field>/soilgrids.parquet and the card.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.fetch.guards import DataGuardError
from pipeline.fetch.soilgrids import DEPTHS, PROPS
from pipeline.fetch.worldcover import distance_km

REPO = Path(__file__).resolve().parents[2]
WCS = ("https://maps.isric.org/mapserv?map=/map/{p}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
       "&COVERAGEID={p}_{d}_mean&FORMAT=image/tiff&SUBSET=long({x0},{x1})&SUBSET=lat({y0},{y1})"
       "&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326")
# property -> (mapped units, d_factor): ISRIC REST unit_measure blocks, 2026-11-12 (tests/test_soilgrids.py UNITS)
DOCUMENTED_UNITS = {"wv0033": ("(10-2 cm³/cm³)*10", 10), "wv1500": ("(10-2 cm³/cm³)*10", 10), "sand": ("g/kg", 10),
                    "clay": ("g/kg", 10), "soc": ("dg/kg", 10), "bdod": ("cg/cm³", 100)}
D_FACTOR = {p: f for p, (_, f) in DOCUMENTED_UNITS.items()}
UNITS_SOURCE = ("ISRIC REST unit_measure blocks (d_factor, mapped and target units), copied 2026-11-12; ISRIC "
                "'SoilGrids layers' table (docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html), same factors, verified 2026-11-12")


def convert(prop, mapped):
    return mapped / D_FACTOR[prop] * PROPS[prop][2]


def check_units(unit_blocks):
    """Compare REST unit blocks ({prop: unit_measure}) with DOCUMENTED_UNITS and PROPS; fail loudly on any change.
    Returns {prop: mapped units}."""
    out = {}
    for p, (mapped, factor) in DOCUMENTED_UNITS.items():
        u = unit_blocks.get(p)
        if u is None:
            raise DataGuardError(f"{p}: no unit block to check")
        if u["d_factor"] != factor or u["mapped_units"] != mapped or u["target_units"] != PROPS[p][1]:
            raise DataGuardError(f"{p}: ISRIC unit block {u} differs from the table used here "
                                 f"(d_factor {factor}, mapped '{mapped}', target '{PROPS[p][1]}')")
        out[p] = u["mapped_units"]
    return out


def valid_mask(a, nodata):
    """True where a map holds a prediction: not its declared nodata; without a declared nodata, not 0
    (ambiguous, so never taken as a value). NaN is never valid."""
    a = np.asarray(a, dtype=float)
    ok = np.isfinite(a)
    if nodata is not None and np.isfinite(nodata):
        return ok & (a != nodata)
    return ok & (a != 0)


def prediction_mask(grids, nodatas):
    """A cell has a prediction only where every map (property x depth) is valid."""
    return np.all([valid_mask(grids[k], nodatas[k]) for k in grids], axis=0)


def _centres(shape, transform):
    rows, cols = np.indices(shape)
    return transform.f + transform.e * (rows + 0.5), transform.c + transform.a * (cols + 0.5)


def holding_cell(shape, transform, lat, lon):
    """(row, col) of the cell holding the point; a point outside the maps fails loudly (no index wrap)."""
    r = int(np.floor((lat - transform.f) / transform.e))
    c = int(np.floor((lon - transform.c) / transform.a))
    if not (0 <= r < shape[0] and 0 <= c < shape[1]):
        raise ValueError(f"{lat}, {lon} is outside the SoilGrids maps (row {r}, col {c} of {shape[0]} x {shape[1]})")
    return r, c


def pick_cell(valid, transform, lat, lon, max_m):
    valid = np.asarray(valid, dtype=bool)
    hold_r, hold_c = holding_cell(valid.shape, transform, lat, lon)
    clat, clon = _centres(valid.shape, transform)
    if valid[hold_r, hold_c]:
        return {"row": hold_r, "col": hold_c, "distance_m": 0, "lat": float(clat[hold_r, hold_c]), "lon": float(clon[hold_r, hold_c])}
    best = nearest_with_values(valid, transform, lat, lon)
    if best is None:
        raise ValueError(f"no SoilGrids cell with values in the box near {lat}, {lon}")
    if best["distance_m"] > max_m:
        raise ValueError(f"no SoilGrids cell with values within {max_m} m of {lat}, {lon}; "
                         f"the nearest is {best['distance_m']} m away")
    return best


def nearest_with_values(valid, transform, lat, lon):
    clat, clon = _centres(np.shape(valid), transform)
    best = None
    for r, c in zip(*np.nonzero(np.asarray(valid, dtype=bool))):
        d = distance_km(lat, lon, clat[r, c], clon[r, c]) * 1000
        if best is None or d < best["distance_m"]:
            best = {"row": int(r), "col": int(c), "distance_m": round(d), "lat": float(clat[r, c]), "lon": float(clon[r, c])}
    return best


def neighbourhood_taw(valid, transform, fc, wp, lat, lon, used, radius_m, depth_m):
    """How the cell used compares with the cells around the field (owner's answer 10 to REVIEW_2, 2026-11-13): the
    water the soil holds for plants (field capacity minus wilting point, mm) over 0..depth_m, at the cell `used`
    (row, col) and over every cell with values within radius_m of the field. fc, wp: {depth label: grid, m3/m3}.
    A description only: the twin still uses the nearest cell."""
    from pipeline.twin.soil_water import taw_from_layers
    clat, clon = _centres(np.shape(valid), transform)

    def held(r, c):
        layers = pd.DataFrame([{"top_cm": int(d.replace("cm", "").split("-")[0]), "bottom_cm": int(d.replace("cm", "").split("-")[1]),
                                "theta_fc_m3m3": float(fc[d][r, c]), "theta_wp_m3m3": float(wp[d][r, c])} for d in DEPTHS])
        return taw_from_layers(layers, depth_m)
    vals = [held(r, c) for r, c in zip(*np.nonzero(np.asarray(valid, dtype=bool)))
            if distance_km(lat, lon, clat[r, c], clon[r, c]) * 1000 <= radius_m]
    used_mm = held(*used)
    return {"radius_m": radius_m, "depth_m": depth_m, "cells": len(vals), "used_mm": round(used_mm, 1),
            "min_mm": round(float(np.min(vals)), 1), "median_mm": round(float(np.median(vals)), 1),
            "max_mm": round(float(np.max(vals)), 1), "cells_holding_less": int(sum(v < used_mm - 1e-9 for v in vals))}


def rest_comparison(rest_dir, grids, transform):
    """Cached REST answers for this field: their unit blocks, and their values against the maps at the same
    points. Returns (unit blocks or None, {"pairs", "equal", "worst_ratio"}). A value off by more than a factor
    of 2 means a unit change and fails loudly."""
    blocks, pairs = None, []
    for f in sorted(Path(rest_dir).glob("*.json")):
        pl = json.loads(f.read_text())
        lon, lat = pl["geometry"]["coordinates"]
        for layer in pl["properties"]["layers"]:
            if layer["name"] not in PROPS:
                continue
            blocks = blocks or {}
            blocks.setdefault(layer["name"], layer["unit_measure"])
            for d in layer["depths"]:
                v = d["values"]["mean"]
                key = (layer["name"], d["label"])
                if v is None or key not in grids:
                    continue
                try:
                    r, c = holding_cell(grids[key].shape, transform, lat, lon)
                except ValueError:
                    continue
                if grids[key][r, c] > 0:
                    pairs.append((float(v), float(grids[key][r, c])))
    if not pairs:
        return blocks, {"pairs": 0, "equal": 0, "worst_ratio": None}
    ratio = [m / v for v, m in pairs if v > 0]
    worst = max(ratio, key=lambda x: abs(np.log(x))) if ratio else None
    if worst is not None and not 0.5 <= worst <= 2.0:
        raise DataGuardError(f"WCS map value / REST value reaches {worst:.2f} at the same point: a unit change?")
    return blocks, {"pairs": len(pairs), "equal": sum(v == m for v, m in pairs), "worst_ratio": worst}


def fetch(field, data_dir=REPO / "data", rules=None, offline=False):
    import rasterio

    from pipeline.fetch import guards as g
    from pipeline.fetch.rules import load_rules
    from pipeline.fetch.soilgrids import check

    rules = rules or load_rules()
    data_dir = Path(data_dir)
    raw = data_dir / "raw" / "soilgrids" / field["id"] / "wcs"
    raw.mkdir(parents=True, exist_ok=True)
    x0, y0, x1, y1 = field["fetch_box"]
    grids, nodatas, maps, transform, grid_attrs = {}, {}, {}, None, {}
    for p in PROPS:
        for d in DEPTHS:
            f = raw / f"{p}_{d}_mean.tif"
            if not f.exists():
                if offline:
                    raise FileNotFoundError(f"{f} is not cached and the run is offline")
                import requests
                r = requests.get(WCS.format(p=p, d=d, x0=x0, x1=x1, y0=y0, y1=y1), timeout=180)
                if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/tiff"):
                    raise g.DataGuardError(f"SoilGrids WCS {p} {d}: HTTP {r.status_code} {r.headers.get('content-type')}")
                f.write_bytes(r.content)
            with rasterio.open(f) as s:
                a = s.read(1).astype(float)
                maps[f.stem] = {"dtype": s.dtypes[0], "nodata": s.nodata, "units": s.units[0], "scale": s.scales[0],
                                "offset": s.offsets[0], "tags": {k: v for k, v in s.tags(1).items()}}
                if transform is None:
                    transform, grid_attrs = s.transform, {"crs": str(s.crs), "res_deg": s.res, "shape": list(s.shape)}
                elif s.transform != transform or a.shape != tuple(grid_attrs["shape"]):
                    raise g.DataGuardError(f"{f.name}: grid differs from the first map")
            grids[(p, d)], nodatas[(p, d)] = a, maps[f.stem]["nodata"]
    print("raw attributes (grid):", grid_attrs)
    for k, v in maps.items():                                   # rule 12a, every map
        print(f"raw attributes {k}: dtype {v['dtype']}, nodata {v['nodata']}, units {v['units'] or 'ABSENT'}, "
              f"scale {v['scale']}, offset {v['offset']}, valid_range ABSENT")
    blocks, comparison = rest_comparison(raw.parent, grids, transform)
    units_in = check_units(blocks) if blocks else {p: m for p, (m, _) in DOCUMENTED_UNITS.items()}
    units_how = ("checked against the cached REST unit blocks for this field" if blocks else
                 "no REST answer cached for this field, so not checked here")
    have = prediction_mask(grids, nodatas)
    any_valid = np.any([valid_mask(grids[k], nodatas[k]) for k in grids], axis=0)
    partial = int((any_valid & ~have).sum())                    # valid in some maps but not all
    max_m = rules["soilgrids"]["nearest_cell_max_m"]
    cell = pick_cell(have, transform, field["lat"], field["lon"], max_m)
    rows = []
    for d in DEPTHS:
        top, bottom = (int(v) for v in d.replace("cm", "").split("-"))
        rows.append({"top_cm": top, "bottom_cm": bottom,
                     **{PROPS[p][0]: convert(p, grids[(p, d)][cell["row"], cell["col"]]) for p in PROPS}})
    df = pd.DataFrame(rows)
    warned = check(df)
    out = data_dir / "clean" / field["id"] / "soilgrids.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    no_pred = int((~have).sum())
    N = rules["soilgrids"]["neighbourhood"]
    around = neighbourhood_taw(have, transform, {d: convert("wv0033", grids[("wv0033", d)]) for d in DEPTHS},
                               {d: convert("wv1500", grids[("wv1500", d)]) for d in DEPTHS}, field["lat"], field["lon"],
                               (cell["row"], cell["col"]), N["radius_m"], N["depth_m"])
    declared = sorted({str(v) for v in nodatas.values()})
    own = cell["distance_m"] == 0
    caveat = ("The field's own cell has a prediction." if own else
              f"Caveat: soil from the nearest SoilGrids cell with a prediction, {cell['distance_m']} m away, not the "
              f"field's own (limit {max_m} m, rules.yaml soilgrids.nearest_cell_max_m).")
    card = g.make_card(
        dataset="soilgrids", product="ISRIC SoilGrids 2.0 (WCS, box)", version="2.0",
        variable=list(PROPS), units_in=units_in, units_out={p: c for p, (c, _, _) in PROPS.items()},
        scale_factor={p: f"1/{D_FACTOR[p]}" + (" then /100" if p.startswith("wv") else "") for p in PROPS},
        fill_values_removed={("0 treated as no prediction (the maps declare no nodata)" if declared == ["None"] else
                              f"declared nodata {declared}"): no_pred},
        quality_flags_used="none (mean maps; uncertainty maps not used)",
        records_dropped=0, date_range=["n/a", "n/a"], time_zone="n/a (static map)", pixel_count=1,
        source="Poggio et al. 2021, SoilGrids 2.0, SOIL 7:217-240, doi:10.5194/soil-7-217-2021 (CC BY 4.0); WCS maps.isric.org",
        resolution="250 m (served in EPSG:4326, about 0.0023 deg)",
        raw_attrs={"grid": grid_attrs, "maps": maps, "units_source": UNITS_SOURCE, "units_check": units_how,
                   "rest_vs_wcs_values": comparison},
        range_warnings=warned, summary={"water_held_for_plants": around},
        location={"requested": [field["lat"], field["lon"]], "used": [round(cell["lat"], 6), round(cell["lon"], 6)],
                  "used_row_col": [cell["row"], cell["col"]], "distance_m": cell["distance_m"],
                  "box": field["fetch_box"], "box_cells": int(have.size), "box_cells_without_prediction": no_pred,
                  "box_cells_valid_in_some_maps_only": partial},
        notes=("Access: WCS for the whole box (the REST point service was down on 2026-11-12). A cell counts as "
               "having a prediction only where all 36 maps (6 properties x 6 depths) are valid. " + caveat
               + (" PLACEHOLDER field." if field.get("placeholder") else "")))
    return {"table": out, "card": g.write_card(card, data_dir / "cards" / field["id"]), "cell": cell, "df": df,
            "no_prediction": no_pred}


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--offline", action="store_true", help="use the cached maps only; fail if one is missing")
    a = ap.parse_args(argv)
    r = fetch(load_field(a.field), offline=a.offline)
    print(r["df"].round(3).to_string(), "\ncell", r["cell"], f"\nbox cells without a prediction: {r['no_prediction']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
