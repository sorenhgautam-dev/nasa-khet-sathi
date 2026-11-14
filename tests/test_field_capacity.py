"""The field's own field capacity from the team's tins (owner's item 4; notes/FIELD_CAPACITY_PROTOCOL.md; rules.yaml
field_capacity_measured, off until the data arrive). Worked numbers by hand below."""
import pandas as pd
import pytest

from pipeline.fetch import field_visit as fv
from pipeline.plans import twin_options as to
from pipeline.twin import field_capacity as fcap
from pipeline.twin import soil_water as sw

COLS = "part,depth_cm,tin,tin_empty_g,tin_volume_ml,wet_with_tin_g,dry_with_tin_g,dried_how,notes"


def test_one_tin():
    """Tin 50 g empty, 250 ml; 450 g wet, 370 g dry: water 80 g = 80 ml -> 80 / 250 = 0.32 m3/m3; dry soil 320 g ->
    bulk density 320 / 250 = 1.28 g/cm3 (pore space 1 - 1.28 / 2.65 = 0.517, so 0.32 fits)."""
    t = fcap.tin_values(pd.DataFrame([{"part": "s1", "depth_cm": "0-15", "tin": "A", "tin_empty_g": 50, "tin_volume_ml": 250,
                                       "wet_with_tin_g": 450, "dry_with_tin_g": 370, "dried_how": "oven", "notes": ""}]))
    assert t["theta_fc_m3m3"].iloc[0] == pytest.approx(0.32) and t["bulk_density_g_cm3"].iloc[0] == pytest.approx(1.28)


@pytest.mark.parametrize("wet, dry, why", [(360, 370, "lighter wet than dry"), (450, 40, "below the empty tin"),
                                          (560, 370, "more water than pore space")])
def test_impossible_tins_stop_the_run(wet, dry, why):
    rows = pd.DataFrame([{"part": "s1", "depth_cm": "0-15", "tin": "A", "tin_empty_g": 50, "tin_volume_ml": 250,
                          "wet_with_tin_g": wet, "dry_with_tin_g": dry, "dried_how": "oven", "notes": why}])
    with pytest.raises(ValueError):
        fcap.tin_values(rows)


def _tins(values):
    rows = []
    for depth, thetas in values.items():
        for i, th in enumerate(thetas):           # 250-ml tins, 50 g empty, 320 g dry soil: water = th x 250 g
            rows.append({"part": f"s{i % 4 + 1}", "depth_cm": depth, "tin": f"{depth}-{i}", "tin_empty_g": 50.0,
                         "tin_volume_ml": 250.0, "wet_with_tin_g": 370.0 + th * 250.0, "dry_with_tin_g": 370.0,
                         "dried_how": "oven", "notes": ""})
    return pd.DataFrame(rows)


def test_median_per_depth_and_the_root_zone_value():
    """0-15 cm: 0.30, 0.31, 0.32, 0.34 -> median 0.315; 15-30 cm: 0.28, 0.29, 0.30 -> 0.29.
    Root zone 0-30 cm, depth-weighted: (0.315 x 15 + 0.29 x 15) / 30 = 0.3025; for a 0.5 m root zone only 0.30 m is measured."""
    med = fcap.depth_medians(fcap.tin_values(_tins({"0-15": [0.30, 0.32, 0.34, 0.31], "15-30": [0.28, 0.30, 0.29]})))
    assert med.set_index("depth_cm")["theta_fc_m3m3"].to_dict() == pytest.approx({"0-15": 0.315, "15-30": 0.29})
    assert med.set_index("depth_cm")["n_tins"].to_dict() == {"0-15": 4, "15-30": 3}
    rz = fcap.root_zone_fc(med, 0.5)
    assert rz["theta_fc_m3m3"] == pytest.approx(0.3025) and rz["measured_depth_m"] == pytest.approx(0.30)


SOIL = pd.DataFrame({"top_cm": [0, 5, 15, 30], "bottom_cm": [5, 15, 30, 60], "theta_fc_m3m3": [0.333, 0.331, 0.326, 0.322],
                     "theta_wp_m3m3": [0.148, 0.152, 0.159, 0.173]})


def test_the_soil_table_takes_the_measured_field_capacity_and_keeps_the_maps_wilting_point():
    """Measured 0-20 cm only (0.30): layers 0-5 and 5-15 -> 0.30; layer 15-30 is half measured -> (0.30 x 5 + 0.326 x 10)
    / 15 = 0.31733; 30-60 keeps the map's 0.322. Wilting points unchanged. Rice TAW over 0.5 m:
    1000 x [(0.30-0.148) x 0.05 + (0.30-0.152) x 0.10 + (0.317333-0.159) x 0.15 + (0.322-0.173) x 0.20] = 7.6 + 14.8 + 23.75 + 29.8 = 75.95 mm."""
    med = pd.DataFrame({"depth_cm": ["0-20"], "top_cm": [0], "bottom_cm": [20], "theta_fc_m3m3": [0.30], "n_tins": [12]})
    s2 = fcap.soil_with_measured_fc(SOIL, med)
    assert s2["theta_fc_m3m3"].tolist() == pytest.approx([0.30, 0.30, 0.317333, 0.322], abs=1e-6)
    assert s2["theta_wp_m3m3"].tolist() == SOIL["theta_wp_m3m3"].tolist()
    assert sw.taw_from_layers(s2, 0.5) == pytest.approx(75.95, abs=1e-3)


def test_a_measured_field_capacity_below_the_maps_wilting_point_stops_the_run():
    med = pd.DataFrame({"depth_cm": ["0-15"], "top_cm": [0], "bottom_cm": [15], "theta_fc_m3m3": [0.14], "n_tins": [3]})
    with pytest.raises(ValueError):
        fcap.soil_with_measured_fc(SOIL, med)


def test_no_file_no_measured_version(tmp_path):
    assert fv.load_field_capacity("demo", tmp_path) is None
    rules = {"field_capacity_measured": {"apply": True}}
    assert to.soil_versions(rules, SOIL, None) == {"map": SOIL}


def test_the_file_gives_both_versions_when_the_switch_is_on(tmp_path):
    d = tmp_path / "field_visit" / "demo"
    d.mkdir(parents=True)
    _tins({"0-15": [0.30, 0.32, 0.34, 0.31], "15-30": [0.28, 0.30, 0.29]}).to_csv(d / "field_capacity.csv", index=False)
    assert open(d / "field_capacity.csv").readline().strip() == COLS
    med = fv.load_field_capacity("demo", tmp_path)
    assert (tmp_path / "cards" / "demo" / "field_capacity.json").exists()
    on = to.soil_versions({"field_capacity_measured": {"apply": True}}, SOIL, med)
    off = to.soil_versions({"field_capacity_measured": {"apply": False}}, SOIL, med)
    assert set(on) == {"map", "measured"} and set(off) == {"map"}
    assert on["measured"]["theta_fc_m3m3"].tolist()[:3] == pytest.approx([0.315, 0.315, 0.29])
