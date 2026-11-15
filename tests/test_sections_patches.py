"""pipeline/sections/grid.patches: a drawn field's 10 m patches by the Dhulikhel package's method (owner, 2026-11-15):
a 10 m grid through the field's centre, each cell clipped to the outline, pieces under 50 m2 joined to the nearest
patch, numbered from the south-west, row by row, west to east."""
import json
import math
import zipfile
from pathlib import Path

import pytest
import yaml

from pipeline.sections import grid

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "design" / "dhulikhel_farm_package.zip"


def _box(lon0, lat0, half_x_m, half_y_m):
    mx, my = grid.M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0)), grid.M_PER_DEG_LAT
    return [[lon0 + sx * half_x_m / mx, lat0 + sy * half_y_m / my] for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def test_a_worked_rectangle():
    """26 m x 20 m around the centre: columns cut at -13, -10, 0, 10, 13 m, rows at -10, 0, 10 m. The 3 m x 10 m edge
    pieces (30 m2) join the 100 m2 cell beside them: four patches of 130 m2, each centred 6.5 m from the middle line
    ((100 x 5 + 30 x 11.5) / 130 = 6.5) and 5 m from the other. Lines: 2 north-south at x = 0, 4 east-west at y = 0."""
    lon0, lat0 = 85.5, 27.6
    ps, lines = grid.patches(_box(lon0, lat0, 13, 10), (lon0, lat0))
    mx, my = grid.M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0)), grid.M_PER_DEG_LAT
    assert [p["id"] for p in ps] == ["p1", "p2", "p3", "p4"]
    assert [(p["row"], p["col"]) for p in ps] == [(-1, -1), (-1, 0), (0, -1), (0, 0)]       # south-west first
    assert [p["area_m2"] for p in ps] == [130.0] * 4
    xy = [((p["centre"][0] - lon0) * mx, (p["centre"][1] - lat0) * my) for p in ps]
    assert xy == [pytest.approx(v, abs=0.01) for v in [(-6.5, -5), (6.5, -5), (-6.5, 5), (6.5, 5)]]
    assert all(len(p["pieces"]) == 2 for p in ps) and len(lines) == 6


def _package():
    with zipfile.ZipFile(PACKAGE) as z:
        return json.loads(z.read("farm_coordinates.json"))


def test_dhulikhel_against_the_package():
    """Our patches against the teammate's (farm_coordinates.json). Eleven match within 1 m and 12 m2. The south-west
    corner differs, by the rule itself, not by tuning: cut exactly from the outline, the piece under p4's cell is 54.3 m2
    (50 or more: its own patch, our p2) and the west piece of the next row is 48.7 m2 (under 50: joined to our p3); the
    package (areas by pixel count) kept the west piece as its p2 and joined the other to its p4."""
    pkg = _package()
    cfg = yaml.safe_load((REPO / "config" / "fields" / "dhulikhel.yaml").read_text())
    assert cfg["polygon"] == pkg["field_outline_lonlat"]
    assert (cfg["lon"], cfg["lat"]) == (pkg["field_centre"]["lon"], pkg["field_centre"]["lat"])
    ps, lines = grid.patches(cfg["polygon"], (cfg["lon"], cfg["lat"]), cfg["patches"]["cell_m"], cfg["patches"]["min_piece_m2"])
    assert [p["id"] for p in ps] == [f"p{k}" for k in range(1, 15)]
    assert sum(p["area_m2"] for p in ps) == pytest.approx(grid.area_m2(cfg["polygon"]), abs=0.5)
    assert all(p["area_m2"] >= 50 for p in ps) and [p["row"] for p in ps] == sorted(p["row"] for p in ps)
    mx, my = grid._scale(cfg["polygon"])
    by_id = {q["id"]: q for q in pkg["patches"]}
    for p in ps:
        q = by_id[p["id"]]
        d = math.hypot((p["centre"][0] - q["lon"]) * mx, (p["centre"][1] - q["lat"]) * my)
        if p["id"] in ("p2", "p3", "p4"):
            continue
        assert d < 1.0 and abs(p["area_m2"] - q["area_m2"]) < 12, p["id"]
    ours = {p["id"]: p for p in ps}
    assert ours["p2"]["row"] == -2 and ours["p2"]["area_m2"] == 54.3                 # its own patch: 54.3 >= 50
    assert ours["p3"]["area_m2"] == pytest.approx(100 + 48.7, abs=0.1)               # the 48.7 m2 west piece joined in
    assert by_id["p2"]["lon"] < by_id["p3"]["lon"] and by_id["p4"]["area_m2"] == 150  # the package's other call
    assert len(lines) == 27


def test_the_drone_file_is_up_to_date_and_the_probe_walk_takes_p1_to_p14(tmp_path):
    """site/data/drone/dhulikhel.json is what pipeline/export/build_drone.py makes now; the bridge reads its parts from it
    before the field is built (robot/bridge.field_section_ids), so a walk over p1..p14 is accepted."""
    from pipeline.export import build_drone
    from pipeline.fetch.fields import load_field
    from robot import bridge
    doc, picture = build_drone.build(load_field("dhulikhel"))
    assert json.loads((REPO / "site" / "data" / "drone" / "dhulikhel.json").read_text()) == json.loads(json.dumps(doc))
    assert (REPO / "site" / "data" / "drone" / "dhulikhel.jpg").read_bytes() == picture
    assert [r["id"] for r in doc["package_check"]["differ"]] == ["p2", "p3", "p4"] and doc["credit"].endswith("OpenAerialMap, CC-BY 4.0")
    (tmp_path / "site" / "data" / "drone").mkdir(parents=True)
    (tmp_path / "site" / "data" / "drone" / "dhulikhel.json").write_text(json.dumps(doc))
    ids, where = bridge.field_section_ids("dhulikhel", repo=tmp_path)
    assert ids == [f"p{k}" for k in range(1, 15)] and where.endswith("dhulikhel.json")
    assert all(bridge.SECTION.match(i) for i in ids) and not bridge.SECTION.match("q1")
    assert set(bridge.where_words(doc["patches"])) == set(ids)


def test_the_index_lists_a_drone_preview_until_its_field_is_built(tmp_path):
    from pipeline.export.build_index import build_index
    from pipeline.fetch.fields import load_field
    cfgs = [load_field("demo"), load_field("dhulikhel")]
    (tmp_path / "fields").mkdir()
    (tmp_path / "drone").mkdir()
    (tmp_path / "fields" / "demo.json").write_text("{}")
    (tmp_path / "drone" / "dhulikhel.json").write_text("{}")
    idx = build_index(cfgs, tmp_path)
    assert [f["id"] for f in idx["fields"]] == ["demo"] and idx["drone_previews"] == ["data/drone/dhulikhel.json"]
    (tmp_path / "fields" / "dhulikhel.json").write_text("{}")
    idx = build_index(cfgs, tmp_path)
    assert "drone_previews" not in idx and idx["fields"][1]["drone"] == "data/drone/dhulikhel.json"
