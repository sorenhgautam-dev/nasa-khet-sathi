# Note for the UI: where the site lives and what it reads

Written 2026-11-13 (Friday). The contract changes several times today; each change is listed, newest first, in
`pipeline/export/CONTRACT_CHANGES.md`. `pipeline/export/schema.json` is the full truth.

## 1. Where your files go

```
site/
  index.html          <- must be here, at the root of site/
  (your css, js, images: any layout you like under site/)
  data/               <- written by the pipeline only. Read it, never edit it.
    index.json
    fields/demo.json
    words.json
```

- **Hosting is GitHub Pages from this repository** (owner, 14 November night; the Vercel plan is dropped). On every
  push to `main`, `.github/workflows/pages.yml` publishes the `site/` folder as it is (**no build step**). If you use a
  bundler, commit its **built output** into `site/`; do not put a `package.json` in `site/`.
- The live address is **https://sorenhgautam-dev.github.io/data-test-game/**. The site sits in the `/data-test-game/` folder of that address.
- **Every path must still be relative**: `fetch('data/index.json')`, `src="img/x.svg"`, `url(../img/bg.svg)`. Never
  start a path with `/`. Relative paths work at the root, in a folder and when you open a preview address.
- **Fully static.** No server functions (no `api/` folder, no `middleware.js`), no environment variables
  (`process.env`, `import.meta.env`), no files that need compiling (`.ts`, `.jsx`, `.vue`, `.scss`). Plain `.html`,
  `.js`, `.css` and images only.
- Check before you hand over: `python3 scripts/check_site.py` from the repository root lists anything that breaks
  these rules.
- File names are case-sensitive on the live site (`Demo.json` is not `demo.json`).
- No server, no login, no key, no call to any outside service (map tiles are fine). Never call an AI service.
- Test it the way a judge sees it: `cd site && python3 -m http.server 8000`, open `http://localhost:8000/` on
  your phone, then turn the laptop's other programs off. Then open the live address on mobile data.

## 2. The three files to read

1. `data/index.json`: the prepared fields. `{"fields": [{"id", "name", "country", "lat", "lon", "bbox"}]}`.
   Use it for "Try our demo field" and the list. A field drawn outside every `bbox` gets a friendly message.
   A field drawn inside the box is not the farmer's own field: say "we show our sample field near you".
2. `data/fields/<id>.json`: everything about one field (today only `demo`). Blocks: `field`, `diary`, `plans`,
   `replay`, `future`, `sources`, `method`.
3. `data/words.json`: every word on the ten screens, the glossary and the crop explainers, in English
   and Nepali. Use these texts as they are; do not retype them. Nepali first, English one tap away.

## 3. What to know about `demo.json` today

- It is a **sample field** with a placeholder rotation. Say so where the field is shown.
- **Real:** `diary`, `plans` (three plans, five tabs and tips each, English and Nepali), `replay` (2002 to 2025 for
  each plan), `sources`, `method`.
- **Not ready yet:** `field.sections` and `future`. The file's `mock` list names them. The 36 sections are real
  outlines (10 m squares) but hold no numbers yet (`status: "grey"`, `wetness: null`, `temp: null`, `sure: 0`), and
  `future` is `null`. **Show "not ready yet" for every block named in `mock`.** When a block becomes real it leaves
  the list, with no other change of shape.
- Values can be `null`: `diary.shift_days` (show "we can't tell yet", never 0), a section's `temp`, and from
  today a section's `wetness` and the whole `future`.
- Each replay year has the farmer's case without watering (`harvest`, `dry_days`, `event`) and with watering
  (`irrigated`). While `field.water_source` is `"unknown"`, show both side by side: "if you can't water" and "if
  you can water". The watered case is 100 and 0 in every year: it assumes water never runs out. Label it so.
- Some years and scores carry a second version, `uncorrected_rain` and `score_uncorrected_rain`: show them as a
  range ("72 to 73"), not as a second result.
- `sources[].type` is `satellite`, `model`, `station` or `probe`. Mark `model` sources as worked out by computer.
- `diary.groundwater.confidence` is about the wide region, not this field. Say "the regional trend is clear",
  never "we are sure about your well".
- Put text on the page with `textContent`, not `innerHTML` (some texts contain `<` and `>`).
- Section polygons are `[lon, lat]` and the ring is not closed. Leaflet wants `[lat, lon]`: swap them.
- Harvest is always a percentage of what the field could grow. Never show tonnes.

## 4. Landed on 13 November, 17:15

- The third plan is called "Feed your soil" (its id stays `safest`).
- `event` is the field's weather for the year: the same on every plan. A drought from one season carries
  `event_season` (`"winter"` or `"monsoon"`): say "A dry winter" / "A dry rainy season" (words.json, screen 7).
- A plan can have one tip only. Do not lay the screen out for exactly three.

## 5. Landed on 13 November, 17:30: the farmer confirms the winter crop

`current_options` holds the current plan for both answers: `rice_potato` (the default) and `rice_wheat`.

- Screen 3 asks: "We think you grow rice first." "Then potato or wheat." "Which one do you grow?" (words.json,
  screen 3, `guess_first`, `guess_options`, `guess_which`, `guess_cannot_tell`).
- Before an answer, show the default option. It is exactly what `plans[0]` and `replay.current` hold, so a site that
  ignores `current_options` still works.
- On the answer, take from that option: `crops`, `score`, `score_uncorrected_rain`, `tabs`, `tips` (and `_ne`) and
  `replay` for the current plan; and for the two other plans the `tabs` / `tabs_ne` in the option's `compared`
  (their "about N more" lines depend on what they are compared with). Everything else stays.

## 6. Landed on 13 November, 17:45: two SI pieces

- `diary.months[].cover_sure` (0 to 1): how sure the month's cover word is. Lower = show a little fog and
  "We are less sure about this month." (words.json, screen 3, `month_less_sure`). June is 0.80 on the demo field.
- `method.field_memory`: a short text (`words.en`, `words.ne`) and numbers for the method page. On the demo field
  it says the learned model did not beat the simple one and was left out. Show it as it is.

## 6b. Landed on 14 November (Saturday), 00:40: room for real sections and the 2040 outlook

New optional fields (details: `pipeline/export/CONTRACT_CHANGES.md`, top entry). They are empty until steps 8 and 9 land on
Saturday. Then `mock` becomes empty.

- Each section can say `low_ground` (true / false / null) and `greener` (`more` / `less` / `same` / `unknown`). Show a
  small mark with a word, never colour alone.
- `field.status_date`: show "as of <date>" wherever the sections' status and wetness appear.
- Each plan, and each current-plan option, gets its own `future` (`harvest`, `harvest_low`, `harvest_high`, one value per
  `future.years`), and maybe `future_uncorrected_rain` (show it as a range). On the 2040 screen show the plan the farmer
  picked. `future.years` will be `[2040]`: label it "by 2040". `future.words` holds the plain sentences on what the range
  means.

## 6c. Landed on 14 November (Saturday), 01:30: the four parts are real

- `field.sections` now holds 4 parts of about 30 m (2 x 2, `s1` SW, `s2` SE, `s3` NW, `s4` NE), not 36 squares.
- Status and wetness come from the twin on `field.status_date` (3 November 2026). All four parts share them, since
  there is one soil and one weather for the whole field. Only the probe will tell the parts apart.
- `sure` is 0.22 before any probe reading.
- `greener`: s3 "more", s2 "less". The difference is small, so say "a little".
- `low_ground` is null everywhere (we can't tell).
- `mock` is now `["future"]`.

## 6d. Landed on 14 November (Saturday), 05:45: the 2040 outlook and the monsoon's usual start

- `mock` is empty: nothing in the file is sample data any more.
- `future` is real. Its `years` is `[2040]`, standing for 2026-2040. Each plan and current option has its own `future`
  (harvest with a low-high range, from many climate models). The design has no 2040 screen, so the owner wants it on
  the "How we know" page, with `future.words`.
- `diary.shift_days` now comes from DHM's official onset dates (-2.2 days, range -11.5 to +7.7). Show `shift_note`:
  "No clear change since 2001." Never "2 days earlier".
- `diary.monsoon_start` gives the usual start (10-16 June, entry into eastern Nepal; a few days later here), late
  years (2009 only, after 20 June) and its `words` in English and Nepali. Show it on "Next 3 months" and the diary.
- `method.onset` holds the "How we know" paragraph on the monsoon's start.

## 6e. Landed on 14 November (Saturday), 10:00: the second rain version is the DHM-scaled dry edge (renamed)

- `uncorrected_rain` is now `dhm_rain`, `score_uncorrected_rain` is `score_dhm_rain`, and `future_uncorrected_rain` is
  `future_dhm_rain`.
- They hold the run with rain scaled to the Bhaktapur station's long-term average: the lower edge of each range.
- Show "about 69 to 72", not two results.

## 6f. Landed on 14 November (Saturday), afternoon: three rain versions, groundwater as context only

- Ranges now take the min and max over the central value, `*_dhm_rain` and the new `*_untuned_rain` (same shapes).
- The water score no longer depends on groundwater; keep the regional trend as context only.
- `diary.shift_note`: "No clear change since 2001, in Nepal's weather office records." (owner's exact words).

## 6g. Landed on 14 November (Saturday), evening: four new files for the farmer's question

One file of each kind per prepared field (demo, sample-1..4): `data/labels/<id>.json`, `data/replay/<id>.json`,
`data/pulse/<id>.json`, `data/checkup/<id>.json`. Fetch them relatively (`fetch('data/replay/' + id + '.json')`); if
one is missing, say "not ready yet". Schemas: `pipeline/export/{labels,replay,pulse,checkup}_schema.json`.

- **labels:** `outputs.<id>.sure` is "verified" or "estimate" (show this word; `status` is for the detail view);
  `scale` is field / neighbourhood / valley / region, with words in `scales.<scale>.en` / `.ne` and `.about` ("30 m or
  finer" ...). `rain_corrected: true` = link to the Data Check-up. Output ids for every number: see the file (46).
- **replay (25-Year Replay):** `start` is fixed (2026-11-04 on the demo); `windows` m3 and m6; show `year_count`
  seasons (24), never a fixed number. Pick the start with the probe's band (`starts[].probe_band`: needs water -> dry,
  good -> medium, too wet -> wet); before any reading use `start_default` (medium). For each plan id (the field file's
  plans and the `current_options` option ids) `results.<window>.<start>[]` holds one square per past season:
  `result` (worked / struggled / failed / null), `score` (0-100, the share of the crop's water need met), `reason`
  (`{"code": "dry_spell", "month": "01", "days": 18}`, `no_dry_days`, `no_crop_in_window`; render the words),
  `enso` (highlight seasons in `enso.same_as_now`), `sensitive` (mark it: another rain version gives another word),
  `other_versions`. Rain-fed only: show `watering.en` beside it.
- **pulse (खेतको नाडी):** `points.hls` (field scale) and `points.modis` (neighbourhood scale) are `[date, ndvi]`;
  `curve.points` `[date, ndvi, source]` weekly; `seasons[]` (greenup, peak, end); `bare_threshold`; `typical[]`
  (planting, greenup, peak, harvest as MM-DD, per slot; the farmer confirms or corrects them; keep answers on the phone
  only); `nearby` (demo only, else null). Bikram Sambat months are yours to render.
- **checkup:** `break_test`, `evidence[]` by id, `correction`, `versions` (tuned is central), `yearly` (one chart:
  gpm as published, twin, chirps), `depends_on_corrected_rain` (label ids). Word it as a check we ran, not a fault.

## 6h. Landed on 14 November (Saturday), evening: three small checks for "How do we know?"

No home cards (owner): place them behind the cards' "How do we know?" buttons. Fetch relatively
(`fetch('data/rainrisk/' + id + '.json')`); if one is missing, say "not ready yet". Schemas: `pipeline/export/{rainrisk,
fertiliser,heatclock}_schema.json`. Words: `words.json`, screen `last_years` (`rr_*`, `hc_*`, `risk_none`, `why_btn`,
`why_title`, `why_sources`) and `what_to_grow` (`fs_*`). Each file has `labels` (show the two chips on every number),
`why.en` / `why.ne` (the Why? button's lines, as they are) and `sources`.

- **Rain at harvest, in the Replay card's details** (`data/rainrisk/<id>.json`). For the plan shown, per crop: "Harvest
  weeks:" with the `window` months (Bikram Sambat in Nepali, plus `months_note`), then `rr_count` with `risk_years` =
  `count` and `year_count`, and one square per `years[]` entry (heavy when `days` > 0: `rr_sq_heavy`, else `rr_sq_none`;
  a picture, never colour alone). A tapped square: `rr_days` and `days`; `rr_records_differ` when the year is in some
  `other_versions.*.heavy_years` lists but not others. In Why?: `rr_range` with `count_low` / `count_high`, then
  `why.*`. `good_news` true: `risk_none`. Always `rr_past_only`. Demo: rice 8 of 24 years (other rain 5 to 8); potato,
  wheat and lentil 0 (good news).
- **Heat and cold, in the Replay card's details** (`data/heatclock/<id>.json`). One card per `checks[]` entry, named by
  `hc_wheat_heat`, `hc_potato_heat` or `hc_potato_cold`, with `hc_weeks` and the `window`, the plans it belongs to
  (`plans`), `hc_years` (`risk_years` = `today.years_with`) and one square per `today.years[]` (its `days`). `good_news`:
  `risk_none`. Cold: always `hc_cold_caveat`. Around 2040 (`future`, may be null): `hc_less` (ssp245) and `hc_more`
  (ssp585) with `hc_per_season` (`median`, one decimal, as text), `hc_their_past` with `past_median`, `hc_spread` with
  `low`–`high`; `future.good_news`: `hc_rare_2040`. Also `hc_left_out`. Demo: potato cold nights in 17 of 24 years, 3.0 a
  season; models 28.0 a season in 1995-2014 against 19.5 (ssp245) and 20.2 (ssp585) in 2026-2040, lowest to highest 7.3
  to 38.5; no hot day for wheat or potato today or around 2040.
- **Fertiliser saver, in the "Feed your soil" plan's details** (`data/fertiliser/<id>.json`, only when `applies`).
  `fs_lead` (`next_crop`, `legume_crop` from `shared.crop_names`), `fs_saved` (`bags_ha_whole`), `fs_plot`,
  `fs_size_why`, `fs_wide`, `fs_measured_less`, `fs_short`, `fs_ask`. The kg and the hectare stay in Why? (`why.*`):
  "hectare" is a word the screens never show (glossary `never_on_screens`), and no ropani figure has a source yet. The
  plan's `check` tab already carries the dhaincha lines (field file), so nothing else is needed there.

## 6i. Landed on 14 November (Saturday), evening: Weather ahead and How we test each plan

- **Weather ahead** is the third choice on your Choose screen. Data: `fields/<id>.json` `weather` (optional; absent on
  fields outside Nepal, so hide the choice). Contract: `pipeline/export/CONTRACT_CHANGES.md` (2026-11-14 evening). Words:
  `words.json` `screens.shared.weather.*`. One line at the top (`top`, `not_forecast`), then the six blocks after the one
  holding today, Bikram Sambat first, three lines each: Usually (rain and temperature words), Watch out (the first
  danger of the farmer's crop, with "Most years." or "Some years."), Do this (the tip, then "Check with your local
  expert."). No numbers on the blocks; the years, "is it changing", rain, temperatures, dry runs, caveats and sources sit
  behind "Why?".
- **How we test each plan** (the Field Twin explainer, for judges): four steps with a picture and one sentence each, then
  one real example from `simple/<id>.json`. Linked from home (one line, `twin.home_line`) and from How we know. Words:
  `screens.shared.twin.*`.

## 6j. Landed on 14 November (Saturday), evening: dry runs after sowing, and two wheat-book checks

Only new keys; every existing value is unchanged. These live on the judges' "How we know" page (rain at harvest, heat and
cold), never on the farmer screens, which show no numbers. Words: `words.json` screen `last_years`.

- **Rain at harvest** (`data/rainrisk/<id>.json`): each crop row has `dry_run` (`window` = sowing day to last day,
  `years[]` one value a year, `typical`, `worst[]` three `{year, days}`, `typical_low`/`typical_high`). Under each crop:
  `rr_dry_usual` with `dry_run_days` = `typical`; then `rr_dry_worst` and each worst year as its year plus `rr_dry_run`
  (`dry_run_days` = its `days`). A tapped year square can add `rr_dry_run` with that year's `dry_run.years[].days`. The
  range over the rain versions stays in Why? (`why.*`, already in the file). Demo, rice sown 23 Jun: usually 6 days.
- **Heat and cold** (`data/heatclock/<id>.json`): `checks[]` now has four more rows (after the first four), one floret-heat
  and one flowering-frost row per wheat sowing. Every row has `words`: name the card with `T('last_years.' + c.words)`
  (old rows: `hc_wheat_heat`, `hc_potato_heat`, `hc_potato_cold`; new: `hc_wheat_floret_formation_heat`,
  `hc_wheat_flowering_cold`). New rows also have `sure: "estimate"`, `days_after_sowing`, `conditions` (English, for the
  Why?): show `hc_book` on them, and on the flowering row show `hc_frost_caveat` instead of `hc_cold_caveat`. Everything
  else as before (`hc_weeks`, `hc_years`, squares, around 2040). `left_out` now names the 8-35 C pollen figure; keep
  `hc_left_out`.

## 6l. Landed on 15 November (Sunday), night: Behind the scenes (for judges)

A new file, `data/behind.json` (demo field), and `js/behind.js`. Nothing else changed. The section "Behind the scenes:
your field, seen by NASA" sits below Home's first screen (it loads only when scrolled to) and first on How we know. It
shows six counted numbers, the flow line, one card per NASA mission (charts from `story.json`, drawn by `how.js`'s
`K.how.plot`) and the pixel-size picture. Farmer answers show a small tag (`farm.tag_rain`, `tag_weather`, `tag_space`,
filled with `year_count`); a tap opens the matching card in a sheet. Details: CONTRACT_CHANGES.md, 2026-11-15.

## 7. Still to come

- `field.sections` with real numbers (build step 8) and `future` (build step 9): they leave the `mock` list when
  they are real, with no other change of shape.
- The probe: `data/live.json` (in-person demo) and `data/probe_log.json` (the replay).


## 8. Site rules we promised the judges (from CLAUDE.md)

Ten screens, one action each. Sentences of eight words or fewer. Pictures before words; never colour alone.
Buttons at least 48 px. Designed at 360 px wide. First screen under 300 KB. Plain HTML, CSS and JavaScript;
Leaflet for the map. No sound.

If something in the file is unclear or missing, ask before working around it: a missing key is cheaper to add
on our side than to guess on yours.
