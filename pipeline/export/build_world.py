"""site/data/world.json for the "Fields around the world" page and its "Could Khet Sathi work here?" answer (owner,
2026-11-15; every rule in config/rules.yaml global_use, committed before the first run). The outline is Natural Earth
1:110m land (pipeline/fetch/world_outline.py), projected and simplified here; the coverage, crop and not-modelled lists come
from the rules and config/crops.json. The page (site/js/world.js) mirrors coverage(), inside() and haversine_km().

    .venv/bin/python -m pipeline.export.build_world
"""
import json
import math
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SIZE, STEP, R_KM = 1000, 0.5, 6371.0


def rules():
    return yaml.safe_load((REPO / "config" / "rules.yaml").read_text())["global_use"]


def project(lon, lat):
    """Web Mercator on a SIZE-wide square: (0, 0) is the middle; the y axis points down."""
    r = math.radians(lat)
    return (lon + 180) / 360 * SIZE, (1 - math.log(math.tan(math.pi / 4 + r / 2)) / math.pi) / 2 * SIZE


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_KM * math.asin(math.sqrt(a))


def inside(x, y, rings):
    """Even-odd rule over flat rings [x0, y0, x1, y1, ...]."""
    hit = False
    for ring in rings:
        n = len(ring) // 2
        for i in range(n):
            x1, y1, x2, y2 = ring[2 * i], ring[2 * i + 1], ring[2 * ((i + 1) % n)], ring[2 * ((i + 1) % n) + 1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def simplify(points):
    """Round to STEP map units, drop repeats; None when under 3 points are left."""
    out = []
    for x, y in points:
        q = (round(x / STEP) * STEP, round(y / STEP) * STEP)
        q = tuple(int(v) if v == int(v) else v for v in q)
        if not out or out[-1] != q:
            out.append(q)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return [v for p in out for v in p] if len(out) >= 3 else None


def coverage(lat, on_land, cov):
    """{dataset: yes | caution | no} from each dataset's documented latitude band and land-only flag."""
    out = {}
    for k, c in cov.items():
        ok = c["lat"][0] <= lat <= c["lat"][1] and (on_land or not c["land_only"])
        out[k] = "no" if not ok else ("caution" if c.get("caution_abs_lat") is not None and abs(lat) > c["caution_abs_lat"] else "yes")
    return out


def nearest(lat, lon, fields):
    """(field id, km) of the prepared field whose centre is nearest."""
    return min(((f["id"], haversine_km(lat, lon, f["lat"], f["lon"])) for f in fields), key=lambda t: t[1])


def build(outline_path=REPO / "data" / "raw" / "naturalearth" / "ne_110m_land.geojson", out=REPO / "site" / "data" / "world.json"):
    g = rules()
    gj = json.loads(Path(outline_path).read_text(encoding="utf-8"))
    rings = []
    for f in gj["features"]:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in polys:
            for ring in poly:
                s = simplify([project(lon, max(-85.0, min(85.0, lat))) for lon, lat in ring])
                if s:
                    rings.append(s)
    y0, y1 = project(0, 80)[1], project(0, -60)[1]
    crops = list(json.loads((REPO / "config" / "crops.json").read_text())["crops"])
    w = {"about": "The world page's outline and its 'Could Khet Sathi work here?' rules (config/rules.yaml global_use). Outline: "
                  + g["outline"]["value"]["product"] + ", public domain. Built by pipeline/export/build_world.py.",
         "outline": {"size": SIZE, "y0": round(y0, 1), "y1": round(y1, 1), "rings": rings},
         "coverage": [{"id": k, **v} for k, v in g["coverage"]["value"].items()],
         "crops": crops,
         "not_modelled": ["snow", "orchards", "other_crops"]}
    Path(out).write_text(json.dumps(w, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {Path(out).relative_to(REPO)}: {len(rings)} rings, {sum(len(r) for r in rings) // 2} points, {Path(out).stat().st_size} bytes")
    return w


if __name__ == "__main__":
    build()
