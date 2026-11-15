"""Probe bridge for the live demo (build step 10; owner's probe brief, 2026-11-14): walk the field's parts with the soil
probe, settle then measure each, and write site/data/live.json for the site.

    .venv/bin/python -m robot.bridge --port /dev/cu.usbserial-0001 --sections s1,s2,s3,s4     # the real probe (macOS)
    .venv/bin/python -m robot.bridge --port COM3                                              # Windows; every part
    .venv/bin/python -m robot.bridge --fake settling --no-wait --out /tmp/live.json --log-dir /tmp/probe   # rehearsal

For each part the operator puts the probe in and presses Enter. The probe prints a line every 2 s (robot/probe.py);
the first 20 good lines are discarded while it settles, the next 10 are measured (robot/settle.py). live.json is
written only when the state changes: settling -> measuring -> done | test_again, never with a number taken while the
probe settles (rules.yaml probe.live.state_writes). A 'done' part gives:

- wetness: the median of the 10 lines on the probe's own scale (air 0, water 100); null if not steady or off the scale
  (a median of 0 or 100: the sketch's own limit, shown as 'off the scale', never as a value).
- temp: the median temperature if its 10 lines agree within 0.5 C, else null. TEMP_NOTE says what the sensor is.
- water_pct, give_or_take_pct, band: only with config/probe_calibration.yaml from the team's real bench test
  (robot/bench.py, scripts/run_probe_bench.py); band from the field's own soil and the crop now (robot/calibrate.py).
  Without it the site shows only 'drier / wetter than the other parts' (relative).
- sure, fused_wetness: the Kalman update of the twin (CLAUDE.md "Probe fusion") from the twin's prior
  (data/clean/<field>/twin_state.json), only with the bench's R; null before the bench test.
Every raw line, good or bad, goes to data/probe/<field>/readings_<date>.jsonl with the session, the part and the
source, and each part's result too. A pulled USB cable gives a plain message, marks live.json stale and the bridge
tries the port again every 2 s (the part restarts); silence for 10 s marks it stale too (REVIEW_2 L7). Only a real
serial port may write under site/data/ or log into data/probe/<field>/. The baud rate is the sketch's 115200.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from pipeline.twin import kalman as kf
from robot import calibrate as cal
from robot import probe, settle

REPO = Path(__file__).resolve().parents[1]
SECTION = re.compile(r"^[sp][0-9]+$")   # the contract's section ids (schema.json): s1.., or p1.. for a drawn field's patches
DEFAULT_BAUD = 115200                     # the probe sketch's Serial.begin rate
SILENT = None                             # what a source yields when a read times out with no line
PTY = re.compile(r"^/dev/(ttys\d+|pts/\d+)$")
TEMP_NOTE = ("temp is what the probe's DS18B20 reads where the sensor sits. From the sketch (robot/firmware/original_probe): "
             "one DS18B20 on GPIO4 over OneWire (DallasTemperature, getTempCByIndex(0)), printed in C to a tenth, and "
             "'Check wiring' when no sensor answers (DEVICE_DISCONNECTED_C). Its comment 'Connect to S on the temperature "
             "sensor' points to a three-pin module; the sketch cannot say whether the sensor is in the soil or in the air, "
             "so this is soil temperature only once the owner confirms the sensor is in the soil (REVIEW_2 answer 19).")


class PortClosed(Exception):
    """The serial port could not be opened, or closed under the bridge (a pulled USB cable)."""


class EndOfInput(Exception):
    """The lines ran out (stdin closed, the fake probe stopped) before a part was finished."""


def _now():
    """Local time with its UTC offset, e.g. 2026-11-14T10:32:00+05:45 (owner's answer 19 to REVIEW_2, 2026-11-13)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_atomic(path, doc):
    """Write JSON to a temporary file and rename it over `path`, so the site never reads half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def mark_stale(path, reason, when):
    """Keep the last state but say it is not live any more (no file: nothing to mark)."""
    path = Path(path)
    try:
        doc = json.loads(path.read_text())
    except (ValueError, OSError):
        return False
    if not isinstance(doc, dict):
        return False
    write_atomic(path, {**doc, "stale": True, "stale_reason": reason, "stale_since": when})
    return True


# ---------- sources ----------

def source_of(port, fake=False):
    if fake:
        return "fake_probe"
    if port == "-":
        return "stdin"
    return f"pty:{port}" if PTY.match(str(port)) else f"serial:{port}"


def is_real(source):
    return str(source).startswith("serial:")


def guard_out_path(out_path, source, protected=None):
    """No made-up number reaches the site (or the real logs): only a real serial port may write under site/data/ or into
    `protected` (e.g. data/probe/<field>/)."""
    p = Path(out_path).resolve()
    for root in [REPO / "site" / "data"] + ([Path(protected)] if protected else []):
        r = Path(root).resolve()
        if not is_real(source) and (p == r or r in p.parents):
            raise ValueError(f"readings from {source} are not from the real probe, so they may not be written under "
                             f"{r.relative_to(REPO) if r.is_relative_to(REPO) else r}/ (no made-up number reaches the site): "
                             "pass a path elsewhere, e.g. /tmp/live.json")


class SerialSource:
    """The probe on a serial port. lines() yields bytes, or SILENT when a read times out; flush() drops what the port
    buffered while the operator was busy; a closed port raises PortClosed."""

    def __init__(self, port, baud=DEFAULT_BAUD, timeout_s=2.0):
        import serial
        self._serial = serial
        try:
            self.s = serial.Serial(port, baud, timeout=timeout_s)
        except (serial.SerialException, OSError) as e:
            raise PortClosed(f"could not open {port}: {e}") from None

    def lines(self):
        while True:
            try:
                raw = self.s.readline()
            except (self._serial.SerialException, OSError) as e:
                raise PortClosed(str(e)) from None
            yield raw if raw else SILENT

    def flush(self):
        try:
            self.s.reset_input_buffer()
        except (self._serial.SerialException, OSError) as e:
            raise PortClosed(str(e)) from None

    def close(self):
        try:
            self.s.close()
        except Exception:                           # closing a vanished port must not crash the bridge
            pass


class IterSource:
    """Lines from any iterable (stdin, the fake probe, tests); lines() continues where the last call stopped."""

    def __init__(self, iterable):
        self.it = iter(iterable)

    def lines(self):
        # not `yield from`: closing one part's generator must not close the shared stream (stdin, the fake probe)
        while True:
            try:
                x = next(self.it)
            except StopIteration:
                return
            yield x

    def flush(self):
        pass

    def close(self):
        pass


def serial_lines(port, baud=DEFAULT_BAUD, max_lines=None, timeout_s=2.0):
    """Lines (bytes) from a serial port; with max_lines set a silent port ends the reading (used by tests)."""
    src, got = SerialSource(port, baud, timeout_s), 0
    try:
        for raw in src.lines():
            if raw is SILENT:
                if max_lines is not None:
                    return
                yield SILENT
                continue
            got += 1
            yield raw
            if max_lines is not None and got >= max_lines:
                return
    finally:
        src.close()


def fake_lines(interval_s=2.0, n=None, seed=0, start_moist=45.0, **kw):
    """robot/fake_probe.py's made-up lines, for rehearsal only (source fake_probe: never into site/data/)."""
    from robot import fake_probe
    for line in fake_probe.lines(n=n, seed=seed, start_moist=start_moist, **kw):
        yield (line + "\r\n").encode("utf-8")
        time.sleep(interval_s)


# ---------- sections ----------

def _sections(doc):
    if isinstance(doc, dict) and isinstance(doc.get("sections"), list):
        return doc["sections"]
    if isinstance(doc, dict) and isinstance(doc.get("patches"), list):      # a drawn field's drone file (p1..)
        return doc["patches"]
    if isinstance(doc, dict) and isinstance(doc.get("field"), dict):
        return doc["field"].get("sections")
    return doc if isinstance(doc, list) else None


def field_section_ids(field_id, repo=REPO):
    """(ids, file): the field's sections from data/checks/<field>/sections.json, else from the field file, else a drawn
    field's patches from its drone file (site/data/drone/<field>.json: p1..p14 for Dhulikhel before its build)."""
    for path in (Path(repo) / "data" / "checks" / field_id / "sections.json",
                 Path(repo) / "site" / "data" / "fields" / f"{field_id}.json",
                 Path(repo) / "site" / "data" / "drone" / f"{field_id}.json"):
        if path.exists():
            secs = _sections(json.loads(path.read_text()))
            if secs and all(isinstance(s, dict) and "id" in s for s in secs):
                return [str(s["id"]) for s in secs], str(path)
    return None, None


def where_words(sections):
    """{id: 'south-west' ...}: each part's corner, from its polygon's centre against the field's."""
    cs = {}
    for s in sections or []:
        poly = s.get("polygon") if isinstance(s, dict) else None
        if poly:
            cs[str(s["id"])] = (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    if len(cs) < 2:
        return {}
    lon0, lat0 = sum(c[0] for c in cs.values()) / len(cs), sum(c[1] for c in cs.values()) / len(cs)
    return {k: ("north" if lat > lat0 else "south") + "-" + ("east" if lon > lon0 else "west") for k, (lon, lat) in cs.items()}


# ---------- one part's numbers (pure) ----------

def twin_prior(twin, day):
    """The twin alone on `day`: its as-of wetness, variance aged by Q a day (rules.yaml probe.kalman.age_after_as_of)."""
    days = (pd.Timestamp(day).normalize() - pd.Timestamp(twin["date"]).normalize()).days
    var = kf.aged_prior_var(twin["prior_var"], twin["q_var_per_day"], twin["p0_var"], max(days, 0))
    return {"wetness": float(twin["wetness_pct"]), "var": var, "sure": kf.sure(var, twin["p0_var"])}


class Context:
    """What the bridge knows besides the probe: the twin state, the bench calibration, the soil at the probe's depth
    and the crop now. Any of them may be missing; then the numbers that need it stay null."""

    def __init__(self, source, rules, twin=None, calibration=None, soil_top=None, crop_p=None, crop=None,
                 soil_distance_m=None):
        self.source, self.rules, self.twin, self.cal = source, rules, twin, calibration
        self.soil_top, self.crop_p, self.crop, self.soil_distance_m = soil_top, crop_p, crop, soil_distance_m

    def caveats(self):
        c = []
        if self.soil_distance_m:
            c.append(f"The soil numbers come from {self.soil_distance_m:g} m away.")
        c.append("The probe reads the top few centimetres, not the whole root zone.")
        if self.cal:
            c.append(f"Water from the {self.cal.get('label') or 'bench test'} of {self.cal['date']}, not tested in the field.")
        return c


def evaluate_part(res, ctx, day):
    """A finished part's result (settle.summarise) -> water %, band, the twin's prior and, with the bench's R, the
    Kalman update (rules.yaml probe.band, probe.kalman). Pure."""
    out = {"water_pct": None, "give_or_take_pct": None, "band": None, "band_limits_pct": None, "z_wetness": None,
           "z_limited": None, "before": None, "after": None, "r_var": None, "note": None}
    if ctx.twin:
        out["before"] = twin_prior(ctx.twin, day)
    if res["state"] != settle.DONE:
        out["note"] = "not steady: test this part again"
        return out
    if res["off_scale"]:
        out["note"] = "off the scale: the probe's own limit, not a reading"
        return out
    if not ctx.cal:
        return out
    x = res["probe_pct"]
    water = cal.apply_fit(x, ctx.cal["fit"])
    out["water_pct"], out["give_or_take_pct"] = round(water, 1), ctx.cal["mae_water_pct"]
    lo, hi = ctx.cal.get("range_probe_pct", [None, None])
    if lo is not None and not lo <= x <= hi:
        out["note"] = f"outside the bench cups' range ({lo:g}-{hi:g} %): the line is stretched"
    if ctx.soil_top and ctx.crop_p:
        b = cal.band(water, ctx.soil_top[0], ctx.soil_top[1], ctx.crop_p)
        out["band"], out["band_limits_pct"] = b["band"], {k: b[k] for k in ("needs_water_below_pct", "too_wet_above_pct")}
    if ctx.twin and out["before"]:
        fc, wp = float(ctx.twin["theta_fc_m3m3"]), float(ctx.twin["theta_wp_m3m3"])
        r = cal.r_twin_var(ctx.cal["r_probe_pct2"], cal.slope_at(x, ctx.cal["fit"]), fc, wp,
                           float(ctx.cal.get("fit_var_water_pct2", 0.0)))
        z = cal.wetness_from_water(water, fc, wp)
        f = kf.fuse_session(out["before"]["wetness"], out["before"]["var"], ctx.twin["p0_var"], [z], r)
        out.update(z_wetness=z, z_limited=f["z_limited"], r_var=r, after={"wetness": f["wetness"], "var": f["var"], "sure": f["sure"]})
    return out


def live_doc(section, state, t, ctx, res=None, ev=None, parts=None, index=None, total=None):
    """live.json for one moment of the walk (fields listed in robot/bridge.py's report to the integrator)."""
    prior = (ev or {}).get("before") or (twin_prior(ctx.twin, t[:10]) if ctx.twin else None)
    doc = {"section": section, "time": t, "state": state, "steady": None, "off_scale": None, "wetness": None,
           "spread_pct": None, "n": None, "temp": None, "temp_steady": None, "water_pct": None, "give_or_take_pct": None,
           "band": None, "relative": None, "sure": None, "fused_wetness": None,
           "prior": None if not prior else {"wetness": int(round(prior["wetness"])), "sure": round(prior["sure"], 2)},
           "twin_date": ctx.twin["date"] if ctx.twin else None, "caveats": ctx.caveats(), "parts": parts or [],
           "part": index, "parts_total": total, "source": ctx.source, "stale": False, "stale_reason": None, "note": None}
    if res is not None:
        doc.update(steady=res["steady"], off_scale=res["off_scale"], spread_pct=res["spread_pct"], n=res["n"],
                   wetness=None if res["probe_pct"] is None else int(round(res["probe_pct"])),
                   temp=None if res["temp_c"] is None else round(res["temp_c"], 1), temp_steady=res["temp_steady"])
    if ev is not None:
        doc.update(water_pct=ev["water_pct"], give_or_take_pct=ev["give_or_take_pct"], band=ev["band"], note=ev["note"])
        if ev["after"]:
            doc.update(sure=round(ev["after"]["sure"], 2), fused_wetness=int(round(ev["after"]["wetness"])))
    for p in doc["parts"]:
        if p["section"] == section:
            doc["relative"] = p["relative"]
    return doc


def parts_summary(done, same_band):
    """[{section, state, wetness, water_pct, band, relative, sure}] with drier / wetter against the other parts."""
    out = []
    for sec, d in done.items():
        others = [o["wetness"] for k, o in done.items() if k != sec and o["wetness"] is not None]
        rel = cal.relative(d["wetness"], others, same_band) if d["wetness"] is not None else None
        out.append({**d, "relative": rel})
    return out


# ---------- the walk ----------

class Log:
    """data/probe/<field>/readings_<date>.jsonl: every raw line, each part's result, events (append-only)."""

    def __init__(self, path, session):
        self.path, self.session = Path(path), session
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, rec):
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"session": self.session, **rec}, ensure_ascii=False, default=float) + "\n")


def measure_part(lines, section, ctx, log, clock, on_state, monotonic=time.monotonic, stale_after_s=None, out_path=None):
    """Feed lines to a settle.Part until it is done or test_again; on_state(state, part) at each change."""
    part = settle.Part.from_rules(ctx.rules)
    last_good, stale = monotonic(), False
    for raw in lines:
        if raw is SILENT:
            if stale_after_s is not None and not stale and monotonic() - last_good >= stale_after_s:
                why = f"no reading from the probe for {stale_after_s:g} s"
                if out_path is not None and mark_stale(out_path, why, clock()):
                    log({"kind": "stale", "time": clock(), "section": section, "reason": why})
                print(f"{why}: check the USB cable and the port (live.json marked stale)", file=sys.stderr)
                stale = True
            continue
        t = clock()
        text = probe.decode_line(raw) if isinstance(raw, bytes) else raw.strip()
        try:
            r = probe.parse_line(text)
        except probe.ProbeLineError as e:
            log({"kind": "line", "time": t, "section": section, "source": ctx.source, "line": text, "ok": False, "error": str(e)})
            continue
        before = part.state
        state = part.add(r)
        last_good, stale = monotonic(), False
        log({"kind": "line", "time": t, "section": section, "source": ctx.source, "line": text, "ok": True, "parsed": r,
             "state": state})
        if r["temp_status"] == "check_wiring" and before == settle.SETTLING and len(part.lines) == 1:
            print("probe says: check the temperature sensor's wiring (temp null; moisture still used)", file=sys.stderr)
        if state != before:
            on_state(state, part, t)
        if part.result() is not None:
            return part
    raise EndOfInput()


def walk(source, sections, out_path, log, ctx, wait, clock=None, write=None, reopen=None, reconnect=False,
         reconnect_every_s=2.0, sleep=time.sleep, monotonic=time.monotonic, stale_after_s=None, where=None):
    """Walk the parts in order; returns 0, or 3 when the port closed and reconnect is off."""
    clock = clock or _now
    write = write or (lambda doc: write_atomic(out_path, doc))
    where = where or {}
    done, i, n = {}, 0, len(sections)
    mark_stale(out_path, "no reading yet: the bridge has just started", clock())
    try:
        while i < n:
            sec = sections[i]
            wait("next", sec, where.get(sec))
            try:
                source.flush()
                write(live_doc(sec, settle.SETTLING, clock(), ctx, parts=parts_summary(done, ctx.rules["same_band_pct"]),
                               index=i + 1, total=n))

                def on_state(state, part, t, sec=sec, i=i):
                    if state == settle.MEASURING:
                        write(live_doc(sec, state, t, ctx, parts=parts_summary(done, ctx.rules["same_band_pct"]),
                                       index=i + 1, total=n))
                part = measure_part(source.lines(), sec, ctx, log, clock, on_state, monotonic, stale_after_s, out_path)
            except PortClosed as e:
                why = "the probe's USB cable was pulled or its port closed"
                print(f"The probe's USB cable was pulled, or its port closed ({e}). live.json is marked stale."
                      + (f" Trying the port again every {reconnect_every_s:g} s; Ctrl-C to stop." if reconnect else ""),
                      file=sys.stderr)
                if mark_stale(out_path, why, clock()):
                    log({"kind": "stale", "time": clock(), "section": sec, "reason": why, "detail": str(e)})
                if not reconnect or reopen is None:
                    log({"kind": "end", "time": clock(), "reason": why})
                    return 3
                source.close()
                while True:
                    sleep(reconnect_every_s)
                    try:
                        source = reopen()
                        break
                    except PortClosed:
                        continue
                print(f"The probe is back. Part {sec} starts again.", file=sys.stderr)
                continue
            except EndOfInput:
                why = "the bridge stopped: the probe's input ended"
                mark_stale(out_path, why, clock())
                log({"kind": "end", "time": clock(), "reason": why})
                return 0
            t, res = clock(), part.result()
            ev = evaluate_part(res, ctx, t[:10])
            done[sec] = {"section": sec, "state": res["state"], "wetness": None if res["probe_pct"] is None else
                         int(round(res["probe_pct"])), "water_pct": ev["water_pct"], "band": ev["band"],
                         "sure": None if not ev["after"] else round(ev["after"]["sure"], 2)}
            doc = live_doc(sec, res["state"], t, ctx, res, ev, parts_summary(done, ctx.rules["same_band_pct"]), i + 1, n)
            write(doc)
            log({"kind": "part", "time": t, "section": sec, "source": ctx.source, "result": res, "eval": ev,
                 "live": {k: doc[k] for k in ("wetness", "water_pct", "band", "relative", "sure", "fused_wetness")},
                 "values": part.values()})
            print(f"part {sec}: {res['state']}" + (f", {doc['wetness']} % on the probe" if doc["wetness"] is not None else "")
                  + (f", water {ev['water_pct']} % ({ev['band']})" if ev["water_pct"] is not None else "")
                  + (f"; {ev['note']}" if ev["note"] else ""), file=sys.stderr)
            if res["state"] == settle.TEST_AGAIN and wait("again", sec, where.get(sec)) != "n":
                continue
            i += 1
        log({"kind": "end", "time": clock(), "reason": "every part walked"})
        return 0
    except KeyboardInterrupt:
        why = "the bridge was stopped (Ctrl-C)"
        mark_stale(out_path, why, clock())
        log({"kind": "end", "time": clock(), "reason": why})
        return 0


def ask(kind, section, where=None):
    """The operator's prompts: put the probe in the next part; test a part again."""
    place = f" ({where})" if where else ""
    if kind == "again":
        return input(f"Part {section} was not steady. Press Enter to test it again, or type n and Enter to go on. ").strip().lower()
    return input(f"Put the probe in part {section}{place}, up to its line, then press Enter. ").strip().lower()


def build_context(field, source, rules, twin_path=None, calibration_path=None):
    """The twin state, the bench calibration, the soil at the probe's depth and the crop now (any may be missing)."""
    from pipeline.fetch.cropslib import load_crops
    twin_path = Path(twin_path or REPO / "data" / "clean" / field / "twin_state.json")
    twin = json.loads(twin_path.read_text()) if twin_path.exists() else None
    calib = cal.load_calibration(calibration_path or REPO / "config" / "probe_calibration.yaml")
    soil_path = REPO / "data" / "clean" / field / "soilgrids.parquet"
    soil_top = tuple(float(v) for v in cal.depth_theta(pd.read_parquet(soil_path), rules["probe_depth_m"])) \
        if soil_path.exists() else None
    crop = twin["crop"] if twin else None
    crop_p = load_crops()[crop]["p"] if crop and crop != "bare" else None
    card = REPO / "data" / "cards" / field / "soilgrids.json"
    dist = json.loads(card.read_text()).get("location", {}).get("distance_m") if card.exists() else None
    return Context(source, rules, twin, calib, soil_top, crop_p, crop, dist)


def main(argv=None):
    from pipeline.fetch.rules import load_rules
    from robot import fake_probe
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port, e.g. /dev/cu.usbserial-0001 or COM3; '-' = stdin")
    ap.add_argument("--fake", choices=fake_probe.SCENARIOS, help="rehearsal with the fake probe in this scenario")
    ap.add_argument("--fake-target", type=float, default=40.0)
    ap.add_argument("--fake-interval", type=float, default=0.05)
    ap.add_argument("--sections", default=None, help="parts to walk, e.g. s1,s2,s3,s4 (default: all of the field's)")
    ap.add_argument("--field", default="demo")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--out", default=str(REPO / "site" / "data" / "live.json"))
    ap.add_argument("--log-dir", default=None, help="default data/probe/<field>/")
    ap.add_argument("--twin-state", default=None)
    ap.add_argument("--calibration", default=None, help="default config/probe_calibration.yaml (from the bench test)")
    ap.add_argument("--no-wait", action="store_true", help="do not wait for Enter (rehearsal): a test_again part is skipped")
    ap.add_argument("--no-reconnect", action="store_true", help="stop (exit 3) when the cable is pulled")
    a = ap.parse_args(argv)
    if not a.port and not a.fake:
        ap.error("give --port (the probe's serial port), or --fake <scenario> for a rehearsal")
    rules = load_rules()["probe"]
    source = source_of(a.port, fake=bool(a.fake))
    log_dir = Path(a.log_dir or REPO / "data" / "probe" / a.field)
    try:
        guard_out_path(a.out, source)
        guard_out_path(log_dir, source, protected=REPO / "data" / "probe" / a.field)
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    ids, where_file = field_section_ids(a.field)
    if ids is None:
        print(f"refused: no sections for field '{a.field}' (data/checks/{a.field}/sections.json or the field file)", file=sys.stderr)
        return 2
    walk_ids = [s.strip() for s in a.sections.split(",")] if a.sections else ids
    bad = [s for s in walk_ids if not SECTION.match(s) or s not in ids]
    if bad:
        print(f"refused: field '{a.field}' has no part {', '.join(bad)} (parts from {where_file}: {', '.join(ids)})", file=sys.stderr)
        return 2
    where = where_words(_sections(json.loads(Path(where_file).read_text())))
    ctx = build_context(a.field, source, rules, a.twin_state, a.calibration)
    status = ("water % and the Kalman sure from the bench calibration of " + ctx.cal["date"]) if ctx.cal else \
        "no bench calibration yet: the probe's own percent and drier / wetter only; sure null"
    session = f"{datetime.now():%Y-%m-%dT%H%M%S}_{source.split(':')[0]}"
    log = Log(log_dir / f"readings_{datetime.now():%Y-%m-%d}.jsonl", session)
    log({"kind": "session", "time": _now(), "source": source, "field": a.field, "port": a.port, "sections": walk_ids,
         "twin_state": None if not ctx.twin else {k: ctx.twin.get(k) for k in (
             "date", "crop", "wetness_pct", "prior_var", "p0_var", "q_var_per_day", "sure_prior")},
         "calibration": None if not ctx.cal else {k: ctx.cal.get(k) for k in ("date", "fit", "mae_water_pct", "r_probe_pct2",
                                                                                 "label", "fit_var_water_pct2")},
         "soil_top": ctx.soil_top, "crop": ctx.crop, "crop_p": ctx.crop_p, "rules": "config/rules.yaml probe",
         "temp_note": TEMP_NOTE, "status": status})

    def reopen():
        return SerialSource(a.port, a.baud)
    try:
        if a.fake:
            src = IterSource(fake_lines(a.fake_interval, None, scenario=a.fake, target=a.fake_target, start_moist=0.0))
        elif a.port == "-":
            src = IterSource(sys.stdin.buffer)
        else:
            src = SerialSource(a.port, a.baud)
    except PortClosed as e:
        print(f"The probe's port did not open ({e}): check the USB cable and the port name.", file=sys.stderr)
        return 3
    wait = (lambda kind, sec, where=None: "n" if kind == "again" else "") if a.no_wait else ask
    print(f"walking {', '.join(walk_ids)} with {source} -> {a.out} (log {log.path}); {status}", file=sys.stderr)
    try:
        return walk(src, walk_ids, a.out, log, ctx, wait, reopen=reopen if source.startswith(("serial", "pty")) else None,
                    reconnect=not a.no_reconnect and source.startswith(("serial", "pty")),
                    reconnect_every_s=rules["live"]["reconnect_every_s"], stale_after_s=rules["live"]["stale_after_s"],
                    where=where)
    finally:
        src.close()


if __name__ == "__main__":
    sys.exit(main())
