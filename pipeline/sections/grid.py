"""Split a field's polygon into sections (CLAUDE.md "Sections"). Pure functions.

About 10 m by 10 m squares, coarser for big fields, aiming for 10 to 40 sections. The grid covers the polygon's
bounding box with equal cells that tile it exactly; a cell is kept when its centre lies inside the polygon.
Terrace steps as boundaries and the per-section attributes (slope, low ground, soil, probe) are build step 8.
Until then the export shows the sections as "not ready yet" (owner's answer 2 to REVIEW_2, 2026-11-13).
"""
import math

M_PER_DEG_LAT = 110574.0          # metres per degree of latitude (mean; good to well under a metre over a field)
M_PER_DEG_LON_EQUATOR = 111320.0


def inside(polygon, lon, lat):
    """Ray casting: is the point inside the polygon ([lon, lat] corners, ring not closed)?"""
    n, hit = len(polygon), False
    for i in range(n):
        (x1, y1), (x2, y2) = polygon[i], polygon[(i + 1) % n]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def grid_sections(polygon, cell_m=10.0, max_sections=40):
    """[{id: 's1'.., polygon: four [lon, lat] corners (SW, SE, NE, NW)}], row by row from the south-west corner."""
    lons, lats = [p[0] for p in polygon], [p[1] for p in polygon]
    lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
    m_lon = M_PER_DEG_LON_EQUATOR * math.cos(math.radians((lat0 + lat1) / 2.0))
    width_m, height_m = (lon1 - lon0) * m_lon, (lat1 - lat0) * M_PER_DEG_LAT
    size = float(cell_m)
    while True:
        nx, ny = max(1, round(width_m / size)), max(1, round(height_m / size))
        cells = []
        for j in range(ny):
            for i in range(nx):
                a, b = lon0 + (lon1 - lon0) * i / nx, lon0 + (lon1 - lon0) * (i + 1) / nx
                c, d = lat0 + (lat1 - lat0) * j / ny, lat0 + (lat1 - lat0) * (j + 1) / ny
                if i == nx - 1:
                    b = lon1
                if j == ny - 1:
                    d = lat1
                if inside(polygon, (a + b) / 2.0, (c + d) / 2.0):
                    cells.append([[a, c], [b, c], [b, d], [a, d]])
        if len(cells) <= max_sections:
            break
        size *= 1.1
    return [{"id": f"s{k + 1}", "polygon": [[round(x, 7), round(y, 7)] for x, y in cell]} for k, cell in enumerate(cells)]
