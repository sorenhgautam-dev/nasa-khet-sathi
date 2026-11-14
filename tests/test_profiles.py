"""Country profiles (owner's item 3, 2026-11-14): config/countries/NP.yaml and default.yaml, pipeline/fetch/profiles.py,
the FAO zone calendar (pipeline/fetch/cropcalendar.py) and the default's whole-year drought (pipeline/plans/events.py).
Nepal's outputs must not change: every moved setting gives Nepal fields exactly what the code used before."""
import json

import pandas as pd
import pytest

from pipeline.fetch import cropcalendar as cc
from pipeline.fetch import profiles as pr
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules
from pipeline.plans import events as ev

NEPAL = ["demo", "sample-1", "sample-2", "sample-3", "sample-4"]
RULES = load_rules()


# --- the files ---

def test_every_setting_has_a_value_and_a_source_and_the_default_has_them_all():
    P = pr.load_profiles()
    assert set(P) >= {"NP", "default"}
    assert set(P["default"]) == set(pr.SETTINGS)
    assert P["NP"]["country"] == {"iso2": "NP", "names": ["Nepal"]}


def test_a_setting_without_a_source_is_refused(tmp_path):
    (tmp_path / "default.yaml").write_text("country: {value: {iso2: null, names: []}}\n")
    with pytest.raises(pr.ProfileError, match="no source"):
        pr.load_profiles(tmp_path)


def test_a_country_file_must_be_named_by_its_code_and_unknown_settings_are_refused(tmp_path):
    good = (pr.COUNTRIES / "default.yaml").read_text()
    (tmp_path / "default.yaml").write_text(good)
    (tmp_path / "XX.yaml").write_text("country: {value: {iso2: NP, names: [Nepal]}, source: s}\n")
    with pytest.raises(pr.ProfileError, match="file name"):
        pr.load_profiles(tmp_path)
    (tmp_path / "XX.yaml").write_text("country: {value: {iso2: XX, names: [X]}, source: s}\nsoil: {value: 1, source: s}\n")
    with pytest.raises(pr.ProfileError, match="unknown settings"):
        pr.load_profiles(tmp_path)


def test_the_field_picks_its_country_by_name_or_code_and_otherwise_the_default():
    P = pr.load_profiles()
    assert pr.profile_id({"country": "Nepal"}, P) == "NP"
    assert pr.profile_id({"country": "Népal", "country_code": "NP"}, P) == "NP"
    assert pr.profile_id({"country": "Madagascar"}, P) == "default"
    assert pr.profile_id({}, P) == "default"


@pytest.mark.parametrize("fid", NEPAL)
def test_the_five_nepal_fields_use_nepals_profile(fid):
    p = pr.profile_for(load_field(fid))
    assert p["_id"] == "NP" and p["_from"]["rain_classes"] == "NP"


def test_the_field_abroad_has_no_profile_and_takes_every_default():
    p = pr.profile_for(load_field("ambohidratrimo"))
    assert p["_id"] == "default" and set(p["_from"].values()) == {"default"}
    assert p["monsoon_onset"] is None and p["scorecard"] is None and p["fertiliser_notes"]["notes"] == []
    assert p["calendar_system"]["first"] == "gregorian" and p["area_units"]["unit"] == "hectare"


# --- the sourced values (notes/SOURCES_CHECK.md and the pages opened 2026-11-14) ---

def test_nepals_rain_classes_are_dhms_five_with_inclusive_lower_bounds():
    rc = pr.load_profiles()["NP"]["rain_classes"]["classes"]
    assert [(c["min_mm"], c["below_mm"]) for c in rc] == [(0, 10), (10, 50), (50, 100), (100, 200), (200, None)]
    assert [c["id"] for c in rc] == ["light", "moderate", "heavy", "very_heavy", "extremely_heavy"]


def test_nepal_has_no_eight_day_dry_spell_and_both_dry_days_are_under_1_mm():
    P = pr.load_profiles()
    assert P["NP"]["dry_spell"]["kind"] == "CDD" and P["NP"]["dry_spell"]["fixed_length_spell"] is None
    assert P["NP"]["dry_spell"]["national_baseline_days"] == 51
    assert P["NP"]["dry_day"]["below_mm"] == P["default"]["dry_day"]["below_mm"] == RULES["trends"]["dry_day_mm"] == 1.0


def test_the_default_rain_classes_are_etccdis_thresholds_named_by_amount_only():
    rc = pr.load_profiles()["default"]["rain_classes"]["classes"]
    assert [(c["min_mm"], c["below_mm"]) for c in rc] == [(0, 1), (1, 10), (10, 20), (20, None)]
    assert not any("heavy" in c["en"].lower() for c in rc)      # ETCCDI's page gives R10mm and R20mm no such names


def test_nepals_fertiliser_notes_are_sources_check_5_and_6_only():
    notes = pr.load_profiles()["NP"]["fertiliser_notes"]["notes"]
    assert [n["id"] for n in notes] == ["shortage_at_planting", "urea_bag"]
    assert notes[1]["bag_kg"] == 50 and notes[1]["prices_npr"] == {"salt_trading_july_2026": 847, "cooperatives_may_2026": 894.5}


# --- moved settings: Nepal gets exactly what the code used before ---

@pytest.mark.parametrize("fid", NEPAL)
def test_nepals_drought_seasons_equal_the_rules_the_code_read_before(fid):
    assert pr.events_rules(load_field(fid), RULES) == RULES["events"]
    assert pr.has_onset_rule(load_field(fid)) is True


@pytest.mark.parametrize("fid", NEPAL)
def test_nepals_crop_library_is_crops_json_unchanged(fid):
    assert load_crops(field=load_field(fid)) == load_crops()


# --- the default's drought year: ETCCDI PRCPTOT, one season, no event season ---

def test_the_default_drought_is_the_calendar_years_wet_day_total_in_the_lowest_fifth():
    idx = pd.date_range("2001-01-01", "2010-12-31")
    rain = pd.Series(0.0, index=idx)
    for y in range(2001, 2011):
        rain[f"{y}-02-10"] = 100.0 + 10 * (y - 2001)            # 100, 110, ... 190 mm
    rain["2001-01-01":"2001-12-31"] += 0.9                      # 2001: 365 days of 0.9 mm (329 mm), all under 1 mm
    rules = pr.events_rules({"country": "Madagascar"}, RULES)
    assert rules["seasons"] == {"year": list(range(1, 13))} and rules["wet_day_mm"] == 1.0
    out = ev.field_year_events(rain, rules)
    # PRCPTOT: 2001 counts only its 100.9 mm wet day, so 2001 (100.9) and 2002 (110) are the two driest of ten
    assert out["detail"]["2001"]["year_mm"] == 100.9 and out["detail"]["2001"]["year_decile"] == 1
    assert [y for y, e in out["events"].items() if e == "drought"] == ["2001", "2002"]
    assert out["event_seasons"] == {}                           # one season: no event_season is exported


def test_a_season_of_all_twelve_months_is_the_calendar_year():
    idx = pd.date_range("2001-01-01", "2002-12-31")
    rain = pd.Series(1.0, index=idx)
    assert ev.season_totals(rain, list(range(1, 13))) == {2001: 365.0, 2002: 365.0}


# --- the FAO zone calendar (api-cropcalendar.apps.fao.org, MG aez 004 as read 2026-11-14) ---

def _session(label, sow, sow_end, harv, harv_end, days, comments=""):
    md = lambda s: {"month": s.split("-")[0].lstrip("0"), "day": s.split("-")[1].lstrip("0")}
    return {"additional_information": label, "comments": comments, "early_sowing": md(sow), "later_sowing": md(sow_end),
            "early_harvest": md(harv), "late_harvest": md(harv_end), "growing_period": {"period": "days", "value": days}}


MG_RICE = {"crop": {"id": "0303", "name": "Rice"}, "aez": {"id": "004", "name": "Highlands Zone South"},
           "sessions": [_session("Riz de saison sèche ou varialoha", "07-15", "08-31", "12-15", "02-28", "145", "Irrigated. Liners"),
                        _session("Riz de saison intermédiaire", "09-15", "11-15", "03-15", "04-30", "155 - 165", "Liners"),
                        _session("Riz de saison de pluie ou vakiambiaty", "11-15", "12-15", "04-15", "05-31", "160 - 165", "Liners")]}


def test_fao_sessions_become_windows_with_the_named_default():
    z = cc.windows_from_fao([MG_RICE], {"rice": "0303", "wheat": "0373"}, {"rice": "Riz de saison de pluie ou vakiambiaty"})
    assert list(z) == ["rice"]                                   # wheat is not in the records: no entry
    w = z["rice"]["windows"]
    assert [(x["sow"], x["sow_end"], x["harvest"], x["harvest_end"], x["days"]) for x in w] == [
        ("07-15", "08-31", "12-15", "02-28", [145]), ("09-15", "11-15", "03-15", "04-30", [155, 165]),
        ("11-15", "12-15", "04-15", "05-31", [160, 165])]
    assert w[0]["note"] == "Riz de saison sèche ou varialoha; Irrigated (FAO)" and z["rice"]["default"] == 2


def test_an_unknown_default_session_is_refused_and_a_session_without_days_is_dropped():
    with pytest.raises(ValueError, match="no FAO session"):
        cc.windows_from_fao([MG_RICE], {"rice": "0303"}, {"rice": "Riz de saison"})
    rec = json.loads(json.dumps(MG_RICE))
    rec["sessions"][0]["growing_period"] = {"period": "", "value": ""}
    z = cc.windows_from_fao([rec], {"rice": "0303"})
    assert len(z["rice"]["windows"]) == 2 and z["rice"]["default"] == 0 and z["rice"]["dropped"][0]["why"]


def test_the_water_words_are_read_from_the_start_of_faos_comments():
    assert cc._note({"comments": "Not irrigated, organic"}) == "rainfed (FAO: 'Not irrigated')"
    assert cc._note({"comments": "Unirrigated. Culture on tanety"}) == "rainfed (FAO: 'Unirrigated')"
    assert cc._note({"additional_information": "Contre-saison", "comments": "Irrigated. Ridge"}) == "Contre-saison; Irrigated (FAO)"
    assert cc._note({"comments": "Irrigated / Rainfed Upolands"}) == ""


def test_stages_are_kept_inside_the_window_and_scaled_to_its_middle_rounded_half_up_outside():
    lib = load_crops()
    # rice: FAO-56 30/30/60/30 = 150 d, window 160-165 d: middle 162.5 -> 163 d
    assert cc.zone_stages(lib["rice"], {"days": [160, 165]}) == {"ini": 33, "dev": 33, "mid": 65, "late": 32}
    # potato: FAO-56 115 d lies in 90-120 d, kept
    assert cc.zone_stages(lib["potato"], {"days": [90, 120]}) == {"ini": 25, "dev": 30, "mid": 30, "late": 30}
    assert sum(cc.zone_stages(lib["potato"], {"days": [120, 150]}).values()) == 135


def test_a_crop_fao_does_not_list_is_never_sown_in_the_zone():
    from pipeline.twin.crops import simulatable_crops
    lib = load_crops()
    zone = {"country": "MG", "aez": "004", "aez_name": "Highlands Zone South",
            "crops": cc.windows_from_fao([MG_RICE], {"rice": "0303"}, {"rice": "Riz de saison de pluie ou vakiambiaty"})}
    out = cc.apply_zone(lib, zone)
    assert sorted(simulatable_crops(out)) == ["rice"]
    assert out["lentil"]["calendar"] == {"windows": [], "default": None} and "not listed" in out["lentil"]["sources"]["simulate"]
    assert out["rice"]["stages_days"] == {"ini": 33, "dev": 33, "mid": 65, "late": 32}
    assert lib["rice"]["stages_days"] == {"ini": 22, "dev": 22, "mid": 44, "late": 22}       # the library is not changed


# --- the index flags a field on the global defaults; a Nepal entry keeps its keys ---

def test_the_index_flags_only_a_field_without_a_country_profile(tmp_path):
    from pipeline.export.build_index import build_index
    from pipeline.export.validate import validate_index
    nepal = {"id": "demo", "name": "Demo", "country": "Nepal", "lat": 27.69, "lon": 85.44, "bbox": [85.38, 27.63, 85.48, 27.71]}
    abroad = {"id": "abroad", "name": "Abroad", "country": "Madagascar", "lat": -18.83, "lon": 47.44,
              "bbox": [47.40, -18.85, 47.44, -18.81]}
    (tmp_path / "fields").mkdir()
    for f in ("demo", "abroad"):
        (tmp_path / "fields" / f"{f}.json").write_text("{}")
    idx = build_index([nepal, abroad], tmp_path)
    assert set(idx["fields"][0]) == {"id", "name", "country", "lat", "lon", "bbox", "sample", "area"}
    assert idx["fields"][1]["profile"] == "default" and idx["fields"][1]["note"]["en"].startswith("A field on another continent")
    assert validate_index(idx) == []
