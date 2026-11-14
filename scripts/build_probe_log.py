"""Build site/data/probe_log.json from the bridge's recorded REAL walks (CLAUDE.md "How judges will see it" 4; owner's probe
brief, 2026-11-14, fix 5).

    .venv/bin/python scripts/build_probe_log.py --field demo          # data/probe/demo/readings_*.jsonl
    .venv/bin/python scripts/build_probe_log.py --field demo --logs data/probe/demo/readings_2026-11-16.jsonl
    .venv/bin/python scripts/build_probe_log.py --field demo --session 2026-11-16T103000_serial --place "the demo field"
    .venv/bin/python scripts/build_probe_log.py --field demo --session 2026-11-16T103000_serial --test garden   # or --test indoor

The file says when (recorded_on, and the note's first words: "Recorded on 16 November 2026") and, with --place, where
(e.g. "four pots of field soil at the event"). --session keeps only the named walks (a rehearsal with the real probe can
be left out); the session ids are printed by the bridge's log. Every reading keeps its date and time: each part's
`lines` are the 30 lines of the attempt that gave its number (20 settle, 10 measure), each with its local time.
Per part: the median on the probe's own scale, spread, steady, off the scale, temperature, water % and band (only after
the bench test), drier or wetter than the session's other parts, and the twin before and after the Kalman update; plus a
link to the bench result (config/probe_calibration.yaml -> data/checks/probe/bench.json). Only sessions read from a real
serial port are used (rules.yaml probe.live.replay_sources): a session from the fake probe, stdin or a pseudo-terminal is
skipped and named, and a log with no real session is refused, so no made-up number reaches the site. Validated against
pipeline/export/probe_log_schema.json; nothing is written if it fails. --test garden or --test indoor marks a test of the
probe away from the field (rules.yaml probe.live.garden_test; docs/PROBE_RECORDING.md 4b): kind 'garden_test' or
'indoor_test', labelled so, with no twin before or after.
"""
import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
SCHEMA = REPO / "pipeline" / "export" / "probe_log_schema.json"
NOTE = ("Readings recorded with the real soil probe at the in-person demo, replayed here: not live. Each part was settled, "
        "then measured; 'before' is the twin alone, 'after' the twin with the probe's reading.")


TESTS = {   # a test of the probe away from the field (owner, 2026-11-14 night): its note; the twin is never updated with it
    "garden": "Garden test of our soil stick, recorded on {when}: a 2 m by 2 m mini-field with one patch watered, all four "
              "patches probed.",
    "indoor": "Indoor test of our soil stick (4 bowls of soil), recorded on {when}: four bowls of the same soil, one watered, "
              "probed in order, 60 seconds each.",
}
NOT_FIELD = " Not the field shown here, and not live: the twin is not updated with this soil."


def note_for(dates, place, test=None):
    days = [datetime.fromisoformat(d) for d in dates]
    when = " and ".join(f"{d.day} {d:%B %Y}" for d in days)
    if test:
        return TESTS[test].format(when=when) + NOT_FIELD + (f" ({place})" if place else "")
    return f"Recorded on {when}" + (f" ({place})" if place else "") + ". " + NOTE


def estimate(d):
    if not d:
        return None
    return {"wetness": int(round(min(100.0, max(0.0, float(d["wetness"]))))), "sure": round(float(d["sure"]), 2)}


def line_docs(buffered, n_measured, settle_n):
    """The attempt's own lines: the last settle_n + n_measured good lines of the part (a pulled cable restarts a part,
    so lines of a broken attempt come before them), each with its time and phase."""
    own = buffered[-(settle_n + n_measured):]
    return [{"time": x["time"], "moisture": float(x["parsed"]["moisture_pct"]),
             "temp": None if x["parsed"].get("temp_c") is None else float(x["parsed"]["temp_c"]),
             "phase": "settle" if i < len(own) - n_measured else "measure"} for i, x in enumerate(own)]


def part_doc(rec, lines=()):
    r, ev = rec["result"], rec.get("eval") or {}
    return {"section": rec["section"], "time": rec["time"], "state": r["state"], "steady": bool(r["steady"]),
            "off_scale": bool(r["off_scale"]), "wetness": None if r["probe_pct"] is None else int(round(r["probe_pct"])),
            "spread_pct": r["spread_pct"], "n": r["n"], "temp": None if r["temp_c"] is None else round(r["temp_c"], 1),
            "water_pct": ev.get("water_pct"), "give_or_take_pct": ev.get("give_or_take_pct"), "band": ev.get("band"),
            "relative": None, "before": estimate(ev.get("before")), "after": estimate(ev.get("after")), "lines": list(lines)}


def build(paths, field, bench=None, allowed=("serial",), same_band=3, place=None, only=None, settle_n=20, test=None,
          watered=None, times=2.0):
    from robot.calibrate import relative
    sessions, sources, twin_dates, buffers = {}, {}, [], {}
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            sid = str(rec.get("session"))
            if rec.get("kind") == "session":
                sources[sid] = rec.get("source")
                if (rec.get("twin_state") or {}).get("date"):
                    twin_dates.append(rec["twin_state"]["date"])
            elif rec.get("kind") == "line" and rec.get("ok"):
                buffers.setdefault((sid, rec.get("section")), []).append(rec)
            elif rec.get("kind") == "part":
                sources.setdefault(sid, rec.get("source"))
                buf = buffers.pop((sid, rec["section"]), [])
                sessions.setdefault(sid, []).append((rec, line_docs(buf, int(rec["result"]["n"]), settle_n)))
    if only:
        missing = [s for s in only if s not in sessions]
        if missing:
            raise ValueError(f"no session {', '.join(missing)} in the logs (sessions found: {', '.join(sorted(sessions)) or 'none'})")
        sessions = {s: v for s, v in sessions.items() if s in only}
    keep = {s: v for s, v in sessions.items() if str(sources.get(s)).split(":")[0] in allowed}
    skipped = sorted(s for s in sessions if s not in keep)
    if not keep:
        raise ValueError(f"no session from a real serial port in {', '.join(str(p) for p in paths)} "
                         f"(skipped: {', '.join(f'{s} ({sources.get(s)})' for s in skipped) or 'none'})")
    out = []
    for sid, recs in sorted(keep.items(), key=lambda kv: kv[1][0][0]["time"]):
        parts = [part_doc(r, lines) for r, lines in recs]
        if test:   # garden or bowl soil is not the field's twin (rules.yaml probe.live.garden_test)
            for prt in parts:
                prt["before"] = prt["after"] = None
        for prt in parts:
            others = [o["wetness"] for o in parts if o is not prt and o["wetness"] is not None]
            prt["relative"] = relative(prt["wetness"], others, same_band) if prt["wetness"] is not None else None
        out.append({"id": sid, "source": sources[sid], "start": parts[0]["time"], "end": parts[-1]["time"], "parts": parts})
        if test and watered:   # the test's check (rules.yaml probe.live.watered_check)
            out[-1]["check"] = watered_check(parts, watered[0], watered[1], times)
    dates = sorted({p["time"][:10] for s in out for p in s["parts"]})
    doc = {"field": field, "note": note_for(dates, place, test), "built": datetime.now().astimezone().isoformat(timespec="seconds"),
           "recorded_on": dates, "place": place, "twin_date": None if test or not twin_dates else twin_dates[-1], "bench": bench,
           "skipped": skipped, "sessions": out}
    return dict(doc, kind=f"{test}_test") if test else doc


def watered_check(parts, watered, at, times):
    """rules.yaml probe.live.watered_check: the watered bowl must read more than `times` x the repeat error above every
    other bowl. A bowl's reading: the median of its steady attempt's measured lines; the repeat error: their standard
    deviation, pooled over the bowls. Not possible while a bowl has no steady reading."""
    sections = sorted({p["section"] for p in parts})
    if watered not in sections:
        raise ValueError(f"--watered {watered} is not a part of the walk ({', '.join(sections)})")
    done = {p["section"]: [x["moisture"] for x in p["lines"] if x["phase"] == "measure"] for p in parts if p["state"] == "done"}
    out = {"watered": watered, "watered_at": at, "possible": False, "passed": None, "repeat_error_pct": None,
           "needed_pct": None, "margin_pct": None}
    if set(done) != set(sections) or not all(done.values()):
        return out
    err = statistics.fmean(statistics.pvariance(v) for v in done.values()) ** 0.5
    margin = statistics.median(done[watered]) - max(statistics.median(v) for s, v in done.items() if s != watered)
    return dict(out, possible=True, passed=bool(margin > times * err), repeat_error_pct=round(err, 2),
                needed_pct=round(times * err, 2), margin_pct=round(margin, 2))


def bench_link(cal_path):
    from robot.calibrate import load_calibration
    c = load_calibration(cal_path)
    if c is None:
        return None
    return {"file": "data/checks/probe/bench.json", "date": str(c["date"]), "cups": int(c["cups"]),
            "mae_water_pct": float(c["mae_water_pct"])}


def validate(doc):
    from jsonschema import Draft202012Validator
    v = Draft202012Validator(json.loads(SCHEMA.read_text()))
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(doc)]


def main(argv=None):
    from pipeline.fetch.rules import load_rules
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--logs", nargs="*", help="bridge logs (default every data/probe/<field>/readings_*.jsonl)")
    ap.add_argument("--dir", default=None, help="folder to scan instead of data/probe/<field>/")
    ap.add_argument("--calibration", default=str(REPO / "config" / "probe_calibration.yaml"))
    ap.add_argument("--out", default=str(REPO / "site" / "data" / "probe_log.json"))
    ap.add_argument("--session", action="append", help="publish only this session (repeat for more); default every real one")
    ap.add_argument("--place", default=None, help='where it was recorded, in plain words, e.g. "four pots of field soil at the event"')
    ap.add_argument("--test", choices=sorted(TESTS), help="the walk was a test of the probe: the garden mini-field or 4 bowls indoors")
    ap.add_argument("--watered", help="with --test: the part that got water, e.g. s3 (bowl 3)")
    ap.add_argument("--watered-at", help="with --watered: the local time the water went in, HH:MM")
    a = ap.parse_args(argv)
    if (a.watered or a.watered_at) and not (a.test and a.watered and a.watered_at and re.fullmatch(r"[sp]\d+", a.watered)
                                             and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", a.watered_at)):
        ap.error("--watered sN and --watered-at HH:MM go together, with --test")
    rules = load_rules()["probe"]
    paths = [Path(p) for p in a.logs] if a.logs else sorted(Path(a.dir or REPO / "data" / "probe" / a.field).glob("readings_*.jsonl"))
    try:
        doc = build(paths, a.field, bench_link(a.calibration), tuple(rules["live"]["replay_sources"]), rules["same_band_pct"],
                    place=a.place, only=a.session, settle_n=int(rules["settle_lines"]), test=a.test,
                    watered=(a.watered, a.watered_at) if a.watered else None,
                    times=float(rules["live"]["watered_check"]["times_repeat_error"]))
    except ValueError as e:
        print(f"NOT YET POSSIBLE: {e}; nothing written", file=sys.stderr)
        return 2
    for s in doc["skipped"]:
        print(f"skipped (not from a real serial port): {s}", file=sys.stderr)
    errors = validate(doc)
    if errors:
        print("probe_log does not validate; nothing written:\n  " + "\n  ".join(errors[:20]), file=sys.stderr)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, out)
    print(f"{len(doc['sessions'])} real session(s), {sum(len(s['parts']) for s in doc['sessions'])} parts -> {out}")
    for s in doc["sessions"]:   # the test's check: the watered patch or bowl should read wetter than the others
        print(f"  {s['id']}: " + ", ".join(f"{p['section']} {p['relative'] or p['state']}" for p in s["parts"]))
        if s.get("check"):
            print(f"  watered-bowl check: {json.dumps(s['check'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
