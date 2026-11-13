"""NEX-GDDP-CMIP6 point fetch (build step 9; rules.yaml future): the pure helpers of pipeline/fetch/nexgddp.py.

Worked numbers: the field's cell (27.625 N, 85.375 E) is the grid point the NCCS THREDDS server itself returned for the
demo field's centre (NetcdfSubset CSV, 2026-11-13: 'GridPointRequestedAt[27.691N_85.442E],27.625,85.375'); the
header, rows and attributes below are copied from the server's answers that night (ACCESS-CM2 tasmax 2000; UKESM1-0-LL
pr 2028, a 360-day calendar with 30 February)."""
import numpy as np
import pytest

from pipeline.fetch import guards as g
from pipeline.fetch import nexgddp as nx

CSV_K = """time,station,latitude[unit="degrees_north"],longitude[unit="degrees_east"],tasmax[unit="K"]
2000-01-01T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,291.8608
2000-01-02T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,290.43753
2000-12-31T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,284.63538
"""

CSV_360 = """time,station,latitude[unit="degrees_north"],longitude[unit="degrees_east"],pr[unit="kg m-2 s-1"]
2028-02-29T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,2.7538513E-4
2028-02-30T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,6.190305E-4
2028-03-01T12:00:00Z,GridPointRequestedAt[27.625N_85.375E],27.625,85.375,1.0E20
"""

DAS = """Attributes {
    pr {
        Float32 _FillValue 1.0E20;
        String standard_name "precipitation_flux";
        String units "kg m-2 s-1";
        Float32 missing_value 1.0E20;
        UInt32 _ChunkSizes 1, 600, 1440;
    }
    time {
        String axis "T";
        String calendar "360_day";
        String units "days since 1850-01-01";
    }
    NC_GLOBAL {
        String cmip6_source_id "UKESM1-0-LL";
        String cmip6_license "CC-BY 4.0";
        String version "2.0";
    }
}
"""

CATALOG = """<?xml version="1.0" encoding="UTF-8"?>
<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.2">
  <dataset name="ACCESS-CM2/historical/r1i1p1f1/tasmax/">
    <dataset name="tasmax_day_ACCESS-CM2_historical_r1i1p1f1_gn_1995_v2.0.nc" ID="x" urlPath="AMES/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1/tasmax/tasmax_day_ACCESS-CM2_historical_r1i1p1f1_gn_1995_v2.0.nc">
      <dataSize units="Mbytes">248.4</dataSize>
    </dataset>
    <catalogRef xlink:href="r1i1p1f1/catalog.xml" xlink:title="r1i1p1f1" ID="y" name="r1i1p1f1"/>
  </dataset>
</catalog>
"""


def test_cell_centre_is_the_cell_the_server_returned_for_the_demo_field():
    assert nx.cell_centre(27.690767, 85.441792) == (27.625, 85.375)
    assert nx.cell_key(27.625, 85.375) == "cell_27.625_85.375"


def test_cell_centre_west_and_south_use_the_grid_0_to_360():
    # 14.6 N, 90.52 W: lon 269.48 E lies in the cell 269.25-269.5, centre 269.375
    assert nx.cell_centre(14.6, -90.52) == (14.625, 269.375)
    assert nx.cell_centre(-1.30, 36.80) == (-1.375, 36.875)


def test_parse_file_name_with_and_without_version():
    f = nx.parse_file_name("tasmax_day_ACCESS-CM2_historical_r1i1p1f1_gn_2000_v2.0.nc")
    assert (f["var"], f["model"], f["exp"], f["variant"], f["grid"], f["year"], f["version"]) == \
        ("tasmax", "ACCESS-CM2", "historical", "r1i1p1f1", "gn", 2000, "2.0")
    f = nx.parse_file_name("pr_day_GFDL-CM4_ssp245_r1i1p1f1_gr1_2030.nc")
    assert (f["model"], f["grid"], f["year"], f["version"]) == ("GFDL-CM4", "gr1", 2030, None)
    assert nx.parse_file_name("readme.txt") is None


def _e(name):
    return {"name": name, "url_path": "P/" + name}


def test_pick_files_prefers_v2_and_records_it():
    entries = [_e("pr_day_M_ssp245_r1i1p1f1_gn_2026.nc"), _e("pr_day_M_ssp245_r1i1p1f1_gn_2026_v1.1.nc"),
               _e("pr_day_M_ssp245_r1i1p1f1_gn_2026_v2.0.nc"), _e("pr_day_M_ssp245_r1i1p1f1_gn_2027_v1.1.nc"),
               _e("tasmax_day_M_ssp245_r1i1p1f1_gn_2026_v2.0.nc")]
    got = nx.pick_files(entries, "pr", "ssp245", [2026, 2027])
    assert got[2026]["name"].endswith("_2026_v2.0.nc") and got[2026]["version"] == "2.0"
    assert got[2027]["name"].endswith("_2027_v1.1.nc")          # the only file for 2027 is used, its version recorded
    with pytest.raises(nx.MissingFiles):
        nx.pick_files(entries, "pr", "ssp245", [2026, 2028])
    with pytest.raises(nx.MissingFiles):                         # two files, neither v2.0: ambiguous, never a guess
        nx.pick_files([_e("pr_day_M_ssp245_r1i1p1f1_gn_2026.nc"), _e("pr_day_M_ssp245_r1i1p1f1_gn_2026_v1.1.nc")],
                      "pr", "ssp245", [2026])


def test_parse_catalog():
    c = nx.parse_catalog(CATALOG)
    assert c["refs"] == ["r1i1p1f1"]
    assert c["files"] == [{"name": "tasmax_day_ACCESS-CM2_historical_r1i1p1f1_gn_1995_v2.0.nc",
                           "url_path": "AMES/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1/tasmax/"
                                       "tasmax_day_ACCESS-CM2_historical_r1i1p1f1_gn_1995_v2.0.nc"}]


def test_parse_csv_reads_units_grid_point_and_model_dates_as_numbers():
    p = nx.parse_csv(CSV_K, "tasmax")
    assert p["units"] == "K" and (p["lat"], p["lon"]) == (27.625, 85.375)
    assert p["rows"][["year", "month", "day"]].values.tolist() == [[2000, 1, 1], [2000, 1, 2], [2000, 12, 31]]
    assert p["rows"]["value"].tolist() == pytest.approx([291.8608, 290.43753, 284.63538])
    q = nx.parse_csv(CSV_360, "pr")                              # 30 February exists in a 360-day calendar
    assert q["rows"][["month", "day"]].values.tolist() == [[2, 29], [2, 30], [3, 1]]
    with pytest.raises(g.DataGuardError):
        nx.parse_csv(CSV_K, "pr")                                # the column asked for is not in the answer


def test_convert_units_with_worked_numbers():
    rain, n_fill = nx.convert(np.array([1.1574074e-5, 0.0, 1.0e20]), "pr", "kg m-2 s-1", fills=[1.0e20])
    assert rain[:2] == pytest.approx([1.0, 0.0], abs=1e-6)       # 1.1574074e-5 kg m-2 s-1 x 86400 s = 1.0 mm/day
    assert np.isnan(rain[2]) and n_fill == 1
    t, _ = nx.convert(np.array([291.8608]), "tasmax", "K", fills=[1.0e20])
    assert t[0] == pytest.approx(18.7108)                         # 291.8608 K - 273.15
    with pytest.raises(g.DataGuardError):
        nx.convert(np.array([291.0]), "tasmax", "degC", fills=[])  # unexpected unit: refused, not guessed
    with pytest.raises(g.DataGuardError):
        nx.convert(np.array([400.0]), "tasmax", "K", fills=[])     # 126.85 C: out of range, never clipped
    with pytest.raises(g.DataGuardError):
        nx.convert(np.array([-1e-6]), "pr", "kg m-2 s-1", fills=[])


def test_parse_das_reads_fill_units_calendar_and_licence():
    d = nx.parse_das(DAS)
    assert d["pr"]["_FillValue"] == 1.0e20 and d["pr"]["units"] == "kg m-2 s-1"
    assert d["time"]["calendar"] == "360_day"
    assert d["NC_GLOBAL"]["cmip6_license"] == "CC-BY 4.0"


def test_year_rows_must_match_the_calendar():
    import pandas as pd
    days360 = pd.DataFrame([(2028, m, d) for m in range(1, 13) for d in range(1, 31)], columns=["year", "month", "day"])
    nx.check_year_rows(days360, 2028, "360_day")
    noleap = pd.DataFrame([(t.year, t.month, t.day) for t in pd.date_range("2028-01-01", "2028-12-31")
                           if not (t.month == 2 and t.day == 29)], columns=["year", "month", "day"])
    nx.check_year_rows(noleap, 2028, "noleap")
    std = pd.DataFrame([(t.year, t.month, t.day) for t in pd.date_range("2028-01-01", "2028-12-31")],
                       columns=["year", "month", "day"])
    nx.check_year_rows(std, 2028, "standard")
    with pytest.raises(g.DataGuardError):
        nx.check_year_rows(noleap, 2028, "standard")             # a leap year without 29 February
    with pytest.raises(g.DataGuardError):
        nx.check_year_rows(days360, 2027, "360_day")             # rows of another year


def test_model_order_is_a_fixed_random_permutation():
    names = ["B", "A", "D", "C", "E"]
    o1, o2 = nx.model_order(names, 2026), nx.model_order(list(reversed(names)), 2026)
    assert o1 == o2 and sorted(o1) == sorted(names)              # same order whatever order the names come in
    assert nx.model_order(names, 2027) != o1 or len(names) < 3


def test_left_out_model_is_never_fetched():
    assert "GFDL-CM4_gr2" in nx.LEFT_OUT
    assert nx.eligible_models(["ACCESS-CM2", "GFDL-CM4", "GFDL-CM4_gr2"]) == ["ACCESS-CM2", "GFDL-CM4"]
