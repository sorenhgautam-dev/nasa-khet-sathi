"""GRACE/GRACE-FO JPL mascon CRI RL06.3 v4 (D5, D7): the monthly water-storage series for the grid cell
holding the field. Synthetic grids."""
import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import grace as gr


def _bounds(start, n, step=0.5):
    lo = start + step * np.arange(n)
    return np.stack([lo, lo + step], axis=1)


def test_the_cell_holding_the_field_is_found_with_0_to_360_longitudes():
    lat_b, lon_b = _bounds(-90, 360), _bounds(0, 720)
    i, j = gr.cell_index(27.6785, 85.427417, lat_b, lon_b)
    assert lat_b[i][0] <= 27.6785 < lat_b[i][1] and lon_b[j][0] <= 85.427417 < lon_b[j][1]
    i2, j2 = gr.cell_index(10.0, -75.2, lat_b, lon_b)                  # western longitudes wrap to 284.8
    assert lon_b[j2][0] <= 284.8 < lon_b[j2][1]


def test_series_turns_fills_into_gaps_and_dates_into_mid_month_days():
    t = np.array([105.5, 136.0, 166.5])                                 # days since 2002-01-01
    lwe = np.array([1.5, -99999.0, -2.0])
    s = gr.series(t, lwe, np.array([0.8, -99999.0, 0.9]), fill=-99999.0, valid=(-2305.0, 1273.7))
    assert list(s["date"]) == [pd.Timestamp("2002-04-16 12:00"), pd.Timestamp("2002-05-17"), pd.Timestamp("2002-06-16 12:00")]
    assert np.isnan(s["lwe_thickness_cm"].iloc[1]) and s["lwe_thickness_cm"].iloc[2] == -2.0


def test_values_outside_the_products_valid_range_fail_loudly():
    with pytest.raises(ValueError, match="valid range"):
        gr.series(np.array([105.5]), np.array([5000.0]), np.array([1.0]), fill=-99999.0, valid=(-2305.0, 1273.7))


def test_the_cri_scale_factor_is_recorded_with_its_reason_and_never_applied():
    """REVIEW_NOTES M4, owner 2026-11-12: the unscaled trend is the main number."""
    rec = gr.scale_factor_record(1.4945, trend_cm_per_year=-1.0)
    assert rec["value"] == pytest.approx(1.4945) and rec["applied"] is False
    assert "CLM" in rec["reason"] and "glaciers" in rec["reason"] and "no source" in rec["reason"]
    assert rec["trend_if_applied_cm_per_year"] == pytest.approx(-1.4945)       # for the record only


def test_the_trend_is_an_ordinary_least_squares_slope_in_cm_per_year():
    days = np.array([0.0, 365.25, 730.5, 1095.75])
    df = pd.DataFrame({"date": pd.Timestamp("2010-01-01") + pd.to_timedelta(days, unit="D"),
                       "lwe_thickness_cm": [10.0, 8.0, np.nan, 4.0]})              # a gap is skipped, not filled
    assert gr.linear_trend_cm_per_year(df) == pytest.approx(-2.0)


def _grace_file(path, lwe, factor=1.4945):
    import h5py
    lat_b, lon_b = _bounds(27.0, 2), _bounds(85.0, 2)
    n = len(lwe)
    with h5py.File(path, "w") as h:
        h.attrs["geospatial_lat_resolution"] = np.bytes_("0.5 degree grid; however the native resolution of the data is 3-degree equal-area mascons")
        t = h.create_dataset("time", data=np.array([105.5 + 30.4 * k for k in range(n)]))
        t.attrs["units"] = np.bytes_("days since 2002-01-01T00:00:00Z")
        for name, data, (lo, hi) in (("lwe_thickness", lwe, (-2305.0, 1273.7)), ("uncertainty", [1.0] * n, (0.2, 53.3))):
            arr = np.zeros((n, 2, 2))
            arr[:, 1, 0] = data                                                    # the field's cell
            v = h.create_dataset(name, data=arr)
            v.attrs["_FillValue"], v.attrs["units"] = np.array([-99999.0]), np.bytes_("cm")
            v.attrs["valid_min"], v.attrs["valid_max"] = np.array([lo]), np.array([hi])
        h.create_dataset("lat_bounds", data=lat_b)
        h.create_dataset("lon_bounds", data=lon_b)
        h.create_dataset("mascon_ID", data=np.full((2, 2), 1213.0))
        h.create_dataset("land_mask", data=np.ones((2, 2)))
        h.create_dataset("scale_factor", data=np.full((2, 2), factor))
    return path


def test_a_cached_file_gives_the_unscaled_series_and_a_card_with_the_factor_not_applied(tmp_path):
    import json
    raw = tmp_path / "raw" / "grace" / "t"
    raw.mkdir(parents=True)
    _grace_file(raw / "GRCTellus.JPL.200204_200208.GLO.RL06.3M.MSCNv04CRI.nc", [3.0, 2.0, 1.0, 0.0, -1.0])
    (tmp_path / "clean" / "t").mkdir(parents=True)
    r = gr.fetch({"id": "t", "lat": 27.69, "lon": 85.44}, data_dir=tmp_path)
    df = pd.read_parquet(r["table"])
    assert "lwe_thickness_scaled_cm" not in df.columns and list(df["lwe_thickness_cm"]) == [3.0, 2.0, 1.0, 0.0, -1.0]
    card = json.loads(r["card"].read_text())
    cri = card["location"]["cell"]["cri_scale_factor"]
    assert cri["value"] == pytest.approx(1.4945) and cri["applied"] is False and "CLM" in cri["reason"]
    assert card["scale_factor"] is None and "not applied" in card["notes"] and "applied for the trend" not in card["notes"]
    trend = card["location"]["cell"]["trend_unscaled_cm_per_year"]
    assert trend == pytest.approx(-12.0, rel=0.01)                                  # -1 cm per 30.4 days
    assert cri["trend_if_applied_cm_per_year"] == pytest.approx(trend * 1.4945)


def test_the_regional_caveat_is_a_sourced_rule():
    from pipeline.fetch.rules import load_rules
    c = load_rules()["groundwater"]["caveat"].lower()
    assert all(w in c for w in ("regional", "hundreds of km", "glaciers", "plains", "not the field"))
