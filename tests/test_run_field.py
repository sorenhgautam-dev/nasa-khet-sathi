"""scripts/run_field.py: one command builds a field from the cached data/ folder, in the order the inputs need."""
import pytest

from scripts import run_field as rf


def _names(field, **kw):
    return [n for n, _ in rf.plan(field, **kw)]


def test_every_step_runs_once_and_each_after_the_steps_it_reads():
    names = _names({"id": "demo"})
    assert names == [s[0] for s in rf.STEPS] and names[-1] == "site_check"
    for before, after in (("weather", "rain_check"), ("diary", "replay"), ("plans", "plans_uncorrected"), ("plans", "plans_dhm"),
                          ("plans", "twin_now"), ("twin_now", "sections"), ("plans", "future"), ("replay_uncorrected",
                          "validation_checks"), ("area_map", "export"), ("export", "index"), ("export", "story"),
                          ("story", "validate"), ("story", "behind"), ("behind", "validate"), ("export", "verification"), ("verification", "story"),
                          ("export", "replay_window"), ("replay_window", "verification"), ("pulse", "verification"),
                          ("checkup", "verification"), ("verification", "labels"), ("labels", "validate"),
                          ("export", "rainrisk"), ("export", "fertiliser"), ("export", "heatclock"), ("heatclock", "labels"),
                          ("export", "weather_ahead"), ("weather_ahead", "replay_window")):
        assert names.index(before) < names.index(after), (before, after)


def test_a_sample_runs_the_core_steps_and_its_break_test_before_the_weather_when_it_has_none():
    sample = {"id": "s", "sample_of": "demo"}
    assert _names(sample) == ["weather", "rain_check", "diary", "replay", "plans", "plans_dhm", "plans_untuned", "export", "weather_ahead",
                              "index", "words",
                              "replay_window", "pulse", "checkup", "rainrisk", "fertiliser", "heatclock", "labels", "simple",
                              "story", "behind", "validate", "site_check"]
    assert _names(sample, has_break_test=False)[:3] == ["rain_check (break test first)", "weather", "rain_check"]


def test_from_and_only_pick_the_steps_and_only_field_steps_get_the_field():
    p = dict(rf.plan({"id": "x"}, start="export"))
    assert list(p)[0] == "export" and p["export"][-2:] == ["--field", "x"] and "--field" not in p["index"]
    assert list(dict(rf.plan({"id": "x"}, only=["plans", "export"]))) == ["plans", "export"]
    with pytest.raises(SystemExit, match="unknown step"):
        rf.plan({"id": "x"}, only=["nope"])
