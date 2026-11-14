# How Khet Sathi works

For answering judges' questions. Numbers as of 14 November 2026; refresh them from "Numbers used" at the end.

**In one breath.** We download public data around one field, run a small model of it (the "twin") through every day
from 2001 to 2025, try 165 crop plans in it, and export small JSON files that a phone website reads.

## The data

- **Rain:** NASA GPM IMERG V07, daily, about 10 km. Around this field its rain gauges stopped reporting in January 2017,
  so each month from 2017 is scaled back to GPM's own 2001-2016 level (VALIDATION 3.9b). A drier case, scaled to Nepal's
  weather office (DHM) normals, is shown beside it.
- **Temperature, humidity, wind, sunshine:** NASA POWER (about 55 km, model-based), temperatures corrected to Kathmandu
  Airport; on held-out years the night error fell from 2.31 to 1.22 °C (3.11).
- **Greenness:** HLS (Landsat and Sentinel-2, 30 m): seasons, bare days, a crop guess, the field's four parts.
- **Also:** soil from ISRIC SoilGrids (a cell 859 m away), height from NASADEM, regional stored water from GRACE/GRACE-FO
  (about 300 km), climate to 2040 from NEX-GDDP-CMIP6 (23 models, two futures).
- **Checks only:** SMAP, GLDAS, ECOSTRESS, MODIS, CHIRPS, IMERG Late, GPCC, DHM's gauges, FAOSTAT.

## The twin

FAO-56: daily reference evaporation, crop water use, a root-zone water "bucket", runoff, bare-soil evaporation. FAO-33:
harvest as a share of what the field could grow, from how short of water the crop was. Each year runs on rain alone and
with water whenever needed (100 by construction). It counts thirst only: no flood damage, pests, nutrients or frost.

## The plans

165 rotations from six crops, each replayed over 24 complete years (2002-2025) and scored 0-100 on harvest, water,
ground cover and soil kept. Every suggestion keeps rice in the monsoon. Shown: today's plan (rice, then potato: harvest
67), "Fill the empty months" (rice, then wheat: 86), "Feed your soil" (rice, then lentil: 78).

## The checks

`VALIDATION.md` has six layers, from "the code runs" to "people can use it". Each rule is committed before its first
run. The equations reproduce FAO-56's printed examples (3.88 mm a day in Example 18). An independent AI review
(`REVIEW_2.md`) recomputed the numbers of 13 November with its own code.

## Verified or estimate (the compliance table)

VERIFIED means an independent reference, at least 10 cases, at least 92% within tolerance.

- **VERIFIED:** each month's rain word matches DHM's Bhaktapur normal in 12 of 12 months, and the heat word in 12 of 12;
  our copy of DHM's monsoon-start dates matches its table in 24 of 24 years (a check of our copy, not of a method).
- **ESTIMATE:** monthly rain within 19% of the valley's gauges in 13 of 20 months (65%; 95% range 43-82%); valley floods
  found 2 of 2 (not blind; 1 false alarm); valley dry seasons 2 of 4 (3 false alarms in 9 flags); both suggestions beat
  today's plan in 94 of 94 model runs (one crop model: robustness, not proof); the soil words; the water, cover and soil
  scores; harvest by 2040.
- **NOT YET VERIFIABLE:** frost words, bare and growing months, sowing dates, the crop guess, each year's harvest, the
  groundwater direction, each part's wetness, the probe. Each waits for the farmer's answers, measured data or the
  bench test.

## What is a placeholder

The field: a 60 m square of mapped cropland near Bhaktapur, chosen by us, not a farmer's. Its crops, dates, water source
(unknown) and soil; the three nearby sample fields too. No farmer has checked any number. The probe has had no bench
test, so the site gives no water number from it, only "drier" or "wetter than the other parts".

## Why no backend

Judges open the site on their own phones, months later, with our laptops off. So all heavy work runs ahead of time, and
the site is plain files on Vercel: no server, no keys, no login, no AI calls. The trade-off: a new field must be
prepared on a laptop first. The one planned exception, a small database for live probe readings, is not built.

## Short answers

- **"Is the 2017 rain jump climate change?"** No. NASA's own gauge share falls from 96-98% to 56-72% a year, and CHIRPS
  shows no step (3.9b).
- **"Do the suggestions help a farmer who can water?"** Not in harvest: with water every plan scores 100.
- **"Whose field is this?"** Nobody's yet. It is a labelled sample.

## Numbers used

| Number | Source |
| --- | --- |
| 2001-2025; 24 complete years (2002-2025) | `site/data/fields/demo.json` `replay` |
| 165 plans; six crops | `data/checks/demo/plans.json` `n_plans`; VALIDATION 3.19 |
| About 10 km GPM; about 55 km POWER; 30 m HLS; about 300 km GRACE | `demo.json` `sources` |
| 2.31 to 1.22 °C | VALIDATION 3.11 |
| Four parts | `demo.json` `field.sections` |
| 859 m | `demo.json` `sources` (ISRIC SoilGrids) |
| 23 models, two futures | `demo.json` `future.models`, `future.scenarios` |
| Harvest 67 / 86 / 78 | `demo.json` `plans[].score.harvest` |
| 3.88 mm a day | VALIDATION 2.1b |
| 92%, 10 cases | VALIDATION, Compliance table header (`rules.yaml verification`) |
| 12 of 12 (rain, heat words) | Compliance table; `data/checks/demo/scorecard.json` |
| 24 of 24 (onset dates) | Compliance table; `scorecard.json` `monsoon_start` |
| 13 of 20, 65%, 43-82%, within 19% | Compliance table; `scorecard.json` `rain_months` |
| Floods 2 of 2, 1 false alarm | Compliance table; `scorecard.json` `flood_years` |
| Dry seasons 2 of 4, 3 false alarms in 9 | Compliance table; `scorecard.json` `drought_years` |
| 94 of 94 runs | Compliance table; `scorecard.json` `plan_*_beats_current` |
| 60 m square | VALIDATION 1.4 |
| 96-98%; 56-72% | VALIDATION 3.9b; `demo.json` `method.rain_correction.gauges` |
| 100 with water | `demo.json` `replay.<plan>[].irrigated`; METHOD_NOTES 38 |
