# How Khet Sathi works

For answering judges' questions. Numbers as of 15 November 2026 (afternoon), recounted for **Kharipati**, the only field
the app shows: a real farm in Kharipati, Bhaktapur, its crops still placeholders, no farmer's answers yet. Each number
has an ID in square brackets: its source is in `docs/PITCH_FACTS.md`. Refresh numbers there first.

**In one breath.** We download public data around one field, run a small model of it (the "twin") through every day
from 2001 to 2025, try 165 crop plans in it [B2], and export small files that a phone website reads. The site answers
one question: "What can I grow in my field's empty months without risking the harvest I depend on?" [B1]

## The data

- **Rain:** NASA GPM IMERG V07, daily, about 10 km. Our rain check found that its gauge input around this field changed
  in January 2017 [F1, F2]. So each month from 2017 is scaled back to its own 2001-2016 level [F7]. Kharipati's model
  uses that corrected rain: 1,853 mm a year, 1.35 times Bhaktapur's usual [F10]. A second version, scaled to DHM's
  gauges, is kept beside it as a range [F14].
- **Temperature, humidity, wind, sunshine:** NASA POWER (about 55 km, model-based), temperatures corrected to Kathmandu
  Airport; on held-out years the night error fell from 2.31 to 1.22 °C [J3].
- **Greenness:** HLS (Landsat and Sentinel-2, 30 m): Field Pulse, seasons, bare days, the area map [D1, A6].
  Kharipati is about one 30 m square.
- **The field's outline and 9 parts:** an open drone map (OpenAerialMap, 5 May 2026), standing in for our future
  drone [E1].
- **Also:** soil from ISRIC SoilGrids (Kharipati's 250 m cell: 156 mm for plants in the top metre) [B6], height from NASADEM, regional stored water from
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
3. **Safe Trial.** A plan tried on one of the field's 9 parts [E1]. The soil stick's readings, part by part, become the
   experiment: the trial part against the rest, with a weekly photo diary kept on the phone. Compared after harvest with the
   rest of the field and with the Replay's estimate [E4].
4. **Data Check-up.** How we checked the rain record, in plain words: the gauges' share in NASA's rain fell from 96-98%
   to 56-72% a year from 2017 [F1]; CHIRPS shows no step [F4]; our correction scales the rain back [F7]; every field
   runs its own check, and Kharipati's found the same change [F13]. Numbers that depend on the corrected rain are flagged [F14].

## The two labels

- **How sure.** Each output's row in a scorecard fixed before any score: VERIFIED = an independent reference, at least
  10 cases, at least 92% within tolerance [G1]. Verified today for Kharipati: the rain, heat and frost word of each
  month (12 of 12 each), and our copy of DHM's monsoon dates and trend (24 of 24 each) [G2]. These test the shape of
  the year and our copy of DHM's record, not a method of ours, and all are valley-wide. ESTIMATE: rain months (13 of 20)
  [F11], soil words (22 of 24), floods (2 of 2, not blind), dry seasons (2 of 4), both suggestions beating today's plan
  (94 of 94 runs of one crop model), good and bad years (6 of 14), the crop guess (5 of 5), bare months (12 of 13),
  sowing dates (2 of 3), groundwater, the scores, 2040 [G3]. NOT YET VERIFIABLE: the probe's water number and each
  part's wetness; each row names the data that would check it [G4].
- **How close.** Your field (HLS 30 m), neighbourhood (250 m cells, the area map), valley (GPM about 10 km, SMAP 9 km),
  region (POWER about 55 km, GRACE about 300 km) [G5].

## The plans

165 rotations from six crops, each replayed over 24 complete years and scored 0-100 on harvest, water, ground cover
and soil kept [B2]. Every suggestion keeps rice in the monsoon. Shown, rain-fed: today's plan (rice, then potato:
harvest 69) [H1]; "Fill the empty months" (rice, then wheat: 87, about 9 to 23 more) [H2]; "Feed your soil" (rice, then
lentil: 78, about 5 to 14 more) [H3]. The same three win with fewer years and other crop sensitivities [H7]. The size of
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

## Which checks are about Kharipati itself, and which are for the valley

Kharipati sits in the same NASA rain square as the earlier Bhaktapur demo square: one IMERG 0.1° cell (27.6-27.7 N,
85.4-85.5 E) and one POWER weather cell. We checked the daily inputs: NASA's rain as published and POWER's temperatures
are the same for both, day for day, 2001-2025.

- **For the valley, so they apply to Kharipati:** the rain-record check and its correction [F1-F7, F12, F13]; the checks
  against DHM's gauges [F11, F12]; the monsoon onset [C7]; the month words for rain, heat and frost [G2]; Weather ahead
  [O1-O3]; the flood and dry years [C2]; the 2040 outlook's climate cell [H11]; groundwater (GRACE, regional, about
  300 km). The area map's numbers come from the same 5 km box [A1-A4].
- **About Kharipati itself:** its outline and 9 parts from the drone photo [E1]; the drone photo's ripe crop on 5 May
  2026 (checks our crop guess and bare months) [G3]; its HLS greenness and seasons, about one 30 m square [D2, D4, A5];
  its soil cell [B6]; the replay and the plans, run on its own seasons and soil [B2, C3, H1-H5]; and the soil stick's
  parts [E3].
- **One difference:** the demo square's rain was also tuned to four of Nepal's gauges; Kharipati's is not [F8].

## What is a placeholder

Kharipati is a real farm in Kharipati, Bhaktapur [B4]. Its outline is real, from an open drone map. Its crops (rice,
then potato; our guess from space is rice, then wheat), dates and water source (unknown) are placeholders until the
farmer answers. No farmer has checked any number. The earlier demo square and four sample fields are hidden from the
app; their files are kept [B5]. The probe has had no bench test, so the site gives no water number from it [E3].

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
- **"Whose field is this?"** A real farm in Kharipati, Bhaktapur. We have not heard from its farmer yet, so its crops
  are placeholders [B4].
- **"Does El Niño matter here?"** We have not tested it. The Replay only highlights similar years [C8].
- **"Can it run anywhere?"** Its inputs are global and one command builds a field; the rain check ran unchanged in
  Madagascar. No field outside Nepal is on the site yet [I4].
