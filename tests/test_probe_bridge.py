"""The probe bridge (build step 10, owner 2026-11-12; owner's probe brief 2026-11-14: walk the parts, settle then measure,
write live.json only at state changes, the bench calibration, REVIEW_2 L7). The probe is the robot teammate's own build; its code is
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


def test_the_bridge_baud_rate_is_the_sketchs():  # noqa: E302
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


def test_the_bridge_stamps_local_time_with_its_utc_offset():
    """Owner's answer 19 to REVIEW_2 (2026-11-13): live.json's time says which clock it is."""
    import re
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", bridge._now())




# ---------- the walk (owner's probe brief, 2026-11-14: fixes 1, 2, 4 and REVIEW_2 L7) ----------

import itertools  # noqa: E402

from robot import settle  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 2
        return f"2026-11-14T10:{32 + self.t // 60:02d}:{self.t % 60:02d}+05:45"

RULES = load_rules()["probe"]
TWIN = {"field": "demo", "date": "2026-11-14", "wetness_pct": 60.0, "prior_var": 100.0, "p0_var": 400.0,
        "q_var_per_day": 5.0, "sure_prior": 0.5, "theta_fc_m3m3": 0.33, "theta_wp_m3m3": 0.17, "crop": "potato"}
CAL = {"date": "2026-11-15", "fit": {"model": "line", "coef": [-5.0, 0.6]}, "mae_water_pct": 2.3, "r_probe_pct2": 1.3,
       "range_probe_pct": [8.0, 68.0], "cups": 6, "made_from": "the bench test of 2026-11-15, not field-tested"}


def _ctx(twin=None, calib=None):
    return bridge.Context("serial:/dev/test", RULES, twin, calib, soil_top=(0.332, 0.150), crop_p=0.35, crop="potato",
                          soil_distance_m=859)


PER_PART = RULES["settle_lines"] + RULES["measure_lines"]   # 10 lines, 20 s (owner, 2026-11-15 afternoon; was 30)


def _fake(scenario, target=45.0, n=PER_PART, seed=4):
    return [(l + "\r\n").encode() for l in fake_probe.lines(n=n, seed=seed, scenario=scenario, target=target)]


def _walk(tmp_path, chunks, sections, ctx, answers=None, **kw):
    """Run the walk on canned lines; returns (code, every live.json written, log records)."""
    docs, out, logf = [], tmp_path / "live.json", tmp_path / "readings.jsonl"
    log = bridge.Log(logf, "test")
    src = bridge.IterSource(itertools.chain.from_iterable(chunks))          # lazy, like a port
    answers = list(answers or [])

    def wait(kind, sec, where=None):
        return answers.pop(0) if (kind == "again" and answers) else ("n" if kind == "again" else "")

    def write(doc):
        docs.append(doc)
        bridge.write_atomic(out, doc)
    code = bridge.walk(src, sections, out, log, ctx, wait, clock=Clock(), write=write, **kw)
    return code, docs, [json.loads(l) for l in logf.read_text().splitlines()]


def test_live_json_is_written_only_at_state_changes_never_while_settling(tmp_path):
    code, docs, recs = _walk(tmp_path, [_fake("settling", 45), _fake("settling", 30, seed=5)], ["s1", "s2"], _ctx())
    assert code == 0
    assert [(d["section"], d["state"]) for d in docs] == [("s1", "settling"), ("s1", "measuring"), ("s1", "done"),
                                                         ("s2", "settling"), ("s2", "measuring"), ("s2", "done")]
    for d in docs:
        if d["state"] in ("settling", "measuring"):
            assert d["wetness"] is None and d["temp"] is None and d["water_pct"] is None
    last = docs[-1]
    assert abs(last["wetness"] - 30) <= 1 and last["steady"] and last["off_scale"] is False and last["n"] == RULES["measure_lines"]
    assert [p["section"] for p in last["parts"]] == ["s1", "s2"]
    assert last["relative"] == "drier" and last["parts"][0]["relative"] == "wetter"       # 30 against 45
    assert last["water_pct"] is None and last["band"] is None and last["sure"] is None    # no bench calibration yet
    lines = [r for r in recs if r["kind"] == "line"]
    assert len(lines) == 2 * PER_PART and {r["section"] for r in lines} == {"s1", "s2"}     # every raw line logged
    assert [r["kind"] for r in recs].count("part") == 2


def test_a_jumpy_part_asks_to_test_again_with_no_number(tmp_path):
    code, docs, _ = _walk(tmp_path, [_fake("jumpy", 45)], ["s1"], _ctx())
    assert docs[-1]["state"] == "test_again" and docs[-1]["wetness"] is None and "again" in docs[-1]["note"]


def test_test_again_measures_the_part_again(tmp_path):
    code, docs, _ = _walk(tmp_path, [_fake("jumpy", 45), _fake("settling", 45)], ["s1"], _ctx(), answers=[""])
    assert [d["state"] for d in docs if d["state"] in ("done", "test_again")] == ["test_again", "done"]


def test_stuck_at_100_is_off_the_scale_never_a_value(tmp_path):
    _, docs, _ = _walk(tmp_path, [_fake("stuck100")], ["s1"], _ctx(TWIN, CAL))
    d = docs[-1]
    assert d["off_scale"] and d["wetness"] is None and d["water_pct"] is None and d["sure"] is None
    assert "off the scale" in d["note"]


def test_wiring_lost_keeps_the_moisture(tmp_path):
    _, docs, _ = _walk(tmp_path, [_fake("wiring_lost", 45)], ["s1"], _ctx())
    assert docs[-1]["state"] == "done" and docs[-1]["temp"] is None and abs(docs[-1]["wetness"] - 45) <= 1


def test_with_the_bench_calibration_hand_worked():
    # probe 45 % -> water -5 + 0.6 x 45 = 22.0 %; band: needs water below 26.83 % (potato p 0.35, fc 0.332, wp 0.150)
    # z = 100 x (0.22 - 0.17) / 0.16 = 31.25; R = 1.3 x (0.6 / 0.16)^2 = 18.28125; K = 100 / 118.28125 = 0.845443
    # x = 60 + K x (31.25 - 60) = 35.6935; P = (1 - K) x 100 = 15.4557; sure = 1 - sqrt(15.4557) / 20 = 0.803431
    res = settle.summarise([{"moisture_pct": 45.0, "temp_c": 18.0}] * 10, 3, 0.5, [0, 100])
    ev = bridge.evaluate_part(res, _ctx(TWIN, CAL), "2026-11-14")
    assert ev["water_pct"] == 22.0 and ev["band"] == "needs water" and ev["give_or_take_pct"] == 2.3
    assert ev["z_wetness"] == pytest.approx(31.25) and ev["r_var"] == pytest.approx(18.28125)
    assert ev["after"]["wetness"] == pytest.approx(35.6935, abs=1e-4) and ev["after"]["sure"] == pytest.approx(0.803431, abs=1e-6)
    assert ev["before"] == {"wetness": 60.0, "var": 100.0, "sure": 0.5}
    doc = bridge.live_doc("s1", "done", "2026-11-14T10:00:00+05:45", _ctx(TWIN, CAL), res, ev)
    assert doc["sure"] == 0.8 and doc["fused_wetness"] == 36 and doc["prior"] == {"wetness": 60, "sure": 0.5}
    assert any("859 m" in c for c in doc["caveats"]) and any("top few centimetres" in c for c in doc["caveats"])


def test_no_bench_calibration_no_water_no_band_no_sure():
    res = settle.summarise([{"moisture_pct": 45.0, "temp_c": 18.0}] * 10, 3, 0.5, [0, 100])
    ev = bridge.evaluate_part(res, _ctx(TWIN, None), "2026-11-14")
    assert ev["water_pct"] is None and ev["band"] is None and ev["after"] is None and ev["before"]["sure"] == 0.5


def test_the_prior_ages_from_the_twins_as_of_day():
    # as of 3 Nov, read 14 Nov: P = min(100 + 5 x 11, 400) = 155; sure = 1 - sqrt(155)/20 = 1 - 12.4499/20 = 0.377505
    p = bridge.twin_prior({**TWIN, "date": "2026-11-03"}, "2026-11-14")
    assert p["var"] == pytest.approx(155.0) and p["sure"] == pytest.approx(0.377505, abs=1e-6) and p["wetness"] == 60.0


class Ticks:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_silence_marks_live_json_stale(tmp_path):
    ticks = Ticks()

    def lines():
        yield from _fake("settling", 45, n=5)
        for _ in range(6):
            ticks.t += 2.0
            yield bridge.SILENT
    code, docs, recs = _walk(tmp_path, [lines()], ["s1"], _ctx(), monotonic=ticks, stale_after_s=10)
    live = json.loads((tmp_path / "live.json").read_text())
    assert live["stale"] is True and "input ended" in live["stale_reason"]
    assert any(r["kind"] == "stale" and "10 s" in r["reason"] for r in recs)


class Pulled(bridge.IterSource):
    """Lines, then the cable is pulled."""
    def lines(self):
        yield from self.it
        raise bridge.PortClosed("device reports readiness to read but returned no data (device disconnected?)")


def test_a_pulled_cable_gives_a_plain_message_and_a_stale_live_json(tmp_path, capsys):
    out, logf = tmp_path / "live.json", tmp_path / "r.jsonl"
    code = bridge.walk(Pulled(_fake("settling", 45, n=3)), ["s1"], out, bridge.Log(logf, "t"), _ctx(),
                       lambda *a: "", clock=Clock())   # pulled while settling
    err = capsys.readouterr().err
    assert code == 3 and "Traceback" not in err and "cable" in err
    live = json.loads(out.read_text())
    assert live["stale"] is True and "cable" in live["stale_reason"] and live["state"] == "settling"


def test_after_a_pulled_cable_the_part_starts_again(tmp_path):
    out, logf, opened = tmp_path / "live.json", tmp_path / "r.jsonl", []

    def reopen():
        opened.append(1)
        if len(opened) == 1:
            raise bridge.PortClosed("could not open port")          # still unplugged
        return bridge.IterSource(_fake("settling", 45))
    docs = []
    code = bridge.walk(Pulled(_fake("settling", 45, n=3)), ["s1"], out, bridge.Log(logf, "t"), _ctx(),
                       lambda *a: "", clock=Clock(), write=lambda d: (docs.append(d), bridge.write_atomic(out, d)),
                       reopen=reopen, reconnect=True, reconnect_every_s=0, sleep=lambda s: None)
    assert code == 0 and len(opened) == 2 and docs[-1]["state"] == "done" and docs[-1]["stale"] is False


@pytest.mark.skipif(sys.platform.startswith("win"), reason="pseudo-terminals are POSIX only")
def test_a_real_port_closing_under_the_bridge_is_handled(tmp_path, capsys):
    """The fake probe serves a pseudo-terminal, prints 3 lines and closes it, as a pulled USB cable does."""
    master, slave_path = fake_probe.open_pty()

    def serve_and_close():
        fake_probe.serve(fd=master, interval_s=0.1, n=3, seed=2)
        threading.Event().wait(0.6)             # let the bridge read the lines, then pull the "cable"
        os.close(master)
        os.close(fake_probe._KEEP_OPEN.pop(master))
    t = threading.Thread(target=serve_and_close, daemon=True)
    t.start()
    out = tmp_path / "live.json"
    code = bridge.walk(bridge.SerialSource(slave_path, timeout_s=0.5), ["s2"], out, bridge.Log(tmp_path / "r.jsonl", "t"),
                       _ctx(), lambda *a: "")
    t.join(timeout=5)
    assert code == 3 and "Traceback" not in capsys.readouterr().err
    assert json.loads(out.read_text())["stale"] is True


@pytest.mark.skipif(sys.platform.startswith("win"), reason="pseudo-terminals are POSIX only")
def test_end_to_end_through_a_pseudo_terminal_like_a_usb_port(tmp_path):
    """The fake probe writes to a pseudo-terminal; the bridge opens its path with pyserial, as it would
    /dev/cu.usbserial-...; lines arrive."""
    master, slave_path = fake_probe.open_pty()
    t = threading.Thread(target=fake_probe.serve, kwargs={"fd": master, "interval_s": 0.05, "n": 12, "seed": 2}, daemon=True)
    t.start()
    try:
        got = [r for r in bridge.serial_lines(slave_path, baud=115200, max_lines=4) if r is not bridge.SILENT]
    finally:
        t.join(timeout=5)
        os.close(master)
    assert len(got) >= 3 and all(probe.parse_line(probe.decode_line(r)) for r in got[1:])


def test_a_part_the_field_does_not_have_is_refused(capsys):
    assert bridge.main(["--fake", "settling", "--no-wait", "--sections", "s1,s99", "--out", "/tmp/x_live.json",
                        "--log-dir", "/tmp/x_probe"]) == 2
    assert "s99" in capsys.readouterr().err


def test_section_ids_and_corners_come_from_sections_json(tmp_path):
    (tmp_path / "data" / "checks" / "demo").mkdir(parents=True)
    (tmp_path / "site" / "data" / "fields").mkdir(parents=True)
    assert bridge.field_section_ids("demo", tmp_path) == (None, None)
    (tmp_path / "site" / "data" / "fields" / "demo.json").write_text(json.dumps({"field": {"sections": [{"id": "s1"}]}}))
    assert bridge.field_section_ids("demo", tmp_path)[0] == ["s1"]
    secs = [{"id": "s1", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]}, {"id": "s2", "polygon": [[1, 0], [2, 0], [2, 1], [1, 1]]},
            {"id": "s3", "polygon": [[0, 1], [1, 1], [1, 2], [0, 2]]}, {"id": "s4", "polygon": [[1, 1], [2, 1], [2, 2], [1, 2]]}]
    (tmp_path / "data" / "checks" / "demo" / "sections.json").write_text(json.dumps({"sections": secs}))
    assert bridge.field_section_ids("demo", tmp_path)[0] == ["s1", "s2", "s3", "s4"]
    assert bridge.where_words(secs) == {"s1": "south-west", "s2": "south-east", "s3": "north-west", "s4": "north-east"}


@pytest.mark.parametrize("port,fake,src", [("/dev/cu.usbserial-0001", False, "serial:/dev/cu.usbserial-0001"),
                                           ("COM3", False, "serial:COM3"), ("/dev/ttys003", False, "pty:/dev/ttys003"),
                                           ("/dev/pts/4", False, "pty:/dev/pts/4"), ("-", False, "stdin"),
                                           (None, True, "fake_probe")])
def test_every_session_names_its_source(port, fake, src):
    assert bridge.source_of(port, fake=fake) == src


def test_only_a_real_serial_port_may_write_under_site_data_or_the_real_logs(tmp_path):
    site_live = bridge.REPO / "site" / "data" / "live.json"
    real_logs = bridge.REPO / "data" / "probe" / "demo"
    for src in ("fake_probe", "stdin", "pty:/dev/ttys003"):
        with pytest.raises(ValueError, match="site/data"):
            bridge.guard_out_path(site_live, src)
        with pytest.raises(ValueError, match="data/probe/demo"):
            bridge.guard_out_path(real_logs, src, protected=real_logs)
        bridge.guard_out_path(tmp_path / "live.json", src)
    bridge.guard_out_path(site_live, "serial:/dev/cu.usbserial-0001")


def test_the_sketch_says_what_the_temperature_sensor_is():
    """REVIEW_2 L7: from the sketch, one DS18B20 on GPIO4 (OneWire), read in C to a tenth, 'Check wiring' when it does not
    answer; the sketch cannot say where the sensor sits (soil or air): the bridge says so."""
    src = SKETCH.read_text(encoding="utf-8")
    assert "DallasTemperature" in src and "TEMP_PIN = 4" in src and "getTempCByIndex(0)" in src
    assert "where the sensor sits" in bridge.TEMP_NOTE and "DS18B20" in bridge.TEMP_NOTE


def test_one_part_ending_never_closes_the_shared_stream(tmp_path):
    """A generator source (the fake probe, stdin) must survive from one part to the next."""
    gen = (l for c in (_fake("settling", 45), _fake("settling", 30, seed=5)) for l in c)
    docs = []
    code = bridge.walk(bridge.IterSource(gen), ["s1", "s2"], tmp_path / "live.json", bridge.Log(tmp_path / "r.jsonl", "t"),
                       _ctx(), lambda *a: "n", clock=Clock(), write=docs.append)
    assert code == 0 and [d["state"] for d in docs if d["state"] == "done"] == ["done", "done"]
