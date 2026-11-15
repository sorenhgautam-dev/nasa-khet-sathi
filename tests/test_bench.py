"""Owner's probe brief, 2026-11-14, fix 3: the bench test is the proof (robot/bench.py, scripts/run_probe_bench.py;
rules.yaml probe.bench). Four proofs: steady (VALIDATION 5.2, and R for the Kalman), in order (5.3), accurate scored
leave-one-cup-out (5.1), and the ice-water temperature. Fixtures only: no real bench data exists yet, so
config/probe_calibration.yaml is never written here except into a temporary folder."""
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
import yaml

from pipeline.fetch.rules import load_rules
from robot import bench, fake_probe
from scripts import run_probe_bench as rpb

RULES = load_rules()["probe"]


# ---------- the pieces, hand-worked ----------

def test_line_and_leave_one_cup_out_hand_worked():
    # x 10 20 30 40, y 0 12 18 30: Sxy 480, Sxx 500 -> b 0.96, a -9; residuals -0.6, 1.8, -1.8, 0.6
    # leave out 10: b 0.9, a -7 -> 2 (err 2); 20: b 0.985714, a -10.2857 -> 9.4286 (2.5714); 30: a -9.0 -> 20.5714
    # (2.5714); 40: b 0.9, a -8 -> 28 (2). MAE = 9.142857 / 4 = 2.285714
    x, y = [10.0, 20.0, 30.0, 40.0], [0.0, 12.0, 18.0, 30.0]
    f = bench.fit_poly(x, y, 1)
    assert f["coef"] == pytest.approx([-9.0, 0.96]) and f["residuals"] == pytest.approx([-0.6, 1.8, -1.8, 0.6])
    assert bench.loo_mae(x, y, 1) == pytest.approx(2.285714, abs=1e-6)


def test_a_curve_only_with_five_cups_and_a_clear_gain():
    x4, y4 = [10.0, 20.0, 30.0, 40.0], [3.0, 8.0, 17.0, 30.0]                 # curved, but only 4 cups: a line
    assert bench.choose_fit(x4, y4, RULES["bench"])["model"] == "line"
    x = np.arange(10.0, 70.0, 10.0)
    y = 2 + 0.1 * x + 0.01 * x ** 2                                            # an exact curve, 6 cups
    f = bench.choose_fit(list(x), list(y), RULES["bench"])
    assert f["model"] == "quadratic" and f["loo_mae"] == pytest.approx(0.0, abs=1e-9)
    assert f["line"]["loo_mae"] >= 1.0 and len(f["line"]["residuals"]) == 6        # the line's residuals reported too


def test_pooled_r_hand_worked():
    # cup A 44 45 46 (mean 45, squares 1 + 0 + 1 = 2), cup B 60 60 63 (mean 61, 1 + 1 + 4 = 6): (2 + 6) / (2 + 2) = 2.0
    assert bench.pooled_r({"A": [44, 45, 46], "B": [60, 60, 63]})["r_probe_pct2"] == pytest.approx(2.0)
    assert bench.pooled_r({"A": [45, 45, 45]})["r_probe_pct2"] == pytest.approx(1 / 12)       # the rounding floor


def test_settling_time_hand_worked():
    # lines every 2 s: 0 10 30 40 44 45 45 46 44 45; median 45, band 3: from the 5th line (44, at 8 s) on all within 3
    t = [2.0 * i for i in range(10)]
    assert bench.settling_time_s(t, [0, 10, 30, 40, 44, 45, 45, 46, 44, 45], 45.0, 3) == 8.0


def test_cups_left_out_by_the_rule_written_before_fitting():
    # 300 g in 250 ml: bulk density 1.2, pore space 1 - 1.2 / 2.65 = 0.5472; 125 g of water is 0.50 (kept), 140 g 0.56 (out)
    ok = {"cup_id": "c6", "cup_volume_ml": 250, "dry_soil_g": 300, "water_added_g": 125, "notes": ""}
    assert bench.exclusion_reasons(ok, value=60.0, steady_push_ins=3) == []
    assert any("pore space" in r for r in bench.exclusion_reasons({**ok, "water_added_g": 140}, 60.0, 3))
    assert any("notes" in r for r in bench.exclusion_reasons({**ok, "notes": "water pooled on top"}, 60.0, 3))
    assert any("off the scale" in r for r in bench.exclusion_reasons(ok, 100.0, 3))
    assert any("steady" in r for r in bench.exclusion_reasons(ok, None, 0))


def test_order_hand_worked():
    assert bench.order_check([0, 10, 20, 30], [12, 25, 37, 48]) == {"passes": True, "spearman": 1.0}
    # ranks 1 3 2 4: sum d^2 = 2 -> rho = 1 - 6 x 2 / (4 x 15) = 0.8; not strictly increasing
    assert bench.order_check([0, 10, 20, 30], [12, 25, 24, 48]) == {"passes": False, "spearman": pytest.approx(0.8)}


def test_ice_water_within_half_a_degree():
    assert bench.ice_check([0.3, 0.2, 0.4], RULES["bench"]["ice_c"])["passes"]
    assert not bench.ice_check([0.8, 0.9, 0.7], RULES["bench"]["ice_c"])["passes"]
    assert bench.ice_check([], RULES["bench"]["ice_c"])["passes"] is None


# ---------- the whole bench from a fixture (the fake probe's settling ramp) ----------

CUPS = [{"cup_id": f"c{i + 1}", "cup_volume_ml": 250, "dry_soil_g": 300, "water_added_g": 25 * i, "notes": ""} for i in range(6)]


class Tick:
    """A clock 2 s a line, as the probe prints."""
    def __init__(self):
        self.t = datetime.fromisoformat("2026-11-15T09:00:00+05:45")

    def __call__(self):
        self.t += timedelta(seconds=2)
        return self.t.isoformat()


def _fixture(source):
    recs, seed, tick = [], 0, Tick()
    for cup in CUPS:
        target = 8 + 1.2 * cup["water_added_g"] / 2.5                      # probe 8, 20, 32, 44, 56, 68 for 0-50 % water
        for k in (1, 2, 3):
            seed += 1
            recs.append(bench.record_pushin(fake_probe.lines(n=30, seed=seed, scenario="settling", target=target),
                                            cup["cup_id"], k, source, RULES, clock=tick))
    for k in (1, 2, 3):
        recs.append(bench.record_pushin(fake_probe.lines(n=30, seed=50 + k, scenario="settling", target=95, soil_temp=0.2,
                                                         start_temp=20.0), "ice", k, source, RULES, clock=tick))
    return recs


def test_the_bench_gives_all_four_proofs_from_a_fixture():
    b = bench.analyse(_fixture("fake_probe"), CUPS, RULES)
    assert b["made_up"] is True and b["cups_used"] == 6
    assert b["steady"]["passes"] and b["steady"]["r_probe_pct2"] > 0                       # 5.2
    assert b["order"]["passes"] and b["order"]["spearman"] == 1.0                          # 5.3
    assert b["accurate"]["model"] == "line" and b["accurate"]["loo_mae_water_pct"] < 1.0    # 5.1 (an almost exact fixture)
    assert b["accurate"]["coef"][1] == pytest.approx(1 / 1.2, abs=0.03)                     # about 0.83 water-% per probe %
    assert b["temperature"]["passes"]                                                      # ice ~0.2 C
    assert b["settling"]["n"] == 21 and b["settling"]["max_s"] <= 40
    assert bench.calibration_doc(b) is None                                                # made-up: never a calibration


def test_a_real_bench_writes_the_calibration_it_says_where_from(tmp_path):
    log = tmp_path / "readings_2026-11-15.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in _fixture("serial:/dev/cu.usbserial-0001")))
    cups = tmp_path / "cups.csv"
    cups.write_text("cup_id,cup_volume_ml,dry_soil_g,water_added_g,notes\n"
                    + "".join(f"{c['cup_id']},{c['cup_volume_ml']},{c['dry_soil_g']},{c['water_added_g']},\n" for c in CUPS))
    out, cal_out = tmp_path / "bench.json", tmp_path / "probe_calibration.yaml"
    assert rpb.main(["--log", str(log), "--cups", str(cups), "--out", str(out), "--calibration-out", str(cal_out)]) == 0
    b = json.loads(out.read_text())
    assert not b["made_up"] and set(b["proofs"]) == {"steady", "order", "accurate", "temperature"}
    c = yaml.safe_load(cal_out.read_text())
    assert c["made_from"] == "the bench test of 2026-11-15, not field-tested" and c["cups"] == 6
    assert c["fit"]["model"] == "line" and c["mae_water_pct"] < 1.0 and c["r_probe_pct2"] > 0


def test_a_made_up_bench_never_writes_the_calibration(tmp_path):
    log = tmp_path / "readings_2026-11-15.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in _fixture("fake_probe")))
    cups = tmp_path / "cups.csv"
    cups.write_text("cup_id,cup_volume_ml,dry_soil_g,water_added_g,notes\n"
                    + "".join(f"{c['cup_id']},{c['cup_volume_ml']},{c['dry_soil_g']},{c['water_added_g']},\n" for c in CUPS))
    out, cal_out = tmp_path / "bench_rehearsal.json", tmp_path / "probe_calibration.yaml"
    assert rpb.main(["--log", str(log), "--cups", str(cups), "--out", str(out), "--calibration-out", str(cal_out)]) == 0
    assert json.loads(out.read_text())["made_up"] and not cal_out.exists()
    with pytest.raises(SystemExit):                               # and never into data/checks/probe/bench.json
        rpb.main(["--log", str(log), "--cups", str(cups), "--calibration-out", str(cal_out)])


def test_a_voided_push_in_leaves_the_proofs_and_its_redo_takes_its_place():
    recs = _fixture("serial:/dev/cu.usbserial-0001")
    bad = next(r for r in recs if r.get("cup") == "c2" and r["push_in"] == 3)
    wrong = {**bad, "result": {**bad["result"], "median_pct": 90.0}}                  # taken in the wrong cup
    recs[recs.index(bad)] = wrong
    void = {"kind": "void", "cup": "c2", "push_in": 3, "why": "wrong cup", "time": "2026-11-15T10:00:00+05:45"}
    redo = {**bad, "time": "2026-11-15T10:01:00+05:45"}                               # recorded after the void
    b = bench.analyse([*recs, void, redo], CUPS, RULES)
    assert b["voided"] == [{"cup": "c2", "push_in": 3, "median_pct": 90.0, "why": "wrong cup"}]
    c2 = next(r for r in b["cups"] if r["cup_id"] == "c2")
    assert c2["push_ins"] == 3 and 90.0 not in c2["push_in_medians_pct"] and b["order"]["passes"]


# ---------- the spoon method: a rough calibration without a scale (owner, 2026-11-15; rules.yaml probe.bench.spoon) ----------

SPOONS = [{"cup_id": f"c{i + 1}", "cup_spoons": 40, "water_spoons": 4 * i, "printed_volume_ml": 250 if i == 0 else "",
           "notes": ""} for i in range(4)]                                    # 0, 10, 20, 30 % of N = 40


def _spoon_fixture(source, probe_at, order=(0, 1, 2, 3)):
    recs, seed, tick = [], 100, Tick()
    for i in order:
        for k in (1, 2, 3):
            seed += 1
            recs.append(bench.record_pushin(fake_probe.lines(n=30, seed=seed, scenario="settling", target=probe_at[i]),
                                            SPOONS[i]["cup_id"], k, source, RULES, clock=tick))
    return recs


def _spoon_sheet(tmp_path):
    p = tmp_path / "cups.csv"
    p.write_text("cup_id,cup_spoons,water_spoons,printed_volume_ml,notes\n"
                 + "".join(f"{c['cup_id']},{c['cup_spoons']},{c['water_spoons']},{c['printed_volume_ml']},\n" for c in SPOONS))
    return p


def test_spoon_reference_is_spoons_over_spoons_and_needs_no_scale():
    # 8 of 40 spoonfuls: 0.20 m3/m3, 20 water-%; printed 250 ml / 40 = 6.25 ml a spoon (a cross-check, never used)
    c = {"cup_id": "c3", "cup_spoons": 40, "water_spoons": 8, "printed_volume_ml": 250, "notes": ""}
    assert bench.reference_water_pct(c) == pytest.approx(20.0) and bench.spoon_ml(c) == pytest.approx(6.25)
    assert bench.spoon_ml({**c, "printed_volume_ml": ""}) is None
    assert bench.exclusion_reasons(c, value=30.0, steady_push_ins=3) == []           # no pore-space test without a mass
    assert any("notes" in r for r in bench.exclusion_reasons({**c, "notes": "would not pack to the line"}, 30.0, 3))


def test_loo_rmse_hand_worked():
    # the leave-one-out errors of test_line_and_leave_one_cup_out_hand_worked: 2, 2.5714, 2.5714, 2 -> RMSE
    # sqrt((4 + 6.612245 + 6.612245 + 4) / 4) = sqrt(5.306122) = 2.303502
    errs = bench.loo_errors([10.0, 20.0, 30.0, 40.0], [0.0, 12.0, 18.0, 30.0], 1)
    assert np.abs(errs) == pytest.approx([2.0, 2.571429, 2.571429, 2.0], abs=1e-6)
    assert float(np.sqrt(np.mean(np.square(errs)))) == pytest.approx(2.303502, abs=1e-6)


def test_a_spoon_bench_within_smaps_yardstick_writes_a_rough_calibration(tmp_path):
    log = tmp_path / "readings_2026-11-15.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in _spoon_fixture("serial:/dev/cu.usbserial-0001", [8, 20, 32, 44])))
    out, cal_out = tmp_path / "bench.json", tmp_path / "probe_calibration.yaml"
    assert rpb.main(["--log", str(log), "--cups", str(_spoon_sheet(tmp_path)), "--out", str(out),
                     "--calibration-out", str(cal_out)]) == 0
    b = json.loads(out.read_text())
    s = b["spoon"]
    assert b["label"].startswith("rough calibration (spoon measures, air-dried soil)") and b["cups_used"] == 4
    assert [r["water_pct"] for r in b["cups"]] == pytest.approx([0, 10, 20, 30]) and b["cups"][0]["spoon_ml"] == 6.25
    assert s["yardstick_m3m3"] == 0.04 and s["loo_rmse_m3m3"] <= 0.04 and s["passes"] is True and s["driest_first"] is True
    assert "few percent above zero" in s["dry_point"]
    c = yaml.safe_load(cal_out.read_text())
    assert c["label"] == "rough calibration (spoon measures, air-dried soil)" and "bench test" in c["made_from"]
    assert c["fit_var_water_pct2"] == pytest.approx(s["loo_rmse_m3m3"] ** 2 * 1e4, abs=1e-3) and c["cups"] == 4
    from robot.calibrate import load_calibration
    assert load_calibration(cal_out)["label"] == c["label"]


def test_a_spoon_bench_outside_the_yardstick_writes_no_calibration_and_the_fog_stays(tmp_path):
    log = tmp_path / "readings_2026-11-15.jsonl"                               # in order, but far from a line
    log.write_text("".join(json.dumps(r) + "\n" for r in _spoon_fixture("serial:/dev/cu.usbserial-0001", [8, 40, 44, 80],
                                                                         order=(3, 2, 1, 0))))
    out, cal_out = tmp_path / "bench.json", tmp_path / "probe_calibration.yaml"
    assert rpb.main(["--log", str(log), "--cups", str(_spoon_sheet(tmp_path)), "--out", str(out),
                     "--calibration-out", str(cal_out)]) == 0
    s = json.loads(out.read_text())["spoon"]
    assert s["loo_rmse_m3m3"] > 0.04 and s["passes"] is False and not cal_out.exists()
    assert s["driest_first"] is False                                          # reported, not a pass or fail
