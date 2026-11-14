# Design wording changes: where the app's words differ from the design

For our UI teammate. The site in `site/` follows your seven-step design (`design/screens/`, phone and web, version
1794632161-9240). It keeps your layout, frosted glass, the #D27A2C accent and your animations (owner, 2026-11-14 evening).
Where our records support your words, we kept them. Where they do not, we changed the words, not the design. Each change
is listed below: the screen, your words, ours, and why.

Rules behind most changes:

- **Honest.** No drone photo and no soil robot exist yet. A person carries the prototype soil stick. No screen may say a
  robot or a drone did anything.
- **Plain words.** "Data" is on the list of words never shown to farmers (`pipeline/words/glossary.json`
  never_on_screens), so it becomes "records". No sentence on screen has more than 8 words, in English or Nepali.
- **Text only.** There are no listen (speaker) buttons, by the owner's decision of 2026-11-12: "text only: no audio".
- **No made-up numbers.** Every number comes from the files in `site/data/`.
- **Simple and accurate (owner, 2026-11-14 evening).** Each farmer screen answers one question. No numbers, years, counts,
  percentages, squares or charts on the farmer's screens; those are on "How we know", for judges. The back end picks
  every sentence (`site/data/simple/<id>.json`), worded by each output's label: "usually" or "may" while it is an
  estimate, never a promise. Months are Bikram Sambat in both languages ("Kartik", "कात्तिक").

All new Nepali is marked "needs native-speaker review" (`pipeline/words/screens.json`).

The screenshots are in `/Users/paritoshbhattarai/Desktop/khet_sathi_screens/`, named after your boards. For example,
`3_Parts_phone_en.png` matches Parts and `W3_Parts_web_en.png` matches W3_Parts.

## Everywhere

| Your design | Ours | Why |
| --- | --- | --- |
| Listen button (speaker) | Not shown | Owner, 2026-11-12: text only, no audio. |
| Language switch "EN / नेपाली" | Same order, plus "···" for the five draft languages | The owner asked for draft languages earlier. Nepali is still the first language the site opens in. |
| — | "Sample field" tag on the screens about the field | The field is our sample (a placeholder), so every screen about it says so. |

## 1 Home (Main, W1_Home)

| Your words | Ours | Why |
| --- | --- | --- |
| Know your land. / Plan your season. | Kept | |
| Soil robot (card tag) | Soil check / माटो जाँच | No robot tests the soil yet. |
| Today / How each part of your field is doing | Kept | |
| NASA data (card tag) | NASA records / नासाका अभिलेख | "Data" is not a farmer word. |
| 3 months / What is coming, and what to grow | 3 months / What these months usually bring. | We show the usual months (2001-2025), not a forecast. |
| Stand in your field. Tap below. / Our drone takes a photo. Our robot checks the soil. | Let's look at your field together. / We help you think. You decide. | The site shows our sample field, not the place where the phone is. There is no drone photo or robot yet. |
| Card caption: Our robot drives to every part… | Space sees wide. Your stick sees close. Together they make a better guess. | No robot yet. |
| Card caption: We read 20 years of NASA satellite records… | What these months usually bring. | No years on the farmer's screens. |
| Show my field | Try our sample field (+ "We picked this field as an example.") | The field shown is our sample. |
| — | "Prepared fields", folded (the other sample fields, and a field in Madagascar with its note) | CLAUDE.md: a short list of prepared fields. |
| — | A small link: "For judges: how we know" | Owner: How we know is for judges only; no button on the other farmer screens. |
| Web: USES NASA OPEN DATA | USES OPEN NASA RECORDS | "Data". |
| Web nav: How it works · Our data · Krishi Scout | The small judges link | Everything for judges is on that page. |
| Web floats: Drone photo / A top view of your farm | NASA map / A top view of your farm | The picture is NASA's map, not a drone photo. |
| Web floats: Soil robot / Tests every part | Soil check / How each part of your field is doing. | No robot yet. |
| Web floats: NASA data / 20 years of records | NASA records / 3 months | "Data"; our records are 2001-2025. |
| Web floats: Next 3 months / What to grow | Kept | |
| Web: Hover a card to see what each part does. | Not shown | The floats are pictures only. |
| Web strip: Drone + robot / Your field, seen and tested | Soil check / How each part of your field is doing. | No drone or robot yet. |
| Web strip: Satellite history / 20 years of NASA data | NASA records / What these months usually bring. | "Data"; not a forecast. |
| Web strip: Farmer first / You stay in charge | Farmer first / We help you think. You decide. | Our reviewed sentence says the same. |
| Web: Free to use. Built for Nepali farmers. | We picked this field as an example. | Honest about the sample field. |

## 2 Photo from above (Photo, W2_Photo)

| Your words | Ours | Why |
| --- | --- | --- |
| Your farm / from the sky (आकाशबाट / तपाईंको खेत) | Kept | NASA's map is from the sky. |
| Drone photo | NASA's map picture of the field (HLS, via NASA GIBS), with the field's outline | There is no drone photo yet. A real photo replaces the map when it arrives. |
| The drone photo will show here. | A real photo comes when we visit. | This shows only if the map cannot load. |
| Is this your farm? / Next, we split it into small parts. | Kept | |
| — | "We think you grow rice, then potato. Is that right?" with "Yes" and "Rice, then wheat" (+ "From space, both look the same.") | Owner: the crop guess becomes a question. The answer stays on the phone and picks the plan words and weather lines. |
| — | One line from Field Pulse: "Your field rests in: Mangsir" (Nepali "मंसिर"), plus "Nepali and English months don't line up exactly." | Owner's brief. The months come from `site/data/simple/<id>.json` pulse_card. A Bikram Sambat month (from the 15th) counts as resting when most of its days fall outside every growing period. |
| Take the photo again (round button) | Mark my own field (round button, pin) | There is no photo to take again. The farmer can mark a field on the map. |
| Yes, make the parts | Kept | |

## 3 Your farm's parts (Parts, W3_Parts)

| Your words | Ours | Why |
| --- | --- | --- |
| Your farm, / in 4 parts | Kept, with the number of parts from the field file | |
| Making the parts… / Here are the 4 parts. | Kept | |
| The robot will take soil from the middle of each part. | We test the middle of each part. | No robot yet. |
| Start robot test | Start the soil test | No robot yet. |

## 4 Soil test (Robot, W4_Robot)

The robot drawing and its walk are kept, as the plan (Krishi Scout). The walk is the real one: `live.json` during the
in-person demo, else the recorded walk (`probe_log.json`). With neither, nothing moves and every part says "Not tested yet".

| Your words | Ours | Why |
| --- | --- | --- |
| Robot is / testing the soil | Your soil, / part by part (तपाईंको माटो, / भाग भाग गरी) | A person carries the prototype stick, and on the public site no part is tested yet. |
| Waiting | Not tested yet | |
| Testing… | Settling… then Measuring… | The stick's two real steps (`live.json` state). |
| Tested ✓ | Kept | |
| — | Test again | When the reading jumped (`live.json` state test_again). |
| 2 of 4 tested (the waiting button) | Tested: 2 / 4 | Shown only while a part is settling or measuring. |
| — | Our soil stick is a prototype. Today we carry it by hand. A robot to carry it comes next. | Owner's brief: honest words. |
| — | Readings come after our team tests it. / Recorded on <date> · <place> / Garden test of our soil stick, recorded on <date> / Indoor test of our soil stick. 4 bowls of soil, recorded on <date> / Practice: made-up numbers | No readings yet, real readings with their date, or the garden test. Practice readings show only at the in-person demo, under a big banner; there is no "Tested: n / N" count (owner, 2026-11-14 night). |
| See what to do | Kept; also shown when nothing is tested | The public site has no readings yet, so the farmer must still be able to go on. |
| Web: round "refresh" button | Shown only with a recorded walk: "Watch a soil check we did earlier." | |

## 5 What next (Choose, W5_Choose)

| Your words | Ours | Why |
| --- | --- | --- |
| Soil tested. / What next? | Kept when a part was tested; otherwise "What do you / want to see?" | Honest when nothing is tested. |
| From the robot | From the soil test | No robot yet. |
| Your field today / How each part is doing, and what to fix now. | Your field today / How each part of your field is doing. | Your sentence has 10 words; the limit is 8. |
| From NASA data | NASA records | "Data". |
| Rain and cold ahead, and what crops to grow. | Three choices: what to grow, and when. | The month screens now hold the plans only; the weather is on "Weather ahead". |
| NASA data + soil test | NASA records | The 6-month plans do not use the soil test. |
| Two crops in a row, so your field is never empty. | Three choices: what to grow, and when. | Our plans do not always fill every month. |
| Coloured month chips | Bikram Sambat months from this one ("Kartik Mangsir Poush"), coloured by our suggestion's crops; empty months stay plain | From the plan's crop calendar. A field abroad keeps Gregorian months. |
| Four soil swatches | Coloured by each part's reading, plain when not tested | From the probe. |

## 6a Your field today (Today, W6_Today)

One line per patch (owner, 2026-11-14 evening), in your cards, numbered 1 to 4.

| Your words | Ours | Why |
| --- | --- | --- |
| Good / Needs water / Too wet + the to-do list | Before the stick's cup test passes: "Patch 3 is drier than the others. Water it first." / "Patch 2 is wetter than the others. Water it last." / "Patch 1 is like the others." After it passes: "Patch 3 is dry. Water it today." / "Patch 1 is fine. No water needed." / "Patch 2 is too wet. Don't water it." | `simple.today.mode` says which (compare now). The to-do list is gone: each line says what to do. |
| A bit dry | Not used | The probe has no such band. |
| — | "Patch 4 is not tested yet." (+ "Start the soil test") | A patch with no reading. |
| — | No "water in the soil: 23%" | No numbers on the farmer's screens. |
| See the next 3 months | Kept | |

The computer's guess for each part (the field twin) is on "How we know".

## 6b and 6c Next 3 months and Next 6 months (Future, Future6, W7, W8)

Both screens now show the same thing for their own window: our three plans, in plain actions.

| Your words | Ours | Why |
| --- | --- | --- |
| From 20 years of NASA data and your soil test. / the month rows / the weather tiles | Not shown | Each screen answers one question: what to grow. What the months usually bring is on "Weather ahead". |
| Best to grow now | Our suggestion (the plan with the best word against the farmer's own plan) | |
| Lentil (masoor) | Our suggestion's new crop (demo, potato grower: Wheat) and the plan's name | |
| Needs little water / Makes your soil better / Ready by March | "Usually better than now." then "Wheat is usually sown in Kartik." "Wheat is usually harvested in Falgun." "Then rice is usually planted in Asar." | Owner: one word per plan against the farmer's own ("Usually better than now." / "About the same as now." / "Usually worse than now." / "Sometimes better, sometimes worse."), and plain actions with Bikram Sambat months. No "X of 10 winters". |
| — | Try it in one part first (button) | Opens the Safe Trial in your sheet. |
| Other choices: Mustard (tori) / Sells well, but needs more water. | Our other plans, each with its word, its actions and the same button | We have no price records. |
| Leave it empty / What you do now. No income for 3 months. | What you do now: its actions, no word | The farmer's own plan gets no word. |
| Your plan: two crops / Step 1, Step 2 / Your field over 6 months | Not shown | The actions say the same in words; no charts on the farmer's screens. |
| You know your land best. Ask your local agriculture office before you sow. | You know your land best. Talk to a farm advisor before changing. | Our reviewed sentences. |
| Done | Kept | |

## Added on 14 November, evening (owner's requests; not in your boards)

These are new, so there are no words of yours to change (where the owner's own lines were shortened, see the last
section). They use your styles: a fourth big card on Choose, frosted glass cards, your sheet.

| Where | What it shows | Why |
| --- | --- | --- |
| Choose (W5_Choose) | A fourth card, "Weather ahead" / "What each month usually brings.", with its six Nepali months. On the web the four cards sit in one row. | Owner. It shows only on fields that have these records (Nepal). |
| Weather ahead (new) | "What each month usually brings. Not a forecast." Then this month and the five after, each one short paragraph: "Mangsir: usually dry, cold. Cold nights may hurt potato. Cover young plants on clear, cold nights. Check with your local expert." No numbers and no Why? button. | Owner, 2026-11-14 evening. The back end picks each sentence for the farmer's crop and water answer. The details are on "How we know". |
| How we know (for judges) | First the field twin in three pictures ("We copy your field into a computer." / "We replay 24 years of NASA weather. Each crop plan, in every year." / "We keep the plan that works most often. Then we tell you what to do."), then a ten-second animation: one small field per plan steps through the 24 seasons, green with a tick when the plan did not fail, red with a cross when it failed, then the winner. Then every label with its why, then the evidence. | Owner. It replaces the separate "How we test each plan" page and the home line about it. |

## Moved off the farmer's screens, onto "How we know"

The judges' page now holds, written simply (after the three pictures, the animation and the labels):

- the three plans' full details (scores, the five tabs, tips): each plan's sheet;
- Weather ahead's details for each month (in how many of 24 years, is it changing, rain, temperatures, dry runs, frost,
  sources);
- the prepared fields;
- the farmer-card comparison ("How we compared": better, same or worse in each past winter, rain-fed and watered, with
  "Better means more water need met by rain. Not price, not labour, not taste.");
- the Replay's 24 squares;
- the Record Check-up;
- rain at harvest, heat and cold, and the fertiliser saver;
- the computer's guess for each part;
- Field Pulse;
- the two labels (how sure, how close) for every number, and the sources.

## Weather ahead and How we test each plan (owner, 2026-11-14 evening)

The owner's own lines, and the spec's words, changed only where a rule required it. (Later the same evening the home
line and the explainer page were replaced by the three pictures on "How we know", and the Weather ahead blocks became
one paragraph each; the rows below record the words as first changed.)

| Where | Asked for | On screen | Why |
| --- | --- | --- | --- |
| Weather ahead, top line | "What usually happens here, from 24 years of records." | "What usually happens here: 24 years of records." | 9 words; the limit is 8 |
| Home, one line | "We tested each plan in 24 years of your field's weather." | "We tested each plan in 24 past years." | 11 words; the limit is 8 |
| Weather ahead, danger | "Heavy rain" (20 mm or more, the spec) | "Big rain" | DHM calls only 50 mm or more "heavy" (our rain-at-harvest check uses DHM's 50 mm); Why? gives both |
| Is it changing? | "about the same" | "No clear change." | A trend test that finds nothing has not shown "the same" (as the onset screen's "No clear shift") |
| Explainer, title | "Field Twin" | "How we test each plan" | "twin" is a glossary word, kept off farmer screens; the glossary explains it |
| Explainer, step 4 | "your probe checks the soil today" | "Your soil stick checks the soil today." | "probe" is never shown to farmers |
| Weather ahead, labels | "Usually: ...", "Watch out: ...", "Do this: ..." | the same, with the label as its own word | label and sentence each stay within 8 words |

