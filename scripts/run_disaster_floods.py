"""Flood years from Nepal's disaster databases against each Bhaktapur field's flood-year flag (owner, 2026-11-15, answer
4; rules.yaml disaster_floods, committed before this ran). Reads data/raw/disaster_db/valley/ (BIPAD incidents, the
DesInventar valley records; VALIDATION 3.41) and site/data/fields/<field>.json replay.current; writes
data/checks/<field>/disaster_floods.json.

    .venv/bin/python scripts/run_disaster_floods.py --field kharipati --field demo
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks import disaster_floods as df  # noqa: E402

RAW = REPO / "data" / "raw" / "disaster_db" / "valley"


def run(field):
    rule = yaml.safe_load((REPO / "config" / "rules.yaml").read_text())["disaster_floods"]
    F = json.loads((REPO / "site" / "data" / "fields" / f"{field}.json").read_text())
    replay = F["replay"]["current"]
    years = [r["year"] for r in replay]
    flagged = [r["year"] for r in replay if r.get("event") == "flood"]
    cov = rule["coverage"]["value"]
    dbs = {"bipad": df.bipad_years(json.loads((RAW / "bipad_incidents.json").read_text()), rule),
           "desinventar": df.desinventar_years(json.loads((RAW / "desinventar_valley.json").read_text()), rule)}
    out = {"field": field, "rule": "rules.yaml disaster_floods", "replay_years": [years[0], years[-1]], "our_flood_years": flagged,
           "databases": {k: {**df.score(v, flagged, years, cov[k], cov["min_flood_years"]),
                             "records": {str(y): ids for y, ids in sorted(v.items())}} for k, v in dbs.items()}}
    dest = REPO / "data" / "checks" / field / "disaster_floods.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", action="append", default=None)
    for f in (ap.parse_args(argv).field or ["kharipati"]):
        o = run(f)
        print(f, "our flood years:", o["our_flood_years"])
        for k, s in o["databases"].items():
            if s["scored"]:
                print(f"  {k} {s['span']}: database flood years {s['db_flood_years']}; we also flag "
                      f"{s['db_also_flagged'][0]} of {s['db_also_flagged'][1]}; of our flagged years there "
                      f"({s['flagged_years']}), {s['flagged_with_record'][0]} of {s['flagged_with_record'][1]} have a record")
            else:
                print(f"  {k} {s['span']}: not scored: {s['why']} (database flood years {s['db_flood_years']})")


if __name__ == "__main__":
    main()
