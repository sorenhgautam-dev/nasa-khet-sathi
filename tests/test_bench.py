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
