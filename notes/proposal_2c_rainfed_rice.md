# Proposal 2c (4c in your queue): when can rain-fed rice be transplanted? For the owner; NOT applied

The rule is `config/rules.yaml` `paddy_rainfed` (status "PROPOSED, awaiting the owner", `apply: false`), committed before
the what-if run (`abbe701`). Nothing in the export changes until you say yes. Runs: `data/checks/demo/rainfed_rice_proposal/`.

**The problem.** The twin runs rain-fed rice as a plain soil bucket that starts on its planned day (23 June for the
current plan). Monsoon rain then keeps it full, so rain-fed rice is about 100 % in nearly every year, sourced monsoon
droughts included (METHOD_NOTES 36). The winter crop alone ranks the plans. In a late monsoon what goes wrong first is
that there is not enough rain to soak and puddle the field, so seedlings wait, go in late, or not at all.

**The rule in plain words.** The nursery is sown 21 days before the planned transplanting day. The field can be puddled
once 150 mm of rain has fallen since then. Transplanting is on the planned day if that rain has come, otherwise on the
day it comes. If it has not come 30 days after the planned day, the season fails: rice harvest 0. A late rice is simulated
from its real day (same bucket, no pond), and a winter crop it would overlap moves to the day after. Irrigated rice is
unchanged. No extra loss per day of delay.

**Sources** (opened 2026-11-14 by a research sub-agent; quotes in SI_LOG).
- 150 mm: land preparation "as low as 100-150 mm ... when the time lag between soaking and transplanting is only a few
  days" (Bouman, Barker, Humphreys, Tuong et al. 2007, *Water for Food, Water for Life*, ch. 14, Box 14.2); about 150 mm
  for low-humic-gley soils (Sri Lanka Department of Agriculture). FAO Training Manual 4 gives 200 mm to saturate the root zone.
- 21 days: seedlings "at least 21 days old" in the rain-fed models of Balwinder-Singh et al. 2019 (Field Crops Research
  239, APSIM, Bihar) and Han et al. 2024 (Climatic Change 177, DSSAT, Bangladesh); the Khumaltar trial used 22-day seedlings.
- 30 days late = failed: at Khumaltar (Kathmandu valley, 1,360 m; Chaulagain et al. 2022, Agronomy Journal of Nepal 6),
  transplanting about 16 days later cut yield 32 %, about 30 days later 85 % ("merely a few filled grains").
- The shape of the rule follows the two models (transplant when rain alone ponds 30-50 mm; no crop after a cutoff). A rain
  total stands in for the ponding depth because the twin has no pond for rain-fed rice.

**Uncertainty.** Each value spans a range: 100-200 mm, 20-40 days (sensitivity declared with the rule). With 100 mm only
2009 and 2019 are late (5 and 3 days); with 200 mm, 16 of 24 years are late by up to 15 days; no season fails at any
setting; the current plan's mean harvest moves 72.2 / 71.8 / 71.1 for 100 / 150 / 200 mm. The twin's rain reads about
1.35 times DHM's Bhaktapur normal, so it reaches 150 mm too easily: real delays are likely longer than these.

**What a farmer would see** (corrected rain; the uncorrected rain gives the same picks).

| | Today | With the proposal |
| --- | --- | --- |
| Harvest cards (now / fill the empty months / feed your soil) | 72 / 90 / 81 | 72 / 89 / 81 |
| Water cards | 38 / 51 / 44 | 38 / 47 / 41 |
| Soil kept | 74 / 75 / 75 | 74 / 70 / 70 |
| Worst-tenth year, current plan | 65.7 | 64.6 |
| Rain-fed rice, mean of seasons | 100.0 % | 99.9 % |
| Current plan's baskets that change | | 6 of 24, by at most 4 points (2020: 84 -> 80) |
| Suggested plans | rice sown 15 June | the same rotations, rice sown 31 May |

**Which years become bad** (checked against `config/known_events.yaml` only after the commit). Transplanting is late in
2009 (11 days), 2019 (12), 2014 (6), 2024 (4), 2010, 2015, 2023 (3) and 2012 (1). The sourced paddy-season droughts are
2009, 2012, 2014, 2015 (central Nepal or Terai) and 2006: four of five are among the late years, 2006 is missed, and 2019
has no listed event. But no year's rice harvest falls: the delay shows only as days, and the baskets that move do so
through the winter crop that follows a late rice.

**Risks.**
- It barely changes the result, so it can look like a fix it is not. The loss the Nepal trials measure after late
  transplanting is mostly October cold and a short grain-filling season, which the twin does not model.
- A delay costs nothing unless it passes 30 days. Plans with an earlier planned day gain, because they can wait for the
  rain: that is why the suggested plans move to 31 May. A per-day loss would stop this, but the sources disagree on the
  size (0.5-2 % a day), so it is not proposed.
- Placeholder field and rotation; one valley trial (two years) sets the cutoff.

**Recommendation.** Do not switch it on as a harvest rule now. If you want the late monsoon visible before Sunday, use
the same rule only as a diary line ("the rain for puddling came 11 days late in 2009"), with no change to any score. The
real fix, after the deadline, is a pond for rain-fed paddy (bund height, 2-3 mm a day of percolation for a puddled
loam, stress once the pond is empty) plus a cold penalty for late rice. You decide.
