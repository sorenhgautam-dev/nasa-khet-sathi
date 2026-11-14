# REVIEW_2.md

Independent review, 2026-11-13 (Friday), by Claude Fable 5.2 via Claude Code (an AI review; logged in SI_LOG.md and
CREDITS.md). Working tree at `f37ecc6` plus 33 modified and 24 untracked files (steps 6b, 6c, 7 and the rain fix are
not committed).

**How it was done.** One main session, the only one that edits files, plus ten read-only sub-reviewers it started
(twin physics; events and diary numbers; weather and corrections; the rain break; satellite greenness; plans;
static data and the switch-off trace; export and site; security, licences and probe; documents). Each recomputed
its slice with its own code from the primary sources (FAO-56, FAO-33, TR-55, product files and user guides) and
compared with the project's functions and stored outputs. The main session then re-ran the findings marked **(M)**
itself. Sub-reviewer scripts are in the session scratchpad, not in the repository. No project file changed during
Phase 1 (305 file hashes identical before and after).

**Status** under each item: OPEN, FIXED (date), or OWNER (waits for a decision; the questions are numbered at the end of
the review part).

**Where things stand after Phases 2 to 4 (the same afternoon).** Everything that could be fixed without changing a
method, rule, threshold, result or the contract is fixed, tests first (871 tests before, 898 now; `demo.json` changed only
in two `sources` rows, in `method.choices` and in one evidence range on the method page). The accuracy runs are done:
the two suggested rotations hold under every perturbation tried, the size of their gain does not; DHM's own 2025 gauges
support the rain fix for the months it covers and show the 92 unscaled days are too wet; SMAP agrees moderately with the
twin and cannot judge the fix. What remains is the owner's: 19 questions, of which the first nine decide what a farmer
reads. Phases 2, 3 and 4 are written up after the questions.

---

## Verdict

The engine is sound. ET0, the crop coefficients, the bucket, runoff, yield, the temperature correction, quantile
mapping, the rain correction, onset, seasons, events, trends, scores and the plan selection all reproduce from
independent code, to rounding, on the real data. A fresh environment installs and 871 tests pass. No secret is in
the repository or its history.

The entry is **not ready to freeze**. There is no website to judge. Two blocks of the export are still made up.
Several things a farmer would read say more than the numbers support (the "Safest in bad years" name, the tips,
"empty 62 days", a winter crop the satellite does not see). The rain fix removed the 2017 jump but the twin's rain
is still about a third above the local normals, and the sentence that said so has dropped out of the export. The
validation log is about 25 statements behind the code, and the credits do not yet credit the rain dataset.

Nothing found suggests a threshold was tuned to pass a check and then hidden.

## The five most important problems

1. **C1. There is no site.** `site/` holds two JSON files; GitHub Pages is off; the live address returns 404; GitHub
   `main` is three contract changes behind this laptop.
2. **H1. Made-up numbers are still in the export.** `field.sections` (with four invented probe temperatures) and
   `future` come from `mock.py`, with nothing a program can read to tell them from results.
3. **H2 and H3. The plan story overreaches.** "Safest in bad years" is worse in bad years than the other suggested
   plan; the order of the plans depends on rooting depths taken at the top of FAO's ranges; rain-fed rice never
   fails, so the winter crop alone ranks the plans; the twin's winter crop sits ten weeks before the crop the
   satellite shows; two tips rest on almost nothing.
4. **H4. Rain is still high, and less is said about it than before.** After the fix the twin has 1,856 mm a year
   against DHM's 1,375 mm for Bhaktapur; the "may read high" lines no longer appear; the 92 un-scaled Late days
   hold the record's wettest day (272 mm against 113 mm at the nearest gauge); both negative controls fail in the
   exported run while VALIDATION says they pass.
5. **H5, H7, M1. The record is behind the work.** Machine-drafted English and Nepali are exported with no person's
   review; CREDITS says GPM is "not yet downloaded"; three licence notices are missing; VALIDATION still calls the
   export mock; and the secret scanner would miss the key shapes step 10b will bring.

---

## Problems

### Critical

#### C1. No website, Pages off, GitHub behind (M)
- **Evidence.** `find site -type f`: only `site/data/index.json` and `site/data/fields/demo.json`; no HTML, JS or CSS
  is tracked. `gh api repos/sorenhgautam-dev/data-test-game/pages`: 404. `curl` of
  `https://sorenhgautam-dev.github.io/data-test-game/` and of `/data/index.json`: 404. All 4 workflow runs fail at
  `actions/configure-pages@v6` ("verify that the repository has Pages enabled"). `git show HEAD:site/data/fields/demo.json`
  has no `method` key, plans `current, cover_gap, follow_shift` with mock tabs and a mock diary; HEAD's schema lacks
  `uncorrected_rain`, `score_uncorrected_rain` and a nullable `shift_days`.
- **Why it matters.** Global judges see only the live site. A UI built against GitHub's contract breaks on the real
  file. Steps 6b, 6c, 7 and the rain fix exist only on this laptop and in backups.
- **Fix.** Owner: enable Pages (Settings > Pages > Source: GitHub Actions) and re-run the workflow. Owner's say-so
  to commit and push the working tree (suite and `scan_history.py` first), or hand the UI teammate today's
  `demo.json`, `schema.json` and `CONTRACT_CHANGES.md`. The UI needs a root `index.html` and relative fetches
  (`data/index.json`): the base path is `/data-test-game/`. The workflow file itself is correct (action versions
  exist; permissions right); no `.nojekyll` is needed.
- **Effort.** Pages 5 min; push 15 min; UI integration unknown (teammate).
- **Status.** Pushed 2026-11-13 (owner's answer 1). **Hosting moved to Vercel the same evening (owner; superseded 2026-11-14 night: GitHub Pages from this repository again, https://sorenhgautam-dev.github.io/data-test-game/):** Root Directory
  `site/`, no build step, no functions, no environment variables; the GitHub Pages workflow was removed and
  `scripts/check_site.py` guards relative paths and a fully static site. Still open: the UI itself (`site/index.html`).

### High

#### H1. `field.sections` and `future` are mock, unlabelled for a program (M)
- **Evidence.** `demo.json`: 12 sections from `pipeline/export/mock.py:26-43` (statuses cycling through the four
  colours, wetness 35..90 in steps of 5, `sure` 0.15..0.70); four carry probe temperatures 18.1, 18.4, 18.7, 19.0 C
  although the contract says `temp` is null until the probe has read; they cover 39.4 m x 33.4 m of the 60 m square.
  `future` is the CLAUDE.md example (`mock.py:113-115`). The only labels: `field.name` ends "(MOCK data)", which
  wrongly brands the real replay, plans and diary too, and one `sources` row. `schema.json` has no mock key;
  `build_field_json.py` never changes the name; `validate.py:142` only warns; `README.md:9` says "each one is marked
  as mock". `pipeline/sections/` and `pipeline/future/` hold only `__init__.py`.
- **Why it matters.** If steps 8 or 9 slip, judges see invented colours, temperatures and 2040 harvests until January.
- **Fix (recommended).** Contract: an optional top-level `"mock": ["field.sections", "future"]` written by the
  exporter; neutral sections (grey, `temp` null, `sure` 0) that tile the real square until step 8; the name loses
  "(MOCK data)" once only listed blocks are mock; `validate --final` fails while anything is mock.
- **Effort.** 1 h pipeline, plus a little UI work.
- **Status.** FIXED 2026-11-13 (owner's answer 2), tests first: a `mock` list names the blocks that are not computed; the
  export holds 36 real sections (10 m squares, `pipeline/sections/grid.py`) with no numbers and `future: null`; the name
  and the sources no longer say MOCK; the validator checks that a named block holds no numbers.

#### H2. "Safest in bad years" is not the safest plan shown; the plan order is not robust (M)
- **Evidence.** `data/checks/demo/plans.json`:

  | Plan | Harvest | 10th-percentile year | Worst year | Water | Cover | Soil kept |
  | --- | --- | --- | --- | --- | --- | --- |
  | cover_gap, rice then wheat | 89.6 | 83.8 | 79.8 | 50.8 | 68.5 | 74.4 |
  | safest, rice then lentil | 80.8 | 75.6 | 73.6 | 44.5 | 66.6 | 74.2 |

  With lentil's assumed Ky at 0.8 or 1.2 its bad year is 80.5 or 70.7, still below wheat's 83.7. The lentil plan is
  in the Pareto set only through the pest-break and nitrogen flags. Its why-text says "Bad years hurt it less than
  now" (true against today's 66) and nothing says the wheat plan does better. `pipeline/words/fill_registry.json`
  `plan_is_safest` reads "for the plan that did best in bad years".
  **Rooting depth** (re-run of the project's simulator in memory; `config/crops.json` takes the larger FAO-56 Table 22
  value for every crop and `pipeline/twin/season.py:95-100` gives the full depth from sowing day):

  | Case (harvest / 10th-percentile year) | current | cover_gap | safest |
  | --- | --- | --- | --- |
  | as exported | 72.3 / 65.7 | 89.6 / 83.8 | 80.8 / 75.6 |
  | wheat at 1.0 m | 72.3 / 65.7 | 80.5 / 74.3 | 80.8 / 75.6 |
  | all four crops at the lower end | 66.1 / 59.0 | 79.7 / 73.4 | 76.2 / 70.2 |
  | winter crops limited to 0.6 m (a plough pan) | 72.3 / 65.7 | 71.7 / 66.4 | 76.7 / 71.6 |

  With wheat at 1.0 m the two suggested plans tie and the gain is +8, not +17. With a 0.6 m limit the wheat plan no
  longer keeps today's harvest, which its own rule requires. VALIDATION 3.19 says "Robust"; 4.4 swept only years, Ky
  and rain.
  **Rice never fails:** current-plan rice is 100.0% in 22 of 25 seasons, lowest 99.7% (season rain 1,035-1,692 mm
  against ETc 436 mm), so a year's number is (100 + winter crop) / 2 and the winter crop alone ranks the plans:
  "about 18 more" is (wheat 79.3 - potato 44.5) / 2. The sourced monsoon droughts of 2009 and 2015 give rice 99.9
  and 99.8.
- **Why it matters.** A farmer picks the third plan for safety; a judge sees the "safest" card lower on every number.
  The headline benefit rests on one unverified soil-depth choice.
- **Fix.** (a) Record the depth sweep in VALIDATION 4.4 and METHOD_NOTES, drop "Robust" (done in Phase 2). (b) Owner:
  rename the third plan for what it gives (a pulse that feeds the soil and breaks the pest cycle), reword
  `why_safest`, correct the registry line; the id `safest` can stay. (c) Owner: show the harvest gain as a range, or
  use the smaller depth after paddy. (d) Owner: one "unknown" line saying the model's rice hardly ever runs short.
- **Effort.** (a) 20 min; (b) 30 min plus Nepali review; (c) 1-2 h; (d) 15 min plus review.
- **Status.** (a) FIXED 2026-11-13: VALIDATION 3.19 and 4.4 (the whole plan step rerun under 13 perturbations: the two
  suggested rotations hold in every case, the size of the gain does not), METHOD_NOTES 35-37. (b)-(d) OWNER (questions 3, 4).

#### H3. The twin's winter crop does not match the satellite, and tips rest on almost nothing (M for the tips)
- **Evidence.** HLS seasons 2014-2025 (threshold method): winter start 7 Jan, peak 18 Mar, end 18 May; monsoon
  17 Jun / 21 Aug / 30 Oct. The placeholder plan grows potato 30 Oct to 21 Feb. On the simulated potato days the
  satellite's labels are growing 45%, bare 44%, harvested 11% (median NDVI 0.27; observed median NDVI 0.18 on 1 Dec,
  0.80 on 15 Mar). Day-by-day agreement of "crop on the ground" between twin and satellite: 53% (rice alone 97%).
  Inside one file: `diary.months` says Nov bare, Dec bare, Mar crop; `plans[0].tips[2]` says "Cover bare soil with
  straw in March" (`pipeline/plans/explain.py:148` takes bare months from the plan calendar, while
  `fill_registry.json` says the tip comes from the diary); the cover_gap why-text says "Your field is empty 62 days a
  year. Wheat can grow in that empty time", pairing the satellite's 62 bare-ground days (mostly Nov-Dec) with a
  plan that swaps potato for wheat in the same slot and still leaves 4 March to 14 June empty (cover 61.6 to 68.5 =
  25 more crop days).
  **Tips:** "Rice gets most thirsty in October. Water it then if you can." rests on 16 dry days in 25 seasons, in 3
  seasons, in the last days before harvest on 10 October (`explain.py:141-147` has no minimum). The Nepali names
  कात्तिक (from about 18 October) for days that fall in असोज. The other plans' "in June" rests on 27-28 days in 25
  seasons.
- **Why it matters.** Every winter number of the current plan (potato harvest, dry days, winter droughts, the
  "thirsty in January" tip) is computed about ten weeks before the crop the satellite shows. Tips are advice.
- **Fix.** Owner: (a) a floor before a "thirsty" tip is shown (or no rice tip); (b) take the straw tip's months
  from the satellite diary for the current plan, or drop it where the diary says "crop"; (c) reword "empty 62 days"
  to what it is (bare ground on about 62 days) and fill the plan's gain from the plan calendar; (d) decide the
  placeholder winter calendar with the real farmer (potato's second FAO window, 15 Nov to 15 Dec, or wheat, fits
  the observed season). Not tuned here: these are text and placeholder choices.
- **Effort.** (a)-(c) 1-2 h plus Nepali review; (d) 1 h of reruns.
- **Status.** OWNER (questions 5, 6). Recorded in METHOD_NOTES 40, VALIDATION 4.2 and CONTRACT_CHANGES.

#### H4. Rain: the level, the 92 Late days and the negative controls (M)
- **Evidence.**
  - *Level.* `weather.parquet`: twin rain 1,856 mm a year (2001-2016 1,842; 2017-2025 1,882) against DHM 1991-2020
    normals of 1,374.7 mm (Bhaktapur) and 1,502.0 mm (airport): 1.35x and 1.24x. VALIDATION 3.1's band is 1,260 to
    1,650 mm, so the twin's own rain fails 3.1 and the row does not say so. `build_field_json.py:337-339` shows the
    "airport measures less" lines only for a 25-40% gap against the station; after the fix the ratio is 1.088, so
    `unk_rain_space`, `unk_rain_airport`, `unk_rain_airport_miss` and `unk_rain_which` appear in no tab, while
    METHOD_NOTES item 21 and CLAUDE.md still say the tab says so.
  - *Late days.* 2025-10-04 is 272.2 mm (IMERG Late, not scaled), the largest of 9,131 days. DHM's bulletins for
    that storm: Bhaktapur 112.8, airport 104.5, Nagarkot 96.0, Changu Narayan 84.2 mm (sub-reviewer, bulletins
    downloaded today). Twin October 2025: 427.7 mm against 204.8 / 210.5 / 197.7 mm at the three gauges. The Late
    check itself shows Late sits at the un-gauged level (Final/Late 0.64-0.85 in 2014-2016, 1.00-1.13 after). A
    what-if with the Late days scaled changes no replay year and no event in the current plan (wettest day 217.9 mm,
    still flood-class).
  - *Negative controls.* In the exported (corrected) run the 2023 **rice** season is drought-flagged (1,148 mm, rank
    4 of 25, decile 2), and DHM has that monsoon at 107% of normal in Bhaktapur. VALIDATION 4.1 says "the 2023 and
    2025 flags come from the winter potato seasons, not the monsoons", which was true of the uncorrected run only.
    The correction restores the level after 2016, not the order of the years.
  - *New independent support* (sub-reviewer, three IMERG Final months of 2025 against DHM's own gauges): GPM as
    published 1.27x, twin 0.88x; monsoon 2025 at the airport: DHM 1,200 mm, GPM 1,823, twin 1,286.
- **Why it matters.** Rain drives every replay number. The fix is sound for what it does, but the export now says
  less about the remaining doubt than it did before the fix.
- **Fix.** (a) Correct VALIDATION 3.1, 4.1 and METHOD_NOTES 21 (Phase 2). (b) Owner: one "unknown" line that the rain
  may still read high, keyed on the DHM-normal ratio. (c) Owner: scale the 92 Late days with the same factors
  (recommended) or label them. (d) Add the DHM bulletin comparison as a validation row (Phase 3).
- **Effort.** (a) 20 min; (b) 30 min plus review; (c) 30-45 min plus re-export; (d) 1 h.
- **Status.** (a) FIXED 2026-11-13 (VALIDATION 3.1, 3.9b, 4.1; METHOD_NOTES 21). (d) FIXED: VALIDATION 3.9c,
  `scripts/run_dhm_bulletin_check.py` (twin 0.88 x DHM's gauges in the three Final months, 1.27 x as published; 1.97 x in
  the Late months). (b), (c) OWNER (questions 7, 8). Scaling the Late days would change only `soil_kept` of the two
  suggested plans, 74 to 75 (VALIDATION 4.4).

#### H5. Unreviewed SI text is exported; credits and licence notices are incomplete
- **Evidence.** All 337 text nodes in `pipeline/words/*.json` carry "needs native-speaker review"; SI_LOG says the
  English lines of 2026-11-13 are unreviewed too; `demo.json` ships `tabs`, `tips`, `tabs_ne`, `tips_ne` for three
  plans; nothing in the exporter or validator reads the mark. CLAUDE.md "Plans" step 5: "a person reviews every text
  before export". `CREDITS.md:116` says GPM IMERG, the twin's rain, is "fetcher built; not yet downloaded" (no DOI);
  lines 113-115 promise HLS and ECOSTRESS citations "when the downloads are cleaned"; MOD13Q1 has none; lines 44 and
  227 say SoilGrids "750 m" (it is 859 m); the SI table's "Reviewed by" is "to fill in" or "pending" in 11 of 13
  rows; `ensure_credit` is never called by `gpm.py`, `appeears.py`, `cogwindows.py`, `nasadem.py`, `grace.py`,
  `worldcover.py` or `soilgrids_wcs.py`. Licences: every Kathmandu Airport value has GHCN source flag `S` (Global
  Summary of the Day), whose readme restricts non-US data under WMO Resolution 40 ("shall not be provided to other
  users or be used for the re-export of commercial services"); `config/dhm_normals_1991_2020.csv` (156 DHM values,
  untracked, not ignored) would be published by the next commit and DHM states no open licence;
  `pipeline/words/crop_explainers.json` and `glossary.json` hold 21 verbatim quotes (18 from FAO, commonly CC
  BY-NC-SA 3.0 IGO); `LICENSE` is plain MIT with no "not covered" paragraph. Missing attribution lines: "Contains
  modified Copernicus Sentinel data" (HLS S30) and WorldCover's "(c) ESA WorldCover project 2021".
- **Why it matters.** Golden rules 10 and 11, the Space Apps AI-use declaration, and a public MIT repository.
- **Fix.** (a) CREDITS and SI_LOG brought up to date, attribution lines added (Phase 2). (b) Owner: who reviews the
  English and the Nepali, and by when; (c) Owner: keep the DHM table with a "(c) DHM, reproduced with attribution for
  validation, not MIT" notice (recommended) or move it under `data/`; add the GSOD notice; add a "not covered by MIT"
  paragraph to LICENSE.
- **Effort.** (a) 45 min; (b) 1-2 h of a person's time; (c) 20 min.
- **Status.** (a) FIXED 2026-11-13: CREDITS (GPM citation, product DOIs checked at doi.org, attribution lines, licence
  flags listed), SI_LOG. `ensure_credit` is still not called by seven fetch modules: OPEN. (b), (c) OWNER (questions 13, 15).

#### H6. A second field cannot be exported without code changes
- **Evidence** (sub-reviewer, a pretend field in a private copy). `build_field_json.py:288` reads an existing site
  file (only `mock.py` creates one, for `demo`); `:327` and `:336` read `rain_check_b.json` unconditionally; the
  exporter never writes name, lat or lon from `config/fields/<id>.yaml`; `sources_block()` (`:172-195`) is a
  hard-coded demo list, including the Kathmandu Airport station; only `mock.py` writes `index.json`.
  `scripts/run_rain_check.py:49,99,130-134` hard-codes the Bhaktapur and airport normals and needs a station.
  `scripts/run_diary.py:101-102` stops if a box spans two UTM zones.
- **Why it matters.** Judge requirement 2: fields abroad "through the same pipeline with no code changes". The
  gauge loss behind the 2017 break is Nepal-wide (GPCC stations in neighbouring boxes fall 11 to 0.8, 14 to 0.8, 7
  to 0, 5 to 0), and other countries have their own breaks.
- **Fix.** Build the skeleton and identity from the field config; build `sources` from the data cards; make the
  rain-check inputs optional (always run the station-free tests); add a `build_index` step. Tests first.
- **Effort.** 3-5 h. Part of build step 11.
- **Status.** OPEN: the first task of build step 11 in the plan below.

#### H7. The secret scanner misses the key shapes this project is about to hold (M)
- **Evidence.** `scripts/scan_history.py:14-22` tested with made-up strings: it misses `FIREBASE_API_KEY=AIza...`
  (the `.env` format; `\b` does not match between `_` and `API`), JSON `"apiKey": "..."`, `#define API_KEY "..."`,
  `#define WIFI_PASS "..."`, a bare `AIza...`, `?key=AIza...`, a Firebase `databaseURL`, `eyJ...` tokens and a netrc
  line for any host but Earthdata. `BAD_FILES` and `.gitignore` do not name `secrets.h`, `google-services.json`,
  `serviceAccount*.json` or `firebase-adminsdk*.json`. `CLAUDE.md:601` says the script "lets through the website's
  key by its exact value only"; no such code exists. The scan covers history, not the uncommitted working tree.
- **Why it matters.** It is the gate before every push, and step 10b adds a Firebase key and Wi-Fi firmware.
  Today's state is clean: the script exits 0 over 16 commits (all refs), an independent 24-pattern scan found
  nothing, and none of the `.env` values is in the tree or history.
- **Fix.** Tests first: add those patterns and file names, scan the working tree as well as history, build the
  allow-list as a SHA-256 of the website key. Correct the CLAUDE.md sentence until then.
- **Effort.** 1 h.
- **Status.** FIXED 2026-11-13 (owner's answer 14), tests first: the new key shapes and file names, the working tree scanned as
  well as the history, the website key let through by its SHA-256 only (`--hash-env` prints a hash, never a value);
  `.gitignore` names the firmware and Firebase secret files and `site/data/live.json`.

#### H8. POWER's 2001-2003 fault is also in temperature and humidity; the hot-day trend is an artefact (M)
- **Evidence.** `weather.parquet` yearly means: Tmax 27.34 / 27.56 / 27.24 C in 2001-2003 against 24.6-26.8 C in
  every later year; POWER humidity 51.8 / 51.8 / 51.9% against 56-71%; ET0 1,435 / 1,419 / 1,433 mm against a
  2004-2025 mean of 1,311 (2012 also reaches 1,440). POWER minus station Tmax on shared days is about 1.7 C higher
  in 2001-2003 than in 2004-2012, in every month; the station's own Tmax shows no warm spell. After the correction
  the twin's Tmax is still +0.5 / +1.8 / +1.2 C above the station in those years. Hot days per year
  (`data/checks/demo/diary.json`): 96, 139, 113, then never above 66. VALIDATION 3.17 and METHOD_NOTES 27 report
  "-1.66 days/yr, p 0.033"; from 2004 it is -0.47 days/yr, p 0.46. `scripts/run_diary.py:408` gives the hot-day
  trend no caveat. Only rain is flagged for those years today.
- **Why it matters.** A stated trend is wrong in the same way the heavy-rain rise was. Replay years 2002 and 2003
  use ET0 about 4-7% too high. The trend itself is not in `demo.json`.
- **Fix.** (a) Caveat in VALIDATION 3.17, METHOD_NOTES 27, DATA_AUDIT 1.1 and the diary output; show 2004-2025
  beside it (Phase 2). (b) Sensitivity run in Phase 3. (c) Owner: whether trends and the replay should start in 2004.
- **Effort.** (a) 30 min; (b) 1 h.
- **Status.** (a) FIXED 2026-11-13: `trends.without_years`, `rules.yaml trends.hot_day_caveat`, the diary output, VALIDATION
  3.17, METHOD_NOTES 27 and 41, DATA_AUDIT 1.1. (b) FIXED: with the ET0 of 2001-2003 lowered to the later level, 3 of 24
  years change by a point and no plan pick changes. (c) OWNER (question 11).

### Medium

#### M1. VALIDATION.md: about 25 stale or wrong statements; the Totals contradict the rows (M for a sample)
- **Evidence.** 871 tests (row 1.1 says 675); row 1.2 "demo.json is still MOCK data"; 1.2b "Real run: NOT YET
  POSSIBLE (no GPM)"; 3.3 and 3.6 "NOT YET POSSIBLE" although both can be answered (3.3 fails: median 16 May); 3.1
  silent on the twin's own rain; 3.9b says both "proposed, not applied" and "applied"; 3.12 "9 days flagged" (170
  flags on 120 days with GPM, all voted); 3.13 without the GPM lag; 3.15's detective scores for 2023-2025 are from
  the uncorrected run (now 0.977, 1.000, 0.955; mean 0.980); 3.17 leads with the uncorrected run; 4.1 "20 sourced
  events" (21), the negative-control sentence (H4) and "2020 is no longer flagged" (true for the current plan
  only); 4.1d "21 of 25" while the stored count is 19 (M10); 4.2, 4.3, 4.5 "NOT YET POSSIBLE"; 5.2 "27 tests" (34);
  housekeeping "1 commit" and "exports are still MOCK"; the Totals paragraph.
- **Fix.** Phase 2, row by row; new Totals.
- **Effort.** 1 h.
- **Status.** FIXED 2026-11-13 (about 30 rows corrected or added; new Totals).

#### M2. DATA_AUDIT.md: about 20 stale statements; the switch-off section no longer matches the code
- **Evidence.** Status rows for GPM ("Downloading"), MODIS and SMAP ("13 tasks still processing"); lines 93-97
  "proposed, not applied"; 1.3 "1,404 of 1,471" and "Pixels: NOT YET POSSIBLE"; 1.4 "MODIS: REQUESTED"; 1.8 "LSTE
  741, ESI 307" (769 and 310); 1.7 quotes the RH-held ET0 series; section 3 comparisons "NOT YET POSSIBLE"; section 5
  lists a card that does not exist and omits four that do; 1.6's valley-gap TODO-VERIFY is answered by ISRIC's FAQ
  (the mask comes from ESA land cover; urban class 190 is masked). Section 4 expects links the code does not have:
  HLS and MODIS to `plans.score.cover` (cover is calendar-based, `pipeline/plans/score.py:38-39`), SoilGrids K and
  NASADEM LS to `soil_kept` (they cancel, `score.py:9-11`), SMAP to `sure`, ECOSTRESS to section status.
- **Fix.** Phase 2; section 4 rewritten from the switch-off run in Phase 3.
- **Effort.** 1 h.
- **Status.** FIXED 2026-11-13 (stale lines; section 4 rewritten from the switch-off runs; section 5; 1.16 and 1.17 added).

#### M3. METHOD_NOTES, README, CLAUDE.md, CONTRACT_CHANGES: stale lines
- **Evidence.** METHOD_NOTES items 16, 18, 19 quote the 12 November run (yearly harvest 74.4 to 74.2, now 72.4 to
  72.3; potato 46.3 to 51.3, now 44.5 to 49.7; "11 of 24", now 12); item 21 "B Friday", "the tab says so"; item 24
  "about 10 June"; items 7 and 8 open questions that were decided. README: `:9` "each one is marked as mock";
  `:34-36` lists SMAP, ECOSTRESS and NEX-GDDP as used; `:75` runs the REST SoilGrids module, whose output the twin
  does not read; `:100` "the export fills in the replay only"; the how-to omits `run_diary.py`, `run_plans.py`,
  `run_rain_check.py` and the `--rain uncorrected` runs. CLAUDE.md: `:127` firmware "empty"; `:112-117` name eight
  files that do not exist; the contract example lacks `method`; `:523` "25 for 2001-2025" (24 for 2002-2025);
  `:601` (H7). CONTRACT_CHANGES `:3-4`, `:29`, `:144`; `:15`'s year list is right for `current` only.
- **Fix.** Phase 2 (CLAUDE.md: factual lines only).
- **Effort.** 1 h.
- **Status.** FIXED 2026-11-13 (CLAUDE.md: factual lines only, with "as built" notes where code and brief differ).

#### M4. Events: the same year differs between plans; "Very dry years: 7 of 24" is a quota (M)
- **Evidence.** `demo.json` `replay`: 7 of 24 years carry different events on different plans (2010, 2013, 2014, 2016,
  2019, 2020, 2022); 2020 is `none` for `current` and `flood` for the other two, because the 272 mm day of 4 Oct 2025
  falls between their crops (`pipeline/plans/events.py:28-40`). CONTRACT_CHANGES `:119` says "The event is about the
  weather". The drought rule flags the lowest fifth of each crop's seasons, so every field gets 5-9 such years by
  construction; flagged rice seasons had 1,035-1,193 mm and 100% harvest; 2015 is "a very dry year" with harvest 75
  against an average of 72. 2019's flag exists only because the unexported 2001 rice season is in the ranking.
- **Fix.** Docs now. Owner: one weather event per year for the field on every tab (a rule change), and reword or
  drop the count.
- **Effort.** Docs 15 min; rule 1-2 h.
- **Status.** Docs FIXED 2026-11-13 (VALIDATION 4.1, METHOD_NOTES 14, CONTRACT_CHANGES). Rule and wording OWNER (question 9).

#### M5. Soil: the cell used is the driest of 56 within 2 km, and the export never says it is 859 m away (M)
- **Evidence.** Raw SoilGrids maps: the cell used (859.3 m, bearing 134 degrees; all 8 neighbours masked) has TAW
  149.3 mm at 1.0 m; the 56 valid cells within 2 km run 149.3 to 186.8 (median 171.5, +15%); within 3 km (191
  cells) 138.0 to 186.8. With the next-nearest cells the current plan's mean harvest goes 72.3 to 74.5 and 74.8;
  over all cells within 3 km 71.2 to 75.9; events unchanged. `demo.json` has no "859"; the tab says only "Nearby
  parts share one soil map" (`pipeline/words/tabs.json:292`); the `sources` row says "soil texture and carbon"
  although the twin reads only the two water contents (`pipeline/twin/soil_water.py:29-36`).
- **Fix.** Sources row corrected with the 859 m note (Phase 2). Owner: a tab line, and whether to keep the nearest
  cell (recommended, with the range shown) or use the neighbourhood median.
- **Effort.** 15 min; tab line 30 min plus review.
- **Status.** `sources` row FIXED 2026-11-13 (names the water contents and the 859 m, read from the soil card). Tab line and
  the choice of cell OWNER (question 10).

#### M6. `sources`: MODIS changes nothing; some numbers have no source row (M)
- **Evidence.** `build_field_json.py:184-185` lists MODIS 2001-2013, but bare days, cover months, the guess and the
  method block use HLS years only (`scripts/run_diary.py:164-165, 428-430, 443-447, 452`). The station row says
  2001-2025 (the record ends 2025-08-24). `method.rain_correction.gauges` (then 96-97% to 56-72%; 50 to 1 stations) were
  constants typed into `config/rules.yaml:222-224` with no raw file, fetch code or card; `station_normal` 1375 comes
  from the hand-transcribed DHM table; neither has a `sources` row. `PLAN_SOURCES` omits HLS although the cover_gap
  why-text uses the HLS count.
- **Fix.** Reword the MODIS row ("checked against HLS; no number shown uses it"), fix the station years (Phase 2);
  fetch the gauge-weight and GPCC evidence with cards (Phase 3); a DHM row needs a schema enum decision (owner).
- **Effort.** 20 min; Phase 3 1 h.
- **Status.** FIXED 2026-11-13: the MODIS row reworded; `pipeline/fetch/gauge_evidence.py` fetches the gauge weight and the
  GPCC counts with a card (DATA_AUDIT 1.17). OPEN: a DHM row in `sources` (needs the owner: schema enum) and HLS in the
  plans' evidence lines (farmer text).

#### M7. `method.choices`: approved choices shown as unapproved; the one post-hoc rule is missing (M)
- **Evidence.** `build_field_json.py:157-161` matches `owner-approved` case-sensitively, so entries whose source
  starts "Owner-approved 2026-11-13" export as plain "Claude's choice" (7 entries carry that status in `demo.json`);
  `plans.third_plan_rule` ("added by Claude AFTER the first run ... Put to the owner") is not listed because its
  text says "added by Claude", not "Claude's choice"; blocks no code reads (`rain_vote`, `et0`, `paddy_rice`,
  `crop_calendar`, `probe`, `ecostress`) are listed as rules in force.
- **Fix.** Tests first: case-insensitive match; include the third-plan rule. Re-export.
- **Effort.** 30 min.
- **Status.** FIXED 2026-11-13 (tests first; re-exported: 5 choices now read owner-approved, 2 entries added). The
  documentation-only blocks are still listed: OPEN.

#### M8. Labels that say more than the evidence
- **Evidence.** "Floods: independent" (VALIDATION 4.1, METHOD_NOTES 14, rules.yaml events.flood_decile_min): SI_LOG
  `:184` and `:320` show the 100 mm and 200 mm versions had been run and the two valley floods were known to be
  among the wettest days before the decile rule was written; a top-fifth rule catches them by construction. 4.1c
  "PASS": January 2010 is "high" because of 1 January (-0.59 C); on the documented night (12 Jan, -0.2 C) the frost
  Tmin is +3.5 C; 7 of 25 Januaries are "high"; the numbers had been looked at the day before the band rule was
  set. 3.14 and 3.9b: the held-out sets that report each error were also used to choose (offset or quantile mapping;
  which of two rain corrections); the rain test's even-year half has station data for 2022 only. A single yearly
  factor (0.676) scores the same as the twelve monthly ones (93.7 to 32.2 mm); the dry-month factors are noise
  (bootstrap 95%: Nov 2.40 [1.58, 3.65] on 7 mm; Dec 0.46 [0.21, 1.43]). "Fixed before it was run" (steps 6b, 6c, 7)
  rests on SI_LOG alone: none of those rules is in a commit. "Tested 2016, 2019, 2022; fitted on 2015-2023" is true
  for Tmin only (Tmax: fit 2001, 2015, 2017, 2019, 2022; test 2005, 2016, 2018, 2021, 2023).
- **Fix.** Reword in VALIDATION, METHOD_NOTES and rules.yaml source texts (Phase 2). From now on commit a rule locally
  before its first run (owner).
- **Effort.** 30 min.
- **Status.** FIXED 2026-11-13 (VALIDATION header, 3.9b, 3.11, 3.14, 4.1, 4.1c; METHOD_NOTES 14). The owner's own words in
  `rules.yaml` were left as written.

#### M9. GPM leads the station by a day; never reported
- **Evidence.** `data/checks/demo/crosscheck_gpm_ghcn_NP000444540.json`: Pearson 0.509 at lag -1, 0.405 at 0, 0.221
  at +1 (POWER against the station is lag 0, 0.634). Of the station's 25 wettest days GPM is larger the day before
  in 16. CLAUDE.md decision C asks for the GPM lag. `pipeline/fetch/ghcn.py:15-18` says station and GPM days are both
  "05:45 to 05:45 Nepal time". The 170 spike votes compare the same calendar day (with GPM moved a day, 144 flags).
  `data/cards/demo/gpm.json` has no `cross_source_flags` (`pipeline/fetch/weather.py:333` annotates only POWER and
  the station). Nothing exported depends on it (the rain test uses monthly totals).
- **Fix.** Report the lag (VALIDATION 3.13, DATA_AUDIT 1.11); correct the day-boundary sentence; write the flags into
  the GPM card. Voting at lag -1 as well would be the owner's call.
- **Effort.** 30 min.
- **Status.** FIXED 2026-11-13: lag reported (VALIDATION 3.13, DATA_AUDIT section 3), flags written into the GPM card (161).
  Voting at lag -1 as well: OWNER.

#### M10. Leap-year slip in the count of pinned onset years (M)
- **Evidence.** `scripts/run_diary.py:395-396` compares day-of-year with 135, so 17 May in a leap year (day 138) is
  missed: `data/checks/demo/diary.json` stores `onset_pinned_years` 19 and "19 of 25"; by date it is 21 (and 22 in
  the uncorrected run, stored 21). `shift_days` is null either way; no export changes.
- **Fix.** Tests first with a leap year; count from each year's own 15 May; rerun the diary step.
- **Effort.** 30 min.
- **Status.** FIXED 2026-11-13 (`trends.pinned_years`, test with a leap year; diary rerun: 21 of 25, and 22 on GPM as published).

#### M11. Rotation guess and bare days: exported without their doubt
- **Evidence.** Winter guess: potato 72.0 against wheat 73.5 (a structural near-tie in `pipeline/diary/guess.py:50-55`,
  since length = end - start + 1); it flips to wheat with the densely observed years 2018-2025 (71.5 against 76.5)
  and wheat wins 4 of the last 5 years; the potato fit uses potato's second FAO window, not the one the twin
  simulates. `diary.guess` is `["rice", "potato"]`, the owner's placeholder, and screen 3 says "We think you grow
  ...". `diary.bare_days` 62 is the 2014-2025 mean of days with NDVI below 0.25 (62.5, written 62); the screens say
  "No crop on 62 days each year" although the season labels give 103 days outside a crop season; sparse years read
  higher (2014-2017 mean 77.8; 2018-2025 54.9).
- **Fix.** Owner: show "rice, then potato or wheat" (wording, or a contract field); reword to "bare ground on about
  62 days".
- **Effort.** 30 min wording plus review.
- **Status.** OWNER (question 12). Recorded in VALIDATION 3.18, METHOD_NOTES 29, CONTRACT_CHANGES.

#### M12. Groundwater: `confidence: 1.0` and "falling" describe a mascon from the Bihar plain to Everest
- **Evidence.** The field's cell belongs to JPL mascon 1213 (25.5-28.5 N, 85.0-88.5 E; 42 identical half-degree
  cells); Kathmandu is on its western edge. The trend is statistically safe (seasonal Sen -2.57 cm/yr; -2.53 +/- 0.15
  allowing for autocorrelation). The schema calls `confidence` "0 to 1, like sure". The falling direction makes
  irrigation count 1.5x in the water score (`pipeline/plans/score.py:31`), lowering the shown score by 14-21 points
  (current plan: rain covers 58.8% of need, shown as 38). The farmer texts are careful ("Stored water in this area",
  "not your own well").
- **Fix.** Name the mascon's extent in METHOD_NOTES and DATA_AUDIT; a UI note in CONTRACT_CHANGES that `confidence` is
  about the regional trend, not the field (Phase 2). The 1.5x is owner-approved.
- **Effort.** 20 min.
- **Status.** FIXED 2026-11-13 (VALIDATION 3.16, METHOD_NOTES 26, DATA_AUDIT 1.10, CONTRACT_CHANGES). How the site shows it: OWNER (question 18).

#### M13. The validator accepts exports the contract forbids; `mock.py` can overwrite the real file
- **Evidence** (sub-reviewer's mutation test). 22 of 30 wrong files validate: replay years without `irrigated`, a
  plan with no replay, a gap in years, the incomplete year 2001, three plans with identical crops, `score.harvest`
  5 against a replay mean of 72, an unknown crop id, the old id `follow_shift`. `python -m pipeline.export.mock`
  (`mock.py:156`) silently replaces the real `demo.json` and `index.json`. `live.json` and `probe_log.json` have no
  schema and are not validated; `site/data/live.json` is not git-ignored.
- **Fix.** Tests first, no schema change: every plan has a replay; years strictly increase with no gap; the crop
  sets differ; `score.harvest` equals the rounded replay mean; `--final` fails while MOCK remains; `mock.py` refuses
  to overwrite a non-mock file without `--force`.
- **Effort.** 1.5 h.
- **Status.** FIXED 2026-11-13, tests first: the two everyday checks, `--final`, the `mock.py` guard. OWNER: `irrigated`
  required in the schema (question 17); `live.json` schema and `.gitignore` line (question 19).

#### M14. Words and Nepali
- **Evidence.** `pipeline/words/{screens,glossary,crop_explainers}.json` are outside the published folder and nothing
  exports them; `plans[].name` is English only. Nepali evidence tabs carry English ("०.१ deg (about १० km)", "about
  ३०० km", "one map"); 12 English and 9 Nepali source lines exceed eight words. `follow_shift` remains in
  `tabs.json`, `fill_registry.json:47`, `screens.json:797`, `explain.py:16`.
- **Fix.** Owner: export `site/data/words.json` (a new site file) or agree a copy with a test. A Nepali lookup for
  the resolution strings (text needing review).
- **Effort.** 1-2 h.
- **Status.** `site/data/words.json` FIXED 2026-11-13 (owner's answer 16; `pipeline/export/build_words.py`, a test fails when it is
  out of date). The Nepali lookup for the resolution strings: OPEN.

#### M15. "If you can water" is 100% and 0 dry days in all 72 plan-years, by construction
- **Evidence.** `pipeline/twin/soil_water.py:75-80` refills whenever stress would start. Flood years carry no loss.
  The irrigation totals (278 mm a year; rice 102, potato 176) are in `data/checks/demo/replay.json` but not in the
  export, and the paddy figure has no percolation or puddling water.
- **Fix.** Owner: one line that the watered case assumes water never runs out and counts thirst only. METHOD_NOTES
  note (Phase 2).
- **Effort.** 15 min docs; text 30 min plus review.
- **Status.** Docs FIXED 2026-11-13 (METHOD_NOTES 38, CONTRACT_CHANGES). Farmer text OWNER.

#### M16. SMAP is half downloaded and unused; the docs are wrong both ways (M)
- **Evidence.** On disk: L3 AM and PM (2015-03-31 to 2025-12-31) and L4 for 2015-2017. The eight L4 tasks for
  2018-2025 are finished at AppEEARS (checked today, expire 12-13 December) and not downloaded. No cleaning code,
  table or card. DATA_AUDIT says "REQUESTED"; `README.md:34` says SMAP is "a check on the twin's soil water". Raw L3
  values reach 0.572, above the product's valid maximum of 0.5.
- **Fix.** Phase 3: download, clean with guards, card, and compare anomalies with the twin by year.
- **Effort.** 1.5-2 h.
- **Status.** FIXED 2026-11-13: `pipeline/fetch/smap.py` (card `smap.json`), `scripts/run_smap_check.py`, VALIDATION 4.2b. L3 has
  no recommended-quality retrieval at the field's cell (0 of 3,263) and is not used; L4 monthly anomalies correlate 0.60
  with the twin's wetness and cannot tell the two rain versions apart.

#### M17. The prepared area is the 10 km fetch box; no field outline is exported
- **Evidence.** `index.json` bbox equals `fetch_box`; `demo.json` has lat and lon but no polygon (only the partial
  mock sections). A field drawn 2.6 km away would get this 60 m square's results as its own.
- **Fix.** Owner: UI wording ("we show our sample field near you") and export the polygon (contract) or wait for real
  sections.
- **Status.** OWNER.

### Low

- **L1. Data cards.** `gpm.json`, `ghcn_NP000444540.json`, `soilgrids.json` and the two ECOSTRESS cards carry stale
  TODO-VERIFY text; `power.json` is located at the first, rejected placeholder (same POWER cell: 0 of 9,131 days
  differ) and `weather.py` has no POWER cell check like `check_gpm_cell`; no card for the DHM table. **Partly FIXED 2026-11-13: GPM card flags written; the stale card texts are listed in DATA_AUDIT section 5 (rebuilding them needs the network).**
- **L2. Elevation by hand.** `weather.py:290` reads `elevation_m` typed into `demo.yaml`; nothing ties it to
  `nasadem_field.json`; slope is read by no code (1.6 degrees is at the noise floor of 1 m heights). OPEN (note).
- **L3. Water balance closes per segment, not over the record.** `pipeline/twin/season.py:59-60, 99-100` hands
  depletion over as a fraction of TAW: over 51 hand-overs a net 870 mm of depletion appears with no water moving
  (35 mm a year); carrying millimetres instead moves potato 44.6 to 42.6 and the yearly mean 72.3 to 71.3. Say so
  in METHOD_NOTES and VALIDATION 2.2 ("within each segment"). OPEN (docs); a rule change would be the owner's. **Docs FIXED 2026-11-13 (VALIDATION 2.2, METHOD_NOTES 39).**
- **L4. FAO-33's valid range** is still TODO-VERIFY (`pipeline/twin/yield_.py:9-12`); 12 of 24 potato seasons have
  ETa/ETc below 0.5. OPEN.
- **L5. Harvest gain wording.** "About 18 more" is 90 - 72 from the rounded cards (the unrounded gap is 17.3), and
  suggested plans take their best sowing date while the current plan is fixed at the middle (like for like about
  13). Consistent with the numbers shown; disclose in METHOD_NOTES. **Docs FIXED 2026-11-13 (METHOD_NOTES 37).**
- **L6. Score definitions in CLAUDE.md** differ from the code: `soil_kept` is against bare fallow all year
  (`score.py:76-77`), not "versus the current plan"; water is 1 - 1.5 x irrigation / ETc from the watered run;
  harvest is rain-fed. `soil_kept` does not separate the three plans (74, 74, 74). **Docs FIXED 2026-11-13 ("as built" notes in CLAUDE.md).**
- **L7. Probe bridge.** A pulled USB cable ends `robot/bridge.py:114-117` with a traceback and leaves a stale
  `live.json`; `time` has no UTC offset; section `s99` is accepted. Whether the DS18B20 is in the soil ("soil
  temperature") and how probe moisture (0% air, 100% water) maps to the twin's wetness are not stated. OPEN for step
  10. **FIXED 2026-11-14 (owner's probe brief): a pulled cable gives one plain message and marks `live.json` stale (also after 10 s of silence); parts the field does not have are refused (from `sections.json`); the sketch shows one DS18B20 on GPIO4 and cannot say whether it sits in soil or air (VALIDATION 5.x). The mapping to soil water waits for the team's bench test (`robot/CUPS_PROTOCOL.md`).**
- **L8. Requirements.** `scipy` and `affine` are imported but only installed as dependencies of other packages;
  `xarray` and `flask` are pinned but never imported. Changing pins is the owner's. **Noted in CREDITS 2026-11-13.**
- **L9. Leftovers.** `scripts/run_season.py:116` hard-codes "750 m"; `diary_onset.json` `labels.rule` says
  "TODO-CONFIRM"; `rules.yaml:234` says "about 10 June"; `SI_LOG.md:162,163,165` contain an absolute home path
  (already public). **`run_season.py` and the `rules.yaml` comment FIXED 2026-11-13; the SI_LOG home paths FIXED 2026-11-14 (now `~/`); `diary_onset.json` TODO-CONFIRM OPEN.**
- **L10. Onset robustness runs cannot show robustness.** With a 20-day look-ahead that starts on a wet day, a 15- or
  20-day dry spell is nearly impossible (`pipeline/diary/onset.py:50-54`); they differ from the main rule in 2007
  only. The dry-spell trend depends on where the year is cut (+0.69/yr p 0.052 by calendar year; +0.50, p 0.49
  across New Year). Pettitt p-values are the approximation (a permutation test gives POWER 0.028, so "POWER: no
  significant change" is not robust). **Docs FIXED 2026-11-13 (VALIDATION 3.9b, 3.17, 4.1d).**
- **L11. ECOSTRESS is unused (and rightly not in `sources`), but five traps wait for step 8:** 742 of 769 LST
  granules are V002; V002 never flags cloud on a valid pixel while V003 does on 10.6%; "valid" LST runs 14.6 K to
  1,306 K; 119 overpass times have two or three product iterations; one 70 m pixel centre lies in the field, so
  10 m sections cannot differ by ECOSTRESS. OPEN (recorded in DATA_AUDIT 1.8). **FIXED 2026-11-14: the five traps handled in `pipeline/fetch/ecostress.py` (DATA_AUDIT 1.8); only 72 clear ESI overpasses survive, 4 seasons per slot against the 6 the pre-declared rule needs, so ECOSTRESS stays a check (VALIDATION 4.2e) and earns no diary line.**
- **L12. Workflow.** `pages.yml` publishes without validating `site/data` or checking `site/index.html`. Owner's call.
- **L13. Latent.** `pipeline/plans/events.py:31` groups seasons by crop only (a crop grown twice a year would be
  ranked across both slots; no exported plan does). `weather.build` lets a NaN pass (the stop comes later, in
  `season.py:43-56`); today there are none. OPEN.

---

## Verified correct (re-checked in this review)

Runs
- A fresh Python 3.12 environment from `requirements.txt` installs and `pip freeze` equals `requirements-lock.txt`
  exactly. **871 passed** with deprecation warnings as errors (M).
- `python -m pipeline.export.validate`: 2 files, 0 problems, one MOCK warning (M). A rebuild of `demo.json` from
  `data/checks` is byte-identical. The Pages workflow is correct; it fails only because Pages is off (M).

Equations (own code against the project's, on the real 2001-2025 weather)
- ET0: FAO-56 Example 18 gives 3.880 mm/day; all 9,131 days match to 4e-15 mm; yearly mean 1,324.8 mm (documented
  1,325); with humidity held 1,281.1; the vapour-pressure cap binds on 5,056 days (55.4%). Radiation is in
  MJ/m2/day and never exceeds Ra; POWER wind is at 2 m.
- Kc curve and climate adjustment: Example 27 gives 1.069 and 1.296 (printed 1.07, 1.30); Kc mid and end for 49
  seasons match to 2e-16.
- Bucket, runoff, yield: Example 37 within 0.05 mm over ten days; TR-55 Table 2-1 exact; TAW 149.3 / 96.9 / 213.8
  mm; daily depletion matches to 3e-14 mm; season balance residual 4e-13 mm.
- Every replay number in `demo.json` (24 years x 3 plans x 2 water cases x 2 rain versions): 0 mismatches.
- `config/crops.json`: every Kc, stage length, root depth, p, height and Ky of the six simulated crops matches
  FAO-56 Tables 11, 12, 22 and 24 as on fao.org today; no `ky_assumed` label is missing.

Weather inputs
- POWER raw JSON equals `power.parquet` on 9,131 days and 6 columns; units as named; fill -999 found 0 times.
- GHCN raw equals clean (PRCP 5,036, TMAX 4,706, TMIN 2,404); S-flag `S` on all 12,147 values; station 7.43 km away.
- Temperature offsets: held-out MAE Tmin 2.310 to 1.223 C (n 714), Tmax 2.249 to 1.161 C (n 1,303); all 24 applied
  offsets equal the card; `tmin_c` and `tmax_c` reproduced exactly.
- Quantile mapping: MAE 1.338; January coldest-night error 2.31 (offset 2.83); nights below 2 C 9 / 22 / 15; no
  leakage; `tmin_frost_c` reproduced on all days; 28 against 55 nights below 0 C.
- New: DHM's 1991-2020 temperature normals (already in `config/`) agree with the corrected temperatures (airport:
  Tmax within 0.27 C, Tmin 0.28 C on average by month, against 1.85 and 2.58 C for raw POWER).

Rain
- Raw GPM files: `precipitation` in mm/day, fill -9999.9, the cell centred 27.65 N, 85.45 E holds the field; 9,039
  Final and 92 Late days; yearly totals from raw equal `gpm.parquet`.
- The break: GPM 1,841.7 then 2,731.2 mm (x1.483); CHIRPS 1,453.5 then 1,436.8 (x0.989); a hand-written Pettitt test
  reproduces all five p-values; the Late table reproduces.
- The cause, re-fetched: IMERG monthly gauge weight 96-98% in 42 sampled months of 2001-2016 and 55-68% in every
  month of 2017; GPCC Full Data V2022 has 45-53 stations a month in the field's box in 2001-2016 and 0.7-1.0 in
  2017-2020.
- The correction: all 12 factors reproduce; exactly the 3,195 Final days from 2017-01-01 are scaled; the Late days
  are untouched; `rain_uncorrected_mm` equals `gpm.parquet`; held-out 93.7 to 31.4 mm and 1.625 to 1.064 reproduce;
  after scaling, days of 20 mm or more number 187 against the station's 187 (297 as published).
- Labels: the source line, `method.rain_correction`, the four rain sentences in every "unknown" tab (both
  languages), `uncorrected_rain` on 12 years per plan and `score_uncorrected_rain` on all three plans are present.

Diary
- HLS (scale 0.0001, fill -19999, Fmask bits) and MODIS (scale 0.0001, fill -3000, reliability 0) read correctly;
  per-image field NDVI for all 1,471 HLS images and all 576 MODIS composites reproduce; the 4 field pixels cover
  77.6% of the field.
- Bare days for all 25 years; 671 MODIS-HLS pairs, r 0.83, -0.085; all 24 HLS-year seasons to the day; no label
  leakage in the season detective; "threshold method kept" holds in every variant tried.
- All 25 onset dates x 3 variants x 2 rain versions; `shift_days` null; all trend slopes and p-values; all 60 month
  words; GRACE units, cell, 261 solutions, seasonal Sen -2.573 cm/yr.
- All 72 exported events and every `uncorrected_rain` event; valley floods 2 of 2 on the right days; valley winter
  droughts 2 of 4; nine cited event sources opened, all as cited.

Plans
- 165 plans, 81 with rice, Pareto set 12, the same three picks in eight variants (years, Ky, rain); ten plans'
  scores to rounding; the erosivity formula and C factors as printed in Yin et al. 2015 and Benavidez et al. 2018.
- Text numbers in the tabs match the export; five tabs per plan in both languages; tips paired in order; "This is a
  sample field", the local-advisor and small-trial lines and "You know your land best" are present; never tonnes.

Static data
- SoilGrids units and the whole profile at the cell used (difference 6e-17); 859.3 m; NASADEM 1,325.0 m and slope
  1.63 degrees with dx scaled by cos(latitude); WorldCover: 107.3 m from the square and 77.1 m from its margin to
  the nearest built-up pixel.

Security and probe
- `scan_history.py` exits 0 over 16 commits; an independent scan found no secret; `.env` and `data/` are ignored;
  none of the `.env` values is in the tree or history; the Firebase database refuses an unsigned read (401).
- The parser accepts exactly what the unchanged sketch prints (4,106 of 4,106 emulated lines) and refuses the rest;
  the fake probe is byte-identical; the bridge writes the five contract keys atomically.

## Uncertain or not checked

- Whether UI code exists elsewhere and which contract version it reads.
- The cause of POWER's 2001-2003 anomaly (likely MERRA-2's land surface driven by its own low rain; not verified).
- Why IMERG still reports 55-72% gauge weight after 2017 while Final equals Late.
- Whether the airport station represents the field; whether the DHM gauges represent the GPM cell on single days.
- CHIRPS v3.0's licence statement (public domain or CC BY 4.0 by its pages; the v3 README states none); DHM's and
  GPCC's terms; whether GSOD's WMO Resolution 40 clause travels with GHCN-Daily values. Legal readings, not settled
  here.
- FAO-33's validity limit for the linear yield relation; the month index in the erosivity model; finger millet's C.
- The Space Apps 2026 challenge page and AI-use rule could not be read by a script; the team should read the 2026
  wording themselves.
- Nepali quality: readable, not a native review.
- Nothing was run on the probe hardware.

## Questions for the owner (each with a recommendation)

1. **Site and push (C1).** Enable Pages and push the working tree now, so the UI teammate builds against the real
   contract? Recommended: yes, today.
2. **Mock blocks (H1).** A `mock` list in the export plus neutral "not ready" sections and no 2040 numbers until
   steps 8 and 9 finish? Recommended: yes (contract change).
3. **Third plan's name (H2).** Rename "Safest in bad years" for what the plan gives? Recommended: yes, for example
   "Feed the soil" (rice then lentil); keep the id.
4. **Rooting depth (H2).** Keep the larger FAO values and show the harvest gain as a range, or use the smaller depth
   after paddy? Recommended: keep, show the range, say so in the "unknown" tab.
5. **Tips (H3).** A floor before a "thirsty" tip is shown, and the straw tip from the satellite's bare months?
   Recommended: yes to both; drop the rice tips for now.
6. **Winter calendar (H3).** Keep the placeholder potato at 30 Oct to 21 Feb although the satellite shows the winter
   crop from January to mid-May? Recommended: decide with the real farmer; until then add one caveat line.
7. **The 92 Late days (H4).** Scale them with the same monthly factors? Recommended: yes.
8. **Rain level (H4).** One "unknown" line that the rain may still read high? Recommended: yes.
9. **Events (M4).** One weather event per year for the field on every tab, and "drier than usual" instead of "very
   dry years: 7 of 24"? Recommended: yes to both.
10. **Soil cell (M5).** Keep the nearest cell and show the neighbourhood range, or use the median of cells within 2
    km? Recommended: keep, with the caveat and the range.
11. **POWER 2001-2003 (H8).** Keep those years in the replay with the caveat if the Phase 3 sensitivity shows the
    plans and events hold? Recommended: yes; report trends for 2004-2025 beside 2001-2025.
12. **Guess and bare days (M11).** "Rice, then potato or wheat", and "bare ground on about 62 days"? Recommended: yes.
13. **Licences (H5).** DHM table kept with a notice; GSOD notice; a "not covered by MIT" paragraph in LICENSE?
    Recommended: yes to all three.
14. **Secret scanner (H7).** Extend `scan_history.py` and `.gitignore` before step 10b? Recommended: yes.
15. **Text review (H5).** Who signs the English and who reviews the Nepali, by when?
16. **Words file (M14).** Export `site/data/words.json`? Recommended: yes, so the site cannot drift from the tested
    texts.
17. **Validator (M13).** May `irrigated` become required on every replay year in `schema.json` (the contract text
    already says "both always written")? Recommended: yes.
18. **Groundwater (M12).** Should the site show `confidence` 1.0 as certainty about the field? Recommended: no; show
    it as "the regional trend is clear".
19. **Probe (L7).** Is the DS18B20 in the soil? Should `live.json` carry a UTC offset and be git-ignored?
20. **Two readings never put to you (M7).** `gpm_series.correction_fields` (a field abroad is corrected only after its own
    rain check finds the break) and `trends.shift_days_span` (the change is the slope times last year minus first year).
    Recommended: approve both; the first matters for step 11, because the gauge loss is Nepal-wide and other countries
    have their own.
21. **Rules before runs (M8).** From now on, commit a new rule locally before its first run, so "fixed in advance" can be
    shown? Recommended: yes (local commits only; pushing stays your call).

---

## The owner's answers (2026-11-13, about 15:10) and what was done with each

All 21 questions were answered. "Done" means tests first, rerun, re-exported, documents updated, committed and pushed.

| # | Answer | Status |
| --- | --- | --- |
| 1 | Commit and push now; the owner enables Pages by hand | **Done**: `6476cc2`, then one push per finished step. Superseded for hosting the same evening: **Vercel**, not GitHub Pages (the workflow is removed). Superseded again 2026-11-14 night: **GitHub Pages** from this repository, the workflow restored |
| 2 | A `mock` list, neutral "not ready yet" sections, no 2040 numbers until steps 8 and 9 are real | **Done** (`f645659`): 36 real 10 m sections with no numbers, `future: null`, both named in `mock`; no MOCK word left in the file |
| 3 | Rename the third plan "Feed your soil" (keep the id); reword its why-text and the registry line | **Done** |
| 4 | Keep FAO's larger root depths; show the gain as a range; explain it in the "unknown" tab | **Done**: wheat plan "about 8 to 22 more", lentil plan "about 4 to 14 more"; two "unknown" lines. Which runs make the range is the reviewer's reading (rules.yaml `plans.gain_range`): put to the owner |
| 5 | A floor before any "thirsty" tip, no rice tips for now; the straw tip from the satellite's bare months | **Done**: floor 5 dry days a year in the crop's worst month (the number is the reviewer's: put to the owner); the current plan's straw tip now says November |
| 6 | Export the current plan for both winter crops (rice then potato, rice then wheat on the best-fitting FAO window), both water cases and both rain versions; suggested plans compared with whichever is picked; a caveat line on winter timing | **Done**: `current_options` in the export (contract change listed), `pipeline/plans/options.py`. Wheat is sown 15 November, the closest date FAO's window offers, still 78 days from the satellite's season; harvest 81.8 (potato option 72.3). **For the owner:** when the farmer picks wheat, "Fill the empty months" is rice then wheat as well (sown 15 October): two of the three plans then grow the same crops and differ in dates only; its gain over the wheat current plan is 6 to 9, and the lentil plan's is "up to 8, maybe none" |
| 7 | Scale the 92 Late days with the same monthly factors | **Done**: 3,287 days scaled; no harvest or dry-day number changed; `soil_kept` of the suggested plans 74 to 75; the Late months are now 1.64 x DHM's gauges (1.97 x before) |
| 8 | One "unknown" line that the rain may still read high, keyed on the DHM-normal ratio | **Done**: shown at 1.25 x the nearest station's normal or more (the limit is the reviewer's: put to the owner); demo 1.35 x |
| 9 | One weather event per year for the field on every tab; "drier than usual"; name the season of a one-season event | **Done**: `pipeline/plans/events.py` `field_year_events`; `event_season`; rule committed before its first run (`a8b9b45`). The seasons used are DHM's monsoon (June-September) and winter (December-February): the reviewer's reading, put to the owner. Known events with the new rule: valley floods 2 of 2, valley winter droughts 2 of 4, both negative controls still fail (VALIDATION 4.1) |
| 10 | Keep the nearest soil cell; show the neighbourhood range; add the caveat line | **Done**: the "unknown" line "The soil numbers come from 859 m away."; the SoilGrids `sources` row and the soil data card give the neighbourhood: 149 mm of water held in the top metre at the cell used, 149 to 187 mm over the 56 cells within 2 km |
| 11 | Keep 2001-2003 with the caveat; report trends for 2004-2025 beside 2001-2025 | **Done**: every trend carries `without_faulty_years`; none is significant without them (VALIDATION 3.17) |
| 12 | "Rice, then potato or wheat"; "bare ground on about 62 days" | **Done**: screen 3 asks "We think you grow rice first. Then potato or wheat. Which one do you grow?"; "The ground is bare about 62 days yearly." |
| 13 | DHM table with a notice; GSOD notice; "not covered by MIT" in LICENSE | **Done** (`6476cc2`) |
| 14 | Extend `scan_history.py` and `.gitignore` now, the website key allowed by SHA-256 only | **Done** (`6476cc2`), tests first |
| 15 | The owner reviews the English and the Nepali by Sunday 10:00; the marks stay until then | Marks kept. New texts to review are listed in SI_LOG |
| 16 | Export `site/data/words.json` | **Done** (`f645659`) |
| 17 | `irrigated` required on every replay year | **Done** (`f645659`) |
| 18 | Show the groundwater confidence as "the regional trend is clear", never as certainty about the field | **Done** in the words (screen 3 `water_wide`, `water_not_yours`) and in the note for the UI |
| 19 | The owner confirms where the temperature sensor sits; `live.json` with a UTC offset and git-ignored | Git-ignore and UTC offset **done** (`robot/bridge.py`). Where the sensor sits: the owner's to confirm |
| 20 | Approve both readings | **Done** in `rules.yaml` |
| 21 | Commit each new rule locally before its first run | **In force** since `a8b9b45` (also `dfb1d4f`) |
| Priority | The season detective as an uncertainty signal ("less sure" where it and the threshold method disagree) | **Done**: `diary.months[].cover_sure` (June 0.80; other months 0.91-1.00); an addition, the threshold method still decides |
| Priority | A minimal, honestly tested field memory (7b) | **Done, and it lost**: held-out error 0.035 against 0.032 for physics alone and 0.030 for "no anomaly" (24 seasons, 12 years), so it is not used; the result is on the method page (`method.field_memory`) and in VALIDATION 4.6 |
| Priority | A note for the UI teammate; a fallback site if his UI is not in the repository by Saturday 12:00 | Note **done** (`notes/ui_note.md`, kept current with each contract change). Fallback site: to build on Saturday if needed |

---

## Phase 2: what was fixed (2026-11-13, tests first; 871 tests before, 898 after)

No scientific method, rule, threshold or exported result was changed. `demo.json` changed in two `sources` rows and in
`method.choices` only.

| Fix | Where | Review item |
| --- | --- | --- |
| Approvals read however they are capitalised; the rule added after the first run is listed | `pipeline/export/build_field_json.py` `stated_choices` | M7 |
| The `sources` rows for MODIS and SoilGrids say what each is used for; the soil cell's 859 m comes from its card | `build_field_json.py` `sources_block` | M5, M6 |
| Pinned onset years counted from each year's own 15 May (19 became 21; 21 became 22) | `pipeline/diary/trends.py` `pinned_years`, `scripts/run_diary.py` | M10 |
| The hot-day trend carries a caveat and is also given without POWER's 2001-2003 | `trends.without_years`, `rules.yaml trends.hot_day_caveat` (a label) | H8 |
| A plan without a replay and replay years out of order are refused; `validate --final` is the freeze check | `pipeline/export/validate.py` | M13 |
| `python -m pipeline.export.mock` no longer overwrites a file holding real results | `pipeline/export/mock.py` | M13 |
| Cross-source flags written into the GPM card too | `pipeline/fetch/weather.py` | M9 |
| Stale label "750 m" | `scripts/run_season.py` | L9 |
| The gauge-weight range on the method page corrected from 96-97% to 96-98%, now read from a data card (the full monthly series was fetched) | `config/rules.yaml gpm_series.break_evidence`, `pipeline/fetch/gauge_evidence.py`; cards may carry a `summary` (`pipeline/fetch/guards.py`) | M6 |
| VALIDATION, DATA_AUDIT, METHOD_NOTES, README, CLAUDE.md (factual lines), CONTRACT_CHANGES, CREDITS, SI_LOG | the documents | M1-M3, M8, M12, H2a, H4a, H5a, L3, L5, L6, L10 |

## Phase 3: accuracy tests and more data (2026-11-13)

**Downloaded, and why** (no new account, no new dependency; all under the git-ignored `data/`):

| What | Size | Why |
| --- | --- | --- |
| SMAP L4 for 2018-2025 (the eight AppEEARS tasks requested on 12 November, finished there) | 16 MB | The check of the twin's soil water that the brief names (M16) |
| IMERG monthly `gaugeRelativeWeighting`, 3 x 3 cells, 2001-2025 (GES DISC OPeNDAP) and GPCC Full Data V2022 station counts (DWD open data) | 45 MB compressed | The evidence for the 2017 break had been read by hand; it is now fetched, carded and summarised by `pipeline/fetch/gauge_evidence.py` (M6) |
| Six DHM monthly bulletins of 2025 (validation only; (c) DHM, not redistributed) | 12 MB | The only gauges near the field that are neither the synoptic station nor inside IMERG (H4) |

**Results.**

1. **Rain, triangulated.** CHIRPS and IMERG Late (already downloaded) reproduce. The gauge evidence, fetched in full (297 months): the gauge weight at the field's cell is 96-98% in
   every month of 2001-2016 and 56-72% by year from January 2017 (the method page said 96-97%: corrected), and GPCC's
   stations in the field's box fall from about 50 a month to about 1. DHM's own gauges in
   2025: in the three IMERG Final months GPM as published is 1.27 x the gauges and the twin's corrected rain 0.88 x; in
   the three Late months the twin is 1.97 x. So the correction is supported where it applies, and the 92 Late days
   are too wet (VALIDATION 3.9b, 3.9c).
2. **SMAP against the twin.** L3 has no recommended-quality retrieval at the field's cell (0 of 3,263) and is not used.
   L4 root-zone monthly anomalies against the twin's wetness, April 2015 to December 2025: Pearson 0.60 (0.74 from
   October to May); the corrected and the published rain agree with SMAP about equally, so SMAP cannot judge the fix
   (VALIDATION 4.2b).
3. **Held-out tests of every correction, recomputed.** Temperature offsets: Tmin MAE 2.31 to 1.22 C, Tmax 2.25 to 1.16 C.
   Quantile mapping: MAE 1.34 C, January coldest-night error 2.31 (offset 2.83), nights below 2 C 15 against the
   station's 9. Rain: 93.7 to 31.4 mm a month, ratio 1.62 to 1.06. All as documented; the rain test's limits are now
   written down (M8). New and independent of the fit: DHM's temperature normals (Bhaktapur: Tmax within 0.50 C, Tmin
   0.98 C; raw POWER 2.34 and 3.08 C).
4. **Sensitivity, and whether the plan ranking holds.** The whole plan step was rerun under 13 perturbations
   (harvest of current / rice then wheat / rice then lentil; base 72.3 / 89.6 / 80.8):

   | Case | Harvest | Picks |
   | --- | --- | --- |
   | Soil water -20% / +20% | 68.6 / 83.6 / 76.8 and 75.8 / 94.0 / 84.6 | same |
   | ET0 -10% / +10% | 75.5 / 93.2 / 84.0 and 69.5 / 86.0 / 78.1 | same rotations (one sowing date moves at -10%) |
   | ET0 of 2001-2003 lowered to the later level | 72.6 / 89.9 / 81.1 | same |
   | Root depths at FAO's smaller values | 66.1 / 79.7 / 76.2 | same rotations (rice sowing date moves) |
   | Wheat's roots at 1.0 m | 72.3 / 80.5 / 80.8 | same; the two suggested plans are level |
   | Ky 0.8 and 1.2; years 2002-2016 only | (step 7) | same |
   | GPM as published | 73.2 / 90.0 / 81.6 | same |
   | One yearly rain factor instead of twelve | 71.6 / 89.2 / 80.4 | same rotations (one sowing date moves) |
   | The 92 Late days scaled too | 72.3 / 89.6 / 80.8 | same; only `soil_kept` of the suggested plans 74 to 75 |
   | Groundwater not falling | water scores 59 / 67 / 63 instead of 38 / 51 / 45 | same |

   The two suggested **rotations** (rice then wheat, rice then lentil) hold in every case. The **size** of the gain does
   not: it runs from +8 to +18 points for the wheat plan, mostly with rooting depth and soil water.
5. **Known events, recomputed.** All 72 exported events reproduce. Valley floods 2 of 2 on the right days; valley winter
   droughts 2 of 4. Both negative controls fail in the exported run (H4).
6. **Switch-off on the real export.** Used: GPM, POWER, the station, SoilGrids, the crop library, GRACE, HLS, NASADEM
   elevation (barely), DHM normals (one number). Not used: MODIS. Checks only: SMAP, ECOSTRESS, WorldCover, FAOSTAT,
   CHIRPS, IMERG Late, GPCC. Still mock: sections, future (DATA_AUDIT section 4).

**Not done:** HLS EVI and NDMI for the paddy-flooding test. It needs about 3,000 more windowed reads and a new rule in the
rotation guess (a method change: the owner's go), and rice is already the robust half of the guess. The DHM bulletin
comparison covers six months of one year; a longer series needs DHM.

## Phase 4: feasibility and plan

It is Friday afternoon. The event runs Saturday 09:00 to Sunday 23:59; submission is Sunday evening; nothing may change
afterwards. That leaves about 28 working hours for the pipeline, in parallel with the UI and the probe.

**Done:** build steps 1 to 7 (with the findings above), the probe's serial parser and bridge (part of step 10), this
review's fixes.

**Left, with honest times** (a Claude session plus the owner's review):

| Work | Time | Needed for |
| --- | --- | --- |
| The owner's answers to the questions above | 45 min | everything below |
| Enable Pages; commit and push so the UI teammate has the real contract | 20 min | the judge path |
| Apply the answers: Late days, third plan's name, tips floor, straw tip, "bare ground" wording, rain-level and rice lines; re-export | 2-3 h | honest plans |
| A native speaker reads the three plans' Nepali (about 60 sentences) | 1-2 h of a person | rule: a person reviews every text |
| `mock` list in the export and neutral "not ready" sections (H1) | 1 h | safe freeze if steps 8 or 9 slip |
| Step 11a: exporter built from the field config and the data cards; `build_index`; optional rain check (H6) | 3-5 h | fields abroad |
| Step 11b: two fields abroad: downloads (GPM daily subsets and HLS windows take hours per field, unattended; MODIS waits in NASA's queue), rain check, diary, plans, export | 3-4 h unattended and 1-2 h attended per field | "the method is global" |
| Step 9: NEX-GDDP deltas (about 13 s per model, variable and year: 5 models in about 40 minutes with four connections), twin runs, slider grid | 4-5 h | the 2040 screen |
| Step 8, small version: sections that tile the real square, status from the twin, low-ground flag from NASADEM; no ECOSTRESS | 2-3 h | screens 4 and 5 |
| Step 10: Kalman update, `twin_state.json`, `probe_log.json`; bench test with the probe | 2-3 h plus 1-2 h with the hardware | local judges; the replay for global judges |
| Step 7b: field memory | 2-3 h | "required" in the brief, but see the cut list |
| Step 10b: Firebase live probe (firmware, rules, keys, scanner) | 4-6 h, high risk | an extra for local judges |
| UI integration in `site/` | unknown (teammate) | the judge path |
| README, freeze check, final commit, live check on a fresh phone | 1.5 h | submission |

**Top risks.**
1. **No site, and the contract on GitHub is stale.** Everything else is invisible without it.
2. **Mock numbers frozen in the export** if steps 8 and 9 slip and H1 is not done.
3. **Fields abroad:** the exporter is demo-shaped, downloads take hours, and each field may have its own rain break.
4. **Text:** every owner decision changes farmer text that then needs a person's review, in two languages.
5. **Firebase** eating Saturday.
6. **One laptop:** `data/` (about 900 MB of downloads) is in no backup. Copy it to a drive once tonight.

**Cut list, first to go first:** the Firebase live probe (10b); ECOSTRESS zones; the photo check and haze calendar;
field memory (7b: say "not built" in VALIDATION 4.6 rather than rush it; its test needs the real rotation anyway, H3);
a third field abroad; the Kalman fusion on the site (keep a recorded probe log); HLS EVI and NDMI.

**Ordered plan, must-haves first.**

- **Friday evening.** (1) Owner: answer questions 1-9; enable Pages; say whether to commit and push. (2) Apply the
  answers and H1, re-export, push the contract to the UI teammate. (3) Start step 11a. (4) Choose two fields abroad
  and start their downloads overnight. (5) Copy `data/` to an external drive.
- **Saturday morning.** Finish step 11a; process the fields abroad as their downloads land; `index.json`.
- **Saturday afternoon.** Step 9 for the demo field, then for the fields abroad.
- **Saturday evening.** Step 8 (small version). Step 10 with the probe if the robot teammate is ready; record the probe
  log at the event.
- **Sunday morning.** Native-speaker review of the Nepali. Check the live site on a phone on mobile data, with the
  laptops off. Field memory only if everything above is done.
- **Sunday 14:00.** Feature freeze. `validate --final`, the full suite, `scan_history.py`, CREDITS and SI_LOG complete,
  README final.
- **Sunday 18:00.** The final commit and push by the owner; the live check on a phone that has never opened the site;
  submit by about 20:00, leaving four hours in hand.
