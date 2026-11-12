# VALIDATION.md

Updated 2026-11-12 (later): the owner's step-4 review answers, the parts of build step 5 that do not need GPM,
and the move to a labelled PLACEHOLDER field (27.67 N, 85.43 E is Bhaktapur's old city; the field is now a 60 m square at 27.690767 N, 85.441792 E, the owner's candidate 1 moved 25 m north, replacing the 100 m square at 27.6785 N, 85.427417 E). Each check was run
today unless it says **NOT YET POSSIBLE**. Results are in `data/checks/demo/`, data cards in
`data/cards/demo/`, plots in `data/plots/demo/`; all are copied into `review_pack/`.

Result words: **PASS** · **FAIL** · **NOT YET POSSIBLE** (reason, and the step that unblocks it).

**How to read the evidence (owner, 2026-11-12):**
- Temperature checks against Kathmandu Airport are labelled **fitted reference**: the correction was
  fitted to that same station, so agreement with it is partly by construction.
- The **independent evidence** is the held-out-year results and the comparison with the sourced
  known events. Held-out years are **independent in time only** (REVIEW_NOTES M8): they do not test
  whether the airport (synoptic-derived, GHCN S-flag `S`, urban, about 7.4 km away) represents the field, nor
  whether offsets fitted on 2015-2023 hold for 2001-2014 (POWER warns of source changes over the record).
- Every Kathmandu Airport value is **synoptic-derived: use with caution** (GHCN S-flag `S` on every record;
  REVIEW_NOTES H2, DATA_AUDIT 1.11), above all for rain.
- The pyet comparison is **not independent** (same algorithm); FAO-56's printed worked examples are
  the independent check of the equations.

## Layer 1: Runs

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1.1 | Tests pass | **PASS**: 466 passed, 0 failed, deprecation warnings treated as errors; also after earthaccess downgraded python-dateutil to 2.9.0.post0 | `pytest -W error::DeprecationWarning` (guards 67, schema 54, twin_water 51, crops_lib 31, replay 23, power 22, gitignore 19, et0 19, spikes 13, weather 11, season 11, mock 11, checks_climate 11, qmap 9, ghcn 9, bias 9, review_pack 8, crosscheck 8, soilgrids 7, gpm 7, faostat 6, cogwindows 6, build_field_json 6, scan_history 5, rain_merge 5, nasadem 5, fields 5, events 5, worldcover 4, known_events 4, appeears 4, rules 3, grace 3, backup 3, credits 2) |
| 1.2 | Every export validates | **PASS**, with a warning: `demo.json` is still MOCK data, now at the placeholder field (name says PLACEHOLDER; index bbox = the fetch box) | `python -m pipeline.export.validate`: 2 files, 0 problems |
| 1.4 | The placeholder field is cropland | **PASS for the chosen field** (27.690767 N, 85.441792 E, 60 m; candidate 1 moved 25 m north by the owner, 2026-11-12, because the Kasan River's strip ran along its southern edge on Google Maps). The square and its 30 m margin are all WorldCover 2021 cropland (210 cells). HLS passes the simple greenness test in both seasons of 2023-2025 (lowest seasonal peak 0.784; winter rise 0.59-0.64 after the rice harvest); the test is a monthly NDVI peak above 0.25, which grass, weeds and trees also pass, so it cannot show a crop (REVIEW_NOTES M11). The 4 sampled pixels' footprints reach up to about 15 m beyond the 60 m square. None of the 9 covering HLS pixels holds a WorldCover tree cell; the nearest is 142 m north. **Exceptions:** its 30 m margin is 77 m from the nearest built-up pixel, against the search's 100 m: **accepted by the owner, 2026-11-12** as an exception to the 100 m rule. The river strip is too narrow to see in these data: the covering pixels stop about 6 m north of the river line as described, and the 4 pixels the season test uses stop about 36 m short. **FAIL for the first placeholder** (owner, satellite view: a construction plot beside new buildings, although WorldCover 2021 calls it cropland). Its HLS record through Dec 2025 still passes the simple bare-soil test (both seasons above NDVI 0.25) but shows **no winter crop** (winter peaks 0.39-0.45 vs monsoon 0.68-0.73, no rise after the rice harvest). | `placeholder_candidates.json` (`chosen_field`, `earlier_placeholders`), `placeholder_candidates.png`, `placeholder_field.png`; REVIEW_NOTES.md H3 |
| 1.5 | Silent failures in the replay (ECC kit review) | **PASS after fixes**: 10 findings checked; NaN inputs, date gaps, POWER outside the GPM record, unknown water source, null events, an empty held-out split and a soil holding no water now stop loudly (tests in `test_replay.py`, `test_build_field_json.py`, `test_qmap.py`) | METHOD_NOTES.md item 15 |
| 1.2b | The replay export refuses what it must refuse | **PASS** (tests): non-GPM rain, a record that is not 2001-2025, a year without an event; it changes only `replay.current` and the result validates. Real run: **NOT YET POSSIBLE** (no GPM): `build_field_json` prints NOT YET POSSIBLE and leaves `demo.json` unchanged | `tests/test_build_field_json.py` |
| 1.3 | The UI loads it | **NOT YET POSSIBLE**: no UI code in this folder | UI teammate |

## Layer 2: Equations

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 2.1 | ET0 matches pyet within 3% (30 real POWER days) | **PASS, not independent**: largest difference 0.0000%; pyet codes the same FAO-56 algorithm with the same constants | `tests/test_et0.py` |
| 2.1b | ET0 reproduces FAO-56's printed examples (**independent**) | **PASS**: Example 2 (P 81.8 kPa, gamma 0.054), Example 8 (Ra 32.2), Example 18 (Rso 30.90, Rnl 3.71, Rn 13.28, **ET0 3.88 mm/day**) | `tests/test_et0.py`, values from fao.org |
| 2.1c | Crop coefficient curve, TAW/RAW, Ks and daily depletion reproduce FAO-56's printed examples (**independent**) | **PASS**: Examples 28 and 30 (Kc on given days), 36 (TAW, RAW for 3 crops x 3 soils), 37 (ten days of Dr, all within 0.15 mm), 39 (Ks at 7 depletions) | `tests/test_twin_water.py` |
| 2.1d | SCS runoff reproduces published values (**independent**) | **PASS**: 10 cases from TR-55 Table 2-1 and NEH 630 Example 10-1 (TR-55 Example 2-4 left out: it used a rounded S) | `tests/test_twin_water.py` |
| 2.2 | Water balance closes within 1 mm per season | **PASS**: synthetic seasons with and without irrigation close within 1e-6 mm, counting the irrigated paddy's pond water once, as irrigation; rain-fed rice now gets no outside water (REVIEW_NOTES H1; before the fix the balance closed only because the rain-fed pond's unsourced top-up was counted as an inflow). The real 2016 test year and the station-rain dry run (3 windows × 2 cases, rice then potato) close to **0.0000 mm** | `tests/test_twin_water.py`, `test_season.py`, `test_replay.py`, `season_2016.json`, `replay_station_dryrun.json` |
| 2.3 | Extremes behave | **PASS**: 60 dry days drive Ks below 0.3; steady rain keeps Ks at 1; harvest stays 0 to 100 for dry, normal and very wet seasons; with irrigation a rainless season has no dry day and 100% harvest, and bare soil is never irrigated | `tests/test_twin_water.py`, `test_season.py`, `test_replay.py` |
| 2.4 | Irrigation was never applied (bug found 2026-11-12) | **FIXED**: `season.simulate` passed the irrigated flag to the paddy rule only, so irrigated wheat was never watered. Now wired, with the refill at the start of the day (CLAUDE.md "refill when Dr > RAW"). Rain-fed wheat 2016 is now **59.1%** in the one-season test (weather table rebuilt 2026-11-12 with ea held, M6). The **44.2%** the same season gets inside a wheat→rice replay is not a contradiction (REVIEW_NOTES M13a): same weather, but the replay starts wheat with the root zone left 44% depleted by the rice before it (Dr 43.3 of 194.4 mm on 29 Oct 2015, against 0.5 mm in the one-season run); running wheat alone from each start reproduces both numbers. The old 59.6% vs 55% pair was the same effect | `tests/test_season.py`, `test_twin_water.py`; `season_2016.json` |

## Layer 3: Data sensible

Data: NASA POWER (model-based, one cell), the twin's weather table (POWER with the Kathmandu-valley
correction), and NOAA GHCN-Daily station NP000444540 Kathmandu Airport.

| # | Check | Result | Numbers |
| --- | --- | --- | --- |
| 3.1 | Kathmandu yearly rain roughly 1,400 to 1,500 mm (band 1,260 to 1,650) | **FAIL for POWER** | POWER mean 1,150 mm; 2001-2003 about half of later years. The twin's rain will be GPM (D6) |
| 3.1b | Same, at the station | **NOT YET POSSIBLE** (no complete year) | Estimate only: about 1,460 mm |
| 3.2 | Mostly June to September | **PASS** | POWER 78.1%. The 2016 station rain in the season test: 1,032 mm fell in the 110-day rice season |
| 3.3 | Onset near 10 June | **NOT YET POSSIBLE** (GPM download running; EULA accepted 2026-11-12) | Step 6 |
| 3.4 | January nights 0 to 5 C | POWER raw **FAIL** (7.17 C); station 3.72 C and twin input 3.07 C **PASS (fitted reference)** | The independent part is 3.11 |
| 3.5 | Early-summer days 27 to 33 C | **PASS** (POWER 29.5 C); twin input 29.3 C and station 29.4 C are **fitted reference** | |
| 3.6 | Greenness peaks in the monsoon | **NOT YET POSSIBLE**: HLS and MODIS are downloaded; the diary is step 6 | Step 6 |
| 3.7 | POWER rain vs station (monthly) | **FAIL as a rain source** | 49 months: POWER 21.3% drier, r 0.93, MAE 46.8 mm/month. The station rain is synoptic-derived (S-flag `S`; use with caution), so part of the gap may be the station's |
| 3.8 | POWER temperature vs station, before correction (**fitted reference**) | **FAIL** | Tmin +3.8 C in January; Tmax -1.67 C over the year |
| 3.9 | GPM vs POWER vs station rain | **NOT YET POSSIBLE** (GPM download running) | Step 6; the three-source vote is built and tested, waiting for GPM. The station is synoptic-derived (use with caution) |
| 3.10 | MODIS vs HLS NDVI | **NOT YET POSSIBLE**: both are downloaded for the box (AppEEARS; HLS windows) | Step 6 |
| 3.11 | Temperature correction on held-out years (**independent in time only**; station synoptic-derived) | **PASS for Tmin and Tmax; RH not possible** | Tmin MAE 2.31 → 1.22 C (n 714; test 2016, 2019, 2022); Tmax MAE 2.25 → 1.16 C (n 1,303). The station has no humidity |
| 3.12 | Cross-source spike check | **RUN: 9 days flagged**, none deleted | Unchanged from step 3; the vote labels them once GPM exists |
| 3.13 | Day alignment | **PASS: lag 0** | Pearson 0.634 at lag 0 vs 0.387 / 0.264 at -1 / +1. This shows no whole-day shift does better; it does not establish a common day boundary (station observation time unknown) |
| 3.14 | Cold nights: quantile mapping vs monthly offset, held-out years 2016, 2019, 2022 (**independent in time only**; small samples: the coldest-night error rests on 3 Januaries (offset 1.76, 1.59, 5.14 C; QM 1.00, 1.19, 4.74 C, so QM is closer in all three by 0.4-0.8 C) and the nights-below-2 C count on 9 station nights (exact Poisson 95% range 4.1-17.1: QM's 15 lies inside, the offset's 22 does not; cold nights cluster, so the true range is wider)) | **Both used, each for its job** (owner, 2026-11-12): offset for the twin's temperatures and ET0 (`tmin_c`), QM for frost only (`tmin_frost_c`) | MAE: offset **1.22**, QM 1.34 C. Error in each January's coldest night: offset 2.83, **QM 2.31** C. Nights below 2 C (station 9): offset 22, **QM 15**. Both overcount, so frost is shown as risk bands with the caveat, never a count. Over 2001-2025 the frost Tmin has 28 nights below 0 C, the offset Tmin 55 |

## Layer 4: Believable

| # | Check | Result | Notes |
| --- | --- | --- | --- |
| 4.1 | The worst replay years match known dry years | **Replay built; full comparison NOT YET POSSIBLE** (needs GPM rain) | `config/known_events.yaml`: 20 sourced events, 2 negative controls. **First match (independent):** the step-4 test year gives wheat in winter 2015/16 only 32 mm of rain, ETa/ETc 0.64, 63 stressed days, harvest 59% of potential; the list documents the 2015/16 winter drought (national wheat -11%, FAO GIEWS). One year, temporary station rain (synoptic-derived), rain-fed assumption: not yet evidence for the method. **Dry run (rerun 2026-11-12 after the H1/H4/M1 fixes, TEMPORARY station rain, never exported; years with station rain on 90%+ of days: 2015-17, 2019, 2021-22; placeholder rotation rice then potato; rain-fed):** rice 2015 99.3% with 8 dry days, so the **2015 monsoon drought is still a miss** (a monsoon that is late before transplanting is invisible); rice 2016 100%, 2017 98.0% (25 dry days), 2019, 2021, 2022 100%: **3 of 6 rice seasons at exactly 100%** (all 6 before the fix); potato 2016 32.8%, 2017 29.2%, 2022 66.4% (rain-fed potato suffers in dry valley winters; FAO's calendar treats winter crops here as irrigated). Year harvests 2016 66.4, 2017 63.6, 2022 83.2. Events: flood 2015, 2019, 2021; **drought never fires**, because windows with 1-3 seasons per crop cannot reach decile 2. Irrigated: 100% and 0 dry days every year; rice irrigation (all pond water) 140-223 mm a season, potato 136-211 mm. Not evidence: six windows of station rain |
| 4.1b | Cold waves in the corrected temperatures | **Mixed (caveat stays)** | Jan 2018: corrected 0.7 C vs station 0.0 C. Jan 2013 coldest corrected night -4.2 C vs reported -1.1 C (offset over-corrects). Held-out Januaries (station / offset / QM): 2016 2.5 / 0.7 / 1.5; 2019 1.0 / -0.6 / -0.2; 2022 3.8 / -1.3 / -0.9 C |
| 4.2 | Twin stress agrees with satellite greenness by year | **NOT YET POSSIBLE** | Steps 5, 6 |
| 4.3 | Ups and downs match FAOSTAT national yields | **Data ready; comparison NOT YET POSSIBLE** | Nepal rice, wheat, maize 2001-2024. Wheat 2016 is 2,329 kg/ha after 2,591 in 2015, the year the test season shows wheat stress; one year is not a comparison |
| 4.4 | The best plan survives small threshold changes | **NOT YET POSSIBLE** | Step 7 |
| 4.4b | Plan ranking with Ky 0.8 and 1.2 for crops whose Ky is assumed (owner, 2026-11-12) | **Ranking: NOT YET POSSIBLE** (step 7). **Replay of the placeholder rotation (rerun 2026-11-12): small change, rain-fed only.** Rice 2015 99.43 / 99.29 / 99.15% and 2017 98.39 / 97.99 / 97.59% at Ky 0.8 / 1.0 / 1.2; mean of the six rain-fed years 85.47 / 85.41 / 85.35; the 2017 year's site integer moves 64 → 63 at Ky 1.2. Irrigated: no change. The earlier "no change" came from the rain-fed paddy's unlimited water (REVIEW_NOTES H1), not from robustness | `plans/simulate.py` `ky_sensitivity`; `replay_station_dryrun.json` |
| 4.5 | Season detection, three methods | **NOT YET POSSIBLE** | Step 6 |
| 4.6 | Field memory beats physics alone | **NOT YET POSSIBLE** | Step 7b |

## Layer 5: Probe

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 5.1 | Calibration in air and in water | **NOT YET POSSIBLE** | Step 10 |
| 5.2 | Five readings of one cup barely differ ("barely" needs a number: TODO-CONFIRM) | **NOT YET POSSIBLE** | Step 10 |
| 5.3 | Dry, damp and wet cups come out in order | **NOT YET POSSIBLE** | Step 10 |

## Layer 6: People

| # | Check | Result | Unblocked by |
| --- | --- | --- | --- |
| 6.1 | Someone new reaches "Your plan" in two or three minutes unaided (manual) | **NOT YET POSSIBLE**: no UI here | UI teammate |

## Outside the six layers (housekeeping)

| Check | Result |
| --- | --- |
| `.gitignore` keeps `data/` and secrets out and `site/data/` in | **PASS** (19 tests) |
| Backup leaves out `data/` and secrets | **PASS** |
| CLAUDE.md complete | **PASS** |
| Full git history secret scan (H) | **PASS** on 2026-11-11 (1 commit, 0 hits); rerun before going public |
| Every threshold in `config/rules.yaml` and every crop value in `config/crops.json` has a source | **PASS** (`tests/test_rules.py`, `tests/test_crops_lib.py`) |
| Switch-off test | **FAIL (expected)**: exports are still MOCK |

## Totals

Layer checks run today: **PASS 15** (1.1, 1.2, 1.2b tests, 2.1, 2.1b, 2.1c, 2.1d, 2.2, 2.3, 3.2, 3.5,
3.11, 3.13, and 3.4 for the station and the twin input, both fitted reference), **FIXED 1** (2.4
irrigation bug), **FAIL 4** (3.1 POWER rain, 3.4 POWER raw, 3.7, 3.8 before correction), **decision
recorded 1** (3.14: both, each for its job), **run with findings 4** (3.12, 4.1 dry run: 1 match,
1 miss, 1 unexplained; 4.1b; 4.4b replay part), **data ready 1** (4.3), **NOT YET POSSIBLE 16** (1.3,
3.1b, 3.3, 3.6, 3.9, 3.10, 4.2, 4.4, 4.4b ranking, 4.5, 4.6, 5.1, 5.2, 5.3, 6.1, plus the full 4.1
replay comparison and the real 1.2b export).
