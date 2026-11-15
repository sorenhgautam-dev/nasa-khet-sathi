"""A drawn field's drone photo and patches for the site: site/data/drone/<field>.json and its picture (owner, 2026-11-15).

    .venv/bin/python -m pipeline.export.build_drone --field dhulikhel

From the field's config: `drone_photo` (the package zip, the clean picture's file, bounds and credit), `polygon` (the
outline), its centre (lat, lon) and `patches` (cell_m, min_piece_m2). The patches are cut by our own code
(pipeline/sections/grid.patches) and compared with the package's own list (farm_coordinates.json), the result kept in
the file. The picture is copied unchanged from the zip. The site draws the outline and the lines between patches over
the picture as vector lines (crisp at any size), on the parts and soil screens when the field is listed, or on How we
know as a preview when it is not (pipeline/export/build_index.py).
"""
import argparse
import json
import math
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(REPO))
SCHEMA_KEYS = ("field", "image", "bounds", "size_px", "date", "credit", "source", "resolution", "outline", "patches", "lines",
               "method", "package_check")


def package_check(ours, theirs, scale):
    """Each patch against the package's patch of the same id: centre distance (m) and area difference (m2). Pure."""
    by_id = {q["id"]: q for q in theirs}
    rows = []
    for p in ours:
        q = by_id.get(p["id"])
        if q is None:
            rows.append({"id": p["id"], "centre_m": None, "area_m2": None})
            continue
        d = math.hypot((p["centre"][0] - q["lon"]) * scale[0], (p["centre"][1] - q["lat"]) * scale[1])
        rows.append({"id": p["id"], "centre_m": round(d, 1), "area_m2": round(p["area_m2"] - q["area_m2"], 1)})
    close = [r["id"] for r in rows if r["centre_m"] is not None and r["centre_m"] < 1.0 and abs(r["area_m2"]) < 12]
    return {"patches_ours": len(ours), "patches_package": len(theirs), "within_1m_and_12m2": close,
            "differ": [r for r in rows if r["id"] not in close], "rows": rows}


def build(field, repo=REPO):
    from pipeline.sections import grid
    d = field["drone_photo"]
    with zipfile.ZipFile(repo / d["package"]) as z:
        picture = z.read(d["file"])
        pkg = json.loads(z.read("farm_coordinates.json"))
    cfg = field["patches"]
    ps, lines = grid.patches(field["polygon"], (field["lon"], field["lat"]), cfg["cell_m"], cfg["min_piece_m2"], cfg["ids"])
    doc = {"field": field["id"], "image": f"data/drone/{field['id']}.jpg", "bounds": d["bounds"], "size_px": d["size_px"],
           "date": d["date"], "credit": d["credit"], "source": d["source"], "resolution": d["resolution"],
           "outline": [[float(x), float(y)] for x, y in field["polygon"]],
           "patches": [{"id": p["id"], "area_m2": p["area_m2"], "centre": p["centre"], "polygon": p["polygon"],
                        "whole": p["whole"]} for p in ps],
           "lines": lines,
           "method": f"a {cfg['cell_m']:g} m grid through the field's centre, pieces under {cfg['min_piece_m2']:g} m2 joined to "
                     "the nearest patch, numbered from the south-west, row by row (pipeline/sections/grid.patches)",
           "package_check": package_check(ps, pkg["patches"], grid._scale(field["polygon"]))}
    return doc, picture


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", required=True)
    ap.add_argument("--out-dir", default=str(REPO / "site" / "data" / "drone"))
    a = ap.parse_args(argv)
    field = load_field(a.field)
    if not field.get("drone_photo") or not field.get("patches"):
        print(f"field '{a.field}' has no drone_photo and patches in its config: nothing to build")
        return 0
    doc, picture = build(field)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.field}.jpg").write_bytes(picture)
    (out / f"{a.field}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    c = doc["package_check"]
    print(f"{len(doc['patches'])} patches, {len(doc['lines'])} lines -> {out / (a.field + '.json')}; "
          f"{len(c['within_1m_and_12m2'])} of {c['patches_package']} match the package within 1 m and 12 m2; "
          f"differ: {', '.join(r['id'] for r in c['differ']) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
