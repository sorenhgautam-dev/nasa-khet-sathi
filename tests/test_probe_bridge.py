"""The probe bridge (build step 10, owner 2026-11-12). The probe is the robot teammate's own build; its code is
not changed and not in this repository. Over USB serial it prints one line every 2 seconds, exactly:

    Temperature: 23.1 °C  |  Moisture: 45%
    Temperature: Check wiring  |  Moisture: 45%      (temperature sensor disconnected)

Moisture is already 0-100 %, calibrated on the probe. rules.yaml probe.serial_line records this."""
import json
import os
import sys
import threading

import pytest

from pipeline.fetch.rules import load_rules
from robot import bridge, fake_probe, probe

OWNER_EXAMPLE = "Temperature: 23.1 °C  |  Moisture: 45%"
OWNER_WIRING = "Temperature: Check wiring  |  Moisture: 45%"


# ---------- parsing one line ----------

def test_the_owners_example_line():
    assert probe.parse_line(OWNER_EXAMPLE) == {"temp_c": 23.1, "moisture_pct": 45.0, "temp_status": "ok"}


def test_check_wiring_gives_no_temperature_but_keeps_the_moisture():
    assert probe.parse_line(OWNER_WIRING) == {"temp_c": None, "moisture_pct": 45.0, "temp_status": "check_wiring"}


def test_the_rules_record_the_owners_format():
    assert load_rules()["probe"]["serial_line"] == OWNER_EXAMPLE


@pytest.mark.parametrize("line,temp,moist", [
    ("Temperature: -2.5 °C  |  Moisture: 0%", -2.5, 0.0),
    ("Temperature: 30 °C  |  Moisture: 100%", 30.0, 100.0),
    ("Temperature: 23.1 °C  |  Moisture: 45.5%", 23.1, 45.5),
    ("Temperature: 23.1 °C  |  Moisture: 45%\r\n", 23.1, 45.0),       # Serial.println ends lines with \r\n
    ("Temperature: 23.1 °C | Moisture: 45%", 23.1, 45.0),              # spacing around the bar may vary
])
def test_variants_of_the_same_format(line, temp, moist):
    r = probe.parse_line(line)
    assert (r["temp_c"], r["moisture_pct"]) == (temp, moist)


@pytest.mark.parametrize("line", [
    "",
    "perature: 23.1 °C  |  Moisture: 45%",           # the first line read after opening a port is often cut
    "Temperature: 23.1 °C  |  Moisture: ",
    "Temperature: 23.1 C  |  Moisture: 45%",           # no degree sign
    "Moisture: 45%  |  Temperature: 23.1 °C",          # order matters
    "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",   # ESP32 boot text
    "Temperature: 23.1 °F  |  Moisture: 45%",
])
def test_anything_else_is_refused(line):
    with pytest.raises(probe.ProbeLineError):
        probe.parse_line(line)


@pytest.mark.parametrize("line", [
    "Temperature: 23.1 °C  |  Moisture: 101%",          # moisture is 0-100 % on the probe
    "Temperature: 60.0 °C  |  Moisture: 45%",           # golden rule 12b: -30 to 50 C
    "Temperature: -31.0 °C  |  Moisture: 45%",
])
def test_out_of_range_values_are_refused_not_clipped(line):
    with pytest.raises(probe.ProbeLineError, match="range"):
        probe.parse_line(line)


def test_bytes_decode_whether_the_degree_sign_is_utf8_or_one_latin1_byte():
    utf8 = "Temperature: 23.1 °C  |  Moisture: 45%\r\n".encode("utf-8")
    latin1 = b"Temperature: 23.1 \xb0C  |  Moisture: 45%\r\n"
    assert probe.decode_line(utf8) == probe.decode_line(latin1) == "Temperature: 23.1 °C  |  Moisture: 45%"


# ---------- the fake probe ----------

def test_the_fake_probe_prints_lines_the_parser_accepts():
    lines = list(fake_probe.lines(n=50, seed=1, wiring_every=0))
    assert len(lines) == 50
    for line in lines:
        r = probe.parse_line(line)
        assert r["temp_status"] == "ok" and 0 <= r["moisture_pct"] <= 100


def test_the_fake_probe_can_print_check_wiring():
    lines = list(fake_probe.lines(n=10, seed=1, wiring_every=5))
    assert sum(probe.parse_line(l)["temp_status"] == "check_wiring" for l in lines) == 2
    assert all("Check wiring" in lines[i] for i in (4, 9))


def test_the_fake_probe_uses_the_exact_format():
    line = next(fake_probe.lines(n=1, seed=1, wiring_every=0))
    assert fake_probe.LINE.format(temp=23.1, moist=45) == OWNER_EXAMPLE
    assert line.startswith("Temperature: ") and line.endswith("%") and "  |  Moisture: " in line


# ---------- the bridge ----------

class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 2
        return f"2026-11-14T10:32:{self.t:02d}"


def test_the_bridge_writes_live_json_from_good_lines_and_skips_bad_ones(tmp_path):
    out, log = tmp_path / "live.json", tmp_path / "readings.jsonl"
    raw = [b"ets Jun  8 2016 00:22:57\r\n", b"perature: 22.0 \xc2\xb0C  |  Moisture: 40%\r\n",
           "Temperature: 23.1 °C  |  Moisture: 45%\r\n".encode(),
           "Temperature: Check wiring  |  Moisture: 47%\r\n".encode()]
    stats = bridge.run(iter(raw), section="s3", out_path=out, log_path=log, clock=Clock())
    assert stats == {"good": 2, "bad": 2}
    live = json.loads(out.read_text())
    assert live == {"section": "s3", "wetness": 47, "temp": None, "sure": None, "time": "2026-11-14T10:32:08"}
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert [r["ok"] for r in rows] == [False, False, True, True]          # every line is kept, good or bad
    assert rows[2]["parsed"] == {"temp_c": 23.1, "moisture_pct": 45.0, "temp_status": "ok"}


def test_the_bridge_rounds_temperature_to_a_tenth_and_wetness_to_a_whole_number(tmp_path):
    out = tmp_path / "live.json"
    bridge.run(iter([b"Temperature: 23.14 \xb0C  |  Moisture: 45.6%\r\n"]), section="s1", out_path=out,
               log_path=tmp_path / "r.jsonl", clock=Clock())
    live = json.loads(out.read_text())
    assert live["temp"] == 23.1 and live["wetness"] == 46


def test_the_bridge_leaves_live_json_alone_when_no_line_is_good(tmp_path):
    out = tmp_path / "live.json"
    out.write_text('{"keep": true}')
    stats = bridge.run(iter([b"garbage\r\n"]), section="s1", out_path=out, log_path=tmp_path / "r.jsonl", clock=Clock())
    assert stats == {"good": 0, "bad": 1} and json.loads(out.read_text()) == {"keep": True}


def test_the_bridge_section_must_be_a_section_id():
    with pytest.raises(ValueError, match="section"):
        bridge.run(iter([]), section="part 3", out_path="x", log_path="y", clock=Clock())


@pytest.mark.skipif(sys.platform.startswith("win"), reason="pseudo-terminals are POSIX only")
def test_end_to_end_through_a_pseudo_terminal_like_a_usb_port(tmp_path):
    """The fake probe writes to a pseudo-terminal; the bridge opens its path with pyserial, as it would
    /dev/cu.usbserial-...; two readings arrive and live.json is written."""
    master, slave_path = fake_probe.open_pty()
    t = threading.Thread(target=fake_probe.serve, kwargs={"fd": master, "interval_s": 0.05, "n": 12, "seed": 2},
                         daemon=True)
    t.start()
    out = tmp_path / "live.json"
    try:
        stats = bridge.run(bridge.serial_lines(slave_path, baud=115200, max_lines=4), section="s2", out_path=out,
                           log_path=tmp_path / "r.jsonl")
    finally:
        t.join(timeout=5)
        os.close(master)
    assert stats["good"] >= 3
    live = json.loads(out.read_text())
    assert live["section"] == "s2" and 0 <= live["wetness"] <= 100


# ---------- the real sketch (robot/firmware/original_probe, sent by the owner 2026-11-12) ----------
import re
from pathlib import Path

SKETCH = Path(__file__).resolve().parents[1] / "robot" / "firmware" / "original_probe" / "original_probe.ino"


def _sketch_line(temp_c, moisture_pct):
    """What the sketch's print statements produce (Serial.print(temperature, 1) gives one decimal)."""
    head = "Check wiring" if temp_c is None else f"{temp_c:.1f}" + " °C"
    return "Temperature: " + head + "  |  Moisture: " + str(moisture_pct) + "%"


def test_the_sketch_prints_the_pieces_the_parser_expects():
    src = SKETCH.read_text(encoding="utf-8")
    for piece in ('Serial.print("Temperature: ")', 'Serial.print("Check wiring")', 'Serial.print(" °C")',
                  'Serial.print("  |  Moisture: ")', 'Serial.println("%")', "Serial.print(temperature, 1)",
                  "constrain(moisturePercent, 0, 100)", "delay(2000)"):
        assert piece in src, piece


def test_the_bridge_baud_rate_is_the_sketchs():
    baud = int(re.search(r"Serial\.begin\((\d+)\)", SKETCH.read_text(encoding="utf-8")).group(1))
    assert baud == bridge.DEFAULT_BAUD == 115200


@pytest.mark.parametrize("temp,moist", [(23.1, 45), (-2.5, 0), (49.9, 100), (None, 47)])
def test_every_line_the_sketch_can_print_in_range_parses(temp, moist):
    r = probe.parse_line(_sketch_line(temp, moist))
    assert r["temp_c"] == temp and r["moisture_pct"] == float(moist)


def test_the_ds18b20_power_on_value_is_refused_not_passed_on():
    """A DS18B20 read before its first conversion reports 85.0 C; outside -30..50, so the bridge skips it."""
    with pytest.raises(probe.ProbeLineError, match="range"):
        probe.parse_line(_sketch_line(85.0, 45))
