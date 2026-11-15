# How we know

This is the app's **"How we know"** page as a file, for judges and for anyone who wants to check our work. It is built
from the same files the website reads (`site/data/`), so its numbers match the site. In the app: open
**LIVE_ADDRESS_PENDING**, tap **"For judges: how we know"** at the bottom of Home, and
start with **"Our numbers, explained"**.

The field shown is **Kharipati**, a real farm in Bhaktapur, Nepal. Its crops, dates and water source are
**placeholders** until its farmer answers. No farmer has checked any number yet.

## How to read our numbers

- Harvest is a share of this field's best. Not a weight.
- A range shows how sure we are.
- Fog or grey means not sure yet.
- Every number names its source and years.
- No made-up numbers. Missing ones say so.

## What this tool can and cannot tell you

- It shows a real farm and sample fields.
- No farmer has answered our questions yet.
- Our advice is only a starting point.
- Check with your local agriculture office.

**Checked against real records:** Rainy and dry months; Warm and cool months; Frost months; When the monsoon starts; Has the monsoon start shifted?

**Estimates, not checked yet:** Rain on the field; Dry and wet soil months; Flood years; Dry years; 'Fill the empty months' grows more; 'Feed your soil' grows more; Good and bad harvest years; Our guess of your crops; Bare and growing months; Planting and harvest dates; Water under the ground; Harvest by 2040; Water, cover and soil scores; The soil stick's reading; How wet each part is.

## How each answer becomes verified

- Verified: checked against a record we did not use to make it. Right at least 92 times in 100, on 10 or more checks.
- Estimate: checked only against models or our own runs, or right fewer times. Shown with its range, never as a promise.
- Not yet checkable: the record that would check it does not exist yet.
- Today: 5 verified, 13 estimates, 2 not yet checkable.
- Four things will check the rest:
- The farmer's records: sowing and harvest dates, best and worst years, bare months.
- A probe walk on the real field: each part's soil water, measured.
- A season of Safe Trial: one part of the field tries a plan.
- Projections, like 2040: checked against published ranges only.

Verified means right at least 92 times in 100, on 10 or more checks. The range shows how sure that number is.

## Our report card

Each answer the app gives, how sure we are, and why. The numbers in brackets are sections of [records/checks.txt](records/checks.txt).

| Answer | How sure | Why |
| --- | --- | --- |
| When the field is green | high | Three methods find the same 23 seasons. Start dates typically differ by 14 days. It cannot tell which crop it is. The model now starts crops on these dates. So the two no longer check each other. (3.6, 3.10, 3.15, 3.18, 3.23, 4.2c) |
| Days the field lies bare | low | This field: about 23 bare days a year. Our bare line is not tuned yet. Nudged a little, nearby fields read 0-30 days. Older satellite years are not comparable. (3.10, 3.23) |
| Rain on the field | medium | From 2017, fewer gauges fed NASA's rain here. So the record stepped up. We corrected for it. We checked 6 months of 2025 against gauges. 3 months read 0.88 times the gauges. The last 3 still read too wet. Yearly rain: 1.35 times the town's usual. (3.1, 3.9, 3.9b, 3.9c, 3.9d, 4.2d) |
| Harvest numbers (out of 100) | low | These come from a computer model. Wheat years follow Nepal's yields (r 0.56). Potato years do not follow Nepal's yields. Rice years do not follow Nepal's yields. Root depth and soil change them a lot. (4.2, 4.3, 4.4, 4.4c, 3.21) |
| Which plan comes first | medium | The same plans won when we changed inputs. How much better they are is unsure. Your real crops are not known yet. (3.19, 3.21, 4.4, 4.4b) |
| Flood years | medium | It found 2 of 2 valley floods. It also flagged 1 unrecorded flood year. We knew these floods before setting the rule. (4.1, 3.9b) |
| Dry years | low | It found 2 of 4 valley dry spells. It called 2 normal or wet monsoons dry. 3 of 9 flagged seasons were not confirmed. The rain fix cannot reorder the years. (4.1, 3.9b, 3.9d) |
| Frost risk | low | We show risk by month, never counts. Our cold nights outnumber the airport's. The recorded frost night itself was missed. Bhaktapur's winter nights are colder still. (3.14, 4.1b, 4.1c, 3.11b) |
| Weather ahead (each month) | low | Rain words match DHM's normals: 12 of 12. Big rain on 6 of 6 flood dates. The dangers use our cold-night numbers. Those count too many cold nights. Past years only, not a forecast. (4.10, 3.14, 4.1c) |
| Water under the ground | medium | The region loses about 2.6 cm a year. This trend is clear. The region is about 300 km wide. It includes glaciers and snow, not your well. No well readings have checked it. (3.16) |
| When the monsoon starts | medium | Nepal's weather office: usually 10-16 June. It reaches here a few days later. No clear change since 2001. Our own satellite methods failed this check. (3.3, 4.1d, 4.1e, 4.1f, 3.22, 3.22b) |
| The soil probe | low | In cups, off by about 0.9 points. A rough test, copied by hand. Some cup checks were not possible. It reads only the top few centimetres. (5.1, 5.2, 5.3, 5.4) |
| Harvest by 2040 | low | 23 climate models, two possible futures. Their changes fit published ranges for Nepal. Only averages change; extremes stay as observed. It rests on the same harvest model. (4.7) |

## Counted from our own files

- **9,131 days of rain records.** Every day from 2001 to 2025.
- **2,047 pictures from space.** Landsat 336, Sentinel-2 1,135, MODIS 576. 1,304 were clear enough to use.
- **24 years replayed.** Every full year from 2002 to 2025.
- **23 climate models.** For 2026 to 2040, 2 possible futures.
- **7,465 crop seasons run.** 165 crop plans, each crop, each year. The main run only.
- **11 datasets.** Tap a name for its square size and years. The checks use more.

## Where our numbers come from

| Source | How it was made | Square size | Years | What it is |
| --- | --- | --- | --- | --- |
| GPM IMERG | seen from space | 0.1 deg (about 10 km) | 2001-2025 | V07 Final daily (Late for Oct-Dec 2025); days from 2017 scaled back, month by month, to its own 2001-2016 level (the rain gauges behind it stopped reporting here) |
| NASA POWER | worked out by computer | 0.5 x 0.625 deg (about 55 km) | 2001-2025 | Daily API v2.10.3 (MERRA-2 weather, CERES sunshine); temperatures corrected to Kathmandu Airport |
| Kathmandu Airport station | measured on the ground | one point, 10 km west | 2001-2025 | NOAA GHCN-Daily NP000444540 (temperature correction, checks) |
| Harmonized Landsat Sentinel-2 | seen from space | 30 m | 2013-2025 | HLS-VI v2.0 greenness (NDVI) |
| MODIS Terra | seen from space | 250 m | 2001-2013 | MOD13Q1 v061 greenness (NDVI), before HLS: the older, coarser line in Field Pulse; no plan number uses it |
| GRACE and GRACE-FO | seen from space | about 300 km | 2002-2026 | JPL mascon CRI RL06.3 v04: water stored across the region |
| ISRIC SoilGrids | worked out by computer | 250 m | one map | 2.0: water the soil holds at field capacity and wilting point (machine-learning map). Water it holds for plants in the top 1 m: 156 mm; the 104 cells within 2 km of the field hold 146 to 180 mm |
| NASADEM | seen from space | 30 m | 2000 | v001 elevation |
| NASA SMAP L4 | worked out by computer | 9 km | 2015-2025 | SPL4SMGP v008 root-zone soil moisture, model-assisted: sets only how sure the twin is before any probe reading |
| Khet Sathi field twin | worked out by computer | the field | 2001-2025 | FAO-56 soil water, FAO-33 harvest, from the data above |
| DHM (Department of Hydrology and Meteorology, Government of Nepal) | measured on the ground | one date a year for Nepal (eastern Nepal; Kathmandu a few days later) | 2001-2024 | Monsoon onset dates, entry into eastern Nepal (Monsoon Onset and Withdrawal date information, Table 1) |
| NEX-GDDP-CMIP6 | worked out by computer | 0.25 deg | 1995-2014 and 2026-2040 | daily, bias-corrected and downscaled (BCSD), v2.0 |

Exact products, versions and citations: [records/credits.txt](records/credits.txt). Every check, with its numbers: [records/checks.txt](records/checks.txt).

## Open our raw files

Every screen reads only these files. There is no server and no database behind the site.

| File | What it holds |
| --- | --- |
| [`site/data/fields/kharipati.json`](site/data/fields/kharipati.json) | This field: its parts, the three plans, the 24 past years, the 2040 outlook, the sources |
| [`site/data/behind.json`](site/data/behind.json) | The counted numbers behind the scenes |
| [`site/data/story.json`](site/data/story.json) | The charts and the report card on How we know |
| [`site/data/words.json`](site/data/words.json) | Every word on the screens, in every language |
| [`site/data/index.json`](site/data/index.json) | The list of fields |
| [`site/data/version.json`](site/data/version.json) | Which version of our code made them |

The field file must match [`pipeline/export/schema.json`](pipeline/export/schema.json).

## Languages

- **नेपाली** (Nepali): a local reader still needs to check it.
- **English** (English): written by our team.
- **हिन्दी** (Hindi): computer draft (AI); a local reader still needs to check it.
- **বাংলা** (Bengali): computer draft (AI); a local reader still needs to check it.
- **Español** (Spanish): computer draft (AI); a local reader still needs to check it.
- **Français** (French): computer draft (AI); a local reader still needs to check it.
- **Kiswahili** (Swahili): computer draft (AI); a local reader still needs to check it.

In the app, the globe button in the top bar opens this list.

## Where AI was used

AI drafted texts and translations and helped write code, at build time only. The public site never calls an AI
service. Every use, and what a person reviewed, is in [records/ai_log.txt](records/ai_log.txt) and [records/credits.txt](records/credits.txt).

## Not done yet

- **Pea and cabbage after rice** are named on the plan screens as "not tested yet". Their numbers are checked, but our
  model has not run them.
- **Fertilizer amounts.** The plan screens have a small "Fertilizer and sprays" card under "More": ask your agriculture
  office how much (it depends on your soil), the rice-after-lentil saver note (an estimate), and three spray lines with
  no product names or doses. No rate is shown: the government paper we wanted to quote could not be opened, and the
  government replaced the old one-size rice rate in 2022.
