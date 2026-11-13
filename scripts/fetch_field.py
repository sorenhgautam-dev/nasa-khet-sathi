"""Fetch everything a prepared field needs, in order, resumably (build step 11: "the same pipeline, no code changes").

    .venv/bin/python scripts/fetch_field.py --field ambohidratrimo                 # every step not yet done
    .venv/bin/python scripts/fetch_field.py --field ambohidratrimo --steps gpm chirps
    .venv/bin/python scripts/fetch_field.py --field ambohidratrimo --list            # the plan and each step's state

Each step runs one existing module as its own process, logs to data/raw/_logs/<field>_<step>.log, and is recorded in
data/raw/_logs/<field>_steps.json (exit code, start, end). A step that ended with exit 0 is skipped on the next run
unless --force names it; every module caches its downloads, so a rerun after a failure resumes where it stopped.

Box steps need only the config's fetch_box, so they run before the field's square is picked. Field steps (the
point, cell or polygon) wait until the config has a polygon: the placeholder step writes the candidates
(data/clean/<field>/placeholder_candidates.json) and a person (or Claude, recorded in METHOD_NOTES) copies the chosen
square into the config. Steps that use a global file (GRACE, GPCC, FAOSTAT) reuse the copy already held for another
field. MODIS, SMAP and ECOSTRESS are not fetched abroad (no number shown there uses them); NEX-GDDP has its own
fetcher (pipeline/fetch/nexgddp.py).
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
PY = sys.executable

# name -> (needs the field's square, command after the interpreter, condition key)
STEPS = [
    ("worldcover", False, ["-m", "pipeline.fetch.worldcover"], None),
    ("hls_recent", False, ["-m", "pipeline.fetch.cogwindows", "--set", "hls_l30", "hls_s30", "--since", "2023-01-01"], None),
    ("placeholder", False, ["-m", "pipeline.fetch.placeholder"], None),
    ("gpm", False, ["-m", "pipeline.fetch.gpm", "--workers", "6"], None),
    ("chirps", False, ["-m", "pipeline.fetch.chirps", "--years", "2001-2025"], None),
    ("hls", False, ["-m", "pipeline.fetch.cogwindows", "--set", "hls_l30", "hls_s30"], None),
    ("hls_cards", True, ["-m", "pipeline.fetch.cogwindows", "--set", "hls_l30", "hls_s30", "--card"], None),
    ("gpm_build", True, ["-m", "pipeline.fetch.gpm", "--from-cache"], None),
    ("chirps_build", True, ["-m", "pipeline.fetch.chirps", "--from-cache"], None),
    ("power", True, ["-m", "pipeline.fetch.power"], None),
    ("nasadem", True, ["-m", "pipeline.fetch.nasadem"], None),
    ("soilgrids", True, ["-m", "pipeline.fetch.soilgrids_wcs"], None),
    ("gauge_evidence", True, ["-m", "pipeline.fetch.gauge_evidence"], None),
    ("grace", True, ["-m", "pipeline.fetch.grace"], None),
    ("faostat", True, ["-m", "pipeline.fetch.faostat"], None),
    ("ghcn", True, ["-m", "pipeline.fetch.ghcn"], "validation_station"),
    ("weather", True, ["-m", "pipeline.fetch.weather"], None),
    ("rain_check", True, ["scripts/run_rain_check.py"], None),
]


def plan(field, done, only=None, force=()):
    """[(step, action)] with action 'run', 'skip: done', 'wait: no square yet' or 'skip: <key> not in config'. Pure."""
    out = []
    for name, needs_square, _, cond in STEPS:
        if only and name not in only:
            continue
        if cond and not field.get(cond):
            out.append((name, f"skip: {cond} not in config"))
        elif name in done and done[name].get("exit") == 0 and name not in force:
            out.append((name, "skip: done"))
        elif needs_square and not field.get("polygon"):
            out.append((name, "wait: no square yet (pick it from placeholder_candidates.json)"))
        else:
            out.append((name, "run"))
    return out


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", required=True)
    ap.add_argument("--steps", nargs="+", default=None, help=f"only these steps: {[s[0] for s in STEPS]}")
    ap.add_argument("--force", nargs="+", default=[], help="rerun these steps although they are done")
    ap.add_argument("--list", action="store_true", help="print the plan and stop")
    a = ap.parse_args(argv)
    logs = REPO / "data" / "raw" / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    state_path = logs / f"{a.field}_steps.json"
    done = json.loads(state_path.read_text()) if state_path.exists() else {}
    commands = {n: c for n, _, c, _ in STEPS}
    failed = []
    for name, action in plan(load_field(a.field), done, a.steps, a.force):
        print(f"{name:15s} {action}", flush=True)
        if action != "run" or a.list:
            continue
        log = logs / f"{a.field}_{name}.log"
        start = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        with open(log, "a") as fh:
            fh.write(f"\n=== {start} {name}: {' '.join(commands[name])} --field {a.field}\n")
            fh.flush()
            code = subprocess.call([PY, *commands[name], "--field", a.field], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT)
        done = json.loads(state_path.read_text()) if state_path.exists() else {}
        done[name] = {"exit": code, "start": start, "end": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                      "log": str(log.relative_to(REPO))}
        state_path.write_text(json.dumps(done, indent=1) + "\n")
        print(f"{'':15s} exit {code} -> {log.relative_to(REPO)}", flush=True)
        if code != 0:
            failed.append(name)
        if name == "placeholder" and code == 0 and not load_field(a.field).get("polygon"):
            print("The candidates are in data/clean/<field>/placeholder_candidates.json: copy the chosen square into the "
                  "config (lat, lon, polygon), then run this script again for the field steps.", flush=True)
    if failed:
        print(f"FAILED: {failed} (see their logs; rerun to resume)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
