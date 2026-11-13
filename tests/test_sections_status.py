"""pipeline/sections/status.py (build step 8): a section's status and wetness from the twin's state (rules.yaml
sections.status_red_ks_below). FAO-56 eq. 84: Ks = (TAW - Dr) / ((1 - p) TAW) = (TAW - Dr) / (TAW - RAW)."""
import math

import pytest

from pipeline.fetch.rules import load_rules
from pipeline.sections import status as st

TAW, RAW = 150.0, 30.0           # p = 0.2


def test_ks_worked_numbers():
    assert st.ks(20.0, TAW, RAW) == 1.0
    assert st.ks(30.0, TAW, RAW) == 1.0                    # at RAW: no stress yet
    assert st.ks(90.0, TAW, RAW) == pytest.approx(0.5)     # 60 / 120
    assert st.ks(100.0, TAW, RAW) == pytest.approx(50.0 / 120.0)
    assert st.ks(150.0, TAW, RAW) == 0.0


def test_wetness_worked_numbers():
    assert st.wetness_pct(0.0, TAW) == 100.0
    assert st.wetness_pct(20.0, TAW) == pytest.approx(86.6667, abs=1e-4)
    assert st.wetness_pct(150.0, TAW) == 0.0


def test_status_cuts():
    red = load_rules()["sections"]["status_red_ks_below"]
    assert red == 0.5
    assert st.status(20.0, TAW, RAW, red) == "green"
    assert st.status(30.0, TAW, RAW, red) == "green"
    assert st.status(90.0, TAW, RAW, red) == "yellow"      # Ks 0.5 is not below 0.5
    assert st.status(100.0, TAW, RAW, red) == "red"
    assert st.status(None, TAW, RAW, red) == "grey" and st.status(math.nan, TAW, RAW, red) == "grey"


@pytest.mark.parametrize("dr, taw, raw", [(151.0, 150.0, 30.0), (-1.0, 150.0, 30.0), (10.0, 150.0, 160.0), (0.0, 0.0, 0.0)])
def test_impossible_bucket_values_fail_loudly(dr, taw, raw):
    with pytest.raises(ValueError):
        st.status(dr, taw, raw, 0.5)


def test_from_twin_state_checks_the_file_against_itself():
    state = {"dr_mm": 100.0, "taw_mm": TAW, "raw_mm": RAW, "ks": 0.4167, "wetness_pct": 33.3, "date": "2025-12-31"}
    r = st.from_twin_state(state, 0.5)
    assert r["status"] == "red" and r["wetness_pct"] == pytest.approx(33.3333, abs=1e-3) and r["ks"] == pytest.approx(0.41667, abs=1e-4)
    with pytest.raises(ValueError, match="ks"):
        st.from_twin_state({**state, "ks": 0.9}, 0.5)
    with pytest.raises(ValueError, match="wetness"):
        st.from_twin_state({**state, "wetness_pct": 70.0}, 0.5)
    assert st.from_twin_state(None, 0.5) == {"status": "grey", "wetness_pct": None, "ks": None}
