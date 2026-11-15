"""site/data/behind.json: "Behind the scenes: your field, seen by NASA" (owner, 2026-11-15).

Unit tests use small made-up tables (they test the counting, never the page); the tests marked "real" read the project's
own outputs under data/ and skip where those are absent (data/ is git-ignored).
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.export import build_behind as bb
from pipeline.export.build_story import sentences

REPO = Path(__file__).resolve().parents[1]
BEHIND = REPO / "site" / "data" / "behind.json"
SRC = lambda name, res="30 m", years="2001-2003", kind="satellite": {  # noqa: E731
    "name": name, "product": "p", "resolution": res, "years": years, "type": kind}


def _inputs():
    """Three days of rain (one missing), five pictures (two cloudy), two plans, two replay years, three models."""
    fj = {"field": {"name": "Test field (PLACEHOLDER)"},
          "sources": [SRC("GPM IMERG", "0.1 deg (about 10 km)"), SRC("Harmonized Landsat Sentinel-2"), SRC("MODIS Terra", "250 m"),
                      SRC("NASA POWER", "0.5 x 0.625 deg (about 55 km)", kind="model"), SRC("GRACE and GRACE-FO", "about 300 km"),
                      SRC("NASA SMAP L4", "9 km", kind="model"), SRC("NEX-GDDP-CMIP6", "0.25 deg", "1995-2014 and 2026-2040", "model"),
                      SRC("Khet Sathi field twin", "the field", kind="model")],
          "replay": {"current": [{"year": 2002}, {"year": 2003}]},
          "future": {"models": ["a", "b", "c"], "scenarios": ["ssp245", "ssp585"], "period": "2026-2040", "years": [2040]},
          "diary": {"groundwater": {"trend_cm_per_year": -2.57, "direction": "falling"}}}
    return {
        "field": "test", "paths": bb.input_paths("test"), "field_json": fj,
        "gpm": pd.DataFrame({"date": pd.to_datetime(["2001-01-01", "2001-01-02", "2002-01-01"]), "rain_mm": [0.0, None, 3.0]}),
        "greenness": pd.DataFrame({"source": ["hls_l30", "hls_s30", "hls_s30", "modis", "modis"], "ndvi": [0.5, None, 0.4, 0.3, None]}),
        "plans": {"n_plans": 2, "plans": [{"crops": ["rice", "potato"], "years": [2002, 2003]}, {"crops": ["rice"], "years": [2001, 2002, 2003]}]},
        "future": {"n_models": 3},
        "field_config": {"polygon": [[85.0, 27.0], [85.0006, 27.0], [85.0006, 27.00054], [85.0, 27.00054]]},
    }


def test_size_reads_the_first_length_in_metres_or_kilometres():
    assert bb.size_m("30 m") == 30 and bb.size_m("0.1 deg (about 10 km)") == 10_000
    assert bb.size_m("about 300 km") == 300_000 and bb.size_m("9 km") == 9_000
    with pytest.raises(ValueError):
        bb.size_m("0.25 deg")


def test_every_big_number_is_counted_from_the_tables():
    got = {n["id"]: n for n in bb.numbers(_inputs())}
    assert got["rain_days"]["value"] == 2                       # days with a rain value: the missing day is not counted
    assert got["images"]["value"] == 5 and "3 were clear enough" in got["images"]["detail"]["en"]
    assert got["years_replayed"]["value"] == 2 and "2002 to 2003" in got["years_replayed"]["detail"]["en"]
    assert got["climate_models"]["value"] == 3 and "2 possible futures" in got["climate_models"]["detail"]["en"]
    assert got["seasons"]["value"] == 2 * 2 + 1 * 3             # each plan: its crops times its years
    assert got["datasets"]["value"] == 7                        # the field file's sources, our own twin not counted
    assert all(n["from"] and all(set(s) == {"name", "resolution", "years", "type"} for s in n["sources"]) for n in got.values())
    assert got["rain_days"]["detail"]["ne"].startswith("२००१")  # Nepali digits are Devanagari


def test_the_model_counts_must_agree():
    inp = _inputs()
    inp["future"]["n_models"] = 4
    with pytest.raises(ValueError, match="climate models"):
        bb.numbers(inp)


def test_the_pixel_picture_uses_the_sizes_the_source_list_states():
    px = bb.pixels(_inputs())
    assert [(q["name"], q["size_m"]) for q in px["squares"]] == [("HLS", 30), ("SMAP", 9000), ("GPM", 10000), ("GRACE", 300000)]
    assert 55 < px["field_m"] < 65                              # the square root of the outline's area: a 60 m square


def test_the_temperature_chart_draws_the_rules_frost_and_heat_lines():
    days = pd.date_range("2001-01-01", "2002-12-31")
    w = pd.DataFrame({"date": days, "tmax_c": 20.0 + days.month, "tmin_c": 5.0 + days.month, "tmin_frost_c": 4.0 + days.month})
    rules = {"cold_nights": {"frost_night_c": 2.0}, "heat_clock": {"potato_heat": {"at_or_above_c": 35}},
             "power_rain": {"never_fill_years": [2001, 2002, 2003]}}
    c = bb.power_chart(w, rules, SRC("NASA POWER", "0.5 x 0.625 deg (about 55 km)", kind="model"))
    by = {s["name"]["en"]: s["points"] for s in c["series"]}
    assert by["Day, usual"][0] == ["Jan", 21.0] and by["Night, usual"][11] == ["Dec", 17.0]
    assert by["Frost line: 2 °C"] == [["Jan", 2.0], ["Dec", 2.0]] and by["Heat line: 35 °C"] == [["Jan", 35], ["Dec", 35]]
    assert by["Coldest night to hottest day, 2001-2002"][0] == ["Jan", [5.0, 21.0]]
    assert "model-based" in c["sources"][0] and "2001-2002" in c["sources"][0] and "2001-2003" in c["note"]["en"]


def test_a_tag_must_open_cards_that_exist():
    doc = json.loads(BEHIND.read_text())
    assert bb.validate_behind(doc) == []
    doc["tags"]["rain"] = ["nope"]
    assert bb.validate_behind(doc) == ["tags/rain: no card 'nope'"]


# --- the published file -------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def behind():
    return json.loads(BEHIND.read_text())


def test_published_file_matches_the_schema(behind):
    assert bb.validate_behind(behind) == [] and behind["ne_review"] == "needs native-speaker review"
    assert [n["id"] for n in behind["numbers"]] == ["rain_days", "images", "years_replayed", "climate_models", "seasons", "datasets"]


def test_every_card_has_a_ready_chart_and_one_plain_sentence(behind):
    story = {c["id"]: c for c in json.loads((REPO / "site" / "data" / "story.json").read_text())["charts"]}
    own = {c["id"]: c for c in behind["charts"]}
    assert [c["id"] for c in behind["cards"]] == ["gpm", "hls", "power", "grace", "nexgddp", "smap_gldas"]
    for c in behind["cards"]:
        chart = own.get(c["chart"]) or story[c["chart"]]
        assert chart["status"] == "ready" and chart["series"], c["id"]
        assert len(sentences(c["say"]["en"], "en")) == 1 and len(c["say"]["en"].split()) <= 12, c["id"]   # one short sentence
        assert set(c.get("only", [])) <= {k["id"] for k in (chart["x"].get("categories") or [])}
    assert {c["id"]: c["kind"] for c in behind["cards"]}["power"] == "model"                      # labelled as worked out by computer


def test_the_flow_ends_at_the_farmers_answers_with_the_replays_own_year_count(behind):
    field = json.loads((REPO / "site" / "data" / "fields" / f"{behind['field']}.json").read_text())
    n = len(field["replay"]["current"])
    # C (owner, 2026-11-15): plain names, "Field Twin" only once, in brackets, in How we know's explanation
    assert [f["en"] for f in behind["flow"]] == ["NASA data", "A copy of your field", f"Tested in {n} past years", "Your answers"]


def test_real_published_file_is_what_the_exporter_builds_now(behind):
    if not (REPO / "data" / "clean" / behind["field"] / "gpm.parquet").exists():
        pytest.skip("data/ is not here")
    inp = bb.load_inputs(REPO, behind["field"])
    assert bb.build_behind(inp) == behind, "behind.json is stale: run .venv/bin/python -m pipeline.export.build_behind"
    by = {n["id"]: n["value"] for n in behind["numbers"]}
    assert by["rain_days"] == int(inp["gpm"]["rain_mm"].notna().sum()) == len(inp["gpm"])       # no day without rain data
    assert by["images"] == len(inp["greenness"]) and by["years_replayed"] == len(inp["field_json"]["replay"]["current"])


# --- the site ---------------------------------------------------------------------------------------------------------

def test_nothing_of_the_section_loads_on_the_first_screen():
    site = REPO / "site"
    assert "behind" not in (site / "index.html").read_text()                       # no script, no data on the first screen
    app = (site / "js" / "app.js").read_text()
    assert "loadScript('js/behind.js')" in app and "IntersectionObserver" in app   # loaded when it is scrolled to
    assert "data/behind.json" in (site / "js" / "behind.js").read_text()


def test_the_farmer_tags_have_words_in_every_language(behind):
    words = json.loads((REPO / "site" / "data" / "words.json").read_text())
    farm, langs = words["shared"]["farm"], [x["code"] for x in words["languages"]]
    for kind in behind["tags"]:
        assert all(farm[f"tag_{kind}"].get(lang) for lang in langs), kind
        assert "{year_count}" in farm[f"tag_{kind}"]["en"]
    assert farm["behind_title"]["en"] == behind["title"]["en"] and farm["behind_title"]["ne"] == behind["title"]["ne"]
