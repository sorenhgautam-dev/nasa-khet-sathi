"""pipeline/sections/grid.py (CLAUDE.md "Sections"; owner's answer 2 to REVIEW_2, 2026-11-13): split the field's
polygon into about 10 m squares, 10 to 40 of them. Until step 8 fills them, the export shows them as "not ready yet"."""
import math

from pipeline.sections import grid

DEMO = [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]   # 60 m square


def _size_m(poly):
    lons, lats = [p[0] for p in poly], [p[1] for p in poly]
    return ((max(lons) - min(lons)) * 111320.0 * math.cos(math.radians(lats[0])), (max(lats) - min(lats)) * 110574.0)


def test_a_60_m_square_gives_36_sections_of_about_10_m():
    s = grid.grid_sections(DEMO)
    assert len(s) == 36 and [x["id"] for x in s] == [f"s{i}" for i in range(1, 37)]
    for x in s:
        w, h = _size_m(x["polygon"])
        assert 9.0 < w < 11.0 and 9.0 < h < 11.0 and len(x["polygon"]) == 4


def test_the_sections_tile_the_whole_field_and_nothing_else():
    s = grid.grid_sections(DEMO)
    lons = [p[0] for x in s for p in x["polygon"]]
    lats = [p[1] for x in s for p in x["polygon"]]
    assert min(lons) == DEMO[0][0] and max(lons) == DEMO[1][0] and min(lats) == DEMO[0][1] and max(lats) == DEMO[2][1]
    area = sum(_size_m(x["polygon"])[0] * _size_m(x["polygon"])[1] for x in s)
    fw, fh = _size_m(DEMO)
    assert abs(area - fw * fh) < 1.0


def test_a_big_field_gets_coarser_sections_never_more_than_40():
    big = [[85.0, 27.0], [85.003, 27.0], [85.003, 27.002], [85.0, 27.002]]      # about 297 m x 221 m
    s = grid.grid_sections(big)
    assert 10 <= len(s) <= 40


def test_a_triangle_keeps_only_the_cells_whose_centre_is_inside():
    tri = [[85.0, 27.0], [85.0006, 27.0], [85.0, 27.0005]]
    s = grid.grid_sections(tri)
    assert 0 < len(s) < 36
    for x in s:
        cx = sum(p[0] for p in x["polygon"]) / 4
        cy = sum(p[1] for p in x["polygon"]) / 4
        assert grid.inside(tri, cx, cy)
