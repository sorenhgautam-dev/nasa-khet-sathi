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
