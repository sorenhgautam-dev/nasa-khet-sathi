"""The independent checks of the twin (rules.yaml validation_checks; VALIDATION 4.2, 4.2c, 4.2d, 4.3): the pure parts of
pipeline/checks/ecostress_check.py, twin_vs_greenness.py, faostat_check.py and gldas_check.py, on small worked cases."""
import numpy as np
import pandas as pd
import pytest

from pipeline.checks import ecostress_check as ec
from pipeline.checks import faostat_check as fc
from pipeline.checks import gldas_check as gc
from pipeline.checks import twin_vs_greenness as tg

SEASONS = [{"crop": "rice", "start": "2019-06-23", "end": "2019-10-10", "year": 2019, "eta_over_etc": 1.0},
           {"crop": "potato", "start": "2019-10-30", "end": "2020-02-21", "year": 2020, "eta_over_etc": 0.5}]


# --- ECOSTRESS -----------------------------------------------------------------------------------------------------------
def test_season_esi_counts_and_averages_the_overpasses_inside_each_season():
    ov = pd.DataFrame({"local_date": pd.to_datetime(["2019-07-01", "2019-08-01", "2019-10-10", "2019-10-20", "2020-01-05"]),
                       "esi": [0.8, 0.6, 0.7, 0.1, 0.3]})
    s = ec.season_esi(ov, SEASONS)
    assert s.loc[0, "n_overpasses"] == 3 and s.loc[0, "esi_mean"] == pytest.approx(0.7)
    assert s.loc[1, "n_overpasses"] == 1 and s.loc[1, "esi_mean"] == pytest.approx(0.3)
    assert s.loc[1, "slot"] == "winter" and s.loc[0, "slot"] == "monsoon"


def test_a_slot_with_too_few_qualifying_seasons_is_not_testable():
    df = pd.DataFrame({"year": range(2018, 2026), "n_overpasses": [3, 2, 4, 1, 5, 3, 0, 2],
                       "esi_mean": np.linspace(0.3, 0.7, 8), "eta_over_etc": np.linspace(0.4, 0.8, 8)})
    r = ec.slot_result(df, min_overpasses=3, min_seasons=6)
    assert r["qualifying_seasons"] == 4 and r["holds_up"] is False and r["status"].startswith("not testable")


def test_a_degenerate_twin_slot_is_not_testable():
    df = pd.DataFrame({"year": range(2018, 2026), "n_overpasses": [5] * 8, "esi_mean": np.linspace(0.3, 0.7, 8),
                       "eta_over_etc": [1.0] * 6 + [0.99, 0.98]})
    r = ec.slot_result(df, min_overpasses=3, min_seasons=6)
    assert r["holds_up"] is False and "degenerate" in r["status"]


def test_a_clear_positive_slot_holds_up():
    df = pd.DataFrame({"year": range(2014, 2026), "n_overpasses": [4] * 12, "esi_mean": np.linspace(0.2, 0.8, 12),
                       "eta_over_etc": np.linspace(0.3, 0.9, 12) + np.r_[0.01, -0.01] .repeat(6)[:12] * 0})
    r = ec.slot_result(df, min_overpasses=3, min_seasons=6)
    assert r["holds_up"] is True and r["correlation"]["spearman"] == pytest.approx(1.0)


def test_overpass_day_pairs_esi_with_the_twins_daily_ks():
    ks = pd.Series([1.0, 0.5, 0.2, 0.9], index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-02-01", "2021-01-01"]))
    ov = pd.DataFrame({"local_date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-02-01", "2021-01-01", "2022-01-01"]),
                       "esi": [0.9, 0.4, 0.3, 0.8, 0.5]})
    p = ec.overpass_pairs(ov, ks)
    assert len(p) == 4 and p["ks"].tolist() == [1.0, 0.5, 0.2, 0.9]


# --- twin vs HLS -----------------------------------------------------------------------------------------------------------
def test_pairing_twin_seasons_with_satellite_seasons_by_slot_and_year():
    hls = {"2020": [{"start": "2020-01-11", "peak": "2020-03-17", "end": "2020-05-17", "peak_ndvi": 0.86, "source": "hls"},
                    {"start": "2020-06-11", "peak": "2020-08-09", "end": "2020-10-19", "peak_ndvi": 0.92, "source": "hls"}],
           "2019": [{"start": "2019-06-19", "peak": "2019-08-29", "end": "2019-10-31", "peak_ndvi": 0.88, "source": "hls"}],
           "2012": [{"start": "2012-06-16", "peak": "2012-09-06", "end": "2012-11-07", "peak_ndvi": 0.91, "source": "modis"}]}
    twin = [{"crop": "rice", "start": "2019-06-23", "end": "2019-10-10", "year": 2019, "eta_over_etc": 1.0, "dry_days": 0, "harvest_pct": 100.0},
            {"crop": "potato", "start": "2019-10-30", "end": "2020-02-21", "year": 2020, "eta_over_etc": 0.7, "dry_days": 86, "harvest_pct": 67.8},
            {"crop": "rice", "start": "2012-06-23", "end": "2012-10-10", "year": 2012, "eta_over_etc": 1.0, "dry_days": 0, "harvest_pct": 100.0}]
    df = tg.pair(twin, hls)
    assert sorted(zip(df["year"], df["slot"])) == [(2019, "monsoon"), (2020, "winter")]       # MODIS years are left out
    w = df[df["slot"] == "winter"].iloc[0]
    assert w["crop"] == "potato" and w["peak_ndvi"] == 0.86 and w["peak_anomaly"] == pytest.approx(0.0)


def test_metric_result_reports_the_expected_side():
    df = pd.DataFrame({"year": range(2014, 2026), "slot": "winter", "eta_over_etc": np.linspace(0.3, 0.7, 12),
                       "peak_anomaly": np.linspace(-0.03, 0.03, 12)})
    r = tg.metric_result(df, "eta_over_etc", sign=+1, min_seasons=8)
    assert r["agrees"] is True and r["correlation"]["n"] == 12
    r = tg.metric_result(df, "eta_over_etc", sign=-1, min_seasons=8)
    assert r["agrees"] is False


# --- FAOSTAT ---------------------------------------------------------------------------------------------------------------
def _row(item="116", name="Potatoes", year=2016, value=13000.0, unit="kg/ha", element="Yield", area="149"):
    return {"Area Code": area, "Item Code": item, "Item": name, "Element": element, "Year": str(year), "Unit": unit,
            "Value": str(value), "Flag": "A"}


def test_parse_items_keeps_nepal_yields_of_the_asked_items():
    rows = [_row(), _row(year=2017, value=13500.0), _row(item="27", name="Rice"), _row(area="100"), _row(element="Production")]
    df = fc.parse_items(rows, {"116": "potato"})
    assert df[["year", "crop", "yield_kg_ha"]].values.tolist() == [[2016, "potato", 13000.0], [2017, "potato", 13500.0]]


def test_first_differences_and_same_sign_share():
    years = [2002, 2003, 2004, 2005, 2006]
    fao = pd.Series([100.0, 110.0, 105.0, 120.0, 118.0], index=years)      # +10 -5 +15 -2
    twin = pd.Series([50.0, 60.0, 40.0, 45.0, 44.0], index=years)          # +10 -20 +5 -1
    r = fc.first_difference_check(fao, twin)
    assert r["years"] == [2003, 2004, 2005, 2006] and r["same_sign_share"] == 1.0
    assert r["correlation"]["n"] == 4


def test_a_degenerate_twin_crop_is_not_testable():
    years = list(range(2002, 2014))
    r = fc.first_difference_check(pd.Series(np.arange(12.0), index=years), pd.Series([100.0] * 10 + [99.7, 100.0], index=years))
    assert r["status"].startswith("not testable") and r["holds_up"] is False


# --- GLDAS -----------------------------------------------------------------------------------------------------------------
def test_twin_monthly_means_and_sums_over_complete_months():
    d = pd.DataFrame({"date": pd.date_range("2001-01-01", "2001-02-28", freq="D")})
    d["dr_mm"], d["taw_mm"], d["eta_mm"] = 25.0, 100.0, 2.0
    d.loc[d["date"] >= "2001-02-01", "dr_mm"] = 50.0
    m = gc.twin_monthly(d)
    assert m.loc[pd.Timestamp("2001-01-01"), "wetness"] == pytest.approx(0.75)
    assert m.loc[pd.Timestamp("2001-02-01"), "wetness"] == pytest.approx(0.5)
    assert m.loc[pd.Timestamp("2001-01-01"), "eta_mm"] == pytest.approx(62.0)


def test_monthly_comparison_uses_anomalies_and_year_blocks():
    idx = pd.date_range("2001-01-01", "2010-12-01", freq="MS")
    rng = np.random.default_rng(1)
    base = 10 * np.sin(2 * np.pi * idx.month / 12)                          # a shared seasonal cycle, removed by anomalies
    noise = rng.normal(0, 1, len(idx))
    a, b = pd.Series(base + noise, idx), pd.Series(base + noise + rng.normal(0, 0.1, len(idx)), idx)
    r = gc.compare_monthly(a, b, agree_r=0.3)
    assert r["months"] == 120 and r["pearson"] > 0.95 and r["holds_up"] is True
    c = pd.Series(base + rng.normal(0, 1, len(idx)), idx)                   # same cycle, unrelated anomalies
    r2 = gc.compare_monthly(a, c, agree_r=0.3)
    assert r2["holds_up"] is False and abs(r2["pearson"]) < 0.3
