"""Sample fields across the box (rules.yaml sample_fields). The candidate rule is the demo's own, imported from
pipeline/fetch/placeholder.py by the runner; only the spread rule and the config writer live here."""
import yaml

from pipeline.fetch.worldcover import distance_km, square_polygon


def quadrant(lat, lon, origin):
    return ("N" if lat >= origin["lat"] else "S") + ("E" if lon >= origin["lon"] else "W")


def spread_pick(ranked, demo_latlon, origin, min_apart_km):
    """Down the ranked list: one per quadrant, each at least min_apart_km from the demo field and every pick."""
    chosen, taken = [], set()
    for c in ranked:
        q = quadrant(c["lat"], c["lon"], origin)
        if q in taken:
            continue
        pts = [demo_latlon] + [(d["lat"], d["lon"]) for d in chosen]
        if all(distance_km(c["lat"], c["lon"], la, lo) >= min_apart_km for la, lo in pts):
            chosen.append({**c, "quadrant": q})
            taken.add(q)
        if len(taken) == 4:
            break
    return chosen


def sample_config(n, cand, demo, why):
    """A config/fields/sample_<n>.yaml modelled on the demo's: a labelled PLACEHOLDER sample in the same box."""
    return {"id": f"sample_{n}", "name": f"Bhaktapur sample field {n} (PLACEHOLDER)", "placeholder": True,
            "sample": True, "sample_of": demo["id"], "sample_why": why, "country": demo["country"],
            "origin_point": dict(demo["origin_point"]), "lat": round(cand["lat"], 6), "lon": round(cand["lon"], 6),
            "polygon": square_polygon(cand["lat"], cand["lon"], 60),
            "fetch_box": list(demo["fetch_box"]), "bbox": list(demo["bbox"]),
            "elevation_m": None, "water_source": None,
            "current_rotation": list(demo["current_rotation"]),
            "current_rotation_options": [list(r) for r in demo["current_rotation_options"]],
            "current_rotation_source": ("PLACEHOLDER (sample field, as the demo's, owner 2026-11-12 and 2026-11-13): rice in the "
                                        "monsoon, then potato in winter, or rice then wheat; nobody has asked this field's farmer"),
            "validation_station": demo["validation_station"], "correction_label": demo["correction_label"]}


def write_yaml(path, cfg, header):
    path.write_text(header + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, default_flow_style=None, width=200))
    return path
