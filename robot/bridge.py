"""Probe bridge for the live demo (build step 10): read the soil probe over USB serial and write
site/data/live.json for the site.

    .venv/bin/python -m robot.bridge --port /dev/cu.usbserial-0001 --section s1   # the real probe (macOS)
    .venv/bin/python -m robot.bridge --port COM3 --section s1                     # Windows
    .venv/bin/python -m robot.bridge --port - --section s1                        # lines on stdin (fake probe pipe)

The probe prints one line every 2 seconds (robot/probe.py has the format, owner 2026-11-12). For each good line
the bridge writes live.json atomically:

    {"section": "s1", "wetness": 45, "temp": 23.1, "sure": null, "time": "2026-11-14T10:32:00"}

- wetness: the probe's moisture, already 0-100 % and calibrated on the probe, rounded to a whole number.
- temp: soil temperature in C to a tenth; null when the probe says "Check wiring".
- sure: null until the step-10 Kalman update fuses the reading with the twin (CLAUDE.md "Probe fusion").
- time: the laptop's local time when the line arrived.

A bad line (cut short when the port opens, the ESP32's boot text, a value out of range) is skipped with a
warning and never reaches live.json. Every line, good or bad, is appended to a log (data/probe/<field>/
readings_<date>.jsonl, gitignored) from which site/data/probe_log.json is made after the demo.
The baud rate is the probe sketch's Serial.begin(115200) (robot/firmware/original_probe, sent by the owner
2026-11-12).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from robot import probe

REPO = Path(__file__).resolve().parents[1]
SECTION = re.compile(r"^s[0-9]+$")       # the contract's section ids (schema.json)
DEFAULT_BAUD = 115200                     # the probe sketch's Serial.begin rate


def _now():
    """Local time with its UTC offset, e.g. 2026-11-14T10:32:00+05:45 (owner's answer 19 to REVIEW_2, 2026-11-13)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_atomic(path, doc):
    """Write JSON to a temporary file and rename it over `path`, so the site never reads half a file."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def run(raw_lines, section, out_path, log_path, clock=None):
    """Read lines (bytes or text) until they run out; return {'good': n, 'bad': n}."""
    if not SECTION.match(str(section)):
        raise ValueError(f"section must be a section id like s1 or s12 (the contract's), not {section!r}")
    clock = clock or _now
    out_path, log_path = Path(out_path), Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {"good": 0, "bad": 0}
    with log_path.open("a", encoding="utf-8") as log:
        for raw in raw_lines:
            t = clock()
            line = probe.decode_line(raw) if isinstance(raw, bytes) else raw.strip()
            try:
                r = probe.parse_line(line)
            except probe.ProbeLineError as e:
                stats["bad"] += 1
                log.write(json.dumps({"time": t, "section": section, "line": line, "ok": False, "error": str(e)},
                                     ensure_ascii=False) + "\n")
                log.flush()
                print(f"skipped: {e}", file=sys.stderr)
                continue
            stats["good"] += 1
            live = {"section": section, "wetness": int(round(r["moisture_pct"])),
                    "temp": None if r["temp_c"] is None else round(r["temp_c"], 1), "sure": None, "time": t}
            write_atomic(out_path, live)
            log.write(json.dumps({"time": t, "section": section, "line": line, "ok": True, "parsed": r},
                                 ensure_ascii=False) + "\n")
            log.flush()
            if r["temp_status"] == "check_wiring":
                print("probe says: check the temperature sensor's wiring (temp written as null)", file=sys.stderr)
    return stats


def serial_lines(port, baud=DEFAULT_BAUD, max_lines=None, timeout_s=5.0):
    """Lines (bytes) from a serial port. A silent port prints a warning every `timeout_s`; with max_lines
    set, a silent port ends the reading instead (used by tests)."""
    import serial

    with serial.Serial(port, baud, timeout=timeout_s) as s:
        got = 0
        while max_lines is None or got < max_lines:
            raw = s.readline()
            if not raw:
                print(f"no line from the probe for {timeout_s:g} s: check the USB cable, the port and the baud rate",
                      file=sys.stderr)
                if max_lines is not None:
                    return
                continue
            got += 1
            yield raw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", required=True, help="serial port, e.g. /dev/cu.usbserial-0001 or COM3; '-' = stdin")
    ap.add_argument("--section", required=True, help="the section the probe is in, e.g. s1")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--field", default="demo")
    ap.add_argument("--out", default=str(REPO / "site" / "data" / "live.json"))
    a = ap.parse_args(argv)
    log = REPO / "data" / "probe" / a.field / f"readings_{datetime.now():%Y-%m-%d}.jsonl"
    src = sys.stdin.buffer if a.port == "-" else serial_lines(a.port, a.baud)
    print(f"reading {a.port} for section {a.section} -> {a.out} (log {log})", file=sys.stderr)
    try:
        stats = run(src, a.section, a.out, log)
    except KeyboardInterrupt:
        return 0
    print(f"done: {stats['good']} good, {stats['bad']} skipped", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
