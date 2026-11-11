"""The output contract (CLAUDE.md "The output contract") as tests.

Each rejection case names a rule from CLAUDE.md; if the schema stops enforcing it, that case fails.
"""
import pytest
from jsonschema import Draft202012Validator

from pipeline.export.mock import build_field, build_index
from pipeline.export.validate import load_schema, validate_field, validate_index


def test_field_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(load_schema("schema.json"))


def test_index_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(load_schema("index_schema.json"))


def test_mock_field_passes_the_contract():
    assert validate_field(build_field()) == []


def test_mock_index_passes_the_contract():
    assert validate_index(build_index()) == []


# --- field file: every mutation breaks one CLAUDE.md rule and must be rejected ---

def _status_blue(d): d["field"]["sections"][0]["status"] = "blue"            # status is green/yellow/red/grey
def _sure_above_one(d): d["field"]["sections"][0]["sure"] = 1.2              # sure runs 0 to 1
def _sure_below_zero(d): d["field"]["sections"][0]["sure"] = -0.1
def _score_above_100(d): d["plans"][0]["score"]["harvest"] = 101             # scores run 0 to 100
def _score_below_0(d): d["plans"][0]["score"]["water"] = -1
def _replay_harvest_above_100(d): d["replay"]["current"][0]["harvest"] = 120  # yield is % of potential
def _event_storm(d): d["replay"]["current"][0]["event"] = "storm"            # none/drought/flood/frost
def _no_current_plan(d): d["plans"][0]["id"] = "old"                         # must include the current rotation
def _two_plans(d): d["plans"] = d["plans"][:2]                               # at least three strategies
def _bad_date(d): d["plans"][0]["crops"][0]["start"] = "6-15"                # dates are MM-DD
def _month_13_date(d): d["plans"][0]["crops"][0]["end"] = "13-01"
def _unknown_top_key(d): d["extra"] = 1                                      # contract is closed
def _missing_sources(d): del d["sources"]                                    # every number carries a source
def _empty_sources(d): d["sources"] = []
def _source_type_guess(d): d["sources"][0]["type"] = "guess"                 # label model vs satellite etc.
def _eleven_months(d): d["diary"]["months"].pop()                            # monthly calendar has 12 months
def _months_out_of_order(d):
    m = d["diary"]["months"]; m[0], m[1] = m[1], m[0]
def _duplicate_section_id(d): d["field"]["sections"][1]["id"] = d["field"]["sections"][0]["id"]
def _replay_for_unknown_plan(d): d["replay"]["ghost"] = d["replay"]["current"]
def _future_too_short(d): d["future"]["with_plan"]["harvest"].pop()
def _empty_tab(d): d["plans"][0]["tabs"]["why"] = ""                         # every tab has text
def _missing_tab(d): del d["plans"][0]["tabs"]["check"]
def _point_with_three_numbers(d): d["field"]["sections"][0]["polygon"][0] = [85.43, 27.67, 1300]
def _polygon_two_points(d): d["field"]["sections"][0]["polygon"] = d["field"]["sections"][0]["polygon"][:2]
def _lat_out_of_range(d): d["field"]["lat"] = 95
def _replay_year_out_of_record(d): d["replay"]["current"][0]["year"] = 1999   # replay is 2001-2025
def _duplicate_replay_year(d): d["replay"]["current"][1]["year"] = d["replay"]["current"][0]["year"]
def _frost_word(d): d["diary"]["months"][0]["frost"] = "maybe"
# 2026-11-11 contract fixes (owner's A13 decision): month words are closed lists
def _old_frost_word(d): d["diary"]["months"][0]["frost"] = "frost"           # frost is none|risk|high
def _cover_crop_name(d): d["diary"]["months"][0]["cover"] = "wheat"          # cover is bare|partial|crop
def _rain_word(d): d["diary"]["months"][0]["rain"] = "wet"                   # rain is low|medium|high
def _soil_word(d): d["diary"]["months"][0]["soil"] = "low"                   # soil is dry|medium|wet
def _heat_word(d): d["diary"]["months"][0]["heat"] = "medium"                # heat is none|some|high
# future ranges (rule 11: projections are ranges)
def _low_above_harvest(d):
    s = d["future"]["with_plan"]; s["harvest_low"][0] = s["harvest"][0] + 1
def _high_below_harvest(d):
    s = d["future"]["nothing_changes"]; s["harvest_high"][1] = s["harvest"][1] - 1
def _low_too_short(d): d["future"]["with_plan"]["harvest_low"].pop()
def _missing_high(d): del d["future"]["nothing_changes"]["harvest_high"]
def _high_above_100(d): d["future"]["with_plan"]["harvest_high"][0] = 101
# groundwater (owner's D7 decision)
def _missing_groundwater(d): del d["diary"]["groundwater"]
def _groundwater_direction_word(d): d["diary"]["groundwater"]["direction"] = "down"
def _groundwater_confidence_above_one(d): d["diary"]["groundwater"]["confidence"] = 1.5
def _groundwater_extra_key(d): d["diary"]["groundwater"]["mm"] = 3
def _falling_but_trend_up(d):
    d["diary"]["groundwater"].update(direction="falling", trend_cm_per_year=0.8)
def _rising_but_trend_down(d):
    d["diary"]["groundwater"].update(direction="rising", trend_cm_per_year=-0.8)


FIELD_BREAKS = [
    _status_blue, _sure_above_one, _sure_below_zero, _score_above_100, _score_below_0,
    _replay_harvest_above_100, _event_storm, _no_current_plan, _two_plans, _bad_date, _month_13_date,
    _unknown_top_key, _missing_sources, _empty_sources, _source_type_guess, _eleven_months,
    _months_out_of_order, _duplicate_section_id, _replay_for_unknown_plan, _future_too_short,
    _empty_tab, _missing_tab, _point_with_three_numbers, _polygon_two_points, _lat_out_of_range,
    _replay_year_out_of_record, _duplicate_replay_year, _frost_word,
    _old_frost_word, _cover_crop_name, _rain_word, _soil_word, _heat_word,
    _low_above_harvest, _high_below_harvest, _low_too_short, _missing_high, _high_above_100,
    _missing_groundwater, _groundwater_direction_word, _groundwater_confidence_above_one,
    _groundwater_extra_key, _falling_but_trend_up, _rising_but_trend_down,
]


@pytest.mark.parametrize("mutate", FIELD_BREAKS, ids=[f.__name__.strip("_") for f in FIELD_BREAKS])
def test_field_contract_rejects(mutate):
    d = build_field()
    mutate(d)
    assert validate_field(d) != []


# --- index file ---

def _bbox_inverted(d): d["fields"][0]["bbox"] = [85.44, 27.66, 85.42, 27.68]
def _centre_outside_bbox(d): d["fields"][0]["lat"] = 30.0
def _bad_id(d): d["fields"][0]["id"] = "Demo Field"
def _duplicate_id(d): d["fields"].append(dict(d["fields"][0]))
def _no_fields(d): d["fields"] = []
def _bbox_three_numbers(d): d["fields"][0]["bbox"] = [85.42, 27.66, 85.44]


INDEX_BREAKS = [_bbox_inverted, _centre_outside_bbox, _bad_id, _duplicate_id, _no_fields, _bbox_three_numbers]


@pytest.mark.parametrize("mutate", INDEX_BREAKS, ids=[f.__name__.strip("_") for f in INDEX_BREAKS])
def test_index_contract_rejects(mutate):
    d = build_index()
    mutate(d)
    assert validate_index(d) != []
