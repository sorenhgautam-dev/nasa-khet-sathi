"""Area map of the demo box (Local Impact 4a; rules.yaml area_map, committed before the first run in cb85cc8).
Every function is checked on a worked number, and the per-pixel path against the field diary's own functions."""
import numpy as np
import pandas as pd
import pytest
from rasterio.transform import from_origin

from pipeline.area import pixels as px
from pipeline.area import render as rd
from pipeline.area import stats as st
from pipeline.diary import greenness as gr
from pipeline.diary import seasons as se

S = {"smooth_window_days": 31, "smooth_polyorder": 2, "min_amplitude": 0.1, "min_amplitude_range_fraction": 0.35,
     "min_amplitude_range_years": 3, "threshold_fraction": 0.2}


# ---------- cropland on the 30 m grid ----------

def test_cropland_fraction_counts_the_10m_centres_inside_each_30m_pixel():
    """3 x 3 ten-metre pixels in each 30 m pixel; 5 of the 9 in the first are cropland -> 5/9."""
    wc = np.zeros((6, 6), np.uint8) + 30
    wc[0, 0:3] = 40; wc[1, 0:2] = 40                     # 5 cropland centres in the top-left 30 m pixel
    wc[3:6, 3:6] = 40                                    # bottom-right 30 m pixel all cropland
    t10 = from_origin(500000, 3060000, 10, 10)
    t30 = from_origin(500000, 3060000, 30, 30)
    frac, n = px.cropland_fraction(wc, t10, "EPSG:32645", (2, 2), t30, "EPSG:32645", 40)
    assert n.tolist() == [[9, 9], [9, 9]]
    assert frac[0, 0] == pytest.approx(5 / 9) and frac[1, 1] == 1.0 and frac[0, 1] == 0.0


def test_cropland_rule_needs_coverage_and_a_majority():
    frac = np.array([[0.5, 0.49], [1.0, 1.0]])
    n = np.array([[12, 12], [12, 5]])                     # 5 of an expected 11.8 centres: outside the box
    assert px.cropland_mask(frac, n, expected=11.8, min_fraction=0.5, min_coverage=0.5).tolist() == [[True, False], [True, False]]


def test_expected_worldcover_centres_in_a_30m_pixel_at_the_box():
    """1/12000 deg pixels at 27.67 N: 9.266 m x 8.205 m -> 900 / 76.03 = 11.84 centres."""
    t = from_origin(85.38, 27.71, 1 / 12000, 1 / 12000)
    assert px.expected_centres(t, 27.67, 30) == pytest.approx(11.84, abs=0.01)


# ---------- the field diary's series, per pixel ----------

def _random_obs(rng, n_pix, start, end, n_obs):
    days = pd.date_range(start, end)
    d = np.sort(rng.choice(days.to_numpy(), n_obs))       # repeats = same-day granules
    v = rng.uniform(0.05, 0.9, (n_obs, n_pix)).round(4)
    v[rng.random((n_obs, n_pix)) < 0.4] = np.nan          # clouds
    return pd.DatetimeIndex(d), v


def test_daily_matrix_equals_the_diary_series_for_every_pixel():
    rng = np.random.default_rng(3)
    dates, v = _random_obs(rng, 7, "2014-01-01", "2016-12-31", 140)
    start, end = "2014-01-01", "2016-12-31"
    udays, mean = px.same_day_mean(dates, v)
    daily = px.daily_matrix(udays, mean, start, end)
    for p in range(v.shape[1]):
        ref = gr.daily_series(pd.DataFrame({"date": dates, "ndvi": v[:, p]}), start, end)["ndvi"].to_numpy()
        np.testing.assert_array_equal(daily[:, p], ref)     # bit for bit, NaN outside the first and last clear day


def test_yearly_counts_worked_number_and_the_diary_rule():
    """0.10 on 1 Jan, 0.30 on 11 Jan: 0.10 + 0.02 x day, below 0.25 on days 0-7 -> 8 bare days of 11 with a value."""
    daily = px.daily_matrix(pd.DatetimeIndex(["2020-01-01", "2020-01-11"]), np.array([[0.10], [0.30]]),
                            "2020-01-01", "2020-12-31")
    bare, has = px.yearly_counts(daily, pd.date_range("2020-01-01", "2020-12-31"), [2020], 0.25)
    assert bare.tolist() == [[8]] and has.tolist() == [[11]]
    ref = gr.bare_days(pd.DataFrame({"date": pd.date_range("2020-01-01", "2020-12-31"), "ndvi": daily[:, 0],
                                     "gap_days": 0}), 0.25, 20)["by_year"]["2020"]
    assert (ref["bare_days"], ref["days_with_value"]) == (8, 11)


def test_pixel_seasons_are_the_threshold_method_counted_by_peak_year():
    days = pd.date_range("2014-01-01", "2017-12-31")
    t = np.arange(len(days))
    ndvi = 0.45 + 0.3 * np.cos(2 * np.pi * (t - 60) / 182.6)      # two seasons a year
    peaks = px.pixel_season_peak_years(days, ndvi, S)
    sm = se.smooth(ndvi, 31, 2)
    ref = se.threshold_seasons(days, sm, 0.1, 0.2, 0.35, 3)
    assert peaks == [s["peak"].year for s in ref]
    assert px.count_by_year(peaks, [2015, 2016]) == [2, 2]


def test_pixel_seasons_skip_days_without_a_value():
    days = pd.date_range("2014-01-01", "2016-12-31")
    ndvi = 0.45 + 0.3 * np.cos(2 * np.pi * (np.arange(len(days)) - 60) / 182.6)
    ndvi[:40] = np.nan
    ref = se.threshold_seasons(days[40:], se.smooth(ndvi[40:], 31, 2), 0.1, 0.2, 0.35, 3)
    assert px.pixel_season_peak_years(days, ndvi, S) == [s["peak"].year for s in ref]
    assert px.pixel_season_peak_years(days, np.full(len(days), np.nan), S) == []


# ---------- area numbers ----------

def test_mean_over_counted_years_needs_min_years():
    vals = np.array([[10, 20], [30, 99], [50, 40]], float)            # years x pixels
    ok = np.array([[True, True], [True, False], [True, False]])
    m = st.mean_over_counted(vals, ok, min_years=2)
    assert m[0] == 30 and np.isnan(m[1])


def test_season_class_rounds_halves_up_and_caps_at_three():
    assert st.season_class(np.array([0.49, 0.5, 1.49, 1.5, 2.49, 2.5, 4.0, np.nan])).tolist() == [0, 1, 1, 2, 2, 3, 3, -1]


def test_bare_class_breaks():
    assert st.bare_class(np.array([0, 29.9, 30, 60, 89, 120, 300, np.nan]), [30, 60, 90, 120]).tolist() == [0, 0, 1, 2, 2, 4, 4, -1]


def test_worldcover_bound_worked_numbers():
    """c = 1 - (80.6 - 2.8) / 100 = 0.222; s = 0.5 -> [0.278 / 0.778, 0.5 / 0.778] = [0.357, 0.643]."""
    c = st.commission(80.6, 2.8)
    assert c == pytest.approx(0.222)
    lo, hi = st.share_bound(0.5, c)
    assert (lo, hi) == (pytest.approx(0.35733, abs=1e-5), pytest.approx(0.64267, abs=1e-5))
    assert st.share_bound(0.1, c)[0] == 0.0 and st.share_bound(0.9, c)[1] == 1.0
    v = np.arange(1, 1001, dtype=float)                                # quantiles 0.389 and 0.611 of 1..1000
    lo, hi = st.median_bound(v, c)
    assert lo == pytest.approx(np.quantile(v, 0.389)) and hi == pytest.approx(np.quantile(v, 0.611))


# ---------- the PNG layers ----------

def test_mercator_grid_spans_the_box_exactly():
    box = [85.379227, 27.625034, 85.480773, 27.714966]
    t, w, h = rd.mercator_grid(box, 15)
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:3857", "EPSG:4326", [t.c, t.c + t.a * w], [t.f, t.f + t.e * h])
    assert xs == pytest.approx([box[0], box[2]], abs=1e-9) and ys == pytest.approx([box[3], box[1]], abs=1e-9)
    assert 600 < w < 760 and 600 < h < 760                              # about 10 km at about 15 m


def test_png_is_a_palette_image_with_transparent_non_cropland(tmp_path):
    from PIL import Image
    cls = np.array([[-2, 0, 1], [2, -1, 3]])                            # -2 not cropland, -1 not enough data
    path = tmp_path / "x.png"
    rd.write_png(cls, ["#edf8e9", "#bae4b3", "#74c476", "#238b45"], "#969696", path)
    im = Image.open(path)
    assert im.mode == "P"
    rgba = np.asarray(im.convert("RGBA"))
    assert rgba[0, 0, 3] == 0 and tuple(rgba[0, 1]) == (0xed, 0xf8, 0xe9, 255)
    assert tuple(rgba[1, 1]) == (0x96, 0x96, 0x96, 255) and tuple(rgba[1, 2][:3]) == (0x23, 0x8b, 0x45)


# ---------- the written site files (skipped until scripts/run_area_map.py has run) ----------

SITE = __import__("pathlib").Path(__file__).resolve().parents[1] / "site" / "data" / "area"


@pytest.mark.skipif(not (SITE / "demo.json").exists(), reason="run scripts/run_area_map.py first")
def test_site_area_file_is_small_plain_and_labelled():
    import json
    from pipeline.fetch.fields import load_field
    from pipeline.fetch.rules import load_rules
    d = json.loads((SITE / "demo.json").read_text())
    box = load_field("demo")["fetch_box"]
    K = load_rules()["area_map"]["classes"]
    assert d["bounds"] == [[box[1], box[0]], [box[3], box[2]]] and d["placeholder"] is True
    assert d["ne_status"] == "needs native-speaker review"
    lines = [d["layers"][i]["title"]["en"] for i in range(2)] + d["layers"][0]["legend"]["en"]
    lines += [c["en"] for lay in d["layers"] for c in lay["classes"]] + [x for n in d["numbers"] for x in n["en"]]
    assert all(len(x.split()) <= 8 for x in lines), [x for x in lines if len(x.split()) > 8]
    assert [c["colour"] for c in d["layers"][0]["classes"]] == K["bare_days_colours"]
    assert [c["colour"] for c in d["layers"][1]["classes"]] == K["seasons_colours"]
    for lay in d["layers"]:
        assert (SITE / lay["image"]).stat().st_size < 100_000
    assert all(n["low"] <= n["value"] <= n["high"] for n in d["numbers"])
    assert {s["type"] for s in d["sources"]} <= {"satellite", "model", "station", "probe"}
