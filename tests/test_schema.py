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
def _event_storm(d): d["replay"]["current"][0]["event"] = "storm"            # none/drought/flood
def _event_frost(d): d["replay"]["current"][0]["event"] = "frost"            # owner, 2026-11-12 (M1): no frost event
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


# irrigated replay (owner's go, 2026-11-12): {harvest 0-100, dry_days 0-366} and nothing else
def _irrigated_harvest_above_100(d): d["replay"]["current"][0]["irrigated"]["harvest"] = 101
def _irrigated_missing_dry_days(d): del d["replay"]["current"][0]["irrigated"]["dry_days"]
def _irrigated_negative_dry_days(d): d["replay"]["current"][0]["irrigated"]["dry_days"] = -1
def _irrigated_extra_key(d): d["replay"]["current"][0]["irrigated"]["water_mm"] = 120

# Nepali tabs and tips (owner, 2026-11-12): every plan carries tabs_ne and tips_ne beside the English
def _missing_tabs_ne(d): del d["plans"][0]["tabs_ne"]
def _missing_tips_ne(d): del d["plans"][0]["tips_ne"]
def _tab_ne_missing_key(d): del d["plans"][0]["tabs_ne"]["check"]
def _tab_ne_extra_key(d): d["plans"][0]["tabs_ne"]["extra"] = "धान"
def _tab_ne_empty(d): d["plans"][0]["tabs_ne"]["why"] = ""
def _tab_ne_in_english(d): d["plans"][0]["tabs_ne"]["why"] = "This is English, not Nepali."
def _tip_ne_in_english(d): d["plans"][0]["tips_ne"][0] = "Water it in September."
def _tip_ne_empty(d): d["plans"][0]["tips_ne"][0] = ""
def _tips_ne_one_more_than_tips(d): d["plans"][0]["tips_ne"].append("धानलाई पानी दिनुहोस्।")
def _tips_ne_one_fewer_than_tips(d): d["plans"][0]["tips_ne"].pop()

# method page (owner's go, 2026-11-13): the three-way season-detection comparison
def _method_missing(d): del d["method"]
def _method_two_methods(d): d["method"]["season_detection"]["methods"].pop()
def _method_score_above_one(d): d["method"]["season_detection"]["methods"][0]["score"] = 1.2
def _method_unknown_id(d): d["method"]["season_detection"]["methods"][0]["id"] = "guess"
def _method_duplicate_id(d): d["method"]["season_detection"]["methods"][1]["id"] = "threshold"
def _method_year_missing(d): d["method"]["season_detection"]["methods"][0]["by_year"].pop()
def _method_chosen_against_rule(d): d["method"]["season_detection"]["chosen"] = "detective"   # 0.97 - 0.96 < 0.02
def _method_threshold_is_si(d): d["method"]["season_detection"]["methods"][0]["si"] = True


FIELD_BREAKS = [
    _status_blue, _sure_above_one, _sure_below_zero, _score_above_100, _score_below_0,
    _replay_harvest_above_100, _event_storm, _event_frost, _no_current_plan, _two_plans, _bad_date, _month_13_date,
    _unknown_top_key, _missing_sources, _empty_sources, _source_type_guess, _eleven_months,
    _months_out_of_order, _duplicate_section_id, _replay_for_unknown_plan, _future_too_short,
    _empty_tab, _missing_tab, _point_with_three_numbers, _polygon_two_points, _lat_out_of_range,
    _replay_year_out_of_record, _duplicate_replay_year, _frost_word,
    _old_frost_word, _cover_crop_name, _rain_word, _soil_word, _heat_word,
    _low_above_harvest, _high_below_harvest, _low_too_short, _missing_high, _high_above_100,
    _missing_groundwater, _groundwater_direction_word, _groundwater_confidence_above_one,
    _groundwater_extra_key, _falling_but_trend_up, _rising_but_trend_down,
    _irrigated_harvest_above_100, _irrigated_missing_dry_days, _irrigated_negative_dry_days, _irrigated_extra_key,
    _missing_tabs_ne, _missing_tips_ne, _tab_ne_missing_key, _tab_ne_extra_key, _tab_ne_empty, _tab_ne_in_english,
    _tip_ne_in_english, _tip_ne_empty, _tips_ne_one_more_than_tips, _tips_ne_one_fewer_than_tips,
    _method_missing, _method_two_methods, _method_score_above_one, _method_unknown_id, _method_duplicate_id,
    _method_year_missing, _method_chosen_against_rule, _method_threshold_is_si,
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


def test_every_mock_replay_year_has_the_irrigated_case():
    d = build_field()
    assert all(set(y["irrigated"]) == {"harvest", "dry_days"} for rows in d["replay"].values() for y in rows)


def test_a_replay_year_without_the_irrigated_case_is_refused():
    """Owner's answer 17 to REVIEW_2 (2026-11-13): both water cases on every replay year (was optional)."""
    d = build_field()
    del d["replay"]["current"][0]["irrigated"]
    assert validate_field(d) != []


# --- owner's answer 2 to REVIEW_2 (2026-11-13): blocks that are not ready are named and hold no made-up numbers ---

def _not_ready():
    d = build_field()
    d["mock"] = ["field.sections", "future"]
    d["future"] = None
    for sec in d["field"]["sections"]:
        sec.update(status="grey", wetness=None, temp=None, sure=0)
    return d


def test_blocks_named_as_not_ready_validate_when_they_hold_no_numbers():
    assert validate_field(_not_ready()) == []


def test_a_block_named_as_not_ready_must_not_carry_numbers():
    d = _not_ready()
    d["field"]["sections"][0]["wetness"] = 55
    assert any("field.sections" in e for e in validate_field(d))
    d = _not_ready()
    d["future"] = build_field()["future"]
    assert any("future" in e for e in validate_field(d))


def test_an_empty_block_must_be_named_in_the_list():
    d = _not_ready()
    d["mock"] = ["field.sections"]
    assert any("future" in e for e in validate_field(d))
    d = _not_ready()
    del d["mock"]
    assert validate_field(d) != []


def test_only_known_blocks_can_be_named():
    d = _not_ready()
    d["mock"] = ["plans"]
    assert validate_field(d) != []


# --- owner's batch decisions, 2026-11-12 ---

def test_section_temp_may_be_null_before_the_probe_reads_it():
    """Item 23: temp is soil temperature from the probe; a section the probe has not read has none (no invented
    numbers, rule 11). It stays required, so the UI always finds the key."""
    d = build_field()
    d["field"]["sections"][0]["temp"] = None
    assert validate_field(d) == []
    del d["field"]["sections"][0]["temp"]
    assert validate_field(d) != []


def test_the_mock_has_sections_with_and_without_a_probe_reading():
    temps = [s["temp"] for s in build_field()["field"]["sections"]]
    assert None in temps and any(t is not None for t in temps)


@pytest.mark.parametrize("value", ["unknown", "rain-only", "canal", "well", "irrigated"])
def test_field_water_source_takes_the_config_values(value):
    """Item 8: the site labels the two replay cases from this ('if you can water' / 'if you can't')."""
    d = build_field()
    d["field"]["water_source"] = value
    assert validate_field(d) == []


def test_field_water_source_is_required_and_closed():
    d = build_field()
    d["field"]["water_source"] = "rain only"
    assert validate_field(d) != []
    del d["field"]["water_source"]
    assert validate_field(d) != []


def test_the_mock_demo_field_water_source_is_unknown():
    assert build_field()["field"]["water_source"] == "unknown"


def test_a_method_that_beats_the_margin_must_be_chosen():
    from pipeline.export.mock import build_field
    from pipeline.export.validate import validate_field
    d = build_field()
    sd = d["method"]["season_detection"]
    sd["methods"][2]["score"] = 0.99                               # detective beats threshold 0.96 by 0.03
    assert any("picks 'detective'" in e for e in validate_field(d))
    sd["chosen"] = "detective"
    assert validate_field(d) == []


# --- REVIEW_2 M13: what the schema cannot say about plans and their replays ---

def test_a_plan_without_a_replay_is_refused():
    d = build_field()
    del d["replay"]["safest"]
    assert any("no replay" in e for e in validate_field(d))


def test_replay_years_must_rise_one_by_one():
    d = build_field()
    d["replay"]["current"].pop(3)                                   # a gap
    assert any("year by year" in e for e in validate_field(d))
    d = build_field()
    d["replay"]["current"].reverse()
    assert any("year by year" in e for e in validate_field(d))


def _final_ready():
    """The mock made consistent and stripped of its MOCK words: what a file ready to freeze must look like."""
    import json
    d = json.loads(json.dumps(build_field(), ensure_ascii=False).replace("MOCK", "sample"))
    d["plans"][2]["crops"][1]["crop"] = "wheat"                     # three different rotations
    d["plans"][0]["crops"][1]["crop"] = "potato"
    for p in d["plans"]:
        for y in d["replay"][p["id"]]:
            y["harvest"] = p["score"]["harvest"]
    return d


def test_a_consistent_file_without_mock_passes_the_final_check():
    d = _final_ready()
    assert validate_field(d) == [] and validate_field(d, final=True) == []


def test_the_final_check_refuses_mock_data():
    assert any("MOCK" in e for e in validate_field(build_field(), final=True))
    assert validate_field(build_field()) == []                      # the everyday check only warns (CLI)


def test_the_final_check_refuses_two_plans_with_the_same_crops():
    d = _final_ready()
    d["plans"][2]["crops"] = [dict(c) for c in d["plans"][1]["crops"]]
    assert any("same crops" in e for e in validate_field(d, final=True))


def test_the_final_check_refuses_a_score_that_is_not_the_replays_mean():
    d = _final_ready()
    d["plans"][0]["score"]["harvest"] = 5
    assert any("score.harvest" in e for e in validate_field(d, final=True))


def test_a_file_with_blocks_not_ready_passes_the_final_check_if_nothing_is_made_up():
    """Owner's answer 2: if steps 8 and 9 slip, the file freezes with honest 'not ready yet' blocks."""
    import json
    d = _final_ready()
    d["mock"] = ["field.sections", "future"]
    d["future"] = None
    for sec in d["field"]["sections"]:
        sec.update(status="grey", wetness=None, temp=None, sure=0)
    assert "MOCK" not in json.dumps(d) and validate_field(d, final=True) == []


# --- owner's answer 9 to REVIEW_2 (2026-11-13): one weather event per year for the field, the same on every plan ---

def test_a_drought_may_name_its_season_and_nothing_else_may():
    d = build_field()
    for rows in d["replay"].values():
        rows[0]["event"] = "drought"
        rows[0]["event_season"] = "winter"
    assert validate_field(d) == []
    for rows in d["replay"].values():
        rows[0]["event"] = "flood"
    assert any("event_season" in e for e in validate_field(d))
    d["replay"]["current"][0]["event_season"] = "spring"
    assert validate_field(d) != []


def test_the_same_year_has_the_same_event_on_every_plan():
    d = build_field()
    assert validate_field(d) == []
    y = d["replay"]["current"][2]
    y["event"] = "flood" if y["event"] != "flood" else "none"
    assert any("same event" in e for e in validate_field(d))


# --- owner's answer 6 to REVIEW_2 (2026-11-13): the current plan for each winter crop the farmer may confirm ---

def _with_options():
    import copy
    d = build_field()
    cur = d["plans"][0]
    def option(oid, winter):
        o = {"id": oid, "crops": copy.deepcopy(cur["crops"]), "score": dict(cur["score"]),
             "tabs": dict(cur["tabs"]), "tips": list(cur["tips"]), "tabs_ne": dict(cur["tabs_ne"]), "tips_ne": list(cur["tips_ne"]),
             "replay": copy.deepcopy(d["replay"]["current"]),
             "compared": {p["id"]: {"tabs": dict(p["tabs"]), "tabs_ne": dict(p["tabs_ne"])} for p in d["plans"][1:]}}
        o["crops"][1]["crop"] = winter
        return o
    first = option("rice_" + cur["crops"][1]["crop"], cur["crops"][1]["crop"])
    other = option("rice_potato" if cur["crops"][1]["crop"] != "potato" else "rice_maize",
                   "potato" if cur["crops"][1]["crop"] != "potato" else "maize")
    d["current_options"] = {"default": first["id"], "options": [first, other]}
    return d


def test_current_options_validate_and_the_default_is_the_current_plan():
    d = _with_options()
    assert validate_field(d) == []
    d["current_options"]["default"] = "rice_nothing"
    assert any("default" in e for e in validate_field(d))


def test_the_default_option_must_be_what_plans_and_replay_show():
    d = _with_options()
    d["current_options"]["options"][0]["score"]["harvest"] = 1
    assert any("default option" in e for e in validate_field(d))
    d = _with_options()
    d["current_options"]["options"][0]["replay"][0]["harvest"] = 1
    assert any("default option" in e for e in validate_field(d))


def test_every_option_covers_the_same_years_and_compares_every_suggested_plan():
    d = _with_options()
    d["current_options"]["options"][1]["replay"].pop()
    assert any("same years" in e for e in validate_field(d))
    d = _with_options()
    del d["current_options"]["options"][1]["compared"]["safest"]
    assert any("compared" in e for e in validate_field(d))
    d = _with_options()
    d["current_options"]["options"][1]["crops"] = d["current_options"]["options"][0]["crops"]
    assert any("same crops" in e for e in validate_field(d))


# --- owner's priorities, 2026-11-13: the season detective (SI) as a 'less sure' signal per month ---

def test_a_month_may_say_how_sure_its_cover_word_is():
    d = build_field()
    for m in d["diary"]["months"]:
        m["cover_sure"] = 0.82
    assert validate_field(d) == []
    d["diary"]["months"][0]["cover_sure"] = 1.2
    assert validate_field(d) != []
