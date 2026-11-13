"""Owner's probe brief, 2026-11-14, fix 1: settle, then measure (robot/settle.py; rules.yaml probe.settle_lines,
measure_lines, repeat_spread_max_pct, temp_spread_max_c, off_scale_pct), and fix 5: the fake probe's test cases
(robot/fake_probe.py scenarios: a settling ramp, jumpy readings, stuck at 100, wiring lost)."""
import pytest

from pipeline.fetch.rules import load_rules
from robot import fake_probe, probe, settle

RULES = load_rules()["probe"]


def _l(m, t=18.0):
    return {"moisture_pct": float(m), "temp_c": t}


def test_the_rules_hold_the_owners_numbers():
    assert (RULES["settle_lines"], RULES["measure_lines"], RULES["repeat_spread_max_pct"]) == (20, 10, 3)
    assert RULES["temp_spread_max_c"] == 0.5 and RULES["off_scale_pct"] == [0, 100]


def test_a_part_settles_then_measures_hand_worked():
    # 20 lines discarded (they never count), then 44 45 45 46 47 45 44 45 46 45: median 45, spread 47 - 44 = 3 -> steady
    p = settle.Part.from_rules(RULES)
    states = [p.add(_l(m)) for m in range(0, 100, 5)]                   # a wild settling ramp: 0, 5, ... 95
    assert states[:19] == ["settling"] * 19 and states[19] == "measuring"
    temps = [18.0, 18.1, 18.2, 18.1, 18.3, 18.2, 18.2, 18.1, 18.0, 18.2]
    for m, t in zip([44, 45, 45, 46, 47, 45, 44, 45, 46, 45], temps):
        state = p.add(_l(m, t))
    r = p.result()
    assert state == "done" and r["state"] == "done" and r["n"] == 10
    assert r["median_pct"] == 45.0 and r["spread_pct"] == 3.0 and r["steady"] and r["probe_pct"] == 45.0
    # temperatures: median of the ten = 18.15, spread 0.3 <= 0.5 -> steady
    assert r["temp_c"] == pytest.approx(18.15) and r["temp_spread_c"] == pytest.approx(0.3) and r["temp_steady"]
    assert not r["off_scale"]


def test_not_steady_means_test_again_and_no_number():
    r = settle.summarise([_l(m) for m in (40, 44, 41, 45, 40, 43, 44, 41, 42, 40)], 3, 0.5, [0, 100])
    assert r["state"] == "test_again" and r["spread_pct"] == 5.0 and not r["steady"] and r["probe_pct"] is None


def test_a_median_of_100_is_off_the_scale_never_a_value():
    r = settle.summarise([_l(100)] * 10, 3, 0.5, [0, 100])
    assert r["steady"] and r["off_scale"] and r["probe_pct"] is None and r["median_pct"] == 100.0


def test_check_wiring_gives_no_temperature_and_keeps_the_moisture():
    r = settle.summarise([_l(45, None)] * 6 + [_l(45, 18.0)] * 4, 3, 0.5, [0, 100])
    assert r["state"] == "done" and r["probe_pct"] == 45.0 and r["temp_n"] == 4 and r["wiring_lost"] == 6
    r = settle.summarise([_l(45, None)] * 10, 3, 0.5, [0, 100])
    assert r["temp_c"] is None and r["temp_steady"] is None and r["probe_pct"] == 45.0


def test_an_unsteady_temperature_is_null_but_the_moisture_counts():
    r = settle.summarise([_l(45, t) for t in (18.0, 18.9) * 5], 3, 0.5, [0, 100])
    assert r["temp_c"] is None and r["temp_steady"] is False and r["temp_spread_c"] == pytest.approx(0.9)
    assert r["state"] == "done" and r["probe_pct"] == 45.0


# ---------- the fake probe's test cases (fix 5) ----------

def _run(scenario, **kw):
    p = settle.Part.from_rules(RULES)
    for line in fake_probe.lines(n=30, seed=3, scenario=scenario, **kw):
        p.add(probe.parse_line(line))
    return p.result()


def test_fake_settling_ramp_settles_within_the_discarded_lines():
    lines = list(fake_probe.lines(n=30, seed=3, scenario="settling", target=45))
    first = [probe.parse_line(l)["moisture_pct"] for l in lines[:10]]
    assert max(first) - min(first) > 20                                  # the first 20 s are far from steady
    r = _run("settling", target=45)
    assert r["state"] == "done" and r["steady"] and abs(r["probe_pct"] - 45) <= 1 and r["temp_steady"]


def test_fake_jumpy_readings_ask_to_test_again():
    r = _run("jumpy", target=45)
    assert r["state"] == "test_again" and r["probe_pct"] is None


def test_fake_stuck_at_100_is_off_the_scale():
    r = _run("stuck100")
    assert r["off_scale"] and r["probe_pct"] is None


def test_fake_wiring_lost_keeps_the_moisture():
    lines = list(fake_probe.lines(n=30, seed=3, scenario="wiring_lost", target=45))
    assert all("Check wiring" in l for l in lines[5:])
    r = _run("wiring_lost", target=45)
    assert r["state"] == "done" and r["temp_c"] is None and abs(r["probe_pct"] - 45) <= 1


def test_every_scenario_prints_the_exact_format():
    for sc in ("wander", "settling", "jumpy", "stuck100", "wiring_lost"):
        for line in fake_probe.lines(n=40, seed=1, scenario=sc):
            probe.parse_line(line)
