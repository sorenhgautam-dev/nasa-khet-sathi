"""A field on the global defaults (no country profile; owner's item 3, 2026-11-14): its exports never show Nepal's
sources, slots or checks, and the final check accepts the files that only a country profile makes."""
import json

from pipeline.export import build_field_json as bfj
from pipeline.export import build_labels as bl
from pipeline.export import build_pulse as bp
from pipeline.export import validate as va

ABROAD = {"id": "abroad", "name": "A field abroad", "country": "Madagascar", "country_code": "MG", "lat": -18.834125,
          "lon": 47.436917, "validation_station": "MA000067083"}
NEPAL = {"id": "demo", "name": "Demo", "country": "Nepal", "lat": 27.690767, "lon": 85.441792,
         "validation_station": "NP000444540"}


def _cards(tmp_path, fid, weather=None, calendar=None):
    d = tmp_path / "cards" / fid
    d.mkdir(parents=True)
    if weather is not None:
        (d / "weather.json").write_text(json.dumps({"corrections": {"rain_break": weather}}))
    if calendar is not None:
        (d / "crop_calendar.json").write_text(json.dumps(calendar))
    return tmp_path


def test_labels_name_a_field_abroads_own_station_and_crop_calendar_zone(tmp_path):
    data = _cards(tmp_path, "abroad", calendar={"zone": "MG aez 004 Highlands Zone South"})
    names = bl.source_names(ABROAD, "default", data)
    assert names["ghcn"][0] == "Antananarivo/Ivato station" and "km" in names["ghcn"][1]
    assert names["crop_calendar"] == ("FAO Crop Calendar, MG aez 004 Highlands Zone South", "a zone of the country")
    assert not any("Nepal" in n or "Kathmandu" in n for n, _ in names.values())
    assert bl.source_names(NEPAL, "NP", data) == bl.SOURCES                     # Nepal's names, unchanged


def test_labels_on_the_global_defaults_drop_dhms_sources():
    assert bl.own_sources(["gpm", "dhm_bulletins", "dhm_normals", "chirps", "dhm_onset"], "default") == ["gpm", "chirps"]
    assert bl.own_sources(["gpm", "dhm_bulletins"], "NP") == ["gpm", "dhm_bulletins"]


def test_the_rain_fix_mark_follows_the_fields_own_rain(tmp_path):
    """A label marks 'rain fix' only where the field's rain was corrected (its weather card); with no card the rule's
    flag stands, as before."""
    assert bl.rain_fixed("abroad", _cards(tmp_path, "abroad", weather={"applied": False})) is False
    assert bl.rain_fixed("demo", _cards(tmp_path, "demo", weather={"applied": True})) is True
    assert bl.rain_fixed("none", tmp_path) is None


def test_field_pulse_has_no_typical_seasons_on_the_global_defaults():
    """Nepal's slots (peaks June-November 'monsoon', December-May 'winter') and dates counted from 1 January do not fit
    a field whose rainy season crosses the new year: no typical seasons there (the site shows none)."""
    ss = [{"year": 2016, "slot": "winter", "source": "hls", "greenup": "2015-10-17", "peak": "2015-12-10", "end": "2016-05-16"}]
    assert bp.typical_for("default", ss, ["potato", "rice"], {}) == []


def test_the_method_page_says_whose_choices_it_lists():
    assert bfj.choices_note("NP") is None
    note = bfj.choices_note("default")
    assert "Nepal" in note and "global defaults" in note and "config/countries/default.yaml" in note


def test_the_final_check_accepts_a_field_abroad_without_the_profile_only_files(tmp_path):
    index = {"fields": [{"id": "demo"}, {"id": "abroad", "profile": "default"}]}
    missing = va.missing_feature_files(index, tmp_path, "rainrisk")
    assert missing == ["demo: listed in index.json but no rainrisk/demo.json"]
    assert va.missing_feature_files(index, tmp_path, "pulse") == [
        "demo: listed in index.json but no pulse/demo.json", "abroad: listed in index.json but no pulse/abroad.json"]
    problems = va.launch_problems(tmp_path, index, final=True)
    assert str(tmp_path / "basemap" / "demo.json") in problems and str(tmp_path / "basemap" / "abroad.json") not in problems
