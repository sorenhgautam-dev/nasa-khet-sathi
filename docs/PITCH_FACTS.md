# Khet Sathi: the facts we may say

The only numbers the team may say or write about Khet Sathi. Each fact has an ID, a plain sentence, its number and the
file and key it came from. Other docs (`PROJECT_PAGE.md`, `HOW_IT_WORKS.md`, `VIDEO_SCRIPT.md`, `TOUGH_QUESTIONS.md`)
point to these IDs, so a refresh starts here.

**Snapshot:** 15 November 2026, afternoon. **Recounted for Kharipati**, the only field the app shows (owner, 2026-11-15:
"Make Kharipati the only field the app shows"; `config/rules.yaml` `site_hidden_fields`). Kharipati is a real farm in
Kharipati, Bhaktapur (about 27.6863 N, 85.4636 E). Its outline comes from an open drone map; its crops are still
placeholders, and no farmer's answers have arrived yet. The earlier Bhaktapur demo square (27.6908 N, 85.4418 E) and the
four sample fields are hidden from the app; their files are kept. The demo square appears below only as the earlier
placeholder whose 5 km data box Kharipati shares, or where a fact exists for it alone ("demo field only (hidden)").

**Rules.**
- Say a number only if it is here. If it is not here, leave it out.
- Keep every range. A number with a range is said with its range, or with "about" and the range on screen.
- No prices, no money, no yield in tonnes. Harvest is "out of 100" of what the field could grow.
- Never say the tool replaces an agronomist. Say: "It supports the farmer's own judgment. You know your land best."
- Kharipati is a real farm, but its crops, dates and water source are placeholders, and no farmer has checked any
  number. Say so.
- A fact marked "demo field only (hidden)" is not said about Kharipati.
- Credit the designer only as "our UI teammate".

**Labels used below.** *How sure:* VERIFIED, ESTIMATE or NOT YET VERIFIABLE are the compliance table's words
(`data/checks/kharipati/scorecard.json`, VALIDATION "Compliance table"). BUILD means a fact about how we built it, not a
measurement. *How close:* field (Kharipati itself: its drone outline, its parts, about one 30 m HLS square), neighbourhood
(the box about 5 km each way, or a 250 m cell), valley (about 10 km), region (about 55 km or more).

**Shared numbers.** Some numbers are the same for Kharipati and the hidden demo square, because both sit in the same data:
- *Same 5 km box:* the area map (A1-A4, A6-A8). Kharipati lies inside the box first fetched around the demo square.
- *Same NASA rain square and weather cell:* both points lie in latitude 27.6-27.7 N and longitude 85.4-85.5 E, one IMERG
  0.1° cell, and in one POWER cell. Checked on the daily inputs: NASA's rain as published and POWER's temperatures are
  identical, day for day, 2001-2025. So the rain check and its correction (F1-F7, F12, F13), DHM's gauge checks, the
  monsoon onset (C7), the month words, flood and dry years (C2), Weather ahead (O) and the climate outlook's cell (H11)
  apply to Kharipati because it sits in the same rain square. One difference: the demo square's rain also carried a
  gauge tuning (F8); Kharipati's does not (`config/rules.yaml` `gpm_series.gauge_calibration.fields`: demo only).
- *Field-specific:* the outline and 9 parts (E1), the drone photo, HLS greenness and seasons (D2, D4, D5, A5), the soil
  cell (B6), and everything the twin computes on them: the replay, the plans and their scores (B2-B3, C1, C3-C6, H, M1,
  M2, M5, N, J4).

Abbreviations: `F` = `site/data/fields/kharipati.json`; `story` = `site/data/story.json` (built for Kharipati); `area` =
`site/data/area/kharipati.json`; `checks/` = `data/checks/kharipati/`.

## A. The hook: empty farmland around Bhaktapur, seen from space

**Say it like this:** "Seen from space, about 15 in every 100 farm squares around Bhaktapur lie bare for more than two
months a year. It could be none, or nearly a third. Only about 4 in 10 grow two crops a year."
On screen: *15% of the cropland bare over 60 days a year (range 0-31%) · NASA HLS, 30 m, 2014-2025.*

| ID | Say it like this | Number | Source (file: key) | How sure · how close |
| --- | --- | --- | --- | --- |
| A1 | Cropland in the map around the field | 4,307.9 ha ("about 4,300 hectares"); 47,866 squares of 30 m; 43% of the box | `checks/area_map.json`: `cropland.area_ha`, `cropland.pixels`, `cropland.share_of_box`; `story` `charts[area_map].caption` | BUILD (ESA WorldCover 2021 cropland) · neighbourhood. Shared: the same 5 km box as the demo square |
| A2 | Share of that cropland bare more than 60 days a year | **15.3% (range 0 to 31.3%)**; single years 10.1% (2021) to 24.6% (2018) | `checks/area_map.json`: `numbers.share_long_bare` (`value`, `low`, `high`, `single_years`); `area` `numbers[share_long_bare]` (the site rounds it to "2 in 10 fields; could be 0 to 3 in 10") | ESTIMATE (no report-card row of its own; bare days are graded "low": the bare line is not tuned, VALIDATION report card) · neighbourhood. Shared box |
| A3 | A typical farm square is bare about a week a year | 7 days (range 0 to 30); median of all squares | `checks/area_map.json`: `numbers.median_bare_days` (6.583; 0.083 to 30.333); `area` `numbers[median_bare_days]` | ESTIMATE · neighbourhood. Shared box |
| A4 | Share with two crop seasons a year | **37% (range 19 to 47.5%)**; one season: 62.7% (no range computed) | `checks/area_map.json`: `numbers.share_two_seasons`; `class_shares_seasons["1"]` | ESTIMATE ("space sees green, not which crop") · neighbourhood. Shared box |
| A5 | Kharipati's own bare days | about 23 bare days a year (23 to 23); the area page says "Like most fields nearby" | `area` `numbers[this_field_bare_days]`; `checks/area_map.json` `field_check.b_bare_days` (22.7) | ESTIMATE · field |
| A6 | What the map is made from | NASA HLS (Landsat 8/9 and Sentinel-2), 30 m, 2014-2025, 1,471 images; ESA WorldCover 2021 for "cropland" | `area` `sources`; `checks/area_map.json` `hls.granules`, `hls.years` | BUILD. Shared box |
| A7 | Why there is a range | the bare line moved from NDVI 0.20 to 0.30, and WorldCover's published accuracy, worst case | `area` `method.en` | BUILD |
| A8 | The map's code reproduces the field's own diary exactly | PASS, all three parts (Kharipati's diary) | `checks/area_map.json` `field_check` | BUILD (a code check, not accuracy) |
| A9 | The whole area map takes about two minutes to build on a laptop | 119 s | `checks/area_map.json` `runtime_s` | BUILD |

**Honest frame for the hook.** Most farm squares are green most of the year (A3), but most show only one crop season
(A4). So the "empty months" are often green with weeds or grass, not bare. The bare share (A2) is the part a farmer could
fill without ploughing up anything growing. Kharipati, bare about 23 days a year (A5), is barer than the median square
(7 days) but far below the 60-day line of A2.

## B. What Khet Sathi is

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| B1 | One farmer question | "What can I grow in my field's empty months without risking the harvest I depend on?" | The owner's brief (14 Nov) | BUILD |
| B2 | Crop plans tested for one field | 165 plans, 81 of them with rice in the monsoon; 3 shown | `checks/plans.json`: `n_plans`, `picks.eligible` | BUILD |
| B3 | Years replayed | every season of 2002-2025: 24 complete years (record 2001-2025) | `F` `replay.<plan>` (24 entries each) | BUILD |
| B4 | The field: Kharipati | a real farm in Kharipati, Bhaktapur; its outline and parts from an open drone map (OpenAerialMap, 5 May 2026). Its crops (rice, then potato by default; our guess from space: rice, then wheat), dates and water source (unknown) are placeholders; no farmer's answers yet | `F` `field.name` ("Real farm in Kharipati, Bhaktapur (PLACEHOLDER crops)"), `field.water_source`, `current_options` | BUILD |
| B5 | Fields in the app | 1 for farmers: Kharipati. The demo square and the 4 nearby sample fields are hidden, their files kept; the Madagascar field stays on the world page | `config/rules.yaml` `site_hidden_fields`; `site/data/index.json` | BUILD |
| B6 | Soil comes from a map cell | Kharipati's SoilGrids cell holds 156 mm for plants in the top metre; the 104 cells within 2 km hold 146 to 180 mm | `F` `sources[ISRIC SoilGrids].product` | ESTIMATE · neighbourhood (250 m cell) |

## C. Feature 1: the 25-Year Replay

The feature's name says 25 years. When you give a number, say **24 complete years (2002-2025)**.

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| C1 | Each plan runs through every past season | 24 years, one square each | `F` `replay.current`, `replay.cover_gap`, `replay.safest` | each square: ESTIMATE (scorecard `harvest_years`: 6 of 14 good or bad years match Bhaktapur's district yields; the farmer's own years still needed). Say "every square is an estimate" |
| C2 | The weather of each year | 3 flood years (2002, 2004, 2024), 6 dry years (2006, 2009, 2013, 2015, 2023, 2025), 15 ordinary | `F` `replay.current[].event` | flood years: ESTIMATE (2 of 2 valley floods found, not blind); dry years: ESTIMATE (2 of 4 valley dry seasons found) (scorecard `flood_years`, `drought_years`) · valley: the same rain square as the demo square |
| C3 | In dry years, "Fill the empty months" does best of the three | highest rain-fed harvest in all 6 dry years (and in all 24 years) | counted from `F` `replay.<plan>[].harvest` and `.event` | ESTIMATE (one crop model) |
| C4 | Today's plan in its worst years | 61 out of 100 (2009, 2016, 2023); "Fill the empty months" at worst 76 (2009); "Feed your soil" at worst 69 (2010, 2013) | `F` `replay.current[]`, `replay.cover_gap[]`, `replay.safest[]` | ESTIMATE |
| C5 | If you can water, every plan reaches 100 every year | 100, 0 dry days, by construction (water never runs out) | `F` `replay.<plan>[].irrigated`; METHOD_NOTES 38 | BUILD (by construction, not a finding) |
| C6 | The replay starts from the soil's water today | the model's wetness 96 (out of 100) on 3 Nov 2026, each of the 9 parts "how sure" 0.29 | `F` `field.sections[].wetness`, `.sure`, `field.status_date` | NOT YET VERIFIABLE (scorecard `part_soil_water`) · field |
| C7 | When the rains usually come | 10-16 June (middle half of years, DHM 2001-2024); after 20 June in 1 of 24 years (2009); no clear shift: -2.2 days (-11.5 to +7.7) | `F` `diary.monsoon_start`, `diary.shift_days`, `shift_days_low`, `shift_days_high` | our copy of DHM's dates: VERIFIED 24 of 24 (a copy check; scorecard `monsoon_start`, `monsoon_shift`) · region (eastern Nepal; Kathmandu a few days later). Shared: DHM's national record |
| C8 | El Niño / La Niña years are highlighted (NOAA ONI) | **no number yet**: no ONI file in the outputs | - | say only what it does; see section L |

## D. Feature 2: Field Pulse (खेतको नाडी)

| ID | Say it like this | Number | Source (file: key) | How sure · how close |
| --- | --- | --- | --- | --- |
| D1 | The field's greenness from space | HLS 30 m from 2013 (field scale: Kharipati is about one 30 m square); MODIS 250 m for 2001-2013 (neighbourhood scale; no number shown uses it) | `F` `sources` (HLS, MODIS rows) | BUILD |
| D2 | Two green seasons a year | 23 seasons in 12 HLS years (2014-2025): 11 of 12 years had two | `story` `charts[seasons_from_space]` (caption and rows) | ESTIMATE; it cannot tell which crop · field |
| D3 | MODIS and HLS agree | demo field only (hidden): r 0.83 over 671 pairs (VALIDATION 3.10). Not run for Kharipati | VALIDATION 3.10 | do not say for Kharipati |
| D4 | Three ways to find the seasons; we kept the simplest | held-out years 2022-2025: threshold 0.958, change-point 0.896, machine learning 0.933; the simple threshold method scored best | `F` `method.season_detection` (`held_out_years`, `methods[].score`, `chosen`) | BUILD (robustness, not accuracy: no ground truth) |
| D5 | The month we are least sure of | June: the two methods agree on 81% of days | `F` `diary.months[Jun].cover_sure` (0.81) | BUILD |
| D6 | The farmer's own planting and harvest dates are saved only on the phone | - | the feature's design | BUILD |
| D7 | Nearby fields shown as totals | the area-map numbers A2-A4 | section A | as A |

## E. Feature 3: Safe Trial

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| E1 | The field is already split into 9 parts | 9 parts drawn from the drone photo's patches, 96 to 141 m2 each (about 1,084 m2 in all); today each part's greenness is "unknown" | `site/data/drone/kharipati.json` `patches[].area_m2`; `F` `field.sections[].greener` | BUILD · field |
| E2 | Every plan already says to try it small | "Try it on one small part first. You know your land best." | `F` `plans[].tabs.check` | BUILD |
| E3 | The probe has not had its bench test | no water number from the probe until the cup test passes | VALIDATION 5.1-5.3 ("WAITING FOR THE BENCH TEST"); `story` `report_card[probe]` | NOT YET VERIFIABLE (scorecard `probe_water`) |
| E4 | Results come after the season | no trial result exists yet | - | say "after harvest" |

## F. Feature 4: Data Check-up (how we checked the field's rain record)

Word it as a check, not a fault: "NASA's rain combines satellites with ground gauges; from 2017 far fewer gauges near
our valley fed into it, so the record stepped up, and we corrected for it."

**Shared: the whole rain check is about the valley's rain square.** Kharipati and the demo square sit in the same IMERG
0.1° cell, so NASA's rain as published is the same for both, day for day. F1-F7, F12 and F13 apply to Kharipati for
that reason. F8 and F9 are about a gauge tuning that only the demo square used. F10, F11 and F14 are Kharipati's own.

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| F1 | How much the gauges shaped NASA's rain here | 96-98% in every month of 2001-2016; yearly means 56-72% from 2017 | VALIDATION 3.9b; `F` `method.rain_correction.gauges`; `story` `charts[gauge_weight].caption` ("about 97%", "about 65%") | BUILD (read from NASA's own product, GPM_3IMERGM) · valley, shared cell |
| F2 | Gauges reporting in the field's 1-degree box (GPCC) | about 50 a month in 2011-2016; about 1 in 2017-2020; neighbouring boxes fell the same way | VALIDATION 3.9b; `F` `method.rain_correction.gauges.stations_before`, `stations_after` | BUILD · region |
| F3 | NASA's yearly rain at the field stepped up | 1,842 mm (2001-2016) to 2,731 mm (2017-2025), +48%; change-point after 2016, p 0.0014 | `F` `method.rain_correction.rain_mm_per_year`; `story` `charts[rain_jump].caption`; `checks/rain_check_b.json` `pettitt.gpm_yearly_mm` | BUILD · valley, shared cell |
| F4 | CHIRPS shows no step | 1,454 mm then 1,437 mm a year; p 0.24 | VALIDATION 3.9b; `checks/rain_check_b.json` `chirps.pettitt_chirps_yearly`, `chirps.step_chirps` (0.989) | BUILD · valley |
| F5 | IMERG Late, without monthly gauges, barely steps | Late steps 1.13, Final 1.62 (2017-2019 over 2014-2016) | `checks/rain_check_b.json` `late_check.step_late`, `step_final` | BUILD · valley, shared cell |
| F6 | GLDAS's own rain shows no 2017 step and follows our corrected rain | r 0.70, against 0.40 for NASA's rain as published | VALIDATION 4.2d (run at the shared cell) | BUILD (context, not a fixed test) |
| F7 | Our correction, tested on years it did not see | each month from 2017 scaled back to 2001-2016; monthly error at the airport 93.7 to 31.4 mm (48 months) | `F` `method.rain_correction.held_out` | ESTIMATE (the held-out set also chose the method, VALIDATION 3.9b) · valley, shared cell |
| F8 | Demo field only (hidden): then matched to four of Nepal's rain gauges | outside the monsoon about 25% less (x 0.746), in it about 5% more (x 1.053). **Kharipati's rain is not tuned**: its model uses the corrected rain of F7 | `config/rules.yaml` `gpm_series.gauge_calibration.factors`, `.fields` (demo only) | do not say for Kharipati |
| F9 | Demo field only (hidden): that tuned version won, narrowly | 40 of 83 gauge-months within 19%, against 38 of 83 for the corrected rain (within the noise); on the locked 2026 months every version scored 3 of 15 | VALIDATION 3.9e | do not say for Kharipati |
| F10 | The rain Kharipati's model uses | 1,853 mm a year, 1.35 times Bhaktapur's usual 1,375 mm (NASA's as published: 2,162 mm) | `story` `charts[rain_fixed].rows` | ESTIMATE · valley (about 10 km cell) |
| F11 | Kharipati's rain checked against Nepal's gauges | 13 of 20 months within 19% (65%; 43-82%), on Kharipati's own corrected rain | `checks/scorecard.json` `rain_months` (its month values equal Kharipati's model rain, e.g. June 2023: 162.2 mm) | ESTIMATE (the row is marked not independent) · valley |
| F12 | 2025 against DHM's own gauges | the corrected rain read 0.88 times the gauges in three IMERG Final months; NASA's as published 1.27; the last three months (IMERG Late) still 1.64 | VALIDATION 3.9c; `story` `charts[dhm_2025].rows` (from `checks/rain_vs_dhm_2025.json`) | ESTIMATE · valley, shared cell |
| F13 | Every field runs its own rain check | Kharipati's found the 2017 change (as did the 5 hidden Bhaktapur fields); a test field in Madagascar found none and kept NASA's rain as published | `checks/break_test.json` `found` (true, 2017); VALIDATION 3.24 | BUILD |
| F14 | Numbers that depend on rain are flagged and shown as a range | e.g. today's plan 69 (65-69), "Fill the empty months" 87 (83-87) over the rain versions | `F` `plans[].score`, `score_dhm_rain` | ESTIMATE |

## G. The two labels on every number

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| G1 | What "Verified" means | an independent reference, at least 10 cases, at least 92% within tolerance; set before any score | VALIDATION compliance header (`rules.yaml verification`, `fee6817`); `story` `compliance_note` | BUILD |
| G2 | What is Verified today, for Kharipati | 5 rows: the rain word of each month (12 of 12), the heat word (12 of 12), the frost word (12 of 12), our copy of DHM's monsoon dates (24 of 24) and of DHM's monsoon trend (24 of 24) | `checks/scorecard.json` `rain_month_words`, `heat_month_words`, `frost_month_words`, `monsoon_start`, `monsoon_shift` | VERIFIED. Say what they test: the shape of the year against DHM's Bhaktapur normals, and our copy of DHM's record, not a method of ours. All five are valley-wide (shared rain square and weather cell) |
| G3 | What is an estimate | rain months (13 of 20), soil words (22 of 24), floods (2 of 2), dry years (2 of 4), each suggested plan beating today's (94 of 94 runs, one crop model), good and bad years (6 of 14), our crop guess (5 of 5), bare and growing months (12 of 13), sowing and harvest dates (2 of 3), groundwater (2 of 2), 2040 (4 of 4), the scores | `checks/scorecard.json` | ESTIMATE. The crop guess, months and dates are checked against the drone photo of 5 May 2026 and area-level calendars: consistency, not this field's truth |
| G4 | What we cannot check yet, and what would check it | the probe's water number; each part's wetness | `checks/scorecard.json` `probe_water`, `part_soil_water` (`needs`) | NOT YET VERIFIABLE |
| G5 | How close each source is | HLS 30 m; NASADEM 30 m; SoilGrids 250 m; MODIS 250 m; SMAP L4 9 km; GPM about 10 km; Kathmandu Airport station 10 km west; NEX-GDDP 0.25 deg; POWER about 55 km; GRACE about 300 km | `F` `sources[].resolution` | BUILD |

## H. The plans (rain-fed, mean of 2002-2025, central rain)

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| H1 | Today's plan (rice, then potato) | harvest 69 out of 100 (65-69 over rain versions) | `F` `plans[current].score.harvest`, `score_dhm_rain` | ESTIMATE (report card: harvest numbers "low") |
| H2 | "Fill the empty months" (rice, then wheat) | 87 (83-87); about 9 to 23 more than today, over FAO's root depths | `F` `plans[cover_gap].score`; `checks/plans.json` `export.cover_gap.gain_range` (8.53 to 23.26) | ESTIMATE |
| H3 | "Feed your soil" (rice, then lentil) | 78 (74-78); about 5 to 14 more | `F` `plans[safest].score`; `checks/plans.json` `export.safest.gain_range` (5.13 to 14.47) | ESTIMATE |
| H4 | Bad years (the 10th-percentile year) | today 61.5, "Fill the empty months" 77.7, "Feed your soil" 70.5 | `checks/plans.json` `export.<plan>.stability` | ESTIMATE |
| H5 | Water, ground cover, soil kept (0-100, higher is better) | water 54 / 62 / 58; cover 62 / 68 / 67; soil kept 74 / 75 / 74 | `F` `plans[].score` | ESTIMATE (model indices, nothing measured) |
| H6 | "Fill the empty months" covers the ground longer | 25 more days a year than today | `F` `plans[cover_gap].tabs.why` | ESTIMATE |
| H7 | The picks hold when inputs change | same three plans with 2002-2016 only and with crop sensitivity 0.8 and 1.2 | `checks/plans.json` `robustness` (`current`, `cover_gap`, `safest` in each) | ESTIMATE (the size of the gain does not hold: H2, H3) |
| H8 | The gain is only for a farmer who cannot water | with water every plan scores 100 | C5 | BUILD |
| H9 | Demo field only (hidden): rice's water losses counted, and no independent check got worse | SMAP 0.676 to 0.684; GLDAS soil 0.333 to 0.334, ET 0.391 to 0.390; FAOSTAT wheat 0.539 to 0.552. The losses are counted for Kharipati too; this before-and-after test was run on the demo square only | `data/checks/demo/paddy_losses/keep_test.json`; VALIDATION 4.8 | do not say the numbers for Kharipati |
| H10 | The model's rain-fed rice never fails | Kharipati's lowest rice year 91.9% (2010); the sourced monsoon droughts 2009 and 2015: 93.3% and 97.0% | `checks/replay.json` `rain-fed.seasons` (rice `harvest_pct`) | a known limit (see NEXT_STEPS, the rice pond) |
| H12 | The suggestions may pick the best of three sowing dates; today's plan sits at the middle of its window. Given the same choice, today's crops would score 71.1 | today's plan 68.6; best rice-then-potato sowing 71.1 (rice mid-window, potato at the window's start); "Fill the empty months" 86.5 | `checks/plans.json` `plans[id = rice.w1.middle+potato.w0.start].harvest`, `export.current.score.harvest`, `export.cover_gap.score.harvest`; METHOD_NOTES 37 | ESTIMATE |
| H11 | By 2040 the plans stay about where they are | today's plan 69 to 68 (60-75); "Fill the empty months" 87 to 86 (78-91); "Feed your soil" 78 to 77 (70-83); each range spans every climate model and every rain version; 23 climate models, two futures | `F` `future`; `story` `charts[outlook_2040].rows` | ESTIMATE (report card "low") · region (the climate models' 0.25° cell, shared) |

## I. Free, static, any field

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| I1 | No backend: plain files on GitHub Pages, no login, no keys, no AI calls from the site | - | CLAUDE.md "Hosting"; `scripts/check_site.py` | BUILD |
| I2 | Free to open: a web link, no app, no account | - | CLAUDE.md "Hosting" | BUILD (never say a money figure) |
| I3 | One command downloads, one builds | `scripts/fetch_field.py`; `scripts/run_field.py --field <id>` | `scripts/run_field.py` docstring | BUILD |
| I4 | Built from global data | every input of the twin is a global dataset; the rain check ran unchanged in Madagascar | VALIDATION 3.24; `F` `sources` | BUILD. Say "made for any field on Earth", not "proven anywhere": the Madagascar field's answers for the coming months are not made yet |
| I5 | Nepali first | 32 of 915 Nepali texts checked by a person so far; drafts in 5 more languages, unreviewed | `story` `charts[ai_words].rows` | BUILD |
| I6 | Works offline once loaded | **not yet**: `site/` has no service worker, and the map tiles come from OpenStreetMap | see section L | do not say yet |

## J. How we checked our own work

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| J1 | Tests in the repository | 1,494 tests collected (93 files), 14 Nov 2026 afternoon | `.venv/bin/python -m pytest -q -p no:cacheprovider --collect-only -q`, summed | BUILD. Collected, not a pass count: say "passing" only after a full run |
| J2 | The equations reproduce FAO-56's printed examples | e.g. Example 18: 3.88 mm a day | VALIDATION 2.1b-2.1d, 2.5 | BUILD (independent) |
| J3 | Temperature corrected to Kathmandu Airport, tested on years it did not see | night error 2.31 to 1.22 C | VALIDATION 3.11 | ESTIMATE (independent in time only) · valley: the same POWER cell and station, so Kharipati's temperatures are the same, day for day |
| J4 | A learned "field memory" lost to physics, so we dropped it | error 0.0357, against 0.0330 for physics alone and 0.0304 for "no change" | `checks/field_memory.json` `result.rmse` | BUILD |
| J5 | The model moves with other NASA data, some well, some weakly | SMAP r 0.69; GLDAS soil 0.37, water use 0.39; Nepal's wheat yields 0.56 (holds up); potato -0.18 and rice 0.30 (do not); greenness: wheat 0.83, potato 0.54, rice 0.09 (wide ranges) | `story` `charts[other_checks].rows` | ESTIMATE |
| J6 | Each rule is committed before its first run; two model changes were tried, then undone and recorded | satellite planting dates (they made the independent checks weaker); rice waiting for rain (it caught neither the 2009 nor the 2015 monsoon drought) | VALIDATION header; VALIDATION 4.9; `config/rules.yaml` `season_dates.apply` | BUILD |
| J7 | Ten NASA data sources, each with a job and a check | GPM IMERG, POWER, HLS, MODIS, SMAP, GRACE/GRACE-FO, NASADEM, ECOSTRESS, GLDAS, NEX-GDDP-CMIP6 | `docs/PROJECT_PAGE.md` "Data"; DATA_AUDIT section 7 | BUILD |

## M. The case study: a flood, then a winter without rain (used in PROJECT_PAGE)

| ID | Say it like this | Number | Source (file: key) | How sure |
| --- | --- | --- | --- | --- |
| M1 | 2024, a flood year, rain-fed: harvest (dry days) | today 68 (108), "Fill the empty months" 89 (58), "Feed your soil" 79 (93) | `F` `replay.<plan>[year 2024]` | ESTIMATE |
| M2 | 2025, a dry year, rain-fed | 65 (92), 87 (54), 76 (84) | `F` `replay.<plan>[year 2025]` | ESTIMATE |
| M3 | The storm of 28 September 2024, as DHM measured it | 194.5 mm at Nangkhel, Bhaktapur; 239.7 mm at Kathmandu Airport, in 24 hours | VALIDATION 4.1; `config/known_events.yaml` `kathmandu_floods_2024_09` | DHM's record · valley |
| M4 | The dry winter, as DHM measured it | Bhaktapur 0.0 mm, December 2024 to February 2025 (normal 47.8 mm) | `config/known_events.yaml` `winter_drought_2024_25` | DHM's record · valley |
| M5 | Today's potato in that winter, in the model | 30 Oct 2024 to 21 Feb 2025: 18.9 mm of rain, about a third of the water it needed (0.37), harvest 30 out of 100 | `checks/replay.json` `rain-fed.seasons` (potato from 2024-10-30: `rain_mm`, `eta_over_etc`, `harvest_pct`) | ESTIMATE |
| M6 | Root depths in the model | wheat 1.5 m, lentil 0.8 m, potato 0.6 m, rice 1.0 m (the larger end of FAO-56 Table 22) | METHOD_NOTES 35 | BUILD |
| M7 | What it got wrong | the 2025 flag also covers the 2025 monsoon, which DHM had at 117% of normal; the valley's dry winter of 2023/24 was missed (2024 shows the September flood) | VALIDATION 4.1; scorecard `drought_years` | ESTIMATE · valley |
| M8 | The probe's software | an ESP32 probe with two sensors; the Kalman update passes 20 hand-worked tests | VALIDATION 5.4; `robot/firmware/original_probe/` | BUILD (no bench test yet, E3) |

## K. Claims we dropped (the outputs do not support them)

- "Works offline": no service worker in `site/`, and the map needs OpenStreetMap tiles (I6). Say it only after the
  offline feature lands and is tested on a phone in flight mode.
- "Proven for any field on Earth": the inputs are global, but the Madagascar field's answers for the coming months are
  not made yet (I4).
- Any El Niño or La Niña number, or "El Niño years were worse here": no ONI data in the outputs, and no test of whether
  ONI matters for this field (C8).
- Counts of "worked / struggled / failed" squares: the feature is not in the outputs yet.
- How many hectares sit bare: that would be our own arithmetic on A1 and A2, not an output.
- "0.88 times the gauges" for any tuned rain: 0.88 is the corrected rain (F12).
- "Kharipati's rain was tuned to four gauges": only the hidden demo square's was (F8).
- Any demo-square number said about Kharipati: the demo's 65 / 83 / 74, its 62 bare days, its 4 parts, its soil cell
  859 m away, its 1,833 mm. Kharipati's are in this file.
- "1,461 tests passing": old. Today: 1,494 collected, not run by us (J1).
- Any probe accuracy, any trial result, any farmer's verdict: none exist yet (E3, E4).
- A single "percent verified" for the whole app (G2-G4: report the three classes).
- "Three independent records agree" on the monsoon: removed from the site; the records share gauges (`F` `method.onset`).
- Groundwater lowering the water score: no longer true; GRACE is context only now (`config/rules.yaml`
  `plans.water_strict_when_falling` 1.0).

## L. To refresh after the four features land

- C1-C8: the Replay's square words (worked, struggled, failed), the next 3 and 6 months tabs, the starting soil state
  (dry, medium or wet), and any ONI highlight.
- D6, D7: Field Pulse wording, and whether it shows MODIS.
- E1-E4: Safe Trial: which part, which probe spots, what is saved on the phone.
- G5: the "how close" word each source gets in the app.
- H1-H11 and F10-F14: rerun numbers, if the integrator reruns the pipeline.
- I6: offline, once a service worker exists.
- J1: rerun the test count.

## N. Three small checks behind "How do we know?" (added 14 November, evening; rules committed before the first run)

Files: `rr` = `site/data/rainrisk/kharipati.json`, `hc` = `site/data/heatclock/kharipati.json`, `fs` =
`site/data/fertiliser/kharipati.json`. All three are labelled ESTIMATE (no yardstick row yet); rain is "valley" (the
shared rain square), today's temperatures "valley" (the shared weather cell and station), 2040 "region", the fertiliser
range "region" (a published range from elsewhere). Recounted for Kharipati: only N7 differs from the demo square.

| ID | Say | Number | From |
| --- | --- | --- | --- |
| N1 | Heavy rain (50 mm or more in a day, DHM's class) fell in the rice harvest weeks in 8 of 24 years. | 8 of 24 (other rain records: 5 to 8) | `rr` `plans[current].crops[rice].count`, `count_low`, `count_high` |
| N2 | The winter crops' harvest weeks had no heavy-rain day in 24 years: good news. | 0 of 24 (potato, wheat, lentil) | `rr` `plans[*].crops[*].count` |
| N3 | No day above 34 °C while wheat grains fill, and none of 35 °C or more for potato, in 24 years; still none in the climate models around 2040. | 0 of 24; model medians 0.0 days a season | `hc` `checks[wheat_*_heat, potato_1030_heat]` |
| N4 | Cold nights (1 °C or less) fell in the potato season in 17 of 24 years, about 3 a season; our night temperatures count too many. | 17 of 24; 3.0 a season | `hc` `checks[potato_1030_cold].today` |
| N5 | In 22 of 23 climate models, the potato season has fewer such cold nights in 2026-2040 than in the same model's 1995-2014 (middle model: 28 down to about 20). | 22 of 23 (ssp245); medians 28.0 and 19.5 (ssp245), 20.2 (ssp585); lowest to highest 7.3 to 38.5 | `hc` `checks[potato_1030_cold].future.scenarios` |
| N6 | After lentil, rice may need about 1 to 2 fewer 50 kg bags of urea per hectare; a wide, uncertain range from a thesis citing Quinn (2009), and one field study measured far less (2.3 kg N/ha). | 49-97 kg urea, 1.0-1.9 bags per hectare | `fs` `urea_kg_ha`, `bags_ha` |
| N7 | After sowing, the longest run of dry days (under 1 mm, the weather office's measure) is usually 5 to 6 weeks for potato; the worst winters reached about 8-10 weeks. | potato 38 days typical (38-39 over the rain records); worst 2023 68, 2011 60, 2016 59 | `rr` `plans[current].crops[potato].dry_run` |
| N8 | Frost (below 0 °C) around wheat flowering, for wheat sown 15 October: 5 of 24 years; none for wheat sown 15 November. Estimate: FAO's wheat book, our night temperatures. | 5 of 24 (2008, 2011, 2013, 2020, 2022); 0 of 24 | `hc` `checks[wheat_1015_flowering_cold, wheat_1115_flowering_cold].today` |
| N9 | No day above 30 °C while wheat forms its florets, in 24 years. | 0 of 24 (both sowings) | `hc` `checks[wheat_*_floret_formation_heat].today` |

## O. Weather ahead (added 14 November, evening; rules committed `8ade382` before the first run)

File: `w` = `site/data/fields/kharipati.json` `weather`. ESTIMATE; "what usually happened here", never a forecast.
Valley-wide: Kharipati's weather comes from the shared rain square and weather cell.

| ID | Say | Number | From |
| --- | --- | --- | --- |
| O1 | For each of the next six Nepali months, the app says what usually happens, the one biggest danger and one tip, from 24 years of this field's records. Not a forecast. | 12 blocks, 24 years each | `w` `blocks` |
| O2 | In Poush, cold nights (1 °C or less) reached potato in most years. | 15 of 24 | `w` `blocks[Dec].dangers[0]` |
| O3 | Our month words match the weather office's normal rain for Bhaktapur in every month. | 12 of 12 calendar months (scorecard `rain_month_words`, Kharipati) | `checks/scorecard.json`; VALIDATION 4.10 |
| O4 | Demo field only (hidden): big rain (20 mm or more) was on 5 of 6 known flood dates. Not recounted for Kharipati, whose rain is untuned | 5 of 6 (demo square) | VALIDATION 4.10 |

**Do not say:** an 8-day dry spell (no DHM source), that Weather ahead forecasts anything (it is past years), "heavy rain" for 20 mm (DHM's heavy starts at 50 mm), wheat flowering damage at 8-35 °C (FAO's rice text), any saving per
ropani (no opened source), that dhaincha suits this field (only "ask your agriculture office"), or that cold nights will
fall by a given number (the models are not corrected to the station; say "fewer in most models, compared with their own
past").
