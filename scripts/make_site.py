"""Deploy-anywhere kit (owner's item 3, 2026-11-14): one command makes a Khet Sathi site for one field, anywhere.

    .venv/bin/python scripts/make_site.py --lat -18.834 --lon 47.437 --size-m 60 --name "Rakoto's field" \\
        --country Madagascar --country-code MG --aez 004 --rotation rice,potato --out ~/khet-sathi-site
    .venv/bin/python scripts/make_site.py ... --dry-run          # the plan, the downloads and the time, nothing run
    .venv/bin/python scripts/make_site.py --field ambohidratrimo --out DIR    # a field whose config already exists

What it does, in order:
1. writes config/fields/<id>.yaml from the point, size, name and country (a 60 m square is a field of 60 x 60 m around
   the point; the download box reaches --box-km each way). Anything not given is null with a TODO, never guessed: the
   crops grown now (--rotation), the water source, the FAO crop-calendar zone (--aez; the kit lists the country's zones),
   a nearby GHCN-Daily station (--station). An existing config is never overwritten.
2. picks the country's profile (config/countries/<ISO2>.yaml) or the global defaults (config/countries/default.yaml),
3. downloads with scripts/fetch_field.py (resumable: run the same command again after a failure),
4. builds with scripts/run_field.py: every step for a field with a country profile; for a field on the global defaults
   the steps that need only global data (PROFILE_ONLY lists the ones that need a country's own gauges),
5. copies a static site folder (--out) holding the app and only this field's data, with an index.json listing it:
   host it free on GitHub Pages, Vercel or Netlify (docs/DEPLOY_ANYWHERE.md).

--short-record writes `record_years: [2016, 2025]` and shows the shorter downloads in --dry-run; the downloads take it
(scripts/fetch_field.py), the build does not yet (it assumes 2001-2025), so the kit stops before downloading (NOT READY). It needs an Earthdata login in ~/.netrc and the GES DISC data agreement
(docs/DEPLOY_ANYWHERE.md). Progress: each step prints its number, its expected minutes and the time it took.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
PY = sys.executable

FULL_YEARS, SHORT_YEARS = [2001, 2025], [2016, 2025]
# Minutes each download took for the field abroad (data/raw/_logs/, 2026-11-14), full record and short record (10 of 25
# years, scaled by years for the per-day products). Rough: NASA's servers set the pace.
FETCH_MINUTES = {"worldcover": (1, 1), "hls_recent": (12, 12), "placeholder": (1, 1), "gpm": (75, 30), "chirps": (30, 12),
                 "hls": (20, 15), "hls_cards": (1, 1), "gpm_build": (1, 1), "chirps_build": (1, 1), "power": (1, 1),
                 "nasadem": (1, 1), "soilgrids": (1, 1), "gauge_evidence": (30, 12), "grace": (2, 2), "faostat": (1, 1),
                 "oni": (1, 1), "ghcn": (1, 1), "cropcalendar": (1, 1), "modis_submit": (1, 1), "modis": (30, 30),
                 "weather": (1, 1), "rain_check": (1, 1)}
# megabytes read over the network; the global files (GPCC 45 MB packed, 400 MB on disk; GRACE; FAOSTAT) come once per
# installation and are reused by every later field
FETCH_MB = {"gpm": (285, 115), "chirps": (1500, 600), "hls": (40, 30), "hls_recent": (10, 10), "gauge_evidence": (55, 50),
            "nasadem": (13, 13), "grace": (44, 44), "faostat": (32, 32), "power": (1, 1), "modis": (4, 4), "worldcover": (1, 1)}
BUILD_MINUTES = {"weather": 1, "rain_check": 1, "diary": 2, "replay": 1, "plans": 15, "plans_dhm": 15, "plans_untuned": 15,
                 "export": 1, "replay_window": 2, "pulse": 1, "checkup": 1, "labels": 1}
# run_field.py CORE steps not run on the global defaults, and why (each needs something only Nepal's profile has today)
PROFILE_ONLY = {"plans_dhm": "rain scaled to DHM's normals (Nepal's gauges)",
                "plans_untuned": "the gauge-tuned rain's other edge (Nepal's gauges)",
                "rainrisk": "DHM's rain classes and Nepal time in its words (another agent's file: could read the profile)",
                "fertiliser": "Nepal's urea prices and the lentil plan (another agent's file: could read the profile)",
                "heatclock": "the 2040 climate runs (NEX-GDDP), a step not run on the global defaults",
                "replay_window": "the twin's state today (run_twin_now, a Nepal step) and the DHM-scaled rain version",
                "simple": "the 25-Year Replay's file (replay_window)"}
SITE_PARTS = ("index.html", "css", "js", "fonts", "img", "vendor")


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "field"


def square(lat, lon, side_m):
    """[[lon, lat], ...] SW, SE, NE, NW of a square of side_m metres centred on the point (as the configs hold it)."""
    from pipeline.fetch.worldcover import box_around
    x0, y0, x1, y1 = box_around(lat, lon, side_m / 2000.0)
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def config_text(a, fid):
    """The new field's YAML: given values, and null with a TODO for everything unknown. Pure."""
    from pipeline.fetch.worldcover import box_around
    box = box_around(a.lat, a.lon, a.box_km)
    rot = [c.strip() for c in a.rotation.split(",")] if a.rotation else None
    years = SHORT_YEARS if a.short_record else FULL_YEARS
    fao = ({"country": a.country_code, "aez": a.aez} if a.country_code else None)
    lines = [
        f"# Written by scripts/make_site.py on {time.strftime('%Y-%m-%d')} (the deploy-anywhere kit). Anything unknown is null",
        "# with a TODO: fill it in, never guess it. Then run the same make_site.py command again.",
        f"id: {fid}",
        f"name: {json.dumps(a.name)}",
        f"country: {json.dumps(a.country)}",
        f"country_code: {json.dumps(a.country_code)}" + ("" if a.country_code else "   # TODO: the ISO 3166-1 alpha-2 code"),
        f"origin_point: {{lat: {a.lat}, lon: {a.lon}}}",
        f"lat: {a.lat}",
        f"lon: {a.lon}",
        f"polygon: {json.dumps(square(a.lat, a.lon, a.size_m))}   # a {a.size_m:g} m square around the point: SW, SE, NE, NW as [lon, lat]",
        f"fetch_box: {json.dumps(box)}   # {a.box_km:g} km N, S, E, W of the point",
        f"bbox: {json.dumps(box)}",
        "elevation_m: null                   # filled from NASADEM when the pipeline runs",
        "water_source: null                  # TODO: rain-only, canal, well or irrigated. Unknown: both cases are shown",
        f"current_rotation: {json.dumps(rot) if rot else 'null   # TODO: the crops grown now, in order, e.g. [rice, potato]'}",
        f"current_rotation_source: {json.dumps(a.rotation_source or ('given to make_site.py' if rot else None))}",
        "fao_crop_calendar: " + (json.dumps(fao) if fao else "null   # TODO: {country: <ISO2>, aez: <zone>}") +
        ("   # TODO: aez (list the zones: python -m pipeline.fetch.cropcalendar --zones " + a.country_code + ")" if fao and not a.aez else ""),
        "crop_calendar_defaults: {}          # optional: a crop's default FAO session by its label, e.g. {rice: \"...\"}",
        f"validation_station: {json.dumps(a.station)}" + ("" if a.station else "   # TODO (optional): the nearest GHCN-Daily station id"),
        f"record_years: {json.dumps(years)}" + ("   # the shorter record (make_site.py --short-record): every label says so"
                                                   if a.short_record else ""),
    ]
    return "\n".join(lines) + "\n"


def build_steps(field, profile_id):
    """run_field.py steps for this field: all of them with a country profile; on the global defaults the CORE steps that
    need no country gauges (no site-wide steps: the kit writes its own index). Pure."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_field", REPO / "scripts" / "run_field.py")
    rf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rf)
    if profile_id != "default":
        return [n for n, _, kind in rf.STEPS if kind != rf.SITE]
    return [n for n, _, kind in rf.STEPS if kind == rf.CORE and n not in PROFILE_ONLY]


def fetch_plan(field):
    import importlib.util
    spec = importlib.util.spec_from_file_location("fetch_field", REPO / "scripts" / "fetch_field.py")
    ff = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ff)
    state = REPO / "data" / "raw" / "_logs" / f"{field['id']}_steps.json"
    done = json.loads(state.read_text()) if state.exists() else {}
    return ff.plan(field, done, shared_with=ff.shares_box_with(field), present=ff.present_steps(field))


def print_plan(field, profile, steps, short):
    k = 1 if short else 0
    fp = fetch_plan(field)
    print(f"Field {field['id']}: {field['name']} ({field['country']}), {field['lat']}, {field['lon']}")
    print(f"Profile: {profile['_id']} ({'config/countries/' + profile['_id'] + '.yaml' if profile['_id'] != 'default' else 'the global defaults, config/countries/default.yaml'})")
    yrs = field.get("record_years") or FULL_YEARS
    print(f"Record: {yrs[0]}-{yrs[1]}" + (" (the shorter record: every label says so)" if short else ""))
    todo = [k_ for k_ in ("current_rotation", "fao_crop_calendar") if not field.get(k_)]
    if (field.get("fao_crop_calendar") or {}).get("aez") is None and profile["crop_calendar"]["windows"] == "fao_api":
        todo.append("fao_crop_calendar.aez")
    if todo:
        print(f"TODO before the build can run: {todo} in config/fields/{field['id']}.yaml")
    print("\nDownloads (scripts/fetch_field.py):")
    mins = mb = 0
    for name, action in fp:
        m, size = FETCH_MINUTES.get(name, (1, 1))[k], FETCH_MB.get(name, (0, 0))[k]
        if action == "run":
            mins, mb = mins + m, mb + size
        print(f"  {name:15s} {action:45s} {'~%d min' % m if action == 'run' else ''}{', ~%d MB' % size if action == 'run' and size else ''}")
    print(f"  total to download: ~{mb} MB, ~{mins} min")
    print("\nBuild (scripts/run_field.py --only ...):")
    bmins = sum(BUILD_MINUTES.get(s, 1) for s in steps)
    for i, s in enumerate(steps, 1):
        print(f"  {i:2d}. {s:22s} ~{BUILD_MINUTES.get(s, 1)} min")
    print(f"  total: ~{bmins} min. Then the site folder.")
    if profile["_id"] == "default":
        print("Left out on the global defaults (they need a country profile): " +
              "; ".join(f"{s} ({why})" for s, why in PROFILE_ONLY.items()))
    return mins + bmins


def copy_site(field, out, site=REPO / "site"):
    """The static site with only this field: the app's files, words.json, every site/data/<kind>/<id>.* file of the
    field, and an index.json listing the field alone (pipeline/export/build_index.py)."""
    from pipeline.export.build_index import build_index
    from pipeline.export.validate import validate_index
    out = Path(out)
    if out.resolve() == site.resolve() or site.resolve() in out.resolve().parents:
        raise SystemExit("--out must be outside site/")
    out.mkdir(parents=True, exist_ok=True)
    for part in SITE_PARTS:
        src = site / part
        if src.is_dir():
            shutil.copytree(src, out / part, dirs_exist_ok=True)
        elif src.exists():
            shutil.copy2(src, out / part)
    data = out / "data"
    data.mkdir(exist_ok=True)
    shutil.copy2(site / "data" / "words.json", data / "words.json")
    copied = []
    for kind in sorted(p for p in (site / "data").iterdir() if p.is_dir()):
        for f in sorted(kind.glob(f"{field['id']}.*")) + sorted(kind.glob(f"{field['id']}_*")):
            (data / kind.name).mkdir(exist_ok=True)
            shutil.copy2(f, data / kind.name / f.name)
            copied.append(f"{kind.name}/{f.name}")
    for f in ("world.json", "world.jpg"):                       # the map's world picture (NASA Blue Marble)
        if (site / "data" / "basemap" / f).exists():
            (data / "basemap").mkdir(exist_ok=True)
            shutil.copy2(site / "data" / "basemap" / f, data / "basemap" / f)
    if f"fields/{field['id']}.json" not in copied:
        raise SystemExit(f"site/data/fields/{field['id']}.json does not exist: the build did not finish")
    idx = build_index([field], data)
    errs = validate_index(idx)
    if errs:
        raise SystemExit(f"index.json would break its schema: {errs}")
    (data / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n")
    return copied


def run(cmd, label, expect_min):
    print(f"\n== {label} (expected ~{expect_min} min): {' '.join(cmd)}", flush=True)
    t0 = time.time()
    code = subprocess.call([PY, *cmd], cwd=REPO)
    print(f"== {label}: exit {code}, {(time.time() - t0) / 60:.1f} min", flush=True)
    return code


def main(argv=None):
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.profiles import profile_for
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", help="an existing config/fields/<id>.yaml (then the point and name are not needed)")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--size-m", type=float, default=60.0, help="side of the square field, metres (default 60)")
    ap.add_argument("--name")
    ap.add_argument("--country", help="the country's name, as its profile lists it (e.g. Nepal)")
    ap.add_argument("--country-code", help="ISO 3166-1 alpha-2 code (e.g. NP, MG): picks the FAO crop calendar")
    ap.add_argument("--aez", help="the FAO crop-calendar zone id (python -m pipeline.fetch.cropcalendar --zones <ISO2>)")
    ap.add_argument("--rotation", help="the crops grown now, in order, e.g. rice,potato")
    ap.add_argument("--rotation-source", help="who said so, e.g. 'the farmer, 2026-11-20'")
    ap.add_argument("--station", help="a nearby NOAA GHCN-Daily station id (checks only)")
    ap.add_argument("--box-km", type=float, default=2.0, help="download box, km each way (default 2)")
    ap.add_argument("--id", help="the field's id (default: from the name)")
    ap.add_argument("--short-record", action="store_true", help="the last 10 years only (2016-2025), for faster downloads")
    ap.add_argument("--out", help="the static site folder to write (default: site_<id>/ next to the repository)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, the downloads and the time; run nothing")
    ap.add_argument("--skip-fetch", action="store_true", help="build from what data/ already holds")
    a = ap.parse_args(argv)

    if a.field:
        fid = a.field
    else:
        missing = [k for k in ("lat", "lon", "name", "country") if getattr(a, k) is None]
        if missing:
            ap.error(f"a new field needs --{', --'.join(missing)} (or --field <existing id>)")
        fid = a.id or slug(a.name)
    path = REPO / "config" / "fields" / f"{fid}.yaml"
    if not path.exists():
        text = config_text(a, fid)
        if a.dry_run:
            print(f"Would write {path.relative_to(REPO)}:\n{text}")
            field = {**__import__("yaml").safe_load(text)}
        else:
            path.write_text(text)
            print(f"wrote {path.relative_to(REPO)} (fill in its TODOs; never guess them)")
            field = load_field(fid)
    else:
        field = load_field(fid)
        print(f"using the existing {path.relative_to(REPO)}")
    profile = profile_for(field)
    short = (field.get("record_years") or FULL_YEARS)[0] > FULL_YEARS[0]
    steps = build_steps(field, profile["_id"])
    total = print_plan(field, profile, steps, short)
    out = Path(a.out) if a.out else REPO.parent / f"site_{fid}"
    print(f"\nSite folder: {out}  (expected total ~{total} min; hosting: docs/DEPLOY_ANYWHERE.md)")
    if a.dry_run:
        return 0
    if short:
        print("NOT READY: the shorter record. The downloads take record_years (scripts/fetch_field.py), but the build still "
              "assumes 2001-2025 (the rain check's 2001-2016 reference, the diary's MODIS years, the trends' base years). "
              "Dropped under the owner's stop rule (docs/NEXT_STEPS.md 8). Set record_years: [2001, 2025] to build.")
        return 2
    todo = [k for k in ("current_rotation",) if not field.get(k)]
    if profile["crop_calendar"]["windows"] == "fao_api" and not (field.get("fao_crop_calendar") or {}).get("aez"):
        todo.append("fao_crop_calendar (country and aez)")
    if todo:
        print(f"STOPPED: fill in {todo} in {path.relative_to(REPO)}, then run the same command again.")
        return 2
    t0 = time.time()
    if not a.skip_fetch and run(["scripts/fetch_field.py", "--field", fid], "1/3 downloads", total - sum(BUILD_MINUTES.get(s, 1) for s in steps)):
        print("STOPPED at the downloads: see data/raw/_logs/; run the same command again to resume.")
        return 1
    if run(["scripts/run_field.py", "--field", fid, "--only", *steps], "2/3 build", sum(BUILD_MINUTES.get(s, 1) for s in steps)):
        print(f"STOPPED in the build: fix the step it names, then run the same command again (or scripts/run_field.py "
              f"--field {fid} --from <step>).")
        return 1
    copied = copy_site(field, out)
    print(f"\n== 3/3 site folder: {out} ({len(copied)} data files: {copied}); {(time.time() - t0) / 60:.1f} min in all")
    print("Host it free: drag the folder onto Netlify Drop, or push it to a GitHub Pages or Vercel project "
          "(docs/DEPLOY_ANYWHERE.md). Open index.html through a web server, not as a file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
