"""24 years of soil at a glance (owner, 2026-11-15 evening; rules.yaml soil_years): the exported replay recomputed as it
is (scripts/run_replay.py's inputs and switches), and each replayed year's calendar months as the root-zone share
1 - Dr/TAW in four fixed steps. Nothing is written when the recomputed yearly harvests differ from replay.json's.

    .venv/bin/python scripts/run_soil_years.py --field kharipati      -> data/checks/<field>/soil_years.json
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.diary import months as mo  # noqa: E402
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.profiles import events_rules  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.plans import twin_options as to  # noqa: E402
from pipeline.twin.inputs import with_rain  # noqa: E402
from scripts.common import SOIL_DIRS, add_switches, rain_kw, set_switches, soil_for, write_json  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="kharipati")
    add_switches(ap)
    a = ap.parse_args(argv)
    field, rules, data = load_field(a.field), load_rules(), REPO / "data"
    lib = load_crops(field=field)
    rules["events"] = events_rules(field, rules)
    set_switches(rules, a)
    clean, checks = data / "clean" / field["id"], data / "checks" / field["id"]
    w = with_rain(pd.read_parquet(clean / "weather.parquet"), "corrected", **rain_kw(rules, "corrected", field["id"]))
    soil = soil_for(a.soil, rules, field["id"], pd.read_parquet(clean / "soilgrids.parquet"), data)
    rotation, _ = sim.rotation_for(field, rules)
    cover, by_cover = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by_cover["bare"], **{c: by_cover[cover[c]] for c in rotation}}
    case = sim.export_case(field.get("water_source") or "unknown")
    sj = checks / "diary_seasons.json"
    seasons = to.hls_seasons(json.loads(sj.read_text())) if to.season_dates_on(rules) and sj.exists() else None
    res = to.replay(w, rotation, lib, soil, cn, rules, irrigated=case == "irrigated", farmer=True, seasons=seasons)
    saved = json.loads((checks / SOIL_DIRS[a.soil] / "replay.json").read_text())[case]["years"]
    same = [(y["year"], round(y["harvest"], 9)) for y in res["years"]] == [(y["year"], round(y["harvest"], 9)) for y in saved]
    if not same:
        print("REFUSED: the recomputed replay's yearly harvests differ from replay.json's; nothing written")
        return 1
    current = json.loads((REPO / "site" / "data" / "fields" / f"{field['id']}.json").read_text())["replay"]["current"]
    years = [r["year"] for r in current]
    d, edges = res["daily"], rules["soil_years"]["steps"]["edges"]
    share = mo.monthly_wetness(d["date"], d["dr_mm"], d["taw_mm"], years)
    out = {"field": field["id"], "made_by": "scripts/run_soil_years.py (rules.yaml soil_years)", "case": case,
           "rotation": rotation, "years": years, "steps": rules["soil_years"]["steps"],
           "share": {str(y): v for y, v in share.items()},
           "step": {str(y): [mo.wetness_step(x, edges) for x in v] for y, v in share.items()},
           "events": {str(r["year"]): r["event"] for r in current if r["event"] != "none"},
           "check": {"harvests_equal_replay_json": True, "years": len(years)}}
    write_json(checks / "soil_years.json", out)
    counts = [sum(s.count(k) for s in out["step"].values()) for k in range(4)]
    print(f"{field['id']}: {case}, {'+'.join(rotation)}, {years[0]}-{years[-1]}; squares per step "
          f"{dict(zip(rules['soil_years']['steps']['words'], counts))} -> {(checks / 'soil_years.json').relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
