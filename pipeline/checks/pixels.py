"""Which of a dataset's pixels lie in the field (DATA_AUDIT section 2). A pixel counts when its centre is
inside the field polygon, in the dataset's own coordinate system."""
import numpy as np


def count_pixels(shape, transform, crs, polygon_lonlat):
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    ring = [list(p) for p in polygon_lonlat] + [list(polygon_lonlat[0])]
    geom = transform_geom("EPSG:4326", crs, {"type": "Polygon", "coordinates": [ring]})
    return int(geometry_mask([geom], out_shape=shape, transform=transform, invert=True, all_touched=False).sum())


def cells_holding(latlon, lat_edges, lon_edges):
    """(row, col) of the coarse cell (edges ascending) that holds the point."""
    lat, lon = latlon
    i = int(np.searchsorted(lat_edges, lat, side="right") - 1)
    j = int(np.searchsorted(lon_edges, lon, side="right") - 1)
    if not (0 <= i < len(lat_edges) - 1 and 0 <= j < len(lon_edges) - 1):
        raise ValueError("point outside the grid")
    return i, j
