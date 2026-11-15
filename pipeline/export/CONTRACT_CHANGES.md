# Contract changes (for the UI teammate)

`schema.json` is the full truth. `site/data/fields/demo.json` is regenerated after every change. Since 2026-11-13 it holds
no made-up number: what is not computed yet (`field.sections`, step 8; `future`, step 9) is named in its `mock` list and
holds no numbers.

## 2026-11-15 (Sunday, morning): what would verify each answer (`story.json`, `labels`; additions only)

- `story.json` `compliance[].verify_by` (optional, `{en, ne}`): on a row that is not VERIFIED, one plain line saying what
  would verify it ("What would verify it: The farmer's records: ..."); absent on VERIFIED rows. The English is
  `rules.yaml verification.outputs.<id>.verify_by`.
- `story.json` `verify_how` (`{title, lines[]}`, each `{en, ne}`): "How each answer becomes verified" on How we know (the
  three words, today's count, the four ways the rest can be checked). Drawn after the compliance rows (`js/how.js`).
- `compliance` gains the row `monsoon_shift` (the sentence "No clear change since 2001, ..." checked against DHM's own
  onset dates); `labels.outputs.monsoon_shift` now lists `dhm_onset` alone as its source and carries that row's status,
  k and n (was: `dhm_onset`, `chirps`, `gpm`, no scorecard). New statuses: frost words and the monsoon shift VERIFIED;
  soil words and harvest years ESTIMATE with k / n (VALIDATION, compliance table). No key renamed or removed.

## 2026-11-15 (Sunday, after midnight): 4 parts on every Bhaktapur field; `words.json` shared.welcome (addition only)

- The four Bhaktapur sample fields and Ambohidratrimo now have 4 parts (`s1`..`s4`, 2 x 2, each about one 30 m NASA
  pixel, numbered from the south-west), not 36: sectioning is per field (`sections: {cell_m: 30}` in each config). No
  key changed; only `field.sections` of those five files.
- `words.json` `shared.welcome`: the loading curtain's "Welcome" in the 7 languages (`en`, `ne` with `ne_review`, the five
  drafts); `site/index.html` carries the same words for the first paint.
- The soil test and Today show readings only of the field itself: a garden or indoor test (`probe_log.json` `kind`
  `garden_test` / `indoor_test`) shows on How we know only, as bowls; a practice reading (`fake_probe`) is never read.

## 2026-11-14 (Saturday, near midnight): the indoor test's per-bowl lines and watered-bowl check (`probe_log.json`, addition only)

- `probe_log.json` `sessions[]` gains an optional `check` (only with `--test` and `--watered sN --watered-at HH:MM`):
  `watered`, `watered_at`, `possible`, `passed`, `repeat_error_pct`, `needed_pct`, `margin_pct` (rules.yaml
  `probe.live.watered_check`: more than 2 x the pooled repeat error above every other bowl). Files without it are unchanged.
- The soil screen, for an indoor test, shows one plain line per bowl after the replay ("Bowl 1: drier than the others.",
  `check_soil.bowl_drier`, `bowl_wetter`, `bowl_same`, `bowl_none`) and, with a `check`, "Bowl 3 got water. It read
  clearly wetter." or "... It was not clearly wetter." (`bowl_watered_yes`, `bowl_watered_no`).

## 2026-11-15 (Sunday, night): "Behind the scenes: your field, seen by NASA" (a new file `behind.json`; additions only)

- New file `site/data/behind.json` (`pipeline/export/build_behind.py`, schema `behind_schema.json`, run-field step `behind`
  after `story`). Every other file is byte for byte as it was; `words.json` gains four keys in `shared.farm`
  (`behind_title`, `tag_rain`, `tag_weather`, `tag_space`).
- `numbers[]`: six true counts, each with `value`, `label`, `detail`, `from` (the file it was counted from) and `sources`
  (the field file's own source entries: name, resolution, years, type). `flow[]`: NASA data, Field Twin, the replay with
  its own year count, your answers. `cards[]`: one per NASA mission (`gpm`, `hls`, `power`, `grace`, `nexgddp`,
  `smap_gldas`) with `say` (one plain sentence), `chart` (a chart id in `story.json`, or `power_year` in this file's own
  `charts`), `only` (the chart's rows to show), `source`, `resolution`, `years`, `kind`. `pixels`: the field's side and each
  dataset's square in metres. `tags`: a farmer answer's tag (`rain`, `weather`, `space`) -> the cards it opens.
- The site: `js/behind.js` (loaded only when the section is scrolled to on Home, when How we know opens, or when a tag is
  tapped) draws the section at the end of Home's scroll and first on How we know (`#/how/behind`). Farmer answers (the
  crop guess on Photo, the plans on Next 3 / 6 months, each month on Weather ahead) carry a small tag, "NASA rain, 24
  years": the year count comes from the answer's own data (the replay's years, `weather.years`, the HLS source's years).
  Tags and the section show only on the field `behind.json` was built for (`field`); another field says "Not ready yet".

## 2026-11-14 (Saturday, late night): wording only, no number changed

- `index.json` `fields[].note` (a field on the global defaults) now reads "A field on another continent, run by the same
  pipeline. Not checked against local rain gauges yet." (owner). On How we know, "Fields we have looked at" opens the
  chosen field's own How we know; on Home it opens its farmer steps, as before.
- Weather ahead shows each month as three short lines (the usual weather; "Watch out:" and the farmer's own crop's
  danger, or "Usually no big danger."; "Do this:" and its tip, then "Check with your local expert."). A month with no
  danger has no tip, so two lines. The words were already in `words.json` (`weather.watch`, `weather.do`).
- How we know's "What is not ready yet" lists the NASA season outlook as a next step with its reason
  (`your_plan.nr_outlook`, `nr_outlook_why1`, `nr_outlook_why2`; rules.yaml `weather_ahead.season_outlook`).

## 2026-11-14 (Saturday, night): `probe_log.json` may say it is a garden or indoor test; practice readings only on the hotspot

- `probe_log.json` gains an optional `kind: "garden_test"` or `"indoor_test"` (`scripts/build_probe_log.py --test garden|indoor`; rules.yaml
  `probe.live.garden_test`). Then the site labels the walk "Garden test of our soil stick, recorded on <date>"
  (`check_soil.garden_on`), or "Indoor test of our soil stick. 4 bowls of soil, recorded on <date>" (`indoor_title`, `indoor_on`), every part's `before` and `after` are null and `twin_date` is null, and its bands never set
  the field's soil at the start. Files without `kind` are unchanged.
- `live.json` from the fake probe (`source: "fake_probe"`) is shown only when the page is opened from this laptop or its
  hotspot, under a big "Practice: made-up numbers" banner (`check_soil.practice`), and is never used for anything else
  (rules.yaml `probe.live.practice_on_phone`). Real readings (`source: "serial:…"`) show with their date. No "Tested: n / N".

## 2026-11-14 (Saturday, evening): dry runs after sowing, two wheat-book checks (rainrisk and heatclock files; additions only)

Rules committed before the first run (`8ade382`): `rain_risk.dry_spells`, `heat_clock.wheat_floret_*`, `wheat_flower_*`.
`fields/<id>.json` is unchanged. In the two feature files no existing number changed (compared leaf by leaf on all five
fields); only Why? lines (the old "left out" lines replaced, new lines inserted) and the `left_out` wording changed.

- `rainrisk/<id>.json`: new top-level `dry_day_mm` (1); each crop row gains `dry_run` {`window` (sowing day to last day,
  `stage` "season"), `years[]` {year, days}, `typical`, `worst[]` (3), `other_versions.{untuned,dhm,uncorrected}.typical`,
  `typical_low`, `typical_high`}.
- `heatclock/<id>.json`: every check gains `words` (its title's text id); four new rows after the first four (per wheat
  sowing: `floret_formation` heat above 30 C, days 20-100; `flowering` frost below 0 C, days 90-110), each with
  `sure: "estimate"`, `days_after_sowing`, `conditions`; `rule` may be `below_c`. Words: `rr_dry_usual`, `rr_dry_worst`,
  `rr_dry_run` (placeholder `dry_run_days`), `hc_wheat_floret_formation_heat`, `hc_wheat_flowering_cold`, `hc_book`,
  `hc_frost_caveat` (notes/ui_note.md 6j).

## 2026-11-14 (Saturday, late evening): farmer answers in `simple/<id>.json` (additions only)

Owner, 2026-11-14 evening: farmer screens show only the final answer, and each sentence's wording comes from its output's
label (rules `farmer_answers`, committed `5b4ab42` and `e666fea` before the first run). `build_simple.py` adds, beside the
existing keys (unchanged): `labels_used` (the statuses the wording was chosen from), `today.mode` (`compare` until the soil
stick's cup test passes, then `band`), `guess`, `plan_words[answer][window][start][plan]` (`{now: true}` or
`{counts, verdict, text}`), `actions[plan][window]` (lines `{text, fill}`), `animation` (green/red seasons per plan and the
winner) and `weather_lines[answer][water][block]` (`{usual, danger, tip}`). Every line is a words key plus its fills
(`words.json` `shared.farm.*`, `shared.bs_months.*`); month fills are block keys ('Oct' = Kartik). Soft keys (`*_usual`,
"may") are used unless the output is VERIFIED. Schema: `simple_schema.json`.

## 2026-11-14 (Saturday, evening): Weather ahead, an optional `weather` block in the field file (addition only)

Owner, 2026-11-14 evening: the team's weather spec, approved with four changes (rules: `config/rules.yaml` `weather_ahead`,
committed `8ade382` before the first run). `scripts/run_weather.py --field <id>` (run_field step `weather_ahead`, right after
`export`) adds `weather` to `site/data/fields/<id>.json`; nothing else in the file changes (checked: every other key is
equal before and after on all five Nepal fields). Absent on fields outside Nepal (Bikram Sambat months): hide the choice.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `weather` (optional) | did not exist | `{basis, made_by, years: 24, block_starts_on_day: 15, label, blocks[12], windows[], caveats{}, limits[{name, says}], sources[]}` | "Weather ahead", the third choice on Choose |
| `weather.blocks[]` | | `{key, from, to, years: [first, last], usual: {rain: dry/some_rain/wet, temp: cold/mild/warm, frost: none/risk/high, rain_mm: {median, low, high, versions}, tmax_c, tmin_c}, dry_run: {typical, worst[{year, days}]}, dangers[], none_seen[]}`. `key` is the Gregorian month the block starts in ('Nov' = Mangsir, 15 Nov to 14 Dec) | Show the six blocks after the one holding today; Bikram Sambat name first |
| `weather.blocks[].dangers[]` | | ranked, most years first: `{check, kind: cold/heat/dry_spell/big_rain, crop, sow, window, years, of, often: most/some, hit_years, change: more_common/about_same/less_common/cant_tell, change_basis, tip}`. The rules' "watered" list is this one without `kind` dry_spell | "Watch out": the first danger of the farmer's crop (else the first); skip dry_spell when they can water. "Do this": `tip`. The rest behind "Why?" |
| `weather.blocks[].none_seen[]` | | the dangers tested and never seen (`years` 0) | Why?: "Not seen in these years. Good news." |

No numbers on the block itself: the years, "is it changing", the rain range, temperatures, dry runs, caveats and sources
go behind "Why?". Words: `words.json` `screens.shared.weather.*` (EN, NE needs review, drafts). `about_same` is shown as
"No clear change." (not significant is not "the same").

## 2026-11-14 (Saturday, evening): three small checks behind "How do we know?": rain at harvest, fertiliser saver, heat and cold (additions only)

Three new files per prepared field, made by `pipeline/export/build_risks.py --kind <kind>` (rules: `config/rules.yaml`
`rain_risk`, `fertiliser_saver`, `heat_clock`, committed before the first run). Each has its own schema in
`pipeline/export/`, is checked by `validate --final` and `check_site.py` (no web address inside), and carries
`labels` (refreshed by `build_labels`), `why` (`en` and `ne` lists: the Why? details; Nepali drafted by SI, needs review)
and `sources` (`type` may now be `document`: a published text a rule comes from). No home cards (owner): the UI agent puts
rain risk and the heat clock in the Replay card's details, and the fertiliser saver in the "Feed your soil" plan's details.

| File | Schema | What it holds |
| --- | --- | --- |
| `data/rainrisk/<id>.json` | `rainrisk_schema.json` | Per plan and current option, per crop: the harvest weeks (`window`, FAO-56 late stage, MM-DD), one square per year 2002-2025 (`years[]`: `days` of 50 mm or more, `max_mm`), `count` (years with one), `other_versions` (untuned, dhm, uncorrected), `count_low` / `count_high` (show in Why? as a range), `good_news` (count 0) |
| `data/fertiliser/<id>.json` | `fertiliser_schema.json` | For plan `safest`: `legume`, `next_crop`, `n_kg_ha` [23, 45], `urea_n_share` 0.466, `urea_kg_ha` [49, 97], `bags_ha` [1.0, 1.9], `bags_ha_whole` [1, 2], `area` "hectare" (per hectare only), `measured_uptake_kg_n_ha` 2.3; `applies` false (no numbers) when the plan has no legume |
| `data/heatclock/<id>.json` | `heatclock_schema.json` | `checks[]` for wheat (grain filling, above 34 °C) and potato (whole season, 35 °C or more; 1 °C or less): `window`, `plans`, `today.years[]` (risky days per year), `years_with`, `mean_days`, `good_news`; `future` (NEX-GDDP, 23 models): per scenario `median`, `low`, `high`, `past_median` and each model's own `past` / `future` (mean days per season); `good_news` |

- Words: 40 new texts in `pipeline/words/screens.json` (ids `rr_*`, `hc_*`, `risk_none`, `why_*` on `last_years`; `fs_*`
  on `what_to_grow`), with placeholders `risk_years`, `risk_low`, `risk_high`, `per_season` (pass it as text, one
  decimal), `bags_low`, `bags_high`, `next_crop`.
- `fields/<id>.json`: no new field. The "Feed your soil" plan's `check` tab (and `compared.safest` in each current option)
  has six new sentences on dhaincha (NARC's booklet, in its own words, then "Ask your agriculture office if it fits.").
  `method.choices` lists the new rules. No number changed.
- `labels/<id>.json`: four new output ids (`rainrisk_harvest`, `fertiliser_saver`, `heatclock_today`, `heatclock_2040`)
  and a new source `literature` (scale region). `checkup/<id>.json` `depends_on_corrected_rain` gains `rainrisk_harvest`.

## 2026-11-14 (Saturday, evening): a field on another continent in index.json (additions only)

Owner's item 3 ("global, usable everywhere"). `fields/<id>.json` and every Nepal entry of `index.json` are unchanged.

- **`index.json` `fields[]`** may carry two optional keys, only for a field built on the global defaults (no country
  profile in `config/countries/`; written by `pipeline/export/build_index.py`):
  - `profile`: always `"default"` when present.
  - `note`: `{en, ne}`, one line for the field list, e.g. "A field on another continent. Built with the global
    settings, not checked against local rain gauges yet." (the Nepali is Claude's draft, not reviewed).
- The first such field is `ambohidratrimo` (Madagascar). Its labels say NOT YET VERIFIABLE (no country scorecard); its
  replay's droughts are calendar years (no `event_season`).
- **`fields/<id>.json` `method.season_detection` may be `null`** (schema: object or null): a field with no year of 90
  clear satellite images (rules.yaml `season_detection.no_dense_years`) uses the threshold method with no held-out
  comparison, so there is nothing to show. The site already skips it (`if (sd && sd.methods)`).
- On such a field the third plan may keep **less cover than today** (rules.yaml `plans.third_plan_fallback`: no other
  rotation keeps it); its `score.cover` is shown as computed. Nepal's fields never use it.
- A third plan with no legume has `name` **"Safest in bad years"** (decision 5's name; rules.yaml
  `plans.third_plan_name_no_legume`), not "Feed your soil". The site's `planName()` reads the words node
  `lbl.what_to_grow.plan.safest` by id, so it needs a hook to show it (see the field's note in docs/DEPLOY_ANYWHERE.md).
- Also only for a field on the global defaults (Nepal's files are byte-identical, VALIDATION 3.26):
  - **`fields/<id>.json` `method.choices_note`** (new, optional string): the stated choices are the whole project's,
    written for the Nepal fields, and which do not apply to this field. English, technical, as the choices.
  - **`pulse/<id>.json` `typical` is `[]`**: Nepal's slots ("monsoon", "winter") and dates counted from 1 January do not
    fit a rainy season that crosses the new year. The Field Pulse screen then shows no typical seasons.
  - **`labels/<id>.json`**: no DHM source in any output's `sources`; `sources.ghcn` is the field's own station and
    `sources.crop_calendar` its FAO zone. `rain_corrected` is `false` wherever the field's own rain was not corrected
    (its weather card), for any field.
  - **`validate --final`** does not ask a field with `profile: "default"` for `replay/`, `simple/`, `rainrisk/`,
    `fertiliser/`, `heatclock/` or `basemap/` files (`validate.NOT_ON_DEFAULTS`): the site says "not ready yet".

## 2026-11-14 (Saturday, evening): launch files: map pictures, a version stamp, and the probe replay's date and lines (additions only)

The owner wants no outside request at runtime. `fields/<id>.json` is unchanged.

- **`data/basemap/<field>.json` and `data/basemap/world.json`** (new; `basemap_schema.json`, made by
  `pipeline/fetch/basemap.py`). Each has `image` (relative: `data/basemap/<name>.jpg`), `bounds` (`[[south, west],
  [north, east]]` for `L.imageOverlay`), `crs` (EPSG:3857), `size_px`, `native_zoom`, `layer`, `product`, `date`,
  `resolution`, `attribution`, `chosen_by` and `source`.
  - The demo's five fields share `demo.jpg`: NASA HLS, 11 Nov 2025, 32 KB.
  - `world.jpg` is Blue Marble, August 2004, 192 KB.
- **`data/version.json`** (new; `version_schema.json`, written by `scripts/final_check.py`). It has `commit`,
  `commit_short`, `commit_date`, `checked_on`, `uncommitted_changes` and `made_by`.
  - It is for the How-we-know page.
  - It may be missing until `final_check` has run: show nothing then.
- **`data/probe_log.json`** (still absent until real readings exist) gains:
  - `recorded_on`: the readings' local dates. The `note` now starts "Recorded on <date>".
  - `place`: where it was recorded, in the team's words, or null.
  - per part, `lines`: the reading's 30 probe lines, `{time, moisture, temp, phase: settle | measure}`.
- **Fonts:** `site/fonts/` holds the four woff2 files the site used from Google Fonts, with their licences. The site
  agent wires them in.

## 2026-11-14 (Saturday, evening): four new files for the farmer's question (additions only; fields/<id>.json unchanged)

"What can I grow in my field's empty months without risking the harvest I depend on?" Four new files per prepared
field (demo, sample-1..4), each with its own schema in `pipeline/export/` and checked by `validate --final`:

| File | Schema | What it holds |
| --- | --- | --- |
| `data/labels/<id>.json` | `labels_schema.json` | Two labels on every number: `outputs.<output_id>` = `sure` (verified / estimate; verified only when the scorecard says VERIFIED), `status`, `k`, `n`, `scale` (field / neighbourhood / valley / region), `rain_corrected`, `sources`; `scales` with en, ne and "about" words. 46 output ids |
| `data/replay/<id>.json` | `replay_schema.json` | The 25-Year Replay: each plan and current option, the next 3 and 6 months from a fixed `start`, run through every past season (`year_count`, 24 on the demo) from a dry, medium and wet start; per season `result` worked / struggled / failed, `score` (WRSI 0-100), `reason` code, `enso`, `sensitive`, `other_versions` |
| `data/pulse/<id>.json` | `pulse_schema.json` | Field Pulse: HLS and MODIS greenness points, the weekly smoothed curve, the seasons, the bare threshold, the typical planting / harvest dates, and `nearby` (demo only) |
| `data/checkup/<id>.json` | `checkup_schema.json` | Data Check-up: the field's own break test, the evidence items, the correction, the rain versions, a yearly gpm / twin / chirps series, and `depends_on_corrected_rain` (output ids of labels) |

- Every key is described in `notes/ui_note.md` section "Four new files". Words are not in these files: render the codes.
- `scripts/check_site.py` refuses any absolute path or outside address inside these four folders.
- The labels' statuses come from this run's scorecard (`scripts/run_verification.py`); `labels` runs after it and
  refreshes the `label` blocks inside the other three files.

## 2026-11-14 (Saturday, afternoon): a third rain version in the range; groundwater out of the water score (owner's decisions)

- **The central rain is now gauge-tuned:** the break-corrected GPM rain times 1.053 in June-September and 0.746 in the
  other months, fitted on four DHM gauges, June 2023-December 2025 (VALIDATION 3.9e). Every `harvest`, `score`,
  `future` value uses it.
- **New optional fields, same shapes as the dhm ones:** `replay.<plan>[].untuned_rain`, `plans[].score_untuned_rain`,
  `plans[].future_untuned_rain`, and the same two in `current_options.options[]`. They hold the break-corrected rain
  without the gauge factors (the central case until today). Present only where they differ.
- **How to show it:** the range is the min and the max over the central value and every alternative present
  (`dhm_rain`, `untuned_rain`), e.g. "about 63 to 67".
- **Groundwater no longer changes the water score** (owner: background only). `diary.groundwater` is unchanged and
  stays as regional context.
- `diary.shift_note` now says exactly "No clear change since 2001, in Nepal's weather office records." (the owner's
  words); the cross-check sentence moved to the How we know text.

## 2026-11-14 (Saturday, 10:00): the second rain version is now the DHM-scaled dry edge (owner's decision 4b): renamed fields

The owner kept the break-corrected rain as the central case. The other edge of every range is now the rain scaled month
by month to DHM Bhaktapur's 1991-2020 normals (it reads lower). It is no longer GPM as published, which carries the
known 2017 data break; that run stays in data/checks only.

| Before | Now | What the UI must do |
| --- | --- | --- |
| `replay.<plan>[].uncorrected_rain` | `replay.<plan>[].dhm_rain` (same inner shape, present only where it differs) | Show it as the other edge of a range ("about 69 to 72"), never as a second result |
| `plans[].score_uncorrected_rain`, `current_options.options[].score_uncorrected_rain` | `score_dhm_rain` | The same |
| `plans[].future_uncorrected_rain` (and per option) | `future_dhm_rain` | The same, for the 2040 range |
| evidence tab line "Without our rain fix, it was N." | "With the nearby station's rain level: N." | Nothing (text comes from the file) |

Wording for the range: "The lower edge uses the nearby station's long-term rain."

## 2026-11-14 (Saturday, 05:45): the 2040 outlook is real; the monsoon's start comes from DHM's official record

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `future` | `null`, named in `mock` | real: `years` `[2040]` (the period 2026-2040, `period`), `models` (the NEX-GDDP-CMIP6 climate models used), `scenarios` (`ssp245`, `ssp585`), `nothing_changes` (the current plan), `with_plan` (Fill the empty months), `words` (en, ne) on what the range means | Show it on the "How we know" page (owner: the design has no 2040 screen). Label the years "by 2040". Show the range and the `words` |
| `plans[].future`, `current_options.options[].future` | absent | each plan's and option's own `{harvest, harvest_low, harvest_high}` in whole points | Compare with that plan's `score.harvest` (today). Say "about the same" when today sits inside the range |
| `plans[].future_uncorrected_rain` (and per option) | absent | the same on GPM rain as published, only where it differs | Show as a wider range, like `score_uncorrected_rain` |
| `mock` | `["future"]` | `[]`: nothing is sample data any more | Nothing says "not ready yet" |
| `diary.shift_days` | `null` ("can't tell") | **from DHM's official onset dates 2001-2024**: `-2.2` days, with `shift_days_low` `-11.5` and `shift_days_high` `7.7` | Say "no clear change since 2001" (`shift_note`), never "2 days earlier" |
| `diary.shift_source` (new) | absent | a source object for DHM's record (`type` `station`) | Credit DHM next to the answer |
| `diary.shift_note` (new) | absent | `{en, ne}` plain sentences: no clear change since 2001, from Nepal's weather office | Show on the diary screen |
| `diary.monsoon_start` (new) | absent | `{usual_from "06-10", usual_to "06-16", median "06-13", late_after "06-20", late_years [2009], late_share 0.042, years [2001, 2024], source "DHM", words {en, ne}}` (entry into eastern Nepal; Kathmandu a few days later) | Show `words` on "Next 3 months" in June-July and on the diary screen |
| `method.onset` (new) | absent | `{words {en, ne}, caveat}`: two satellite-rain methods tested; the 2017 gauge loss made them unreliable for trends; Nepal's official record used | Show on "How we know" |
| `sources[]` | 9 rows | + DHM onset dates, + NEX-GDDP-CMIP6 (`type` `model`) | Nothing new |

## 2026-11-14 (Saturday, 01:45): `live.json` settles, then measures; `probe_log.json` has a schema (owner's probe brief)

`site/data/live.json` exists only during the in-person demo (git-ignored). The bridge (`robot/bridge.py --sections
s1,s2,s3,s4`) now writes it only when a part's state changes, never every 2-second line. `probe_log.json` (the public
replay) is built only from real sessions and follows `pipeline/export/probe_log_schema.json`. Neither file exists yet:
the team's bench test comes first.

| `live.json` field | Meaning | What the UI must do |
| --- | --- | --- |
| `section`, `part`, `parts_total`, `time` | which part is being read (e.g. part 2 of 4), local time with UTC offset | "Part 2 of 4" |
| `state` | `settling` / `measuring` / `done` / `test_again` | settling and measuring: a waiting animation, no number. test_again: "The reading jumped. Please test again." |
| `steady`, `spread_pct`, `n` | the 10 measured lines agree within 3 points (rules.yaml probe) | Show a number only when `steady` |
| `off_scale` | the median is 0 or 100 (the probe's limits) | "Off the scale", never as a value |
| `wetness` | the settled median on the probe's own 0-100 scale (air 0, water 100); null unless done, steady and on scale | "drier / wetter than the other parts" (see `relative`) |
| `relative` | `drier` / `wetter` / `about the same` / null, against the other parts read in this session | The word, with a picture |
| `water_pct`, `give_or_take_pct` | soil water in % of volume, from the bench calibration, and its error; **null until the bench test** | "about 24% water, give or take 3" only when not null |
| `band` | `needs water` / `good` / `too wet` / null, from the field's own soil and the crop growing now; **null until the bench test** | The word with its face and caveats |
| `temp`, `temp_steady` | soil-probe temperature, null unless its 10 lines agree within 0.5 C | "not sure yet" when null |
| `sure`, `fused_wetness` | the Kalman update of the twin; **null until the bench test** gives the probe's error | Fog clears as `sure` rises |
| `prior` | `{wetness, sure}`: the twin's estimate before this reading; `twin_date` its date | "Before: …" |
| `caveats` | plain lines to show with any number (soil cell 859 m away; the probe reads only the top few cm) | Show them under the number |
| `parts` | `[{section, state, wetness, water_pct, band, sure, relative}]`: every part read so far | The map of parts fills in as the probe walks |
| `source`, `stale`, `stale_reason`, `stale_since`, `note` | `stale: true` when the cable is pulled or 10 s pass with no line | Grey the live view and say "probe not connected" |

## 2026-11-14 (Saturday, 01:30): the four parts are real (build step 8, owner's group 2a)

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `field.sections` | 36 grey 10 m squares, no numbers | **4 parts of about 30 m** (2 x 2; `s1` south-west, `s2` south-east, `s3` north-west, `s4` north-east), each about one HLS pixel. `status` and `wetness` come from the field twin's soil water on `field.status_date` (all four share one twin: the same soil and weather, so the same numbers). `sure` is the twin's own sureness before any probe reading (0.22 today). `temp` stays null until the probe reads that part. `greener`: `s3` "more", `s2` "less", `s1` and `s4` "same". `low_ground`: null in every part (NASADEM cannot tell on this flat valley floor) | Lay out 4 parts, not 36. Show "as of <status_date>". Draw `sure` as fog. `greener`: the difference is small (about 0.006 NDVI, mostly in winter), so say "a little greener" / "a little less green" |
| `field.status_date` | absent | `"2026-11-03"`: the latest day with both NASA POWER and IMERG Late weather | Show "as of 3 November" |
| `mock` | `["field.sections", "future"]` | `["future"]` | Only the 2040 outlook still says "not ready yet" |

## 2026-11-14 (Saturday, 00:40): room for real sections and the 2040 outlook (build steps 8 and 9)

All new fields are optional, so a site built against the old shape still works. They fill in when steps 8 and 9 land
(Saturday). Then `mock` becomes empty.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `field.sections[].low_ground` (new, optional) | did not exist | `true` / `false` / `null`. True means this part lies lower than the land around it (NASADEM 30 m), so cold air can collect on still nights | Show a small "low ground" mark (a picture and a word, never colour alone). `null`: show nothing |
| `field.sections[].greener` (new, optional) | did not exist | `"more"`, `"less"`, `"same"` or `"unknown"`: how green this part usually is next to the rest of the field, from its own HLS 30 m pixels over many seasons (a test fixed in advance says when a difference is real) | `more`/`less`: a small leaf mark with "greener than the rest" / "less green than the rest". `same`: nothing. `unknown`: "we can't tell" |
| `field.status_date` (new, optional) | did not exist | `"YYYY-MM-DD"`: the day of the field twin's soil water behind every section's `status` and `wetness` (the latest day with weather data) | Show "as of <date>" on the screens that show sections |
| `plans[].future`, `current_options.options[].future` (new, optional) | only `future.nothing_changes` and `future.with_plan` | each plan's own `{harvest, harvest_low, harvest_high}`, one value per entry in `future.years` | On the 2040 screen, show the plan the farmer picked: its own `future`. `nothing_changes` stays the current plan (the default option); `with_plan` stays the first suggested plan |
| `plans[].future_uncorrected_rain`, `current_options.options[].future_uncorrected_rain` (new, optional) | did not exist | the same outlook on GPM rain as published (without the 2017 fix) | Show it as a range beside `future`, like `score_uncorrected_rain` |
| `future.period`, `future.models`, `future.scenarios`, `future.words` (new, optional) | did not exist | `"2026-2040"`; the climate models and the two scenarios behind the range; `words`: `{en: [...], ne: [...]}`, plain sentences on what the range means | `years` holds the period's last year (`[2040]`): label it "by 2040". Show `words` under the dials |

## 2026-11-13 (Friday, 18:00): the soil source shows its neighbourhood; `live.json` time carries its UTC offset (owner's answers 10, 19)

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `sources[]` SoilGrids `product` | "...; nearest cell with values, 859 m from the field" | adds "Water it holds for plants in the top 1 m: 149 mm; the 56 cells within 2 km of the field hold 149 to 187 mm" | Nothing (longer text) |
| `site/data/live.json` `time` (in-person demo only; the file is git-ignored) | `"2026-11-14T10:32:00"` | `"2026-11-14T10:32:00+05:45"` (local time with its UTC offset) | Parse it with `new Date(...)`; do not assume UTC |

## 2026-11-13 (Friday, 17:45): two SI additions: a "less sure" signal per month, and the field-memory test on the method page

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `diary.months[].cover_sure` (new, optional) | did not exist | a number 0 to 1, like a section's `sure`: how often our two ways of reading the seasons (the rule method and the SI "season detective") agree in that month. Demo: June 0.80, the other months 0.91 to 1.00 | Show a month with a lower number as less sure (a little fog, as for sections); words.json screen 3 `month_less_sure`: "We are less sure about this month." Never hide the month's `cover` word |
| `method.field_memory` (new, optional) | did not exist | `{kept, seasons, years, error: {no_anomaly, physics_only, memory}, words: {en, ne}}`: we tried to teach a small model this field's habits and tested it on years it had not seen. Demo: `kept: false` (it did not beat the simple water count), 24 seasons, 12 years | Show `words` on the method page, whichever way it went. An honest "it did not help" is part of the method |

## 2026-11-13 (Friday, 17:30): the farmer confirms the winter crop: `current_options` (owner's answer 6)

From space the winter crop of the demo field could be potato or wheat: the timing cannot tell them apart. So screen 3 asks
the farmer, and the file holds the current plan's results for both answers. Nothing is simulated in the browser.

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `current_options` (new, top level, optional) | did not exist | `{"default": "rice_potato", "options": [{...}, {...}]}`. Each option: `id` (`rice_potato`, `rice_wheat`), `crops`, `score`, `score_uncorrected_rain` (where it differs), `tabs`, `tips`, `tabs_ne`, `tips_ne` (the current plan's own texts), `replay` (24 years in the shape of `replay.current`: both water cases, the `uncorrected_rain` ranges), and `compared`: for each suggested plan id, its `tabs` and `tabs_ne` when it is compared with this current plan. Absent when the rotation is known | Screen 3: ask "We think you grow rice first. Then potato or wheat. Which one do you grow?" (words.json screen 3: `guess_first`, `guess_options`, `guess_which`, `guess_cannot_tell`; crop names from `shared.crop_names`). On the answer, show that option as the current plan (its crops, score, tabs, tips, replay) and, for `cover_gap` and `safest`, the tabs from the option's `compared` (their gains differ). Their scores, crops, tips and replays do not change. Before an answer, show the `default` option, which is exactly what `plans[0]` and `replay.current` hold |
| `plans[].tabs.unknown` | | one more line while the winter crop is not confirmed: "Your winter crop dates may differ from ours." | Nothing |

The wheat option sows wheat on 15 November (the latest date in FAO's Hill-zone window); the satellite's winter season is
still about 78 days from it (later start, later end), which is what the new "unknown" line is about. When the farmer picks
wheat, "Fill the empty months" is also rice then wheat, sown a month earlier: the two plans then differ in their dates
only (flagged for the owner).

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
