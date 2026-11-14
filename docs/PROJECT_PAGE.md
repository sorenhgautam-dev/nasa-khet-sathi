# Khet Sathi: project page texts (draft)

Draft for the Space Apps 2026 project page, written 14 November 2026. Numbers may change: each is listed in "Numbers
used" at the end (for us, not the page).

## Summary

Khet Sathi ("field friend" in Nepali) is a phone website that helps smallholder farmers choose what to grow, and when,
using NASA data. For one field it replays every season from 2001 to 2025 through a small model of the soil's water and
crops, tests 165 crop plans, and shows three: today's plan and two others, each with its evidence, its unknowns and what
to check locally. Along the way we found that the rain gauges behind NASA's rain product went silent around our field
in January 2017; we measured the break in NASA's own data, confirmed it in five other records and corrected it.
Everything heavy runs ahead of time, so the site is plain files that open on a phone, Nepali first, and every number
says where it came from and how sure we are.

## Project details

**What it does.** For one field the site shows what satellites saw, the field in small parts, the last 24 years as
baskets of harvest, three plans with five tabs each (why, evidence, benefits, unknowns, what to check locally), the
field in 2040, and a takeaway: "you know your land best".

**How.** A Python pipeline downloads public data around the field. A "twin" of the field (FAO-56 soil water, FAO-33
harvest) runs day by day, on rain alone and with water whenever needed, and scores 165 rotations on harvest, water,
ground cover and soil kept. Harvest is a share of what the field could grow, never tonnes. The site only reads the JSON
files this writes.

**Who it is for.** Smallholder farmers, Nepal first, and the extension workers and co-operatives who advise them.

**Real:** the replay, the three plans with tabs in English and Nepali, the diary (seasons, bare days, regional stored
water, monthly calendar, the monsoon's start from Nepal's weather office, DHM), the 2040 outlook (23 climate models),
four field parts with their own greenness, and a "How we know" page that scores every output.

**Placeholder:** the demo field is a labelled sample, a 60 m square of mapped cropland near Bhaktapur, Nepal, chosen by
us from satellite maps. It is not a farmer's field yet. Its crops (rice, then potato), dates, water source (unknown) and
soil (a map cell 859 m away) are placeholders too, as are three nearby sample fields. No farmer has checked any number.

## Use of AI (SI)

**Inside the product,** all at build time. The site never calls an AI service; nothing leaves the phone.
- **Season detective:** a random-forest classifier labels each date growing, harvested or bare. On five held-out years
  it kept 98.0% of the reference labels against 96.7% for a simple threshold method: below the 2-point margin fixed in
  advance, so the site uses the simpler method. (No ground truth: this tests robustness, not accuracy.)
- **Field memory:** a learned correction did worse than physics alone on held-out years (error 0.0350 against 0.0321),
  so it is not used, and the method page says so.
- **Plain words:** SI drafted the tabs and tips (templates filled with the numbers), the glossary and the Nepali, plus
  draft translations into Hindi, Bengali, Spanish, French and Swahili, labelled as drafts.

**To build it:** Claude Code (Anthropic's Claude Opus 5.5) wrote most of the pipeline code and tests under our
direction, and built the site from our UI teammate's design. The "Fable review" (Claude Fable 5.2, `REVIEW_2.md`), an
independent AI review of the 13 November version, recomputed the equations, corrections and plan scores with its own
code (they reproduced to rounding) and listed fixes. We used Perplexity for research.

**How people checked it:** Claude proposed; we decided every method, rule and threshold, and since 13 November each rule
is committed before its first run. The physics is tested against published worked examples. `SI_LOG.md` lists what a
person must still review: all Nepali, the draft translations, the newest English lines and the Fable review.

## Data

| NASA data | Product | Its job |
| --- | --- | --- |
| GPM IMERG | V07 Final daily (GPM_3IMERGDF); Late daily (GPM_3IMERGDL); Final monthly (GPM_3IMERGM) | The model's rain; the 2017 break |
| NASA POWER | Daily API v2.10.3 (MERRA-2, GEOS-IT, CERES) | Temperature, humidity, wind, sunshine |
| HLS | HLSL30_VI, HLSS30_VI v2.0, 30 m | Greenness: seasons, bare days, crop guess, parts |
| MODIS | MOD13Q1 v061 | Compared with HLS only |
| SMAP | SPL4SMGP v008, SPL3SMP_E v006 | Checks the model's soil water |
| GRACE / GRACE-FO | JPL mascon CRI RL06.3 v04 | Regional stored-water trend |
| NASADEM | NASADEM_HGT v001 | Height, slope, low ground |
| ECOSTRESS | ECO_L2T_LSTE, ECO_L4T_ESI V003 | A check on crop stress |
| GLDAS | GLDAS_NOAH025_M v2.1 | Checks soil water, water use, rain |
| NEX-GDDP-CMIP6 | v2.0, SSP2-4.5 and SSP5-8.5 | Climate to 2040 |

**The challenge's resource list** (DATA_AUDIT 8). *Used:* SMAP, GPM IMERG, NASA POWER, ECOSTRESS, GLDAS, Landsat,
Sentinel-2, MODIS, SRTM. *US only, so an equivalent:* SoilGrids (for Web Soil Survey, SSURGO/STATSGO2), WorldCover
(Cropland Data Layer, NLCD), DHM (PRISM, CoCoRaHS), FAOSTAT (NASS QuickStats). *Not used:* VIIRS, NAIP, NWIS, OpenET,
LANDFIRE, Ag Data Commons, AMS Market News (no money figures), GEDI (forest canopy), ERA5, FAO GAEZ (linked only:
non-commercial licence).

**Other data:** DHM (normals, bulletins, onset dates, event reports), ISRIC SoilGrids 2.0, ESA WorldCover, NOAA
GHCN-Daily, FAOSTAT, CHIRPS v3.0, GPCC, OpenStreetMap. Citations: `CREDITS.md`.

## Case study: a flood, then a winter without rain

The sample field, 2024-2025. Harvest is out of 100; a year holds that spring's winter crop and that year's rice.

| Harvest (dry days) | Today: rice, then potato | Fill the empty months: rice, then wheat | Feed your soil: rice, then lentil |
| --- | --- | --- | --- |
| 2024, flood year, rain-fed | 63 (105) | 88 (63) | 80 (87) |
| 2025, after the dry winter, rain-fed | 62 (96) | 85 (62) | 77 (81) |
| 2025, rain scaled to DHM's normals | 61 | 83 | 74 |
| 2024 and 2025, if you can water | 100 (0) | 100 (0) | 100 (0) |
| Mean 2002-2025, rain-fed | 67 | 86 | 78 |

**The storm.** On 28 September 2024 DHM measured new 24-hour records: 194.5 mm at Nangkhel, Bhaktapur, and 239.7 mm at
Kathmandu Airport. The model's rain has 158.8 mm on 27 September (a UTC day) and flags 2024 a flood year. The model
counts only thirst, so the flood takes no harvest; the real storm damaged standing paddy.

**The dry winter.** Bhaktapur's gauge had 0.0 mm from December 2024 to February 2025 (normal 47.8 mm); the model has
16.7 mm and flags 2025 a drought. Today's potato got 26.8 mm in its season and about a third of the water it needed.

**The plans.** Without water, both suggestions do better. Much of the gain comes from root depth (wheat 1.5 m, lentil
0.8 m, potato 0.6 m in the model); with shallower roots it shrinks. With water, every plan scores 100 every year, by
construction, so the gain matters only where winter water is short. The wheat plan's own tab warns that wheat here
usually needs watering.

**What it got wrong.** The 2025 flag also covers the 2025 monsoon, which DHM had at 117% of normal. The winter of
2023/24, also a valley drought (Bhaktapur 13.8 mm), was missed: the model had 47.4 mm.

## Our headline finding: NASA's rain lost its gauges here in 2017

NASA's daily rain (GPM IMERG Final) blends satellite estimates with monthly gauge totals. Around our field the gauges
dropped out in January 2017. The satellite estimate, wetter here, took over: yearly rain jumped from 1,842 mm
(2001-2016) to 2,731 mm (2017-2025). It looks like climate change. It is a data break.

1. **NASA's own record:** IMERG's gauge share, 96-98% in every month of 2001-2016, falls to 56-72% a year from 2017 (VALIDATION 3.9b).
2. **The gauge archive:** GPCC, behind IMERG, had about 50 stations a month in the field's 1° box in 2011-2016, about 1
   in 2017-2020 (3.9b).
3. **A change-point test** on GPM's yearly totals: change after 2016, p 0.0014 (3.9b).
4. **CHIRPS v3.0:** no step (1,454 mm a year before, 1,437 after; p 0.24) (3.9b).
5. **IMERG Late,** without monthly gauges, steps 1.13 where Final steps 1.62 (3.9b).
6. **DHM's gauges, 2025:** in three IMERG Final months, GPM reads 1.27 times the gauges, our corrected rain 0.88 (3.9c).
7. **GLDAS's rain:** no 2017 step; it follows our corrected rain (r 0.70) far better than GPM as published (r 0.40) (4.2d).

GPCC, CHIRPS and GLDAS share some gauges, so they are not fully independent. **The fix:** each month from 2017 scaled
back to GPM's 2001-2016 level; on held-out years the monthly error against the airport fell from 93.7 to 31.4 mm.
**Limits:** it restores the level, not the order of wet and dry years; the rain is still 1.35 times DHM's Bhaktapur
normal; October-December 2025 still reads too wet (1.64 times). So the site also shows a drier case.

## The soil probe's proof

**WAITING FOR THE BENCH TEST:** "readings agree within X points; drier soil always reads drier; against weighed water
the probe is off by about Y." Until then the site gives no water number from the probe, only "drier" or "wetter than the
other parts".

## The awards we aim at

**Best Use of Data (top priority).** *For:* ten NASA data sources, each with a job and a check (DATA_AUDIT 7); the 2017
break found in IMERG's own gauge-weight field and confirmed in five other records; each source's effect measured by
switching it off; source, resolution and years on every number. *Not yet:* no shown number uses MODIS; ECOSTRESS had
too few clear passes to test; SMAP L3 had no good value here; GRACE is a 300 km regional signal; the rain still reads
1.35 times the local normal.

**Best Use of Science.** *For:* the equations reproduce FAO-56's printed examples; rules committed before they run;
held-out years and negative controls; every shown output scored against a yardstick fixed in advance; a learned model
that lost to physics, dropped and reported. *Not yet:* no ground truth. Harvest numbers are low confidence (only wheat
years follow Nepal's national yields, r 0.52). The model cannot show a bad rice year. Dry years: 2 of 4 found. Today's
plan follows satellite sowing dates, the suggestions calendar dates, which tilts the comparison.

**Best Use of Technology.** *For:* no backend: plain files on Vercel, no login, no keys. A test-first pipeline (1,461 tests
passing at the last recorded run) and a validator that refuses made-up numbers. An open probe (ESP32, two sensors) and
a Kalman update that passes hand-worked tests. *Not yet:* the bench test; the online probe; a test with new users.

**Local Impact.** *For:* Nepali first, Bikram Sambat months, Nepal's own data, valley floods and droughts checked by
name. The 2017 break may affect anyone using NASA's rain in Nepal after 2016: GPCC's neighbouring boxes lost their
stations too. *Not yet:* no farmer has used it; the field is a placeholder; the Nepali awaits a native speaker.

**Galactic Impact.** *For:* the model's inputs are global datasets. The rain-break test runs per field: in Madagascar it
found no break and kept NASA's rain as published. Open code (MIT) and probe design; drafts in five more languages.
*Not yet:* no field outside Nepal is on the site; the translations are unreviewed; the crop calendars are Nepal's.

## How farmers would get this

A phone link, Nepali first: no app, no account, best used with a helper, an extension worker or co-operative member.

1. **A co-operative names its fields:** corners, crops and dates, and whether each can be watered: what our placeholder
   lacks.
2. **We prepare each field** on a laptop; the site itself never computes.
3. **The helper sits with the farmer:** the replay first ("were these your bad years?"), then the plans and the "check
   locally" tab. The answers become our first ground truth.
4. **Once the probe passes its bench test,** the helper reads each part of the field.

Every plan says "try it on one small part first". The tool supports the farmer's judgment; it never replaces it.

## Numbers that are safe to say in the 30-second video

| Say it like this | Source |
| --- | --- |
| "Around this field, NASA's rain lost its ground gauges in January 2017. We found it in NASA's own data." | VALIDATION 3.9b |
| "We fixed it. In three months of 2025 our rain read 0.88 times Nepal's gauges; NASA's as published, 1.27 times." | 3.9c |
| "Each month's rain and heat words match Nepal's weather office in 12 of 12 months." | Compliance table (VERIFIED; tests the shape of the year) |
| "We replayed 24 years of weather and tested 165 crop plans." | `demo.json` `replay`; 3.19 |
| "Ten NASA data sources, each with a job and a check." | DATA_AUDIT 7 |
| "In our model, without watering, filling the empty winter months lifts harvest from 67 to 86 out of 100." | `demo.json` `plans` (ESTIMATE: say "in our model") |

Do not say: any probe accuracy, "2 of 2 floods" (not a blind test), or a single "percent verified".

## Numbers used

| Number | Where | Source |
| --- | --- | --- |
| 165 plans | Summary, details, video | `data/checks/demo/plans.json` `n_plans`; VALIDATION 3.19 |
| 2001-2025; 24 years (2002-2025) | Summary, details, video | `site/data/fields/demo.json` `replay` (24 entries a plan) |
| 60 m square; soil cell 859 m away | Details | VALIDATION 1.4; `demo.json` `sources` (ISRIC SoilGrids) |
| 23 models, two futures | Details | `demo.json` `future.models`, `future.scenarios` |
| Four parts | Details | `demo.json` `field.sections` |
| Three sample fields | Details | `site/data/index.json` |
| 98.0% vs 96.7%; 2-point margin; five held-out years | SI | VALIDATION 3.15 |
| 0.0350 vs 0.0321 | SI | VALIDATION 4.6 |
| Five draft languages | SI, awards | `site/data/words.json` `languages`; CREDITS SI table |
| 2024: 63/88/80, dry days 105/63/87 | Case study | `demo.json` `replay.<plan>`, year 2024 |
| 2025: 62/85/77, dry days 96/62/81 | Case study | `demo.json` `replay.<plan>`, year 2025 |
| 2025 DHM-scaled: 61/83/74 | Case study | `demo.json` `replay.<plan>`, 2025 `dhm_rain.harvest` |
| 100 (0) if you can water | Case study | `demo.json` `replay.<plan>[].irrigated`; METHOD_NOTES 38 |
| Means 67/86/78 | Case study, video | `demo.json` `plans[].score.harvest` |
| 194.5 and 239.7 mm, 28 Sep 2024 | Case study | `config/known_events.yaml` `kathmandu_floods_2024_09` |
| 158.8 mm, 27 Sep 2024 | Case study | VALIDATION 4.1; `data/clean/demo/weather.parquet` `rain_mm` |
| 0.0 mm; normal 47.8 mm | Case study | `known_events.yaml` `winter_drought_2024_25` |
| 16.7 mm (Dec 2024-Feb 2025); 47.4 mm (Dec 2023-Feb 2024) | Case study | `weather.parquet` `rain_mm`, summed |
| 26.8 mm; a third of its water (0.34) | Case study | `data/checks/demo/replay.json` `rain-fed.seasons`, potato from 2024-11-24 |
| Root depths 1.5, 0.8, 0.6 m | Case study | METHOD_NOTES 35; VALIDATION 4.4 |
| 117% of normal | Case study | VALIDATION 4.1 (negative controls) |
| 13.8 mm (winter 2023/24) | Case study | `known_events.yaml` `winter_drought_2023_24` |
| 1,842 and 2,731 mm | Headline | `demo.json` `method.rain_correction.rain_mm_per_year` |
| 96-98%; 56-72% | Headline, video | VALIDATION 3.9b; `method.rain_correction.gauges` |
| About 50 and about 1 stations | Headline | VALIDATION 3.9b |
| p 0.0014 | Headline | VALIDATION 3.9b (Pettitt) |
| 1,454 and 1,437 mm; p 0.24 | Headline | VALIDATION 3.9b (CHIRPS) |
| 1.13 and 1.62 | Headline | VALIDATION 3.9b (IMERG Late) |
| 1.27, 0.88 and 1.64 times | Headline, video | VALIDATION 3.9c |
| r 0.70 and 0.40 | Headline | VALIDATION 4.2d |
| 93.7 to 31.4 mm; 48 months | Headline | `method.rain_correction.held_out`; VALIDATION 3.9b |
| 1.35 times the normal | Headline, awards | VALIDATION 3.1, 3.9d |
| Ten NASA data sources | Awards, video | The data table above (DATA_AUDIT 7) |
| 300 km | Awards | VALIDATION 3.16 |
| r 0.52 (wheat) | Awards | `site/data/story.json` `report_card` (harvest); VALIDATION 4.3 |
| 2 of 4 dry seasons | Awards | Compliance table; `data/checks/demo/scorecard.json` `drought_years` |
| 1,461 tests | Awards | full suite run 2026-11-14, about 10:45, exit 0 |
| 12 of 12 months | Video | Compliance table; `scorecard.json` `rain_month_words`, `heat_month_words` |
