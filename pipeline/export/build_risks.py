"""Three small screens of 2026-11-14 (owner's brief), one file each per prepared field:

    .venv/bin/python -m pipeline.export.build_risks --field demo --kind rainrisk    # site/data/rainrisk/<field>.json
    .venv/bin/python -m pipeline.export.build_risks --field demo --kind fertiliser  # site/data/fertiliser/<field>.json
    .venv/bin/python -m pipeline.export.build_risks --field demo --kind heatclock   # site/data/heatclock/<field>.json

Rules: config/rules.yaml rain_risk, fertiliser_saver, heat_clock (committed before the first run). Arithmetic:
pipeline/plans/risk.py. Reads the exported field file (plans, current_options, replay years, sources),
data/clean/<field>/weather.parquet and nexgddp_daily.parquet. Each file carries its labels (refreshed later by
build_labels), a `why` text in English and Nepali (the screen's Why? button; Nepali drafted by SI, needs review) and
its sources, without web addresses (scripts/check_site.py).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

from pipeline.export.build_labels import label_for, load_scorecard
from pipeline.export.build_replay import plans_of
from pipeline.fetch.cropslib import load_crops
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules
from pipeline.plans import risk
from pipeline.twin.inputs import with_rain

REPO = Path(__file__).resolve().parents[2]
KINDS = ("rainrisk", "fertiliser", "heatclock")
OTHER_RAIN = ("untuned", "dhm", "uncorrected")
NE_REVIEW = "needs native-speaker review"
NE_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MON_NE = ["जनवरी", "फेब्रुअरी", "मार्च", "अप्रिल", "मे", "जुन", "जुलाई", "अगस्ट", "सेप्टेम्बर", "अक्टोबर", "नोभेम्बर", "डिसेम्बर"]
CROP_NE = {"rice": "धान", "wheat": "गहुँ", "potato": "आलु", "lentil": "मसुर"}
DOCS = {   # sources that are texts, not data (no web address: check_site.py refuses them in these folders)
    "dhm_terms": {"name": "DHM, Terms used in Weather Forecasting in Nepal", "product": "rain in 24 hours: heavy is 50 mm "
                  "or more but less than 100 mm; very heavy and extremely heavy above it (Meteorological Forecasting Division)",
                  "resolution": "a definition for Nepal", "years": "page dated 2026", "type": "document"},
    "dhm_cdd": {"name": "DHM, Update of Climate Change Study of Nepal", "product": "Table 6, p.16: CDD, the longest run of "
                "days with rain under 1 mm in a year (Final Report, August 2024)", "resolution": "an index for Nepal",
                "years": "2024", "type": "document"},
    "bread_wheat": {"name": "Acevedo, Silva and Silva, 'Wheat growth and physiology', in Bread Wheat: Improvement and "
                    "Production (FAO Plant Production and Protection Series No. 30)", "product": "above 30 C during floret "
                    "formation causes complete sterility; frost below 0 C (minimum screen temperature) from flag leaf "
                    "emergence to ten days after anthesis; Table 3.1, days from emergence (spring wheat)",
                    "resolution": "a published text", "years": "2002", "type": "document"},
    "fao56": {"name": "FAO Irrigation and Drainage Paper 56 (Allen et al. 1998)", "product": "crop growth stages, chapter 6; "
              "stage lengths of our crop table from its Table 11, scaled to the local season", "resolution": "a method",
              "years": "1998", "type": "document"},
    "fao66": {"name": "FAO Irrigation and Drainage Paper 66, Crop yield response to water", "product": "wheat p.98 (above "
              "34 C during grain filling), Table 1 p.95; potato p.187 (cold 1 C and less, heat 35 C or higher)",
              "resolution": "a published text", "years": "2012", "type": "document"},
    "thesis": {"name": "Nagaraju (2017), M.Sc. thesis, Banaras Hindu University", "product": "p.2: 'carry-over of N from "
               "lentil is low at 23-45 kg N ha-1', citing Quinn (2009), The Lentil, pp. 229-247", "resolution": "studies "
               "elsewhere; place not stated", "years": "2017", "type": "document"},
    "mooleki": {"name": "Mooleki, Slinkard and van Kessel, University of Saskatchewan", "product": "'Nitrogen and non-"
                "nitrogen benefits of lentil in the succeeding wheat crop', p.297: 2.3 kg N/ha recovered in the next wheat",
                "resolution": "one field site, Dinsmore, Canada", "years": "1994-1995", "type": "document"},
    "iupac": {"name": "IUPAC CIAAW, Abridged Standard Atomic Weights 2024", "product": "H 1.0080, C 12.011, N 14.007, "
              "O 15.999: urea's nitrogen share", "resolution": "a constant", "years": "2024", "type": "document"},
    "bags": {"name": "BankingNews (16 July 2026) and The Kathmandu Post (26 May 2026)", "product": "urea in 50 kg bags; "
             "fertiliser short when paddy planting begins (Terai districts)", "resolution": "Nepal, news reports",
             "years": "2026", "type": "document"},
}


def ne(s):
    return str(s).translate(NE_DIGITS)


def date_en(mmdd):
    m, d = map(int, mmdd.split("-"))
    return f"{d} {MON[m - 1]}"


def date_ne(mmdd):
    m, d = map(int, mmdd.split("-"))
    return f"{MON_NE[m - 1]} {ne(d)}"


def _src(doc, prefix):
    return next(s for s in doc["sources"] if s["name"].startswith(prefix))


def _span(lo, hi, to="to"):
    return f"{lo}" if lo == hi else f"{lo} {to} {hi}"


def _base(kind, fid, field, why, sources, labels):
    return {"field": fid, "placeholder": bool(field.get("placeholder")),
            "made_by": f"pipeline/export/build_risks.py --kind {kind} (rules.yaml {RULE[kind]})",
            "labels": labels, "why": {**why, "ne_review": NE_REVIEW,
                                      "drafted_by": "SI (Claude Opus 5.5 via Claude Code), 2026-11-14"},
            "sources": sources}


RULE = {"rainrisk": "rain_risk", "fertiliser": "fertiliser_saver", "heatclock": "heat_clock"}


def _weather(fid, data):
    w = pd.read_parquet(data / "clean" / fid / "weather.parquet")
    w["date"] = pd.to_datetime(w["date"])
    return w


def _years(doc, w, windows):
    """The replay's complete years (2002-2025 on the demo), checked to be complete for every window."""
    years = [y["year"] for y in doc["replay"]["current"]]
    d0, d1 = w["date"].min(), w["date"].max()
    for a, b in windows:
        ok = risk.complete_seasons(d0.year, d1.year, a, b)
        if d0 != pd.Timestamp(f"{d0.year}-01-01") or d1 != pd.Timestamp(f"{d1.year}-12-31") or not set(years) <= set(ok):
            raise SystemExit(f"weather record {d0.date()}..{d1.date()} does not hold every {a}..{b} window of {years}")
    return years


# ---------------- item 1: heavy rain in the harvest weeks ----------------
def build_rainrisk(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules, lib = load_field(fid), load_rules(), load_crops()
    R = rules["rain_risk"]
    thr = float(R["heavy_rain_mm"]["threshold"])
    if not R["heavy_rain_mm"]["inclusive"]:
        raise SystemExit("rain_risk.heavy_rain_mm: DHM's bounds are inclusive")
    doc = json.loads((site / "fields" / f"{fid}.json").read_text())
    w = _weather(fid, data)
    from scripts.common import rain_kw
    rains = {"central": w, **{v: with_rain(w, v, **rain_kw(rules, v, fid)) for v in OTHER_RAIN}}
    plans = plans_of(doc)
    wins = {(c["crop"], c["start"], c["end"]): risk.window_mmdd(c, lib, "late") for _, _, cs in plans for c in cs}
    years = _years(doc, w, [*wins.values(), *((s, e) for _, s, e in wins)])
    dry_mm = float(rules["trends"]["dry_day_mm"])
    out_plans, seen, dry_seen = [], {}, {}
    for pid, role, crops in plans:
        rows = []
        for c in crops:
            a, b = wins[(c["crop"], c["start"], c["end"])]
            per = {v: risk.heavy_rain_years(x["date"], x["rain_mm"], a, b, years, thr) for v, x in rains.items()}
            heavy = {v: [r["year"] for r in rs if r["days"] > 0] for v, rs in per.items()}
            counts = [len(h) for h in heavy.values()]
            dry = {v: risk.longest_dry_runs(x["date"], x["rain_mm"], c["start"], c["end"], years, dry_mm)
                   for v, x in rains.items()}
            typ = {v: risk.typical_worst(r)["typical"] for v, r in dry.items()}
            rows.append({"crop": c["crop"], "sow": c["start"], "end": c["end"],
                         "window": {"from": a, "to": b, "days": int(lib[c["crop"]]["stages_days"]["late"]), "stage": "late"},
                         "years": per["central"], "count": len(heavy["central"]),
                         "other_versions": {v: {"count": len(heavy[v]), "heavy_years": heavy[v]} for v in OTHER_RAIN},
                         "count_low": min(counts), "count_high": max(counts), "good_news": len(heavy["central"]) == 0,
                         "dry_run": {"window": {"from": c["start"], "to": c["end"],
                                                "days": risk.window_days(c["start"], c["end"]), "stage": "season"},
                                     "years": [{"year": y, "days": dry["central"][y]} for y in years],
                                     **risk.typical_worst(dry["central"]),
                                     "other_versions": {v: {"typical": typ[v]} for v in OTHER_RAIN},
                                     "typical_low": min(typ.values()), "typical_high": max(typ.values())}})
            seen.setdefault((c["crop"], a, b), rows[-1])
            dry_seen.setdefault((c["crop"], c["start"], c["end"]), rows[-1]["dry_run"])
        out_plans.append({"id": pid, "role": role, "crops": rows})
    dry_lines = sorted(dry_seen.items())
    lines = sorted(seen.items(), key=lambda x: (x[0][0], x[0][1]))
    en = [f"Heavy rain means a day with {thr:g} mm of rain or more: DHM's 'heavy' class and above (DHM, Terms used in "
          "Weather Forecasting in Nepal).",
          "Harvest weeks are each crop's last growth stage before harvest, the 'late season' of FAO-56 (FAO Irrigation "
          "and Drainage Paper 56), with the stage lengths of our crop table: "
          + "; ".join(f"{c} {date_en(a)} to {date_en(b)} ({r['window']['days']} days)" for (c, a, b), r in lines) + ".",
          f"Years: {years[0]} to {years[-1]}, {len(years)} harvests; a year is the year the harvest weeks end.",
          "Rain: GPM IMERG, NASA's satellite rain map (cells of about 10 km), fixed for its 2017 break and matched to "
          "nearby DHM rain gauges (the Record Check-up shows how).",
          "Heavy-rain days depend strongly on the rain record. The range under each crop also uses our three other rain "
          "versions: before the gauge match, scaled to DHM Bhaktapur's long-term average, and GPM as published.",
          "IMERG days are UTC days, 05:45 to 05:45 Nepal time. DHM's page does not say which 24 hours it uses, so one "
          "storm may fall on two of our days but one of DHM's, or the other way round.",
          "These are counts of past years, not a forecast. 'Estimate' means they are not yet checked against farmers' "
          "own records.",
          f"Longest dry run: the most days in a row with less than {dry_mm:g} mm of rain, from each crop's sowing day to "
          "its last day (" + "; ".join(f"{c} {date_en(s)} to {date_en(e)}" for (c, s, e), _ in dry_lines) + "). A run "
          "is cut where the season starts and where it ends.",
          f"This is DHM's own measure of dry spells, CDD, the longest run of days under {dry_mm:g} mm (DHM, Update of "
          "Climate Change Study of Nepal, 2024, Table 6, p.16). DHM counts it over each calendar year; we count it over "
          "each crop's season, from sowing, so the two numbers are not the same. Our days are IMERG UTC days.",
          f"'Usually' is the middle year of the {len(years)} (half a day rounds up). The worst years are the three "
          "longest runs (on a tie, the later year first).",
          "Under our four rain versions the usual longest dry run is: " + "; ".join(
              f"{c} sown {date_en(s)}, {_span(d['typical_low'], d['typical_high'])} days" for (c, s, _), d in dry_lines)
          + "."]
    nep = [f"भारी वर्षा भनेको एक दिनमा {ne(f'{thr:g}')} मिलिमिटर वा बढी पानी परेको दिन हो: जल तथा मौसम विज्ञान विभाग (DHM) "
           "को 'भारी' वर्ग वा त्योभन्दा माथि (DHM, नेपालको मौसम पूर्वानुमानमा प्रयोग हुने शब्दावली)।",
           "बाली काट्ने हप्ता भनेको हरेक बालीको काट्नुअघिको अन्तिम चरण हो, FAO-56 (FAO सिँचाइ तथा निकास पत्र ५६) को "
           "'late season', हाम्रो बाली तालिकाका चरण-लम्बाइअनुसार: "
           + "; ".join(f"{CROP_NE.get(c, c)} {date_ne(a)} देखि {date_ne(b)} सम्म ({ne(r['window']['days'])} दिन)"
                       for (c, a, b), r in lines) + "।",
           f"वर्ष: {ne(years[0])} देखि {ne(years[-1])}, {ne(len(years))} बाली; वर्ष भनेको बाली काट्ने हप्ता सकिने वर्ष हो।",
           "वर्षा: GPM IMERG, नासाको आकाशबाट नापिएको वर्षाको नक्सा (करिब १० किलोमिटरका कोठा), २०१७ को टुटका लागि "
           "मिलाइएको र नजिकका DHM वर्षामापन केन्द्रसँग मिलाइएको (अभिलेख जाँचले कसरी भनेर देखाउँछ)।",
           "भारी वर्षाका दिन वर्षाको अभिलेखमा धेरै भर पर्छन्। हरेक बालीमुनिको दायराले हाम्रा अरू तीन वर्षा-संस्करण पनि "
           "हेर्छ: वर्षामापन केन्द्रसँग मिलाउनुअघिको, DHM भक्तपुरको लामो समयको औसतमा मिलाइएको, र GPM जस्ताको तस्तै।",
           "IMERG का दिन UTC दिन हुन्, नेपाली समय बिहान ५:४५ देखि भोलिपल्ट बिहान ५:४५ सम्म। DHM को पानाले कुन २४ घण्टा "
           "भनेर लेखेको छैन, त्यसैले एउटै झरी हाम्रा दुई दिनमा तर DHM को एक दिनमा, वा उल्टो, पर्न सक्छ।",
           "यी विगतका वर्षको गन्ती हुन्, पूर्वानुमान होइन। 'अनुमान' को अर्थ: किसानका आफ्नै अभिलेखसँग अझै जाँचिएको छैन।",
           f"सबैभन्दा लामो सुक्खा लहर: हरेक बाली रोपेको दिनदेखि उसको अन्तिम दिनसम्म, लगातार {ne(f'{dry_mm:g}')} मिलिमिटरभन्दा "
           "कम पानी परेका सबैभन्दा धेरै दिन (" + "; ".join(f"{CROP_NE.get(c, c)} {date_ne(s)} देखि {date_ne(e)} सम्म"
                                                          for (c, s, e), _ in dry_lines) + ")। सिजन सुरु हुने र सकिने "
           "ठाउँमा लहर काटिन्छ।",
           f"यो सुक्खा लहरको DHM कै नाप हो, CDD: {ne(f'{dry_mm:g}')} मिलिमिटरभन्दा कम पानी परेका दिनको सबैभन्दा लामो लहर "
           "(DHM, नेपालको जलवायु परिवर्तन अध्ययनको अद्यावधिक, २०२४, तालिका ६, पृष्ठ १६)। DHM ले यसलाई हरेक पात्रो-वर्षमा "
           "गन्छ; हामी हरेक बालीको सिजनमा, रोपेको दिनदेखि गन्छौं, त्यसैले दुई अङ्क उस्तै होइनन्। हाम्रा दिन IMERG का UTC "
           "दिन हुन्।",
           f"'प्रायः' भनेको {ne(len(years))} वर्षको बीचको वर्ष हो (आधा दिन माथि गोलाइन्छ)। सबैभन्दा खराब वर्ष भनेका तीन "
           "सबैभन्दा लामो लहर हुन् (बराबर भए पछिल्लो वर्ष पहिले)।",
           "हाम्रा चार वर्षा-संस्करणमा प्रायः हुने सबैभन्दा लामो सुक्खा लहर: " + "; ".join(
               f"{date_ne(s)} मा रोपेको {CROP_NE.get(c, c)} {ne(_span(d['typical_low'], d['typical_high'], 'देखि'))} दिन"
               for (c, s, _), d in dry_lines) + "।"]
    card = load_scorecard(fid, field, data)
    out = _base("rainrisk", fid, field, {"en": en, "ne": nep},
                [_src(doc, "GPM IMERG"), DOCS["dhm_terms"], DOCS["fao56"], DOCS["dhm_cdd"]],
                {"rainrisk_harvest": label_for("rainrisk_harvest", field, rules, card)})
    return {**out, "years": years, "year_count": len(years), "threshold_mm": thr, "versions": ["central", *OTHER_RAIN],
            "day": "IMERG day: UTC, 05:45 to 05:45 Nepal time", "plans": out_plans, "dry_day_mm": dry_mm}


# ---------------- item 2: the urea the next crop after lentil may not need ----------------
def build_fertiliser(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules, lib = load_field(fid), load_rules(), load_crops()
    F = rules["fertiliser_saver"]
    doc = json.loads((site / "fields" / f"{fid}.json").read_text())
    plan = next((p for p in doc["plans"] if p["id"] == "safest"), None)
    crops = [c["crop"] for c in plan["crops"]] if plan else []
    legume = next((c for c in crops if lib[c].get("legume")), None)
    card = load_scorecard(fid, field, data)
    labels = {"fertiliser_saver": label_for("fertiliser_saver", field, rules, card)}
    if legume is None:
        return {**_base("fertiliser", fid, field, {"en": [], "ne": []}, [], labels), "applies": False, "plan": "safest"}
    nxt = crops[(crops.index(legume) + 1) % len(crops)]
    s = risk.urea_saved(F["carry_over_kg_n_ha"], F["urea_n_share"], F["bag_kg"])
    (n0, n1), (u0, u1), (b0, b1), share = s["n_kg_ha"], s["urea_kg_ha"], s["bags_ha"], F["urea_n_share"]
    up, bag = F["measured_uptake_kg_n_ha"], F["bag_kg"]
    en = [f"{nxt.capitalize()} after {legume} may need less nitrogen. A published range for the nitrogen {legume} leaves "
          f"('carry-over of N from lentil') is {n0}-{n1} kg N per hectare: Nagaraju (2017), M.Sc. thesis, Banaras Hindu "
          "University, p.2, citing Quinn (2009). The thesis does not say how it was measured, or where.",
          f"One field study, in Saskatchewan, Canada (Mooleki, Slinkard and van Kessel), found only about {up} kg N per "
          "hectare from the lentil's leftovers in the next crop. So the real saving may be much smaller than the range.",
          f"Urea is CO(NH2)2. Its nitrogen share: 2 x 14.007 = 28.014 of 60.056, so {share * 100:.1f} % (IUPAC atomic "
          "weights, 2024).",
          f"Urea saved: {n0} / {share} = {u0} kg to {n1} / {share} = {u1} kg per hectare. In {bag} kg bags: {b0} to {b1} "
          f"bags per hectare, about {s['bags_ha_whole'][0]} to {s['bags_ha_whole'][1]}.",
          f"Urea is sold in {bag} kg bags (BankingNews, 16 July 2026; The Kathmandu Post, 26 May 2026).",
          "Per hectare only: one hectare is 10,000 square metres (100 m by 100 m). A figure in ropani waits for a source "
          "we could open.",
          "Farmers report fertiliser shortages when paddy planting begins (The Kathmandu Post, 26 May 2026; the districts it "
          "names are in the Terai, not Bhaktapur).",
          "This is a wide, uncertain range from studies elsewhere, not a measurement on this field. Ask your local "
          "agriculture office before you use less fertiliser."]
    nl, nn = CROP_NE.get(legume, legume), CROP_NE.get(nxt, nxt)
    nep = [f"{nl}पछिको {nn}लाई कम नाइट्रोजन चाहिन सक्छ। {nl}ले छाड्ने नाइट्रोजनको एक प्रकाशित दायरा ('carry-over of N "
           f"from lentil') प्रति हेक्टर {ne(n0)}–{ne(n1)} किलो नाइट्रोजन हो: नागराजु (२०१७), एमएससी शोधपत्र, बनारस हिन्दू "
           "विश्वविद्यालय, पृष्ठ २, क्विन (२००९) लाई उद्धृत गर्दै। शोधपत्रले यो कसरी वा कहाँ नापियो भनेर भन्दैन।",
           f"क्यानडाको सस्काचेवानमा एउटा खेत-अध्ययन (मुलेकी, स्लिनकार्ड र भ्यान केसेल) ले अर्को बालीमा {nl}को अवशेषबाट "
           f"प्रति हेक्टर करिब {ne(up)} किलो नाइट्रोजन मात्र भेट्यो। त्यसैले साँचो बचत यो दायराभन्दा धेरै कम हुन सक्छ।",
           f"युरिया CO(NH2)2 हो। यसमा नाइट्रोजनको भाग: २ × १४.००७ = २८.०१४, ६०.०५६ मध्ये, त्यसैले {ne(f'{share * 100:.1f}')} "
           "प्रतिशत (IUPAC परमाणु भार, २०२४)।",
           f"बचत हुने युरिया: {ne(n0)} ÷ {ne(share)} = {ne(u0)} किलो देखि {ne(n1)} ÷ {ne(share)} = {ne(u1)} किलो प्रति "
           f"हेक्टर। {ne(bag)} किलोको बोरामा: प्रति हेक्टर {ne(b0)} देखि {ne(b1)} बोरा, करिब {ne(s['bags_ha_whole'][0])} देखि "
           f"{ne(s['bags_ha_whole'][1])}।",
           f"युरिया {ne(bag)} किलोको बोरामा बिक्छ (बैंकिङ न्युज, १६ जुलाई २०२६; द काठमाडौं पोस्ट, २६ मे २०२६)।",
           "प्रति हेक्टर मात्र: एक हेक्टर १०,००० वर्ग मिटर (१०० मिटर × १०० मिटर) हो। रोपनीमा अङ्क हामीले खोलेर जाँच्न "
           "सकेको स्रोत नआउञ्जेल पर्खन्छ।",
           "धान रोप्ने बेला सुरु हुँदा मलको अभाव भएको किसान बताउँछन् (द काठमाडौं पोस्ट, २६ मे २०२६; यसले नाम लिएका जिल्ला तराईका हुन्, "
           "भक्तपुर होइन)।",
           "यो अन्यत्रका अध्ययनबाट आएको फराकिलो र अनिश्चित दायरा हो, यो खेतमा नापिएको होइन। मल घटाउनुअघि स्थानीय कृषि "
           "कार्यालयलाई सोध्नुहोस्।"]
    out = _base("fertiliser", fid, field, {"en": en, "ne": nep},
                [DOCS["thesis"], DOCS["mooleki"], DOCS["iupac"], DOCS["bags"]], labels)
    return {**out, "applies": True, "plan": "safest", "legume": legume, "next_crop": nxt, "area": "hectare",
            "n_kg_ha": s["n_kg_ha"], "urea_n_share": share, "bag_kg": bag, "urea_kg_ha": s["urea_kg_ha"],
            "bags_ha": s["bags_ha"], "bags_ha_whole": s["bags_ha_whole"], "measured_uptake_kg_n_ha": up}


# ---------------- item 4: heat and cold at the sensitive times of wheat and potato ----------------
CHECKS = (   # (crop, kind, rule key, window stage, our column, NEX-GDDP column, stage word)
    ("wheat", "heat", "wheat_grain_filling_heat", "late", "tmax_c", "tasmax_c", "grain_filling"),
    ("potato", "heat", "potato_heat", "season", "tmax_c", "tasmax_c", "season"),
    ("potato", "cold", "potato_cold", "season", "tmin_frost_c", "tasmin_c", "season"),
    ("wheat", "heat", "wheat_floret_heat", "wheat_floret_window", "tmax_c", "tasmax_c", "floret_formation"),   # FAO's
    ("wheat", "cold", "wheat_flower_frost", "wheat_flower_window", "tmin_frost_c", "tasmin_c", "flowering"),   # wheat book
)
BOOK_CONDITIONS = {   # heat_clock.wheat_floret_*, wheat_flower_*: the conditions each wheat-book row carries
    "floret_formation": ["The book does not say which temperature of the day: we use the daily maximum, strictly above 30 C.",
                         "The book does not say when floret formation ends: we use its whole stage from floral initiation "
                         "(day 20) to anthesis (day 100), Table 3.1."],
    "flowering": ["Frost harms from flag leaf emergence to ten days after anthesis; flag leaf emergence is not in Table 3.1, "
                  "so the window starts at heading (day 90) and may start a little late; it ends on day 110.",
                  "Our nights (tmin_frost_c) count too many cold nights against Kathmandu Airport, while Bhaktapur's own "
                  "winter nights are 1.0-1.5 C colder than the twin's (VALIDATION.md 3.11b)."],
    "both": ["Table 3.1 counts days from emergence; we count from the sowing day (day 0; FAO-66 Table 1, India: emergence "
             "about 4 days after sowing). Its 140-day spring wheat is used as it is: our wheat is 140 days too.",
             "The dates are counted in a 365-day year, the same every year."],
}
PAST, FUTURE = (1995, 2014), (2026, 2040)


def _cell(x):
    return math.floor(x / 0.25) * 0.25 + 0.125


def nex_series(fid, field, data):
    """(table, whose) for the field: its own NEX-GDDP series, else its source field's when both lie in one 0.25 deg cell."""
    own = data / "clean" / fid / "nexgddp_daily.parquet"
    if own.exists():
        return pd.read_parquet(own), fid
    src = field.get("sample_of")
    if src and (data / "clean" / src / "nexgddp_daily.parquet").exists():
        sf = load_field(src)
        if (_cell(sf["lat"]), _cell(sf["lon"])) == (_cell(field["lat"]), _cell(field["lon"])):
            return pd.read_parquet(data / "clean" / src / "nexgddp_daily.parquet"), src
    return None, None


def build_heatclock(fid, data=REPO / "data", site=REPO / "site" / "data"):
    field, rules, lib = load_field(fid), load_rules(), load_crops()
    H = rules["heat_clock"]
    doc = json.loads((site / "fields" / f"{fid}.json").read_text())
    w = _weather(fid, data)
    nex, whose = nex_series(fid, field, data)
    found = {}
    for pid, _, crops in plans_of(doc):
        for c in crops:
            for crop, kind, rkey, stage, col, ncol, word in CHECKS:
                if c["crop"] == crop:   # the wheat-book rows (book True) come after the first three checks' rows
                    book = stage not in ("late", "season")
                    if book:
                        stage = (H[stage]["from_days_after_sowing"], H[stage]["to_days_after_sowing"])
                    key = (book, crop, c["start"], c["end"], word if book else kind)   # book rows: floret, then flowering
                    found.setdefault(key, (kind, rkey, stage, col, ncol, word, []))[6].append(pid)
    wins = {k: risk.window_mmdd({"crop": k[1], "start": k[2], "end": k[3]}, lib, v[2]) for k, v in found.items()}
    years = _years(doc, w, wins.values())
    d = w["date"].dt
    checks = []
    for k, (kind, rkey, stage, col, ncol, word, pids) in sorted(found.items()):
        (book, crop, sow, end, _), (a, b) = k, wins[k]
        rule = {k: v for k, v in H[rkey].items() if k not in ("temperature", "inclusive")}
        if H[rkey]["temperature"] != col or H[rkey]["inclusive"] != ("_or_" in next(iter(rule))):
            raise SystemExit(f"heat_clock.{rkey}: temperature {H[rkey]['temperature']} is not {col}, or inclusive "
                             f"does not match {rule}")
        n = risk.days_by_season(d.year, d.month, d.day, w[col], rule, a, b, years)
        fut = None
        if nex is not None:
            means = risk.model_means(nex, ncol, rule, a, b, {"historical": PAST, "ssp245": FUTURE, "ssp585": FUTURE})
            sc = {s: risk.scenario_summary(means, s) for s in ("ssp245", "ssp585")}
            fut = {"past": list(PAST), "period": list(FUTURE), "models": len(means), "column": ncol, "series_of": whose,
                   "metric": "mean risky days per complete season, each model in its own calendar", "scenarios": sc,
                   "good_news": all(m["future"] < 1 for s in sc.values() for m in s["models"])}
        checks.append({"id": f"{crop}_{sow.replace('-', '')}_{kind}", "crop": crop, "sow": sow, "end": end, "kind": kind,
                       "stage": word, "window": {"from": a, "to": b, "days": (pd.Timestamp(f"2002-{b}") - pd.Timestamp(
                           f"{2001 if risk._md(a) > risk._md(b) else 2002}-{a}")).days + 1},
                       "temperature": {"tmax_c": "daily maximum", "tmin_frost_c": "daily minimum"}[col], "column": col,
                       "rule": rule, "plans": sorted(set(pids)),
                       "today": {"years": [{"year": y, "days": n[y]} for y in years],
                                 "years_with": sum(v > 0 for v in n.values()),
                                 "mean_days": round(sum(n.values()) / len(years), 2),
                                 "good_news": all(v == 0 for v in n.values())},
                       "future": fut, "words": f"hc_{crop}_{word + '_' if book else ''}{kind}"})
        if book:      # heat_clock.wheat_book_checks: an estimate, with its conditions; its own id and screen words
            checks[-1].update(id=f"{crop}_{sow.replace('-', '')}_{word}_{kind}", sure="estimate",
                              days_after_sowing={"from": stage[0], "to": stage[1]},
                              conditions=BOOK_CONDITIONS[word] + BOOK_CONDITIONS["both"])
    book_rows = [c for c in checks if "sure" in c]
    book_dates = {k: "; ".join(f"sown {date_en(c['sow'])}: {date_en(c['window']['from'])} to {date_en(c['window']['to'])}"
                               for c in book_rows if c["stage"] == k) for k in ("floret_formation", "flowering")}
    book_dates_ne = {k: "; ".join(f"{date_ne(c['sow'])} मा रोपेको: {date_ne(c['window']['from'])} देखि "
                                  f"{date_ne(c['window']['to'])} सम्म" for c in book_rows if c["stage"] == k)
                     for k in ("floret_formation", "flowering")}
    en = ["Wheat: FAO-66 (FAO Irrigation and Drainage Paper 66, Crop yield response to water, 2012, p.98) says "
          "temperatures above 34 °C are possible during grain filling and can shrink the grain. It describes what is "
          "possible, not a tested limit, and does not say which temperature of the day: we count days whose highest "
          "temperature is above 34 °C.",
          f"Grain-filling weeks: the last growth stage of FAO-56, the {lib['wheat']['stages_days']['late']} days before "
          "harvest. FAO-66 gives no grain-filling length (its India row: flowering 70-103 days and maturity 85-145 days "
          "after sowing), so our weeks may miss the first days of grain filling.",
          "Potato: FAO-66 (p.187) puts cold stress at 1 °C and less and heat stress at 35 °C or more, with no crop stage, "
          "so we count the whole season: nights whose lowest temperature is 1 °C or less, and days whose highest is 35 °C "
          "or more. Varieties differ, and the damage depends on how strong and how long.",
          f"Today: our weather {years[0]}-{years[-1]} from NASA POWER (cells of about 55 km), corrected to Kathmandu "
          "Airport's thermometer. Our night temperatures count too many cold nights: in a check on years held back, they "
          "gave 15 nights below 2 °C where the station recorded 9. So the true number of cold nights is likely lower.",
          ("Around 2040: 23 climate models (NEX-GDDP-CMIP6, one cell of about 25 km), 2026-2040, on two paths: SSP2-4.5 "
           "(the world warms less) and SSP5-8.5 (the world warms more). The models are not corrected to our station, so "
           "each model's 2026-2040 is compared with its own 1995-2014. We show the middle model, and the lowest and "
           "highest." if nex is not None else "Around 2040: no climate-model series for this field yet."),
          "Left out: the '8-35 °C' pollen figure at wheat flowering. It is from FAO-66's rice chapter, not wheat. Rice and "
          "lentil are left out too: we found no checked limit for them.",
          "These are counts of past years and computer guesses, not a forecast."]
    nep = ["गहुँ: FAO-66 (FAO सिँचाइ तथा निकास पत्र ६६, बालीको पानीप्रतिको उब्जनी, २०१२, पृष्ठ ९८) भन्छ, दाना भरिने बेला "
           "३४ डिग्रीभन्दा बढी तापक्रम हुन सक्छ र दाना सानो पार्न सक्छ। यो हुन सक्ने कुरा हो, जाँचिएको सीमा होइन, र दिनको कुन "
           "तापक्रम भनेर लेखिएको छैन: हामी दिनको सबैभन्दा बढी तापक्रम ३४ डिग्रीभन्दा माथि भएका दिन गन्छौं।",
           f"दाना भरिने हप्ता: FAO-56 को अन्तिम चरण, काट्नुअघिका {ne(lib['wheat']['stages_days']['late'])} दिन। FAO-66 ले दाना "
           "भरिने अवधि दिँदैन (भारतको पङ्क्ति: रोपेको ७०–१०३ दिनमा फूल, ८५–१४५ दिनमा पाक्ने), त्यसैले हाम्रा हप्ताले दाना "
           "भरिने सुरुका केही दिन छुटाउन सक्छन्।",
           "आलु: FAO-66 (पृष्ठ १८७) अनुसार १ डिग्री वा कम चिसो र ३५ डिग्री वा बढी गर्मी हानिकारक हो, बालीको चरण नभनी; त्यसैले "
           "हामी पूरै सिजन गन्छौं: सबैभन्दा कम तापक्रम १ डिग्री वा कम भएका रात, र सबैभन्दा बढी ३५ डिग्री वा बढी भएका दिन। "
           "जातअनुसार फरक पर्छ, र हानि कति कडा र कति लामो भन्नेमा भर पर्छ।",
           f"आज: हाम्रो {ne(years[0])}–{ne(years[-1])} को मौसम, NASA POWER बाट (करिब ५५ किलोमिटरका कोठा), काठमाडौं विमानस्थलको "
           "थर्मामिटरसँग मिलाइएको। हाम्रा रातका तापक्रमले चिसो रात धेरै गन्छन्: अलग राखिएका वर्षको जाँचमा २ डिग्रीभन्दा कमका "
           "१५ रात देखाए, केन्द्रले ९ रात मात्र नापेको थियो। त्यसैले साँचो चिसो रात कम हुन सक्छन्।",
           ("सन् २०४० तिर: २३ वटा जलवायु मोडेल (NEX-GDDP-CMIP6, करिब २५ किलोमिटरको एउटा कोठा), २०२६–२०४०, दुई बाटोमा: "
            "SSP2-4.5 (संसार कम तातिए) र SSP5-8.5 (संसार बढी तातिए)। मोडेलहरू हाम्रो केन्द्रसँग मिलाइएका छैनन्, त्यसैले हरेक "
            "मोडेलको २०२६–२०४० लाई उसैको आफ्नै १९९५–२०१४ सँग दाँजिएको छ। बीचको मोडेल, र सबैभन्दा कम र बढी देखाइएको छ।"
            if nex is not None else "सन् २०४० तिर: यो खेतका लागि जलवायु मोडेलको शृङ्खला अझै छैन।"),
           "छाडिएको: गहुँ फुल्ने बेलाको '८–३५ डिग्री' परागको अङ्क। यो FAO-66 को धानको अध्यायबाट हो, गहुँको होइन। धान र मसुर "
           "पनि छाडिएका छन्: तिनका लागि जाँचिएको सीमा भेटिएन।",
           "यी विगतका वर्षको गन्ती र कम्प्युटरका अनुमान हुन्, पूर्वानुमान होइन।"]
    if book_rows:     # heat_clock.wheat_floret_*, wheat_flower_*: after the potato line
        en[3:3] = [
            "Wheat, from FAO's wheat book (Acevedo, Silva and Silva, 'Wheat growth and physiology', in Bread Wheat: "
            "Improvement and Production, FAO, 2002): 'Temperatures above 30°C during floret formation cause complete "
            "sterility', and frost harms 'between flag leaf emergence and ten days after anthesis' at 'minimum screen "
            "temperatures below 0°C'. Both checks are estimates.",
            "Floret weeks: the book does not say when floret formation ends, so we count its whole stage, from floral "
            f"initiation (day 20) to anthesis, when the wheat flowers (day 100), from its Table 3.1: "
            f"{book_dates['floret_formation']}. It does not say which temperature of the day: we count days whose highest "
            "temperature is above 30 °C.",
            "Frost weeks: Table 3.1 has no day for flag leaf emergence, so we start at heading (day 90), which follows it, "
            f"and end ten days after anthesis (day 110): {book_dates['flowering']}. So our weeks may start a little late. "
            "We count nights whose lowest temperature is below 0 °C. Two checks point opposite ways: our nights count too "
            "many cold nights against Kathmandu Airport, but DHM's Bhaktapur normals put winter nights (November to April) "
            "1.0-1.5 °C colder than ours. So the true number of frost nights may be lower or higher.",
            "Table 3.1 counts days from emergence; we count from the sowing day (emergence comes about 4 days after "
            "sowing in FAO-66's India row), so our weeks may sit a few days early. Its spring wheat takes 140 days, as "
            "ours does. The dates are the same every year (a 365-day year)."]
        nep[3:3] = [
            "गहुँ, FAO को गहुँ पुस्तकबाट (Acevedo, Silva र Silva, 'Wheat growth and physiology', Bread Wheat: Improvement "
            "and Production, FAO, २००२): फूलका कोपिला बन्दा ३० डिग्रीभन्दा बढी तापक्रमले गहुँ पूरै बाँझो हुन्छ, र झण्डा-पात "
            "निस्केदेखि फुलेको दस दिनपछिसम्म ० डिग्रीभन्दा कमको तुषारोले हानि गर्छ। दुवै जाँच अनुमान हुन्।",
            "फूलका कोपिला बन्ने हप्ता: पुस्तकले यो कहिले सकिन्छ भन्दैन, त्यसैले हामी पूरै चरण गन्छौं, फूल बन्न थाल्ने (दिन २०) "
            f"देखि गहुँ फुल्ने (दिन १००) सम्म, यसको तालिका ३.१ अनुसार: {book_dates_ne['floret_formation']}। दिनको कुन "
            "तापक्रम भनेर लेखिएको छैन: हामी दिनको सबैभन्दा बढी तापक्रम ३० डिग्रीभन्दा माथि भएका दिन गन्छौं।",
            "तुषारोका हप्ता: तालिका ३.१ मा झण्डा-पात निस्कने दिन छैन, त्यसैले हामी बाला निस्कने दिन (दिन ९०) बाट सुरु "
            f"गर्छौं, जुन त्यसपछि आउँछ, र फुलेको दस दिनपछि (दिन ११०) सकाउँछौं: {book_dates_ne['flowering']}। त्यसैले "
            "हाम्रा हप्ता अलि ढिलो सुरु हुन सक्छन्। हामी सबैभन्दा कम तापक्रम ० डिग्रीभन्दा कम भएका रात गन्छौं। दुई जाँच "
            "उल्टो दिशा देखाउँछन्: हाम्रा रातले काठमाडौं विमानस्थलको तुलनामा चिसो रात धेरै गन्छन्, तर DHM को भक्तपुरको "
            "औसतमा जाडोका रात (नोभेम्बरदेखि अप्रिल) हाम्रोभन्दा १.०–१.५ डिग्री चिसा छन्। त्यसैले साँचो तुषारो रात कम वा "
            "बढी हुन सक्छन्।",
            "तालिका ३.१ ले उम्रेको दिनदेखि गन्छ; हामी रोपेको दिनदेखि गन्छौं (FAO-66 को भारतको पङ्क्तिअनुसार रोपेको करिब ४ "
            "दिनमा उम्रन्छ), त्यसैले हाम्रा हप्ता केही दिन चाँडो पर्न सक्छन्। यसको वसन्ते गहुँ १४० दिनको हो, हाम्रो पनि "
            "त्यति नै। मिति हरेक वर्ष उस्तै हुन्छन् (३६५ दिनको वर्ष)।"]
    if whose and whose != fid:
        en.append(f"The climate models' cell is the {whose} field's: both fields lie in the same 0.25 degree cell.")
        nep.append(f"जलवायु मोडेलको कोठा {whose} खेतकै हो: दुवै खेत एउटै ०.२५ डिग्रीको कोठामा पर्छन्।")
    card = load_scorecard(fid, field, data)
    srcs = [_src(doc, "NASA POWER"), _src(doc, "Kathmandu Airport"), DOCS["fao66"], DOCS["fao56"]]
    if nex is not None:
        srcs.insert(2, _src(json.loads((site / "fields" / f"{whose}.json").read_text()), "NEX-GDDP"))
    srcs += [DOCS["bread_wheat"]] if book_rows else []
    labels = {k: label_for(k, field, rules, card) for k in ("heatclock_today", "heatclock_2040")}
    out = _base("heatclock", fid, field, {"en": en, "ne": nep}, srcs, labels)
    return {**out, "years": years, "year_count": len(years),
            "left_out": ["rice", "lentil", "wheat pollen at flowering (8-35 C, a rice figure)"], "checks": checks}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--kind", required=True, choices=KINDS)
    a = ap.parse_args(argv)
    doc = {"rainrisk": build_rainrisk, "fertiliser": build_fertiliser, "heatclock": build_heatclock}[a.kind](a.field)
    out = REPO / "site" / "data" / a.kind / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(REPO))
    sys.exit(main())
