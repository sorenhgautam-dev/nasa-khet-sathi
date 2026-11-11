# VALIDATION.md

Updated 2026-11-11, end of build step 2. Each check was run today unless it says **NOT YET
POSSIBLE**. Result files are in `data/checks/demo/` and are copied into `review_pack/checks/`.

Result words: **PASS** · **FAIL** · **NOT YET POSSIBLE** (reason, and the step that unblocks it).
Where the owner's expectation says "roughly" or "near", I chose a tolerance and marked it
**TODO-CONFIRM**.

## Layer 1: Runs

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1.1 | Tests pass | **PASS**: 209 passed, 0 failed | `pytest`: schema 54, guards 64, power 21, gitignore 19, checks_climate 10, mock 10, ghcn 9, review pack 7, fields 5, crosscheck 5, backup 3, credits 2 |
| 1.2 | Every export validates | **PASS**, with a warning: `demo.json` is still MOCK data | `python -m pipeline.export.validate`: 2 files, 0 problems |
| 1.3 | The UI loads it | **NOT YET POSSIBLE**: `site/` holds only `data/`; the UI code is not in this folder | UI teammate; then rerun |

## Layer 2: Equations

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 2.1 | ET0 matches pyet within 3% (30 days of real POWER data) | **NOT YET POSSIBLE**: no ET0 code yet. POWER data is now ready | Step 3 |
| 2.2 | Water balance closes: rain in minus runoff, drainage and evaporation equals the change in soil water, within 1 mm per season | **NOT YET POSSIBLE** | Step 4 |
| 2.3 | Extremes behave: 60 dry days give heavy stress; constant rain gives none; harvest stays 0 to 100 | **NOT YET POSSIBLE**. (The export contract already rejects harvest outside 0 to 100; test A3 cases `score_above_100`, `replay_harvest_above_100`) | Step 4 |

## Layer 3: Data sensible

Data: NASA POWER (model-based, one cell at 27.67 N 85.43 E, 2001-01-01 to 2025-12-31, 9,131 days)
and NOAA GHCN-Daily station NP000444540 Kathmandu Airport (ground station, about 7 km away).

| # | Check | Result | Numbers |
| --- | --- | --- | --- |
| 3.1 | Kathmandu yearly rain roughly 1,400 to 1,500 mm | **FAIL for POWER** | POWER mean **1,150 mm** (25 complete years). My tolerance was 1,260 to 1,650 mm (TODO-CONFIRM). POWER's 2001 to 2003 totals are 621, 525 and 534 mm, about half of every later year (901 to 1,588 mm). This looks like a break in the record; cause unknown, TODO-VERIFY |
| 3.1b | Same, at the station | **NOT YET POSSIBLE** directly: no year 2001 to 2025 has all 12 months complete | Estimate only: POWER is 21% drier than the station month by month (3.7), and 1,150 / 0.787 ≈ **1,460 mm**, inside the expected band. Not a measurement |
| 3.2 | Mostly June to September | **PASS** | POWER: **78.1%** of rain falls June to September ("mostly" read as more than half, TODO-CONFIRM) |
| 3.3 | Onset near 10 June | **NOT YET POSSIBLE**: onset uses GPM IMERG (needs Earthdata login) | Step 6 |
| 3.4 | January nights near freezing | **FAIL for POWER**; station borderline | POWER January mean minimum **7.2 C** (all 25 Januaries). On the 205 January days both have, station **3.7 C** and POWER 7.5 C: **POWER is 3.8 C too warm**. The station's 3.7 C is just outside my 0 ± 3 C reading of "near freezing" (TODO-CONFIRM) |
| 3.5 | Early-summer days near 30 C | **PASS** | POWER May-June mean maximum **29.5 C**. On 829 shared days, station 29.4 C and POWER 29.5 C (difference +0.08 C) |
| 3.6 | Greenness peaks in the monsoon | **NOT YET POSSIBLE**: HLS and MODIS need the Earthdata login | Step 6 |
| 3.7 | Cross-check: POWER rain vs station | **FAIL as a rain source** (supports D6) | Owner's rule: monthly totals, only years with at least 330 records (2015, 2016, 2017, 2019, 2021, 2022), only complete months. **49 months: POWER 21.3% drier, r = 0.93, mean absolute error 46.8 mm per month.** Daily extremes are worse: POWER's wettest day is **2025-03-01 at 233.7 mm, in the dry season, when the station had 3.8 mm**; 2024-06-26 has 114.3 mm vs 4.3 mm. The real Kathmandu flood of 2024-09-27/28 (station 97.0 + 194.1 mm) shows in POWER as only 76.3 + 93.3 mm. The range guards cannot catch these (all values are physically possible); only the cross-check did |
| 3.8 | Cross-check: POWER temperature vs station | **Tmax PASS, Tmin FAIL** | See 3.4 and 3.5. Consequence: frost from POWER alone would be badly undercounted; step 8 needs a correction or another source |
| 3.9 | Cross-check: GPM IMERG vs POWER vs station rain | **NOT YET POSSIBLE** (login) | Step 6. Day boundaries differ: IMERG UTC, POWER local solar time, station unknown (0 of 12,147 records give an observation time), so compare monthly |
| 3.10 | Cross-check: MODIS vs HLS NDVI, 2013 on | **NOT YET POSSIBLE** (login, field outline) | Step 6 |

## Layer 4: Believable

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 4.1 | The worst replay years match known dry years | **NOT YET POSSIBLE**: no replay. A sourced list of known dry years is also needed (TODO) | Step 5 |
| 4.2 | Twin stress agrees with satellite greenness, year by year | **NOT YET POSSIBLE** | Steps 5 and 6 |
| 4.3 | Ups and downs match FAOSTAT national yields | **NOT YET POSSIBLE**: FAOSTAT is not fetched yet (a new source; it will be logged in CREDITS.md when used) | Step 5 or 7 |
| 4.4 | The best plan survives small threshold changes | **NOT YET POSSIBLE** | Step 7 |
| 4.5 | Season detection: thresholds vs change-point vs SI season detective on held-out years (SI components 1; placement in layer 4 is my choice, TODO-CONFIRM) | **NOT YET POSSIBLE** | Step 6 |
| 4.6 | Field memory beats physics alone on held-out years, reported either way (SI components 2) | **NOT YET POSSIBLE** | Step 7b |

## Layer 5: Probe

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 5.1 | Calibration in air and in water | **NOT YET POSSIBLE** | Step 10 (hardware) |
| 5.2 | Five readings of one cup barely differ ("barely" needs a number: TODO-CONFIRM) | **NOT YET POSSIBLE** | Step 10 |
| 5.3 | Dry, damp and wet cups come out in order | **NOT YET POSSIBLE** | Step 10 |

## Layer 6: People

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 6.1 | Someone new reaches "Your plan" in two or three minutes unaided (manual; record who, when, time taken) | **NOT YET POSSIBLE**: no UI in this folder | UI teammate |

## Outside the six layers (housekeeping)

| Check | Result |
| --- | --- |
| `.gitignore` keeps `data/` and secrets out and `site/data/` in | **PASS** (`/data/` fix from step 1 holds; 19 tests) |
| Backup leaves out `data/` and secrets | **PASS** (3 tests; real run logged in SI_LOG.md) |
| CLAUDE.md complete | **FAIL**: the file on disk still ends mid-word ("…replaces an agronomi"). The complete version you mentioned is not in this folder |
| Contract conflicts from step 1 (A13) | **PASS**: futures are now ranges; month words are closed lists |
| Guard vs product ranges (A9) | **PASS** by decision D2 (product range is the hard limit; rule 12 gives warnings) |
| Switch-off test | **FAIL (expected)**: no export uses real data yet, so removing any dataset changes nothing (DATA_AUDIT.md section 4) |

## Totals

Layer checks run today: **5 PASS** (1.1, 1.2, 3.2, 3.5, Tmax in 3.8), **4 FAIL** (3.1 POWER rain,
3.4 POWER January nights, 3.7 POWER rain vs station, Tmin in 3.8), and 1 estimate (3.1b).
**NOT YET POSSIBLE: 18** (1.3, 2.1 to 2.3, 3.3, 3.6, 3.9, 3.10, 4.1 to 4.6, 5.1 to 5.3, 6.1).
Housekeeping: 4 PASS, 2 FAIL (CLAUDE.md incomplete; switch-off, expected at this stage).
The failures are about POWER, not about the code. They support using IMERG for rain (D6) and show
that frost needs more than POWER's night temperatures.
