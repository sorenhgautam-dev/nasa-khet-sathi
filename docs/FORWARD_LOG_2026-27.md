# Forward log: what we expect this winter on the demo field (written 2026-11-14)

The owner asked (item D4) for a dated file, committed before the feature freeze, saying what the tool expects for the
coming winter on the demo field, so it can be checked after January. **Nothing on the site changes because of this
file.** Every number below is copied from an output that existed when this was written (commit `412362c` and the
feature files of the same day); nothing will be edited after the fact. A later file reports the comparison.

The demo field is a **placeholder** (CLAUDE.md "Demo field"): a 60 m square near Bhaktapur. The rotation is the owner's
placeholder (rice, then potato), and the water source is unknown, so everything here is **rain-fed** ("if you can't
water"). Watering removes the dry stress the twin counts.

## Where the season starts

- The twin's state on **3 November 2026**: potato sown 30 October (FAO calendar), root zone **96 % wet** (rain-fed;
  `data/clean/demo/twin_state.json`). That is the "medium" start of the 25-Year Replay (`site/data/replay/demo.json`
  `start_default`).
- **El Niño:** NOAA CPC's ONI for August-October 2026 is **+2.46 °C** (`data/raw/oni/oni.ascii.txt`). Seven past
  seasons in our record share an El Niño state: 2002-03, 2004-05, 2006-07, 2009-10, 2015-16, 2018-19 and 2023-24.

## What we expect (estimates, not promises)

1. **Rain, month by month** (the site's month words; terciles of the twin's central, tuned rain at the field,
   2001-2025, `site/data/fields/demo.json` `diary.months` and `data/clean/demo/weather.parquet`):

   | Month | Our word | Low below | High above | Median |
   | --- | --- | --- | --- | --- |
   | December 2026 | low | 2.5 mm | 8.7 mm | 4.2 mm |
   | January 2027 | low | 5.9 mm | 16.3 mm | 9.3 mm |
   | February 2027 | low | 10.0 mm | 22.8 mm | 15.4 mm |

   **El Niño does not change this in our record:** December-February rain in the seven El Niño seasons ranged from
   21 to 90 mm, against a median of 38 mm for all seasons (terciles 25 and 51 mm). Four were above the median and three
   below. We expect a dry winter because winters here are dry, not because of El Niño.
2. **Soil:** the month words say medium in December, then dry in January and February. Frost risk is in December
   and January.
3. **The Replay** (rain-fed, medium start, `site/data/replay/demo.json`, water need met over the window's crop days;
   worked at 80 or more, failed below 50):

   | Plan (winter crop) | Next 3 months, all 24 past seasons | The 7 El Niño seasons |
   | --- | --- | --- |
   | What you do now (potato) | 12 struggled, 12 failed | 4 struggled, 3 failed |
   | Fill the empty months (wheat, sown 15 Oct) | 15 worked, 9 struggled | 4 worked, 3 struggled |
   | Feed your soil (lentil) | 1 worked, 23 struggled | 7 struggled |

   So, **if the potatoes are not watered**, we expect them to struggle or fail this winter, as in every past season of
   our record. If they are watered, the twin expects no dry stress (we do not know how this field is watered).

## How we will check it after January (fixed now)

- **Rain:** DHM's monthly bulletins for December 2026 and January 2027, mean of the Bhaktapur, Changu Narayan and
  Kathmandu Airport gauges (at least two reporting), the same gauges as `rules.yaml verification.rain_months`. A month
  word is **right** when that mean falls in the word's band in the table above. With two months, this is a story to
  tell, not a statistic: n = 2 cannot verify anything (`verification.common.n_min` is 10).
- **The season:** the farmer (or the field team) answers three questions in February 2027. Were the potatoes watered?
  Did they come up well? Was this a good, normal or bad potato year? A rain-fed field that "came up well" in a dry
  winter would count against the Replay; a watered one tells us nothing about it.
- **The probe:** any readings in December or January go into the comparison as they are, labelled with their dates.
- Whatever happens, the result is reported in a dated file beside this one, including the misses.
