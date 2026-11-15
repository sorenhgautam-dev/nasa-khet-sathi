"""pipeline/sections/grid.py (CLAUDE.md "Sections"; build step 8): split the field's outline into sections that tile it.

A four-corner field is split by its own corners (any orientation); any other outline by bounding-box cells clipped to
it. Step 8 uses rules.yaml sections.cell_m (30 m, about one HLS pixel): the 60 m demo square gives 2 x 2. The default
10 m is the step-1 grid that pipeline/export/build_field_json.py still draws (36 grey squares) until the integrator
switches the export to the real sections."""
import math

import pytest

from pipeline.fetch.rules import load_rules
from pipeline.sections import grid

DEMO = [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]   # 60 m square


def _size_m(poly):
    lons, lats = [p[0] for p in poly], [p[1] for p in poly]
    return ((max(lons) - min(lons)) * 111320.0 * math.cos(math.radians(lats[0])), (max(lats) - min(lats)) * 110574.0)


def test_shoelace_and_area_worked_numbers():
    assert grid.shoelace([(0, 0), (2, 0), (2, 2), (0, 2)]) == 4.0
    # 0.001 x 0.001 deg at the equator: 111.32 m x 110.574 m = 12,309.098 m2
    assert grid.area_m2([[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001]]) == pytest.approx(12309.098, abs=0.01)
    # the demo square: 0.00061 deg x 111320 x cos(27.690767 deg) = 60.13 m wide, 0.00054 x 110574 = 59.71 m high
    assert grid.area_m2(DEMO) == pytest.approx(3590.2, abs=1.0)


def test_clip_to_rect_worked_numbers():
    sq = [(0, 0), (2, 0), (2, 2), (0, 2)]
    assert grid.shoelace(grid.clip_to_rect(sq, 1, 1, 3, 3)) == pytest.approx(1.0)
    tri = [(0, 0), (4, 0), (0, 4)]
    assert grid.shoelace(grid.clip_to_rect(tri, 0, 0, 2, 2)) == pytest.approx(4.0)      # the square lies under x + y = 4
    assert grid.shoelace(grid.clip_to_rect(tri, 1, 1, 3, 3)) == pytest.approx(2.0)      # (1,1) (3,1) (1,3)
    assert grid.clip_to_rect(sq, 5, 5, 6, 6) == []


def test_the_60_m_demo_square_at_30_m_gives_2_by_2_sections():
    cell = load_rules()["sections"]["cell_m"]
    assert cell == 30
    s = grid.grid_sections(DEMO, cell_m=cell)
    assert [x["id"] for x in s] == ["s1", "s2", "s3", "s4"]
    for x in s:
        w, h = _size_m(x["polygon"])
        assert 29.0 < w < 31.0 and 29.0 < h < 31.0 and len(x["polygon"]) == 4
        assert x["area_m2"] == pytest.approx(3590.2 / 4, abs=1.0)
    # row by row from the south-west corner: s1 SW, s2 SE, s3 NW, s4 NE
    assert s[0]["polygon"][0] == DEMO[0] and s[1]["polygon"][1] == DEMO[1]
    assert s[3]["polygon"][2] == DEMO[2] and s[2]["polygon"][3] == DEMO[3]


def test_a_10_m_cell_is_only_ever_asked_for_never_the_default():
    """Owner, 2026-11-15: the 10 m default gave the sample fields 36 parts; the default is the 30 m of rules.yaml now."""
    assert [x["id"] for x in grid.grid_sections(DEMO)] == ["s1", "s2", "s3", "s4"]
    s = grid.grid_sections(DEMO, cell_m=10.0)
    assert len(s) == 36 and [x["id"] for x in s] == [f"s{i}" for i in range(1, 37)]
    for x in s:
        w, h = _size_m(x["polygon"])
        assert 9.0 < w < 11.0 and 9.0 < h < 11.0


def _south_west_first(parts):
    """True when the parts are numbered from the south-west, row by row, west to east (centres, to 1 m)."""
    c = [(sum(p[0] for p in x["polygon"]) / len(x["polygon"]), sum(p[1] for p in x["polygon"]) / len(x["polygon"])) for x in parts]
    return c == sorted(c, key=lambda q: (round(q[1], 5), q[0]))


def test_sectioning_is_per_field_and_the_demo_and_sample_fields_have_exactly_4_parts():
    """Owner, 2026-11-15: sectioning is set in each field's config; the Bhaktapur demo field and the sample fields keep
    4 parts (2 x 2, each about one 30 m NASA pixel), numbered from the south-west; only a field with drone-photo
    `patches` (Dhulikhel) has 10 m patches. Checked on the configs and on the files the site reads."""
    import json
    from pathlib import Path
    from pipeline.export.build_index import all_configs
    rules, site = load_rules()["sections"], Path(__file__).resolve().parents[1] / "site" / "data" / "fields"
    seen = []
    for cfg in all_configs():
        if cfg.get("patches"):
            continue
        seen.append(cfg["id"])
        assert cfg["sections"] == {"cell_m": 30}, cfg["id"]
        parts = grid.field_sections(cfg, rules)
        assert [p["id"] for p in parts] == ["s1", "s2", "s3", "s4"] and _south_west_first(parts), cfg["id"]
        built = json.loads((site / f"{cfg['id']}.json").read_text())["field"]["sections"]
        assert [p["id"] for p in built] == ["s1", "s2", "s3", "s4"] and _south_west_first(built), cfg["id"]
        assert [p["polygon"] for p in built] == [p["polygon"] for p in parts], cfg["id"]
    assert "demo" in seen and {"sample-1", "sample-2", "sample-3", "sample-4"} <= set(seen)


def test_a_fields_own_cell_size_wins_over_the_rule():
    rules = load_rules()["sections"]
    field = {"polygon": DEMO}
    assert len(grid.field_sections(field, rules)) == 4                                     # rules.yaml: 30 m
    assert len(grid.field_sections({**field, "sections": {"cell_m": 20}}, rules)) == 9     # the field's config: 3 x 3


@pytest.mark.parametrize("cell", [10.0, 30.0])
def test_the_sections_tile_the_whole_field_and_nothing_else(cell):
    s = grid.grid_sections(DEMO, cell_m=cell)
    lons = [p[0] for x in s for p in x["polygon"]]
    lats = [p[1] for x in s for p in x["polygon"]]
    assert min(lons) == DEMO[0][0] and max(lons) == DEMO[1][0] and min(lats) == DEMO[0][1] and max(lats) == DEMO[2][1]
    assert sum(grid.area_m2(x["polygon"]) for x in s) == pytest.approx(grid.area_m2(DEMO), abs=0.5)


def test_a_turned_four_corner_field_is_split_by_its_own_corners():
    """A 60 m square turned by 30 degrees: 2 x 2 sections of 900 m2 inside it, tiling it."""
    lat0, lon0 = 27.0, 85.0
    mx = 111320.0 * math.cos(math.radians(lat0))
    a = math.radians(30)
    corners = [(0, 0), (60, 0), (60, 60), (0, 60)]
    quad = [[lon0 + (x * math.cos(a) - y * math.sin(a)) / mx, lat0 + (x * math.sin(a) + y * math.cos(a)) / 110574.0]
            for x, y in corners]
    s = grid.grid_sections(quad, cell_m=30.0)
    assert len(s) == 4
    assert sum(x["area_m2"] for x in s) == pytest.approx(grid.area_m2(quad), abs=0.5)
    for x in s:
        assert x["area_m2"] == pytest.approx(900.0, abs=2.0)
        cx = sum(p[0] for p in x["polygon"]) / 4
        cy = sum(p[1] for p in x["polygon"]) / 4
        assert grid.inside(quad, cx, cy)


def test_a_big_field_gets_coarser_sections_never_more_than_40():
    big = [[85.0, 27.0], [85.003, 27.0], [85.003, 27.002], [85.0, 27.002]]      # about 297 m x 221 m
    for cell in (10.0, 30.0):
        s = grid.grid_sections(big, cell_m=cell)
        assert 10 <= len(s) <= 40
        assert sum(x["area_m2"] for x in s) == pytest.approx(grid.area_m2(big), rel=1e-4)   # areas rounded to 0.1 m2


def test_a_triangle_is_tiled_by_cells_clipped_to_it():
    tri = [[85.0, 27.0], [85.0006, 27.0], [85.0, 27.0005]]
    s = grid.grid_sections(tri)
    assert 0 < len(s) <= 40
    assert sum(x["area_m2"] for x in s) == pytest.approx(grid.area_m2(tri), rel=1e-3)
    for x in s:
        assert len(x["polygon"]) >= 3
        cx = sum(p[0] for p in x["polygon"]) / len(x["polygon"])
        cy = sum(p[1] for p in x["polygon"]) / len(x["polygon"])
        assert grid.inside(tri, cx, cy)
