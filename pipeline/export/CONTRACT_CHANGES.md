# Contract changes (for the UI teammate)

`schema.json` is the full truth. `site/data/fields/demo.json` is regenerated after every change. Since 2026-11-13 it holds
no made-up number: what is not computed yet (`field.sections`, step 8; `future`, step 9) is named in its `mock` list and
holds no numbers.

## 2026-11-13 (Friday, 17:15): one weather event per year; "Feed your soil"; the gain as a range; new tips (owner's answers 3, 4, 5, 7, 8, 9)

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `replay.<plan>[].event` | computed from each plan's own crop seasons; the same year could differ between plans (7 of 24 years) | **the field's weather for that calendar year, the same on every plan** (drought: a dry monsoon or a dry winter; flood: the year's wettest day; drought first). Demo: flood 2002, 2004, 2024; drought 2006, 2009, 2013, 2015, 2023, 2025 | You may show the event once per year, whatever plan is open |
| `replay.<plan>[].event_season` (new, optional) | did not exist | `"winter"` or `"monsoon"`, **only with `event: "drought"` and only when the drought comes from that one season** (2006 winter; 2013 and 2015 monsoon). Absent when both seasons were dry (2009, 2023, 2025). Also inside `uncorrected_rain` | Say "A dry winter" / "A dry rainy season" (words.json, screen 7 `labels.event_season`) instead of the drought words when it is there |
| `plans[2].name` (id `safest`) | "Safest in bad years" | **"Feed your soil"** (rice then lentil does not do best in bad years; rice then wheat does). The id stays `safest` | Use the name from the file; Nepali name in words.json screen 8 `labels.plan.items.safest` |
| `plans[].tabs.benefits` | "Harvest: about 18 more, out of 100." | "Harvest: about 8 to 22 more." (a range over how deep roots may reach); the "unknown" tab says why | Nothing: the text comes filled |
| `plans[].tabs.evidence` | "Very dry years: 7 of 24." | "Drier than usual: 6 of 24 years." | Nothing |
| `plans[].tabs.unknown` | | new lines: the soil numbers come from 859 m away; the harvest gain is a range; our rain may still read too high | Nothing |
| `plans[].tips` / `tips_ne` | a rice tip resting on almost no dry days; "straw in March" from the plan calendar | no rice tip; a "thirsty" tip only for a crop short of water on 5 or more days a year in its worst month; the straw tip names a month the satellite shows bare (November for the current plan) and is left out where a suggested plan grows a crop then. **A plan may now have one tip only** | Do not assume three tips |
| `plans[].score.soil_kept` | 74 / 74 / 74 | 74 / 75 / 75 (the 92 IMERG Late days of Oct-Dec 2025 are scaled too) | Nothing |
| `sources[0].product` (GPM) | "Final days from 2017 scaled back ..." | "days from 2017 scaled back, month by month, ..." | Nothing |
| words.json | | screen 3: "The ground is bare about {bare_days} days yearly." (it counts bare ground, not days without a crop); two lines saying the water trend is about the wide area, not the farmer's well (`water_wide`, shown when `diary.groundwater.confidence` is at least 0.95; `water_not_yours`); screen 7: `labels.event.items.drought` is now "A drier year than usual"; `labels.event_season` | Never show `diary.groundwater.confidence` as certainty about the field |

## 2026-11-13 (Friday, 16:00): no made-up numbers any more; `mock` list; `irrigated` required; `words.json` (owner's answers 2, 16, 17)

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `mock` (new, top level, optional) | did not exist | a list of the blocks that are **not computed yet**: today `["field.sections", "future"]`. Absent or empty when everything is real | Show "not ready yet" for every block named here. Never show a number from it |
| `field.sections[]` | 12 made-up sections with made-up wetness and probe temperatures | **36 real sections** (10 m squares that tile the 60 m field, `s1` at the south-west corner, row by row), each `status: "grey"`, `wetness: null`, `temp: null`, `sure: 0` until build step 8 | Draw the outlines; show every part as "not ready yet" (fog). `wetness` can be `null` now |
| `future` | a made-up 2040 outlook | **`null`** until build step 9 | Show "not ready yet" on the 2040 screen. Check for `null` before reading it |
| `field.name` | ended "(MOCK data)" | "Bhaktapur demo field (PLACEHOLDER location and rotation)", from the field's config | Still say it is a sample field |
| `sources[]` | a last row "MOCK data for building the site" | that row is gone (9 rows) | Nothing |
| `replay.<plan>[].irrigated` | optional | **required** on every year (it was always written) | Nothing |
| `site/data/words.json` (new file) | did not exist; texts sat in `pipeline/words/` | `{about, screens[10], shared, glossary[], crop_explainers}`: every word on the ten screens, the shared words (buttons, crop names, months, source kinds), the glossary and the crop explainers, English and Nepali | Read the screen texts from it; fill `{placeholders}` from the field file; do not retype texts. Each Nepali text carries `ne_review` until a person has reviewed it: do not show that key |

`python -m pipeline.export.validate` now checks that a block named in `mock` holds no numbers, and that an empty block is
named there. `--final` (the freeze check) accepts "not ready yet" blocks and still refuses anything with made-up (MOCK)
numbers. The validator also reads `words.json`.

## 2026-11-13 (Friday, afternoon): REVIEW_2, an independent review. No key added, removed or renamed

What changed in `demo.json` (labels and one evidence range; no result):

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `sources[]` MODIS row | "greenness (NDVI), before HLS" | adds "compared with HLS only; no number shown uses it" | Do not attribute any number to MODIS |
| `sources[]` SoilGrids row | "soil texture and carbon" | "water the soil holds at field capacity and wilting point (machine-learning map); nearest cell with values, 859 m from the field" | Show the distance where the soil source is shown: it is not the field's own soil |
| `method.rain_correction.gauges.weight_before_pct` | `[96, 97]` (read by hand) | `[96, 98]` (the full monthly series, fetched and carded) | Nothing |
| `method.choices[].status` | 5 owner-approved choices read "Claude's choice" (a capital letter was missed) | they read "Claude's choice, owner-approved 2026-11-13"; two entries added (`plans.third_plan_rule`, "put to the owner"; `temperature_correction.min_shared_days_per_year`) | Nothing |

What the validator now refuses (`python -m pipeline.export.validate`): a plan without a replay; replay years that do not
run year by year. New: `--final`, the freeze check, which also fails while anything is MOCK, when two plans grow the same
crops, when a plan's `score.harvest` is not the mean of its replay (within a point), or when a replay year lacks
`irrigated`. `python -m pipeline.export.mock` no longer overwrites a file that holds real results (`--force` to do so).

Things the review found that the UI should know (all in REVIEW_2.md):

- **`event` is per plan, not per year of weather.** The same year carries different events on different plans in 7 of 24
  years (2020 is `none` for `current` and `flood` for the other two). Do not show it as "the weather of that year" across
  plans until the owner decides (REVIEW_2 M4).
- **`score.harvest` and the replay's `harvest` are the rain-fed case; `score.water` comes from the watered run** (how much
  of the crop's need irrigation must supply, counted 1.5 times while `diary.groundwater.direction` is `falling`).
- **`irrigated` is `{harvest: 100, dry_days: 0}` in every year of every plan**, by construction: "if you can water" assumes
  the water never runs out and counts thirst only. Label it so; it is not a forecast of full baskets (M15).
- **`diary.groundwater.confidence` (1.0) is about the regional trend** (a GRACE mascon from the Bihar plain to Everest),
  not about the field. Do not show it like a section's `sure` (M12).
- **`diary.guess` (`["rice", "potato"]`) is a near-tie with wheat for the winter crop** (M11), and `diary.bare_days` (62)
  counts days of bare ground (NDVI below 0.25), not days without a crop.
- **`diary.months[].cover` (satellite) and the plans' crop dates (calendar) disagree in winter**: the satellite shows
  bare ground in November and December and a crop from January to May; the placeholder potato runs 30 October to 21
  February. Tips about bare months come from the plan calendar (H3).
- **`plans[].name` is English only**; the Nepali names and all screen words are in `pipeline/words/screens.json`, which is
  not published under `site/` (M14).


## 2026-11-13 (Friday, midday): the plans are real; ranges for the rain fix; the method page grows (owner's decisions 1, 4, 5)

`demo.json` now holds the three real plans (step 7), their replays, the real `sources`, and two new method-page blocks.
Still MOCK: `field.sections` (step 8) and `future` (step 9); the sources list says so.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `plans[]` | MOCK | `current` (rice then potato, the placeholder), `cover_gap` "Fill the empty months" (rice sown 15 Jun, then wheat 15 Oct), **`safest` "Safest in bad years"** (rice 15 Jun, then lentil 15 Oct). Real scores, five tabs and tips in English and Nepali (all SI drafts: English for the owner's review, Nepali for a native speaker's) | The third plan's id is now **`safest`** (was `follow_shift` in the mock). Its Nepali name is in `pipeline/words/screens.json`, screen `what_to_grow`, `labels.plan.items.safest` |
| `plans[].score_uncorrected_rain` | did not exist | **optional**, same four keys as `score`: the plan's scores with GPM's rain as published (no 2017 fix). Present only when a score differs | Show each score as a range from the lower to the higher of the two (e.g. water 51-55). Label: "with and without our rain fix" |
| `replay.<plan>[].uncorrected_rain` | did not exist | **optional** `{harvest, dry_days, event, irrigated}`: the same year with GPM's rain as published. Present only in years it changes (for the demo's current plan 2004, 2005, 2010 and 2017-2025; `cover_gap` 2005, 2013, 2014 and 2017-2025; `safest` 2005, 2010, 2013 and 2017-2025; the events move because they rank years against each other) | Show the basket as a range (lower to higher harvest); if the event differs, show both icons small, or "may have been" |
| `replay` keys | `current`, `cover_gap`, `follow_shift` (MOCK) | `current`, `cover_gap`, `safest`, 24 years each (2002-2025) | Read the keys from `plans[].id` |
| `sources[]` | one MOCK entry | nine real datasets (GPM IMERG, NASA POWER, the airport station, HLS, MODIS, GRACE, SoilGrids, NASADEM, the twin) plus one MOCK entry for the parts still made up | Nothing new |
| `method.rain_correction` | did not exist | **optional**: `applied`, `from` (2017-01-01), `reference_years`, `factors` (Jan-Dec), `held_out` (error and ratio against the airport station, before and after), `rain_mm_per_year`, `gauges` (gauge weight and station counts before and after), `words` `{en, ne}`: the plain-word explanation | On the method page, show `words` (Nepali first), then the numbers for readers who want them |
| `method.choices` | did not exist | **optional** list of `{id, choice, value, status}`: every choice no published source fixes, with who approved it | A plain list on the method page (English, technical) |

`validate.py` refuses an `uncorrected_rain` or `score_uncorrected_rain` that changes nothing.

## 2026-11-13 (Friday): the diary is real; `shift_days` may be null

`demo.json`'s `diary` now holds real numbers (step 6c). One change in meaning:

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `diary.shift_days` | a number | a number **or `null`**: null = "can't tell" | The demo field is **null**: the onset rule finds the first lasting rain spell, which is pinned at 15-17 May in 21 of 25 years, so no shift can be measured. Show "We can't tell yet" (fog), never "0 days" |
| `diary.guess` | MOCK `["rice", "wheat"]` | `["rice", "potato"]` from season timing (a near-tie with wheat in winter) | Show it as a guess the farmer confirms or changes |
| `diary.groundwater` | MOCK | falling, -2.57 cm/yr, confidence 1.0, from GRACE/GRACE-FO (regional, about 300 km) | Say "water stored under and on the land, across the whole region", not "your well" |
| `diary.months[]` | MOCK | real words (rain, soil, heat by terciles of the field's own year; frost band; cover) | Nothing new |

## 2026-11-13 (Friday, early): the method page's season comparison, APPLIED (owner's go)

New **required** top-level key `method` (the site's method page). `demo.json` carries the real numbers from step 6b.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `method.season_detection` | did not exist | `chosen` (`threshold`, `changepoint` or `detective`), `margin` (0.02), `held_out_years`, `thin_days` (16), `rule_methods_agree` (0-1), and `methods`: three entries `{id, si, score, by_year: [{year, score}], start_diff_days, peak_diff_days, end_diff_days}` | On the method page, show the three methods side by side with their scores (0-1, e.g. as a share of 100 days), mark the SI one (`si: true`, the "season detective"), and say which one is used and why: a method replaces the threshold method only if it beats it by `margin`, a rule set before the test. Always show the caveat: there is no farmer calendar yet, so the score shows how well each method copes with missing images, **not** how accurate it is. The date differences are days between each method's season dates and the threshold method's (null for the threshold method) |

`validate.py` checks that `chosen` follows the margin rule from the scores, so a hand edit cannot pick a
different method. Words for the method page (English and Nepali) come at step 7 from `pipeline/words`.

## 2026-11-12 (Thursday evening): water source, soil temperature may be null, complete years, APPLIED (owner's batch decisions)

`demo.json` (still MOCK) carries the new keys. All values are owner decisions of 2026-11-12.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `field.water_source` | did not exist | **required**: `unknown`, `rain-only`, `canal`, `well` or `irrigated` (the demo: `unknown`) | While it is `unknown`, show the two baskets **side by side**, labelled **"If you can't water"** (`harvest`, `dry_days`) and **"If you can water"** (`irrigated.harvest`, `irrigated.dry_days`). Labels: `pipeline/words/screens.json`, screen `last_years`, `labels.water_case` (`rain_fed`, `irrigated`), in Nepali and English |
| `field.sections[].temp` | a number | a number **or `null`** (still required): soil temperature from the probe, `null` until the probe has read that section | Show "not sure yet" (fog) for `null`; never show 0 |
| `replay.<plan>[]` years | 2001-2025 | **complete years only**: years holding every crop of the rotation. For rice then potato that is **2002-2025** (24 years); 2001 had rice only and would look like the best year | Read the years from the file (`{year_count}` on screen 7); do not assume 25 |
| `replay.<plan>[].event` | flood = a day of 100 mm or more (10 of 25 years) | same values (`none`, `drought`, `flood`); flood now = the year's wettest crop-season day in the heaviest fifth of the record's years, a rule fixed in advance (about one year in five) | Nothing |
| `site/data/live.json` (not in the schema) | `sure` a number | `wetness` = the probe's own 0-100 % moisture; `temp` = soil temperature, `null` when the probe says "Check wiring"; `sure` is `null` until the step-10 Kalman update | Show fog while `sure` is `null`; show "check the probe" when `temp` is `null` |

The site is **text only**: the shared "Listen" button is gone from the word files, and no MP3s will be
made (owner, 2026-11-12). Nepali month names now carry the Gregorian months in Devanagari, e.g.
बैशाख (अप्रिल–मे).

## 2026-11-12 (late night): Nepali tabs and tips, no frost event, APPLIED (owner's go)

The site is Nepali first, so every plan now carries Nepali text beside the English. Frost is no longer a
replay event. Now in `schema.json`;
`demo.json` (still MOCK) carries it.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `plans[].tabs_ne` | did not exist | **required**: the same five keys as `tabs` (`why`, `evidence`, `benefits`, `unknown`, `check`), each a non-empty Nepali string that must contain Devanagari | Show `tabs_ne` first, and `tabs` one tap away |
| `plans[].tips_ne` | did not exist | **required**: one Nepali tip per English tip, **same order and same count** as `tips` (validate.py checks the count) | Pair `tips_ne[i]` with `tips[i]` |
| `plans[].tabs`, `plans[].tips` | English | unchanged | Nothing |
| `replay.<plan>[].event` | `none`, `drought`, `flood` or `frost` | **`none`, `drought` or `flood`**: `frost` is gone (owner, REVIEW_NOTES M1). The frost series overcounts cold nights, so frost is shown only as the monthly risk band `diary.months[].frost`, never as a per-year event | Drop the frost basket icon on the replay screen; keep the frost icon in the twelve-month calendar |

Both are filled at build time (step 7) from `pipeline/words/tabs.json`. The site never fills a template
itself. The Nepali needs native-speaker review before submission (`pipeline/words/PREVIEW.md`).

**Meaning clarified, no shape change:** `field.sections[].temp` is **soil temperature from the probe**
(owner, 2026-11-12), not air temperature. The screen text is now "How warm the soil is: {temp} degrees."

**Answered 2026-11-12 (owner's batch decisions item 23):** `temp` may be `null` for a section the probe has not
read; see the Thursday-evening entry above.

## 2026-11-12 (night): the demo field moved again (values only, no schema change)

The 100 m square below turned out to be a construction plot. The placeholder is now a **60 m square**
the owner chose from HLS-checked candidates, moved 25 m north to keep a river strip out of it. It is
still a labelled placeholder, and `demo.json` still holds MOCK numbers.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `field.lat`, `field.lon` | 27.6785, 85.427417 | **27.690767, 85.441792** (about 2.6 km north-east of the old point) | Centre the map here |
| `field.sections[].polygon` | inside the 100 m square | inside the 60 m square, from its south-west corner (85.441487, 27.690497) (still MOCK) | Nothing |
| `index.json` `lat`, `lon` | 27.6785, 85.427417 | **27.690767, 85.441792** | Nothing, if the map reads them from the file |
| `index.json` `bbox`, `name` | unchanged | unchanged | Nothing |

## 2026-11-12 (later): the demo field moved (values only, no schema change)

The owner found that 27.67 N, 85.43 E is Bhaktapur's old city, not farmland. Until the real field is
known, the demo is a labelled **placeholder**: a 100 m square of cropland (ESA WorldCover 2021) about
1 km north of that point.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `field.name` | `Demo field (MOCK data)` | `Bhaktapur demo field (PLACEHOLDER location and rotation) (MOCK data)` | Show the word placeholder somewhere visible (for example a small "sample field" tag) |
| `field.lat`, `field.lon` | 27.67, 85.43 | **27.6785, 85.427417** | Centre the map here |
| `field.sections[].polygon` | started at the old point | start at the placeholder square's south-west corner (still MOCK) | Nothing |
| `index.json` `bbox` | `[85.42, 27.66, 85.44, 27.68]` | **`[85.379227, 27.625034, 85.480773, 27.714966]`** (about 5 km each way around the old point: every dataset is fetched for this box) | A field drawn inside this box is "inside a prepared area" |
| `index.json` `name` | `Bhaktapur demo field` | `Bhaktapur demo field (PLACEHOLDER location and rotation)` | Nothing |

## 2026-11-12 (evening): irrigated replay, APPLIED (owner's go)

The owner asked that every replay run both rain-fed and irrigated, so the site can show what irrigation
changes. Now in `schema.json`; `demo.json` (still MOCK) carries it.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `replay.<plan>[]` (each year) | `{year, harvest, dry_days, event}` | adds `irrigated: {harvest, dry_days}` (harvest 0 to 100, dry_days 0 to 366, no other keys). `harvest`, `dry_days` and `event` stay the field's own case (rain-fed while its water source is unknown) | Show a second basket "with water" beside each year, or a toggle. The key is optional in the schema, so older files still validate, but every file the pipeline writes has it |

"Irrigated" means water whenever the root zone passes the point where stress starts: an upper bound on
what irrigation can change (METHOD_NOTES.md item 3). The `event` is about the weather, so it is the same
in both cases.

Also for the UI teammate: harvest for rice and other crops with no published Ky uses an assumed Ky
(owner decision); the "unknown" tab will say so.

## 2026-11-11 (b): owner decisions A13 and D7

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `future.nothing_changes`, `future.with_plan` | `{harvest: [...]}` | `{harvest, harvest_low, harvest_high}`: three arrays, one value per year in `future.years`, with low <= harvest <= high | Show a range (for example a band on each dial), not one number. Golden rule 11: projections are ranges |
| `diary.groundwater` | did not exist | `{trend_cm_per_year: number, direction: "falling" or "steady" or "rising", confidence: 0 to 1}`, required | A simple picture (well or water level going down, flat or up) plus fog when confidence is low. It is regional (from GRACE satellites), not this one field: say so in the glossary |
| `diary.months[].frost` | `none / risk / frost` | `none / risk / high` | Rename the third icon state |
| `diary.months[].cover` | free text (crop names) | `bare / partial / crop` | Three cover pictures; crop names are no longer here |
| `diary.months[].rain` | `low / medium / high` | unchanged | — |
| `diary.months[].soil` | `dry / medium / wet` | unchanged | — |
| `diary.months[].heat` | `none / some / high` | unchanged | — |

## 2026-11-11 (a): first version (build step 1)

- Section polygons are `[lon, lat]` pairs and the ring is not closed. **Leaflet wants `[lat, lon]`,
  so swap them.**
- `sources[].type` is one of `satellite`, `model`, `station`, `probe`. Show "model" sources as
  model-based (golden rule 8).
- At least 3 plans; one has id `current`. `replay` has a key per plan id; only complete years are exported, year by year (2002 to 2025 for the demo).
- No extra keys are allowed anywhere. Ask before relying on a key that is not in the schema.
