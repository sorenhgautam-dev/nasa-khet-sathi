"""Global use (owner, 2026-11-15; config/rules.yaml global_use): the world outline, each NASA dataset's coverage from its
own documentation, land or sea, and the nearest prepared field. Worked numbers first."""
import json
import math
from pathlib import Path

import pytest

from pipeline.export import build_world as bw

REPO = Path(__file__).resolve().parents[1]
COV = bw.rules()["coverage"]["value"]


def test_web_mercator_worked_numbers():
    assert bw.project(0, 0) == pytest.approx((500, 500))
    assert bw.project(-180, 0)[0] == pytest.approx(0) and bw.project(180, 0)[0] == pytest.approx(1000)
    # 45 N: (1 - ln(tan(67.5 deg)) / pi) / 2 x 1000 = (1 - 0.881374 / pi) / 2 x 1000 = 359.73
    assert bw.project(0, 45)[1] == pytest.approx(359.73, abs=0.01)


def test_haversine_is_a_quarter_circle_from_the_equator_to_the_pole():
    assert bw.haversine_km(0, 0, 90, 0) == pytest.approx(6371 * math.pi / 2, rel=1e-9)


def test_even_odd_rule_with_a_hole():
    square, hole = [0, 0, 10, 0, 10, 10, 0, 10], [3, 3, 7, 3, 7, 7, 3, 7]
    assert bw.inside(5, 5, [square]) and not bw.inside(15, 5, [square])
    assert not bw.inside(5, 5, [square, hole]) and bw.inside(1, 1, [square, hole])


def test_simplify_rounds_to_half_units_and_drops_repeats():
    assert bw.simplify([(0.1, 0.1), (0.2, 0.2), (10.26, 0), (10.24, 9.9), (0, 10)]) == [0, 0, 10.5, 0, 10, 10, 0, 10]
    assert bw.simplify([(0, 0), (0.1, 0.1), (0.2, 0)]) is None   # under 3 points left


def test_coverage_follows_each_datasets_documented_limits():
    north = bw.coverage(65.0, True, COV)          # mainland Nunavut: above NASADEM's 60 N, IMERG with its caution
    assert north == {"gpm_imerg": "caution", "power": "yes", "hls": "yes", "nasadem": "no", "nexgddp": "yes"}
    assert bw.coverage(27.69, True, COV) == {k: "yes" for k in COV}
    antarctica = bw.coverage(-70, True, COV)
    assert antarctica["hls"] == antarctica["nasadem"] == antarctica["nexgddp"] == "no" and antarctica["power"] == "yes"
    sea = bw.coverage(0, False, COV)              # land-only products do not cover the sea
    assert sea["hls"] == sea["nasadem"] == "no" and sea["gpm_imerg"] == sea["power"] == sea["nexgddp"] == "yes"


def test_the_shipped_world_file():
    w = json.loads((REPO / "site" / "data" / "world.json").read_text(encoding="utf-8"))
    assert set(w) == {"about", "outline", "coverage", "crops", "not_modelled"}
    rings = w["outline"]["rings"]
    for name, (lat, lon) in bw.rules()["examples"]["value"].items():
        assert bw.inside(*bw.project(lon, lat), rings), f"{name} should be land on our map"
    assert not bw.inside(*bw.project(-30, 0), rings)            # the middle of the Atlantic
    assert [c["id"] for c in w["coverage"]] == list(COV)
    assert w["crops"] == list(json.loads((REPO / "config" / "crops.json").read_text())["crops"])
    assert (REPO / "site" / "data" / "world.json").stat().st_size < 60_000   # small: the page loads it on a phone


def test_the_nearest_prepared_field_for_each_example():
    fields = json.loads((REPO / "site" / "data" / "index.json").read_text())["fields"]
    ex = bw.rules()["examples"]["value"]
    near = {k: bw.nearest(lat, lon, fields) for k, (lat, lon) in ex.items()}
    assert near["nepal"][0] == "demo" and near["nepal"][1] < 1
    assert near["madagascar"][0] == "ambohidratrimo" and near["madagascar"][1] < 1
    assert near["us_midwest"][0] in {"demo", "ambohidratrimo", "kharipati", "sample-1", "sample-2", "sample-3", "sample-4"}
    assert near["northern_canada"][1] > 5000
