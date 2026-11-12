"""ISRIC SoilGrids 2.0 at the field: water content at 33 and 1500 kPa (field capacity, wilting point),
sand, clay, organic carbon and bulk density, six depths to 2 m. Model-based map, 250 m.

    .venv/bin/python -m pipeline.fetch.soilgrids --field demo

Access: the REST API (rest.isric.org, beta). Owner rule (2026-11-12): if the REST API is down, use
ISRIC's downloadable GeoTIFF files instead and record which in the data card; that fallback is not
built yet because the API answered on 2026-11-12. Units and conversion factors are taken from each
response's `unit_measure` and checked against the expected target units (fail loudly if they change).

If the field's own cell has no prediction (any value null; all null for the demo point on 2026-11-12),
the nearest cell where every property and depth has a value is used, searching outward in 250 m steps up
to the limit in rules.yaml, and the distance is written into the data card.

Outputs (REVIEW_NOTES M5): data/clean/<field>/soilgrids_rest.parquet and the card soilgrids_rest.json.
The twin's soil table, data/clean/<field>/soilgrids.parquet, is written only by soilgrids_wcs.py (the
whole box from the WCS maps, nearest cell on the full 250 m grid), so a rerun of this module never
replaces it with a coarser ring search.
"""
import argparse
import datetime as dt
import json
import math
import sys
import time
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from pipeline.fetch import guards as g
from pipeline.fetch.credits import ensure_credit
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules

API = "https://rest.isric.org/soilgrids/v2.0/properties/query"
REPO = Path(__file__).resolve().parents[2]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]
# property -> (column, expected target unit from the API, extra factor from target unit to column unit)
PROPS = {
    "wv0033": ("theta_fc_m3m3", "10-2 cm³/cm³", 0.01),    # volume percent -> m3/m3
    "wv1500": ("theta_wp_m3m3", "10-2 cm³/cm³", 0.01),
    "sand": ("sand_pct", "%", 1.0),
    "clay": ("clay_pct", "%", 1.0),
    "soc": ("soc_g_kg", "g/kg", 1.0),
    "bdod": ("bdod_kg_dm3", "kg/dm³", 1.0),
}
DIRECTIONS = [0, 45, 90, 135, 180, 225, 270, 315]     # N, NE, E, SE, S, SW, W, NW


def build_url(lat, lon):
    q = [("lon", f"{lon:.6f}"), ("lat", f"{lat:.6f}")] + [("property", p) for p in PROPS] \
        + [("depth", d) for d in DEPTHS] + [("value", "mean")]
    return f"{API}?{urllib.parse.urlencode(q)}"


def parse(payload):
    layers = {l["name"]: l for l in payload["properties"]["layers"]}
    rows, info = {}, {"units": {}, "all_null": True, "complete": True}
    for prop, (col, target, extra) in PROPS.items():
        if prop not in layers:
            raise g.DataGuardError(f"SoilGrids answer lacks {prop}")
        u = layers[prop]["unit_measure"]
        if u["target_units"] != target:
            raise g.DataGuardError(f"{prop}: API target unit '{u['target_units']}', expected '{target}'")
        info["units"][prop] = u
        for d in layers[prop]["depths"]:
            key = (d["range"]["top_depth"], d["range"]["bottom_depth"])
            v = d["values"]["mean"]
            if v is not None:
                info["all_null"] = False
            else:
                info["complete"] = False
            rows.setdefault(key, {})[col] = np.nan if v is None else v / u["d_factor"] * extra
    df = pd.DataFrame([{"top_cm": t, "bottom_cm": b, **vals} for (t, b), vals in sorted(rows.items())])
    return df, info


def check(df):
    warned = g.check_table(df, {"theta_fc_m3m3": "theta_m3m3", "theta_wp_m3m3": "theta_m3m3"})
    bad = df[~(df["theta_fc_m3m3"] > df["theta_wp_m3m3"])]
    if len(bad):
        raise g.DataGuardError(f"field capacity not above wilting point at depths {bad['top_cm'].tolist()} cm")
    for col in ("sand_pct", "clay_pct"):
        if ((df[col] < 0) | (df[col] > 100)).any():
            raise g.DataGuardError(f"{col} outside 0 to 100")
    if (df["sand_pct"] + df["clay_pct"] > 100).any():
        raise g.DataGuardError("sand + clay above 100%")
    for col in ("soc_g_kg", "bdod_kg_dm3"):
        g.assert_nonnegative(df[col].to_numpy(), col)
    return warned


def candidate_points(lat, lon, step_m, max_m):
    pts = []
    for dist in range(step_m, max_m + 1, step_m):
        for bearing in DIRECTIONS:
            b = math.radians(bearing)
            pts.append((lat + dist * math.cos(b) / 111320.0,
                        lon + dist * math.sin(b) / (111320.0 * math.cos(math.radians(lat))), dist))
    return pts


def _http_get_json(url, tries=3):
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, timeout=180, headers={"User-Agent": "khet-sathi-pipeline"})
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == tries:
                raise
            time.sleep(10 * attempt)


def _get_cached(raw_dir, lat, lon, get_json):
    path = raw_dir / f"{lat:.6f}_{lon:.6f}.json"
    if path.exists():
        return json.loads(path.read_text())
    payload = get_json(build_url(lat, lon))
    path.write_text(json.dumps(payload))
    return payload


def fetch(field, data_dir=REPO / "data", get_json=_http_get_json, rules=None, credits_path=None):
    rules = rules or load_rules()
    fid, data_dir = field["id"], Path(data_dir)
    raw_dir = data_dir / "raw" / "soilgrids" / fid
    raw_dir.mkdir(parents=True, exist_ok=True)
    step, max_m = rules["soilgrids"]["nearest_cell_step_m"], rules["soilgrids"]["nearest_cell_max_m"]
    tried = [(field["lat"], field["lon"], 0)] + candidate_points(field["lat"], field["lon"], step, max_m)
    for lat, lon, dist in tried:
        payload = _get_cached(raw_dir, lat, lon, get_json)
        df, info = parse(payload)
        if info["complete"]:                     # a partly null answer is not a prediction (M5)
            break
    else:
        raise g.DataGuardError(f"SoilGrids has no prediction within {max_m} m of the field")
    print(f"[soilgrids raw attrs] { {p: info['units'][p] for p in PROPS} }")
    warned = check(df)
    out = data_dir / "clean" / fid / "soilgrids_rest.parquet"         # never the twin's soilgrids.parquet (M5)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    note = ("Access: REST API (rest.isric.org, beta); GeoTIFF fallback not needed. "
            + ("The field's own cell had a prediction." if dist == 0 else
               f"The field's own 250 m cell returned no prediction (at least one value null), so the nearest cell with every value, "
               f"{dist} m away, is used (soil from the nearest SoilGrids cell with a prediction, not the field's own). "
               f"Reason for the gap (e.g. a land-cover mask) TODO-VERIFY.")
            + " The twin reads soilgrids.parquet from soilgrids_wcs.py, not this REST answer.")
    card = g.make_card(
        dataset="soilgrids_rest", product="ISRIC SoilGrids 2.0 (REST API, beta)", version="2.0",
        variable=list(PROPS), units_in={p: info["units"][p]["mapped_units"] for p in PROPS},
        units_out={p: c for p, (c, _, _) in PROPS.items()},
        scale_factor={p: f"1/{info['units'][p]['d_factor']}" + (" then /100" if p.startswith("wv") else "") for p in PROPS},
        fill_values_removed="none: null values become missing", quality_flags_used="none provided",
        records_dropped=0, date_range="static map", time_zone="n/a", pixel_count=1,
        source="ISRIC SoilGrids 2.0 (model-based map)", resolution="250 m",
        raw_attrs={p: info["units"][p] for p in PROPS}, range_warnings=warned,
        location={"requested": [field["lat"], field["lon"]], "used": [round(lat, 6), round(lon, 6)],
                  "distance_m": dist},
        notes=note)
    card_path = g.write_card(card, data_dir / "cards" / fid)
    if credits_path:
        ensure_credit(credits_path, f"- ISRIC SoilGrids 2.0 REST API (model-based, CC-BY 4.0), field `{fid}`, "
                                    f"cell {dist} m from the field point, fetched {dt.date.today()}")
    return {"table": out, "card": card_path, "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    out = fetch(load_field(ap.parse_args(argv).field), credits_path=REPO / "CREDITS.md")
    print(pd.read_parquet(out["table"]).round(3).to_string(index=False))
    print(f"location {out['card_data']['location']}\n-> {out['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
