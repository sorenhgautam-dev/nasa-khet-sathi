"""Every bit of a field in exactly one part (rules.yaml sections.patches_shape; owner, 2026-11-15, fix A2): each patch's
shape is the union of all its pieces, so the parts cover the outline with no gaps and no overlaps, for every field."""
import json
import math
from pathlib import Path

import pytest
import yaml

from pipeline.sections import grid

REPO = Path(__file__).resolve().parents[1]
FIELDS = sorted((REPO / "site" / "data" / "fields").glob("*.json"))
DRONES = sorted((REPO / "site" / "data" / "drone").glob("*.json"))


def _ring(lon0, lat0, xy_m):
    mx, my = grid.M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat0)), grid.M_PER_DEG_LAT
    return [[lon0 + x / mx, lat0 + y / my] for x, y in xy_m]


def _near_edge(xy, x, y, tol_m):
    for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy)))
        if math.hypot(x - x0 - t * dx, y - y0 - t * dy) < tol_m:
            return True
    return False


def _cover(outline, parts, n=160, tol_m=0.03):
    """(points in the outline, in no part, in two or more parts, in a part but outside the outline), sampled on an
    n x n grid offset by odd fractions so that no point lies on a grid line or a shared edge. Points within tol_m of the
    outline are skipped: part corners are stored to 7 decimals of a degree (about 1 cm)."""
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    scale, o = grid._scale(outline), (outline[0][0], outline[0][1])
    xy = grid.local_metres(outline, o, scale)
    counts = [0, 0, 0, 0]
    for a in range(n):
        for b in range(n):
            lon = min(xs) + (max(xs) - min(xs)) * (a + 0.3713) / n
            lat = min(ys) + (max(ys) - min(ys)) * (b + 0.6187) / n
            if _near_edge(xy, (lon - o[0]) * scale[0], (lat - o[1]) * scale[1], tol_m):
                continue
            k, inn = sum(grid.inside(q, lon, lat) for q in parts), grid.inside(outline, lon, lat)
            counts[0] += inn
            counts[1] += inn and k == 0
            counts[2] += k >= 2
            counts[3] += (not inn) and k >= 1
    return counts


def test_an_l_shaped_patch_is_drawn_whole():
    """Cells 10 m, an L-shaped outline of 160 m2: the whole cell (0..10, 0..10) and two 30 m2 edge pieces, one east
    (10..13, 0..10) and one north (0..10, 10..13), both joined to it. The cells make an L, not a rectangle, so the shape
    was the main piece only (100 m2); it must be the union, the whole outline: 160 m2, every point in the one part."""
    lon0, lat0 = 85.5, 27.6
    ring = _ring(lon0, lat0, [(0, 0), (13, 0), (13, 10), (10, 10), (10, 13), (0, 13)])
    ps, lines = grid.patches(ring, (lon0, lat0), join="touching")
    assert len(ps) == 1 and ps[0]["area_m2"] == 160.0 and not ps[0]["whole"] and len(ps[0]["pieces"]) == 3
    assert grid.area_m2(ps[0]["polygon"]) == pytest.approx(160.0, abs=0.1)
    assert _cover(ring, [ps[0]["polygon"]])[1:] == [0, 0, 0]
    assert lines == []


def test_a_u_shaped_field_with_small_pieces_joined_by_nearest_centre_is_still_covered_once():
    """A U-shaped outline (30 m x 10 m, two 6 m x 4 m arms on top) cut through its corner: the arms' tops are 24 m2
    pieces joined by nearest centre (the Dhulikhel option). Every point still lies in exactly one part."""
    lon0, lat0 = 85.5, 27.6
    ring = _ring(lon0, lat0, [(0, 0), (30, 0), (30, 14), (24, 14), (24, 10), (6, 10), (6, 14), (0, 14)])
    ps, _ = grid.patches(ring, (lon0, lat0))
    assert sum(p["area_m2"] for p in ps) == pytest.approx(grid.area_m2(ring), abs=0.1)
    assert _cover(ring, [p["polygon"] for p in ps])[1:] == [0, 0, 0]


@pytest.mark.parametrize("path", FIELDS, ids=[p.stem for p in FIELDS])
def test_every_fields_parts_cover_its_outline_once(path):
    outline = yaml.safe_load((REPO / "config" / "fields" / f"{path.stem}.yaml").read_text())["polygon"]
    parts = [s["polygon"] for s in json.loads(path.read_text())["field"]["sections"]]
    inn, gap, two, out = _cover(outline, parts)
    assert inn > 5000 and (gap, two, out) == (0, 0, 0), (path.stem, inn, gap, two, out)


@pytest.mark.parametrize("path", DRONES, ids=[p.stem for p in DRONES])
def test_every_drone_files_patches_cover_its_outline_once_and_match_the_field_file(path):
    d = json.loads(path.read_text())
    inn, gap, two, out = _cover(d["outline"], [p["polygon"] for p in d["patches"]])
    assert inn > 5000 and (gap, two, out) == (0, 0, 0), (path.stem, inn, gap, two, out)
    for p in d["patches"]:                        # the number sits inside its own part
        assert grid.inside(p["polygon"], *p["centre"]), (path.stem, p["id"])
    f = REPO / "site" / "data" / "fields" / f"{path.stem}.json"
    if f.exists():                                # the parts screen and the photo draw the same shapes
        secs = {s["id"]: s["polygon"] for s in json.loads(f.read_text())["field"]["sections"]}
        assert secs == {p["id"]: p["polygon"] for p in d["patches"]}
