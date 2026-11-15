# Tough questions: a skeptical judge panel's 15 hardest

Rewritten 14 November 2026 (afternoon) for the four features and the outputs after the owner's decisions of that
afternoon (tuned rain, rice water losses on, satellite planting dates and "rice waits for rain" undone, groundwater out
of the water score). Hardest first. Each answer cites `VALIDATION.md` rows (e.g. 3.9b), `METHOD_NOTES.md` items (MN 35),
`docs/TRACEABILITY.md` ("Gaps found") and `docs/PITCH_FACTS.md` IDs in square brackets. Where we have no good answer, we
say so, and say what would fix it.

## 1. The model never shows a bad rice year

**Question.** Rice is half of every plan and the harvest the farmer depends on. Does your model ever show rice failing?

**Our answer.** No. Rain-fed rice runs as a soil-water bucket with no water held behind the bunds (MN 2, 103). With its
seepage and percolation now counted, Kharipati's lowest rice year is 91.9 out of 100; the sourced monsoon droughts of
2009 and 2015 give 93.3 and 97.0 [H10]. A rule that made rice wait for 150 mm of rain before transplanting caught neither drought and
was undone (4.9). Rice's years do not follow Nepal's national rice yields (r 0.30, interval reaching 0) [J5]. So the
winter crop alone ranks the plans (MN 36), and the farmer's own question, "without risking the harvest I depend on", is
answered for the winter crop only.

**No good answer.** Fix: the rice pond (`docs/NEXT_STEPS.md` 1: standing water, bund height, a measured percolation
rate). Until then we say: "Our model cannot show a bad rice year."

**Verdict:** not answered.

## 2. Is the gain the crop, or the way you compare?

**Question.** "Fill the empty months" scores 87 against 69 for today's plan. How much of that is your set-up?

**Our answer.** Some of it. Both plans now use crop-calendar dates (the satellite dates were undone, 4.9), so that tilt
is gone. But the suggestions may pick the best of three sowing dates, while today's plan sits mid-window. Given the
same choice, today's crops would score 71.1 [H12]. Harvest is a share of each crop's own potential, so 87 against 69
compares wheat with potato as percentages, not weight or money (MN 37). The gain exists only without water: with water
every plan scores 100 [C5, H8]. FAO's wheat window here is for irrigated wheat (3.19), and the wheat plan's own tab says
wheat here usually needs watering.

**No good answer** for the wording. The benefits tab says "Harvest: about 9 to 23 more" with no "if you can't water",
and the gain is measured against today's plan at a fixed date. Fix: compare like with like (today's crops at their best
date too) and add "if you can't water" to that line.

**Verdict:** partly answered.

## 3. Root depth and soil decide the size of the gain

**Question.** Why believe the wheat plan's lead, when it needs deep roots in soil from a 250 m map cell?

**Our answer.** We don't fully. Root depths are the larger end of FAO-56 Table 22, never measured here (MN 35). The site
shows the gain as a range over Table 22's depths: about 9 to 23 for the wheat plan, 5 to 14 for the lentil plan [H2,
H3]. The soil is Kharipati's own SoilGrids cell: 156 mm for plants in the top metre, against 146 to 180 mm in the 104
cells within 2 km [B6]. On the earlier demo square, the neighbourhood median soil added 2 to 3 points (4.4c), and a
plough pan under the paddy that stops winter roots at 0.6 m put the wheat plan below today's plan (71.7 against 72.3;
4.4, run before the changes of 14 November); neither was rerun for Kharipati. The same three plans win with fewer years and with other crop sensitivities [H7]; potato and wheat
sensitivities were never varied.

**No good answer** for the plough pan: the range leaves out the case where the gain vanishes. Fix: rerun the 0.6 m case
on today's model and show it as the low end; measure the field's own field capacity with the soil tins
(`notes/FIELD_CAPACITY_PROTOCOL.md`; the site then shows both results).

**Verdict:** partly answered.

## 4. Whose field is this?

**Question.** Has anyone checked a single number against a real field?

**Our answer.** No one yet. Kharipati is a real farm in Kharipati, Bhaktapur, and its outline comes from an open drone
map of 5 May 2026. We have not heard from its farmer, so its crops, dates and water source are placeholders [B4]. Our
crop guess agrees with the ripe cereal in the drone photo, but that is one date, seen by eye [G3]. The earlier demo
square (a 60 m square we picked from maps; our first pick was a construction plot, 1.4) and four sample fields are
hidden [B5]. The field-visit notes are empty (`notes/FIELD_VISIT_FINDINGS.md`). Every screen carries a placeholder chip. The scorecard lists, for
every output, the data that would check it [G4].

**No good answer.** Fix: the farmer interview (`notes/REAL_FIELD_RECORDING.md`: the best and worst years are asked before
the farmer sees the app), the farmer test (`docs/FARMER_TEST.md`) and a co-operative pilot (`docs/NEXT_STEPS.md` 7).

**Verdict:** not answered.

## 5. Your hook says the land sits empty. Your own map says a typical field is bare about a week

**Question.** Which is it?

**Our answer.** Both, and we show both. The typical farm square is bare about 7 days a year (0 to 30) [A3]. About 15 in
100 are bare for more than two months (0 to 31) [A2]. Only about 37 in 100 show two crop seasons (19 to 48) [A4]. So most
"empty months" are green with something other than a second crop: weeds, grass or fallow. Space sees green, not which
crop. The bare line (NDVI 0.25) is not tuned, which is why the range is wide [A7] and why bare days are graded "low" on
the report card. Kharipati, bare about 23 days a year, is barer than the typical square but far below the 60-day line [A5].

**No good answer** for the bare line: there is no ground record of bare days. Fix: farmers' calendars for at least 10
fields (scorecard `cover_months`), then tune the line on half and test on the rest.

**Verdict:** partly answered.

## 6. You tuned the rain on Nepal's gauges, then scored it on the same gauges

**Question.** Isn't your rain check circular now?

**Our answer.** Not for Kharipati: its rain is the corrected rain, not tuned; only the earlier demo square's rain was
tuned [F8]. Kharipati's rain scores 13 of 20 months within 19%, and the row is still marked not independent [F11]. The
tuning test itself (demo square) was thin: leaving one gauge out, the tuned rain scored 40 of 83 months against 38 of
83 for the untuned, within the noise. On the locked 2026 months every version scored 3 of 15, and 2026 is IMERG Late
only, so that test mostly measures Late's own errors [F9]. The level is still 1.35 times Bhaktapur's usual [F10]. The
"0.88 times the gauges" for 2025 is the untuned rain, and its script runs outside the one-command chain
(TRACEABILITY "Gaps found") [F12].

**No good answer:** no rain version comes within 19% in most months. Fix: IMERG Final for 2026 and more of DHM's monthly
bulletins, then score once on months the tuning never saw (3.9e).

**Verdict:** not answered.

## 7. The 2017 correction removes any real change by construction

**Question.** What if the monsoon really did get wetter after 2016?

**Our answer.** The change in NASA's inputs is well shown: the gauges' share falls from 96-98% to 56-72% a year, GPCC's
stations from about 50 a month to about 1, CHIRPS has no step (p 0.24), and IMERG Late steps 1.13 where Final steps
1.62 [F1-F5]. A real change would be removed too, and the "unknown" tab says so. The correction's held-out test is weak:
only the years after 2016 are split, one synoptic station scores it, and the same months chose the method; a single
yearly factor scores the same (3.9b). It restores the level, not the order of wet and dry years: both negative controls
fail (4.1).

**Limitation** we state: "The correction restores the average after 2016, not which years were wet or dry." Fix: DHM's gauge
data for 2017-2023, the only thing that could reorder the years (3.9e).

**Verdict:** partly answered (the change itself: answered).

## 8. "Verified" sounds strong. Verified what?

**Question.** What exactly is verified, against what, decided when?

**Our answer.** Five rows for Kharipati, all valley-wide, on a yardstick written and committed before any score: an
independent reference, at least 10 cases, at least 92% within tolerance [G1]. The rain, heat and frost word of each
month (12 of 12 each) test the shape of the year, not any single year. The two monsoon rows test our copy of DHM's
own table and its trend (24 of 24 each), not a method of ours [G2]. Everything a farmer would act on, each year's square, each plan's harvest and gain, is an estimate or not
yet checkable [G3, G4]. We report the three classes, never one percentage.

**Verdict:** answered, with the warning that the five verified rows are easy passes.

## 9. You changed the model on the last day. Did you tune it to your checks?

**Question.** Satellite dates on, then off; rice rule on, then off; rain version switched. How is that not tuning?

**Our answer.** Partly it is. Each rule is committed before its first run [J6]. The rice water losses had a keep rule
fixed before the comparison, and passed on the demo square: no independent check got worse [H9]. But the satellite planting dates were
undone after the independent checks got weaker (`config/rules.yaml` `season_dates.apply`), and the rain version was
chosen on gauge months [F9]. Choosing by the checks after seeing them is a mild form of tuning. Every undone run is kept
and described (4.9), so a reader can see both. The flood rule's earlier versions were also run before it was set (4.1).

**No good answer** for the undo itself. Fix: freeze the model now; any later change names in advance the check that
decides it.

**Verdict:** partly answered.

## 10. The replay "finds" known floods and droughts. Was it blind?

**Question.** How many did it find, and how many did it invent?

**Our answer.** Not blind. Valley floods: 2 of 2, but the 100 mm and 200 mm flood rules were run before the final rule,
so those floods were known to be among the wettest days (4.1). One flagged flood year, 2004, has no recorded flood.
Valley dry seasons: 2 of 4; 3 of 9 flagged seasons were not confirmed; both negative controls fail (the 2023 and 2025
monsoons, which DHM had at 107% and 117% of normal) [C2]. The rules are quotas: the driest fifth of seasons is flagged,
whatever the rain.

**Limitation** we state: "'Dry year' means our driest fifth of seasons." Fix: more sourced valley events (scorecard
`needs`).

**Verdict:** partly answered.

## 11. The probe is untested and reads the wrong depth

**Question.** How accurate is it, and how can a few centimetres of soil update a root zone of 0.6 to 1.5 m?

**Our answer.** It is untested: the cup test waits for the team (5.1-5.3) [E3]. The sensor's 0-100 scale runs from air
to water; it is not soil water, and such sensors respond to texture, salt, temperature and packing (`robot/README.md`).
Its error R would be repeatability only, so "how sure" after a reading would be too high (5.4, MN 62). Each of Kharipati's
9 parts already shows "how sure" 0.29 and wetness 96 from the model alone, as of 3 November [C6]; on the demo square,
aged to 14 November, the model alone would be at 0.05 (5.4). In Safe Trial the probe only compares parts of the same field, never gives a water number.

**No good answer.** Fix: run the six cups (`robot/CUPS_PROTOCOL.md`, about two hours) and the soil tins
(`notes/FIELD_CAPACITY_PROTOCOL.md`). Until then: "The probe is a prototype."

**Verdict:** not answered.

## 12. Why should El Niño or La Niña years matter for this field?

**Question.** The Replay highlights years with the same ONI state as this year. Where is the evidence that ONI tells
anything about rain in the Kathmandu valley?

**Our answer.** There is none in our outputs [C8]. We have not tested ONI against this field's rain or the replay's
harvests. The highlight groups similar years for the farmer to look at; it is not a forecast. With 24 years, each ENSO
state holds only a handful of them, so any test would be weak.

**No good answer.** Fix: a rule fixed before the run: compare the field's monsoon and winter rain, and the replay's
harvests, across ONI states with a permutation test, and against DHM's gauges. Until then the screen should say
"similar years, not a forecast".

**Verdict:** not answered.

## 13. Safe Trial: one part, one probe reading, one season. What can that show?

**Question.** Is one part of a small farm an experiment?

**Our answer.** Not a powered one. A part of Kharipati is 96 to 141 m² [E1], with one probe reading, one season, and a probe without
a bench test [E3]. What it does: it lets a farmer see a plan on their own land before risking the whole field, which is
what every plan's "check" tab already asks [E2]. It also gives us a first measured harvest to compare with the Replay's
estimate. We will report each trial as one case, never as proof [E4].

**What would fix it:** many farmers' trials pooled through a co-operative, with the comparison rule written before the
season (`docs/NEXT_STEPS.md` 7).

**Verdict:** partly answered.

## 14. Does the 2040 range include your own model's doubt?

**Question.** Today's plan stays about 69 by 2040 (68; 60 to 75). Is that band honest?

**Our answer.** It is honest about what it is: the spread of 23 climate models, two futures and our rain versions,
changing only monthly means on the observed weather [H11] (MN 50). Dry spells, storm intensity, heat damage and CO2 stay
as observed, and warming reaches the crops only through water (MN 53). Root depth alone moves the wheat plan's gain by
about 14 points [H2], as wide as the whole climate band. The plausibility check (4.7) catches unit and sign errors, not
bias.

**Limitation** we state: "The range shows how climate models differ. Our model's own doubts are larger."

**Verdict:** partly answered.

## 15. "Made for any field on Earth." Where is the proof?

**Question.** Every field on your site is near Bhaktapur.

**Our answer.** True. The twin's inputs are global datasets, and two commands download and build a field [I3, I4].
Kharipati, the earlier demo square and four sample fields (now hidden) were built by the same command [B5]. A field in Madagascar ran its rain
check with no code change and found no gauge change, so it kept NASA's rain as published [F13]; its replay and plans
are not on the site. The crop calendars are Nepal's, DHM's records are Nepal's, and the temperature correction needs a
nearby station.

**No good answer** yet. Fix: build the Madagascar field end to end (its config exists) with its own crop calendar, and
put it on the site.

**Verdict:** not answered.

## Fixed since the last version of this list

- **Groundwater lowered the water scores by up to 21 points.** Now context only: irrigation counts once whatever the
  regional trend (`config/rules.yaml` `plans.water_strict_when_falling` 1.0, owner's decision).
- **Satellite planting dates made the twin-satellite check circular.** Undone; the check is independent again (4.2c,
  4.9).
- **"Three independent records agree" on the monsoon.** Removed. The site says "No clear change since 2001, in Nepal's
  weather office records" and "These records share some rain gauges" (`F` `diary.shift_note`, `method.onset`).
- **A single "92% verified" number.** Replaced by the compliance table's three classes [G2-G4].
- **"How sure" came from SMAP with no source tag.** SMAP L4 is now in the field's sources (`F` `sources`).

## The three fixes that would most improve our answers

1. **Ground truth** (questions 3, 4, 5, 11): the farmer interview, the farmer test, the soil tins and the probe's cups.
   Each takes hours, not weeks.
2. **The rice pond** (question 1): the one model change that could let a bad rice year show at all.
3. **One honest wording pass** (questions 2, 6, 12): "if you can't water" on every harvest gain; today's crops at their
   best date in the comparison; "similar years, not a forecast" beside the El Niño highlight.
