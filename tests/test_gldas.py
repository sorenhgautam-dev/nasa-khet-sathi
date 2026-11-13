"""GLDAS-2.1 Noah monthly (owner, 2026-11-14: a check on the twin's soil water and evapotranspiration only):
pipeline/fetch/gldas.py. Worked numbers for the pure parts: the 0.25-degree cell that holds the field, the DAP4
constraint, the unit conversions, the fill and range guards, and the month of a file."""
import h5py
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import gldas
from pipeline.fetch.guards import DataGuardError


def test_the_demo_field_is_in_cell_row_350_col_1061():
    # GLDAS 0.25 deg grid: 600 rows from -59.875 N, 1440 columns from -179.875 E (the file's own lat/lon, read 2026-11-14)
    assert gldas.cell_index(27.690767, 85.441792) == (350, 1061)
    assert gldas.cell_centre(350, 1061) == (27.625, 85.375)


def test_a_point_south_of_the_grid_is_refused():
    with pytest.raises(ValueError, match="outside"):
        gldas.cell_index(-65.0, 85.0)


def test_the_constraint_asks_for_the_3x3_cells_around_the_field():
    ce = gldas.constraint((350, 1061), ["SoilMoi0_10cm_inst", "Evap_tavg"])
    assert "/SoilMoi0_10cm_inst[0:1:0][349:1:351][1060:1:1062]" in ce
    assert "/Evap_tavg[0:1:0][349:1:351][1060:1:1062]" in ce
    assert "/lat[349:1:351]" in ce and "/lon[1060:1:1062]" in ce and "/time_bnds" in ce


def test_unit_conversions():
    # kg m-2 of water = mm; a 0-10 cm layer holding 25 mm is 0.25 m3/m3
    assert gldas.layer_theta(25.0, "SoilMoi0_10cm_inst") == pytest.approx(0.25)
    assert gldas.layer_theta(90.0, "SoilMoi10_40cm_inst") == pytest.approx(0.30)
    # 1e-5 kg m-2 s-1 x 86,400 s/day = 0.864 mm/day
    assert gldas.flux_mm_day(1e-5) == pytest.approx(0.864)
    # 100 W m-2 / (2.45 MJ/kg) x 86,400 s = 3.5265 mm/day (FAO-56's latent heat)
    assert gldas.energy_mm_day(100.0) == pytest.approx(3.5265, abs=1e-4)


def _cached(path, sm=20.0, et=1e-5, fill_centre=False, lat0=27.375, lon0=85.125, t0=366.0):
    with h5py.File(path, "w") as h:
        h["lat"] = np.array([lat0, lat0 + 0.25, lat0 + 0.5], dtype="f4")
        h["lon"] = np.array([lon0, lon0 + 0.25, lon0 + 0.5], dtype="f4")
        h["time"] = np.array([t0])
        h["time_bnds"] = np.array([[t0, t0 + 31]])
        for v in gldas.VARIABLES:
            val = {"Evap_tavg": et, "Rainf_f_tavg": 2e-5}.get(v, 100.0 if v.endswith("_tavg") else sm * gldas.LAYER_MM.get(v, 1000.0) / 100.0)
            a = np.full((1, 3, 3), val, dtype="f4")
            if fill_centre:
                a[0, 1, 1] = -9999.0
            d = h.create_dataset(v, data=a)
            d.attrs["_FillValue"] = np.array([-9999.0], dtype="f4")
            d.attrs["units"] = np.bytes_(gldas.UNITS_IN[v])
    return path


def test_read_month_converts_and_labels_the_month(tmp_path):
    row = gldas.read_month(_cached(tmp_path / "a.nc4"), (350, 1061))
    assert row["month"] == pd.Timestamp("2001-01-01")
    assert row["theta_0_10cm_m3m3"] == pytest.approx(0.20)
    assert row["theta_0_100cm_m3m3"] == pytest.approx(0.20)
    assert row["et_mm_day"] == pytest.approx(0.864, abs=1e-6)
    assert row["et_mm"] == pytest.approx(0.864 * 31, abs=1e-4)
    assert row["pet_mm_day"] == pytest.approx(3.5265, abs=1e-4)
    assert row["rain_mm_day"] == pytest.approx(1.728, abs=1e-6)


def test_a_fill_in_the_fields_cell_fails_loudly(tmp_path):
    with pytest.raises(DataGuardError, match="fill"):
        gldas.read_month(_cached(tmp_path / "a.nc4", fill_centre=True), (350, 1061))


def test_a_shifted_grid_is_refused(tmp_path):
    with pytest.raises(ValueError, match="grid"):
        gldas.read_month(_cached(tmp_path / "a.nc4", lat0=27.125), (350, 1061))


def test_soil_moisture_above_the_rule_12_range_fails_loudly(tmp_path):
    with pytest.raises(DataGuardError):
        gldas.read_month(_cached(tmp_path / "a.nc4", sm=70.0), (350, 1061))     # 0.70 m3/m3 > 0.6


def test_wrong_units_are_refused(tmp_path):
    p = _cached(tmp_path / "a.nc4")
    with h5py.File(p, "r+") as h:
        h["Evap_tavg"].attrs["units"] = np.bytes_("mm/day")
    with pytest.raises(DataGuardError, match="units"):
        gldas.read_month(p, (350, 1061))


def test_missing_months_are_listed():
    have = [pd.Timestamp("2001-01-01"), pd.Timestamp("2001-03-01")]
    assert gldas.missing_months(have, "2001-01", "2001-03") == ["2001-02"]


def test_a_file_holding_another_month_is_refused(tmp_path):
    # 2026-11-14: under parallel requests the cloud OPeNDAP answered 3 of 300 months with March 2001's granule
    p = _cached(tmp_path / "GLDAS_NOAH025_M.A200102.021.sub.nc4", t0=366.0)      # holds January 2001
    with pytest.raises(DataGuardError, match="holds 2001-01"):
        gldas.read_month(p, (350, 1061), expect_month="2001-02")
    assert gldas.read_month(p, (350, 1061), expect_month="2001-01")["month"] == pd.Timestamp("2001-01-01")


def test_the_month_is_read_from_the_cache_name():
    assert gldas.month_of_cache("x/GLDAS_NOAH025_M.A200102.021.sub.nc4") == "2001-02"
