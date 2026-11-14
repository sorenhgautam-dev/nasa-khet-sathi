# Khet Sathi: project page texts (draft)

Draft for the Space Apps 2026 project page, rewritten 14 November 2026 (afternoon) around the farmer's question and the
four features. Every number has an ID in square brackets, e.g. [A2]: its source is in `docs/PITCH_FACTS.md`. Refresh
numbers there first. The IDs are for us, not for the page: remove them before pasting.

## Summary

Khet Sathi ("field friend" in Nepali) is a phone website for smallholder farmers. It answers one question: "What can I
grow in my field's empty months without risking the harvest I depend on?" [B1]. Seen from space, about 15 in every 100
farm squares around Bhaktapur, Nepal lie bare for more than two months a year (could be 0 to 31) [A2], and only about 4
in 10 grow two crops [A4]. For one field, Khet Sathi runs each crop plan through every past season in our record, shows
the field's greenness history, lets a farmer try a plan on one quarter of the field, and shows how we checked the field's
rain record. Every number carries two labels: how sure we are, and how close the data is to the field. It is plain files,
Nepali first, with no account and no server.

## Project details

**The question.** A farmer near Bhaktapur grows rice in the monsoon. The months between crops are often empty. A new
winter crop could fill them, but it could also fail, or take water the rice needs. Khet Sathi shows the evidence for one
field, one plan at a time, and leaves the choice to the farmer.

**Four features.**
1. **25-Year Replay.** Each plan's coming season is run through every past season in our record: 24 complete years,
   2002-2025 [B3, C1]. One square per year, marked worked, struggled or failed, with the reason (a flood year, a dry
   year) [C2]. Years with the same El Niño or La Niña state as this year are highlighted (NOAA ONI). The run starts from
   the field's soil water today, dry, medium or wet, picked with the soil probe [C6]. Tabs show the next 3 and 6 months.
   Every square is an estimate.
2. **Field Pulse (खेतको नाडी).** The field's greenness history from space, drawn as a heartbeat line in Bikram Sambat
   months. HLS at 30 m is field scale; MODIS at 250 m is neighbourhood scale [D1]. It finds two green seasons a year
   [D2]. The farmer confirms or corrects planting and harvest dates; the answers stay on the phone [D6]. Nearby fields
   are shown as totals from our area map [A1-A4].
3. **Safe Trial.** Try a plan on one quarter of the field [E1]. The probe's four spots become the experiment: one in the
   trial quarter, three in the rest. A weekly photo diary stays on the phone. After harvest the trial is compared with
   the rest of the field and with the Replay's estimate. Results come after the season [E4].
4. **Data Check-up.** How we checked the field's rain record. NASA's daily rain (IMERG Final) blends satellite estimates
   with monthly rain-gauge totals. Around this field, the gauges' share fell from 96-98% to 56-72% a year from 2017
   [F1], as reporting gauges went from about 50 a month to about 1 [F2]. CHIRPS shows no step [F4]. Our correction
   scales the rain back, and each field runs its own check [F7, F13]. Numbers that depend on the corrected rain are
   flagged and shown as a range [F14].

**Two labels on every number.** *How sure:* Verified, Estimate or Not yet checkable, from a scorecard fixed before any
score [G1-G4]. *How close:* your field, neighbourhood, valley or region, from each source's resolution [G5].

**How.** A Python pipeline downloads public data around the field. A small model of the field (the "twin": FAO-56 soil
water, FAO-33 harvest) runs day by day on rain alone and with water whenever needed, and scores 165 crop plans on
harvest, water, ground cover and soil kept [B2]. Harvest is a share of what the field could grow, never tonnes. The site
only reads the files this writes.

**Who it is for.** Smallholder farmers, Nepal first, and the extension workers and co-operatives who advise them.

**Real:** the replay of three plans; the tabs in English and Nepali; the greenness history and seasons; the area map;
the rain check and its correction; the 2040 outlook (23 climate models) [H11]; four field parts with their own
greenness [E1]; and a "How we know" page that labels every output.

**Placeholder:** the demo field is a labelled sample: a 60 m square of mapped cropland near Bhaktapur, chosen by us from
maps [B4]. It is not a farmer's field yet. Its crops (rice, then potato), dates, water source (unknown) and soil (a map
cell 859 m away [B6]) are placeholders, as are the four nearby sample fields [B5]. No farmer has checked any number.

## Use of AI (SI)

**Inside the product,** all at build time. The site never calls an AI service; nothing leaves the phone.
- **Season detective:** a random-forest classifier labels each date growing, harvested or bare. On five held-out years
  it scored 0.980 against 0.967 for a simple threshold method: below the 0.02 margin fixed in advance, so the site uses
  the simpler method [D4]. (No ground truth: this tests robustness, not accuracy.)
- **Field memory:** a learned correction did worse than physics alone on held-out years, so it is not used, and the
  method page says so [J4].
- **Plain words:** SI drafted the tabs and tips (templates filled with the numbers), the glossary and the Nepali, plus
  draft translations into Hindi, Bengali, Spanish, French and Swahili, labelled as drafts [I5].

**To build it:** Claude Code (Anthropic's Claude Opus 5.5) wrote most of the pipeline code and tests under our
direction, and built the site from our UI teammate's design. The "Fable review" (Claude Fable 5.2, `REVIEW_2.md`), an
independent AI review of the 13 November version, recomputed the equations, corrections and plan scores with its own
code and listed fixes. We used Perplexity for research.

**How people checked it:** Claude proposed; we decided every method, rule and threshold, and each rule is committed
before its first run [J6]. The physics is tested against published worked examples [J2]. `SI_LOG.md` lists what a person
must still review: most of the Nepali (32 of 385 texts checked so far [I5]), the draft translations and the newest
English lines.

## Data

| NASA data | Product | Its job |
| --- | --- | --- |
| GPM IMERG | V07 Final daily (GPM_3IMERGDF); Late daily (GPM_3IMERGDL); Final monthly (GPM_3IMERGM) | The model's rain; the rain check |
| NASA POWER | Daily API v2.10.3 (MERRA-2, GEOS-IT, CERES) | Temperature, humidity, wind, sunshine |
| HLS | HLSL30_VI, HLSS30_VI v2.0, 30 m | Field Pulse, seasons, bare days, the area map, the field's parts |
| MODIS | MOD13Q1 v061 | Older greenness, compared with HLS only |
| SMAP | SPL4SMGP v008, SPL3SMP_E v006 | Checks the model's soil water; sets how sure it is |
| GRACE / GRACE-FO | JPL mascon CRI RL06.3 v04 | Regional stored water, as context |
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

The sample field, 2024-2025, from the 25-Year Replay. Harvest is out of 100; a year holds that spring's winter crop and
that year's rice [M1, M2, C5, H1-H3].

| Harvest (dry days) | Today: rice, then potato | Fill the empty months: rice, then wheat | Feed your soil: rice, then lentil |
| --- | --- | --- | --- |
| 2024, flood year, rain-fed | 65 (108) | 85 (70) | 75 (98) |
| 2025, dry year, rain-fed | 63 (96) | 83 (65) | 73 (88) |
| 2024 and 2025, if you can water | 100 (0) | 100 (0) | 100 (0) |
| Mean 2002-2025, rain-fed | 65 | 83 | 74 |

**The storm.** On 28 September 2024 DHM measured 194.5 mm at Nangkhel, Bhaktapur, and 239.7 mm at Kathmandu Airport in
24 hours [M3]. The replay flags 2024 a flood year. The model counts only thirst, so the flood takes no harvest; the real
storm damaged standing paddy.

**The dry winter.** DHM's Bhaktapur gauge had 0.0 mm from December 2024 to February 2025 (normal 47.8 mm) [M4]. In the model,
today's potato (30 October 2024 to 21 February 2025) got 14.1 mm of rain and about a third of the water it needed; its
harvest was 27 out of 100 [M5].

**The plans.** Without water, both suggestions do better, in every year of the replay [C3]. Much of the gain comes from
root depth (wheat 1.5 m, lentil 0.8 m, potato 0.6 m in the model) [M6]; with shallower roots it shrinks [H2, H3]. With water,
every plan scores 100 every year, by construction, so the gain matters only where winter water is short [C5]. The wheat
plan's own tab warns that wheat here usually needs watering.

**What it got wrong.** The 2025 flag also covers the 2025 monsoon, which DHM had at 117% of normal. The valley's dry
winter of 2023/24 was missed: the replay shows 2024 as a flood year instead [M7].

## What our rain check found

NASA's daily rain (IMERG Final) blends satellite estimates with monthly gauge totals. Around our field, the gauge input
changed in January 2017: far fewer gauges reported, and the satellite estimate, wetter here, carried more weight. NASA's
yearly rain at the field went from 1,842 mm (2001-2016) to 2,731 mm (2017-2025) [F3]. That looks like a wetter climate.
Our check says it is a change in the inputs.

1. **NASA's own record:** the gauges' share, 96-98% in every month of 2001-2016, falls to 56-72% a year from 2017 [F1].
2. **The gauge archive:** GPCC, behind IMERG, had about 50 stations a month in the field's 1° box in 2011-2016, about 1
   in 2017-2020 [F2].
3. **A change-point test** on NASA's yearly totals: a change after 2016, p 0.0014 [F3].
4. **CHIRPS v3.0:** no step (1,454 mm a year before, 1,437 after; p 0.24) [F4].
5. **IMERG Late,** without monthly gauges, steps 1.13 where Final steps 1.62 [F5].
6. **GLDAS's rain:** no 2017 step; it follows our corrected rain (r 0.70) far better than NASA's as published (r 0.40)
   [F6].

GPCC, CHIRPS and GLDAS share some gauges, so they are not fully independent. **The correction:** each month from 2017
scaled back to the 2001-2016 level; on held-out years the monthly error against the airport fell from 93.7 to 31.4 mm
[F7]. Then, by a rule fixed in advance, it was matched to four of Nepal's rain gauges: about 25% less rain outside the
monsoon, about 5% more in it [F8]. That version won narrowly, within the noise [F9]. **Limits:** the correction restores
the level, not the order of wet and dry years; the rain is still 1.33 times Bhaktapur's usual [F10]; and the check
against the gauges is in-sample now [F11]. So every rain-dependent number is shown as a range [F14]. Each field runs this
check itself: in Madagascar it found no change and kept NASA's rain as published [F13].

## The soil probe's proof

**WAITING FOR THE BENCH TEST:** "readings agree within X points; drier soil always reads drier; against weighed water
the probe is off by about Y." Until then the site gives no water number from the probe [E3]. Safe Trial uses the
probe's four spots only to compare parts of the same field.

## The awards we aim at

**Best Use of Data (top priority).** *For:* ten NASA data sources, each with a job and a check [J7]; the 2017 rain change
found in IMERG's own gauge-weight field and checked in five other records [F1-F6]; every field runs its own rain check
[F13]; the area map turns 4,300 hectares of cropland into a few honest numbers with ranges [A1-A4]; source, resolution
and "how close" on every number [G5]. *Not yet:* no shown number uses MODIS; ECOSTRESS had too few clear passes to test;
SMAP L3 had no good value here; GRACE is a 300 km regional signal; the rain still reads 1.33 times the local normal
[F10].

**Best Use of Science.** *For:* the equations reproduce FAO-56's printed examples [J2]; rules committed before they run,
and two model changes tried, undone and recorded [J6]; held-out years and negative controls; every shown
output labelled against a yardstick fixed in advance [G1]; a learned model that lost to physics, dropped and reported
[J4]. *Not yet:* no ground truth. Harvest numbers are low confidence: only wheat years follow Nepal's national yields
(r 0.55) [J5]. The model cannot show a bad rice year [H10]. Dry years: 2 of 4 found [C2].

**Best Use of Technology.** *For:* no backend: plain files on Vercel, no login, no keys [I1]. A test-first pipeline
(1,494 tests collected [J1]) and a validator that refuses made-up numbers. An open probe (ESP32, two sensors) and a
Kalman update that passes hand-worked tests [M8]. *Not yet:* the bench test; offline use [I6]; a test with new users
(`docs/FARMER_TEST.md`).

**Local Impact.** *For:* Nepali first, Bikram Sambat months, Nepal's own data, valley floods and droughts checked by
name; the area map shows how much of the valley floor's cropland sits empty [A2, A4]. The 2017 gauge change may affect
anyone using NASA's rain in Nepal after 2016: GPCC's neighbouring boxes lost their stations too [F2]. *Not yet:* no farmer
has used it; the field is a placeholder; most of the Nepali awaits a native speaker [I5].

**Galactic Impact.** *For:* the model's inputs are global datasets, and one command builds a field [I3, I4]. The rain
check runs per field: in Madagascar it found no change and kept NASA's rain as published [F13]. Open code (MIT) and
probe design; drafts in five more languages. *Not yet:* no field outside Nepal is on the site (one is built, VALIDATION 3.26);
the translations are unreviewed.

## Global, usable everywhere

**Built and verified in Nepal; any organisation can set it up for any field on Earth with one command; better wherever
a country adds its profile. Next step: a hosted service for instant check-ups.**

**Global core, local plug-ins.** The twin, the plans and the site are the same everywhere. What is country-specific
lives in one profile file per country, each setting with its source: rain classes, dry day and dry spell, drought
seasons, rain gauges, crop-calendar zone, calendar, language, area units and fertiliser notes. Nepal's profile is the
first. A country with no profile gets sourced global defaults: ETCCDI's dry day (under 1 mm) and rain indices, NOAA's
GHCN-Daily and GPCC rain gauges, the FAO Crop Calendar for its zone, Gregorian months and hectares.

**One command.** `scripts/make_site.py` takes a point, a size, a name and a country. It writes the field's settings
(anything unknown is left as a question, never guessed), downloads the public data, runs every step and writes a folder
of plain files to host free on GitHub Pages, Vercel or Netlify. It needs a free NASA Earthdata login. A new field takes
about 3 to 4 hours, nearly all of it downloads (`docs/DEPLOY_ANYWHERE.md`).

**A field on another continent.** A placeholder field in Madagascar's central highlands was built with the kit on the
global defaults: its own rain check (no gauge change found, so NASA's rain is used as published), its own FAO crop
calendar (rainy-season rice, then dry-season potato), and labels that say "not yet verifiable" wherever no local check
exists. It never borrows Nepal's checks. It is not on the live site yet: the third plan's words and name were written
for Nepal's pulse crop and must first follow the field (VALIDATION 3.26).

## How farmers would get this

A phone link, Nepali first: no app, no account [I2], best used with a helper, an extension worker or co-operative
member.

1. **A co-operative names its fields:** corners, crops and dates, and whether each can be watered: what our placeholder
   lacks.
2. **We prepare each field** on a laptop; the site itself never computes.
3. **The helper sits with the farmer:** Field Pulse first ("is this when your field turns green?"), then the Replay
   ("were these your bad years?"), then the plans and the "check locally" tab. The answers become our first ground
   truth.
4. **A Safe Trial on one quarter,** if the farmer wants one. The result comes after harvest.

Every plan says "try it on one small part first" [E2]. The tool supports the farmer's judgment; it never replaces it.

## Numbers safe for the 30-second video

See `docs/VIDEO_SCRIPT.md`; every number there is in `docs/PITCH_FACTS.md`. Do not say: any probe accuracy, any El Niño
number, "works offline" (not yet), "2 of 2 floods" as a blind test, or a single "percent verified" (PITCH_FACTS
section K).

## Three small checks on the plans (added 14 November, evening)

Behind the "How do we know?" buttons, three checks answer the farmer's question with past years and published limits,
each with its two labels and a "Why?" that names the source:

- **Rain at harvest.** In how many of the last 24 years did a day of heavy rain (50 mm or more, the Nepal weather
  office's class) fall in each crop's harvest weeks? Rice: 8 of 24 (5 to 8 with our other rain records). The winter
  crops: none [N1, N2].
- **Heat and cold at key times.** Days above 34 °C while wheat grains fill and 35 °C or more for potato (FAO's limits):
  none in 24 years, and still rare in 23 climate models around 2040. Cold nights of 1 °C or less in the potato season:
  17 of 24 years, which our night temperatures likely overcount; most models show fewer by 2040 than in their own past
  [N3-N5].
- **Fertiliser saver.** Rice after lentil may need about 1 to 2 fewer bags of urea per hectare, from a published range
  that is wide and uncertain; the plan says to ask the local agriculture office first, and mentions dhaincha in the NARC
  booklet's own words [N6].
