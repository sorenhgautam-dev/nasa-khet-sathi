"""site/data/story.json, the "How we know" page as a data story (2026-11-14).

Unit tests use small made-up tables (they test the code, never the page); the tests marked "real" read the project's own
outputs under data/ and skip where those are absent (data/ is git-ignored).
"""
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from pipeline.export import build_story as bs

REPO = Path(__file__).resolve().parents[1]
STORY = REPO / "site" / "data" / "story.json"


# --- helpers ---------------------------------------------------------------------------------------------------------

def test_ne_digits_converts_every_digit_and_keeps_the_rest():
    assert bs.ne_digits("2017: 1,375 mm, 0.88x") == "२०१७: १,३७५ mm, ०.८८x"


def test_ne_digits_keeps_product_names():
    assert bs.ne_digits("FAO-56, L4, SSP2-4.5 र 2040") == "FAO-56, L4, SSP2-4.5 र २०४०"


def test_sentences_split_on_full_stops_but_not_decimals():
    assert bs.sentences("It read 0.88 times. Then 1.6!", "en") == ["It read 0.88 times", "Then 1.6"]
    assert bs.sentences("पहिलो वाक्य। दोस्रो वाक्य।", "ne") == ["पहिलो वाक्य", "दोस्रो वाक्य"]


def test_word_limit_finds_long_sentences():
    assert bs.long_sentences("One two three. One two three four five six seven eight nine.", "en", 8) == [
        "One two three four five six seven eight nine"]


# --- yearly and monthly summaries ------------------------------------------------------------------------------------

def _gauge_table():
    rows = []
    for year, weight, stations in ((2015, 97.0, 50.0), (2016, 96.0, 48.0), (2017, 60.0, 1.0), (2018, 70.0, None)):
        for m in range(1, 13):
            rows.append({"month": f"{year}-{m:02d}", "imerg_gauge_weight_pct": weight + (m % 2),
                         "gpcc_stations": stations, "gpcc_rain_mm": 10.0 if stations is not None else None})
    return pd.DataFrame(rows)


def test_yearly_gauge_weight_has_mean_and_month_range():
    out = bs.yearly_gauge_weight(_gauge_table())
    assert out[2015] == {"mean": 97.5, "low": 97.0, "high": 98.0, "months": 12}
    assert out[2017]["mean"] == 60.5


def test_yearly_station_counts_skip_years_without_counts():
    out = bs.yearly_station_counts(_gauge_table())
    assert out == {2015: 50.0, 2016: 48.0, 2017: 1.0}


def test_break_year_is_the_first_year_the_gauge_share_falls():
    assert bs.break_year(bs.yearly_gauge_weight(_gauge_table()), below_pct=90) == 2017


def test_yearly_totals_use_complete_years_only():
    dates = pd.date_range("2015-01-01", "2016-03-31", freq="D")
    totals = bs.yearly_totals(dates, [1.0] * len(dates))
    assert totals == {2015: 365.0}            # 2016 is incomplete


def test_monthly_mean_ndvi_uses_hls_clear_observations_only():
    df = pd.DataFrame({"date": pd.to_datetime(["2014-01-03", "2014-01-20", "2014-01-25", "2014-02-02"]),
                       "source": ["hls_l30", "hls_s30", "modis", "hls_s30"],
                       "ndvi": [0.4, 0.6, 0.9, None]})
    assert bs.monthly_mean_ndvi(df, 2014, 2014) == [["2014-01-15", 0.5]]


def test_sen_line_passes_through_the_median_residual():
    t = [0.0, 1.0, 2.0, 3.0]
    y = [1.0, -1.0, -3.0, -5.0]
    a, b = bs.sen_line(t, y, slope=-2.0)
    assert (a, b) == (1.0, -2.0)


# --- event timeline --------------------------------------------------------------------------------------------------

EVENTS = {
    "events": [
        {"id": "valley_flood", "years": [2002], "category": "flood", "kathmandu_valley": "yes", "months": "Jul"},
        {"id": "terai_flood", "years": [2017], "category": "flood", "kathmandu_valley": "no", "months": "Aug"},
        {"id": "valley_dry_a", "years": [2021], "category": "drought", "kathmandu_valley": "yes", "months": "Jan"},
        {"id": "valley_dry_b", "years": [2023], "category": "drought", "kathmandu_valley": "yes", "months": "Jan"},
        {"id": "cold", "years": [2013], "category": "frost", "kathmandu_valley": "yes", "months": "Jan"},
    ],
    "negative_controls": [{"id": "wet_monsoon_2023", "years": [2023], "summary": "normal"},
                          {"id": "wet_monsoon_2024", "years": [2024], "summary": "wet"}],
}
REPLAY = [
    {"year": 2002, "event": "flood"}, {"year": 2004, "event": "flood"}, {"year": 2013, "event": "none"},
    {"year": 2017, "event": "none"}, {"year": 2021, "event": "none"},
    {"year": 2023, "event": "drought"}, {"year": 2024, "event": "drought", "event_season": "winter"},
]


def test_events_found_missed_and_quiet():
    rows, summary = bs.match_events(REPLAY, EVENTS)
    by_year = {r["year"]: r for r in rows}
    assert by_year[2002]["records"][0]["result"] == "found"
    assert by_year[2017]["records"][0]["result"] == "quiet"          # outside the valley, not flagged: right
    assert by_year[2021]["records"][0]["result"] == "missed"
    assert by_year[2004]["result"] == "no record"
    assert summary["valley_floods"] == [1, 1]
    assert summary["valley_droughts"] == [1, 2]
    assert summary["unrecorded_flood_years"] == [2004]


def test_frost_is_never_a_yearly_event():
    rows, _ = bs.match_events(REPLAY, EVENTS)
    assert all(rec["category"] != "frost" for r in rows for rec in r["records"])


def test_negative_control_fails_when_the_monsoon_is_called_dry():
    _, summary = bs.match_events(REPLAY, EVENTS)
    controls = {c["year"]: c["passes"] for c in summary["negative_controls"]}
    assert controls == {2023: False, 2024: True}     # 2023 dry in both seasons; 2024 dry in winter only


# --- the probe -------------------------------------------------------------------------------------------------------

REAL_BENCH = {"made_up": False, "label": "bench test", "sources": ["serial"], "date": "2026-11-14",
              "cups": [{"cup_id": "c1", "water_pct": 0.0, "value_pct": 8.0}, {"cup_id": "c2", "water_pct": 10.0,
                                                                                "value_pct": 20.0}],
              "excluded": [], "accurate": {"model": "line", "coef": [-6.67, 0.833], "loo_mae_water_pct": 1.2,
                                           "range_probe_pct": [8.0, 20.0]},
              "proofs": {"steady": True, "order": True, "accurate": 1.2, "temperature": True}}


def test_probe_chart_is_not_ready_without_a_bench_file():
    chart = bs.chart_probe(None)
    assert chart["status"] == "not_ready" and chart["series"] == []


@pytest.mark.parametrize("change", [{"made_up": True}, {"label": "REHEARSAL: made-up"}, {"sources": ["fake_probe"]}])
def test_probe_chart_refuses_the_rehearsal(change):
    assert bs.chart_probe({**REAL_BENCH, **change})["status"] == "not_ready"


def test_probe_chart_from_a_real_bench_test():
    chart = bs.chart_probe(REAL_BENCH)
    assert chart["status"] == "ready"
    assert chart["series"][0]["points"] == [[0.0, 8.0], [10.0, 20.0]]


# --- the schema and the real page ------------------------------------------------------------------------------------

def test_story_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(bs.load_schema())


def _real_inputs():
    try:
        return bs.load_inputs(REPO, "demo")
    except FileNotFoundError as e:
        pytest.skip(f"real outputs not present: {e}")


@pytest.fixture(scope="module")
def story():
    return bs.build_story(_real_inputs(), generated="2026-11-14")


def test_real_story_validates(story):
    assert bs.validate_story(story) == []


def test_real_story_is_light(story):
    assert len(json.dumps(story, ensure_ascii=False).encode()) < 150_000


def test_every_chart_lists_existing_inputs_and_sources(story):
    for chart in story["charts"]:
        assert chart["sources"], chart["id"]
        paths = story["inputs"][chart["id"]]
        assert paths, chart["id"]
        for p in paths:
            assert (REPO / p).exists(), p
            assert "fixture" not in p and "REHEARSAL" not in p


def test_every_section_chart_exists(story):
    ids = {c["id"] for c in story["charts"]}
    for section in story["sections"]:
        assert set(section["charts"]) <= ids


def test_short_plain_sentences(story):
    texts = []
    for c in story["charts"]:
        texts += [c["title"], c["caption"]]
    for r in story["report_card"]:
        texts += [r["thing"], r["why"]]
    for s in story["satellites"]:
        texts += [s["job"], s["checked"]]
    for r in story["resources"]:
        texts.append(r["how"])
    for t in texts:
        for lang in ("en", "ne"):
            assert bs.long_sentences(t[lang], lang, 8) == [], (lang, t[lang])


def test_report_card_covers_every_thing_and_cites_real_validation_rows(story):
    ids = [r["id"] for r in story["report_card"]]
    assert ids == ["seasons", "bare_days", "rain", "harvest", "plan_ranking", "floods", "dry_years", "frost",
                   "groundwater", "onset", "probe", "outlook_2040"]
    validation = (REPO / "VALIDATION.md").read_text()
    for r in story["report_card"]:
        assert r["confidence"] in ("high", "medium", "low")
        for ref in r["refs"]:
            assert re.search(rf"^\| {re.escape(ref)} \|", validation, re.M), (r["id"], ref)


def test_resources_cover_the_challenge_list(story):
    names = [r["name"] for r in story["resources"]]
    assert len(names) == len(bs.RESOURCES) == 24
    gaez = next(r for r in story["resources"] if r["name"].startswith("FAO GAEZ"))
    assert gaez["status"] == "not used" and gaez["label"] == "linked as a reference, data not used"
    assert gaez["link"].startswith("https://gaez.fao.org")
    for r in story["resources"]:
        if r["status"] == "equivalent":
            assert r["instead"]


def test_satellite_inventory_names_every_mission(story):
    missions = " ".join(s["mission"] for s in story["satellites"])
    for name in ("GPM", "Landsat", "Sentinel-2", "Terra", "SMAP", "GRACE", "ECOSTRESS", "SRTM", "CERES", "MERRA-2",
                 "Sentinel-1", "CHIRPS", "GLDAS", "NEX-GDDP-CMIP6"):
        assert name in missions, name


def test_real_rain_numbers_are_the_data(story):
    inputs = _real_inputs()
    chart = next(c for c in story["charts"] if c["id"] == "rain_jump")
    gpm = dict(chart["series"][0]["points"])
    sums = inputs["gpm"].groupby(inputs["gpm"].date.dt.year).rain_mm.sum()
    assert gpm[2018] == round(float(sums[2018]))


def test_area_map_points_to_the_site_file(story):
    chart = next(c for c in story["charts"] if c["id"] == "area_map")
    assert chart["kind"] == "map" and chart["link"] == "data/area/demo.json"
    assert (REPO / "site" / chart["link"]).exists()


def test_farmer_years_slot_is_coming_with_no_data(story):
    chart = next(c for c in story["charts"] if c["id"] == "best_worst_years")
    assert chart["status"] == "coming" and chart["series"] == [] and chart["rows"] == []


def test_written_file_matches_the_schema():
    if not STORY.exists():
        pytest.skip("site/data/story.json not built yet")
    story = json.loads(STORY.read_text())
    assert bs.validate_story(story) == []
    assert STORY.stat().st_size < 150_000
