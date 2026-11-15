# Khet Sathi: the 30-second video

Written 14 November 2026 (afternoon); shots 3 to 8 updated that night to match the final app (the farmer's four
answers, and the field twin on "How we know"). About 87 spoken words: brisk but clear. If a take runs long, shorten the
Record Check-up line first. Every number is in `docs/PITCH_FACTS.md` (IDs in square brackets) or the file named in the
Facts column: check them there before recording. Screens come from the live site, designed by our UI teammate. The field on
screen is Kharipati, a real farm in Kharipati, Bhaktapur; its crops are placeholders, so keep the app's placeholder chip
(today "Sample field") visible whenever it is on screen.

## Shot list

| Time | Shot (what we see) | Voice | Text on screen | Facts |
| --- | --- | --- | --- | --- |
| 0:00-0:04 | **Hook.** Satellite view of Bhaktapur. The area map's bare-days layer fades in, square by square (`site/data/area/kharipati_bare_days.png`). | "About 15 in 100 farm squares near Bhaktapur sit bare over two months a year." | Seen from space: 15% of cropland bare over 60 days a year · range 0-31% · NASA HLS, 30 m, 2014-2025 | A2, A6 |
| 0:04-0:08 | **The question.** A phone in a farmer's hand at a field's edge (no face needed). The question on screen, Nepali first. | "What can I grow in my empty months, without risking the harvest I depend on?" | The full question in Nepali, then English | B1 |
| 0:08-0:12 | **The field twin** (How we know, for judges). Its three pictures, then the 10-second animation: one small field per plan steps through the seasons, ticks and crosses; it ends "Works most often: Fill the empty months." | "We replay 24 years of NASA weather on each plan." | 24 past seasons · each season is an estimate | B3; `site/data/simple/kharipati.json` `animation` |
| 0:12-0:15 | **Four answers.** The "What do you want to see?" screen: four big cards. | "Then four short answers, in plain words." | Your field today · Next 3 months · Next 6 months · Weather ahead · no numbers on farmer screens | `site/js/app.js` `SCREENS.choose` |
| 0:15-0:18 | **What to grow.** Next 3 months: "Our suggestion", Wheat, "Usually better than now.", then its actions in Nepali months; a thumb taps "Try it in one part first" and one of the 9 parts lights up. Quick cut to Weather ahead's first paragraph. | "What to grow, and what each month usually brings." | Usually better than now · try it in one part first · Weather ahead: not a forecast | E1, E4, O1; `site/data/simple/kharipati.json` `plan_words`, `actions` |
| 0:18-0:24 | **Record Check-up** (How we know). The gauge-share chart: a flat line near 97%, then a drop in 2017. CHIRPS stays level beside it. | "Record Check-up: from 2017, far fewer gauges fed NASA's rain here. We corrected for it." | Gauge share 96-98% → 56-72% a year · CHIRPS: no step · every field runs its own check | F1, F4, F7, F13 |
| 0:24-0:27 | **Two labels** (How we know). One number with two chips beside it: "Estimate" and "Your field". | "Every number says how sure, and how close." | How sure · How close | G1, G5 |
| 0:27-0:30 | **Close.** The end of Next 3 months: "You know your land best. Talk to a farm advisor before changing." Then the home screen. Logo. | Version A (today): "Free, and made for any field on Earth." | Free · no app, no account · global NASA data · "You know your land best." | I2, I4 |

**Version B of the last line, only if the offline feature has landed** and has been tested on a phone in flight mode
(PITCH_FACTS I6): "Free, works offline, and made for any field on Earth."

## Rules for the edit

- Keep the hook's range on screen (0-31%) while the voice says "about 15 in 100".
- "Made for any field on Earth", never "works anywhere" or "proven worldwide": the field in Madagascar is on the site,
  but its answers for the coming months are not made yet (PITCH_FACTS I4; `site/data/index.json`).
- No El Niño number, no probe accuracy, no "worked / struggled / failed" counts, no money (PITCH_FACTS section K). The
  animation shows its own tally under each field: keep it on screen only, never in the voice.
- No robot or drone does anything on screen or in the voice. The soil stick is a prototype carried by hand; the robot
  (Krishi Scout) is only drawn. The field's picture is an open drone map (Kharipati, OpenAerialMap, 5 May 2026),
  standing in for our future drone: never say our drone took it. We do not use the phone-as-drone demo mode. The public site has no soil-stick readings yet ("Not
  tested yet"); show readings only if real and dated, with their label (a garden or indoor test says so). Never film
  the "Practice: made-up numbers" screens as if they were real.
- The rain check is a check, not a fault: "far fewer gauges fed NASA's rain here", never "NASA's data is wrong".
- No farmer's face or name without their written consent. A hand and a field are enough.
- Captions in English on the video; the app itself shown in Nepali, as farmers will see it.

## Spare lines (if a shot runs short)

- "Harvest is out of 100 of what the field could grow. Never tonnes." (PITCH_FACTS H1)
- "Only about 4 in 10 farm squares here grow two crops a year." (PITCH_FACTS A4; keep "could be 2 to 5 in 10" on
  screen)
