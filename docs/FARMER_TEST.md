# Farmer test: three timed tasks

Written 14 November 2026. A short test of the website with real farmers, to fill VALIDATION layer 6 ("People", row
6.1: "Someone new reaches 'Your plan' in two or three minutes unaided"). It tests the website, not the farmer, and not
the advice. Run it after the four features are on the live site.

## Who, where, what you need

- **Five farmers** near Bhaktapur who grow rice. Ideally a mix: young and old, some who read easily and some who don't.
- **Two people from our team:** a helper who reads the tasks aloud in Nepali and answers only "try it your way", and a
  note-taker with a watch and the sheet below.
- **One test phone** with the live site open on the demo field, Nepali first. Charged, on mobile data.
- **The sheet below**, printed, one per farmer.

## Fix before the first session (and do not change after)

Write these on the sheet, date them, and commit them to the repository **before the first farmer**. They are the
success criteria; changing them after seeing results would make the test worthless.

1. **The Nepali wording of each task.** Read the same words to every farmer.
2. **The answer key for each task,** taken from the live site on the day (see each task).
3. **The time limits:** task 1, 2 minutes; task 2, 3 minutes; task 3, 3 minutes.
4. **A task counts as a success** only if it is right, done without help, and inside the time limit. "With one hint"
   is recorded separately and does not count as a success.
5. **A task passes** if at least 4 of the 5 farmers succeed. Every result is reported, passes and fails alike.

## Before each session

1. **Consent, read aloud in Nepali.** "We are testing our phone website, not you. It is a sample field, not yours. The
   plans are not advice. We will not write your name. We will not photograph you. You can stop at any time. Is that
   all right?" Write "consent: yes" on the sheet. If the answer is no, thank them and stop.
2. **Clear the phone.** Clear the site's saved data in the browser, so no earlier farmer's dates or photos remain. Do
   it in front of the farmer.
3. **One practice task, not timed:** "Switch the words to English and back." It shows how the phone works.

## The three tasks

Start every task from the home screen. Start the watch when the helper finishes reading the task. Stop it when the
farmer says "here" or "this one", or gives up, or time runs out.

### Task 1. 25-Year Replay: which plan failed least in dry years?

- **Read:** "Find which plan did best in the dry years. Show me."
- **Answer key:** the plan with the fewest "failed" squares in the years the site marks dry. Read it from the live site
  before the first session. (In today's outputs, "Fill the empty months" has the highest rain-fed harvest in every dry
  year: PITCH_FACTS C3. Check that the built screen says the same.)
- **Success:** names or points to that plan within 2 minutes, unaided.
- **Also note:** did they find the dry years by the highlight, or by reading? Did they think a square was a real
  harvest from their own field?

### Task 2. Field Pulse: when does the field turn green?

- **Read:** "Show me when this field turns green in the rainy season. Then change the planting date to the date you
  would plant."
- **Answer key:** the month the site's greenness line rises for the monsoon, as the site labels it in Bikram Sambat.
  Read it from the live site before the first session. (In today's outputs the monsoon green-up is June to early July:
  VALIDATION 3.15.)
- **Success:** points to the right month and saves a planting date, within 3 minutes, unaided.
- **Do not write down the date they choose.** It is about their own farming and it stays on the phone. Note only
  "saved: yes / no". (If a farmer wants to give us their real dates, that is a separate interview with its own consent:
  `notes/REAL_FIELD_RECORDING.md`.)

### Task 3. Safe Trial and the two labels

- **Read:** "Start a trial of 'Feed your soil' on one quarter of the field. Then tell me: is this plan's harvest number
  checked, or a guess? And is it about this field, or a whole region?"
- **Answer key:** the trial starts on any one quarter; the harvest number's two labels as the live site shows them
  (today the scorecard calls harvest numbers an estimate: PITCH_FACTS G3). Read the "how close" word from the live
  site before the first session.
- **Success:** the trial is started on one quarter, and both labels are read correctly, within 3 minutes, unaided.
- **No photos of people.** If the photo diary asks for a picture, photograph the ground. Delete it before the next
  farmer.

## Three more screens: "what does this tell you?" (added 14 November, evening, before any session)

These sit behind the cards' "How do we know?" buttons (rain at harvest and heat and cold under the Replay; the
fertiliser saver under "Feed your soil"). For each, the helper opens the screen, hands over the phone and asks the same
words. Not timed. Write down what the farmer says, quoted, without a name. Fix the answer keys from the live site before
the first session, as above.

### Task 4. Rain at harvest

- **Show:** the rain-at-harvest squares for "What you do now" (rice, then potato).
- **Ask:** "What does this tell you?" Then: "Is this about the coming year, or past years?"
- **Answer key:** in some past years (today: 8 of 24) heavy rain fell when rice is cut; none when potato is dug; past
  years, not a forecast.
- **Success:** the farmer says, in their own words, that heavy rain at rice harvest happened in some past years, and
  that it is about the past. Note whether they read a heavy-rain square as "my crop was lost" (it does not say that).

### Task 5. Heat and cold

- **Show:** the heat and cold screen, potato's cold card first.
- **Ask:** "What does this tell you?" Then: "Is this a lot of cold nights, or a few?"
- **Answer key:** cold nights in most past potato seasons (today: 17 of 24 years, about 3 a season); we may count too
  many; no very hot days for wheat or potato.
- **Success:** the farmer names cold nights for potato and no heat problem. Note whether they notice "our cold nights may
  be too many", and how they read "around 2040".

### Task 6. Fertiliser saver

- **Show:** the fertiliser saver in "Feed your soil".
- **Ask:** "What does this tell you?" Then: "For how much land?"
- **Answer key:** after lentil, rice may need a little less urea (about 1 to 2 bags) on a big plot; it is a guess; ask
  the agriculture office first. The land size is in "Why?" (one hectare).
- **Success:** the farmer says less urea may be needed after lentil and that it is not certain. Note whether they find
  the land size, and whether they think the bags are for their own field.

## What to record (per farmer, per task)

| Column | What to write |
| --- | --- |
| Farmer | P1 to P5. Never a name |
| About them (only if they agree) | grows rice: yes/no; uses a smartphone daily: yes/no; reads Nepali easily: yes/no |
| Task | 1 to 6 (4 to 6: not timed) |
| Time | seconds, from the end of the reading to "here", giving up, or the limit |
| Result | success / with one hint / failed / gave up |
| Hints | how many, and what was said |
| Wrong turns | the screens they opened that led nowhere |
| Words | what they said that shows confusion or understanding, quoted, without a name |
| Language | Nepali only / switched to English |
| Ease | after each task: "How easy was that?" Five faces, 1 (very hard) to 5 (very easy) |

## After the five sessions

- Count successes per task against the criteria fixed in advance. Report the times as a median and the slowest.
- Put the result, pass or fail, in VALIDATION 6.1, and any new number in `docs/PITCH_FACTS.md`.
- Keep the paper sheets off the public repository. Only the counts, times and unnamed quotes go into it.

## Privacy, in short

- No names, phone numbers or home locations are recorded.
- No photos or video of people. No audio recording.
- What a farmer saves in the site (dates, trial, photos) stays on the test phone, and is cleared in front of them
  before the next farmer.
- Nothing a farmer says about their own field goes into the model or the site without the separate consent in
  `notes/REAL_FIELD_RECORDING.md`.
- Tell every farmer: the field is a sample, the plans are not advice, and "you know your land best".
