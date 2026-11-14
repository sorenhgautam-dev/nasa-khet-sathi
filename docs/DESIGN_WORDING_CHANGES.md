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
| Card caption: We read 20 years of NASA satellite records… | What these months usually bring. We read NASA records, 2001-2025. | Our records are 2001-2025. |
| Show my field | Try our sample field (+ "We picked this field as an example.") | The field shown is our sample. |
| — | How we know (button) | The page for judges. |
| Web: USES NASA OPEN DATA | USES OPEN NASA RECORDS | "Data". |
| Web nav: How it works · Our data · Krishi Scout | One "How we know" button | Everything for judges is on that page. |
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
| — | One line from Field Pulse: "Your field rests in: November" (Nepali: "तपाईंको खेत यी महिना खाली रहन्छ: मंसिर", plus "Nepali and English months don't line up exactly.") | Owner's brief. The months come from `site/data/simple/<id>.json` pulse_card. A month counts as resting when most of its days fall outside every growing period. |
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
| — | Readings come after our team tests it. / Recorded on <date> · <place> / Practice soil stick | No readings yet, a recorded walk, or a rehearsal. |
| See what to do | Kept; also shown when nothing is tested | The public site has no readings yet, so the farmer must still be able to go on. |
| Web: round "refresh" button | Shown only with a recorded walk: "Watch a soil check we did earlier." | |

## 5 What next (Choose, W5_Choose)

| Your words | Ours | Why |
| --- | --- | --- |
| Soil tested. / What next? | Kept when a part was tested; otherwise "What do you / want to see?" | Honest when nothing is tested. |
| From the robot | From the soil test | No robot yet. |
| Your field today / How each part is doing, and what to fix now. | Your field today / How each part of your field is doing. | Your sentence has 10 words; the limit is 8. |
| From NASA data | NASA records | "Data". |
| Rain and cold ahead, and what crops to grow. | Rain and cold ahead, and what to grow. | Your sentence has 9 words. |
| NASA data + soil test | NASA records | The 6-month plans do not use the soil test. |
| Two crops in a row, so your field is never empty. | Three choices: what to grow, and when. | Our plans do not always fill every month. |
| Coloured month chips | Coloured by our suggestion's crops; empty months stay plain | From the plan's crop calendar. |
| Four soil swatches | Coloured by each part's reading, plain when not tested | From the probe. |
| — | How we know (button) | |

## 6a Your field today (Today, W6_Today)

| Your words | Ours | Why |
| --- | --- | --- |
| Good / Needs water / Too wet | Kept, from the probe's band | Bands come only after the bench calibration (robot/calibrate.py, rules.yaml probe.band). None exists today. |
| A bit dry | Not used | The probe has no such band. |
| — | Drier than the other parts / Wetter than the other parts / About the same as the others | What the stick can say before the calibration. |
| — | Not tested yet | A part with no reading. |
| — | "Water in the soil: about 23%, give or take 4" | Only once the calibration exists. None today, so not shown yet. |
| Water part 2 today. | Kept, for a part whose band is "needs water" | |
| Dig a small channel in part 3 so water can leave. | Let water drain from part 3. | Your sentence has 11 words. |
| Water part 4 in 2 or 3 days. | Not used | We have no timing for this. |
| — | Test the soil first. (+ "Start the soil test" button) / We can only say which parts are drier. / The tested parts look fine today. | No readings / no calibration / all good. |
| See the next 3 months | Kept | |

The computer's guess for each part (the field twin) is now on "How we know".

## 6b Next 3 months (Future, W7_Future)

| Your words | Ours | Why |
| --- | --- | --- |
| From 20 years of NASA data and your soil test. | We read NASA records, 2001-2025. | "Data"; the months come from 2001-2025; the plans do not use the soil test. |
| Dry. Very little rain. / Very cold. Frost on some nights. / Warmer. A few showers. | From our month words, e.g. "Little rain. Some nights near freezing." (+ "We may show too many freezing nights.") | Each month is compared with the field's own 2001-2025 record. |
| Best to grow now | Our suggestion | We compare plans on water only (rain-fed winters), not on price, labour or taste. |
| Lentil (masoor) | Our suggestion's new crop (demo, potato grower: Wheat) | |
| Needs little water / Makes your soil better / Ready by March | "Rain only: better in 10 of 10 winters" (from the Replay), the crop's explainer (e.g. "Crops with deep roots"), "Wheat: harvest in March." | Owner's brief: one plain line from the Replay, rain only, 8 words or fewer. |
| — | Try it in one part first (button) | Opens the Safe Trial in a sheet: pick one part, the stick's spots, a photo each week on the phone, "after harvest, we compare". |
| Other choices: Mustard (tori) / Sells well, but needs more water. | Our other plans, each with its Replay line and the same button | We have no price records. |
| Leave it empty / What you do now. No income for 3 months. | What you do now / rice → potato (no line) | The current plan gets no line. We do not model income. |
| You know your land best. Ask your local agriculture office before you sow. | You know your land best. Talk to a farm advisor before changing. | Our reviewed sentences. |
| Done | Kept (+ How we know) | |

## 6c Next 6 months (Future6, W8_Future6)

| Your words | Ours | Why |
| --- | --- | --- |
| Weather ahead | What these months usually bring. | Not a forecast. |
| Dry / Very cold / A few showers / Warm, dry / Hot / First storms | From our month words (e.g. "Little rain", "Some nights near freezing", "Some hot days") | 2001-2025 records. |
| Your plan: two crops | One choice for these months · <plan name> | Our suggestion may hold one crop in these six months. |
| Step 1 · Dec to Feb / Step 2 · Mar to May | First / Then | From the plan's crop calendar. |
| Sow now · harvest in March | Wheat: plant in October · Wheat: harvest in March | The usual crop calendar, not the farmer's own dates. |
| Your field over 6 months: Now / This plan | Now / This choice, coloured by crop, with a legend | |
| No empty months. Two harvests before the rice season. | Empty months: Now 3 · This choice 3 | Counted from the plans. |
| — | The Replay line and "Try it in one part first" | Owner's brief. |
| Other choices, note, Done | As on 6b | |

## Added on 14 November, evening (owner's requests; not in your boards)

These are new, so there are no words of yours to change (where the owner's own lines were shortened, see the last
section). They use your styles: a fourth big card on Choose, frosted glass cards, your sheet. Screenshots: `5_Choose_*`, `6d_WeatherAhead_*`, `6e_WeatherAhead_Why_sheet_*`, `10_HowWeTest_*`
and their `W` versions.

| Where | What it shows | Why |
| --- | --- | --- |
| Home (Main, W1_Home) | One line under "Try our sample field": "We tested each plan in 24 past years. See how" | Owner: one line to the page for judges. |
| Choose (W5_Choose) | A fourth card, "Weather ahead" / "What each month usually brings.", with the six Nepali months it covers. On the web the four cards sit in one row. | Owner: a third choice beside the months, in your style. It shows only on fields that have these records (Nepal). |
| Weather ahead (new) | "What usually happens here: 24 years of records. Not a forecast." Then six months, each with "Usually:", "Watch out:" (one danger, "Most years." or "Some years.") and "Do this:" (a tip and "Check with your local expert."), and a "Why?" button. No numbers on the month cards. | Owner and the coordinator's spec. The danger is the farmer's own crop when there is one (their winter crop, and rice from June to October). |
| Weather ahead, month name | Nepali: the Bikram Sambat month with its English months, e.g. "मंसिर (नोभेम्बर–डिसेम्बर)". English: the two months it spans, e.g. "November–December". | Each block runs from the 15th of one month to the 14th of the next. |
| Why? (your sheet) | In how many of 24 years, "Is it changing?", the other dangers and the ones never seen, rain (usual year and the driest and wettest years), day and night temperature, the longest run of dry days, frost, "This is an estimate.", and the sources. | Owner: numbers and sources go behind "Why?". |
| How we test each plan (new) | Four steps, each a picture and one sentence; then one real example: "A potato farmer who cannot water. Wheat did better in 24 of 24 winters." | Owner: for judges. The word "twin" is for the glossary only, so the page says "How we test each plan". |
| How we know | A button to "How we test each plan" at the top | Owner: linked from home and from How we know. |

## Moved off the farmer's screens, onto "How we know"

The judges' page now holds, written simply:

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

The owner's own lines, and the spec's words, changed only where a rule required it:

| Where | Asked for | On screen | Why |
| --- | --- | --- | --- |
| Weather ahead, top line | "What usually happens here, from 24 years of records." | "What usually happens here: 24 years of records." | 9 words; the limit is 8 |
| Home, one line | "We tested each plan in 24 years of your field's weather." | "We tested each plan in 24 past years." | 11 words; the limit is 8 |
| Weather ahead, danger | "Heavy rain" (20 mm or more, the spec) | "Big rain" | DHM calls only 50 mm or more "heavy" (our rain-at-harvest check uses DHM's 50 mm); Why? gives both |
| Is it changing? | "about the same" | "No clear change." | A trend test that finds nothing has not shown "the same" (as the onset screen's "No clear shift") |
| Explainer, title | "Field Twin" | "How we test each plan" | "twin" is a glossary word, kept off farmer screens; the glossary explains it |
| Explainer, step 4 | "your probe checks the soil today" | "Your soil stick checks the soil today." | "probe" is never shown to farmers |
| Weather ahead, labels | "Usually: ...", "Watch out: ...", "Do this: ..." | the same, with the label as its own word | label and sentence each stay within 8 words |

