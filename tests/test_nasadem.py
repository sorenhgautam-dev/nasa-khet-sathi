"""NASADEM over the fetch box: field elevation (for ET0) and slope (for the curve numbers, owner 2026-11-12:
revisit CN once the slope is known). Synthetic grids."""
import numpy as np
import pytest
from rasterio.transform import from_origin

from pipeline.fetch import nasadem as nd

RES = 1 / 3600                                      # NASADEM 1 arc-second


def test_slope_of_a_plane_matches_its_gradient():
    x = np.arange(20) * 30.0
    dem = np.tile(0.1 * x, (20, 1))                 # rises 0.1 m per metre eastward
    s = nd.slope_deg(dem, dx_m=30.0, dy_m=30.0)
    assert np.nanmean(s[1:-1, 1:-1]) == pytest.approx(np.degrees(np.arctan(0.1)), abs=1e-6)
    assert np.isnan(s[0]).all() and np.isnan(s[:, -1]).all()          # edges have no full 3x3 window


def test_flat_ground_has_zero_slope():
    assert np.nanmax(nd.slope_deg(np.full((5, 5), 1300.0), 30.0, 30.0)) == 0.0


def test_pixel_size_in_metres_shrinks_east_west_with_latitude():
    dx, dy = nd.pixel_metres(RES, 27.68)
    assert dy == pytest.approx(30.88, abs=0.05) and dx == pytest.approx(dy * np.cos(np.radians(27.68)), rel=1e-6)


def test_field_stats_use_pixels_whose_centres_fall_in_the_polygon():
    dem = np.arange(100, dtype=float).reshape(10, 10)
    t = from_origin(85.0, 27.01, RES, RES)
    poly = [[85.0 + 2 * RES, 27.01 - 5 * RES], [85.0 + 5 * RES, 27.01 - 5 * RES],
            [85.0 + 5 * RES, 27.01 - 2 * RES], [85.0 + 2 * RES, 27.01 - 2 * RES]]
    st = nd.field_stats(dem, t, poly)
    assert st["pixels"] == 9 and st["mean"] == pytest.approx(np.mean(dem[2:5, 2:5]))


def test_voids_or_out_of_range_heights_fail_loudly():
    dem = np.full((5, 5), 1300.0)
    dem[2, 2] = -32768
    with pytest.raises(ValueError, match="void"):
        nd.check_heights(dem, nodata=-32768)
