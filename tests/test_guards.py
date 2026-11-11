"""Data guards (CLAUDE.md golden rule 12): print raw attributes, assert ranges, fail loudly, never
clip, and write a data card per dataset."""
import json
import logging

import numpy as np
import pandas as pd
import pytest

from pipeline.fetch import guards as g

# Ranges exactly as written in golden rule 12.
RULE_12 = [
    ("rain_mm", 0.0, 500.0),
    ("temp_c", -30.0, 50.0),
    ("ndvi", -1.0, 1.0),
    ("theta_m3m3", 0.0, 0.6),
    ("rh_pct", 0.0, 100.0),
]
IDS = [k for k, _, _ in RULE_12]


def test_ranges_are_exactly_golden_rule_12():
    assert g.RANGES == {k: (lo, hi) for k, lo, hi in RULE_12}


@pytest.mark.parametrize("kind,lo,hi", RULE_12, ids=IDS)
def test_values_on_the_edges_pass(kind, lo, hi):
    g.assert_in_range(np.array([lo, (lo + hi) / 2, hi]), kind, "col")


@pytest.mark.parametrize("kind,lo,hi", RULE_12, ids=IDS)
def test_value_below_range_fails_loudly(kind, lo, hi):
    with pytest.raises(g.DataGuardError, match="below"):
        g.assert_in_range(np.array([lo - 0.001, lo]), kind, "col")


@pytest.mark.parametrize("kind,lo,hi", RULE_12, ids=IDS)
def test_value_above_range_fails_loudly(kind, lo, hi):
    with pytest.raises(g.DataGuardError, match="above"):
        g.assert_in_range(np.array([hi, hi + 0.001]), kind, "col")


@pytest.mark.parametrize("kind,lo,hi", RULE_12, ids=IDS)
def test_out_of_range_values_are_never_clipped(kind, lo, hi):
    values = np.array([lo, hi + 1.0])
    before = values.copy()
    with pytest.raises(g.DataGuardError):
        g.assert_in_range(values, kind, "col")
    np.testing.assert_array_equal(values, before)


def test_error_names_the_column_the_count_and_the_worst_value():
    with pytest.raises(g.DataGuardError) as err:
        g.assert_in_range(pd.Series([10.0, 612.5, 501.0, 3.0]), "rain_mm", "rain_mm")
    msg = str(err.value)
    assert "rain_mm" in msg and "2 value" in msg and "612.5" in msg


def test_missing_values_are_allowed_by_the_range_check():
    g.assert_in_range(np.array([np.nan, 1.0]), "rain_mm", "rain_mm")


def test_infinite_values_fail():
    with pytest.raises(g.DataGuardError, match="infinite"):
        g.assert_in_range(np.array([np.inf, 1.0]), "rain_mm", "rain_mm")


def test_unknown_kind_fails():
    with pytest.raises(g.DataGuardError, match="no range"):
        g.assert_in_range(np.array([1.0]), "wind_ms", "ws2m_ms")


def test_check_table_checks_every_mapped_column():
    df = pd.DataFrame({"rain_mm": [0.0, 12.0], "tmax_c": [18.0, 31.0], "note": ["a", "b"]})
    assert g.check_table(df, {"rain_mm": "rain_mm", "tmax_c": "temp_c"}) == {"rain_mm": 0, "tmax_c": 0}


def test_check_table_uses_product_ranges_and_counts_warnings():
    df = pd.DataFrame({"theta_m3m3": [0.2, 0.7, 0.8]})
    warned = g.check_table(df, {"theta_m3m3": "theta_m3m3"}, valid_ranges={"theta_m3m3": (0.0, 0.9)})
    assert warned == {"theta_m3m3": 2}


def test_check_table_fails_on_a_bad_column():
    df = pd.DataFrame({"rain_mm": [0.0, 12.0], "tmax_c": [18.0, 60.0]})
    with pytest.raises(g.DataGuardError, match="tmax_c"):
        g.check_table(df, {"rain_mm": "rain_mm", "tmax_c": "temp_c"})


def test_check_table_fails_when_a_mapped_column_is_missing():
    with pytest.raises(g.DataGuardError, match="missing"):
        g.check_table(pd.DataFrame({"rain_mm": [1.0]}), {"tmin_c": "temp_c"})


# --- D2 (owner, 2026-11-11): the product's documented valid range is the hard limit; where it is
# wider than the rule-12 range, values beyond rule 12 are logged as warnings, not failures ---

SMAP_L4 = (0.0, 0.9)        # sm_rootzone valid range, CMR UMM-Var V3707348437-NSIDC_CPRD
MODIS_NDVI = (-0.2, 1.0)    # -2000..10000 x 0.0001, CMR UMM-Var V3143914093-LPCLOUD


def test_product_range_turns_a_rule_12_failure_into_a_warning():
    assert g.assert_in_range(np.array([0.3, 0.75]), "theta_m3m3", "sm_rootzone", valid_range=SMAP_L4) == 1


def test_value_outside_the_product_range_still_fails():
    with pytest.raises(g.DataGuardError, match="above"):
        g.assert_in_range(np.array([0.95]), "theta_m3m3", "sm_rootzone", valid_range=SMAP_L4)


def test_rule_12_warning_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="khet_sathi.guards"):
        g.assert_in_range(np.array([0.75]), "theta_m3m3", "sm_rootzone", valid_range=SMAP_L4)
    assert "sm_rootzone" in caplog.text and "0.6" in caplog.text


def test_no_warning_inside_the_rule_12_range(caplog):
    with caplog.at_level(logging.WARNING, logger="khet_sathi.guards"):
        assert g.assert_in_range(np.array([0.3]), "theta_m3m3", "sm", valid_range=SMAP_L4) == 0
    assert caplog.text == ""


def test_without_a_product_range_rule_12_is_the_hard_limit():
    with pytest.raises(g.DataGuardError):
        g.assert_in_range(np.array([0.75]), "theta_m3m3", "theta_m3m3")


def test_a_product_range_narrower_than_rule_12_is_enforced():
    with pytest.raises(g.DataGuardError, match="below"):
        g.assert_in_range(np.array([-0.5]), "ndvi", "modis_ndvi", valid_range=MODIS_NDVI)


def test_scaled_range_converts_a_raw_documented_range():
    assert g.scaled_range((-2000, 10000), 0.0001) == pytest.approx(MODIS_NDVI)


def test_scaled_range_applies_offset():
    assert g.scaled_range((0, 100), 0.5, add_offset=10) == pytest.approx((10, 60))


def test_nonnegative_passes_zero_and_nan():
    g.assert_nonnegative(np.array([0.0, 3.2, np.nan]), "ws2m_ms")


def test_nonnegative_fails_loudly_on_a_negative_value():
    with pytest.raises(g.DataGuardError, match="ws2m_ms"):
        g.assert_nonnegative(np.array([1.0, -0.1]), "ws2m_ms")


# --- fill values ---

def test_mask_fill_counts_and_removes_fill_values_without_touching_the_input():
    raw = np.array([1.0, -9999.0, 3.0, -9999.0])
    before = raw.copy()
    masked, n_removed = g.mask_fill(raw, [-9999.0])
    assert n_removed == 2
    assert np.isnan(masked[[1, 3]]).all() and masked[0] == 1.0
    np.testing.assert_array_equal(raw, before)


@pytest.mark.parametrize("documented_fill", [-9999.9, -9999.900390625])
def test_mask_fill_matches_a_float32_fill_however_it_is_written(documented_fill):
    # GPM IMERG stores _FillValue as float32 -9999.9 (= -9999.900390625 in float64).
    raw = np.array([-9999.9, 2.0], dtype=np.float32)
    _, n_removed = g.mask_fill(raw, [documented_fill])
    assert n_removed == 1


# --- raw attributes ---

def test_describe_raw_attrs_reports_all_five_and_marks_absent_ones():
    # xarray moves scale_factor/_FillValue from attrs into encoding when it decodes a file.
    out = g.describe_raw_attrs({"units": "mm/day", "_FillValue": -9999.9}, {"scale_factor": 0.0001})
    assert out == {"units": "mm/day", "scale_factor": 0.0001, "add_offset": "ABSENT",
                   "_FillValue": -9999.9, "valid_range": "ABSENT"}


def test_describe_raw_attrs_builds_valid_range_from_min_and_max():
    out = g.describe_raw_attrs({"valid_min": -2000, "valid_max": 10000})
    assert out["valid_range"] == [-2000, 10000]


# --- data cards ---

def _card(**over):
    card = dict(
        dataset="power", product="NASA POWER Daily API, community AG", version="v2.10.3",
        variable="PRECTOTCORR", units_in="mm/day", units_out="rain_mm (mm per day)",
        scale_factor=None, fill_values_removed={"-999": 0}, quality_flags_used="none provided",
        records_dropped=0, date_range=["2001-01-01", "2025-12-31"], time_zone="LST",
        pixel_count=1, source="NASA POWER", resolution="0.5 x 0.625 deg",
        raw_attrs={"units": "mm/day", "scale_factor": "ABSENT", "add_offset": "ABSENT",
                   "_FillValue": -999.0, "valid_range": "ABSENT"},
    )
    card.update(over)
    return card


def test_make_card_accepts_a_complete_card():
    assert g.make_card(**_card())["dataset"] == "power"


@pytest.mark.parametrize("missing", g.CARD_FIELDS)
def test_make_card_refuses_a_card_with_a_missing_field(missing):
    c = _card()
    del c[missing]
    with pytest.raises(g.DataGuardError, match=missing):
        g.make_card(**c)


def test_make_card_records_a_product_switch():
    # D1: IMERG Final to 2025-09-30, then Late; the card must show the switch.
    segs = [{"product": "GPM_3IMERGDF", "version": "07", "from": "2001-01-01", "to": "2025-09-30"},
            {"product": "GPM_3IMERGDL", "version": "07", "from": "2025-10-01", "to": "2025-12-31"}]
    card = g.make_card(**_card(segments=segs, range_warnings={"rain_mm": 0}))
    assert card["segments"] == segs and card["range_warnings"] == {"rain_mm": 0}


def test_make_card_refuses_unknown_fields():
    with pytest.raises(g.DataGuardError, match="unknown"):
        g.make_card(**_card(colour="blue"))


def test_write_card_writes_json_named_after_the_dataset(tmp_path):
    card = g.make_card(**_card())
    path = g.write_card(card, tmp_path)
    assert path == tmp_path / "power.json"
    assert json.loads(path.read_text()) == card
