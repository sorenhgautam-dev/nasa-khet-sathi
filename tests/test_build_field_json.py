"""Build step 5 export: write a real replay into site/data/fields/<id>.json (replay.current) and nothing
else. It refuses a replay made without GPM rain (D6) or one that does not cover 2001 to 2025."""
import copy

import pytest

from pipeline.export import build_field_json as b
from pipeline.export.mock import build_field
from pipeline.export.validate import validate_field


def _replay(rain_source="gpm", years=range(2001, 2026)):
    return {"labels": {"rain_source": rain_source},
            "years": [{"year": y, "harvest": 71.64, "dry_days": 12, "crops": ["wheat", "rice"], "ky_assumed": True}
                      for y in years],
            "irrigated_years": [{"year": y, "harvest": 99.6, "dry_days": 0, "crops": ["wheat", "rice"], "ky_assumed": True}
                                for y in years],
            "events": {str(y): "none" for y in years}}


def test_replay_current_is_replaced_and_the_file_still_validates():
    doc = build_field()
    before = copy.deepcopy(doc)
    out = b.apply_replay(doc, _replay(), plan_id="current")
    assert out["replay"]["current"][0] == {"year": 2001, "harvest": 72, "dry_days": 12, "event": "none",
                                           "irrigated": {"harvest": 100, "dry_days": 0}}
    assert len(out["replay"]["current"]) == 25
    assert validate_field(out) == []
    assert {k: v for k, v in out.items() if k != "replay"} == {k: v for k, v in before.items() if k != "replay"}
    assert doc == before                                   # the input is not changed in place


def test_a_replay_without_gpm_rain_is_refused():
    with pytest.raises(ValueError, match="GPM"):
        b.apply_replay(build_field(), _replay(rain_source="TEMPORARY station rain"), plan_id="current")


def test_a_replay_that_misses_years_is_refused():
    with pytest.raises(ValueError, match="2001"):
        b.apply_replay(build_field(), _replay(years=range(2002, 2026)), plan_id="current")


def test_every_year_needs_an_event():
    r = _replay()
    del r["events"]["2010"]
    with pytest.raises(ValueError, match="event"):
        b.apply_replay(build_field(), r, plan_id="current")


def test_events_still_to_be_computed_are_refused_cleanly():
    r = _replay()
    r["events"] = None
    with pytest.raises(ValueError, match="event"):
        b.apply_replay(build_field(), r, plan_id="current")


def test_a_placeholder_rotation_is_exported_only_if_the_field_says_placeholder():
    r = _replay()
    r["labels"]["rotation_source"] = "PLACEHOLDER: FAO Hill-zone default"
    doc = build_field()
    doc["field"]["name"] = "Demo field"
    with pytest.raises(ValueError, match="placeholder"):
        b.apply_replay(doc, r, plan_id="current")
    doc["field"]["name"] = "Demo field (placeholder location and rotation)"
    assert b.apply_replay(doc, r, plan_id="current")["replay"]["current"]


def test_the_irrigated_case_must_cover_the_same_years():
    r = _replay()
    r["irrigated_years"] = r["irrigated_years"][1:]
    with pytest.raises(ValueError, match="irrigated"):
        b.apply_replay(build_field(), r, plan_id="current")
