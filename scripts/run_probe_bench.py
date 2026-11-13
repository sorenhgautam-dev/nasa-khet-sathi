"""The bench test's four proofs (owner's probe brief, 2026-11-14, fix 3) -> data/checks/probe/bench.json, and, only from
a real bench, config/probe_calibration.yaml.

    .venv/bin/python scripts/run_probe_bench.py                  # data/probe/bench/readings_*.jsonl + cups.csv

Reads the push-ins logged by robot/bench.py and the team's cups sheet (cup_id, cup_volume_ml, dry_soil_g,
water_added_g, notes). Proofs (robot/bench.analyse; rules.yaml probe.bench, fixed before any bench data):
(a) steady (VALIDATION 5.2): the spread within each push-in (at most 3 points) and between a cup's push-ins; the pooled
    variance of the repeats is the probe's error R for the Kalman;
(b) in order (5.3): cup values rise strictly with added water (Spearman reported);
(c) accurate (5.1): water % = water_added_g / cup_volume_ml x 100, fitted to the probe's percent with a line (a
    quadratic only by the rule fixed in advance), scored leave one cup out (MAE in water-% points), residuals reported;
(d) temperature: the ice-water cup reads 0 C within 0.5 C.
Also how long settling really takes. A log from the fake probe gives a labelled rehearsal result, which may not be
written to data/checks/probe/bench.json, and never a calibration file.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from robot import bench  # noqa: E402

BENCH_DIR = REPO / "data" / "probe" / "bench"
OUT = REPO / "data" / "checks" / "probe" / "bench.json"
CAL = REPO / "config" / "probe_calibration.yaml"


def main(argv=None):
    import yaml

    from pipeline.fetch.rules import load_rules
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", nargs="*", help="bench logs (default data/probe/bench/readings_*.jsonl)")
    ap.add_argument("--cups", default=str(BENCH_DIR / "cups.csv"))
    ap.add_argument("--out", default=None, help=f"default {OUT.relative_to(REPO)} (a real bench only)")
    ap.add_argument("--calibration-out", default=str(CAL))
    a = ap.parse_args(argv)
    logs = [Path(p) for p in a.log] if a.log else sorted(BENCH_DIR.glob("readings_*.jsonl"))
    if not logs or not Path(a.cups).exists():
        print("WAITING FOR THE BENCH TEST: no bench log or no cups.csv (robot/CUPS_PROTOCOL.md); nothing written")
        return 2
    records = [json.loads(l) for p in logs for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    cups = pd.read_csv(a.cups, dtype={"cup_id": str}, keep_default_na=False).to_dict("records")
    b = bench.analyse(records, cups, load_rules()["probe"])
    out = Path(a.out) if a.out else OUT
    if b["made_up"] and not a.out:
        ap.exit(2, "refused: these push-ins are made up (fake probe, stdin or a pseudo-terminal): pass --out to a file "
                   "outside data/checks/probe/bench.json\n")
    b["logs"] = [str(p) for p in logs]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(b, indent=1) + "\n")
    p, s = b["proofs"], b["settling"]
    print(f"{b['label']}: {b['cups_used']} cups used, excluded {b['excluded'] or 'none'}")
    print(f"(a) steady {p['steady']} (R {b['steady']['r_probe_pct2']}); (b) in order {p['order']} (Spearman "
          f"{b['order']['spearman']}); (c) accurate: leave-one-cup-out MAE {p['accurate']} water-% points "
          f"({b['accurate'].get('model')}); (d) ice water {p['temperature']} ({b['temperature']['median_c']} C)")
    print(f"settling: median {s['median_s']} s, longest {s['max_s']} s over {s['n']} steady push-ins -> {out}")
    doc = bench.calibration_doc(b)
    if doc is None:
        print("no calibration file: " + ("made-up readings" if b["made_up"] else "the fit or the order check failed"))
    else:
        cal = Path(a.calibration_out)
        cal.parent.mkdir(parents=True, exist_ok=True)
        cal.write_text("# Made by scripts/run_probe_bench.py from the team's bench cups. Not field-tested.\n"
                       + yaml.safe_dump(doc, sort_keys=False))
        print(f"-> {cal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
