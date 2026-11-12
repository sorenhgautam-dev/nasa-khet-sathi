"""Field outline over each gridded dataset's pixels (DATA_AUDIT section 2): which pixel centres fall in the
field, in the dataset's own coordinate system."""
import numpy as np
import pytest
from rasterio.transform import from_origin

from pipeline.checks import pixels as px

POLY = [[85.4270, 27.6780], [85.4276, 27.6780], [85.4276, 27.6786], [85.4270, 27.6786]]   # about 60 m


def test_pixels_in_a_geographic_grid():
    t = from_origin(85.4260, 27.6790, 1 / 3600, 1 / 3600)          # 1 arc-second (NASADEM)
    n = px.count_pixels((20, 20), t, "EPSG:4326", POLY)
    assert 2 <= n <= 6


def test_pixels_in_a_utm_grid_use_the_polygon_reprojected():
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:4326", "EPSG:32645", [85.4260], [27.6790])
    t = from_origin(xs[0], ys[0], 30, 30)                           # HLS 30 m, UTM 45N
    n = px.count_pixels((10, 10), t, "EPSG:32645", POLY)
    assert 2 <= n <= 6


def test_a_field_smaller_than_one_pixel_is_reported_as_inside_one_cell():
    assert px.cells_holding((27.6783, 85.4273), lat_edges=np.arange(27.0, 28.01, 0.5), lon_edges=np.arange(85.0, 86.01, 0.5)) == (1, 0)
