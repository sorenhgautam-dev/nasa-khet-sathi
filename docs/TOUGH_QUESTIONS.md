# Tough questions: a skeptical judge's 15 objections

Written 2026-11-14 by Claude (Opus 5.5) as an adversarial judge. Strongest first. Numbers cite `VALIDATION.md` rows
(e.g. 3.9c) and `METHOD_NOTES.md` items (MN 35); refresh them from those rows after today's reruns. "Pre-switch" marks
runs before the 2026-11-14 switches (bare soil, satellite sowing dates, rain-fed paddy rule).

## 1. The suggested plan wins partly because of how the comparison is set up

**Question.** "Fill the empty months" shows "about 10 to 24 more" harvest than the farmer's plan. Is that the crop, or
the rules of your comparison?

**Our answer.** Suggested plans keep calendar dates and the best of three sowing days. The farmer's plan is sown on the
satellite's dates (`rules.yaml season_dates.suggested_plans`: the difference "holds the date difference as well as the
crop difference"). That switch alone cost the farmer's plan 5 points (4.2c, 2014-2025: 72.1 to 66.8; potato 44.1 to 36.6).
Harvest is a percentage of each crop's own potential, so 86 against 67 compares wheat with potato, not weight or
money (MN 37). The gain exists only without water: watered, every plan scores 100 (MN 38). FAO's wheat window here is for
irrigated wheat (3.19). The third plan's rule was changed after the first run, and "Safest in bad years" was renamed
"Feed your soil" when it proved not safest (3.19, MN 33). The picked rotations do hold across years, Ky and rain (4.4).

**No good answer.** The benefits tab states the gain with no "if you can't water". Fix: rerun the gain range with the
farmer's plan on calendar dates too (`--season-dates calendar` exists), and add "if you can't water" to that line.

**Verdict:** not answered.

## 2. The planned "92% verified accuracy" scorecard

**Question.** Verified against what, with which tolerances, set when, on how many cases?

**Our answer.** No such number is in the repository yet. VALIDATION's own Totals give 22 PASS and 9 FAIL (71%), plus 30
"run with findings" and 6 waiting or not possible. Half the PASSes (11 of 22) are software or equation checks (1.1, 1.2,
1.2b, 1.5, 2.1-2.5), not accuracy against the world. Others are fitted reference (3.4, 3.5) or not blind (4.1c). A tolerance moved
after data: the January-nights band went from 0 ± 3 C to 0-5 C on the day the first results were reported (SI_LOG,
2026-11-11); under the old band 3.4 fails. The report card's rain rule (MN 98) was written on 14 November, after 3.9c's
0.88 was known. Many checks have tiny n: 3 months (3.9c), 12 years (4.2), 2 valley floods (4.1), 1 frost night
(4.1c). Secondary passes were picked among several (the wheat option in 4.2 and 4.3; potato fails, rice not testable).
Dropping "not testable" rows from a denominator raises any percentage.

**No good answer.** Any single percentage can be gamed by the choice of denominator. Fix: drop "92%". Show counts by
class (independent / fitted reference / code check), each with pass, fail, not testable and n.

**Verdict:** not answered.

## 3. The field is a placeholder: nothing has ground truth

**Question.** Whose field is this, and has anyone checked a single number against it?

**Our answer.** Nobody's. A 60 m square picked from WorldCover 2021 and an NDVI test that grass also passes, then
moved 25 m by eye; the first pick was a construction plot (1.4, MN 13). Rotation, dates, water and soil are
placeholders, and the twin's winter potato (30 Oct-21 Feb) is not the season the satellite sees (Jan-May; MN 40). The
field-visit form is empty (`notes/FIELD_VISIT_FINDINGS.md`). Every output says "placeholder".

**No good answer.** Fix: run the farmer interview (`notes/REAL_FIELD_RECORDING.md`) and compare the farmer's worst years
with the replay. Otherwise state: "This is a sample field. No farmer has checked its crops, dates, water or soil."

**Verdict:** not answered.

## 4. Root depth and soil decide the size of the gain

**Question.** The wheat plan's lead needs roots at 1.5 m in soil from a map cell 859 m away. Why believe either?

**Our answer.** Depths are the larger end of FAO-56 Table 22 (MN 35), never measured here. With wheat at 1.0 m the gain
falls from +17 to +8. With winter roots stopped at 0.6 m by a plough pan under the paddy, the wheat plan falls below
today's (71.7 against 72.3; 4.4, REVIEW_2 H2; pre-switch). The site's "+10 to +24" spans Table 22 only, so it leaves out
the case where the gain vanishes. Soil: the field's own SoilGrids cell is masked as urban, and the cell used is the
driest of 56 within 2 km (MN 7). The neighbourhood median adds 2-3 points (4.4c). The picks hold in every case (4.4).

**No good answer** for the plough pan. Fix: add the 0.6 m case as the low end of the gain range ("from about 0").

**Verdict:** partly answered.

## 5. The model cannot see a bad rice year

**Question.** Rice is half of every rotation. Does your model ever show a rice failure?

**Our answer.** No. Rain-fed paddy has no bund storage (MN 2) and scores about 96-99% after the switches (3.21, 4.2c).
No paddy season fails in any plan or rain version (4.1). The land-preparation rule (MN 69) misses the sourced 2009 and
2015 monsoon droughts. In 2015 FAOSTAT rice fell 205 kg/ha while the twin rose 4.9 points (4.1). Rice is "not testable"
against HLS (4.2), FAOSTAT (4.3) and ECOSTRESS (4.2e). So each year is about (100 + winter crop) / 2, and the winter crop
alone ranks the plans (MN 36).

**No good answer.** Limitation: "Our model cannot show a bad rice year. Its rice numbers say nothing about rice
drought."

**Verdict:** not answered.

## 6. Rain level: the central case is a third above the nearest gauge

**Question.** DHM's Bhaktapur gauge, 2.3 km away, averages 1,375 mm. Your model uses 1,853 mm. Why is the gauge only
the "edge"?

**Our answer.** The fix restores GPM's own 2001-2016 level, already 1.34 x Bhaktapur's normal while the gauges were in it
(3.9b, 3.1). Against DHM's 2025 gauges the corrected rain reads 0.88 x in three IMERG Final months, the DHM-scaled rain
0.61 x; Late months read 1.64 x (3.9c, 3.9d). The rain version moves harvest 3-4 points and water scores about 9, not
the picks (3.9d). The dry edge is GPM scaled to 1991-2020 monthly normals, not "the nearby station's rain level" as the
evidence tab says.

**No good answer.** Three months of one year are the only support for the central level. The report card grades rain
"medium" on exactly that test (MN 98); the 1.35 x long-term level fails the same 0.8-1.25 band. Fix: grade rain "low",
or apply the band to the long-term level too.

**Verdict:** partly answered.

## 7. Satellite dates now drive the model: circular checks

**Question.** You sow the model's crops on the satellite's green-up. How can twin-satellite agreement still count?

**Our answer.** It cannot, and we say so (4.2c, report card). But 4.2 still reports the winter crop as "agrees" (rho
0.64, n 12) on dates taken from the same seasons. The seasons' "high" grade rests on three methods: two built the
reference, the third was trained on their agreement (3.15). No field calendar exists, and the NDVI rise may be weeds
or the nursery (4.2c). The circular input also moves the ranking: satellite dates push potato into the dry spring while
suggested plans keep calendars (objection 1). The unknown tab still says "Planting dates are typical ones, not yours".

**Fix:** drop 4.2's winter result as evidence; grade seasons "high for when the field is green, not tested for crops";
correct the unknown-tab line.

**Verdict:** partly answered.

## 8. The 2017 correction removes real change by construction

**Question.** You scaled 2017-2025 back to 2001-2016. What if the monsoon really changed?

**Our answer.** The break is well shown: IMERG's gauge weight drops from 96-98% to 56-72% in January 2017, GPCC
stations from about 50 to about 1 a month, CHIRPS has no step (p 0.24), and IMERG Late steps 1.13 against Final's 1.62
(3.9b). The correction does remove any real change, and we say so. Its held-out test is weak: only post-2017 years are
split, the even half has 12 station months, one synoptic station scores it, and the same months chose the method.
A single yearly factor scores the same (32.2 against 31.4 mm), and November's factor of 2.40 rests on 7 mm against 3
(3.9b). The fix restores the level, not the order of years: both negative controls fail (4.1).

**Limitation:** "The fix restores the average after 2016, not which years were wet or dry."

**Verdict:** partly answered (the break itself: answered).

## 9. Monsoon onset: the source changed after two failures

**Question.** Your onset rule failed, your second measure failed, then you used DHM's dates. Is that shopping for an
answer?

**Our answer.** Both our methods fail DHM's window and stay shown as failing (4.1d: median 16 May; 4.1e, 3.22: 27 May).
DHM's official dates are the right record, and the rule was committed before the run (3.22b). DHM gives -2.2 days over
2001-2024 (-11.5 to +7.7): no clear shift.

**No good answer for the words.** The site says "The rains start when they used to" and "Three independent records
agree" (`diary.shift_note`), yet the range allows 11 days earlier or 8 later, CHIRPS's onset does not follow DHM's years
(Spearman 0.17), and CHIRPS and IMERG may share DHM's gauges (3.22b). "Usually 10-16 June" is only the middle half of
years. Fix: "No clear change since 2001, in DHM's records"; drop the other two lines.

**Verdict:** partly answered.

## 10. A 300 km GRACE signal lowers the plans' water scores

**Question.** GRACE's mascon runs from the Bihar plain to Everest. Why does it change your field's scores?

**Our answer.** The cell is in JPL mascon 1213 (25.5-28.5 N, 85.0-88.5 E), glaciers and snow included (3.16, MN 26).
The trend is clear (-2.57 cm/yr); `confidence` 1.0 is 1 - p, not knowledge of the field. "Falling" makes irrigation
count 1.5 x, lowering water scores by 14-21 points (4.4: 58.8 / 67.2 / 63.0 without it against 38.2 / 50.8 / 44.5;
pre-switch). The 1.5 x is an owner-approved choice with no published source. The why tab says "Stored water in this
area is falling". No well data check it.

**No good answer.** Fix: take the 1.5 x out of the score and show the trend as context only. Otherwise state: "Regional,
glaciers included, not your well. It lowers water scores by up to 21 points."

**Verdict:** not answered.

## 11. The probe is untested and reads the wrong depth

**Question.** How accurate is the probe, and how can a few centimetres of soil update a 0.6-1.5 m root zone?

**Our answer.** It is untested: the bench test (5.1-5.3) waits for the team's cups. The capacitive sensor's 0-100 scale
(air to water) is not soil water (`robot/README.md`), and such sensors respond to texture, salt, temperature and
packing. The Kalman R is repeatability only, without fit error or depth mismatch, so `sure` after a reading "is too
high" (5.4, MN 62). The site already shows `sure` 0.21 and wetness 96 on every part with no probe reading: the twin on
3 November, for a calendar-sown potato. By the project's own ageing rule `sure` is 0 today
(`data/clean/demo/twin_state.json`; row 5.4's P0, r and sure_prior are stale against it).

**Fix:** run the six cups (`robot/CUPS_PROTOCOL.md`, about two hours). Until then: "The probe is a prototype. Its
readings are not yet checked against weighed soil water."

**Verdict:** not answered.

## 12. The 2040 range leaves out the model's own doubt

**Question.** Today's plan scores 61-74 by 2040. Does that band include your own uncertainty?

**Our answer.** No. It is the lowest to highest of 46 runs (23 models, two scenarios) that change only monthly mean
rain and temperature on the observed 2002-2025 weather (MN 50, 54). Dry spells, storm intensity, heat damage, CO2 and
crop timing stay fixed (MN 50-53). Root depth alone spans 14 points of gain (objection 4), as wide as the whole climate
band. The plausibility test (4.7) compares one 25 km cell with a Nepal-wide range that may come from the same NEX-GDDP
data: it catches unit errors, not bias. Row 4.7 still shows 5 models; `data/checks/demo/future.json` has 23.

**Limitation:** "The range shows only how climate models differ. Our model's own doubts are larger."

**Verdict:** partly answered.

## 13. Ky and FAO-33 are pushed past their range

**Question.** Where do the crop sensitivities come from, and do they hold at large water shortfalls?

**Our answer.** Wheat 1.15 and potato 1.1 are FAO-33 seasonal values; rice and lentil are assumed 1.0 (MN 5). Ky 0.8 and
1.2 for the assumed crops keep the same picks (4.4b). But FAO-33's straight line is applied beyond its range: 12 of 24
rain-fed potato seasons get less than half their water (MN 19, pre-switch). Potato and wheat Ky were never varied, and
the lentil plan's harvest rests on an assumed value.

**Fix:** rerun the picks with potato and wheat Ky at ±20% (one `scripts/run_plans.py` run). Limitation: "In very dry
seasons the harvest numbers are an extrapolation."

**Verdict:** partly answered.

## 14. Event years: not blind, quotas, failed controls

**Question.** Your replay "finds" the known floods and droughts. Was the test blind?

**Our answer.** No. The 100 mm and 200 mm flood rules ran before the decile rule; drought deciles 1-2 were preferred
partly because they matched more events (MN 14). Both rules are quotas: a fifth of years is flagged whatever the rain.
Valley floods 2 of 2, valley droughts 2 of 4; both negative controls fail (the 2023 and 2025 monsoons flagged dry, DHM
107% and 117%; 4.1). Four of the five worst years are listed droughts, but so are 12 of 24 years: 16% by chance. The
report card still grades floods "medium".

**Limitation:** "'Drier than usual' means our driest fifth of years. After 2016 the order of years is less sure."

**Verdict:** partly answered.

## 15. The FAO-56 shortcuts

**Question.** Which simplifications could change your numbers?

**Our answer.** The equations reproduce FAO-56's printed examples (2.1b-2.1d, 2.5). Listed shortcuts: full root depth
from sowing (MN 35); depletion carried as a fraction at crop changes, creating 870 mm over the record (MN 39); unlimited
water in the watered case (MN 38). Not listed anywhere: capillary rise from a shallow valley-floor water table, which
would feed winter crops. Outside checks are weak: GLDAS soil r 0.34, below the bar set (4.2d); ECOSTRESS sees no dry
season while the twin is short of water on 39% of overpass days (4.2e). The bare-soil method, switched on today, moved
harvest 72 to 69 (3.21).

**Fix:** add "We assume no shallow water table" to the unknown tab and METHOD_NOTES.

**Verdict:** partly answered.

## The three fixes that would most improve our answers

1. **Compare like with like** (objections 1, 4, 7). Rerun the gain with the farmer's plan on calendar dates and with a
   0.6 m plough-pan case. Show the range that results, and add "if you can't water" to every harvest-gain line.
2. **Replace any "92%" with a classed tally** (objection 2): independent / fitted reference / code check, each with
   pass, fail, not testable and n, taken from VALIDATION's rows as they stand.
3. **One wording pass on overclaims** (objections 6, 9, 10, 11): grade rain "low" (or test the long-term level); remove
   "three independent records agree" and "the rains start when they used to"; make the groundwater line name its
   1.5 x effect on water scores; show no `sure` on a part until the probe has read it.
