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
field. A sample field (`sample_of: <field>` with the same fetch_box) shares that field's box downloads: its raw folders
for the box datasets (SHARED) are links to the other field's, its box fetch steps are skipped, and the builds read them;
POWER (a point) and the station table are its own. MODIS (MOD13Q1 through AppEEARS, a few MB) is fetched for the box
because the diary reads it for the years before HLS (no exported number uses it); a box whose MODIS bundle is already
held skips it. SMAP and ECOSTRESS are not fetched abroad (no number shown there uses them); NEX-GDDP has its own fetcher
(pipeline/fetch/nexgddp.py). The crop calendar (pipeline/fetch/cropcalendar.py) runs for a field whose config names its
FAO zone (`fao_crop_calendar`: the global default of config/countries/default.yaml; Nepal's fields use crops.json).
A config with `record_years: [first, last]` (scripts/make_site.py --short-record) fetches only those years.
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
    ("modis_submit", False, ["-m", "pipeline.fetch.appeears", "submit", "--tasks", "modis"], None),   # the diary's
    ("modis", False, ["-m", "pipeline.fetch.appeears", "download", "--wait-s", "5400"], None),       # pre-HLS years
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
    ("oni", True, ["-m", "pipeline.fetch.oni"], None),           # the 25-Year Replay's El Nino / La Nina (window_replay.enso)
    ("ghcn", True, ["-m", "pipeline.fetch.ghcn"], "validation_station"),
    ("cropcalendar", False, ["-m", "pipeline.fetch.cropcalendar"], "fao_crop_calendar"),   # owner's item 3: the FAO zone
    ("weather", True, ["-m", "pipeline.fetch.weather"], None),
    ("rain_check", True, ["scripts/run_rain_check.py"], None),
]


SHARED = ("gpm", "chirps", "hls_l30", "hls_s30", "nasadem", "worldcover", "soilgrids", "gauge_evidence",
          "appeears", "gpm_now", "eco_lste", "eco_esi", "gldas")   # data/raw/<x>/ (appeears: the box's MODIS and SMAP;
# gpm_now: IMERG Late box subsets; eco_*: ECOSTRESS box windows; gldas: one 0.25 deg cell, its build refuses another cell)
BOX_FETCH = ("worldcover", "hls_recent", "gpm", "chirps", "hls", "modis_submit", "modis")
# a record shorter than 2001-2025 (config record_years, make_site.py --short-record): each step's own date options
RECORD_ARGS = {"gpm": lambda y0, y1: ["--start", f"{y0}-01-01", "--end", f"{y1}-12-31"],
               "gpm_build": lambda y0, y1: ["--start", f"{y0}-01-01", "--end", f"{y1}-12-31"],
               "chirps": lambda y0, y1: ["--years", f"{y0}-{y1}"],
               "power": lambda y0, y1: ["--start", f"{y0}-01-01", "--end", f"{y1}-12-31"],
               "gauge_evidence": lambda y0, y1: ["--start", f"{y0}-01"],
               "hls": lambda y0, y1: ["--since", f"{max(y0, 2013)}-01-01"]}


def command(name, field):
    """The step's command after the interpreter, with the field's record years when it has a shorter record. Pure."""
    cmd = list(next(c for n, _, c, _ in STEPS if n == name))
    yrs = field.get("record_years")
    if yrs and list(yrs) != [2001, 2025] and name in RECORD_ARGS:
        if name == "chirps":
            cmd = [c for c in cmd if c not in ("--years", "2001-2025")]
        cmd += RECORD_ARGS[name](*yrs)
    return cmd


def present_steps(field, raw_root=REPO / "data" / "raw"):
    """Steps whose download is already held although no log records it (the Nepal box's MODIS, fetched by hand)."""
    held = (Path(raw_root) / "appeears" / field["id"] / "modis").is_dir()
    return {"modis_submit", "modis"} if held else set()


def shares_box_with(field, other=None):
    """The field whose box downloads this one reuses: `sample_of` or `box_of`, when its fetch_box is the same. None
    otherwise."""
    src = field.get("sample_of") or field.get("box_of")
    if not src:
        return None
    if other is None:
        from pipeline.fetch.fields import load_field
        other = load_field(src)
    return src if list(other["fetch_box"]) == list(field["fetch_box"]) else None


def link_shared(field_id, src_id, raw_root):
    """data/raw/<x>/<field_id> -> <src_id> for every SHARED dataset the source holds; an existing folder is left alone."""
    made = []
    for x in SHARED:
        dst, src = Path(raw_root) / x / field_id, Path(raw_root) / x / src_id
        if src.is_dir() and not dst.exists() and not dst.is_symlink():
            dst.symlink_to(src_id, target_is_directory=True)
            made.append(x)
    return made


def plan(field, done, only=None, force=(), shared_with=None, present=()):
    """[(step, action)] with action 'run', 'skip: done', 'wait: no square yet', 'skip: <key> not in config', 'skip: the
    square is in the config' (placeholder), 'skip: box shared with <field>' (a sample's box fetches) or 'skip: already
    held' (`present`). Pure."""
    out = []
    for name, needs_square, _, cond in STEPS:
        if only and name not in only:
            continue
        if name in present and name not in force and not (name in done and done[name].get("exit") != 0):
            out.append((name, "skip: already held"))
        elif shared_with and name in BOX_FETCH and name not in force:
            out.append((name, f"skip: box shared with {shared_with}"))
        elif name == "placeholder" and field.get("polygon") and name not in force:
            out.append((name, "skip: the square is in the config"))
        elif cond and not field.get(cond):
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
    failed = []
    field = load_field(a.field)
    src = shares_box_with(field)
    if src and not a.list:
        made = link_shared(field["id"], src, REPO / "data" / "raw")
        print(f"box shared with {src}: linked {made or 'nothing new'}", flush=True)
    for name, action in plan(field, done, a.steps, a.force, shared_with=src, present=present_steps(field)):
        print(f"{name:15s} {action}", flush=True)
        if action != "run" or a.list:
            continue
        log = logs / f"{a.field}_{name}.log"
        start = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        cmd = command(name, field)
        with open(log, "a") as fh:
            fh.write(f"\n=== {start} {name}: {' '.join(cmd)} --field {a.field}\n")
            fh.flush()
            code = subprocess.call([PY, *cmd, "--field", a.field], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT)
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
