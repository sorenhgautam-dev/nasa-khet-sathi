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


BS = {k: {"en": e, "ne": n} for k, e, n in (("Jun", "Asar", "असार"), ("Sep", "Asoj", "असोज"), ("Oct", "Kartik", "कात्तिक"),
                                             ("Nov", "Mangsir", "मंसिर"), ("Dec", "Poush", "पुस"), ("Feb", "Falgun", "फागुन"),
                                             ("Mar", "Chaitra", "चैत"), ("Apr", "Baisakh", "वैशाख"))}


def test_crop_months_shows_the_models_and_the_calendars_harvest_month_and_the_field_from_space():
    """Fix A4 (rules.yaml farmer_answers.actions_calendar_months): wheat sown 15 Oct ends 3 Mar in the model (Falgun) and
    is harvested 15 Mar on FAO's calendar (Chaitra); sown 15 Nov, 4 Apr (Chaitra) against 15 Apr (Baisakh); potato sown
    30 Oct, 21 Feb against 28 Feb (both Falgun). From space: two winter seasons ending 1 May and 21 May, median 11 May."""
    fj = {"plans": [{"id": "current", "crops": [{"crop": "rice", "start": "06-23", "end": "10-10"}, {"crop": "potato", "start": "10-30", "end": "02-21"}]},
                    {"id": "cover_gap", "crops": [{"crop": "rice", "start": "06-23", "end": "10-10"}, {"crop": "wheat", "start": "10-15", "end": "03-03"}]}],
          "current_options": {"options": [{"id": "rice_wheat", "crops": [{"crop": "rice", "start": "06-23", "end": "10-10"},
                                                                         {"crop": "wheat", "start": "11-15", "end": "04-03"}]}]}}
    cal = {"wheat": {"windows": [{"sow": "10-15", "sow_end": "11-15", "harvest": "03-15", "harvest_end": "04-15"}]},
           "potato": {"windows": [{"sow": "10-15", "sow_end": "11-15", "harvest": "02-15", "harvest_end": "03-15"}]},
           "rice": {"windows": [{"sow": "06-01", "sow_end": "07-15", "harvest": "10-15", "harvest_end": "11-15"}]}}
    seasons = {"chosen": {"seasons_by_year": {
        "2015": [{"start": "2014-12-27", "peak": "2015-03-24", "end": "2015-05-01", "source": "hls", "peak_ndvi": 0.7},
                 {"start": "2015-06-20", "peak": "2015-08-20", "end": "2015-10-20", "source": "hls", "peak_ndvi": 0.8}],
        "2016": [{"start": "2016-01-16", "peak": "2016-03-16", "end": "2016-05-21", "source": "hls", "peak_ndvi": 0.7}]}}}
    c = bs.chart_crop_months(fj, cal, seasons, BS)
    assert c["id"] == "crop_months" and c["section"] == "seasons" and c["kind"] == "table"
    rows = {(r["crop"], r["sown"]): r for r in c["rows"] if "crop" in r}
    assert (rows[("wheat", "Oct")]["model"], rows[("wheat", "Oct")]["calendar"]) == ("Feb", "Mar")
    assert (rows[("wheat", "Nov")]["model"], rows[("wheat", "Nov")]["calendar"]) == ("Mar", "Apr")
    assert (rows[("potato", "Oct")]["model"], rows[("potato", "Oct")]["calendar"]) == ("Feb", "Feb")
    assert (rows[("rice", "Jun")]["model"], rows[("rice", "Jun")]["calendar"]) == ("Sep", "Oct")
    assert "Falgun" in rows[("wheat", "Oct")]["text"]["en"] and "Chaitra" in rows[("wheat", "Oct")]["text"]["en"]
    space = [r for r in c["rows"] if r.get("from_space")]
    assert space and space[0]["winter_end"] == "05-11" and space[0]["winter_seasons"] == 2


def test_the_offline_section_says_the_first_visit_needs_internet_and_live_readings_need_the_laptop():
    c = bs.chart_offline()
    text = " ".join(r["text"]["en"] for r in c["rows"])
    assert c["section"] == "offline" and "once with internet" in text and "no internet" in text and "laptop" in text
    assert any(s[0] == "offline" and "offline_use" in s[2] for s in bs.SECTIONS)
    assert all(r["text"]["ne"] and r["head"]["ne"] for r in c["rows"])


def test_the_limits_block_groups_the_compliance_table_into_checked_and_estimates():
    """Owner's plan, part A2 (2026-11-15): 'What this tool can and cannot tell you': a real farm and sample fields, no
    farmer's answers yet; a starting point; check with your local agriculture office; which parts are checked (VERIFIED in
    the compliance table) and which are estimates (ESTIMATE, and NOT YET VERIFIABLE, which the wording rule treats as an
    estimate: rules.yaml farmer_answers.wording)."""
    rows = [{"id": "a", "thing": {"en": "Rainy and dry months", "ne": "क"}, "status": "VERIFIED"},
            {"id": "b", "thing": {"en": "Flood years", "ne": "ख"}, "status": "ESTIMATE"},
            {"id": "c", "thing": {"en": "Groundwater", "ne": "ग"}, "status": "NOT YET VERIFIABLE"}]
    L = bs.limits_block(rows)
    assert [x["en"] for x in L["checked"]["items"]] == ["Rainy and dry months"]
    assert [x["en"] for x in L["estimates"]["items"]] == ["Flood years", "Groundwater"]
    text = " ".join(x["en"] for x in L["lines"])
    assert "real farm" in text and "sample fields" in text and "No farmer" in text and "starting point" in text
    assert "agriculture office" in text
    for x in [L["title"], L["checked"]["title"], L["estimates"]["title"], *L["lines"]]:
        assert x["en"] and x["ne"] and len(x["en"].split()) <= 8, x       # farmer screens: 8 words or fewer, both languages


def test_our_promise_says_free_no_ads_no_accounts_data_on_the_phone_and_open():
    """Owner, 2026-11-15 (afternoon): 'Our promise' on Home and How we know: free for every farmer, always; no ads and no
    accounts; the field's data and photos stay on the phone; open code and open data, so anyone can check our work or
    bring it to their own valley. Nepali first, marked for review; 8 words or fewer per line."""
    P = bs.promise_block()
    text = " ".join(x["en"] for x in P["lines"])
    for w in ("Free for every farmer, always", "No ads", "No accounts", "photos stay on your phone", "Open code",
              "open data", "check our work", "your own valley"):
        assert w in text, w
    for x in [P["title"], *P["lines"]]:
        assert x["en"] and x["ne"] and len(x["en"].split()) <= 8, x
    assert P["ne_review"] == bs.NE_REVIEW
    money = re.compile(r"\b(customers?|markets?|moneti[sz]\w*|revenue|business|price\w*|sell\w*)\b", re.I)
    assert not money.search(text)


def test_the_rain_chapter_calls_the_2017_change_fewer_gauges_never_a_fault():
    """Owner, 2026-11-15: NASA's rain combines satellites with ground gauges; from 2017 far fewer gauges near our valley
    fed into it, so the record stepped up, and we corrected for it. Never a flaw, an error or a bug in NASA's data."""
    src = open("pipeline/export/build_story.py", encoding="utf-8").read()
    for bad in ("vanished", "lost its gauges", "found the break", "jumped", "त्यो त्रुटि भेटेर", "Gauge reports stop", "Our fix"):
        assert bad not in src, bad
    assert "fewer gauges fed NASA's rain here" in src and "We corrected for it." in src


def test_home_and_how_we_know_show_the_limits_block_and_its_lists_only_on_their_own_field():
    app = (REPO / "site" / "js" / "app.js").read_text()
    how = (REPO / "site" / "js" / "how.js").read_text()
    body = re.search(r"function limitsBox\(lazy\) \{.*?\n  \}", app, re.S).group(0)
    assert "st.limits" in body and "st.field === S.fid" in body            # the lists belong to story.json's field
    assert "both.append(scr, promiseBox(true), limitsBox(true), behindBox(true))" in app   # Home: below the first screen, lazily
    assert "K.limitsBox()" in how and how.index("K.promiseBox()") > how.index("K.limitsBox()")   # How we know: promise first (unshifted last)
    pbody = re.search(r"function promiseBox\(lazy\) \{.*?\n  \}", app, re.S).group(0)
    assert "st.promise" in pbody and "P(Pr.title)" in pbody


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
                   "weather_ahead", "groundwater", "onset", "probe", "outlook_2040"]
    validation = (REPO / "records" / "checks.txt").read_text()
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
