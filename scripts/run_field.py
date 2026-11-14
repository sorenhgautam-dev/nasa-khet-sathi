"""One command: build a prepared field from the cached data/ folder (no downloads), then the site's files and the checks.

    .venv/bin/python scripts/run_field.py --field demo                  # every step, in order
    .venv/bin/python scripts/run_field.py --field demo --from plans     # resume at a step
    .venv/bin/python scripts/run_field.py --field demo --only export    # some steps only (--only diary replay ...)
    .venv/bin/python scripts/run_field.py --field demo --list           # the steps, and which run for this field

Builds from the downloads (scripts/fetch_field.py fetches them). Each step is one script or module, run as its own process
in the order the inputs need; the run stops at the first failure and --from resumes there. A sample field (config
`sample_of`) runs the CORE steps only, its checks being its source field's; before its own break test exists, the rain
check runs once before the weather too (rules.yaml gpm_series.correction_for_samples). Not in the chain: run_season.py
(step 4's one-season test), run_dhm_bulletin_check.py (needs DHM's bulletins), the probe's scripts, the one-off tools
pick_sample_fields.py and plot_pixels.py, and the proposal check runs written with --out-dir.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CORE, FULL, SITE = "every field", "not samples", "site-wide"
STEPS = [   # (name, command after the interpreter, which fields); --field <id> is added to every CORE and FULL step
    ("weather", ["-m", "pipeline.fetch.weather"], CORE),
    ("checks", ["scripts/run_checks.py"], FULL),
    ("rain_check", ["scripts/run_rain_check.py"], CORE),
    ("diary", ["scripts/run_diary.py"], CORE),
    ("diary_uncorrected", ["scripts/run_diary.py", "--steps", "onset,diary", "--rain", "uncorrected"], FULL),
    ("replay", ["scripts/run_replay.py"], CORE),
    ("replay_uncorrected", ["scripts/run_replay.py", "--rain", "uncorrected"], FULL),
    ("replay_dhm", ["scripts/run_replay.py", "--rain", "dhm"], FULL),
    ("replay_untuned", ["scripts/run_replay.py", "--rain", "untuned"], FULL),
    ("plans", ["scripts/run_plans.py"], CORE),
    ("plans_uncorrected", ["scripts/run_plans.py", "--rain", "uncorrected"], FULL),
    ("plans_dhm", ["scripts/run_plans.py", "--rain", "dhm"], CORE),
    ("plans_untuned", ["scripts/run_plans.py", "--rain", "untuned"], CORE),
    ("replay_soil_measured", ["scripts/run_replay.py", "--soil", "measured"], FULL),   # nothing runs without the team's
    ("plans_soil_measured", ["scripts/run_plans.py", "--soil", "measured"], FULL),     # tins and the switch (item 4)
    ("memory", ["scripts/run_memory.py"], FULL),
    ("twin_now", ["scripts/run_twin_now.py"], FULL),
    ("sections", ["scripts/run_sections.py"], FULL),
    ("future", ["scripts/run_future.py"], FULL),
    ("smap_check", ["scripts/run_smap_check.py"], FULL),
    ("validation_checks", ["scripts/run_validation_checks.py"], FULL),
    ("onset_check", ["scripts/run_onset_check.py"], FULL),
    ("onset_dhm", ["scripts/run_onset_dhm.py"], FULL),
    ("rain_selection", ["scripts/run_rain_selection.py"], FULL),
    ("area_map", ["scripts/run_area_map.py"], FULL),
    ("export", ["-m", "pipeline.export.build_field_json"], CORE),
    ("weather_ahead", ["scripts/run_weather.py"], CORE),   # the optional weather block (2026-11-14 evening), right after export
    ("index", ["-m", "pipeline.export.build_index"], SITE),
    ("words", ["-m", "pipeline.export.build_words"], SITE),
    ("replay_window", ["-m", "pipeline.export.build_replay"], CORE),   # the farmer's question (2026-11-14): 25-Year Replay,
    ("pulse", ["-m", "pipeline.export.build_pulse"], CORE),            # Field Pulse and Data Check-up, before verification
    ("checkup", ["-m", "pipeline.export.build_checkup"], CORE),        # (it scores them once the farmer's files exist)
    ("rainrisk", ["-m", "pipeline.export.build_risks", "--kind", "rainrisk"], CORE),       # 2026-11-14: rain at harvest,
    ("fertiliser", ["-m", "pipeline.export.build_risks", "--kind", "fertiliser"], CORE),   # fertiliser saver and heat clock
    ("heatclock", ["-m", "pipeline.export.build_risks", "--kind", "heatclock"], CORE),     # (labels refreshes their labels)
    ("verification", ["scripts/run_verification.py"], FULL),     # before story: the page shows this run's scorecard
    ("labels", ["-m", "pipeline.export.build_labels"], CORE),         # after verification: this run's scorecard
    ("simple", ["-m", "pipeline.export.build_simple"], CORE),         # the three farmer cards, from the replay and pulse files
    ("story", ["-m", "pipeline.export.build_story"], SITE),
    ("behind", ["-m", "pipeline.export.build_behind"], SITE),         # "Behind the scenes" (2026-11-15): counts and cards, after the story's charts
    ("validate", ["-m", "pipeline.export.validate", "--final"], SITE),
    ("site_check", ["scripts/check_site.py", "--final"], SITE),
]


def plan(field, only=None, start=None, has_break_test=True):
    """[(step, command)] for this field, in order. Pure."""
    names = [s[0] for s in STEPS]
    for n in [*(only or []), *([start] if start else [])]:
        if n not in names:
            raise SystemExit(f"unknown step {n!r}; the steps: {names}")
    sample = bool(field.get("sample_of"))
    out = []
    for name, cmd, kind in STEPS[names.index(start) if start else 0:]:
        if (only and name not in only) or (sample and kind == FULL):
            continue
        cmd = cmd if kind == SITE else [*cmd, "--field", field["id"]]
        if name == "weather" and sample and not has_break_test:
            out.append(("rain_check (break test first)", ["scripts/run_rain_check.py", "--field", field["id"]]))
        out.append((name, cmd))
    return out


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", required=True)
    ap.add_argument("--from", dest="start", default=None, help=f"start at this step: {[s[0] for s in STEPS]}")
    ap.add_argument("--only", nargs="+", default=None, help="run only these steps")
    ap.add_argument("--list", action="store_true", help="print the steps and stop")
    a = ap.parse_args(argv)
    field = load_field(a.field)
    steps = plan(field, a.only, a.start, (REPO / "data" / "checks" / field["id"] / "break_test.json").exists())
    t_all = time.time()
    for name, cmd in steps:
        print(f"== {name}: {' '.join(cmd)}", flush=True)
        if a.list:
            continue
        t0 = time.time()
        code = subprocess.call([sys.executable, *cmd], cwd=REPO)
        print(f"== {name}: exit {code}, {time.time() - t0:.0f} s", flush=True)
        if code != 0:
            print(f"STOPPED at {name} (exit {code}); fix it, then: scripts/run_field.py --field {a.field} --from "
                  f"{name.split()[0]}", file=sys.stderr)
            return 1
    if not a.list:
        print(f"done: {len(steps)} steps, {time.time() - t_all:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
