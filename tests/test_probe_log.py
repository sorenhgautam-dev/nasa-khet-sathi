"""site/data/probe_log.json (CLAUDE.md "How judges will see it" 4; owner's probe brief 2026-11-14, fix 5): per part the
median, spread, steady, water % and band, the twin before and after, and a link to the bench result, from REAL sessions
only (scripts/build_probe_log.py). Everything runs in a temporary folder: no real reading exists yet, so
site/data/probe_log.json is not written."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pipeline.fetch.rules import load_rules
from robot import bridge, fake_probe
from scripts import build_probe_log as bpl

REPO = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((REPO / "pipeline" / "export" / "probe_log_schema.json").read_text())
RULES = load_rules()["probe"]
TWIN = {"field": "demo", "date": "2026-11-14", "wetness_pct": 60.0, "prior_var": 100.0, "p0_var": 400.0,
        "q_var_per_day": 5.0, "sure_prior": 0.5, "theta_fc_m3m3": 0.33, "theta_wp_m3m3": 0.17, "crop": "potato"}
CAL = {"date": "2026-11-15", "fit": {"model": "line", "coef": [-5.0, 0.6]}, "mae_water_pct": 2.3, "r_probe_pct2": 1.3,
       "range_probe_pct": [8.0, 68.0], "cups": 6, "made_from": "the bench test of 2026-11-15, not field-tested"}


class Clock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 2
        return f"2026-11-16T10:{self.t // 60:02d}:{self.t % 60:02d}+05:45"


def _session(log_path, source, session, calib=CAL):
    ctx = bridge.Context(source, RULES, TWIN, calib, soil_top=(0.332, 0.150), crop_p=0.35, crop="potato", soil_distance_m=859)
    lines = [(l + "\r\n").encode() for t in (45, 30) for l in fake_probe.lines(n=RULES["settle_lines"] + RULES["measure_lines"], seed=int(t), scenario="settling", target=t)]
    log = bridge.Log(log_path, session)
    log({"kind": "session", "time": "2026-11-16T10:00:00+05:45", "source": source, "sections": ["s1", "s2"]})
    bridge.walk(bridge.IterSource(lines), ["s1", "s2"], log_path.parent / "live.json", log, ctx, lambda *a: "", clock=Clock())


def test_a_real_session_becomes_a_valid_replay(tmp_path):
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "serial:/dev/cu.usbserial-0001", "2026-11-16T100000_serial")
    doc = bpl.build([log], field="demo", bench={"file": "data/checks/probe/bench.json", "date": "2026-11-15",
                                                 "cups": 6, "mae_water_pct": 2.3})
    Draft202012Validator(SCHEMA).validate(doc)
    s = doc["sessions"][0]
    assert s["source"].startswith("serial:") and [p["section"] for p in s["parts"]] == ["s1", "s2"]
    p1 = s["parts"][0]
    assert p1["state"] == "done" and p1["steady"] and abs(p1["wetness"] - 45) <= 1 and p1["n"] == RULES["measure_lines"]
    assert p1["water_pct"] == pytest.approx(-5 + 0.6 * p1["wetness"], abs=0.5) and p1["band"] in ("needs water", "good", "too wet")
    # read 16 Nov, twin as of 14 Nov: P = 100 + 2 x 5 = 110, sure = 1 - sqrt(110) / 20 = 0.4756 -> 0.48
    assert p1["before"] == {"wetness": 60, "sure": 0.48} and p1["after"]["sure"] > 0.48
    assert s["parts"][1]["relative"] == "drier" and doc["bench"]["mae_water_pct"] == 2.3


def test_fake_sessions_are_skipped_and_a_file_of_only_fake_sessions_is_refused(tmp_path):
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "fake_probe", "2026-11-16T100000_fake_probe")
    with pytest.raises(ValueError, match="real serial port"):
        bpl.build([log], field="demo")
    _session(log, "serial:COM3", "2026-11-16T110000_serial")              # the same file, a real session after it
    doc = bpl.build([log], field="demo")
    assert [s["id"] for s in doc["sessions"]] == ["2026-11-16T110000_serial"] and doc["skipped"] == ["2026-11-16T100000_fake_probe"]


@pytest.mark.parametrize("source", ["stdin", "pty:/dev/ttys003"])
def test_stdin_and_pseudo_terminal_sessions_are_refused(tmp_path, source):
    log = tmp_path / "readings.jsonl"
    _session(log, source, f"x_{source.split(':')[0]}")
    with pytest.raises(ValueError, match="real serial port"):
        bpl.build([log], field="demo")


def test_no_real_session_writes_nothing(tmp_path):
    _session(tmp_path / "readings_2026-11-16.jsonl", "fake_probe", "f")
    out = tmp_path / "probe_log.json"
    assert bpl.main(["--field", "demo", "--dir", str(tmp_path), "--out", str(out)]) == 2 and not out.exists()


def test_the_cli_writes_a_valid_file_from_the_real_sessions(tmp_path):
    _session(tmp_path / "readings_2026-11-16.jsonl", "serial:COM3", "r")
    out = tmp_path / "probe_log.json"
    assert bpl.main(["--field", "demo", "--dir", str(tmp_path), "--out", str(out)]) == 0
    Draft202012Validator(SCHEMA).validate(json.loads(out.read_text()))


def test_before_the_bench_test_a_part_has_no_water_and_no_after(tmp_path):
    log = tmp_path / "readings.jsonl"
    _session(log, "serial:COM3", "r", calib=None)
    doc = bpl.build([log], field="demo")
    Draft202012Validator(SCHEMA).validate(doc)
    p = doc["sessions"][0]["parts"][0]
    assert p["water_pct"] is None and p["band"] is None and p["after"] is None and p["wetness"] is not None
    assert doc["bench"] is None


def test_the_file_says_when_and_where_it_was_recorded(tmp_path):
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "serial:COM3", "r")
    doc = bpl.build([log], field="demo", place="four pots of field soil at the event")
    Draft202012Validator(SCHEMA).validate(doc)
    assert doc["recorded_on"] == ["2026-11-16"] and doc["place"] == "four pots of field soil at the event"
    assert doc["note"].startswith("Recorded on 16 November 2026 ") and "four pots of field soil at the event" in doc["note"]
    assert bpl.build([log], field="demo")["place"] is None


def test_a_garden_test_is_labelled_so_and_never_updates_the_fields_twin(tmp_path):
    """Owner's answer 4, 2026-11-14 night; rules.yaml probe.live.garden_test."""
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "serial:COM3", "r")                 # with the bench calibration, so a normal walk has before and after
    normal = bpl.build([log], field="demo")
    assert normal["sessions"][0]["parts"][0]["after"] is not None and "kind" not in normal
    doc = bpl.build([log], field="demo", test="garden")
    Draft202012Validator(SCHEMA).validate(doc)
    assert doc["kind"] == "garden_test" and doc["twin_date"] is None
    assert doc["note"].startswith("Garden test of our soil stick, recorded on 16 November 2026")
    indoor = bpl.build([log], field="demo", test="indoor")
    Draft202012Validator(SCHEMA).validate(indoor)
    assert indoor["kind"] == "indoor_test" and indoor["note"].startswith("Indoor test of our soil stick (4 bowls of soil), recorded on 16")
    assert all(p["before"] is None and p["after"] is None for p in indoor["sessions"][0]["parts"])
    assert all(p["before"] is None and p["after"] is None and p["wetness"] is not None for p in doc["sessions"][0]["parts"])
    assert [p["relative"] for p in doc["sessions"][0]["parts"]] == [p["relative"] for p in normal["sessions"][0]["parts"]]


def test_every_reading_keeps_its_date_and_time_settling_lines_included(tmp_path):
    log = tmp_path / "readings.jsonl"
    _session(log, "serial:COM3", "r")
    doc = bpl.build([log], field="demo")
    Draft202012Validator(SCHEMA).validate(doc)
    for p in doc["sessions"][0]["parts"]:
        lines = p["lines"]
        assert len(lines) == RULES["settle_lines"] + RULES["measure_lines"]          # 5 settle, then 5 measured
        assert [x["phase"] for x in lines] == ["settle"] * RULES["settle_lines"] + ["measure"] * RULES["measure_lines"]
        assert all(x["time"].startswith("2026-11-16T") and x["time"].endswith("+05:45") for x in lines)
        assert [x["time"] for x in lines] == sorted(x["time"] for x in lines) and lines[-1]["time"] <= p["time"]
        measured = sorted(x["moisture"] for x in lines if x["phase"] == "measure")
        assert p["wetness"] == int(round(measured[len(measured) // 2]))             # the median of the 5 measured


def test_a_part_measured_again_keeps_only_the_lines_of_its_own_attempt(tmp_path):
    """A pulled cable restarts a part: the lines of the broken attempt are not the reading's lines."""
    log_path = tmp_path / "readings.jsonl"
    ctx = bridge.Context("serial:COM3", RULES, None, None)
    log = bridge.Log(log_path, "r")
    log({"kind": "session", "time": "2026-11-16T10:00:00+05:45", "source": "serial:COM3", "sections": ["s1"]})
    clock = Clock()
    for i, l in enumerate(fake_probe.lines(n=3, scenario="settling", target=60)):     # 3 lines, then the cable is pulled
        log({"kind": "line", "time": clock(), "section": "s1", "source": "serial:COM3", "line": l, "ok": True,
             "parsed": {"moisture_pct": 99.0, "temp_c": 20.0, "temp_status": "ok"}, "state": "settling"})
    log({"kind": "stale", "time": clock(), "section": "s1", "reason": "the probe's USB cable was pulled"})
    per = RULES["settle_lines"] + RULES["measure_lines"]
    lines = [(l + "\r\n").encode() for l in fake_probe.lines(n=per, seed=1, scenario="settling", target=40)]
    bridge.walk(bridge.IterSource(lines), ["s1"], tmp_path / "live.json", log, ctx, lambda *a: "", clock=clock)
    p = bpl.build([log_path], field="demo")["sessions"][0]["parts"][0]
    assert len(p["lines"]) == per and 99.0 not in [x["moisture"] for x in p["lines"]]


def test_only_the_chosen_sessions_are_published(tmp_path):
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "serial:COM3", "rehearsal")
    _session(log, "serial:COM3", "demo-walk")
    doc = bpl.build([log], field="demo", only=["demo-walk"])
    assert [s["id"] for s in doc["sessions"]] == ["demo-walk"]
    with pytest.raises(ValueError, match="no-such"):
        bpl.build([log], field="demo", only=["no-such"])
    out = tmp_path / "probe_log.json"
    assert bpl.main(["--field", "demo", "--dir", str(tmp_path), "--out", str(out), "--session", "demo-walk",
                     "--place", "the demo field"]) == 0
    got = json.loads(out.read_text())
    assert [s["id"] for s in got["sessions"]] == ["demo-walk"] and got["place"] == "the demo field"


def test_the_schema_itself_refuses_a_fake_source():
    doc = {"field": "demo", "note": "x", "built": "t", "recorded_on": ["2026-11-16"], "place": None, "twin_date": None,
           "bench": None, "skipped": [], "sessions": [{"id": "a", "source": "fake_probe", "start": "t", "end": "t", "parts": []}]}
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc))


def _bowl(section, measured, state="done"):
    return {"section": section, "state": state, "lines": [{"moisture": 50.0, "phase": "settle"}] * 20
            + [{"moisture": float(v), "phase": "measure"} for v in measured]}


def test_the_watered_bowl_check_with_worked_numbers():
    """rules.yaml probe.live.watered_check (owner, 2026-11-14 night): more than 2 x the repeat error above every other bowl.
    Each bowl alternates two values 2 points apart, so each variance is 1 and the pooled repeat error is 1: needed 2."""
    bowls = [_bowl("s1", [9, 11] * 5), _bowl("s2", [1, 3] * 5), _bowl("s3", [1, 3] * 5), _bowl("s4", [7, 9] * 5)]
    two = bpl.watered_check(bowls, "s1", "21:30", 2)     # medians 10, 2, 2, 8: the margin is 10 - 8 = 2, not MORE than 2
    assert two == {"watered": "s1", "watered_at": "21:30", "possible": True, "passed": False, "repeat_error_pct": 1.0,
                   "needed_pct": 2.0, "margin_pct": 2.0}
    bowls[3] = _bowl("s4", [6, 8] * 5)                    # median 7: margin 3 > 2
    assert bpl.watered_check(bowls, "s1", "21:30", 2)["passed"] is True
    assert bpl.watered_check(bowls, "s4", "21:30", 2)["margin_pct"] == -3.0     # bowl 1 reads wetter: fails
    flat = [_bowl("s1", [12] * 10), _bowl("s2", [3] * 10), _bowl("s3", [2, 4] * 5), _bowl("s4", [2, 4] * 5)]
    c = bpl.watered_check(flat, "s1", "21:30", 2)          # pooled: sqrt((0 + 0 + 1 + 1) / 4) = 0.7071
    assert (c["repeat_error_pct"], c["needed_pct"], c["margin_pct"], c["passed"]) == (0.71, 1.41, 9.0, True)
    unsteady = bowls[:3] + [_bowl("s4", [6, 8] * 5, state="test_again")]
    assert bpl.watered_check(unsteady, "s1", "21:30", 2)["possible"] is False   # a bowl with no steady reading
    with pytest.raises(ValueError):
        bpl.watered_check(bowls, "s9", "21:30", 2)


def test_the_check_is_written_only_for_a_test_and_validates(tmp_path):
    log = tmp_path / "readings_2026-11-16.jsonl"
    _session(log, "serial:COM3", "r")
    doc = bpl.build([log], field="demo", test="indoor", watered=("s1", "09:30"))
    Draft202012Validator(SCHEMA).validate(doc)
    assert doc["sessions"][0]["check"]["watered"] == "s1" and doc["sessions"][0]["check"]["possible"] is True
    assert "check" not in bpl.build([log], field="demo", watered=("s1", "09:30"))["sessions"][0]
    with pytest.raises(SystemExit):
        bpl.main(["--logs", str(log), "--out", str(tmp_path / "p.json"), "--watered", "s1", "--watered-at", "09:30"])  # no --test
    with pytest.raises(SystemExit):
        bpl.main(["--logs", str(log), "--out", str(tmp_path / "p.json"), "--test", "indoor", "--watered", "s1"])   # no time
