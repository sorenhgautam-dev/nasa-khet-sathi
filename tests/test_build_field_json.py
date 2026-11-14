"""Build step 5 export: write a real replay into site/data/fields/<id>.json (replay.current) and nothing
else. It refuses a replay made without GPM rain (D6) or one that does not cover 2001 to 2025."""
import copy

import pytest

from pipeline.export import build_field_json as b
from pipeline.export.mock import build_field
from pipeline.export.validate import validate_field


def _replay(rain_source="gpm", years=range(2001, 2026), first_year_crops=("wheat", "rice")):
    def crops(y):
        return list(first_year_crops) if y == min(years) else ["wheat", "rice"]
    return {"labels": {"rain_source": rain_source, "rotation": ["wheat", "rice"], "water_source": "unknown"},
            "years": [{"year": y, "harvest": 71.64, "dry_days": 12, "crops": crops(y), "ky_assumed": True}
                      for y in years],
            "irrigated_years": [{"year": y, "harvest": 99.6, "dry_days": 0, "crops": crops(y), "ky_assumed": True}
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
    assert {k: v for k, v in out.items() if k not in ("replay", "field")} == \
        {k: v for k, v in before.items() if k not in ("replay", "field")}
    assert {k: v for k, v in out["field"].items() if k != "water_source"} == \
        {k: v for k, v in before["field"].items() if k != "water_source"}
    assert doc == before                                   # the input is not changed in place


def test_a_replay_without_gpm_rain_is_refused():
    with pytest.raises(ValueError, match="GPM"):
        b.apply_replay(build_field(), _replay(rain_source="TEMPORARY station rain"), plan_id="current")


def test_a_replay_that_misses_the_last_years_is_refused():
    with pytest.raises(ValueError, match="2025"):
        b.apply_replay(build_field(), _replay(years=range(2001, 2025)), plan_id="current")


def test_a_replay_with_a_gap_is_refused():
    r = _replay()
    r["years"] = [y for y in r["years"] if y["year"] != 2010]
    r["irrigated_years"] = [y for y in r["irrigated_years"] if y["year"] != 2010]
    with pytest.raises(ValueError, match="2010"):
        b.apply_replay(build_field(), r, plan_id="current")


def test_only_complete_years_are_exported():
    """Owner's batch decisions item 14: 2001 holds rice only (its winter crop was sown before the weather
    record), so its basket would look like the best year. Export only years with every crop of the rotation."""
    out = b.apply_replay(build_field(), _replay(first_year_crops=("rice",)), plan_id="current")
    years = [y["year"] for y in out["replay"]["current"]]
    assert years == list(range(2002, 2026))
    assert validate_field(out) == []


def test_an_incomplete_year_after_the_first_is_refused():
    r = _replay()
    r["years"][10]["crops"] = ["rice"]
    with pytest.raises(ValueError, match="2011"):
        b.apply_replay(build_field(), r, plan_id="current")


def test_the_field_water_source_comes_from_the_replay_labels():
    """Item 8: the site labels the two cases side by side from field.water_source."""
    out = b.apply_replay(build_field(), _replay(), plan_id="current")
    assert out["field"]["water_source"] == "unknown"


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


def _seasons(best="threshold", det=0.982):
    years = ["2018", "2022"]
    return {"held_out": {"years": [2018, 2022], "thin_days": 16, "best": best, "best_margin": 0.02,
                         "threshold_vs_changepoint_all_obs": 0.7293,
                         "mean_score": {"threshold": 0.9667, "changepoint": 0.958, "detective": det},
                         "per_year": {y: {"thinned": {"threshold": 0.95, "changepoint": 0.96, "detective": det}} for y in years}},
            "season_date_differences_days": {"changepoint_vs_threshold": {"start": 14.5, "peak": 4.0, "end": 6.0},
                                             "detective_vs_threshold": {"start": 4.5, "peak": 0.0, "end": 2.0}}}


def test_the_method_page_gets_the_three_way_comparison():
    out = b.apply_method(build_field(), _seasons())
    sd = out["method"]["season_detection"]
    assert sd["chosen"] == "threshold" and [m["id"] for m in sd["methods"]] == ["threshold", "changepoint", "detective"]
    assert sd["methods"][2]["si"] and sd["methods"][2]["score"] == 0.982 and sd["methods"][1]["start_diff_days"] == 14.5
    assert validate_field(out) == []


def test_a_choice_against_the_rule_fixed_in_advance_is_refused():
    with pytest.raises(ValueError, match="picks 'threshold'"):
        b.apply_method(build_field(), _seasons(best="detective"))


def _diary(shift=None):
    months = [{"m": m, "rain": "low", "soil": "dry", "heat": "none", "frost": "none", "cover": "bare"}
              for m in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")]
    return {"export": {"shift_days": shift, "bare_days": 62, "guess": ["rice", "potato"],
                       "groundwater": {"trend_cm_per_year": -2.57, "direction": "falling", "confidence": 1.0}, "months": months}}


def test_the_real_diary_replaces_the_mock_and_validates():
    out = b.apply_diary(build_field(), _diary())
    assert out["diary"]["shift_days"] is None and out["diary"]["guess"] == ["rice", "potato"]
    assert out["diary"]["groundwater"]["direction"] == "falling" and validate_field(out) == []


def test_a_diary_without_twelve_months_is_refused():
    d = _diary(shift=-3.0)
    d["export"]["months"].pop()
    with pytest.raises(ValueError, match="twelve months"):
        b.apply_diary(build_field(), d)


# ---------- build step 7 (2026-11-13): plans, ranges for the uncorrected rain, sources, method page ----------

def test_uncorrected_rain_is_added_only_to_years_it_changes():
    from pipeline.export.build_field_json import with_second_rain
    base = [{"year": 2016, "harvest": 70, "dry_days": 80, "event": "none", "irrigated": {"harvest": 100, "dry_days": 0}},
            {"year": 2020, "harvest": 84, "dry_days": 86, "event": "none", "irrigated": {"harvest": 100, "dry_days": 0}}]
    unc = [dict(base[0]), {**base[1], "harvest": 90, "dry_days": 63, "event": "flood"}]
    out = with_second_rain(base, unc)
    assert "dhm_rain" not in out[0]
    assert out[1]["dhm_rain"] == {"harvest": 90, "dry_days": 63, "event": "flood", "irrigated": {"harvest": 100, "dry_days": 0}}
    with pytest.raises(ValueError, match="same years"):
        with_second_rain(base, unc[:1])


def test_stated_choices_list_claudes_choices_with_their_approval():
    from pipeline.export.build_field_json import stated_choices
    rules = {"a": {"x": {"value": 1, "source": "Claude's choice, owner-approved 2026-11-13: why"}},
             "b": {"value": 2, "source": "FAO-56 Table 12"},
             "c": {"value": 3, "source": "Claude's reading. Put to the owner"}}
    out = stated_choices(rules)
    assert [(c["id"], c["status"]) for c in out] == [("a.x", "Claude's choice, owner-approved 2026-11-13"),
                                                     ("c", "Claude's choice, put to the owner")]


def test_stated_choices_read_an_approval_however_it_is_capitalised():
    """REVIEW_2 M7: sources that begin 'Owner-approved 2026-11-13 ...' were exported as plain 'Claude's choice'."""
    from pipeline.export.build_field_json import stated_choices
    rules = {"a": {"value": 1, "source": "Owner-approved 2026-11-13 (batch). Claude's choice: stop at 30 September"},
             "b": {"value": 2, "source": "Owner-approved 2026-11-12 (proposed by Claude: 200 days)"}}
    assert [(c["id"], c["status"]) for c in stated_choices(rules)] == [
        ("a", "Claude's choice, owner-approved 2026-11-13"), ("b", "Claude's choice, owner-approved 2026-11-12")]


def test_stated_choices_list_a_rule_added_by_claude_and_still_with_the_owner():
    """REVIEW_2 M7: the one rule changed after its first run (plans.third_plan_rule) was missing from the list."""
    from pipeline.export.build_field_json import stated_choices
    rules = {"plans": {"third_plan_rule": {"value": "x", "source": "Owner, decision 5: option A. The fallback is "
                                           "Claude's, fixed before the run. 'Other crops' was added by Claude AFTER "
                                           "the first run. Put to the owner"}},
             "other": {"value": 1, "source": "Replaces Claude's unsourced 0.2; NASA MCD12Q2 User Guide sec. 2.2"}}
    assert [(c["id"], c["status"]) for c in stated_choices(rules)] == [
        ("plans.third_plan_rule", "Claude's choice, put to the owner")]


def test_the_real_rules_list_the_third_plan_rule_and_no_approved_choice_as_unapproved():
    import re
    from pathlib import Path
    import yaml
    from pipeline.export.build_field_json import stated_choices
    rules = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "rules.yaml").read_text())
    out = {c["id"]: c for c in stated_choices(rules)}
    assert "plans.third_plan_rule" in out
    for c in out.values():
        if c["status"] == "Claude's choice":
            assert not re.search(r"(?i)owner-approved \d{4}-\d{2}-\d{2}", c["choice"]), c["id"]


def test_the_sources_label_model_based_data_and_hold_no_mock_row():
    from pipeline.export.build_field_json import sources_block
    s = {x["name"]: x for x in sources_block()}
    assert s["NASA POWER"]["type"] == "model" and s["ISRIC SoilGrids"]["type"] == "model"
    assert s["GPM IMERG"]["type"] == "satellite" and "2017" in s["GPM IMERG"]["product"]
    assert not any("MOCK" in x["name"] for x in s.values())       # owner's answer 2: the `mock` list names such blocks


def test_blocks_that_are_not_computed_yet_are_named_and_emptied():
    """Owner's answer 2 to REVIEW_2 (2026-11-13): a `mock` list, neutral sections that tile the real field, no 2040
    numbers; the field's name comes from its config, without '(MOCK data)'."""
    field = {"name": "Sample field (PLACEHOLDER)", "lat": 27.690767, "lon": 85.441792,
             "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]}
    out = b.not_ready_blocks(build_field(), field)
    assert out["mock"] == ["field.sections", "future"] and out["future"] is None
    assert out["field"]["name"] == "Sample field (PLACEHOLDER)" and "MOCK" not in out["field"]["name"]
    assert len(out["field"]["sections"]) == 36
    assert all(sec["status"] == "grey" and sec["wetness"] is None and sec["temp"] is None and sec["sure"] == 0
               for sec in out["field"]["sections"])
    assert validate_field(out) == []


def test_the_sources_say_what_each_dataset_is_really_used_for():
    """REVIEW_2 M5, M6: MODIS changes no number shown; the twin reads only the soil's two water contents, from a cell
    that is not the field's own."""
    from pipeline.export.build_field_json import sources_block
    s = {x["name"]: x for x in sources_block(soil_distance_m=859.3)}
    assert "no number shown uses it" in s["MODIS Terra"]["product"]
    soil = s["ISRIC SoilGrids"]["product"]
    assert "field capacity" in soil and "wilting point" in soil and "texture" not in soil
    assert "859 m from the field" in soil
    assert "from the field" not in {x["name"]: x for x in sources_block()}["ISRIC SoilGrids"]["product"]


def test_the_exported_demo_file_has_three_rice_plans_and_ranges_where_the_rain_fix_matters():
    import json
    from pathlib import Path
    from pipeline.export.validate import validate_field
    d = json.loads((Path(__file__).resolve().parents[1] / "site" / "data" / "fields" / "demo.json").read_text())
    if "rain_correction" not in d["method"]:
        pytest.skip("demo.json not yet exported with step 7")
    assert validate_field(d) == [] and [p["id"] for p in d["plans"]] == ["current", "cover_gap", "safest"]
    assert all(any(c["crop"] == "rice" for c in p["crops"]) for p in d["plans"])
    assert len({tuple(sorted(c["crop"] for c in p["crops"])) for p in d["plans"]}) == 3      # three rotations
    years = {y["year"]: y for y in d["replay"]["current"]}
    # owner's decision 4b (2026-11-14): the second version is the DHM-scaled rain, which differs in any year, not only from 2017
    assert any("dhm_rain" in y for y in years.values())
    assert d["method"]["rain_correction"]["from"] == "2017-01-01"


# --- owner's answer 9 to REVIEW_2 (2026-11-13): one weather event per year, with the season of a one-season drought ---

def test_a_drought_year_carries_the_season_it_comes_from():
    r = _replay()
    y0 = r["years"][3]["year"]
    r["events"][str(y0)] = "drought"
    r["event_seasons"] = {str(y0): "winter"}
    rows = b.replay_rows(r)
    row = next(x for x in rows if x["year"] == y0)
    assert row["event"] == "drought" and row["event_season"] == "winter"
    assert all("event_season" not in x for x in rows if x["year"] != y0)


def test_the_uncorrected_run_keeps_its_own_event_season():
    r, u = _replay(), _replay()
    y0 = r["years"][3]["year"]
    u["events"][str(y0)] = "drought"
    u["event_seasons"] = {str(y0): "monsoon"}
    rows = b.with_second_rain(b.replay_rows(r), b.replay_rows(u))
    row = next(x for x in rows if x["year"] == y0)
    assert row["event"] == "none" and row["dhm_rain"]["event"] == "drought"
    assert row["dhm_rain"]["event_season"] == "monsoon"


def test_the_exported_demo_file_holds_the_current_plan_for_both_winter_crops():
    """Owner's answer 6 to REVIEW_2 (2026-11-13): the site switches between saved results when the farmer answers."""
    import json
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[1] / "site" / "data" / "fields" / "demo.json").read_text())
    if "current_options" not in d:
        pytest.skip("demo.json not yet exported with the current-plan options")
    co = d["current_options"]
    assert co["default"] == "rice_potato" and [o["id"] for o in co["options"]] == ["rice_potato", "rice_wheat"]
    wheat = co["options"][1]
    assert [c["crop"] for c in wheat["crops"]] == ["rice", "wheat"] and len(wheat["replay"]) == len(d["replay"]["current"])
    assert all("irrigated" in y for y in wheat["replay"]) and any("dhm_rain" in y for y in wheat["replay"])
    assert set(wheat["compared"]) == {"cover_gap", "safest"}
    assert "Your winter crop dates may differ from ours." in d["plans"][0]["tabs"]["unknown"]
    assert "sample field" in d["plans"][0]["tabs"]["unknown"]


# --- field memory on the method page (build step 7b; owner's priorities, 2026-11-13) ---

def _memory(kept):
    return {"result": {"n_seasons": 24, "n_years": 12, "kept": kept,
                       "rmse": {"no_anomaly": 0.0296, "physics_only": 0.0321, "memory": 0.035 if not kept else 0.02}}}


def test_field_memory_that_did_not_beat_physics_is_reported_and_left_out():
    from pipeline.words import texts
    block = b.field_memory_block(_memory(False), texts.load("tabs"))
    assert block["kept"] is False and block["seasons"] == 24 and block["years"] == 12
    assert block["error"] == {"no_anomaly": 0.03, "physics_only": 0.032, "memory": 0.035}
    assert "It did not beat our simple water count." in block["words"]["en"] and "So we left it out." in block["words"]["en"]
    assert "24" in block["words"]["en"] and "२४" in block["words"]["ne"]
    doc = build_field()
    doc["method"]["field_memory"] = block
    assert validate_field(doc) == []


def test_field_memory_that_wins_says_it_is_used():
    from pipeline.words import texts
    block = b.field_memory_block(_memory(True), texts.load("tabs"))
    assert block["kept"] is True and "We use it." in block["words"]["en"] and "left it out" not in block["words"]["en"]


def test_the_soil_source_shows_the_neighbourhood_range():
    """Owner's answer 10 to REVIEW_2 (2026-11-13)."""
    from pipeline.export.build_field_json import sources_block
    around = {"radius_m": 2000, "depth_m": 1.0, "cells": 56, "used_mm": 149.3, "min_mm": 149.3, "median_mm": 171.5, "max_mm": 186.8}
    soil = {x["name"]: x for x in sources_block(soil_distance_m=859.3, soil_around=around)}["ISRIC SoilGrids"]["product"]
    assert "859 m from the field" in soil and "149 mm" in soil and "56 cells within 2 km" in soil and "149 to 187 mm" in soil


# --- owner's group 2a (2026-11-14): four real parts, each with its own greenness, status from the twin ---

_FIELD = {"name": "Sample field (PLACEHOLDER)", "lat": 27.690767, "lon": 85.441792,
          "polygon": [[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037], [85.441487, 27.691037]]}


def _sections_check():
    words = ["same", "less green", "greener", "can't tell"]
    secs = []
    for i in range(4):
        secs.append({"id": f"s{i + 1}", "polygon": [[85.4415, 27.6905], [85.4418, 27.6905], [85.4418, 27.6908]],
                     "status": "green", "wetness_pct": 95.67, "low_ground": None,
                     "greenness": {"usually": words[i]}})
    return {"sections": secs}


_STATE = {"date": "2026-11-03", "wetness_pct": 95.67, "ks": 1.0, "sure_prior": 0.217}


def test_real_sections_carry_wetness_status_and_their_own_words():
    out = b.not_ready_blocks(build_field(), _FIELD, sections=_sections_check(), twin_state=_STATE)
    secs = out["field"]["sections"]
    assert [s["id"] for s in secs] == ["s1", "s2", "s3", "s4"]
    assert [s["greener"] for s in secs] == ["same", "less", "more", "unknown"]
    assert all(s["wetness"] == 96 and s["status"] == "green" and s["temp"] is None and s["low_ground"] is None for s in secs)
    assert all(s["sure"] == 0.22 for s in secs)                  # the twin's own sureness before any probe reading
    assert out["field"]["status_date"] == "2026-11-03"
    assert "field.sections" not in out["mock"] and "future" in out["mock"]
    assert validate_field(out) == []


def test_sections_without_the_twin_state_stay_not_ready():
    out = b.not_ready_blocks(build_field(), _FIELD, sections=_sections_check(), twin_state=None)
    assert "field.sections" in out["mock"]
    assert all(s["status"] == "grey" and s["wetness"] is None and s["sure"] == 0 for s in out["field"]["sections"])
    assert len(out["field"]["sections"]) == 4                     # the real parts' outlines, still without numbers
    assert validate_field(out) == []


def _onset_dhm():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parents[1] / "data/checks/demo/onset_dhm.json").read_text())


@pytest.mark.skipif(not __import__("pathlib").Path(__file__).resolve().parents[1].joinpath("data/checks/demo/onset_dhm.json").exists(),
                    reason="needs scripts/run_onset_dhm.py output")
def test_dhms_monsoon_record_fills_the_shift_and_the_usual_start():
    """Owner, 2026-11-14: fill shift_days from DHM's official onset dates, with their range, credited to DHM."""
    d = b.apply_onset_dhm(build_field(), _onset_dhm())
    dy = d["diary"]
    assert dy["shift_days"] == -2.2 and dy["shift_days_low"] == -11.5 and dy["shift_days_high"] == 7.7
    assert dy["shift_source"]["name"].startswith("DHM") and dy["monsoon_start"]["late_years"] == [2009]
    assert dy["monsoon_start"]["words"]["en"] and dy["shift_note"]["ne"]
    assert any(s["name"].startswith("DHM") for s in d["sources"]) and d["method"]["onset"]["words"]["en"]
    assert validate_field(d) == []
    assert b.apply_onset_dhm(d, _onset_dhm())["sources"] == d["sources"]          # applying twice adds no second row


def _future_check():
    def run(h, lo, hi):
        return {"outlook": {"harvest": h, "harvest_low": lo, "harvest_high": hi}}
    plans = {"P_cur": {"corrected": run(70.9, 66.8, 72.8), "dhm": run(71.8, 67.3, 73.8)},
             "P_wheat": {"corrected": run(87.8, 85.0, 89.2), "dhm": run(88.0, 85.1, 89.9)},
             "P_lentil": {"corrected": run(79.4, 76.2, 81.0), "dhm": run(79.4, 76.2, 81.0)},
             "P_opt": {"corrected": run(80.6, 76.0, 82.1), "dhm": run(80.9, 76.3, 82.4)}}
    return {"models": ["A", "B", "C", "D", "E"], "labels": {"scenarios": ["ssp245", "ssp585"],
            "periods": {"historical": [1995, 2014], "future": [2026, 2040]}}, "plans": plans}


def test_the_2040_outlook_fills_every_plan_and_option():
    """Owner's group 2e (2026-11-14): every shown plan and both current options, the spread across models and scenarios
    as the range, rounded to whole points; the uncorrected rain as a second version only where it differs."""
    d = build_field()
    d["current_options"] = {"default": "rice_potato", "options": [{"id": "rice_potato"}, {"id": "rice_wheat"}]}
    ids = {"current": "P_cur", "cover_gap": "P_wheat", "safest": "P_lentil"}
    opt_ids = {"rice_potato": "P_cur", "rice_wheat": "P_opt"}
    out = b.apply_future(d, _future_check(), ids, opt_ids)
    f = out["future"]
    assert f["years"] == [2040] and f["period"] == "2026-2040" and len(f["models"]) == 5
    assert f["nothing_changes"] == {"harvest": [71], "harvest_low": [67], "harvest_high": [73]}
    assert f["with_plan"] == {"harvest": [88], "harvest_low": [85], "harvest_high": [89]}
    p = {x["id"]: x for x in out["plans"]}
    assert p["safest"]["future"] == {"harvest": [79], "harvest_low": [76], "harvest_high": [81]}
    assert "future_dhm_rain" in p["current"] and "future_dhm_rain" not in p["safest"]
    assert out["current_options"]["options"][1]["future"]["harvest"] == [81]
    assert "future" not in out.get("mock", [])
    assert f["words"]["en"] and f["words"]["ne"]
