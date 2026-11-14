"""site/data/index.json from every prepared field's config (REVIEW_2 H6, stage A).

    .venv/bin/python -m pipeline.export.build_index [--data-dir site/data]

A field is listed once its file site/data/fields/<id>.json exists (so the field abroad appears only when exported), with
its id, name, country, point and prepared area (`bbox` in its config) and two labels: `sample` (a sample field near a
demo field: config `sample: true`) and `area`, the area map it belongs to. A field on the global defaults (no country
profile in config/countries/; owner's item 3, 2026-11-14) also carries `profile: "default"` and a `note` for the list. An area is a field's own id or, for a sample,
the field it is a sample of (`sample_of`), and is listed only when its map site/data/area/<id>.json exists; its name is
the config's `area_name` or "<field name before any parenthesis> area". The index must validate (index_schema.json).
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline.export.validate import REPO, validate_index


def _area_of(cfg):
    return cfg.get("sample_of") or cfg["id"]


GLOBAL_NOTE = {   # owner, 2026-11-14 night: "A field on another continent, run by the same pipeline"
    "en": "A field on another continent, run by the same pipeline. Not checked against local rain gauges yet.",
    "ne": "अर्को महादेशको खेत, उही प्रणालीले चलाएको। स्थानीय वर्षा मापकसँग अझै जाँच गरिएको छैन।"}


def _profile_flag(cfg):
    """{'profile': 'default', 'note': ...} for a field on the global defaults (no country profile, owner's item 3), else {}:
    a field with a country profile keeps its entry as before."""
    from pipeline.fetch.profiles import load_profiles, profile_id
    return {"profile": "default", "note": dict(GLOBAL_NOTE)} if profile_id(cfg, load_profiles()) == "default" else {}


def build_index(configs, data_dir):
    """{fields, areas} from the configs (dicts as load_field gives them) and what exists under data_dir (site/data)."""
    data_dir = Path(data_dir)
    by_id = {c["id"]: c for c in configs}
    listed = [c for c in configs if (data_dir / "fields" / f"{c['id']}.json").exists()]
    with_map = {a for a in {_area_of(c) for c in listed} if (data_dir / "area" / f"{a}.json").exists()}
    fields = [{"id": c["id"], "name": c["name"], "country": c["country"], "lat": c["lat"], "lon": c["lon"],
               "bbox": list(c["bbox"]), "sample": bool(c.get("sample")),
               "area": _area_of(c) if _area_of(c) in with_map else None, **_profile_flag(c),
               **({"drone": f"data/drone/{c['id']}.json"} if (data_dir / "drone" / f"{c['id']}.json").exists() else {})}
              for c in listed]
    areas = []
    for a in dict.fromkeys(_area_of(c) for c in listed if _area_of(c) in with_map):     # in the order the fields come
        owner = by_id.get(a, {})
        areas.append({"id": a, "name": owner.get("area_name") or f"{str(owner.get('name', a)).split(' (')[0]} area",
                      "bbox": list(owner.get("bbox") or json.loads((data_dir / "area" / f"{a}.json").read_text())["bbox"]),
                      "map": f"data/area/{a}.json", "fields": [f["id"] for f in fields if f["area"] == a]})
    # a drawn field's drone photo whose field is not listed yet: shown on How we know as a preview (owner, 2026-11-15)
    previews = [f"data/drone/{c['id']}.json" for c in configs
                if c not in listed and (data_dir / "drone" / f"{c['id']}.json").exists()]
    return {"fields": fields, "areas": areas, **({"drone_previews": previews} if previews else {})}


def all_configs(config_dir=REPO / "config" / "fields"):
    from pipeline.fetch.fields import load_field
    ids = sorted(p.stem for p in Path(config_dir).glob("*.yaml"))
    order = sorted(ids, key=lambda i: (i != "demo", i))           # the demo first ("Try our demo field")
    return [load_field(i, config_dir) for i in order]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(REPO / "site" / "data"))
    a = ap.parse_args(argv)
    data_dir = Path(a.data_dir)
    idx = build_index(all_configs(), data_dir)
    errs = validate_index(idx)
    if errs:
        print("REFUSED: the index would break its schema:\n" + "\n".join(errs))
        return 1
    (data_dir / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n")
    print(f"index: {[f['id'] for f in idx['fields']]}; areas {[(x['id'], x['fields']) for x in idx['areas']]} -> {data_dir / 'index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
