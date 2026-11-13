"""ECOSTRESS cleaning (DATA_AUDIT 1.8's five traps; rules.yaml validation_checks.ecostress): pipeline/fetch/ecostress.py.
Worked examples: the file name, one granule per overpass, QC bits, cloud, the physical LST range, ESI, pixel shares."""
import numpy as np
import pandas as pd
import pytest
from affine import Affine

from pipeline.fetch import ecostress as eco
from pipeline.fetch.guards import DataGuardError


def test_parse_a_v002_and_a_v003_name():
    a = eco.parse_name("ECOv002_L2T_LSTE_03426_004_45RUL_20190212T035435_0712_02")
    assert a == {"version": "V002", "product": "L2T_LSTE", "orbit": "03426", "scene": "004", "tile": "45RUL",
                 "time_utc": pd.Timestamp("2019-02-12 03:54:35"), "build": "0712", "iteration": 2}
    b = eco.parse_name("ECOv003_L4T_ESI_42096_011_45RUL_20251208T103221_02")
    assert b["version"] == "V003" and b["build"] == "" and b["iteration"] == 2


def test_one_granule_per_overpass_latest_build_then_iteration():
    names = ["ECOv002_L2T_LSTE_27675_004_45RUL_20230524T094259_0710_01",
             "ECOv002_L2T_LSTE_27675_004_45RUL_20230524T094259_0711_02",
             "ECOv002_L2T_LSTE_03426_004_45RUL_20190212T035435_0712_01",
             "ECOv002_L2T_LSTE_03426_004_45RUL_20190212T035435_0712_03",
             "ECOv002_L2T_LSTE_03426_004_45RUL_20190212T035435_0712_02"]
    assert sorted(eco.latest_per_overpass(names)) == [names[3], names[1]]


def test_qc_best_quality_is_bits_1_0_equal_00():
    # 35520 = ...1100 0000 (bits 1-0 = 00); 17089 ends in 01 (degraded); 65535 every bit set; NaN no value
    assert eco.qc_best([35520, 17089, 65535, np.nan, 2496]).tolist() == [True, False, False, False, True]


def test_clean_lst_masks_then_checks_the_physical_range():
    lst_k = np.array([300.0, 14.6, 1305.8, 330.0, 250.0, np.nan])
    qc = np.array([0, 1, 1, 0, 0, 0])
    cloud = np.array([0, 0, 0, 0, 1, 0])
    c, n = eco.clean_lst(lst_k, qc, cloud)
    assert c[0] == pytest.approx(26.85) and c[3] == pytest.approx(56.85)
    assert np.isnan(c[[1, 2, 4, 5]]).all()
    assert n == {"no_value": 1, "qc_not_best": 2, "cloud": 1, "kept": 2, "rule12_warnings": 1}


def test_a_best_quality_clear_lst_outside_the_physical_range_fails_loudly():
    with pytest.raises(DataGuardError):
        eco.clean_lst(np.array([400.0]), np.array([0]), np.array([0]))           # 126.85 C


def test_clean_esi_needs_cloud_free_and_a_kept_lst():
    esi = np.array([0.5, 0.6, 0.7, np.nan])
    e, n = eco.clean_esi(esi, cloud=np.array([0, 1, 0, 0]), lst_kept=np.array([True, True, False, True]))
    assert e[0] == 0.5 and np.isnan(e[1:]).all()
    assert n == {"no_value": 1, "cloud": 1, "lst_not_kept": 1, "kept": 1}


def test_an_esi_above_one_fails_loudly():
    with pytest.raises(DataGuardError):
        eco.clean_esi(np.array([1.2]), cloud=np.array([0]), lst_kept=np.array([True]))


def test_pixel_shares_of_a_square_on_a_70_m_grid():
    # 2 x 2 grid of 70 m pixels from (0, 140); a 60 m square from x 35-95, y 35-95 (metres, the grid's own CRS)
    sq = {"type": "Polygon", "coordinates": [[(35, 35), (95, 35), (95, 95), (35, 95), (35, 35)]]}
    s = eco.pixel_shares(sq, Affine(70.0, 0, 0.0, 0, -70.0, 140.0), (2, 2))
    assert s[(0, 0)] == pytest.approx(875 / 4900, abs=1e-6)     # x 35-70, y 70-95
    assert s[(1, 0)] == pytest.approx(1225 / 4900, abs=1e-6)    # x 35-70, y 35-70
    assert s[(0, 1)] == pytest.approx(625 / 4900, abs=1e-6)
    assert s[(1, 1)] == pytest.approx(875 / 4900, abs=1e-6)


def test_local_date_is_utc_plus_0545():
    assert eco.local_date(pd.Timestamp("2019-02-12 20:00:00")) == pd.Timestamp("2019-02-13")
    assert eco.local_date(pd.Timestamp("2019-02-12 03:54:35")) == pd.Timestamp("2019-02-12")
