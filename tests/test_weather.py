"""The twin's daily weather table: POWER, corrected from a nearby station when the field has one
(decision A, applied before ET0 and frost), rain from GPM with POWER as fill-in only (D), spike flags
written into the data cards (B), and ET0 (step 3). Synthetic inputs."""
import json

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import guards as g
from pipeline.fetch import weather as w
from pipeline.fetch.rules import load_rules
from pipeline.twin import inputs
from pipeline.twin.et0 import et0_mm

ST = "NP000444540"
LABEL = "Kathmandu-valley correction"


def _inputs(tmp_path):
    dates = pd.date_range("2015-01-01", "2022-12-31")
    doy = dates.day_of_year.to_numpy()
    st_tmin = 6 + 10 * np.sin(2 * np.pi * (doy - 80) / 365)
    st_tmax = st_tmin + 11
    jan = dates.month == 1
    power = pd.DataFrame({"date": dates, "tmax_c": st_tmax + 0.1, "tmin_c": st_tmin + np.where(jan, 3.8, 0.5),
                          "rh_pct": 60.0, "ws2m_ms": 1.5, "rs_mj_m2_day": 15.0, "rain_mm": 2.0})
    station = pd.DataFrame({"date": dates, "rain_mm": 2.0, "tmax_c": st_tmax, "tmin_c": st_tmin})
    spike = dates == pd.Timestamp("2019-03-01")
    power.loc[spike, "rain_mm"] = 233.7
    station.loc[spike, "rain_mm"] = 3.8
    clean = tmp_path / "clean" / "demo"
    clean.mkdir(parents=True)
    power.to_parquet(clean / "power.parquet", index=False)
    station.to_parquet(clean / f"ghcn_{ST}.parquet", index=False)
    card = dict(dataset="power", product="p", version="v", variable=[], units_in={}, units_out={},
                scale_factor=None, fill_values_removed={}, quality_flags_used="", records_dropped=0,
                date_range=["2015-01-01", "2022-12-31"], time_zone="LST", pixel_count=1, source="NASA POWER",
                resolution="r", raw_attrs={}, location={"lat": 27.67, "lon": 85.43, "elevation_m": 1269.39})
    g.write_card(g.make_card(**card), tmp_path / "cards" / "demo")
    return tmp_path


FIELD = {"id": "demo", "lat": 27.67, "lon": 85.43, "elevation_m": None,
         "validation_station": ST, "correction_label": LABEL}


@pytest.fixture
def built(tmp_path):
    data = _inputs(tmp_path)
    out = w.build(FIELD, data_dir=data, rules=load_rules())
    return data, pd.read_parquet(out["table"]), json.loads(out["card"].read_text())


def test_january_minimum_is_corrected_toward_the_station(built):
    data, df, _ = built
    st = pd.read_parquet(data / "clean" / "demo" / f"ghcn_{ST}.parquet")
    jan = df["date"].dt.month == 1
    assert (df.loc[jan, "tmin_c"] - st.loc[jan, "tmin_c"]).abs().max() < 1e-6
    assert df.loc[jan, "tmin_corrected"].all()
    assert (df.loc[jan, "tmin_c_power"] - df.loc[jan, "tmin_c"]).mean() == pytest.approx(3.8)


def test_the_card_labels_the_correction_and_reports_held_out_error(built):
    _, _, card = built
    c = card["corrections"]["tmin_c"]
    assert c["label"] == f"{LABEL} (station {ST})" and c["applied"] is True
    assert c["test"]["mae_after"] < c["test"]["mae_before"]


def test_cold_nights_record_the_comparison_and_each_method_s_role(built):
    _, _, card = built
    c = card["corrections"]["tmin_c"]
    for method in ("offset", "qmap"):
        assert {"mae", "jan_coldest_error", "nights_below_abs_diff"} <= set(c["cold_night_comparison"][method])
    assert c["roles"] == {"temperature_and_et0": "monthly offset", "frost": "quantile mapping"}
    assert "risk bands" in c["frost caveat"] and "never" in c["frost caveat"]


def test_frost_tmin_is_quantile_mapped_while_et0_tmin_keeps_the_offset(built):
    data, df, _ = built
    st = pd.read_parquet(data / "clean" / "demo" / f"ghcn_{ST}.parquet")
    jan = df["date"].dt.month == 1
    assert (df.loc[jan, "tmin_frost_c"] - st.loc[jan, "tmin_c"]).abs().max() < 1e-6   # pure shift: QM is exact too
    assert df.loc[jan, "tmin_frost_corrected"].all()


def test_without_a_station_frost_tmin_is_uncorrected_power(tmp_path):
    data = _inputs(tmp_path)
    field = {k: v for k, v in FIELD.items() if k not in ("validation_station", "correction_label")}
    df = pd.read_parquet(w.build(field, data_dir=data, rules=load_rules())["table"])
    assert (df["tmin_frost_c"] == df["tmin_c_power"]).all() and not df["tmin_frost_corrected"].any()


def test_humidity_check_is_reported_as_not_possible_without_station_humidity(built):
    _, _, card = built
    assert "not possible" in card["corrections"]["rh_pct"]["status"]


def test_rain_stays_missing_until_gpm_exists(built):
    _, df, card = built
    assert df["rain_mm"].isna().all() and set(df["rain_source"]) == {"missing"}
    assert "GPM" in card["notes"]


def test_spike_is_written_to_the_weather_and_power_cards(built):
    data, _, card = built
    assert [f["date"] for f in card["cross_source_flags"]] == ["2019-03-01"]
    power_card = json.loads((data / "cards" / "demo" / "power.json").read_text())
    assert power_card["cross_source_flags"][0]["high_source"] == "power"


def test_et0_uses_corrected_temperature_and_records_the_elevation_used(built):
    _, df, card = built
    assert (df["et0_mm"] > 0).all()
    assert card["location"]["elevation_m"] == 1269.39 and "POWER cell" in card["location"]["elevation_source"]


def test_once_gpm_exists_the_three_sources_vote_and_gpm_supplies_the_rain(tmp_path):
    data = _inputs(tmp_path)
    dates = pd.date_range("2015-01-01", "2022-12-31")
    gpm = pd.DataFrame({"date": dates, "rain_mm": 2.0, "product": "final"})
    gpm.loc[dates == pd.Timestamp("2019-03-01"), "rain_mm"] = 4.0        # GPM sides with the station
    gpm.to_parquet(data / "clean" / "demo" / "gpm.parquet", index=False)
    _gpm_card(data, FIELD["lat"], FIELD["lon"])
    out = w.build(FIELD, data_dir=data, rules=load_rules())
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    assert set(df["rain_source"]) == {"gpm"}
    spike = [f for f in card["cross_source_flags"] if f["date"] == "2019-03-01" and f["low_source"] == "station"]
    assert spike[0]["vote"]["label"] == "POWER spike"


def test_without_a_station_power_is_used_uncorrected_and_labelled(tmp_path):
    data = _inputs(tmp_path)
    field = {k: v for k, v in FIELD.items() if k not in ("validation_station", "correction_label")}
    out = w.build(field, data_dir=data, rules=load_rules())
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    assert (df["tmin_c"] == df["tmin_c_power"]).all() and not df["tmin_corrected"].any()
    assert card["corrections"]["tmin_c"]["label"] == "uncorrected POWER (no nearby station)"


def _gpm_card(data, lat, lon):
    """A GPM card as pipeline/fetch/gpm.py writes it: box cell centres and the field's cell within the box."""
    from pipeline.fetch import gpm
    i, j = gpm.cell_index(lat, lon)
    lons, lats = gpm.cell_centres(i - 1, i + 1, j - 1, j + 1)
    card = dict(dataset="gpm", product="GPM IMERG daily", version="V07 (GPM_3IMERGDF Final, then GPM_3IMERGDL Late)",
                variable="precipitation", units_in="mm/day",
                units_out="rain_mm", scale_factor=None, fill_values_removed={}, quality_flags_used="",
                records_dropped=0, date_range=["2015-01-01", "2022-12-31"], time_zone="UTC", pixel_count=9,
                source="Huffman et al., GPM IMERG Final/Late Precipitation L3 1 day 0.1 degree V07, NASA GES DISC",
                resolution="0.1 deg (about 10 km); the field's cell and the box mean", raw_attrs={},
                location={"box_cells_lon": lons, "box_cells_lat": lats, "field_cell": [1, 1]})
    g.write_card(g.make_card(**card), data / "cards" / "demo")


def _gpm_rain(data):
    gpm = pd.DataFrame({"date": pd.date_range("2015-01-01", "2022-12-31"), "rain_mm": 2.0, "product": "final"})
    gpm.to_parquet(data / "clean" / "demo" / "gpm.parquet", index=False)


def test_gpm_rain_fetched_for_another_cell_stops_the_build(tmp_path):
    """REVIEW_NOTES H3: gpm.parquet holds the cell the field was in at fetch time; a moved field must not use it."""
    data = _inputs(tmp_path)
    _gpm_rain(data)
    _gpm_card(data, FIELD["lat"] + 0.25, FIELD["lon"])                  # two cells north of the field
    with pytest.raises(ValueError, match="GPM"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def test_gpm_rain_without_its_card_stops_the_build(tmp_path):
    data = _inputs(tmp_path)
    _gpm_rain(data)
    with pytest.raises(ValueError, match="GPM"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def _gpm_with_gaps(data, n_gaps, year=2018):
    """GPM rain on every day except `n_gaps` days of `year`, which POWER then fills."""
    dates = pd.date_range("2015-01-01", "2022-12-31")
    gpm = pd.DataFrame({"date": dates, "rain_mm": 2.0, "product": "final"})
    gpm.loc[gpm["date"].isin(pd.date_range(f"{year}-06-01", periods=n_gaps)), "rain_mm"] = np.nan
    gpm.to_parquet(data / "clean" / "demo" / "gpm.parquet", index=False)
    _gpm_card(data, FIELD["lat"], FIELD["lon"])


# ---- REVIEW_NOTES M6, owner decision 2026-11-12: hold ea from POWER, capped at e0 of the corrected Tmin ----

def test_ea_is_held_from_power_and_capped_at_e0_of_the_corrected_tmin():
    """Worked numbers; e0 as in FAO-56 Annex 2 Table 2.3: e0(25 C) 3.168, e0(15 C) 1.705, e0(11 C) 1.312 kPa.
    POWER 25 / 15 C, corrected Tmin 11 C. RH 60 %: ea = 0.60 x (3.168 + 1.705) / 2 = 1.462 kPa, above
    e0(11 C) = 1.312, so the cap binds. RH 50 %: ea = 0.50 x 2.437 = 1.218 kPa, under the cap, kept. (RH held
    with corrected 26 / 11 C would give 0.50 x (3.361 + 1.312) / 2 = 1.168 kPa: ea falls with the correction.)"""
    ea, capped = inputs.ea_held_from_power_kpa([60.0, 50.0], [25.0, 25.0], [15.0, 15.0], [11.0, 11.0])
    assert ea == pytest.approx([1.312, 1.218], abs=1e-3)
    assert capped.tolist() == [True, False]


def test_et0_uses_power_ea_with_corrected_temperatures_and_keeps_the_rh_held_choice(built):
    _, df, _ = built
    ea, capped = inputs.ea_held_from_power_kpa(df["rh_pct"], df["tmax_c_power"], df["tmin_c_power"], df["tmin_c"])
    assert df["ea_kpa"].to_numpy() == pytest.approx(ea) and (df["ea_capped"].to_numpy() == capped).all()
    args = (df["tmax_c"], df["tmin_c"], df["ws2m_ms"], df["rs_mj_m2_day"], 1269.39, FIELD["lat"], df["date"].dt.day_of_year)
    assert df["et0_mm"].to_numpy() == pytest.approx(et0_mm(*args, ea=ea))
    assert df["et0_rh_held_mm"].to_numpy() == pytest.approx(et0_mm(*args, rh_mean=df["rh_pct"]))
    from pipeline.twin.et0 import ea_from_rhmean_kpa
    jan = (df["date"].dt.month == 1).to_numpy()
    rh_held_ea = ea_from_rhmean_kpa(df["rh_pct"], df["tmax_c"], df["tmin_c"])
    assert (df["ea_kpa"].to_numpy()[jan] > rh_held_ea[jan]).all()      # the January correction no longer dries the air
    assert not np.allclose(df["et0_mm"], df["et0_rh_held_mm"])


def test_et0_choice_summary_on_a_hand_example():
    """2019-2020 (365 + 366 days): et0_mm 2.0 a day, the RH-held ET0 1.5 a day except 4.0 on 2020-07-04.
    Annual means (730 + 732) / 2 = 731.0 and (547.5 + 549.0 - 1.5 + 4.0) / 2 = 549.5 mm. Mean daily
    difference: January 0.5; July (61 x 0.5 - 2.0) / 62 = 0.4597 mm. Largest: -2.0 mm on 2020-07-04."""
    dates = pd.date_range("2019-01-01", "2020-12-31")
    used = np.full(len(dates), 2.0)
    other = np.where(dates == pd.Timestamp("2020-07-04"), 4.0, 1.5)
    s = inputs.et0_choice_summary(dates, used, other, dates.month == 1)
    assert s["mean_annual_mm"] == {"et0_mm": pytest.approx(731.0), "et0_rh_held_mm": pytest.approx(549.5)}
    assert s["years"] == [2019, 2020]
    assert s["mean_daily_diff_mm_by_month"][1] == pytest.approx(0.5)
    assert s["mean_daily_diff_mm_by_month"][7] == pytest.approx(0.4597, abs=1e-4)
    assert s["largest_daily_diff"] == {"date": "2020-07-04", "diff_mm": pytest.approx(-2.0), "et0_mm": 2.0,
                                       "et0_rh_held_mm": 4.0}
    assert s["cap_days"] == 62 and s["cap_days_by_month"] == {1: 62}


def test_the_card_reports_both_et0_choices_and_the_days_the_cap_binds(built):
    _, df, card = built
    e = card["corrections"]["ea_kpa"]
    assert "POWER" in e["method"] and "capped" in e["method"]
    assert e["cap_days"] == int(df["ea_capped"].sum()) > 0
    annual = df.groupby(df["date"].dt.year)[["et0_mm", "et0_rh_held_mm"]].sum().mean()
    assert e["et0_compare"]["mean_annual_mm"]["et0_mm"] == pytest.approx(annual["et0_mm"])
    assert e["et0_compare"]["mean_annual_mm"]["et0_rh_held_mm"] == pytest.approx(annual["et0_rh_held_mm"])
    assert len(e["et0_compare"]["mean_daily_diff_mm_by_month"]) == 12
    assert {"date", "diff_mm"} <= set(e["et0_compare"]["largest_daily_diff"])


# ---- REVIEW_NOTES M8: a month without a fitted offset is reported loudly ----

def test_no_month_is_left_uncorrected_when_every_month_has_an_offset(built):
    _, _, card = built
    assert card["corrections"]["tmin_c"]["months_uncorrected"] == []
    assert card["corrections"]["tmax_c"]["months_uncorrected"] == []
    assert card["corrections"]["tmin_c"]["frost_months_uncorrected"] == []


def test_a_month_without_an_offset_is_named_in_a_warning_and_in_the_card(tmp_path, capsys):
    data = _inputs(tmp_path)
    p = data / "clean" / "demo" / f"ghcn_{ST}.parquet"
    st = pd.read_parquet(p)
    st[~((st["date"].dt.month == 2) & (st["date"].dt.day > 2))].to_parquet(p, index=False)   # 2 Feb days a year
    card = json.loads(w.build(FIELD, data_dir=data, rules=load_rules())["card"].read_text())
    assert card["corrections"]["tmin_c"]["months_uncorrected"] == [2]
    assert card["corrections"]["tmax_c"]["months_uncorrected"] == [2]
    assert card["corrections"]["tmin_c"]["frost_months_uncorrected"] == []     # quantile mapping falls back to DJF
    err = capsys.readouterr().err
    assert "WARNING" in err and "Feb" in err and "tmin_c" in err and "tmax_c" in err


# ---- REVIEW_NOTES M9: Tmin above Tmax, frost Tmin range, per-column source and resolution ----

def test_tmin_above_tmax_after_correction_fails_loudly(tmp_path):
    data = _inputs(tmp_path)
    p = data / "clean" / "demo" / "power.parquet"
    pw = pd.read_parquet(p)
    day = pw["date"] == pd.Timestamp("2018-06-10")
    pw.loc[day, "tmin_c"] = pw.loc[day, "tmax_c"] + 5.0
    pw.to_parquet(p, index=False)
    with pytest.raises(g.DataGuardError, match="tmin_c above tmax_c.*2018-06-10"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def test_frost_tmin_above_tmax_fails_loudly(tmp_path, monkeypatch):
    data = _inputs(tmp_path)
    monkeypatch.setattr(w.qmap, "apply_qmap", lambda df, col, models: df[col] + 15.0)
    with pytest.raises(g.DataGuardError, match="tmin_frost_c above tmax_c"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def test_frost_tmin_is_range_checked_like_tmin(tmp_path, monkeypatch):
    data = _inputs(tmp_path)
    monkeypatch.setattr(w.qmap, "apply_qmap", lambda df, col, models: df[col] - 40.0)
    with pytest.raises(g.DataGuardError, match="tmin_frost_c"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def test_the_card_records_that_no_day_has_tmin_above_tmax(built):
    _, df, card = built
    assert card["corrections"]["tmin_not_above_tmax"]["days"] == {"tmin_c": 0, "tmin_frost_c": 0}
    assert card["range_warnings"] == {"tmax_c": 0, "tmin_c": 0, "tmin_frost_c": 0}


def test_the_card_names_each_column_s_source_and_resolution(tmp_path):
    data = _inputs(tmp_path)
    _gpm_with_gaps(data, 3)
    out = w.build(FIELD, data_dir=data, rules=load_rules())
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    src, res = card["source"], card["resolution"]
    assert set(df.columns) - {"date"} <= set(src) and set(df.columns) - {"date"} <= set(res)
    assert "GPM IMERG" in src["rain_mm"] and "V07" in src["rain_mm"] and "POWER" in src["rain_mm"]
    assert "0.1 deg" in res["rain_mm"] and "0.5 x 0.625 deg" in res["rain_mm"]      # fill-in days: POWER's cell
    assert "NASA POWER" in src["tmin_c"] and ST in src["tmin_c"] and "0.5 x 0.625 deg" in res["tmin_c"]
    assert "quantile" in src["tmin_frost_c"] and "1 x 1 deg" in res["rs_mj_m2_day"]
    assert "model-based" in src["tmax_c"] and "model-based" in src["et0_mm"]


def test_without_gpm_the_card_says_rain_has_no_source(built):
    _, _, card = built
    assert "GPM not fetched" in card["source"]["rain_mm"]


# ---- REVIEW_NOTES M2: POWER may fill at most 5 % of any year's days (rules.yaml power_rain) ----

def test_power_filling_more_than_the_cap_in_a_year_fails_loudly(tmp_path):
    """19 of 2018's 365 days = 5.2 %, above 0.05."""
    data = _inputs(tmp_path)
    _gpm_with_gaps(data, 19)
    with pytest.raises(g.DataGuardError, match="2018: 19 of 365"):
        w.build(FIELD, data_dir=data, rules=load_rules())


def test_power_fill_at_the_cap_passes_and_is_counted_per_year(tmp_path):
    """18 of 365 days = 4.9 %: allowed, flagged, and counted in the card."""
    data = _inputs(tmp_path)
    _gpm_with_gaps(data, 18)
    out = w.build(FIELD, data_dir=data, rules=load_rules())
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    assert int(df["rain_filled"].sum()) == 18
    r = card["corrections"]["rain_mm"]
    assert r["max_filled_fraction_per_year"] == 0.05
    assert r["by_year"]["2018"] == {"days": 365, "filled": 18, "missing": 0, "fraction_filled": pytest.approx(18 / 365)}
    assert r["by_year"]["2017"]["filled"] == 0 and r["filled_outside_gpm_record"] == 0


# ---- GPM break correction (owner's decision 1, 2026-11-13; rules.yaml gpm_series) ----

def _gpm_stepped(data):
    """GPM 2 mm a day in 2015-2016 and 4 mm a day from 2017 (Final), the last quarter of 2022 from Late."""
    dates = pd.date_range("2015-01-01", "2022-12-31")
    gpm = pd.DataFrame({"date": dates, "rain_mm": np.where(dates.year >= 2017, 4.0, 2.0),
                        "product": np.where(dates >= pd.Timestamp("2022-10-01"), "late", "final")})
    gpm.to_parquet(data / "clean" / "demo" / "gpm.parquet", index=False)
    _gpm_card(data, FIELD["lat"], FIELD["lon"])


def test_final_rain_from_2017_is_scaled_back_and_the_uncorrected_rain_is_kept(tmp_path):
    """Factors 2/4 = 0.5 per month (February (56 + 57) / 2 / 112 over 2015-2016 vs 2017-2022: 0.504...), from Final
    days only; the Late days (Oct-Dec 2022) are left as they are."""
    data = _inputs(tmp_path)
    _gpm_stepped(data)
    out = w.build(FIELD, data_dir=data, rules=load_rules())
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    s = df.set_index("date")
    assert s.loc["2016-12-31", "rain_mm"] == 2.0 and s.loc["2017-07-01", "rain_mm"] == pytest.approx(2.0)
    assert s.loc["2017-07-01", "rain_uncorrected_mm"] == 4.0 and bool(s.loc["2017-07-01", "rain_break_corrected"])
    assert s.loc["2022-11-01", "rain_mm"] == 4.0 and not bool(s.loc["2022-11-01", "rain_break_corrected"])
    b = card["corrections"]["rain_break"]
    assert b["applied"] and b["factors_by_month"]["Jul"] == 0.5 and b["days_not_scaled_after_start"] == {"final": 0, "late": 92}
    assert "rain_uncorrected_mm" in card["source"] and "rain_break_corrected" in card["resolution"]


def test_a_field_without_a_rain_check_finding_is_not_corrected(tmp_path):
    data = _inputs(tmp_path)
    _gpm_stepped(data)
    rules = load_rules()
    rules["gpm_series"]["correction_fields"] = ["somewhere_else"]
    out = w.build(FIELD, data_dir=data, rules=rules)
    df, card = pd.read_parquet(out["table"]), json.loads(out["card"].read_text())
    assert (df["rain_mm"] == df["rain_uncorrected_mm"]).all() and not df["rain_break_corrected"].any()
    assert card["corrections"]["rain_break"]["applied"] is False
