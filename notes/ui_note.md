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

- GitHub publishes the `site/` folder, as it is, on every push to `main` (`.github/workflows/pages.yml`). There is
  no build step on GitHub. If you use a bundler, commit its **built output** into `site/`.
- The live address is **https://sorenhgautam-dev.github.io/data-test-game/**, so the site does not sit at the
  root of the domain. **Every path must be relative**: `fetch('data/index.json')`, `src="img/x.svg"`. A path that
  starts with `/` breaks on the live site.
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

## 6. Changes still coming (each will be in CONTRACT_CHANGES.md as it lands)

- A "less sure" signal for the months where our two ways of reading the satellite disagree.

## 7. Site rules we promised the judges (from CLAUDE.md)

Ten screens, one action each. Sentences of eight words or fewer. Pictures before words; never colour alone.
Buttons at least 48 px. Designed at 360 px wide. First screen under 300 KB. Plain HTML, CSS and JavaScript;
Leaflet for the map. No sound.

If something in the file is unclear or missing, ask before working around it: a missing key is cheaper to add
on our side than to guess on yours.
