"""The world's land outline for the "Fields around the world" page (owner, 2026-11-15; config/rules.yaml global_use.outline):
Natural Earth 1:110m land, public domain, fetched ONCE at build time and cached in data/raw/naturalearth/. The site never
asks for it: pipeline/export/build_world.py writes the small simplified file site/data/world.json.

    .venv/bin/python -m pipeline.fetch.world_outline
"""
import json
from pathlib import Path

import requests
import yaml

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw" / "naturalearth" / "ne_110m_land.geojson"


def fetch(force=False):
    if RAW.exists() and not force:
        print(f"cached: {RAW.relative_to(REPO)}")
        return RAW
    rule = yaml.safe_load((REPO / "config" / "rules.yaml").read_text())["global_use"]["outline"]["value"]
    r = requests.get(rule["url"], timeout=120, headers={"User-Agent": "khet-sathi-pipeline"})
    r.raise_for_status()
    gj = r.json()
    assert gj.get("type") == "FeatureCollection" and gj["features"], "not a GeoJSON feature collection"
    kinds = {f["geometry"]["type"] for f in gj["features"]}
    assert kinds <= {"Polygon", "MultiPolygon"}, f"unexpected geometry types {kinds}"
    print(f"attributes: {len(gj['features'])} features, geometry {sorted(kinds)}, CRS {gj.get('crs', 'WGS84 lon/lat (GeoJSON)')}")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_bytes(r.content)
    card = REPO / "data" / "cards" / "world" / "naturalearth.json"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(json.dumps({"dataset": "naturalearth", "product": rule["product"], "url": rule["url"],
                                "licence": "public domain (naturalearthdata.com/about/terms-of-use/)", "features": len(gj["features"]),
                                "bytes": len(r.content), "units": "degrees of longitude and latitude (WGS84)", "used_for":
                                "the outline on the world page and the land-or-sea test (rules.yaml global_use)"}, indent=1) + "\n")
    print(f"wrote {RAW.relative_to(REPO)} ({len(r.content)} bytes) and {card.relative_to(REPO)}")
    return RAW


if __name__ == "__main__":
    fetch()
