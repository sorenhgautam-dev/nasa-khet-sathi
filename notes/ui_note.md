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

- **Hosting is Vercel** (changed on 13 November; GitHub Pages is no longer used). Vercel serves the `site/` folder
  as it is on every push (Root Directory `site/`, **no build step**). If you use a bundler, commit its **built
  output** into `site/`; do not put a `package.json` in `site/`.
- The live address is **(address to be added when the owner sends it)**. The site sits at the root of that address.
- **Every path must still be relative**: `fetch('data/index.json')`, `src="img/x.svg"`, `url(../img/bg.svg)`. Never
  start a path with `/`. Relative paths work at the root, in a folder and when you open a preview address.
- **Fully static.** No Vercel functions (no `api/` folder, no `middleware.js`), no environment variables
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
