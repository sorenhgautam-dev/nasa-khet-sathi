"""The current plan's options (owner's answer 6 to REVIEW_2, 2026-11-13; rules.yaml plans.current_options):
pipeline/plans/options.py. The farmer confirms the winter crop; a crop the default rotation does not grow is sown on
the date whose simulated season lies closest to the season the satellite sees."""
import json

import pandas as pd
import pytest

from pipeline.plans import generate as ge
from pipeline.plans import options as po

LIB = json.load(open("config/crops.json"))["crops"]
POSITIONS = ("start", "middle", "end")
DEFAULT = ge.ordered([{"crop": "rice", "window": 1, "position": "middle"}, {"crop": "potato", "window": 0, "position": "middle"}], LIB)


def _winters(start="01-07", end="05-18", years=range(2014, 2026)):
    return [{"start": pd.Timestamp(f"{y}-{start}"), "peak": pd.Timestamp(f"{y}-03-18"), "end": pd.Timestamp(f"{y}-{end}")}
            for y in years]


def test_distance_is_days_between_green_up_plus_days_between_season_ends():
    spec = {"crop": "wheat", "window": 0, "position": "end"}                  # sown 15 November
    sow, end = ge.season_in_year(spec, LIB, 2013)
    ini = int(LIB["wheat"]["stages_days"]["ini"])
    season = {"start": sow + pd.Timedelta(ini + 10, unit="D"), "end": end + pd.Timedelta(25, unit="D")}
    assert po.season_distance(season, spec, LIB) == 35
    assert po.sowing_distance([season, season], spec, LIB) == 35.0


def test_wheat_after_rice_takes_the_latest_date_when_the_satellite_season_is_late():
    best = po.best_spec(_winters(), "wheat", LIB, POSITIONS, [DEFAULT[0]])
    assert best["spec"] == {"crop": "wheat", "window": 0, "position": "end"}
    assert best["distance_days"] == min(c["distance_days"] for c in best["candidates"])
    assert [c["spec"]["position"] for c in best["candidates"]] == ["start", "middle", "end"]   # only the 140-day window


def test_a_date_that_overlaps_the_other_crop_is_never_chosen():
    late_rice = {"crop": "rice", "window": 2, "position": "end"}             # sown 15 August, in the field to December
    best = po.best_spec(_winters("10-25", "03-10"), "wheat", LIB, POSITIONS, [late_rice])
    assert best is None or ge.fits([late_rice, best["spec"]], LIB)


def test_an_option_keeps_the_default_dates_for_the_crops_it_shares():
    specs, why = po.option_specs(["rice", "wheat"], DEFAULT, {"winter": _winters(), "monsoon": []}, LIB, POSITIONS)
    assert ge.plan_id(specs) == "rice.w1.middle+wheat.w0.end"
    assert why["wheat"]["slot"] == "winter" and why["wheat"]["distance_days"] > 0
    same, why0 = po.option_specs(["rice", "potato"], DEFAULT, {"winter": _winters(), "monsoon": []}, LIB, POSITIONS)
    assert ge.plan_id(same) == ge.plan_id(DEFAULT) and why0 == {}


def test_a_crop_with_no_date_that_fits_stops_loudly():
    with pytest.raises(ValueError, match="no sowing date"):
        po.option_specs(["rice", "finger_millet"], DEFAULT, {"winter": _winters(), "monsoon": _winters("06-17", "10-30")}, LIB, POSITIONS)
