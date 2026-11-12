"""Parse the soil probe's USB serial lines (build step 10). Pure: no I/O.

The probe is the robot teammate's own build; its code is not changed and not in this repository. The owner
(2026-11-12) gave its output: one line every 2 seconds, exactly

    Temperature: 23.1 °C  |  Moisture: 45%
    Temperature: Check wiring  |  Moisture: 45%      (temperature sensor disconnected)

Moisture is already 0-100 %, calibrated on the probe itself (air = 0, water = 100), so it is used as it is.
The tokens, their order and the units must match; only the spacing around the bar may vary. Anything else
(a line cut short when the port opens, the ESP32's boot text) is refused, and so is a value outside its range
(golden rule 12c: fail loudly, never clip). rules.yaml probe.serial_line records the format.
"""
import re

TEMP_RANGE_C = (-30.0, 50.0)          # CLAUDE.md golden rule 12b
MOISTURE_RANGE_PCT = (0.0, 100.0)     # the probe's own calibrated scale (owner, 2026-11-12)

_NUM = r"-?\d+(?:\.\d+)?"
LINE = re.compile(rf"Temperature:\s+(?:(?P<temp>{_NUM})\s*°C|(?P<wiring>Check wiring))"
                  rf"\s*\|\s*Moisture:\s+(?P<moist>\d+(?:\.\d+)?)%")


class ProbeLineError(ValueError):
    """A serial line that is not a valid probe reading."""


def decode_line(raw):
    """Bytes from the serial port -> text without the line ending. The degree sign may arrive as UTF-8 (two
    bytes) or as one Latin-1 byte (0xB0), depending on how the firmware was saved; both give '°'."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return text.strip()


def parse_line(line):
    """'Temperature: 23.1 °C  |  Moisture: 45%' -> {'temp_c': 23.1, 'moisture_pct': 45.0, 'temp_status': 'ok'}.
    'Check wiring' gives temp_c None and temp_status 'check_wiring'. Raises ProbeLineError otherwise."""
    text = line.strip()
    m = LINE.fullmatch(text)
    if not m:
        raise ProbeLineError(f"not a probe line: {text!r}")
    moist = float(m["moist"])
    lo, hi = MOISTURE_RANGE_PCT
    if not lo <= moist <= hi:
        raise ProbeLineError(f"moisture {moist}% is outside the range {lo:g}-{hi:g}%: {text!r}")
    if m["wiring"]:
        return {"temp_c": None, "moisture_pct": moist, "temp_status": "check_wiring"}
    temp = float(m["temp"])
    lo, hi = TEMP_RANGE_C
    if not lo <= temp <= hi:
        raise ProbeLineError(f"temperature {temp} C is outside the range {lo:g} to {hi:g} C: {text!r}")
    return {"temp_c": temp, "moisture_pct": moist, "temp_status": "ok"}
