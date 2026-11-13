"""The bench test, which is the proof (owner's probe brief, 2026-11-14, fix 3; robot/CUPS_PROTOCOL.md).

    .venv/bin/python -m robot.bench --port /dev/cu.usbserial-0001 --cup c1      # 3 push-ins, Enter between
    .venv/bin/python -m robot.bench --port /dev/cu.usbserial-0001 --cup ice     # the ice-water cup (temperature)
    .venv/bin/python scripts/run_probe_bench.py                                 # the four proofs -> bench.json

Each push-in is settled and measured exactly as a part in the field (robot/settle.py: 20 lines discarded, 10 measured),
every raw line is logged with the cup id and push-in number to data/probe/bench/readings_<date>.jsonl, and a 'pushin'
record keeps the result with every good line's time and value (for the settling time). The analysis is pure
(analyse): steady (5.2, and R for the Kalman), in order (5.3), accurate scored leave one cup out (5.1), the ice-water
temperature, and how long settling really takes. Rules: config/rules.yaml probe.bench (fixed before any bench data).
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from robot import probe, settle

REPO = Path(__file__).resolve().parents[1]
BENCH_DIR = REPO / "data" / "probe" / "bench"
QUAD_MIN_CUPS, QUAD_MARGIN = 5, 1.0           # rules.yaml probe.bench.fit (the sentence says both)
PORE_PARTICLE_DENSITY = 2.65                  # rules.yaml probe.bench.exclude_cups
NOTE_WORDS = ("pool", "pack")


# ---------- the analysis (pure) ----------

def fit_poly(x, y, degree):
    """Least squares; coef from the constant up (a, b[, c]); residuals y - fit."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    coef = np.polyfit(x, y, degree)[::-1]
    pred = sum(c * x ** k for k, c in enumerate(coef))
    return {"coef": [float(c) for c in coef], "residuals": [float(r) for r in y - pred]}


def loo_mae(x, y, degree):
    """Leave one cup out: refit without it, predict it; the mean absolute error."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    errs = []
    for i in range(len(x)):
        keep = np.arange(len(x)) != i
        coef = np.polyfit(x[keep], y[keep], degree)[::-1]
        errs.append(abs(y[i] - sum(c * x[i] ** k for k, c in enumerate(coef))))
    return float(np.mean(errs))


def choose_fit(x, y, bench_rules):
    """rules.yaml probe.bench.fit: a line, unless 5+ cups and a quadratic's leave-one-out error is 1.0 point lower."""
    line = {**fit_poly(x, y, 1), "loo_mae": loo_mae(x, y, 1)}
    quad = None
    if len(x) >= QUAD_MIN_CUPS:
        quad = {**fit_poly(x, y, 2), "loo_mae": loo_mae(x, y, 2)}
    use_quad = quad is not None and quad["loo_mae"] <= line["loo_mae"] - QUAD_MARGIN
    best = quad if use_quad else line
    return {"model": "quadratic" if use_quad else "line", "coef": best["coef"], "loo_mae": best["loo_mae"],
            "line": line, "quadratic": quad, "rule": bench_rules["fit"]}


def pooled_r(groups):
    """rules.yaml probe.bench.r: pooled variance of the repeats about their cup's mean, at least 1/12."""
    ss = dof = 0.0
    for vals in groups.values():
        v = np.asarray(vals, float)
        if len(v) >= 2:
            ss += float(((v - v.mean()) ** 2).sum())
            dof += len(v) - 1
    if dof == 0:
        return {"r_probe_pct2": None, "raw_pct2": None, "dof": 0}
    return {"r_probe_pct2": max(ss / dof, 1.0 / 12.0), "raw_pct2": ss / dof, "dof": int(dof)}


def settling_time_s(times_s, values, median, band):
    """rules.yaml probe.bench.settling: seconds from the first line to the first line after which every line stays
    within `band` of the measured median (None if it never does)."""
    v = np.abs(np.asarray(values, float) - float(median)) <= band
    for i in range(len(v)):
        if v[i:].all():
            return float(times_s[i] - times_s[0])
    return None


def exclusion_reasons(cup, value, steady_push_ins, off_scale=(0, 100)):
    """rules.yaml probe.bench.exclude_cups: why a cup is left out of the fit (empty list = used)."""
    why = []
    notes = str(cup.get("notes") or "").lower()
    if any(w in notes for w in NOTE_WORDS):
        why.append(f"notes say water pooled or the soil could not be packed: '{cup.get('notes')}'")
    vol, soil, water = float(cup["cup_volume_ml"]), float(cup["dry_soil_g"]), float(cup["water_added_g"])
    pore = 1.0 - (soil / vol) / PORE_PARTICLE_DENSITY
    if water / vol > pore:
        why.append(f"water {water / vol:.3f} of the cup is more than its pore space {pore:.3f}")
    if steady_push_ins == 0 or value is None:
        why.append("no steady push-in")
    elif float(value) in {float(o) for o in off_scale}:
        why.append(f"off the scale ({value:g} %)")
    return why


def order_check(water, values):
    """rules.yaml probe.bench.order: strictly rising with added water; Spearman's rho."""
    s = pd.DataFrame({"w": water, "v": values}).sort_values("w")
    v = s["v"].to_numpy(float)
    rho = round(float(s["w"].rank().corr(s["v"].rank())), 4) if len(s) > 1 else None
    return {"passes": bool(len(v) > 1 and (np.diff(v) > 0).all()), "spearman": rho}


def ice_check(temps, rule):
    if not temps:
        return {"passes": None, "median_c": None, "rule": rule}
    med = float(np.median(temps))
    return {"passes": bool(abs(med - rule["expected"]) <= rule["tolerance"] + 1e-9), "median_c": med, "rule": rule}


def _seconds(times):
    t = pd.to_datetime(list(times), utc=True)
    return (t - t[0]).total_seconds().to_numpy(float)


def analyse(records, cups, rules):
    """Push-in records (record_pushin) and the cups sheet (cups.csv rows) -> bench.json's content. Pure."""
    b = rules["bench"]
    pis = [r for r in records if r.get("kind") == "pushin"]
    if not pis:
        raise ValueError("no push-in in the bench log")
    sources = sorted({str(r["source"]) for r in pis})
    made_up = any(not s.startswith("serial:") for s in sources)
    by_cup = {}
    for r in pis:
        by_cup.setdefault(str(r["cup"]), []).append(r)
    rows, used, excluded = [], [], []
    for cup in cups:
        cid = str(cup["cup_id"])
        if cid == "ice":
            continue
        got = by_cup.get(cid, [])
        steady = [r["result"]["median_pct"] for r in got if r["result"]["steady"]]
        value = float(np.median(steady)) if steady else None
        why = exclusion_reasons(cup, value, len(steady), rules["off_scale_pct"])
        row = {"cup_id": cid, "water_pct": float(cup["water_added_g"]) / float(cup["cup_volume_ml"]) * 100.0,
               "push_ins": len(got), "push_in_medians_pct": [r["result"]["median_pct"] for r in got],
               "within_spread_pct": [r["result"]["spread_pct"] for r in got], "steady_push_ins": len(steady),
               "between_spread_pct": float(max(steady) - min(steady)) if len(steady) > 1 else None,
               "value_pct": value, "excluded": why, "notes": cup.get("notes") or ""}
        rows.append(row)
        (excluded if why else used).append(row)
    used.sort(key=lambda r: r["water_pct"])
    soil_pis = [r for r in pis if str(r["cup"]) != "ice"]
    rr = pooled_r({r["cup_id"]: [m for m, s in zip(r["push_in_medians_pct"], r["within_spread_pct"])
                                 if s <= rules["repeat_spread_max_pct"]] for r in used})
    steady = {"passes": bool(soil_pis) and all(r["result"]["steady"] for r in soil_pis),
              "push_ins": len(soil_pis), "not_steady": [f"{r['cup']}#{r['push_in']}" for r in soil_pis if not r["result"]["steady"]],
              "limit_pct": rules["repeat_spread_max_pct"], **rr}
    order = order_check([r["water_pct"] for r in used], [r["value_pct"] for r in used]) if len(used) > 1 else \
        {"passes": None, "spearman": None}
    if len(used) >= b["min_cups"]:
        f = choose_fit([r["value_pct"] for r in used], [r["water_pct"] for r in used], b)
        accurate = {"model": f["model"], "coef": f["coef"], "loo_mae_water_pct": round(f["loo_mae"], 4),
                    "line": f["line"], "quadratic": f["quadratic"], "cups": [r["cup_id"] for r in used],
                    "range_probe_pct": [min(r["value_pct"] for r in used), max(r["value_pct"] for r in used)]}
        slope = f["coef"][1]
        steady["r_water_pct2_at_slope"] = None if rr["r_probe_pct2"] is None else rr["r_probe_pct2"] * slope ** 2
    else:
        accurate = {"model": None, "why": f"{len(used)} cups used, at least {b['min_cups']} needed"}
    ice = [r["result"]["temp_c"] for r in pis if str(r["cup"]) == "ice" and r["result"]["temp_c"] is not None]
    temperature = ice_check(ice, b["ice_c"])
    times = []
    for r in pis:
        if r["result"]["steady"]:
            s = settling_time_s(_seconds(r["times"]), r["values"], r["result"]["median_pct"], rules["repeat_spread_max_pct"])
            times.append(s)
    known = [t for t in times if t is not None]
    settling = {"n": len(times), "median_s": float(np.median(known)) if known else None,
                "max_s": float(max(known)) if known else None,
                "within_settle_lines": sum(t <= 2.0 * rules["settle_lines"] for t in known),
                "definition": b["settling"]}
    date = str(pd.Timestamp(pis[0]["time"]).date())
    return {"made_up": made_up, "label": ("REHEARSAL: made-up readings (fake probe, stdin or a pseudo-terminal), never a "
                                          "calibration") if made_up else f"bench test of {date}",
            "date": date, "sources": sources, "cups": rows, "cups_used": len(used),
            "excluded": [{"cup_id": r["cup_id"], "why": r["excluded"]} for r in excluded],
            "steady": steady, "order": order, "accurate": accurate, "temperature": temperature, "settling": settling,
            "proofs": {"steady": steady["passes"], "order": order["passes"],
                       "accurate": accurate.get("loo_mae_water_pct"), "temperature": temperature["passes"]},
            "rules": "config/rules.yaml probe.bench, settle_lines, measure_lines, repeat_spread_max_pct"}


def calibration_doc(b):
    """config/probe_calibration.yaml's content, or None: only from a real bench with a fit and cups in order."""
    if b["made_up"] or not b["accurate"].get("model") or not b["order"]["passes"] or b["steady"]["r_probe_pct2"] is None:
        return None
    a = b["accurate"]
    return {"made_from": f"the bench test of {b['date']}, not field-tested", "date": b["date"], "cups": b["cups_used"],
            "fit": {"model": a["model"], "coef": a["coef"]}, "mae_water_pct": round(a["loo_mae_water_pct"], 2),
            "range_probe_pct": a["range_probe_pct"], "r_probe_pct2": round(b["steady"]["r_probe_pct2"], 4),
            "excluded_cups": b["excluded"], "ice_water_c": b["temperature"]["median_c"],
            "proofs": b["proofs"], "rules": b["rules"], "made_by": "scripts/run_probe_bench.py"}


# ---------- recording one push-in ----------

def record_pushin(lines, cup, push_in, source, rules, clock=None, log=None):
    """Read lines (bytes, text, or the bridge's SILENT) until the push-in is settled and measured; every raw line goes to
    `log` (a callable) when given. Returns the 'pushin' record."""
    from robot.bridge import SILENT, _now
    clock = clock or _now
    part = settle.Part.from_rules(rules)
    times, bad = [], 0
    for raw in lines:
        if raw is SILENT:
            continue
        t = clock()
        text = probe.decode_line(raw) if isinstance(raw, bytes) else raw.strip()
        try:
            r = probe.parse_line(text)
        except probe.ProbeLineError as e:
            bad += 1
            if log:
                log({"kind": "line", "cup": cup, "push_in": push_in, "time": t, "source": source, "line": text,
                     "ok": False, "error": str(e)})
            continue
        state = part.add(r)
        times.append(t)
        if log:
            log({"kind": "line", "cup": cup, "push_in": push_in, "time": t, "source": source, "line": text, "ok": True,
                 "parsed": r, "state": state})
        if part.result() is not None:
            return {"kind": "pushin", "cup": cup, "push_in": push_in, "time": times[0], "source": source,
                    "result": part.result(), "values": part.values(), "times": times, "bad_lines": bad}
    raise ValueError(f"the probe's input ended before cup {cup} push-in {push_in} was settled and measured")


def main(argv=None):
    from pipeline.fetch.rules import load_rules
    from robot import bridge
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="the probe's serial port, e.g. /dev/cu.usbserial-0001 or COM3")
    ap.add_argument("--fake", action="store_true", help="rehearsal with the fake probe (never into data/probe/bench/)")
    ap.add_argument("--target", type=float, default=40.0, help="fake only: the moisture the fake probe settles to")
    ap.add_argument("--cup", required=True, help="cup id from cups.csv (c1 ... c6), or 'ice'")
    ap.add_argument("--log-dir", default=str(BENCH_DIR))
    ap.add_argument("--no-wait", action="store_true", help="do not wait for Enter between push-ins (rehearsal)")
    a = ap.parse_args(argv)
    if not a.port and not a.fake:
        ap.error("give --port, or --fake for a rehearsal")
    rules = load_rules()["probe"]
    source = bridge.source_of(a.port, fake=a.fake)
    if not bridge.is_real(source) and Path(a.log_dir).resolve() == BENCH_DIR.resolve():
        print(f"refused: readings from {source} are made up: pass --log-dir to a folder outside data/probe/bench/", file=sys.stderr)
        return 2
    log_path = Path(a.log_dir) / f"readings_{datetime.now():%Y-%m-%d}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(rec):
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    src = (bridge.IterSource(bridge.fake_lines(0.05, None, start_moist=0.0, scenario="settling", target=a.target))
           if a.fake else bridge.SerialSource(a.port))
    try:
        for k in range(1, rules["bench"]["push_ins"] + 1):
            if not a.no_wait:
                input(f"Cup {a.cup}, push-in {k} of {rules['bench']['push_ins']}: push the probe in to its line, then press Enter. ")
            src.flush()
            print(f"  settling {rules['settle_lines']} lines, then measuring {rules['measure_lines']} (about "
                  f"{2 * (rules['settle_lines'] + rules['measure_lines'])} s) ...", flush=True)
            rec = record_pushin(src.lines(), a.cup, k, source, rules, log=log)
            log(rec)
            r = rec["result"]
            print(f"  {a.cup} #{k}: {r['state']}, median {r['median_pct']:g} %, spread {r['spread_pct']:g}"
                  + (f", temp {r['temp_c']:.1f} C" if r["temp_c"] is not None else ", temp not steady or no sensor")
                  + (" (OFF THE SCALE)" if r["off_scale"] else ""))
            if k < rules["bench"]["push_ins"] and not a.no_wait:
                print("  take the probe out and wipe it.")
    except bridge.PortClosed as e:
        print(f"The probe's USB cable was pulled, or its port closed ({e}); the push-ins done so far are in {log_path}.",
              file=sys.stderr)
        return 3
    finally:
        src.close()
    print(f"-> {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
