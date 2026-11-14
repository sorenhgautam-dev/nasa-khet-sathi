"""Split a field's outline into sections (CLAUDE.md "Sections"; build step 8). Pure functions.

- A field drawn by its four corners (config/fields/<id>.yaml `polygon`: SW, SE, NE, NW as [lon, lat]) is split by its
  own corners: n_u x n_v four-sided sections from bilinear interpolation of the corners, n = round(side / cell_m) and at
  least 1, a side being the mean of two opposite edges. The sections tile the field exactly, whatever its orientation.
- Any other outline (or four corners that are not convex) is covered by square cells of its bounding box, each clipped
  to the outline (Sutherland-Hodgman), so the pieces tile it too; crumbs under min_piece_m2 are dropped.
- When a field would have more than max_sections, the cell side grows by coarsen_factor until it fits (CLAUDE.md:
  coarser for big fields, at most 40).
Ids s1..sN run row by row from the first corner (the south-west one). Polygons are [lon, lat] rings, not closed.

Step 8 passes rules.yaml sections.cell_m (30 m, about one HLS pixel). The default 10 m is the step-1 grid that
pipeline/export/build_field_json.py still draws while the export names the sections as "not ready yet".
Distances use a flat-earth scale at the outline's mean latitude (good to well under a metre over a field).
"""
import math

M_PER_DEG_LAT = 110574.0          # metres per degree of latitude (mean; good to well under a metre over a field)
M_PER_DEG_LON_EQUATOR = 111320.0


def inside(polygon, lon, lat):
    """Ray casting: is the point inside the polygon ([lon, lat] corners, ring not closed)?"""
    n, hit = len(polygon), False
    for i in range(n):
        (x1, y1), (x2, y2) = polygon[i][:2], polygon[(i + 1) % n][:2]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def shoelace(points):
    """Area of a simple polygon given as (x, y) corners, ring not closed."""
    n = len(points)
    if n < 3:
        return 0.0
    s = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n))
    return abs(s) / 2.0


def _scale(polygon):
    lat_mean = sum(p[1] for p in polygon) / len(polygon)
    return M_PER_DEG_LON_EQUATOR * math.cos(math.radians(lat_mean)), M_PER_DEG_LAT


def local_metres(polygon, origin=None, scale=None):
    """[(x_m, y_m)] east and north of `origin` (default: the first corner), flat-earth at the mean latitude."""
    mx, my = scale or _scale(polygon)
    lon0, lat0 = origin or (polygon[0][0], polygon[0][1])
    return [((p[0] - lon0) * mx, (p[1] - lat0) * my) for p in polygon]


def area_m2(polygon):
    """Area of a [lon, lat] polygon in square metres."""
    return shoelace(local_metres(polygon))


def clip_to_rect(points, xmin, ymin, xmax, ymax):
    """Sutherland-Hodgman: the part of a polygon ((x, y) corners) inside an axis-parallel rectangle; [] if none.
    Exact in area for any simple polygon (a concave one may come back with zero-width joins)."""
    def x_cut(x0):
        return lambda a, b: (x0, a[1] + (x0 - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))

    def y_cut(y0):
        return lambda a, b: (a[0] + (y0 - a[1]) / (b[1] - a[1]) * (b[0] - a[0]), y0)

    edges = ((lambda p: p[0] >= xmin, x_cut(xmin)), (lambda p: p[0] <= xmax, x_cut(xmax)),
             (lambda p: p[1] >= ymin, y_cut(ymin)), (lambda p: p[1] <= ymax, y_cut(ymax)))
    pts = [tuple(p[:2]) for p in points]
    for keep, cut in edges:
        if not pts:
            return []
        out = []
        for k in range(len(pts)):
            cur, prev = pts[k], pts[k - 1]
            if keep(cur):
                if not keep(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif keep(prev):
                out.append(cut(prev, cur))
        pts = out
    clean = []
    for p in pts:                                            # drop repeated corners
        if not clean or abs(p[0] - clean[-1][0]) > 1e-12 or abs(p[1] - clean[-1][1]) > 1e-12:
            clean.append(p)
    if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) <= 1e-12 and abs(clean[0][1] - clean[-1][1]) <= 1e-12:
        clean.pop()
    return clean if len(clean) >= 3 else []


def _convex(xy):
    signs = set()
    n = len(xy)
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = xy[i], xy[(i + 1) % n], xy[(i + 2) % n]
        cross = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
        if abs(cross) < 1e-9:
            return False
        signs.add(cross > 0)
    return len(signs) == 1


def _split_quad(p, cell_m, max_sections, coarsen_factor):
    xy = local_metres(p)

    def d(a, b):
        return math.hypot(b[0] - a[0], b[1] - a[1])

    side_u = (d(xy[0], xy[1]) + d(xy[3], xy[2])) / 2.0
    side_v = (d(xy[0], xy[3]) + d(xy[1], xy[2])) / 2.0
    size = float(cell_m)
    while True:
        nu, nv = max(1, round(side_u / size)), max(1, round(side_v / size))
        if nu * nv <= max_sections:
            break
        size *= coarsen_factor

    def at(u, v):
        return tuple((1 - u) * (1 - v) * p[0][k] + u * (1 - v) * p[1][k] + u * v * p[2][k] + (1 - u) * v * p[3][k]
                     for k in (0, 1))

    return [[at(i / nu, j / nv), at((i + 1) / nu, j / nv), at((i + 1) / nu, (j + 1) / nv), at(i / nu, (j + 1) / nv)]
            for j in range(nv) for i in range(nu)]


def _clip_grid(p, cell_m, max_sections, coarsen_factor, min_piece_m2):
    origin, scale = (p[0][0], p[0][1]), _scale(p)
    xy = local_metres(p, origin, scale)
    xs, ys = [q[0] for q in xy], [q[1] for q in xy]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    size = float(cell_m)
    while True:
        nx, ny = max(1, round((x1 - x0) / size)), max(1, round((y1 - y0) / size))
        pieces = []
        for j in range(ny):
            for i in range(nx):
                a = x0 + (x1 - x0) * i / nx
                b = x1 if i == nx - 1 else x0 + (x1 - x0) * (i + 1) / nx
                c = y0 + (y1 - y0) * j / ny
                e = y1 if j == ny - 1 else y0 + (y1 - y0) * (j + 1) / ny
                piece = clip_to_rect(xy, a, c, b, e)
                if piece and shoelace(piece) >= min_piece_m2:
                    pieces.append(piece)
        if len(pieces) <= max_sections:
            break
        size *= coarsen_factor
    return [[(origin[0] + x / scale[0], origin[1] + y / scale[1]) for x, y in piece] for piece in pieces]


def grid_sections(polygon, cell_m=10.0, max_sections=40, coarsen_factor=1.1, min_piece_m2=1.0):
    """[{id: 's1'.., polygon: [lon, lat] corners (ring not closed), area_m2}], row by row from the first corner."""
    pts = [(float(q[0]), float(q[1])) for q in polygon]
    if len(pts) == 4 and _convex(local_metres(pts)):
        cells = _split_quad(pts, cell_m, max_sections, coarsen_factor)
    else:
        cells = _clip_grid(pts, cell_m, max_sections, coarsen_factor, min_piece_m2)
    return [{"id": f"s{k + 1}", "polygon": [[round(x, 7), round(y, 7)] for x, y in cell],
             "area_m2": round(area_m2(cell), 1)} for k, cell in enumerate(cells)]


def centroid_area(points):
    """(x, y, area) of a simple polygon given as (x, y) corners, ring not closed (the area-weighted centre)."""
    a = cx = cy = 0.0
    for i in range(len(points)):
        (x0, y0), (x1, y1) = points[i][:2], points[(i + 1) % len(points)][:2]
        k = x0 * y1 - x1 * y0
        a, cx, cy = a + k, cx + (x0 + x1) * k, cy + (y0 + y1) * k
    return (cx / (3 * a), cy / (3 * a), abs(a) / 2) if a else (0.0, 0.0, 0.0)


def patches(polygon, centre, cell_m=10.0, min_piece_m2=50.0, prefix="p"):
    """A drawn field's patches (the Dhulikhel package's method, owner 2026-11-15): a cell_m grid whose lines pass through
    the field's centre ([lon, lat]), each cell clipped to the outline; a piece under min_piece_m2 is joined to the patch
    whose centre is nearest its own; numbered from the south-west, row by row, west to east. Each patch: id, row, col
    (of its main cell), area_m2, centre [lon, lat] (the centre of its own area), pieces ([lon, lat] rings) and polygon:
    one ring, the outline clipped to the rectangle its cells make (exactly its pieces' union), or, when its cells do not
    make a rectangle, its main piece only (whole: false).
    Returns (patches, lines): lines are the [[lon, lat], [lon, lat]] edges between two different patches, for drawing
    them over a photo with the outline (edges between the pieces of one patch are left out)."""
    pts = [(float(q[0]), float(q[1])) for q in polygon]
    scale, lon0, lat0 = _scale(pts), float(centre[0]), float(centre[1])
    xy = local_metres(pts, (lon0, lat0), scale)
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    pieces = []
    for j in range(math.floor(min(ys) / cell_m), math.ceil(max(ys) / cell_m)):
        for i in range(math.floor(min(xs) / cell_m), math.ceil(max(xs) / cell_m)):
            ring = clip_to_rect(xy, i * cell_m, j * cell_m, (i + 1) * cell_m, (j + 1) * cell_m)
            x, y, a = centroid_area(ring) if ring else (0.0, 0.0, 0.0)
            if a > 1e-6:
                pieces.append({"i": i, "j": j, "ring": ring, "x": x, "y": y, "a": a})
    big = [p for p in pieces if p["a"] >= min_piece_m2] or [max(pieces, key=lambda p: p["a"])]
    for p in pieces:
        p["owner"] = p if p in big else min(big, key=lambda b: math.hypot(b["x"] - p["x"], b["y"] - p["y"]))
    big.sort(key=lambda b: (b["j"], b["i"]))
    to_lonlat = lambda x, y: [round(lon0 + x / scale[0], 7), round(lat0 + y / scale[1], 7)]   # noqa: E731
    out = []
    for k, b in enumerate(big):
        b["id"] = f"{prefix}{k + 1}"
        mine = [p for p in pieces if p["owner"] is b]
        area = sum(p["a"] for p in mine)
        ii, jj = {p["i"] for p in mine}, {p["j"] for p in mine}
        whole = len(mine) == (max(ii) - min(ii) + 1) * (max(jj) - min(jj) + 1)
        ring = clip_to_rect(xy, min(ii) * cell_m, min(jj) * cell_m, (max(ii) + 1) * cell_m, (max(jj) + 1) * cell_m) if whole else b["ring"]
        out.append({"id": b["id"], "row": b["j"], "col": b["i"], "area_m2": round(area, 1),
                    "polygon": [to_lonlat(x, y) for x, y in ring], "whole": whole,
                    "centre": to_lonlat(sum(p["a"] * p["x"] for p in mine) / area, sum(p["a"] * p["y"] for p in mine) / area),
                    "pieces": [[to_lonlat(x, y) for x, y in p["ring"]] for p in mine]})
    cell = {(p["i"], p["j"]): p for p in pieces}
    lines = []
    for p in pieces:                      # a piece's edge on its cell's east or north side, when the next cell's piece
        for di, dj in ((1, 0), (0, 1)):   # belongs to another patch: one line per shared edge
            nb = cell.get((p["i"] + di, p["j"] + dj))
            if nb is None or nb["owner"] is p["owner"]:
                continue
            k = (p["i"] + 1) * cell_m if di else (p["j"] + 1) * cell_m
            on = [q for q in p["ring"] if abs((q[0] if di else q[1]) - k) < 1e-6]
            if len(on) >= 2:
                lo, hi = (min(on, key=lambda q: q[1]), max(on, key=lambda q: q[1])) if di else \
                         (min(on, key=lambda q: q[0]), max(on, key=lambda q: q[0]))
                lines.append([to_lonlat(*lo), to_lonlat(*hi)])
    return out, lines
