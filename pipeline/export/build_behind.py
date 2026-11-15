"""Build site/data/behind.json: "Behind the scenes: your field, seen by NASA" (owner, 2026-11-15).

    .venv/bin/python -m pipeline.export.build_behind [--field demo] [--out site/data/behind.json]

For judges: how deeply the field's answers use NASA's data, while the farmer's path stays simple. Reads only finished
outputs and reruns nothing. No number is typed in: each big number is counted here from the file named in its `from`;
the mission cards point at charts that are already in site/data/story.json (`chart`), plus one chart built here from the
twin's weather (NASA POWER's temperature through the year, with the frost and heat lines of config/rules.yaml); the
squares of the pixel picture are the sizes the field file's own source list states. Every Nepali text is an SI draft:
the file says "needs native-speaker review".
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
import yaml
from jsonschema import Draft202012Validator

from pipeline.export.build_story import NE_REVIEW, S, T, axis_x, axis_y, chart, fmt
from pipeline.sections.grid import area_m2

REPO = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).with_name("behind_schema.json")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# a farmer answer's small tag (site/js/app.js nasaTags) -> the cards it opens (weather is temperature and rain)
TAGS = {"rain": ["gpm"], "weather": ["power", "gpm"], "space": ["hls"]}


def source(field_json, starts):
    """The field file's own source entry whose name starts with `starts` (name, product, resolution, years, type)."""
    hit = [s for s in field_json["sources"] if s["name"].startswith(starts)]
    if len(hit) != 1:
        raise ValueError(f"the field file must list exactly one source named {starts!r}, found {len(hit)}")
    return hit[0]


def size_m(resolution):
    """'30 m' -> 30, '0.1 deg (about 10 km)' -> 10000, 'about 300 km' -> 300000: the first length in metres or kilometres."""
    m = re.search(r"(\d[\d,.]*)\s*(km|m)\b", resolution)
    if not m:
        raise ValueError(f"no length in metres or kilometres in {resolution!r}")
    return float(m.group(1).replace(",", "")) * (1000 if m.group(2) == "km" else 1)


def numbers(inp):
    """The six big numbers, each counted from one of our own files (`from`), never typed in."""
    gpm, green, fj, plans = inp["gpm"], inp["greenness"], inp["field_json"], inp["plans"]
    p = inp["paths"]
    days = int(gpm["rain_mm"].notna().sum())
    y0, y1 = int(pd.to_datetime(gpm["date"]).dt.year.min()), int(pd.to_datetime(gpm["date"]).dt.year.max())
    by = green.groupby("source")["ndvi"].agg(["size", "count"])          # size: pictures read; count: clear enough to use
    read = {k: int(by["size"].get(k, 0)) for k in ("hls_l30", "hls_s30", "modis")}
    replay = fj["replay"]["current"]
    models = fj["future"]["models"]
    if len(models) != inp["future"]["n_models"]:
        raise ValueError("the field file and data/checks future.json disagree on the number of climate models")
    seasons = sum(len(x["crops"]) * len(x["years"]) for x in plans["plans"])
    sets = [s for s in fj["sources"] if "field twin" not in s["name"]]

    def n(nid, value, en, ne, d_en, d_ne, src, names):
        return {"id": nid, "value": value, "label": T(en, ne), "detail": T(d_en, d_ne), "from": src,
                "sources": [{k: source(fj, name)[k] for k in ("name", "resolution", "years", "type")} for name in names]}

    return [
        n("rain_days", days, "days of rain records", "दिनको वर्षा अभिलेख",
          f"Every day from {y0} to {y1}.", f"{y0} देखि {y1} सम्म हरेक दिन।", f"{p['gpm']}: days with a rain value", ["GPM IMERG"]),
        n("images", int(by["size"].sum()), "pictures from space", "अन्तरिक्षका तस्बिर",
          f"Landsat {fmt(read['hls_l30'])}, Sentinel-2 {fmt(read['hls_s30'])}, MODIS {fmt(read['modis'])}. "
          f"{fmt(int(by['count'].sum()))} were clear enough to use.",
          f"Landsat {fmt(read['hls_l30'])}, Sentinel-2 {fmt(read['hls_s30'])}, MODIS {fmt(read['modis'])}। "
          f"{fmt(int(by['count'].sum()))} तस्बिर प्रयोग गर्न पुग्ने सफा थिए।",
          f"{p['greenness']}: rows (pictures read over the field); rows with a greenness value (clear enough)",
          ["Harmonized Landsat Sentinel-2", "MODIS Terra"]),
        n("years_replayed", len(replay), "years replayed", "वर्ष दोहोर्‍याइयो",
          f"Every full year from {replay[0]['year']} to {replay[-1]['year']}.",
          f"{replay[0]['year']} देखि {replay[-1]['year']} सम्मका हरेक पूरा वर्ष।",
          f"{p['field_json']}: replay.current (years)", ["Khet Sathi field twin"]),
        n("climate_models", len(models), "climate models", "जलवायु मोडेल",
          f"For {fj['future']['period'].replace('-', ' to ')}, {len(fj['future']['scenarios'])} possible futures.",
          f"{fj['future']['period'].replace('-', ' देखि ')} का लागि, {len(fj['future']['scenarios'])} सम्भावित भविष्य।",
          f"{p['field_json']}: future.models (checked against {p['future']}: n_models)", ["NEX-GDDP-CMIP6"]),
        n("seasons", seasons, "crop seasons run", "बाली याम चलाइयो",
          f"{fmt(plans['n_plans'])} crop plans, each crop, each year. The main run only.",
          f"{fmt(plans['n_plans'])} बाली योजना, हरेक बाली, हरेक वर्ष। मुख्य हिसाब मात्र।",
          f"{p['plans']}: plans (for each plan, its crops times its years)", ["Khet Sathi field twin"]),
        n("datasets", len(sets), "datasets", "डाटासेट",
          "Tap a name for its square size and years. The checks use more.",
          "वर्गको आकार र वर्ष हेर्न नाममा थिच्नुहोस्। जाँचमा अझ बढी प्रयोग भए।",
          f"{p['field_json']}: sources (our own field twin not counted)", [s["name"] for s in sets]),
    ]


def power_chart(weather, rules, src):
    """NASA POWER's temperature through the year as the twin uses it: each month's usual day and night, the coldest
    night and hottest day of the record, and the frost and heat lines of rules.yaml."""
    w = weather.assign(m=pd.to_datetime(weather["date"]).dt.month, y=pd.to_datetime(weather["date"]).dt.year)
    g = w.groupby("m").agg(day=("tmax_c", "mean"), night=("tmin_c", "mean"), hot=("tmax_c", "max"), cold=("tmin_frost_c", "min"))
    if list(g.index) != list(range(1, 13)):
        raise ValueError("weather.parquet must hold every calendar month")
    y0, y1 = int(w["y"].min()), int(w["y"].max())
    frost, heat = rules["cold_nights"]["frost_night_c"], rules["heat_clock"]["potato_heat"]["at_or_above_c"]
    warm = sorted(rules["power_rain"]["never_fill_years"])     # the years whose POWER days read too warm (trends.hot_day_caveat)
    pts = lambda col: [[MONTHS[m - 1], round(float(g.loc[m, col]), 1)] for m in range(1, 13)]   # noqa: E731
    flat = lambda v: [[MONTHS[0], v], [MONTHS[-1], v]]                                         # noqa: E731
    return chart(
        "power_year", "behind", T("Temperature through the year", "वर्षभरिको तापक्रम"),
        T("Days and nights through the year, with frost and heat lines.", "वर्षभरिका दिन र रात, तुसारो र गर्मीका रेखासहित।"),
        [f"{src['name']}: {src['product']}, {src['resolution']}, {y0}-{y1}; model-based (worked out by computer)",
         f"Frost line: nights below {fmt(frost)} °C (config/rules.yaml cold_nights.frost_night_c). Heat line: days of "
         f"{fmt(heat)} °C or more (heat_clock.potato_heat, FAO-66). Coldest nights: the frost series (quantile mapping)"],
        "line", axis_x(T("Month", "महिना"), "month"), axis_y(T("Temperature", "तापक्रम"), "°C"),
        [S(T("Day, usual", "दिन, सामान्य"), "main", pts("day")),
         S(T("Night, usual", "रात, सामान्य"), "compare", pts("night")),
         S(T(f"Frost line: {fmt(frost)} °C", f"तुसारो रेखा: {fmt(frost)} °C"), "compare", flat(frost)),
         S(T(f"Heat line: {fmt(heat)} °C", f"गर्मी रेखा: {fmt(heat)} °C"), "compare", flat(heat)),
         S(T(f"Coldest night to hottest day, {y0}-{y1}", f"सबैभन्दा चिसो रातदेखि सबैभन्दा तातो दिनसम्म, {y0}–{y1}"), "range",
           [[MONTHS[m - 1], [round(float(g.loc[m, "cold"]), 1), round(float(g.loc[m, "hot"]), 1)]] for m in range(1, 13)])],
        note=T(f"The days of {warm[0]}-{warm[-1]} read too warm here.", f"{warm[0]}–{warm[-1]} का दिन यहाँ बढी तातो देखिन्छन्।"))


def cards(inp, power):
    """One card per NASA mission: a chart id (in story.json, or the chart built here), one plain sentence whose numbers
    come from the data, and the field file's own source entry (resolution, years, kind)."""
    fj, story = inp["field_json"], {c["id"]: c for c in inp["story"]["charts"]}
    for cid in ("rain_fixed", "seasons_from_space", "groundwater", "outlook_2040", "other_checks"):
        if story.get(cid, {}).get("status") != "ready":
            raise ValueError(f"story.json has no ready chart {cid!r}")
    gpm = inp["gpm"]
    rain_years = int(pd.to_datetime(gpm["date"]).dt.year.nunique())
    jump = story["rain_fixed"]["markers"][0]["x"]
    gw = fj["diary"]["groundwater"]
    move = {"falling": ("falls", "घट्छ"), "rising": ("rises", "बढ्छ"), "steady": ("stays level", "उस्तै रहन्छ")}[gw["direction"]]
    rate = fmt(abs(gw["trend_cm_per_year"]), 1)
    n_models, year = len(fj["future"]["models"]), fj["future"]["years"][-1]
    only = [c["id"] for c in story["other_checks"]["x"]["categories"] if re.match(r"smap|gldas", c["id"])]

    def card(cid, mission, starts, chart_id, en, ne, **extra):
        s = source(fj, starts)
        return {"id": cid, "mission": mission, "say": T(en, ne), "chart": chart_id, "source": s["name"],
                "resolution": s["resolution"], "years": s["years"], "kind": s["type"], **extra}

    out = [
        card("gpm", "GPM", "GPM IMERG", "rain_fixed",
             f"Rain every day for {rain_years} years; corrected for fewer gauges from {jump}.",
             f"{rain_years} वर्षको हरेक दिनको वर्षा; {jump} देखि घटेका मापकका लागि मिलाइएको।"),
        card("hls", "HLS (Landsat + Sentinel-2)", "Harmonized Landsat", "seasons_from_space",
             "The field's green heartbeat: each wave is a crop.", "खेतको हरियो धड्कन: हरेक लहर एउटा बाली हो।"),
        card("power", "NASA POWER", "NASA POWER", power["id"], power["caption"]["en"], power["caption"]["ne"]),
        card("grace", "GRACE + GRACE-FO", "GRACE", "groundwater",
             f"Water under the whole region {move[0]}" + ("." if gw["direction"] == "steady" else f" about {rate} cm a year."),
             "पूरै क्षेत्रको जमिनमुनिको पानी " + (f"{move[1]}।" if gw["direction"] == "steady" else f"वर्षमा करिब {rate} सेमी {move[1]}।")),
        card("nexgddp", "NEX-GDDP-CMIP6", "NEX-GDDP", "outlook_2040",
             f"{n_models} climate models compare harvests today with {year}.",
             f"{n_models} जलवायु मोडेलले आज र {year} को उब्जनी दाँज्छन्।"),
        card("smap_gldas", "SMAP + GLDAS", "NASA SMAP", "other_checks",
             "Two NASA soil-water records check our copy of your field.", "नासाका दुई माटो-पानी अभिलेखले तपाईंको खेतको नक्कल जाँच्छन्।",
             only=only, also="NASA GLDAS-2.1 Noah, 0.25°, monthly (model-based)"),
    ]
    return out


def pixels(inp):
    """Each dataset's square over the field, in metres: the sizes the field file's source list states, and the field's
    own side (the square root of its outline's area)."""
    fj = inp["field_json"]
    what = {"Harmonized Landsat": ("HLS", T("greenness", "हरियाली")), "NASA SMAP": ("SMAP", T("soil water", "माटोको पानी")),
            "GPM IMERG": ("GPM", T("rain", "वर्षा")), "GRACE": ("GRACE", T("water under the region", "क्षेत्रमुनिको पानी"))}
    squares = [{"id": name.lower(), "name": name, "what": text, "size_m": size_m(source(fj, starts)["resolution"]),
                "source": source(fj, starts)["name"]} for starts, (name, text) in what.items()]
    return {"field_m": round(math.sqrt(area_m2(inp["field_config"]["polygon"])), 1), "squares": sorted(squares, key=lambda q: q["size_m"]),
            "say": T("Each record sees the land in squares of its own size.", "हरेक अभिलेखले जमिनलाई आफ्नै आकारका वर्गमा हेर्छ।"),
            "note": T("Each picture is true to scale. A dot marks what is too small to draw.",
                      "हरेक चित्र साँचो नापमा छ। कोर्न नसकिने सानो कुरालाई थोप्लाले देखाउँछ।")}


NE_MONTHS = ["जन", "फेब", "मार्च", "अप्रि", "मे", "जुन", "जुला", "अग", "सेप", "अक्टो", "नोभे", "डिसे"]
NE_CROPS = {"rice": "धान", "potato": "आलु", "wheat": "गहुँ", "lentil": "मसुरो", "maize": "मकै", "mustard": "तोरी"}
STEP_WORDS = {"very_dry": T("Very dry", "धेरै सुक्खा"), "dry": T("Dry", "सुक्खा"), "damp": T("Damp", "चिस्यान"), "wet": T("Wet", "ओसिलो")}


def soil_years(g):
    """24 years of soil at a glance (owner, 2026-11-15 evening; rules.yaml soil_years): data/checks/<field>/soil_years.json
    as a grid of steps (one row per replayed year), with its words."""
    n, rot, dry = len(g["years"]), g["rotation"], g["case"] == "rain-fed"
    plan = (", then ".join(rot), ", त्यसपछि ".join(NE_CROPS.get(c, c) for c in rot))
    return {
        "title": T(f"{n} years of soil at a glance", f"{n} वर्षको माटो एकै नजरमा"),
        "say": T("How wet the soil was each month, in our copy of your field.",
                 "हाम्रो खेतको नक्कलमा हरेक महिना माटो कति ओसिलो थियो।"),
        "case": T(f"Your plan now ({plan[0]}), " + ("if you can't water." if dry else "with water."),
                  f"अहिलेको योजना ({plan[1]}), " + ("पानी हाल्न नसके।" if dry else "पानी हाल्दा।")),
        "years": g["years"], "step": [g["step"][str(y)] for y in g["years"]], "events": g["events"],
        "colours": g["steps"]["colours"], "words": [STEP_WORDS[w] for w in g["steps"]["words"]],
        "months": [T(m, ne) for m, ne in zip(MONTHS, NE_MONTHS)],
        "marks": {"flood": T("Flood year", "बाढी वर्ष"), "drought": T("Dry year", "खडेरी वर्ष")},
        "legend": [T("Dry", "सुक्खा"), T("Wet", "ओसिलो")],
        "tap": T("Tap a square to see its month.", "महिना हेर्न वर्ग थिच्नुहोस्।"),
        "note": T("Each square is the month's average: how full the soil's water store was. "
                  "An estimate from our copy of your field, with NASA rain and weather.",
                  "हरेक वर्ग महिनाको औसत हो: माटोले राख्न सक्ने पानी कति भरिएको थियो। "
                  "नासाको वर्षा र मौसमसहित हाम्रो खेतको नक्कलबाट अनुमान।"),
    }


def build_behind(inp):
    """The whole file from loaded inputs (pure)."""
    fj = inp["field_json"]
    power = power_chart(inp["weather"], inp["rules"], source(fj, "NASA POWER"))
    n = len(fj["replay"]["current"])
    p = inp["paths"]
    grid = {"soil_years": soil_years(inp["soil_years"])} if inp.get("soil_years") else {}
    return {
        "field": inp["field"], "placeholder": bool(re.search("placeholder", fj["field"]["name"], re.I)), "ne_review": NE_REVIEW,
        "made_by": "pipeline/export/build_behind.py",
        "title": T("Behind the scenes: your field, seen by NASA", "पर्दा पछाडि: नासाले देखेको तपाईंको खेत"),
        "numbers": numbers(inp),
        # C (owner, 2026-11-15): plain names; "Field Twin" is named once, in brackets, in How we know's explanation only
        "flow": [T("NASA data", "नासाको डाटा"), T("A copy of your field", "तपाईंको खेतको नक्कल"),
                 T(f"Tested in {n} past years", f"विगतका {n} वर्षमा जाँचियो"), T("Your answers", "तपाईंका जवाफ")],
        "cards": cards(inp, power), "charts": [power], "pixels": pixels(inp), "tags": TAGS,
        "units": {"m": T("m", "मि"), "km": T("km", "किमी")},
        "inputs": {"numbers": sorted({p[k] for k in ("gpm", "greenness", "field_json", "plans", "future")}),
                   "cards": [p["story"], p["field_json"], p["gpm"]], "power_year": [p["weather"], "config/rules.yaml"],
                   "pixels": [p["field_json"], p["field_config"]], **({"soil_years": [p["soil_years"]]} if grid else {})},
        **grid,
    }


def input_paths(field):
    c, k = f"data/clean/{field}", f"data/checks/{field}"
    return {"gpm": f"{c}/gpm.parquet", "greenness": f"{c}/greenness_field.parquet", "weather": f"{c}/weather.parquet",
            "plans": f"{k}/plans.json", "future": f"{k}/future.json", "field_json": f"site/data/fields/{field}.json",
            "story": "site/data/story.json", "field_config": f"config/fields/{field}.yaml", "soil_years": f"{k}/soil_years.json"}


def load_inputs(repo, field):
    """Read every input (I/O); each must exist."""
    from pipeline.fetch.rules import load_rules
    paths = input_paths(field)
    out = {"field": field, "paths": paths, "rules": load_rules()}
    for key, rel in paths.items():
        path = Path(repo) / rel
        if key == "soil_years" and not path.exists():   # optional: scripts/run_soil_years.py (2026-11-15 evening)
            continue
        out[key] = pd.read_parquet(path) if rel.endswith(".parquet") else \
            yaml.safe_load(path.read_text()) if rel.endswith(".yaml") else json.loads(path.read_text())
    if out["story"]["field"] != field:
        raise ValueError(f"site/data/story.json is for field {out['story']['field']!r}, not {field!r}")
    return out


def validate_behind(doc):
    """Problems as strings; [] when the file matches behind_schema.json and its charts match story.json's chart rule."""
    story = json.loads(SCHEMA.with_name("story_schema.json").read_text())
    one_chart = {"$schema": story["$schema"], "$ref": "#/$defs/chart", "$defs": story["$defs"]}
    errs = [f"{'/'.join(str(x) for x in e.absolute_path)}: {e.message}"
            for e in Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(doc)]
    for c in doc.get("charts", []):
        errs += [f"charts/{c.get('id')}/{'/'.join(str(x) for x in e.absolute_path)}: {e.message}"
                 for e in Draft202012Validator(one_chart).iter_errors(c)]
    ids = {c["id"] for c in doc.get("cards", [])}
    errs += [f"tags/{k}: no card {c!r}" for k, v in doc.get("tags", {}).items() for c in v if c not in ids]
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--field", default=None, help="default: rules.yaml site_main_field (the field the site opens first)")
    ap.add_argument("--out", default=None, help="default site/data/behind.json")
    a = ap.parse_args(argv)
    if a.field is None:
        from pipeline.fetch.rules import load_rules
        a.field = load_rules()["site_main_field"]
    doc = build_behind(load_inputs(REPO, a.field))
    if problems := validate_behind(doc):
        print("behind.json does not match behind_schema.json:\n  " + "\n  ".join(problems[:20]), file=sys.stderr)
        return 1
    out = Path(a.out) if a.out else REPO / "site" / "data" / "behind.json"
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(text)
    tmp.replace(out)
    print(f"wrote {out}: {len(doc['numbers'])} numbers, {len(doc['cards'])} cards, {len(text.encode()) / 1024:.1f} KB")
    for x in doc["numbers"]:
        print(f"  {x['id']}: {x['value']}  ({x['from']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
