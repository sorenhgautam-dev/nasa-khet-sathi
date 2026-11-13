"""CHIRPS v3.0 cross-check fetch (rain check B; pipeline/fetch/chirps.py): the pure parts, with worked numbers."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import chirps as ch
from pipeline.fetch.guards import DataGuardError

LAT = np.round(-59.975 + 0.05 * np.arange(2400), 3)        # CHIRPS v3 0.05 deg cell centres (read 2026-11-13)
LON = np.round(-179.975 + 0.05 * np.arange(7200), 3)
BOX = [85.379227, 27.625034, 85.480773, 27.714966]           # demo fetch box


def test_box_cells_are_the_cells_overlapping_the_box_and_the_field_cell_holds_the_point():
    rows, cols, fcell = ch.box_cells(LAT, LON, BOX, 27.690767, 85.441792)
    assert [LAT[i] for i in rows] == [27.625, 27.725] and [LON[j] for j in cols] == [85.375, 85.475]
    assert LAT[rows[0] + fcell[0]] == 27.675 and LON[cols[0] + fcell[1]] == 85.425   # 27.65-27.70 N, 85.40-85.45 E


def test_a_box_outside_the_grid_fails():
    with pytest.raises(ValueError, match="no CHIRPS cell"):
        ch.box_cells(LAT, LON, [85.4, 61.0, 85.5, 61.1], 61.05, 85.45)


def test_time_axis_in_days_since_an_origin():
    d = ch.days_from_time([14610, 14611], "days since 1980-1-1 0:0:0")
    assert list(d) == [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02")]   # 1980-01-01 + 14610 days
    with pytest.raises(ValueError, match="time units"):
        ch.days_from_time([1], "hours since 1980-01-01")


def test_fills_are_removed_and_counted_and_a_value_out_of_range_fails():
    a, n = ch.clean_values(np.array([0.0, -9999.0, 12.5], np.float32), [-9999.0])
    assert n == 1 and np.isnan(a[1]) and a[2] == 12.5
    with pytest.raises(DataGuardError, match="above 500"):
        ch.clean_values(np.array([600.0], np.float32), [-9999.0])


def test_years_around_the_break_come_first():
    assert ch.year_order(2001, 2025)[:8] == list(range(2013, 2021))
    order = ch.year_order(2001, 2025)
    assert order[8:12] == [2021, 2012, 2022, 2011] and sorted(order) == list(range(2001, 2026))


def test_a_cached_year_round_trips_without_pickles(tmp_path):
    """The cache must load with allow_pickle=False: dates are stored as fixed-width text, not Python objects."""
    days = pd.date_range("2020-01-01", "2020-01-03")
    r = {"days": days, "values": np.zeros((3, 2, 2)), "lat": np.array([27.675, 27.725]), "lon": np.array([85.425, 85.475]),
         "field_cell": (0, 0), "raw_attrs": {"units": "mm/day"}, "attrs": {}, "fills": 0, "http": {"requests": 1}}
    ch.save_year(tmp_path, 2020, r)
    back = ch.load_year(tmp_path, 2020)
    assert list(back["days"]) == list(days) and back["field_cell"] == (0, 0) and back["raw_attrs"] == {"units": "mm/day"}
