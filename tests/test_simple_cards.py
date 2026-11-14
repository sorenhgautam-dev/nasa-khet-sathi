"""pipeline/export/build_simple.py: the three farmer cards (rules.yaml simple_cards), worked numbers."""
from pipeline.export import build_simple as bs

RULES = {"replay_window": "m6", "start": "start_default", "compare": {"better_by": 10, "worse_by": 10}}


def test_each_past_winter_is_better_same_or_worse_by_ten_points():
    #            +10 -> better, 0 -> same, -15 -> worse, +3 -> same, -10 -> worse
    assert bs.compare([60, 70, 80, 75, 40], [50, 70, 95, 72, 50], 10, 10) == {"better": 1, "same": 2, "worse": 2}


def test_faces_per_ten_add_up_to_ten_by_largest_remainder():
    # 10 x 20/24 = 8.33, 10 x 3/24 = 1.25, 10 x 1/24 = 0.42: floors 8 + 1 + 0 = 9; the leftover face goes to worse (0.42)
    assert bs.per_ten({"better": 20, "same": 3, "worse": 1}, 24) == {"better": 8, "same": 1, "worse": 1}
    assert bs.per_ten({"better": 12, "same": 0, "worse": 12}, 24) == {"better": 5, "same": 0, "worse": 5}
    # equal remainders (3.33 each): better first, then same
    assert bs.per_ten({"better": 8, "same": 8, "worse": 8}, 24) == {"better": 4, "same": 3, "worse": 3}


def test_the_verdict_is_said_plainly():
    assert bs.verdict({"better": 20, "same": 3, "worse": 1}, 24) == "better"
    assert bs.verdict({"better": 5, "same": 7, "worse": 12}, 24) == "worse"
    assert bs.verdict({"better": 3, "same": 15, "worse": 6}, 24) == "same"
    assert bs.verdict({"better": 8, "same": 8, "worse": 8}, 24) == "mixed"
    assert bs.verdict({"better": 12, "same": 0, "worse": 12}, 24) == "mixed"


def _sq(scores):
    return [{"year": 2002 + i, "score": s} for i, s in enumerate(scores)]


def test_the_suggestion_is_the_other_crop_that_beats_the_farmers_most():
    replay = {"start_default": "medium", "plans": [
        {"id": "current", "crops_in_window": {"m6": [{"crop": "potato"}]}, "results": {"m6": {"medium": _sq([40, 40, 40, 40])}}},
        {"id": "cover_gap", "crops_in_window": {"m6": [{"crop": "wheat"}]}, "results": {"m6": {"medium": _sq([70, 70, 30, 40])}}},
        {"id": "safest", "crops_in_window": {"m6": [{"crop": "lentil"}]}, "results": {"m6": {"medium": _sq([55, 52, 45, 40])}}},
        {"id": "rice_potato", "crops_in_window": {"m6": [{"crop": "potato"}]}, "results": {"m6": {"medium": _sq([40, 40, 40, 40])}}},
        {"id": "rice_wheat", "crops_in_window": {"m6": [{"crop": "wheat"}]}, "results": {"m6": {"medium": _sq([70, 70, 30, 40])}}}]}
    answers = {"potato": "rice_potato", "wheat": "rice_wheat"}
    cards = bs.replay_cards(replay, answers, RULES)
    # potato grower: wheat 2 better, 1 worse (+1); lentil 2 better, 0 worse (+2) -> lentil
    assert cards["potato"]["water_no"]["crop"] == "lentil" and cards["potato"]["water_no"]["counts"] == {"better": 2, "same": 2, "worse": 0}
    # wheat grower: only lentil differs (wheat is his own crop)
    assert cards["wheat"]["water_no"]["crop"] == "lentil"
    # with water, the twin meets every crop's need: every winter the same
    assert cards["potato"]["water_yes"]["counts"] == {"better": 0, "same": 4, "worse": 0}
    assert cards["potato"]["water_yes"]["verdict"] == "same"


def test_each_plan_gets_its_own_line_against_the_farmers_crop():
    replay = {"start_default": "medium", "plans": [
        {"id": "current", "crops_in_window": {"m6": [{"crop": "potato"}]}, "results": {"m6": {"medium": _sq([40, 40, 40, 40])}}},
        {"id": "cover_gap", "crops_in_window": {"m6": [{"crop": "wheat"}]}, "results": {"m6": {"medium": _sq([70, 70, 30, 40])}}},
        {"id": "safest", "crops_in_window": {"m6": [{"crop": "lentil"}]}, "results": {"m6": {"medium": _sq([55, 52, 45, 40])}}},
        {"id": "rice_potato", "crops_in_window": {"m6": [{"crop": "potato"}]}, "results": {"m6": {"medium": _sq([40, 40, 40, 40])}}},
        {"id": "rice_wheat", "crops_in_window": {"m6": [{"crop": "wheat"}]}, "results": {"m6": {"medium": _sq([70, 70, 30, 40])}}}]}
    lines = bs.plan_lines(replay, {"potato": "rice_potato", "wheat": "rice_wheat"}, RULES)
    # potato grower: wheat better in 2, worse in 1 of 4 winters -> 5 / 2.5 / 2.5 per ten -> 5, 3, 2 (ties: same before worse)
    assert lines["potato"]["cover_gap"] == {"crop": "wheat", "counts": {"better": 2, "same": 1, "worse": 1},
                                            "per_ten": {"better": 5, "same": 3, "worse": 2}}
    # the same crop as the farmer's: no line
    assert "cover_gap" not in lines["wheat"] and lines["wheat"]["safest"]["crop"] == "lentil"


# ---------- farmer answers (rules.yaml farmer_answers, owner 2026-11-14 evening) ----------

def test_a_date_takes_the_bikram_sambat_month_that_starts_on_the_15th():
    assert bs.bs_key("10-15") == "Oct"      # Kartik starts about 15 Oct
    assert bs.bs_key("10-14") == "Sep"      # still Asoj
    assert bs.bs_key("03-03") == "Feb"      # Falgun runs to about 14 Mar
    assert bs.bs_key("01-10") == "Dec"      # Poush crosses 1 January


def test_actions_are_the_plans_calendar_with_the_last_harvest_joined_to_the_next_planting():
    rotation = [{"crop": "rice", "start": "06-23", "end": "10-10"}, {"crop": "wheat", "start": "11-15", "end": "04-03"}]
    acts = bs.actions(rotation, [{"crop": "wheat", "start": "11-15", "end": "04-03"}])
    assert acts == [{"do": "sow", "crop": "wheat", "month": "Nov"},
                    {"do": "harvest_then", "crop": "wheat", "month": "Mar", "new_do": "plant", "new_crop": "rice", "new_month": "Jun"}]


def test_action_words_follow_the_label_plain_only_when_verified():
    acts = [{"do": "sow", "crop": "wheat", "month": "Oct"},
            {"do": "harvest_then", "crop": "wheat", "month": "Feb", "new_do": "plant", "new_crop": "rice", "new_month": "Jun"}]
    soft = bs.action_lines(acts, "NOT YET VERIFIABLE")
    assert soft == [{"text": "farm.act_sow_usual", "fill": {"crop": "wheat", "sow_month": "Oct"}},
                    {"text": "farm.act_harvest_usual", "fill": {"crop": "wheat", "harvest_month": "Feb"}},
                    {"text": "farm.act_then_plant_usual", "fill": {"new_crop": "rice", "sow_month": "Jun"}}]
    assert bs.action_lines(acts, "ESTIMATE") == soft
    assert bs.action_lines(acts, "VERIFIED")[0] == {"text": "farm.act_sow", "fill": {"crop": "wheat", "sow_month": "Oct"}}


def test_the_plan_word_is_the_verdict_against_the_farmers_own_plan():
    assert bs.plan_word({"better": 20, "same": 3, "worse": 1}, 24, "ESTIMATE") == {"verdict": "better", "text": "farm.word_better_usual"}
    assert bs.plan_word({"better": 3, "same": 15, "worse": 6}, 24, "ESTIMATE")["text"] == "farm.word_same"
    assert bs.plan_word({"better": 5, "same": 7, "worse": 12}, 24, "NOT YET VERIFIABLE")["text"] == "farm.word_worse_usual"
    assert bs.plan_word({"better": 8, "same": 8, "worse": 8}, 24, "ESTIMATE")["text"] == "farm.word_mixed"
    assert bs.plan_word({"better": 20, "same": 3, "worse": 1}, 24, "VERIFIED")["text"] == "farm.word_better"


def test_the_animation_winner_has_the_most_seasons_that_did_not_fail():
    plans = {"current": [51, 46, 48, 55], "cover_gap": [73, 70, 49, 81], "safest": [58, 52, 54, 64]}
    a = bs.animation(plans, ["current", "cover_gap", "safest"], failed_below=50)
    assert [p["green"] for p in a["plans"]] == [[True, False, False, True], [True, True, False, True], [True, True, True, True]]
    assert a["winner"] == "safest"                                   # 4 green beats 3
    tie = bs.animation({"a": [60, 40], "b": [80, 40]}, ["a", "b"], failed_below=50)
    assert tie["winner"] == "b"                                      # 1 green each: the higher median wins


def test_a_weather_line_takes_the_farmers_crop_and_says_may():
    block = {"key": "Dec", "usual": {"rain": "dry", "temp": "cold"},
             "dangers": [{"check": "dry_spell", "kind": "dry_spell", "crop": "wheat", "tip": "dry_spell"},
                         {"check": "potato_cold", "kind": "cold", "crop": "potato", "tip": "cold"}]}
    line = bs.weather_line(block, crops={"potato"}, can_water=False)
    assert line == {"usual": {"text": "farm.wx_usual", "fill": {"month": "Dec", "rain_word": "dry", "temp_word": "cold"}},
                    "danger": {"text": "farm.wx_hurt_potato_cold", "fill": {"crop": "potato"}},
                    "tip": {"text": "weather.tip_cold"}}
    # no danger for the farmer's crops: the first danger of any crop; watering drops dry spells
    assert bs.weather_line(block, crops={"lentil"}, can_water=False)["danger"]["text"] == "farm.wx_hurt_dry_spell"
    assert bs.weather_line(block, crops={"lentil"}, can_water=True)["danger"]["text"] == "farm.wx_hurt_potato_cold"
    calm = bs.weather_line({"key": "Apr", "usual": {"rain": "some_rain", "temp": "mild"}, "dangers": []}, {"potato"}, False)
    assert calm["danger"] == {"text": "farm.wx_calm"} and calm["tip"] is None


def test_every_text_key_in_the_farmer_files_is_a_real_word_and_soft_unless_verified():
    """Each farmer line names a words.json key that exists; a plain (not '_usual') action or plan word appears only
    when its label is VERIFIED (rules.yaml farmer_answers.wording)."""
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    shared = json.loads((repo / "site" / "data" / "words.json").read_text())["shared"]
    for path in sorted((repo / "site" / "data" / "simple").glob("*.json")):
        doc = json.loads(path.read_text())
        keys = []

        def walk(o):
            if isinstance(o, dict):
                if isinstance(o.get("text"), str):
                    keys.append(o["text"])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk({k: doc[k] for k in ("guess", "plan_words", "actions", "weather_lines")})
        for k in set(keys):
            grp, key = k.split(".")
            assert key in shared[grp], (path.name, k)
        if doc["labels_used"]["plan_months"] != "VERIFIED":
            assert not any(k.startswith("farm.act_") and not k.endswith("_usual") for k in keys), path.name
        if doc["labels_used"]["replay_window"] != "VERIFIED":
            assert not any(k in ("farm.word_better", "farm.word_worse") for k in keys), path.name
