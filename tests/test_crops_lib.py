"""config/crops.json: every parameter carries a source; anything not published is null and TODO-VERIFY
(CLAUDE.md: never invent numbers). FAO-56 values as printed (Tables 11, 12, 22, 24; read 2026-11-12)."""
import pytest

from pipeline.fetch.cropslib import PARAMS, load_crops
from pipeline.twin.crops import kc_curve, scale_stages, season_length, simulatable_crops, window_day_span

CROPS = ["rice", "wheat", "maize", "potato", "lentil", "mustard", "buckwheat", "finger_millet"]


@pytest.fixture(scope="module")
def lib():
    return load_crops()


def test_all_eight_crops_from_claude_md_are_listed(lib):
    assert sorted(lib) == sorted(CROPS)


@pytest.mark.parametrize("crop", CROPS)
def test_every_parameter_has_a_source_or_is_todo_verify(lib, crop):
    c = lib[crop]
    for p in PARAMS:
        assert p in c, f"{crop}.{p} missing"
        src = c["sources"].get(p, "")
        assert src.strip(), f"{crop}.{p} has no source"
        if c[p] is None:
            assert "TODO-VERIFY" in src, f"{crop}.{p} is null but not marked TODO-VERIFY"


@pytest.mark.parametrize("crop,key,value", [
    ("rice", ("kc", "ini"), 1.05), ("rice", ("kc", "mid"), 1.20), ("rice", ("p",), 0.20),
    ("wheat", ("kc", "mid"), 1.15), ("wheat", ("p",), 0.55), ("wheat", ("ky",), 1.15),
    ("maize", ("kc", "mid"), 1.20), ("maize", ("ky",), 1.25), ("potato", ("ky",), 1.1),
    ("potato", ("p",), 0.35), ("lentil", ("kc", "end"), 0.30)])
def test_values_match_fao56_as_printed(lib, crop, key, value):
    v = lib[crop]
    for k in key:
        v = v[k]
    assert v == pytest.approx(value)


ASSUMED_KY = ["rice", "lentil", "mustard", "buckwheat", "finger_millet"]


@pytest.mark.parametrize("crop", ASSUMED_KY)
def test_crops_without_a_published_ky_use_the_owner_assumed_neutral_1_0(lib, crop):
    c = lib[crop]                     # owner, step-4 review item 4, 2026-11-12
    assert c["ky"] == 1.0 and c["ky_assumed"] is True
    assert "assumed" in c["sources"]["ky"] and "2026-11-12" in c["sources"]["ky"]


@pytest.mark.parametrize("crop", ["wheat", "maize", "potato"])
def test_published_ky_values_are_not_marked_assumed(lib, crop):
    assert lib[crop]["ky_assumed"] is False


def test_only_lentil_is_a_legume(lib):
    assert [c for c in CROPS if lib[c]["legume"]] == ["lentil"]


SIMULATABLE = ["rice", "wheat", "maize", "potato", "lentil", "finger_millet"]


@pytest.mark.parametrize("crop", SIMULATABLE)
def test_season_crops_give_a_full_kc_curve(lib, crop):
    c = lib[crop]
    assert len(kc_curve(c["stages_days"], c["kc"])) == season_length(c["stages_days"])


# --- REVIEW_NOTES H4: which crops the twin can run, and stage lengths that fit the calendar ---

def test_simulatable_crops_leave_out_buckwheat_and_mustard(lib):
    assert sorted(simulatable_crops(lib)) == sorted(SIMULATABLE)


@pytest.mark.parametrize("crop", ["buckwheat", "mustard"])
def test_crops_that_cannot_be_simulated_are_marked_and_say_why(lib, crop):
    assert lib[crop]["simulate"] is False and "TODO-VERIFY" in lib[crop]["sources"]["simulate"]


def test_simulatable_crops_needs_stages_kc_zr_p_and_ky():
    full = {"stages_days": {"ini": 10, "dev": 10, "mid": 10, "late": 10}, "kc": {"ini": 0.3, "mid": 1.0, "end": 0.3},
            "zr_m": 1.0, "p": 0.5, "ky": 1.0}
    lib = {"ok": full, "no_ky": {**full, "ky": None}, "no_kc": {**full, "kc": None},
           "no_stage": {**full, "stages_days": {"ini": 10, "dev": None, "mid": 10, "late": 10}},
           "switched_off": {**full, "simulate": False}}
    assert list(simulatable_crops(lib)) == ["ok"]


def test_every_simulatable_crop_season_fits_its_default_calendar_window(lib):
    for crop, c in simulatable_crops(lib).items():
        w = c["calendar"]["windows"][c["calendar"]["default"]]
        n = season_length(c["stages_days"])
        assert min(w["days"]) <= n <= max(w["days"]), f"{crop}: {n} d outside {w['days']}"


def test_scale_stages_reproduces_the_rice_and_wheat_rows():
    """Largest-remainder rounding (ties in stage order), the rule recorded for rice and wheat."""
    assert scale_stages({"ini": 30, "dev": 30, "mid": 60, "late": 30}, 110) == {"ini": 22, "dev": 22, "mid": 44, "late": 22}
    assert scale_stages({"ini": 15, "dev": 25, "mid": 50, "late": 30}, 140) == {"ini": 18, "dev": 29, "mid": 58, "late": 35}


@pytest.mark.parametrize("crop,fao56,local_days,scaled", [
    ("rice", (30, 30, 60, 30), 110, (22, 22, 44, 22)),
    ("wheat", (15, 25, 50, 30), 140, (18, 29, 58, 35)),
    # maize: 180 d -> 130 d (midpoint of 120-140): 21.67/36.11/43.33/28.89 -> 22/36/43/29
    ("maize", (30, 50, 60, 40), 130, (22, 36, 43, 29)),
    # lentil: 170 d -> 133 d (midpoint 132.5 of 120-145, rounded up): 19.56/27.38/54.76/31.29 -> 20/27/55/31
    ("lentil", (25, 35, 70, 40), 133, (20, 27, 55, 31)),
    # finger millet: 105 d -> 117 d (midpoint of 114-120, transplant to harvest): 16.71/27.86/44.57/27.86 -> 17/28/44/28
    ("finger_millet", (15, 25, 40, 25), 117, (17, 28, 44, 28))])
def test_scaled_crops_keep_the_fao56_row_and_the_method(lib, crop, fao56, local_days, scaled):
    c, keys = lib[crop], ("ini", "dev", "mid", "late")
    assert c["stages_fao56"] == dict(zip(keys, fao56))
    assert c["stages_days"] == dict(zip(keys, scaled)) == scale_stages(c["stages_fao56"], local_days)
    src = c["sources"]["stages_days"]
    assert "FAO-56 Table 11" in src and "scaled in proportion" in src and f"= {'/'.join(map(str, scaled))}" in src


def test_window_day_span_from_its_own_dates():
    # sow 15 Oct - 15 Nov, harvest 15 Mar: 15 Nov -> 15 Mar = 120 d, 15 Oct -> 15 Mar = 151 d (non-leap February)
    assert window_day_span({"sow": "10-15", "sow_end": "11-15", "harvest": "03-15", "harvest_end": "03-15"}) == (120, 151)
    # rice window 1: 15 Jul -> 15 Oct = 92 d, 1 Jun -> 15 Nov = 167 d
    assert window_day_span({"sow": "06-01", "sow_end": "07-15", "harvest": "10-15", "harvest_end": "11-15"}) == (92, 167)


def test_mustard_days_are_recomputed_from_each_windows_own_dates(lib):
    ws = lib["mustard"]["calendar"]["windows"]
    assert [w["days"] for w in ws] == [[151, 181], [120, 151]]
    assert all("recomputed" in w["note"] for w in ws)


def test_every_calendar_window_days_lie_within_what_its_dates_allow(lib):
    for crop, c in lib.items():
        for i, w in enumerate(c["calendar"]["windows"]):
            lo, hi = window_day_span(w)
            assert lo <= min(w["days"]) and max(w["days"]) <= hi, f"{crop} window {i}: {w['days']} vs dates {lo}-{hi}"


def test_finger_millet_days_count_from_transplanting_like_its_sow_dates(lib):
    """The source's own pairs: transplanted 20 Jul 2023, harvested 11 Nov 2023 (114 d); transplanted 12 Aug 2024,
    harvested 10 Dec 2024 (120 d). Counted from nursery sowing they were 149 and 148 d."""
    w = lib["finger_millet"]["calendar"]["windows"][0]
    assert (w["sow"], w["sow_end"], w["days"]) == ("07-20", "08-12", [114, 120])
    assert "from transplanting" in w["note"] and "TODO-VERIFY" in lib["finger_millet"]["sources"]["stages_days"]
