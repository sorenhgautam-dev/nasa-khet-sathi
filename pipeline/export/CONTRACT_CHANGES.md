# Contract changes (for the UI teammate)

`schema.json` is the full truth. `site/data/fields/demo.json` is regenerated after every change and
still holds **MOCK numbers**; real numbers arrive from build step 5 on.

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
- At least 3 plans; one has id `current`. `replay` has a key per plan id, years 2001 to 2025.
- No extra keys are allowed anywhere. Ask before relying on a key that is not in the schema.
