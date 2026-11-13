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
    lines = [(l + "\r\n").encode() for t in (45, 30) for l in fake_probe.lines(n=30, seed=int(t), scenario="settling", target=t)]
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
    assert p1["state"] == "done" and p1["steady"] and abs(p1["wetness"] - 45) <= 1 and p1["n"] == 10
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


def test_the_schema_itself_refuses_a_fake_source():
    doc = {"field": "demo", "note": "x", "built": "t", "twin_date": None, "bench": None, "skipped": [],
           "sessions": [{"id": "a", "source": "fake_probe", "start": "t", "end": "t", "parts": []}]}
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc))
