# How Khet Sathi works

For answering judges' questions. Numbers as of 14 November 2026 (afternoon). Each number has an ID in square brackets:
its source is in `docs/PITCH_FACTS.md`. Refresh numbers there first.

**In one breath.** We download public data around one field, run a small model of it (the "twin") through every day
from 2001 to 2025, try 165 crop plans in it [B2], and export small files that a phone website reads. The site answers
one question: "What can I grow in my field's empty months without risking the harvest I depend on?" [B1]

## The data

- **Rain:** NASA GPM IMERG V07, daily, about 10 km. Our rain check found that its gauge input around this field changed
  in January 2017 [F1, F2]. So each month from 2017 is scaled back to its own 2001-2016 level [F7], then matched to four
  of Nepal's rain gauges [F8]. Two other versions are kept beside it as a range [F14].
- **Temperature, humidity, wind, sunshine:** NASA POWER (about 55 km, model-based), temperatures corrected to Kathmandu
  Airport; on held-out years the night error fell from 2.31 to 1.22 °C [J3].
- **Greenness:** HLS (Landsat and Sentinel-2, 30 m): Field Pulse, seasons, bare days, the area map, the field's four
  parts [D1, A6].
- **Also:** soil from ISRIC SoilGrids (a cell 859 m away) [B6], height from NASADEM, regional stored water from
  GRACE/GRACE-FO (about 300 km, context only), climate to 2040 from NEX-GDDP-CMIP6 (23 models, two futures) [H11].
- **Checks only:** SMAP, GLDAS, ECOSTRESS, MODIS, CHIRPS, IMERG Late, GPCC, DHM's gauges, FAOSTAT.

## The twin

FAO-56: daily reference evaporation, crop water use, a root-zone water "bucket", runoff, evaporation from bare soil's
surface layer. FAO-33: harvest as a share of what the field could grow, from how short of water the crop was. Rice's
water losses to seepage and percolation are counted [H9]. Each year runs on rain alone and with water whenever needed
(100 by construction) [C5]. It counts thirst only: no flood damage, pests, nutrients or frost. Rain-fed rice runs as a
bucket, not a pond, so it never fails in the model [H10].

## The four features

1. **25-Year Replay.** Each plan's coming season through every past season: 24 complete years, 2002-2025 [B3]. One
   square a year: worked, struggled or failed, with the reason [C2]. Years with the same El Niño or La Niña state as this
   year are highlighted (NOAA ONI) [C8]. It starts from the soil's water today, picked with the probe [C6]. Tabs for the
   next 3 and 6 months. Every square is an estimate [C1].
2. **Field Pulse (खेतको नाडी).** The field's greenness from space as a heartbeat line, in Bikram Sambat months. HLS 30 m
   is field scale, MODIS 250 m neighbourhood scale [D1]. The farmer confirms or corrects planting and harvest dates,
   saved only on the phone [D6]. Nearby fields appear as totals from the area map [A2-A4].
3. **Safe Trial.** A plan tried on one quarter of the field [E1]. The probe's four spots become the experiment, one in
   the trial quarter and three in the rest, with a weekly photo diary kept on the phone. Compared after harvest with the
   rest of the field and with the Replay's estimate [E4].
4. **Data Check-up.** How we checked the rain record, in plain words: the gauges' share in NASA's rain fell from 96-98%
   to 56-72% a year from 2017 [F1]; CHIRPS shows no step [F4]; our correction scales the rain back [F7]; every field
   runs its own check [F13]. Numbers that depend on the corrected rain are flagged [F14].

## The two labels

- **How sure.** Each output's row in a scorecard fixed before any score: VERIFIED = an independent reference, at least
  10 cases, at least 92% within tolerance [G1]. Verified today: the rain word of each month (12 of 12), the heat word
  (12 of 12), and our copy of DHM's monsoon dates (24 of 24) [G2]. These test the shape of the year and our copy of
  DHM's record, not a method of ours. ESTIMATE: rain months (13 of 20, in-sample since the tuning) [F11], floods (2 of
  2, not blind), dry seasons (2 of 4), both suggestions beating today's plan (94 of 94 runs of one crop model), the soil
  words, the scores, 2040 [G3]. NOT YET CHECKABLE: frost, bare months, sowing dates, the crop guess, each year's harvest,
  groundwater, each part's wetness, the probe; each row names the data that would check it [G4].
- **How close.** Your field (HLS 30 m), neighbourhood (250 m cells, the area map), valley (GPM about 10 km, SMAP 9 km),
  region (POWER about 55 km, GRACE about 300 km) [G5].

## The plans

165 rotations from six crops, each replayed over 24 complete years and scored 0-100 on harvest, water, ground cover
and soil kept [B2]. Every suggestion keeps rice in the monsoon. Shown, rain-fed: today's plan (rice, then potato:
harvest 65) [H1]; "Fill the empty months" (rice, then wheat: 83, about 8 to 22 more) [H2]; "Feed your soil" (rice, then
lentil: 74, about 5 to 14 more) [H3]. The same three win with fewer years and other crop sensitivities [H7]. The size of
the gain rests on root depth and soil [H2, B6]. With water, every plan scores 100 [H8].

## The checks

`VALIDATION.md` has six layers, from "the code runs" to "people can use it". Each rule is committed before its first run;
two model changes were tried, then undone and recorded [J6]. The equations reproduce FAO-56's printed
examples (3.88 mm a day in Example 18) [J2]. The repository has 1,494 tests [J1]. An independent AI review (`REVIEW_2.md`)
recomputed the numbers of 13 November with its own code.

## Testing with farmers: our plan for next season

**A plan, not a result.** No farmer has used the tool for a season yet. The plan: **10 to 20 farmers, through a
cooperative, for one season**. It tests the advice against what really happens; the website test with five farmers is
separate (`docs/FARMER_TEST.md`).

**(a) The short questions we ask, at the start** (in Nepali, by someone the cooperative knows; the answers go into the
farmer's files, `data/field_visit/<field>/`):
1. What do you grow, in which season, and in which part of the field?
2. When did you really sow and harvest each crop, this year and the last three?
3. Do you water? From where (canal, well, rain only), and how often?
4. What soil problems do you see (dry patches, standing water, hard ground)?
5. What would you change on your field if you could?

**(b) What we record during the season:** daily rain, from a simple rain gauge at the cooperative or the farm; each
crop's real sowing and harvest dates; the days the farmer waters; the soil stick's readings, part by part, when the team
visits; and the harvest, in the farmer's own measure (we do not convert it to tonnes; the tool never shows tonnes).

**(c) How we compare our predictions with what happened.** The comparison rule is fixed **before the season starts**:
written into `config/rules.yaml` (only with the owner's go) and committed before the first visit, and the farmers'
files are locked by their SHA-256 in `config/locked_test.yaml` before any score uses them (rules.yaml `verification`).
Nothing is tuned after the data arrive. The yardsticks proposed are the ones the compliance table already uses
(`VALIDATION.md`, "Compliance table"):
- sowing and harvest: the satellite's season start and end within 10 days of the farmer's dates, per crop and year;
- our guess of the crops: equal to the farmer's rotation, per field;
- good and bad years: the farmer's 3 worst years in our lowest third and the 3 best in our highest third;
- rain: the twin's monthly rain within 19 % of the farm's gauge;
- soil water: the twin's soil water before a reading within 0.04 m3/m3 of the calibrated stick.

An answer becomes "Verified" only with at least 10 independent checks and at least 92 % of them right, its 95 % range
shown beside it (rules.yaml `verification`). Whatever the result, it is published as it is, and each screen's label
changes with it.

## Our roadmap

**Plans, not results**, in this order:
1. Let a field use its own local rain readings, a measured soil value and the farmer's real crop calendar.
2. Prepare a whole valley in advance, so a farmer taps their location and gets the nearest prepared plan at once.
3. A one-page printable view for agriculture advisers that works offline.
4. Fewer but stronger outputs.
5. A "what really happened" checker for the season's results.
6. The 2040 outlook rebuilt after the rain correction.
7. Reach farmers through cooperatives and women's groups, since many farms are run by women.

## What is a placeholder

The field: a 60 m square of mapped cropland near Bhaktapur, chosen by us, not a farmer's [B4]. Its crops, dates, water
source (unknown) and soil; the four nearby sample fields too [B5]. No farmer has checked any number. The probe has had no
bench test, so the site gives no water number from it [E3].

## Why no backend

Judges open the site on their own phones, months later, with our laptops off. So all heavy work runs ahead of time, and
the site is plain files on GitHub Pages: no server, no keys, no login, no AI calls [I1]. The trade-off: a new field must be
prepared on a laptop first, with one command to download and one to build [I3]. The site needs the network to open and
for its map; offline use is not built yet [I6]. The one planned exception, a small database for live probe readings, is
not built.

## Short answers

- **"Is the 2017 step up in rain climate change?"** Our check says no. NASA's rain combines satellites with ground
  gauges; from 2017 far fewer gauges near our valley fed into it. Their share falls from 96-98% to 56-72% a year, and
  CHIRPS shows no step [F1, F4]. We corrected for it.
- **"Do the suggestions help a farmer who can water?"** Not in harvest: with water every plan scores 100 [H8].
- **"Whose field is this?"** Nobody's yet. It is a labelled sample [B4].
- **"Does El Niño matter here?"** We have not tested it. The Replay only highlights similar years [C8].
- **"Can it run anywhere?"** Its inputs are global and one command builds a field; the rain check ran unchanged in
  Madagascar. No field outside Nepal is on the site yet [I4].
