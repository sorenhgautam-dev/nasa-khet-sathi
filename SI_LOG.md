# SI_LOG.md

What SI (AI) generated, and what a person must review before it is frozen.

## 2026-11-11: build step 1 + data guards + audit (Claude Opus 5.5 via Claude Code)

### Generated

- Skeleton: `pipeline/` packages, `config/fields/`, `robot/firmware/`, `site/data/`, `tests/`,
  `scripts/`.
- `requirements.txt` (pinned to what installed), `.gitignore`, `pytest.ini`.
- `pipeline/export/schema.json` and `index_schema.json`: the contract in machine form.
- `pipeline/export/validate.py`: schema checks plus order, uniqueness, cross-references and array
  lengths. Warns while any MOCK file remains.
- `pipeline/export/mock.py`, which writes `site/data/fields/demo.json` and `site/data/index.json`.
  **Every number in demo.json is made up** and labelled MOCK.
- `pipeline/fetch/guards.py`: golden rule 12 (raw attributes, fill masking, range checks that never
  clip, data cards).
- `scripts/backup.sh` and `scripts/make_review_pack.py`.
- Tests: 127 in 6 files.
- `DATA_AUDIT.md`, `VALIDATION.md`, `CREDITS.md`, this file.
- Golden rule 12 added to CLAUDE.md, using your wording.

### Please review (in order of importance)

1. **Contract choices in schema.json.** The UI teammate builds against these, so confirm them before
   step 5:
   - month words: rain `low/medium/high`, soil `dry/medium/wet`, heat `none/some/high`, frost
     `none/risk/frost`, cover free text. `some`, `medium` and `wet` are my additions.
   - `sources[].type` is one of `satellite`, `model`, `station`, `probe`.
   - section ids look like `s1`, `s2`, …; polygon points are `[lon, lat]`, ring not closed.
   - replay years are limited to 2001 to 2025; future years to 2026 to 2100.
   - at least 3 plans, one with id `current`; every key is required and no extra keys are allowed.
   - `wetness` is 0 to 100; `temp` is -30 to 50 C (rule 12 bounds).
2. **Conflicts I did not resolve:** rule 11 ("projections are ranges") vs single numbers in `future`;
   the soil-moisture guard (0.6) vs SMAP L4's valid range (0.9).
3. **`.gitignore` fix:** `data/` became `/data/`, because plain `data/` would have hidden `site/data/`.
4. **DATA_AUDIT.md claims:** each VERIFIED line names its source (CMR concept ID or API). Spot-check a
   few.
5. **Guard design:** NaN passes the range check (missing data), infinity fails. Data cards refuse
   unknown keys; `notes` is the only optional key.

### Not done, and why

- No data fetched into the pipeline (step order; Earthdata login absent).
- No `crops.json` or `rules.yaml` (step 4).
- No pixel plots, cross-checks or switch-off numbers (no data, no field polygon).

## 2026-11-11 (later): owner decisions, contract fixes, build step 2 (Claude Opus 5.5 via Claude Code)

### Generated

- `MASTER_PROMPT.md`: the owner's brief, copied word for word from the first message of the session.
- CLAUDE.md edits: rule 12 (D2, per-field card paths), new rule 13 (no AI service from the site);
  layout; contract example and value rules (A13, D7); data-sources table (D1, D3, D4, D5); "who supplies
  what" (D6); groundwater (D7); water score; field memory now required (7b); new "SI components"
  section; build order (steps 2, 5, 6, 7, 7b, 9, 11b, 12).
- Contract: `future.*.harvest_low/high`, `diary.groundwater`, closed month words; validator checks
  low <= harvest <= high and the groundwater direction against the trend's sign;
  `pipeline/export/CONTRACT_CHANGES.md` for the UI teammate. Mock regenerated (still MOCK).
- Guards (D2): `valid_range=` hard limit, rule-12 warnings logged and counted, `scaled_range`,
  `assert_nonnegative`; card fields `range_warnings` and `segments`.
- Step 2: `config/fields/demo.yaml`, `pipeline/fetch/fields.py`, `power.py`, `credits.py`.
- Validation: `pipeline/fetch/ghcn.py` (station, validation only), `pipeline/checks/climate.py`,
  `pipeline/checks/crosscheck.py`, `scripts/run_checks.py`.
- Tests: 209 in total (82 new or changed this round).
- VALIDATION.md (six layers) and DATA_AUDIT.md, both rewritten.

### Please review

1. **`groundwater.confidence` is a number from 0 to 1** (like `sure`); you did not give a type.
2. **My tolerances for "roughly" and "near"** (pipeline/checks/climate.py, marked TODO-CONFIRM):
   1,260 to 1,650 mm; more than half of the rain June to September; 0 ± 3 C; 30 ± 3 C.
3. **Per-field paths:** `data/clean/<field>/`, `data/cards/<field>/`, `data/raw/<source>/<field>/`.
   This changes rule 12's `data/cards/<dataset>.json` and step 2's `data/clean/power.parquet`, so
   that step 11 needs no code change.
4. **The GHCN fetch went beyond step 2.** It was needed to judge your layer-3 expectations. It is
   validation only and never feeds the twin.
5. **Findings to act on:** POWER rain is 21% low against the station and has a suspicious 2001 to 2003
   drop (supports D6). POWER January nights are 3.8 C too warm (frost at step 8 needs a fix).
6. **D6 consequence:** step 5's replay now needs IMERG, so the Earthdata login must exist by step 5.
7. CLAUDE.md on disk was **not** the complete version you mentioned; my edits went into the file that
   was there, which still ends mid-word.

## 2026-11-11 (evening): owner review answers, decisions A to H, build step 3 (Claude Opus 5.5 via Claude Code)

### Generated

- CLAUDE.md: last word completed ("agronomist."); rule 2 now allows pushes only when the owner says so
  in the chat; sections for decisions A to D; FAOSTAT and GHCN rows; ET0 note; history scan (H) before
  any change to public, also added to the final-commit steps; layout.
- Tolerances: owner's approvals applied; January nights band now 0 to 5 C.
- A: `pipeline/twin/bias.py` + `pipeline/fetch/weather.py` (monthly station correction, held-out test,
  applied before ET0); B: `pipeline/checks/spikes.py`; C: `crosscheck.lag_correlation`; D:
  `pipeline/twin/inputs.py`; F: `pipeline/fetch/faostat.py`; H: `scripts/scan_history.py`;
  `config/rules.yaml` + `pipeline/fetch/rules.py` (every threshold with its source).
- E: `config/known_events.yaml`, 20 events + 2 negative controls + 7 unconfirmed, compiled by a research
  sub-agent that opened each cited page.
- G: CREDITS.md citations (POWER reference and data reference, Earthdata guidance as CMR has none,
  SoilGrids, FAO-56), found by a second research sub-agent on the official pages.
- Step 3: `pipeline/twin/et0.py` with FAO-56 Examples 2, 8 and 18 and the pyet comparison; `pyet==1.5.0`
  added to requirements.
- Tests: 282 (73 more than step 2). DATA_AUDIT.md and VALIDATION.md updated.

### Please review

1. **Cold-night overcorrection (VALIDATION 4.1b):** one offset per month makes Jan 2013's coldest night
   -4.2 C where Kathmandu reported -1.1 C. For frost at step 8, choose: (a) a correction that depends on
   the temperature itself (for example quantile mapping, needs your go), (b) keep the monthly offset and
   state the caveat, or (c) use uncorrected POWER for frost counts only.
2. **TODO-CONFIRM in rules.yaml:** at least 200 shared days per year (your 330 rule leaves no Tmin years),
   at least 20 per month, alternating split, apply only if the held-out error drops.
3. **GHCN is no longer validation only:** under A it corrects the twin's temperatures, so temperature
   checks against the same station are partly circular; the held-out test is the independent part.
4. **Rs/Rso floor of 0.3 in ET0:** added to FAO-56 eq. 39 (ASCE-EWRI 2005, as pyet does).
5. **Known-events list:** spot-check a few sources; 8 events hit the valley itself.
6. **Spike flags at the station:** 4 of the 9 flags are the station far above POWER (local storms a
   55 km cell average misses?); flagged, not removed.

## 2026-11-12: step-3 review answers, build step 4 (Claude Opus 5.5 via Claude Code, two research sub-agents)

### Generated

- Cold nights: `pipeline/twin/qmap.py` (empirical quantile mapping per month, per season if under 20
  days), compared with the offset on held-out years; wired into `fetch/weather.py`. Result: offset kept.
- Rain vote: `spikes.vote` (three sources vote once GPM exists), wired into `fetch/weather.py`.
- SoilGrids: `pipeline/fetch/soilgrids.py` (REST, factors from the API, nearest cell with values).
- Step 4: `config/crops.json` + `pipeline/fetch/cropslib.py`; `pipeline/twin/crops.py`, `soil_water.py`,
  `runoff.py`, `yield_.py`, `season.py`; `scripts/run_season.py` (plot `data/plots/demo/season_2016_dr.png`).
- `config/rules.yaml`: approvals, ASCE-EWRI and quantile-mapping citations, curve numbers, soil group,
  paddy, bare soil, unknown water source, crop-calendar rule.
- CLAUDE.md: cold-nights and vote rules, SoilGrids access rule, step-4 note. VALIDATION.md rewritten with
  "fitted reference" and "independent" labels; DATA_AUDIT.md, CREDITS.md updated.
- Tests: 386 (104 more than step 3). Process notes: the crops.json tests were written first but not run
  before the file existed; the ponded-balance test passed on its first run (it guards existing code).
- Sub-agents opened FAO-56 Chapters 6 and 8, FAO-66, TR-55, NEH 630 Chapters 7, 9 and 10, the FAO Crop
  Calendar API, a NARC Khumaltar paper, the ASCE-EWRI final report, and the HESS and Wiley pages.

### Please review

1. **Cold nights:** quantile mapping beat the offset on the two frost numbers but not on MAE (1.34 vs
   1.22 C). My reading "beats = all three" keeps the offset. If "beats" should mean the frost numbers,
   say so and quantile mapping goes in.
2. **The demo point has no SoilGrids prediction**; the soil comes from the cell 750 m west. Real field
   corners would settle this.
3. **Wheat was rain-fed in the test** (water_source unknown) and got 60% of potential in the 2015/16
   drought winter; the FAO Hill-zone calendar marks this wheat window "Irrigated Condition". Please set
   `water_source` in `config/fields/demo.yaml`.
4. **No Ky for rice** (nor lentil, mustard, buckwheat, finger millet) in any opened source: rice gets no
   harvest number. Options: find a peer-reviewed rice Ky, or report rice as water use only.
5. **Choices marked TODO-CONFIRM** (10 in rules.yaml, several in crops.json): scaling FAO-56 stage
   lengths to the local growing period; wheat treated as spring-habit (Kc ini 0.3, Ky 1.15); rice Kc end
   0.75 (midpoint of 0.90-0.60); default calendar windows; straight-row "good" curve numbers for a flat
   field; rice on the small-grain curve number; paddy ponded until a 10-day dry spell; nearest SoilGrids
   cell within 1 km; 99 quantiles; the vote's "station suspect" half.
6. **Bucket hand-over:** when the crop changes, depletion carries over as a fraction of TAW (the jump on
   18 March 2016 in the plot is this, not weather).

### Backup runs

(appended by each step)
- 2026-11-11 19:23: `scripts/backup.sh` -> `~/khet-sathi-backups/khet-sathi_2026-11-11_192320` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-11 19:53: `scripts/backup.sh` -> `~/khet-sathi-backups/khet-sathi_2026-11-11_195346` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-11 20:23: owner-approved commit `d4d3e49` (53 files) pushed to private `github.com/sorenhgautam-dev/data-test-game`, branch `main` (CLAUDE.md rule 2 exception). Jury .docx excluded via .gitignore.
- 2026-11-11 22:19: `scripts/backup.sh` -> `~/khet-sathi-backups/khet-sathi_2026-11-11_221921` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-12 00:28: `scripts/backup.sh` -> `~/khet-sathi-backups/khet-sathi_2026-11-12_002813` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-12 ~13:35: owner-approved commit `68de7c3` (106 files, 649 tests passed on the snapshot, history scan clean) pushed to private `github.com/sorenhgautam-dev/data-test-game`, branch `main` (CLAUDE.md rule 2 exception). Made by the second session (nasa-space-apps-e4) on the owner's word in that session's chat, as it reported. The snapshot is mid-work: it holds the review fixes as they stood at 13:34, while the fetch-module fixes were still in progress.

## 2026-11-12 (later): step-4 review answers, step 5 without GPM, placeholder field, box fetches (Claude Opus 5.5 via Claude Code, one research sub-agent, one review sub-agent)

### Generated
- **Step-4 review answers:** cold nights by role (offset for twin and ET0 as `tmin_c`; quantile mapping for frost only as `tmin_frost_c`; frost as risk bands, never a count); Ky 1.0 assumed for rice, lentil, mustard, buckwheat and finger millet (`ky_assumed`), with a sensitivity of 0.8 and 1.2; all TODO-CONFIRM choices marked approved (curve numbers to be revisited with the slope); `METHOD_NOTES.md` (new, 15 stated assumptions).
- **Bug found and fixed:** `season.simulate` never irrigated non-paddy crops. Irrigation is now wired, with the refill at the start of the day.
- **Step 5 without GPM:** `pipeline/plans/simulate.py` (rotation plan, replay, yearly rows, Ky sensitivity), `pipeline/plans/events.py`, `scripts/run_replay.py` (rain-fed and irrigated; a station-rain dry run, never exported), `pipeline/export/build_field_json.py` (refuses non-GPM rain, missing years or events, and an unlabelled placeholder).
- **ECC kit review:** the kit's silent-failure-hunter agent prompt was used, read-only, on the new code. Real findings fixed test-first: a NaN ET0 that turned every later year into 0 %, date gaps that shifted seasons, POWER fill outside the GPM record exported as GPM, an unknown water-source spelling treated as irrigated, null events crashing the export, an empty held-out split, and a soil that holds no water. The kit's skills and agents were not installed (blocked as a self-modification).
- **Placeholder field (owner, 2026-11-12):** `pipeline/fetch/worldcover.py` picks the nearest 100 m square of WorldCover cropland with a 30 m margin. Result 27.6785 N, 85.427417 E (0.98 km N of the old point); `demo.yaml` is relabelled and the mock export and index follow it.
- **Fetchers:** WorldCover, NASADEM (elevation and slope), GRACE, AppEEARS (MODIS, SMAP L3 and L4), COG windows (HLS-VI, ECOSTRESS V003 then V002), GPM (GES DISC OPeNDAP, with a host fallback); the POWER cache is now keyed by point. Dependencies earthaccess, h5py and rasterio (owner's go) are pinned, plus `requirements-lock.txt`.
- **Research sub-agent:** opened the sources for the event rule (NDMC deciles, WMO SPI guide, McKee 1993, DHM rain scale, Zheng et al. 2015, Frederiks et al. 2015). No seasonal rice Ky was found.

### Please review
1. **Placeholder field:** check 27.6785 N, 85.427417 E on Google Maps (corners in `config/fields/demo.yaml`; plot `data/plots/demo/placeholder_field.png`).
2. **Event rule (TODO-CONFIRM):**
   - drought = a season's rain in deciles 1-2 of that crop's 25 seasons (a short record);
   - flood = a day of 100 mm or more (DHM "very heavy"; or 200 mm, "extremely heavy"?);
   - frost = wheat only, below 0 C in the FAO mid-season stage;
   - precedence drought, flood, frost.
3. **Replay year rule (TODO-CONFIRM):** a season belongs to its harvest year; the year's harvest is the mean of its crops; 2001 has rice only.
4. **Contract proposal:** add `irrigated: {harvest, dry_days}` to each replay year (`CONTRACT_CHANGES.md`). It waits for your go.
5. **Dry-run findings** (TEMPORARY station rain, not evidence):
   - the 2015/16 winter drought matched;
   - 2016/17 wheat is just as low with no known event;
   - the 2015 monsoon drought is invisible to ponded rice.
6. **Slope 2.2 deg** over the placeholder: revisit the curve numbers (straight row vs contoured or terraced).
7. **GES DISC EULA:** needed before GPM, and so before the real replay.

### Backup runs
- See the step summary for the backup folder name.

## 2026-11-12 (night): the demo field moved 25 m north (REVIEW_NOTES H3)

**What the owner decided:** move candidate 1 (centre 27.690542 N) 25 m north to **27.690767 N, 85.441792 E**, still a
60 m square. On Google Maps, the Kasan River's riparian strip ran along the square's southern edge.

### What SI (Claude) did
- **Polygon** from `worldcover.square_polygon`: `[[85.441487, 27.690497], [85.442097, 27.690497],
  [85.442097, 27.691037], [85.441487, 27.691037]]`.
- **Tree-line and candidate-rule check** for the moved square, rerun after the HLS composites were rebuilt. Results are
  in REVIEW_NOTES.md H3; the scripts and map are in a session scratchpad.
  - No tree cell or evergreen-like pixel touches the square; the trees are 117-142 m north.
  - The covering pixels stop about 6 m north of the river line as described.
  - The season test passes.
  - Its 30 m margin is 77 m from the nearest built-up pixel, against the search's 100 m.
- **H3 applied everywhere:**
  - `config/fields/demo.yaml`, with `earlier_placeholders`.
  - NASADEM rerun: 1,325.0 m and 1.6 deg over 4 pixels.
  - `weather.parquet` rebuilt: mean ET0 3.5071 → 3.5076 mm/day.
  - Mock `demo.json` and `index.json` regenerated, then validated.
  - `placeholder.py` now labels the configured field "chosen" and takes the earlier squares from the config. It used
    to call whatever `demo.yaml` held "rejected". The script was rerun: same three candidates.
  - `weather.py` now stops if GPM rain was fetched for a 0.1 deg cell other than the field's. The moved field is in the
    same cell, (2654, 1176).
  - Tests were written first; the docs were updated: CLAUDE.md, METHOD_NOTES 13, VALIDATION 1.4, DATA_AUDIT,
    CONTRACT_CHANGES.

### Please review
1. **The built-up margin.** The moved square is 107 m from the nearest built-up pixel, but its 30 m margin is 77 m from
   it, so it misses the search's rule.
2. **The south-east corner on imagery.** A faint line of slightly greener pixels runs south-west to north-east just
   south-east of the square. If that is the river, its strip comes closest at that corner.
3. **Slope.** The mean slope is now 1.6 deg (it was 2.2 over the first placeholder). This feeds the curve-number
   question.

## 2026-11-12: plain words, SI component 3, text only (parallel session; copied from notes/parallel_session.md)

- 2026-11-12, Claude (Opus 5.5), parallel session. Drafted all English and Nepali texts in `pipeline/words/*.json`:
  glossary, crop explainers, five-tab templates, tips, and screen texts.
- A research sub-agent (Claude) opened FAO, CGIAR (CIMMYT, ICRISAT) and NARC pages and PDFs and copied quotes
  verbatim. Its scratch downloads are in the session scratchpad, not the repo.
- Person to review: a native Nepali speaker reviews every Nepali text; the owner reviews the English and the choices
  listed in notes/parallel_session.md. Not reviewed yet *(at the time of the parallel session; see the entries below
  for the owner's review and decisions)*.

## 2026-11-12 (night): owner's review of the Nepali words (screens and glossary)

**What the owner decided:** after reading the Nepali for the screens and the glossary in `pipeline/words/PREVIEW.md`,
spell frost तुषारो, not तुसारो, everywhere. Mark the screens and the glossary as reviewed, including the fixed lines.
The tabs, tips and crop explainers keep "needs native-speaker review": the owner has not read them yet.

### What SI (Claude) did
- **तुसारो → तुषारो in 7 texts.** Five are in `screens.json`, one in `glossary.json` ("frost risk") and one in `tabs.json`
  (the "unknown" tab's frost line). The 7th was missed in the first count of 6. The tabs line keeps
  "needs native-speaker review".
- **Review mark.** `texts.is_review_mark` accepts "needs native-speaker review" or "reviewed by <name>, <YYYY-MM-DD>".
  The name may not be blank or a [template placeholder], and the date must be real. `tests/test_words.py` uses it in
  place of the old "every text needs review" check. Tests were written first: 37 words tests, 534 in the full suite,
  all pass.
- **PREVIEW.md** now lists each word file's review status at the top and puts a status line above each of its
  22 tables. Together the tables cover all 304 texts. The page was regenerated.
- **Not done yet: the "reviewed by" mark.** Both replies carried the template's "[your full name]" and no name, and
  SI will not guess a reviewer's name. All 304 texts still say "needs native-speaker review". When the owner gives the
  name, the 169 screen texts and the 64 glossary texts get "reviewed by <name>, 2026-11-12".

### Please review
1. **The reviewer's name** for the mark.
2. **Other Nepali fixes.** The second fix in the reply was still the template line "[any other fix ...]", so only the
   frost spelling was changed.

## 2026-11-12 (late night): REVIEW_NOTES fixes, words decisions, Nepali tabs contract (Claude Opus 5.5 via Claude Code; one audit, three fix and one research sub-agent)

After VS Code closed, the owner made this the only build session (a second session that had received the same list
stayed read-only; it later committed and pushed `68de7c3` on the owner's word in its own chat, logged under "Backup runs").

### What SI did
- **State check.** Full suite 534 passed. HLS and ECOSTRESS retries had finished (all granules, 0 failures). GPM had
  stopped at 2009-03-03 (2,980 of 9,131 days) and was restarted from the cache; an AppEEARS poller waits for the 13 SMAP
  tasks still processing at NASA. A read-only audit sub-agent checked every REVIEW_NOTES item: only H3 was done.
- **Words (owner's decisions 1-10).** Bikram Sambat months first in Nepali with the Gregorian months beside them
  (e.g. बैशाख (Apr–May)) and a "don't line up exactly" note on the three screens that name months; section `temp`
  worded as soil temperature from the probe; approvals recorded in notes/parallel_session.md; PREVIEW.md regenerated.
  The new Nepali lines need the owner's review.
- **Contract.** `plans[].tabs_ne` and `tips_ne` (required, Devanagari, same count as the English tips); `event` loses
  `frost` (M1). Schema, validator, mock, CONTRACT_CHANGES.md and CLAUDE.md updated; tests first.
- **REVIEW_NOTES fixes.** Every item; status table in REVIEW_NOTES.md. Three sub-agents fixed code in separate files,
  tests first (twin and crops; fetch modules; weather and greenness); this session made the modelling decisions, edited
  every shared document and rules.yaml, checked the key code (ponded day, ea cap) and reran the dry run, the 2016 season
  test and the field-pixel check on the final soil table. A research sub-agent opened FAO, IIASA and ISRIC pages on
  HWSD v2 (licence and access only; nothing downloaded).
- **Recorded:** the 77 m built-up margin, accepted by the owner (CLAUDE.md, demo.yaml, METHOD_NOTES 13, VALIDATION 1.4).
- Tests: 534 → 654, all pass with deprecation warnings as errors. The export validates (still MOCK).

### Please review (owner)
1. **Rain-fed paddy (H1)** now gets no outside water; this changes approved METHOD_NOTES item 2. Rain-fed rice is 100%
   in 4 of 6 dry-run seasons (all 6 before); the 2015 monsoon drought is still a miss.
2. **The ea cap (M6)** binds on 55% of days and raises ET0 3.4% (1,325 vs 1,281 mm/yr), mostly July-October.
3. **POWER rain fill cap**: 5% of a year's days (TODO-CONFIRM).
4. **HWSD v2**: readable without new packages via ISRIC's SQLite copy, but CC BY-NC-SA and least reliable in South Asia.
   Not used; soil is the SoilGrids cell 859 m SE.
5. **Section `temp` before any probe reading**: allow `null`?
6. **Step 7**: maize→rice and maize→finger millet are refused because the FAO windows overlap (relay crops?);
   finger-millet stages stretched to 117 d (TODO-VERIFY); lentil 133 d; mustard stays calendar-only; rice p 0.20.
7. **water_source** is still null, so the export would show rain-fed potato at 31-68% in dry winters.
8. **Months**: Latin "(Apr–May)" as in the owner's example, or Devanagari "(अप्रिल–मे)"? BS start days TODO-VERIFY.
9. **ECOSTRESS V002** QC and cloud read 0 where data is missing: the diary must mask by LST/ESI.

### Backup runs
- 2026-11-12 13:41: `scripts/backup.sh` -> `~/khet-sathi-backups/khet-sathi_2026-11-12_134141` (6.0 MB; data/, .env*, .netrc, .venv excluded; checked). 654 tests passed just before.
- 2026-11-12 14:04: commit `94be2f4` (11 files: `ghcn.py`, `appeears.py` and their tests, plus this session's doc and rules.yaml edits) pushed to private `github.com/sorenhgautam-dev/data-test-game`, branch `main`, by the fetch-module sub-agent, which reported that the owner asked it mid-run (654 tests passed, pending diff searched for secrets; `scan_history.py` not run). **Not authorised through this session's chat; the owner to confirm.**
- 2026-11-12 ~16:05: owner-approved commit `a6b7160` (2 files: DATA_AUDIT GPM outage note, SI_LOG) pushed to private `github.com/sorenhgautam-dev/data-test-game`, branch `main` (CLAUDE.md rule 2 exception; the owner said "commit and push" in this session's chat). 654 tests passed; `scan_history.py` clean (8 commits, 0 hits).
- 2026-11-12 ~16:10: commit (SI_LOG only: the `a6b7160` line above and this one) pushed to `github.com/sorenhgautam-dev/data-test-game`, branch `main`; the owner said "commit and push" in session 7a992fe8's chat. 654 tests passed; `scan_history.py` clean (9 commits on all refs, 0 hits). **The repository is public, not private:** GitHub records it as public since it was created (2026-11-11 13:27 UTC, a `PublicEvent` at creation; Pages off), so every push so far (`d4d3e49` to `a6b7160`) was public, and the entries above that say "private" are wrong. Asked, the owner chose to keep it public and push (2026-11-12). CLAUDE.md rule 2 still says "private repository": the owner to update it.

## 2026-11-12 (evening): owner review of d34fa93, items 1-11 (Claude Opus 5.5 via Claude Code, session 7a992fe8; one web-fetch and two research sub-agents)

### What SI did
- **1.** `requirements.txt` pinned pandas 3.1.1, which pyet 1.5.0 forbids (its metadata: `pandas<3.0,>=2.1`); pinned 2.3.3. New test: every pin equals the lock file. A fresh Python 3.12 venv installed from `requirements.txt` alone matched `requirements-lock.txt` exactly (pip freeze diff empty) and passed the suite (659 at that moment).
- **2.** Deleted the stray root file `tmax` (it held only "--- tmin check.", a shell redirect).
- **3-4.** `README.md` (plain words; a test checks that every command it names exists) and `LICENSE` (MIT, "The Khet Sathi team"; the owner may want names). The README says data and texts keep their own licences.
- **5.** GitHub Actions workflow `.github/workflows/pages.yml` publishes `site/` (simpler than moving it to `docs/`); action versions checked against each action's latest GitHub release (checkout v7, configure-pages v6, upload-pages-artifact v5, deploy-pages v5). CLAUDE.md layout and final-commit step updated.
- **6.** FAO-56 Kc climate adjustment (eqs. 62, 63, 65) per season, test-first from FAO-56 Example 27 (maize: Taipei 1.07, Mocha 1.30) and Box 15 (dry bean 1.19; Kc end 0.35 not adjusted); crop heights from Table 12 (`crops.json` `height_m`); `rules.yaml` `kc_climate`. The equation is an image on fao.org; its form was confirmed by the text of Chapter 7's analogues, and the three published results are reproduced. First real replay on GPM rain: rain-fed yearly harvest 74.4 → 74.2%, rice Kc mid 1.20 → about 1.15, potato about 1.16, irrigation 269 → 265 mm/yr, no event changed. Bare-soil surface layer (eqs. 71-74) **not done**; its upper bound is +5 points on potato.
- **7.** Status table for H1-L7 at the top of REVIEW_NOTES.md: 23 fixed, 1 partly fixed (M7).
- **8.** TODO-CONFIRM batch: 25 decisions with recommendations (given to the owner in the chat). The flood claim (item 18) was re-checked against the replay: at 200 mm only 2002 and 2024 stay flood years.
- **9.** TODO-VERIFY triage: 92 lines; 46 change a shown number (a), 18 documentation only (b), 28 not markers. Closed with opened sources: IMERG UTC day, GHCN/GSOD GMT day (was wrongly "not documented"), SMAP L3 quality bit, SoilGrids factors, NASADEM EGM96, ECOSTRESS units/QC/cloud/ESI, NEX-GDDP units and wind height. Still open: crop Ky and buckwheat/mustard values (no published source found), POWER flags, IMERG `precipitation_cnt_cond`, ECOSTRESS time stamps, NEX-GDDP calendars, several known events.
- **10.** GPM is complete (9,131 of 9,131 days). Sensitivity, not applied: GPM rain scaled to the station mean (x0.66) gives flood years 10 → 3 and potato 46.3 → 37.9% (VALIDATION 3.9).

### Please review (owner)
- The TODO-CONFIRM batch, especially water_source (item 8), flood 100 → 200 mm (item 18) and exporting only complete years 2002-2025 (item 14).
- The LICENSE holder line, and the README's wording.
- RHmin from ea capped at e°(Tmin) reads about 56% in the monsoon mid-season, which may be low; if so, the Kc mid reduction for rice is too small (METHOD_NOTES 16).
- Two verified known events wait for your decision before they enter validation 4.1: the Jure landslide of 2 Aug 2014 (rain-triggered, but outside the valley) and Kathmandu -0.2 C on 12 Jan 2010.

### Backup runs
- 2026-11-12 17:57 and after this entry: `scripts/backup.sh` (675 tests passed just before). No commit, no push (owner: "Do not push unless I say so").

## 2026-11-12 (Thursday evening): the owner's decisions on the 17:58 report (Claude Opus 5.5 via Claude Code, session 2f8edafe; one web-fetch sub-agent)

The owner's decisions were given in this session's chat (session 7a992fe8, which wrote the report, was told and
stayed read-only). Batch file used: 7a992fe8's `todo_confirm_batch.md`. Item 4 (Kc) and the TODO-VERIFY closures
were already in the working tree (7a992fe8) and were not re-applied.

### What SI did
- **Approved as recommended** (owner: every item except 8, 18 and 22): items 1-3, 5-7, 9-17, 19-21, 23-25. Source texts
  in `rules.yaml`, METHOD_NOTES, REVIEW_NOTES, DATA_AUDIT and VALIDATION now say "owner's batch decisions, item N";
  no TODO-CONFIRM is left open in `rules.yaml`, METHOD_NOTES, VALIDATION or DATA_AUDIT.
- **Code, tests first:**
  - item 14: `build_field_json.complete_years` exports only years holding every crop of the rotation (2002-2025);
  - item 16: `simulate.rotation_for`: the placeholder rotation only for fields listed in `rules.yaml`
    `replay.rotation_unknown_fields` (the demo); any other field without a rotation stops;
  - item 10: `crops.sow_date(position=start|middle|end)` for step 7's generator;
  - item 23: section `temp` may be null (schema, mock, tests);
  - item 25: `cogwindows.layers_where_valid` keeps ECOSTRESS QC and cloud only beside a valid LST or ESI,
    tested on a cached V002 window;
  - item 24: `rules.yaml` `probe.repeat_spread_max_pct` = 3.
- **Item 8 (owner's alternative):** water source stays unknown and both cases are shown side by side.
  New required contract field `field.water_source` ("unknown" for the demo), set by the export from the replay;
  `simulate.WATER_CASES["unknown"]` = rain-fed; screen labels "If you can't water" / "If you can water".
- **Item 18 (owner's alternative):** flood rule fixed in advance from sources, never tuned on the known floods:
  the year's wettest crop-season day (ETCCDI Rx1day) in deciles 9-10 of the record's years (NDMC classes,
  Gibbs & Maher 1967). Both sources opened by a web-fetch sub-agent and quoted in `rules.yaml`. Result
  (VALIDATION 4.1, independent): 2 of 2 valley floods (2002, 2024); 2025 flood-class but shown as drought;
  2006 and 2020 flagged with no listed flood. The drought half of 4.1 is marked not fully independent (deciles
  1-2 were preferred partly because they matched more known droughts).
- **Item 22:** Nepali months "बैशाख (अप्रिल–मे)" (Gregorian names in Devanagari); registry examples and the
  earlier Latin-style test updated.
- **Rain plan A:** four "unknown"-tab lines (condition `station_rain_lower`): our rain comes from space; the
  airport measures about a third less; its record may miss some rain; we do not know which matches the field.
  `scripts/run_checks.py` rerun: GPM +41.2% against the station over 49 complete months (station 29% lower).
  B is planned for Friday; C only if B shows GPM reads high.
- **Audio removed:** the "Listen" button from the word files; CLAUDE.md site rules, SI component 3, layout and
  build step 7 now say text only. A test fails if an audio button or sound-file text comes back.
- **CLAUDE.md rule 2:** the repository is public by the owner's choice (2026-11-12); push only when the owner says
  so; `scripts/scan_history.py` before every push. Also: approved libraries (rule 9), contract text, probe bridge,
  rain plan, step 5 status.
- **Libraries:** scikit-learn 1.9.1, ruptures 1.1.10, pymannkendall 1.4.3, flask 3.1.3, pyserial 3.5, installed
  with every existing version held (constraint: the old lock file), pinned, lock file refreshed, CREDITS updated.
- **Probe:** `robot/probe.py` parses exactly the owner's line format ("Check wiring" gives temp null; out-of-range
  values and partial or boot lines refused), `robot/bridge.py` reads the serial port (or stdin) and writes
  `site/data/live.json` atomically with `sure` null until step 10, logging every line; `robot/fake_probe.py` prints
  the same lines to stdout or a pseudo-terminal. 27 tests, including an end-to-end run through a pseudo-terminal.
- **Replay rerun** with the new rules (`data/checks/demo/replay.json`); mock `demo.json` regenerated for the
  schema change; `CONTRACT_CHANGES.md` entry for the UI teammate.

### Owner decisions recorded
- The `94be2f4` push by the fetch sub-agent: **confirmed by the owner** (2026-11-12).
- The Nepali reviewer's name comes when the review is done; every text keeps "needs native-speaker review" until then.

### Please review (owner)
1. **Flood years 2006 and 2020** have no listed flood; 2006 is a listed national drought year. The rule is relative
   (about one year in five), like the drought rule.
2. **The baud rate** (115200 assumed): the probe's `Serial.begin` rate, from the robot teammate.
3. **"About a third less"** is 29% over 2015-2022's complete months (34% from 2016 in the 7a992fe8 check).

## 2026-11-12 (late evening): online probe (option B) decided, not built (Claude Opus 5.5 via Claude Code, session 2f8edafe; one web-fetch sub-agent)

- **Owner's decision:** option B with Firebase Realtime Database on the free Spark plan, built only after the
  must-have steps (CLAUDE.md build step 10b). CLAUDE.md's out-of-scope rule now allows this one database for live
  probe readings only; "no backend" and judge requirement 1 say the live probe is an extra.
- **Checked on Firebase's own pages (web-fetch sub-agent, 2026-11-12):** Spark Realtime Database: 100 simultaneous
  connections, 1 GB stored, 10 GB/month downloaded, one (default) database; a quota overage shuts that product off
  for the rest of the month; "No payment method needed"; **no statement found** that a Spark project or database is
  paused, suspended, archived or deleted when idle (pricing, database limits, pricing plans, full FAQ, terms, API
  keys, locations and auth limits pages searched); asia-southeast1 (Singapore) offered, location fixed once chosen;
  web API keys restricted to Firebase services are "OK to include in code"; the terms acceptance says use is "for
  purposes related to my trade, business, craft, or profession". Not found: an age clause in the Firebase terms;
  whether anonymous-account clean-up is off by default.
- **Not done:** firmware (the owner's probe code was not in the message: the template line "[paste your probe code
  here]" came through instead); rules, live view and tests wait for the must-have steps.
- **Probe sketch received (owner, 2026-11-12, late evening):** kept unchanged in `robot/firmware/original_probe/`
  (also the USB-only fallback firmware). It settles the baud rate (115200; `bridge.DEFAULT_BAUD`, was TODO-VERIFY)
  and confirms the line format the bridge parses; new tests check the parser against the sketch's own print
  statements (740 tests pass). Notes for step 10b, not acted on: GPIO34 is an ADC1 pin, so it still reads with
  Wi-Fi on, but Wi-Fi can add ADC noise, so the bench test of repeat spread (VALIDATION 5.2) should run with
  Wi-Fi on; the sketch limits moisture to 0-100 (`constrain`), so a 0 or 100 may be a limited value; a DS18B20
  power-on 85.0 C is refused by the bridge's range check.
- **Owner, 2026-11-12:** step 10b sends the raw moisture reading too (before mapping and limiting), beside the
  percentage, so a limited 0 or 100 % is visible; the USB line is unchanged. Recorded in CLAUDE.md step 10b; not built.

## 2026-11-12 (night): build step 6a, onset, greenness, bare days (Claude Opus 5.5 via Claude Code, session 2f8edafe)

### Owner decisions recorded first
- Commit `c1778e5` pushed on the owner's word (740 tests on the snapshot; history scan clean). The step 5 export had
  already been committed and pushed by session 7a992fe8 as `efc1bb2` (22:25).
- **Rain check B (Friday) gains a break test**: change points in yearly GPM totals and the yearly GPM/POWER ratio
  (2001-2025) and the 4 neighbouring cells. Until settled, every rain or monsoon-shift trend carries
  `rules.yaml` gpm_series.trend_caveat (CLAUDE.md, METHOD_NOTES 21, VALIDATION 3.9b).
- **Known events**: Jure landslide excluded (owner's reason recorded); Kathmandu -0.2 C on 12 Jan 2010 added as a
  frost-band check, not a replay event (VALIDATION 4.1c). Early look: the twin's frost Tmin gives January 2010 only
  4 nights below 2 C, so the check may fail once the band rule exists.

### What SI did (tests first)
- `pipeline/diary/onset.py` (13 tests) and rules.yaml `monsoon_onset` from CLAUDE.md, with Claude's readings marked
  TODO-CONFIRM (wet day >= 1 mm; wet days need not be consecutive; look-ahead = the 20 days after the onset day;
  search ends 30 Sep).
- `pipeline/diary/greenness.py` (16 tests) and rules.yaml `greenness`, `bare_days`; `scripts/run_diary.py` writes
  `data/checks/demo/diary_onset.json`, `diary_bare_days.json`, `data/clean/demo/greenness_field.parquet` and the
  card `greenness_field.json`.

### Findings
- **Onset rule fails its sanity check** (VALIDATION 4.1d): median 16 May; 21 of 25 years on 15-17 May; POWER rain
  gives the same, so it is not GPM. Late May already brings 60-80 mm on 5-11 wet days.
- **Bare days**: HLS years about 62 a year; MODIS years about 32, not comparable (VALIDATION 3.10).

### Please review (owner)
1. **The onset rule.** Options (sources to be opened before use):
   (a) the anomalous-accumulation method (Liebmann & Marengo 2001 style): onset = the day after the cumulative
       rain anomaly (daily rain minus the record's mean daily rain) reaches its lowest point; no thresholds to tune;
   (b) stronger thresholds from a published South Asian point definition (needs a source);
   (c) keep CLAUDE.md's rule but search from 1 June (a choice without a source).
   Recommendation: (a), checked against "about 10 June" and the GPM-break caveat.
2. TODO-CONFIRM choices: 75% clear pixels, MODIS reliability 0 only, uncertain when observations are more than
   30 days apart, onset readings.

## 2026-11-12 (late night): build step 6b, three season-detection methods (Claude Opus 5.5 via Claude Code, session 2f8edafe)

### Owner decisions recorded first (pasted in the chat, 2026-11-12)
- Commit `f37ecc6` (step 6a) pushed on the owner's word (768 tests on the snapshot; history scan clean).
- **Firebase** project `khet-sathi-probe` ready (Spark, Singapore, anonymous sign-in on, clean-up off); web config in
  `.env` (gitignored); the database refused an unsigned read and write. **Keys, approved in advance for step 10b**: two
  keys, both limited to the Identity Toolkit and Token Service APIs; the website's also limited to the GitHub Pages
  address; the probe's with no website limit. `scan_history.py` will let through the website key by its exact value
  only; the probe key never enters the repository (CLAUDE.md step 10b).
- **Onset rule kept as set in CLAUDE.md, no tuning to the results** (15- and 20-day versions as robustness checks).
- **Flood rule unchanged**: 2006 and 2020 reported as "flagged, no recorded flood"; 2020 noted against the GPM wet
  shift after 2017 that rain check B tests (VALIDATION 4.1).
- Thresholds: the owner asked to see each with its source and approve them in one batch.

### What SI did (tests first)
- A research sub-agent opened the sources for the TODO-CONFIRM thresholds and the new season settings; Claude checked
  the key quotes in the saved text (MOD13 Table 4, Killick et al. SIC, TIMESAT 4.4, MSLSP30NA 3.3, MCD12Q2 2.2) and
  opened the DHM onset page itself (normal onset 13 June, eastern Nepal; latest 27 June 1982; withdrawal 2 October).
  The sources are in rules.yaml; every choice stays TODO-CONFIRM until the batch.
- `pipeline/diary/seasons.py` (threshold method, change-point method, labels, thinning, scoring, choice) and
  `pipeline/ml/seasons.py` (season detective features, training, prediction), 19 tests in `tests/test_seasons.py`
  (worked examples: 20% of a 64-day rise is day 73; PELT finds the kinks 60, 124, 188 of a clean series).
- rules.yaml `season_detection`: the comparison design (held-out years, 16-day thinning, reference, 2-point margin)
  was written **before** the comparison was first run. One miscount in its text ('2017-2025' for the years with 90+
  clear observations; the rule gives 2018 and 2022-2025) was corrected afterwards; the rule itself was not changed.
- `scripts/run_diary.py --steps seasons` writes `data/checks/demo/diary_seasons.json` and
  `data/clean/demo/seasons_daily.parquet` (the chosen method's day labels, for step 6c's monthly cover).

### Findings
- Held-out mean scores (threshold / change-point / detective): 0.967 / 0.958 / 0.982.
  The detective is highest but short of the 2-point margin, so **the threshold method is used** (VALIDATION 3.15).
- Every HLS year has two seasons: winter green-up late Dec-Jan, peak March, end mid-May; monsoon green-up June-early
  July, peak August, end late October. The winter season's mid-May end fits wheat better than the placeholder's potato
  (to weigh in step 6c's rotation guess, not decided here).
- NASA's MCD12Q2 amplitude rule (>= 0.1 and >= 35% of the series range) gives exactly the same seasons as the
  unsourced 0.2.

### Please review (owner)
1. The threshold batch (each with its source, in the chat and in rules.yaml).
2. The method page needs a contract field (CLAUDE.md SI component 1): proposal in the chat; nothing is added to the
   schema without the owner's go.

## 2026-11-13 (Friday, early): approvals applied, method page, build step 6c (Claude Opus 5.5 via Claude Code, session 2f8edafe)

### Owner decisions (pasted in the chat)
- **Every threshold with a published source approved**, including the sourced replacements Claude recommended:
  onset look-ahead counted from the onset date (Moron et al. 2009; changes no year), uncertain bare days after a
  20-day gap (NASA MSLSP30NA; was 30), the season amplitude rule of NASA MCD12Q2 (>= 0.1 and >= 35% of the 3-year
  range; same seasons and scores), DHM's normal onset (13 June, eastern Nepal) as the onset sanity date. The
  unsourced choices are listed separately for the owner (chat).
- **Season detection agreed**: the threshold method stays (the AI did not beat it by the margin set in advance);
  the full three-way comparison goes into VALIDATION.md and the method page (`method.season_detection`, new
  contract key). Field memory (7b) stays on the plan.
- **Rotation guess**: weigh the evidence fairly; if rice then wheat fits better, say so and use it.
- A further list of accuracy upgrades (rain against DHM normals and CHIRPS, the GPM 2017 jump, seasons into the
  replay, rice flooding evidence, MODIS-HLS harmonisation, ranges, method-page context), after the must-haves.
  Four research sub-agents started on the parts that need sources (no repository edits).

### What SI did (tests first)
- `pipeline/diary/groundwater.py`, `trends.py`, `months.py`, `guess.py` with 18 tests (`tests/test_diary_6c.py`);
  two of Claude's first expectations in those tests were wrong (a tercile count; exact ties in a sine series) and
  were corrected after checking by hand, the code unchanged. rules.yaml `groundwater`, `trends`, `months`,
  `rotation_guess` written before the first run; `trends.shift_days_unmeasurable_when` was set after seeing the
  pinned onsets (said so in its source).
- `scripts/run_diary.py --steps diary` writes `data/checks/demo/diary.json` and the GRACE card;
  `build_field_json` now writes the real diary and the method page into `demo.json` (validated).

### Findings
- GRACE: falling -2.57 cm/yr (2002-2026, p about 0), regional. Frost check January 2010: high (PASS, one event).
- Onset pinned at 15-17 May in 21 of 25 years: `shift_days` null. Hot days falling, heavy-rain days rising
  (GPM caveat), dry spells no clear trend.
- Rotation guess by the rule fixed in advance: **rice then potato**, but the winter slot is a near-tie with wheat
  (72 vs 74 days); timing cannot separate them.
- GitHub Pages: the four failed runs stop at `configure-pages` with "Not Found": Pages is not enabled on the
  repository (`has_pages: false`). All four action versions exist (checkout v7.0.1, configure-pages v6.0.0,
  upload-pages-artifact v5.0.0, deploy-pages v5.0.1 are the latest releases). Hand step for the owner.
- **Slip, found by the full test suite and fixed:** Claude's new `groundwater:` block in rules.yaml repeated an existing
  key, so YAML silently replaced the owner's GRACE rules (caveat, scale-factor decision M4), and the first diary run
  re-read the raw GRACE file and overwrote `data/cards/demo/grace.json`. Fixed: the three new entries were merged into
  the original block, the diary now reads `data/clean/demo/grace.parquet` from `pipeline/fetch/grace.py`, and the card
  was rebuilt from the cached file (same trend). `tests/test_rules.py` should catch a repeated top-level key next time
  (added).

### Rain check B, first result (research sub-agent, 2026-11-13; Claude checked its tables)
- Daily IMERG V07 Final and Late files have no uncalibrated field (DDS of a 2017-07-15 granule: precipitation,
  MWprecipitation, counts, randomError, probabilityLiquidPrecipitation); the half-hourly files carry
  precipitationUncal (V07 release notes; ATBD Table 5). Late V07 was reprocessed back to 1998 with the Final's
  climatological gauge adjustment (release notes; ATBD Table 3).
- **The 2017 jump coincides with the loss of gauges**: IMERG monthly gauge weight 96-97% (2001-2016) -> 56-72% (2017+),
  equivalent gauges about 60 -> about 9; GPCC Full Data V2022 stations in the field's 1-degree box about 50 -> about 1
  a month (2017-2020). Claude recomputed the yearly means from the saved tables. Confirmation (Final vs Late) and the
  owner's other rain checks are still to run.


### Upgrade items 3 and 6, sources checked (research sub-agent, 2026-11-13; Claude spot-checked the saved texts)
- The owner's "Zhang et al. 2026, ESSD" is **Zhao, Zhang, Dong, Yang, Fan, Liu & Xiao (2026)**, "Mapping paddy rice
  distribution and cropping intensity in South and Southeast Asia (1995-2024) at 30 m resolution", ESSD 18:5583-5599,
  doi:10.5194/essd-18-5583-2026. Region: Vietnam, Thailand, Cambodia, Myanmar, Laos, Bangladesh, India, Pakistan
  (**not Nepal**). Flooding rule (sec. 2.3.2): in the 90 days before each season's peak, LSWI + 0.05 >= EVI, with
  EVI <= 0.35 and LSWI > 0.05. 83.74-87.60% is **overall accuracy** of the rice map (Table 3); rice producer's
  accuracy 0.69-0.78; sec. 4.1: rain-fed rice 'often fail[s] to produce a clear flooding signal'.
- Sci Rep 12:13210 (2022), doi:10.1038/s41598-022-17454-y (southern Punjab, Pakistan, 2020): abstract 'overall
  accuracies ... 96% for Sentinel-2, 91.7% for Landsat-8, and 82.6% for MODIS' for a random-forest rice/non-rice map;
  **its own error matrix gives 96.7% (Landsat-8) and 92.6% (MODIS)** (sub-agent's arithmetic; no correction found).
  Rice-class F1 83.8 / 75.5 / 65.5. Mapping accuracies, not season-date accuracies.
- HLS VI v2.0 User Guide: layers `.EVI.tif` and `.NDMI.tif`, int16, scale 0.0001, fill -19999; NDMI =
  (NIR - SWIR1)/(NIR + SWIR1), the LSWI formula (L30 B5, B6; S30 B8A, B11). Not the HLS 'NDWI' layer.

### Upgrade item 1b, CHIRPS and APHRODITE access (research sub-agent, 2026-11-13)
- **CHIRPS v3.0** (released 2025-01-01; 0.05 deg; 60N-60S; daily `final` for 2025 exists). Use the daily **`rnl`**
  variant: `sat` disaggregates pentads with IMERG Late V07 ('not independent validation', daily readme). Even `rnl`
  is scaled by a 1991-2020 climatology that 'incorporate[s] IMERG v6 Final inputs' (chirps3 page), so its year-to-year
  changes come from infrared cloud data and stations. CHC's Nepal station plot: about 55 stations a month in
  2001-2010, about 2-10 from 2011, flat across 2017, so **CHIRPS has its own break in 2011** but can test GPM's 2017
  jump. CHIRPS3 is public domain (CC0 waiver) per CHC; cite doi:10.15780/G2JQ0P and Funk et al. 2026, Sci Data 13:718.
- Access with no new dependency: h5py + requests, reading only the field's chunks of the yearly netCDF-4 files
  (about 2.1 GB, about 1,900 requests, 3-6 hours unattended; the server throttles with HTTP 429). Test read:
  2020-07-15 = 5.31 mm at the field's cell; **2020 total 1,418 mm against GPM's 3,120 mm** (one year only).
- **APHRODITE is not simple**: an ID and password by e-mail; 'shall not be redistributed ... through the Internet'
  (clashes with the public repository and site); APHRO_MA V1901 ends in 2015. Not used.

### Upgrade item 1, DHM normals and the rain comparison (2026-11-13)
- A research sub-agent transcribed DHM's 1991-2020 normals (config/dhm_normals_1991_2020.csv, every number with its
  document and page). Claude checked the Kathmandu Airport row against the PDF image (exact match, 1,502 mm).
- `pipeline/checks/rain_check.py` (monthly climatology over complete months; Pettitt test) with 4 tests; three of
  Claude's first test expectations were wrong (a row DHM leaves blank; a test series that covered March; Pettitt's
  p for a 10/10 step is 0.0016) and were corrected after checking by hand. `scripts/run_rain_check.py` writes
  `data/checks/demo/rain_check_b.json`.
- Two corrections tested on held-out years against the airport station, **neither applied**: scale to Bhaktapur's
  normals (helps 2017-2025, harms 2001-2016) or scale 2017-2025 back to GPM's own 2001-2016 months (best on held-out
  months; flattens any real change across 2017). Owner's decision.

### Soil kept: sources (research sub-agent, 2026-11-13; Claude checked the rows in the saved texts)
- Crop C factors: Panagos et al. 2015b as reprinted in Benavidez et al. 2018 (HESS 22:6059, Table 9): rice 0.15,
  wheat 0.2, maize 0.38, potatoes 0.34, dried pulses 0.32; finger millet 0.2 (Borrelli et al. 2017, Supp. Table 2,
  cereal grains). Bare 1.0 by definition (Wischmeier & Smith 1978, AH 537). Panagos 2015 itself was not opened
  (paywalled); no Nepal or Himalaya C table found.
- Daily erosivity: R_day = 0.2686[1 + 0.5412 cos(pi j/6 - 7 pi/6)] P_day^1.7265 (Xie et al., in Yin et al. 2015,
  HESS 19:4113, Table 3). Sensitivity exponent 1.81 (Richardson et al. 1983, via Sepaskhah & Panahi 2007).
- With soil kept, rice then wheat (sown 15 Jun and 15 Oct) beats the current placeholder plan on all five scores.


## 2026-11-13 (Friday, midday): the owner's decisions 1-6 applied, build step 7 exported (Claude Opus 5.5 via Claude Code, session 2f8edafe)

What SI (Claude) generated, and what a person must still review:
- **Rain fix (decision 1)**: `pipeline/twin/inputs.py` (`complete_month_totals`, `break_factors`, `apply_break_correction`,
  `with_rain`), `pipeline/fetch/weather.py` `correct_gpm_break`, `pipeline/checks/rain_check.py`
  (`holdout_break_correction`, `step_ratio`), the `--rain uncorrected` switch in the three runners, tests
  (`tests/test_rain_break.py`, new cases in `tests/test_weather.py`, `tests/test_rain_check.py`). Two of Claude's
  first test expectations were wrong (February in a leap year changes the factor to 28.5/56) and were corrected by
  hand-checking. Claude's readings, written into rules.yaml before the Late check was read: only IMERG Final days are
  scaled and set the factors (Oct-Dec 2025 come from Late), and only the demo field is corrected. With Final-only
  factors October's factor is 0.80 (0.56 when the Late October 2025 storm was included) and November's 2.40 (1.79):
  November rests on a few mm.
- **Downloads (decisions 2-3)**: `pipeline/fetch/gpm_late.py` (IMERG Late 2014-2019, separate cache) and
  `pipeline/fetch/chirps.py` with `pipeline/fetch/rangefile.py` (HTTP range reads of the yearly CHIRPS files, a
  deadline of Saturday 08:00), `tests/test_chirps.py`.
- **Plans (decisions 4-5)**: `score.choose_three`, `pick_safest`, `same_crops`; `scripts/run_plans.py` exports each
  shown plan's replay. **After the first run** Claude added "the three plans grow different crops": the rule as
  fixed picked rice then wheat twice (rice sown 15 Jun and 1 Jun). Put to the owner, with the name question
  ("Safest in bad years" for rice then lentil, which is safer than today but not than rice then wheat).
- **Words**: `pipeline/plans/explain.py` (conditions and placeholders from the numbers; no free text at export), new
  template lines in `pipeline/words/tabs.json` (safest plan; rain fix in the unknown tab and on the method page;
  wheat needs watering; lentil as the legume option; the two rice lines rewritten for the paddy rule of REVIEW_NOTES
  H1, which the old lines no longer matched), registry entries, and the Nepali name and lines. **Every new English line
  needs the owner's review** (pipeline/words/PREVIEW.md); **every Nepali line needs a native speaker's review**.
- **Export**: `build_field_json` (`replay_rows`, `with_uncorrected`, `apply_plans`, `sources_block`,
  `rain_correction_block`, `stated_choices`), schema keys `uncorrected_rain`, `score_uncorrected_rain`,
  `method.rain_correction`, `method.choices`, mock and tests.
- **Decision 6**: every TODO-CONFIRM in rules.yaml, METHOD_NOTES and VALIDATION now reads "Claude's choice,
  owner-approved 2026-11-13"; they are listed on the method page (`method.choices`, built from rules.yaml).

## 2026-11-13 (Friday, afternoon): independent review, fixes and accuracy tests (Claude Fable 5.2 via Claude Code, session 9f5addf3)

An AI review asked for by the owner, in four phases. The session stopped once after Phase 1 (its usage limit) and
went on later the same afternoon. Everything below was generated by SI; **no person has reviewed it yet.**

**Phase 1, review (no edits).** One main session plus ten read-only sub-reviewers it started (twin physics; events
and diary numbers; weather and corrections; the rain break; satellite greenness; plans; static data and the
switch-off trace; export and site; security, licences and probe; documents). Each recomputed its slice with its own
code from the primary sources and compared with the project's functions and stored outputs; the main session re-ran
the main findings itself and wrote `REVIEW_2.md`. 305 project file hashes were identical before and after.

**Phase 2, fixes (tests first; nothing that changes a method, rule, threshold or result).**
- `pipeline/export/build_field_json.py`: `stated_choices` reads an approval however it is capitalised and lists a rule
  "added by Claude" (5 approved choices had been exported as unapproved; `plans.third_plan_rule` was missing);
  `sources_block` says what MODIS and SoilGrids are really used for and gives the soil cell's distance from its card.
- `pipeline/diary/trends.py`, `scripts/run_diary.py`: `pinned_years` counts from each year's own 15 May (a leap-year
  slip had stored 19 and 21 instead of 21 and 22); `without_years` and `rules.yaml trends.hot_day_caveat` (a label):
  the hot-day trend is also given without POWER's faulty 2001-2003.
- `pipeline/export/validate.py`: a plan without a replay and replay years that do not run year by year are refused;
  `--final` (the freeze check). `pipeline/export/mock.py`: will not overwrite a file holding real results.
- `pipeline/fetch/weather.py`: the cross-source flags are written into the GPM card too. `scripts/run_season.py`: a
  stale soil label.
- Rerun in place: the diary step (both rain versions), the weather build (table identical, cards updated), the
  export. `demo.json` changed in two `sources` rows and in `method.choices` only; no number changed.
- Documents: VALIDATION.md (about 30 rows corrected or added, new totals), DATA_AUDIT.md (stale lines, sections 4
  and 5 rewritten, 1.16 and 1.17 added), METHOD_NOTES.md (items corrected, 35-41 added), README.md, CLAUDE.md
  (factual lines only), CONTRACT_CHANGES.md, CREDITS.md.

**Phase 3, accuracy and more data.**
- New code, tests first: `pipeline/fetch/smap.py` and `scripts/run_smap_check.py` (SMAP cleaned; L4 monthly anomalies
  against the twin's wetness); `pipeline/checks/rain_check.py` `ratio_to_gauges` and
  `scripts/run_dhm_bulletin_check.py` (the twin's 2025 rain against DHM's own gauges); `pipeline/fetch/gauge_evidence.py`
  (IMERG monthly gauge weight and GPCC station counts, fetched and carded, so the evidence for the 2017 break no
  longer rests on numbers read by hand). With all 297 months in hand the gauge weight before 2017 is 96-98%, not 96-97%: `rules.yaml
  gpm_series.break_evidence` and the method page were corrected (17 of 192 months are 98%). Data cards may now carry a
  `summary` (`pipeline/fetch/guards.py`, test first).
- Downloads: the eight SMAP L4 years already finished at AppEEARS (existing tasks; 16 MB); IMERG monthly subsets for
  2001-2025 (GES DISC OPeNDAP, the project's Earthdata login); two GPCC decade files (DWD open data, 45 MB); six DHM
  bulletins of 2025 (validation only, under `data/`, with a hand-transcribed table of 18 values, each re-read by the
  main session in the bulletin text). No new account, no new dependency.
- Runs in a private copy of the repository (nothing written to the project): the plan step under 13 perturbations
  (soil water, ET0, root depth, groundwater, four rain variants) and the station switched off; results in
  VALIDATION 4.4 and DATA_AUDIT section 4.
- Not done, and why: HLS EVI and NDMI for the paddy-flooding test (about 3,000 more windowed reads and a new rule
  for the rotation guess, which needs the owner's go; the monsoon half of the guess, rice, is already the robust
  half).

**Phase 4.** Feasibility and the ordered plan are at the end of `REVIEW_2.md`.

**For a person to review.** `REVIEW_2.md` (its questions for the owner first); the new English sentences inside
`sources` ("compared with HLS only; no number shown uses it"; "water the soil holds at field capacity and wilting
point (machine-learning map); nearest cell with values, 859 m from the field"); `rules.yaml trends.hot_day_caveat`;
every document edit listed above. No Nepali text and no farmer-facing tab or tip was changed by this session.

## 2026-11-13 (Friday, evening): the owner's 21 answers applied (Claude Fable 5.2 via Claude Code, session 9f5addf3)

Generated by SI in this session, after the owner answered REVIEW_2's questions. **No person has reviewed any of it yet.**

- **Pushes.** The owner's answer 1 ("commit and push the working tree now") and "commit and push after each finished
  step" were taken as the say-so for each push; the full suite passed and `scan_history.py` exited 0 before each.
- **Code, tests first:** the extended secret scanner (`scripts/scan_history.py`: new key shapes, the working tree, the
  website key by SHA-256 only); `pipeline/sections/grid.py` (10 m sections); `pipeline/export/build_words.py`
  (`site/data/words.json`); the `mock` list and "not ready yet" blocks (`build_field_json.not_ready_blocks`, schema,
  validator); one weather event per year (`pipeline/plans/events.py` `field_year_events`, `event_season`); the Late days
  scaled (`pipeline/fetch/weather.py`); tips floor, straw rule, gain range and the new "unknown" lines
  (`pipeline/plans/explain.py`, `scripts/run_plans.py` `gain_range`); every trend also for 2004-2025.
- **Rules written and committed before their first run** (`a8b9b45`; owner's answer 21): the event seasons and the
  calendar-year wettest day, the gain-range runs, the tips floor (5 days) and straw rule, the rain-level limit (1.25),
  the current-plan options. Each is marked "put to the owner" where the detail is SI's reading of the owner's answer.
- **New and changed texts, English and Nepali, all SI drafts for the owner's review (answer 15):**
  - Plan name: "Feed your soil" / "माटोलाई मलिलो बनाउने".
  - Why: "The ground is bare about {bare_days} days yearly." / "This plan grows crops {cover_days_gain} more days." /
    "This plan is here to feed your soil."
  - Evidence: "Drier than usual: {drought_years} of {year_count} years."
  - Benefits: "Harvest: about {gain_low} to {gain_high} more." / "Harvest: up to {gain_high} more, maybe none."
  - Unknown: "The soil numbers come from {soil_distance} m away." / "We don't know how deep roots reach here." / "So the
    harvest gain is a range." / "Our rain may still read too high."
  - Screen 3: "The ground is bare about {bare_days} days yearly." / "This trend is clear for the wide area." / "It does
    not tell about your own well."
  - Screen 7: "A drier year than usual" / "A dry winter" / "A dry rainy season".
  - Their Nepali is in `pipeline/words/tabs.json` and `screens.json`, each marked "needs native-speaker review";
    `pipeline/words/PREVIEW.md` lists every text side by side.
- **Licence and notice texts** (LICENSE's last section, `config/dhm_normals_1991_2020.NOTICE.md`): SI drafts, not legal
  advice; for the owner's review.
- **`notes/ui_note.md`**: the note for the UI teammate.
- **Later the same evening.** The current-plan options (`pipeline/plans/options.py`, `current_options` in the export);
  the season detective as a "less sure" signal (`diary.months[].cover_sure`); field memory (`pipeline/ml/memory.py`,
  `scripts/run_memory.py`: a scikit-learn ridge regression, tested leave-one-year-out; it did not beat the physics twin
  and is not used; the result is exported on the method page). Rules for both SI pieces were committed before their
  first run (`dfb1d4f`). New texts for the owner's review, English and Nepali drafts: screen 3 "We think you grow
  {first_crop} first." / "Then {option_a} or {option_b}." / "Which one do you grow?" / "From space, both look the same." /
  "We are less sure about this month."; unknown tab "Your winter crop dates may differ from ours."; method page (field
  memory) "We tried teaching a computer this field's habits." / "It learned from {memory_seasons} seasons seen from
  space." / "We tested it on years it never saw." / "It did not beat our simple water count." / "So we left it out." /
  "It did better than our simple water count." / "We use it." / "It looks at greenness, not at the harvest."

## 2026-11-13 (Friday, 18:00): hosting moved to Vercel (Claude Fable 5.2 via Claude Code, session 9f5addf3)

- **Owner's decision:** the site is hosted on Vercel, connected to the repository, Root Directory `site/`, no build
  step, fully static (no Vercel functions, no environment variables), every fetch relative.
- **SI did:** removed `.github/workflows/pages.yml` and its test; wrote `scripts/check_site.py` (tests first,
  `tests/test_site_static.py`: 25 tests) which refuses paths that start at the domain root, environment-variable reads,
  calls to `api/`, and files that would make Vercel run functions or a build (`api/`, `middleware.*`, `package.json`,
  `.env*`, files that need compiling, a `vercel.json` with functions, env or build commands); updated CLAUDE.md
  ("Hosting", layout, judge path, the final-commit steps, the website key's restriction wording), README.md,
  notes/ui_note.md, REVIEW_2.md and CREDITS.md. The live address is a placeholder in all of them until the owner sends it.
- **For the owner to check:** the Vercel project's settings (Framework Preset "Other", Build and Install Command empty,
  no Environment Variables), which SI cannot see; that the production address opens without a Vercel login; and that
  the website's Firebase key, when step 10b is built, is restricted to the Vercel address, not the GitHub Pages one.
  After submission nothing may be pushed to the connected branch: every push redeploys the live site.


## 2026-11-13 (night): the field in small parts, build step 8 small version (Claude Opus 5.5 via Claude Code, parallel agent)

- **SI did (tests first):** rewrote `pipeline/sections/grid.py` (a four-corner field split by its own corners, any other
  outline by clipped cells; the default 10 m grid the export still draws is unchanged), wrote
  `pipeline/sections/attributes.py` (HLS pixel weights by area, the field's cloud rule by area, season peaks on the
  diary's smoothed curve, the sign test with Holm and the median's interval, TPI and the low-ground flag),
  `pipeline/sections/status.py` (status and wetness from the twin's state, FAO-56 eq. 84) and `scripts/run_sections.py`
  (writes `data/checks/demo/sections.json` only); tests in `tests/test_sections_grid.py`, `test_sections_attributes.py`,
  `test_sections_status.py`, each with worked numbers.
- **Rules first:** `rules.yaml` `sections` (grid size, the 'usually greener' test, its 0.05 'same' band, TPI radius
  500 m and -1 SD from Weiss 2001, NASADEM's ~7 m error, the Ks < 0.5 red cut) was written before any run on real
  data; another agent's rule commit `5dce176` (00:26:58) took the block in unchanged, before the first run (00:30).
- **Sources read by SI tonight:** the HLS v2.0 User Guide (April 2026), the NASADEM User Guide (January 2020) and
  Jenness's TPI documentation (2006), downloaded as PDFs and read as text; Weiss's poster link was dead (404); Conover
  1999 and Holm 1979 are cited from memory (standard results), not opened.
- **Result (VALIDATION 3.20, METHOD_NOTES 55-59):** 4 parts of about one HLS pixel; s3 'greener', s2 'less green', s1
  and s4 'same', all by tiny but steady winter differences; low ground 'can't tell' for every part; status grey until
  the twin's state exists.
- **For a person to review:** the draft 'unknown' lines (English, at most 8 words): "All parts share one soil and
  weather." / "Each part is one dot from space." / "Those dots do not match the parts." / "Greener can mean weeds or
  trees too." / "Height maps cannot find low spots here." / "The probe tells the parts apart." No Nepali drafted. Put
  to the owner: 30 m parts instead of CLAUDE.md's 10 m; the Ks < 0.5 cut; whether 'greener' needs a size floor
  (noticed after the run).
- **2026-11-14, morning, owner's decision on the size floor:** SI searched for a published HLS v2.0 NDVI noise figure
  (HLS User Guide sec. 4.5: reflectance residuals only; Claverie et al. 2018: reflectance only; Zhou et al. 2026 abstract:
  no NDVI number; full text not reachable) and chose Ju et al. 2025's same-day vegetation-index difference, below 4.5%
  (abstract read through OpenAlex). Rule committed first (`e5b9aef`), tests first, rerun: every part 'about the same'.

## 2026-11-13 (night): twin upgrades 2a (FAO-56 bare soil) and 2c (rain-fed rice proposal) (Claude Opus 5.5 via Claude Code, parallel agent)

- **2a, written by SI:** `pipeline/twin/evaporation.py` (FAO-56 Chapter 7 eqs. 71-79, Table 19 REW, USDA texture class),
  the bare-soil path in `soil_water.run_bucket` and `season.simulate` (`bare_kc` as a setting dict), `--bare-soil` and
  `--out-dir` in `scripts/run_replay.py` and `run_plans.py`, tests first (`tests/test_evaporation.py`; additions to
  `test_twin_water.py`, `test_season.py`). Defaults unchanged: the default replay writes a byte-identical `replay.json`,
  and the old method recomputed reproduces `plans.json`.
- **Sources read by SI tonight:** FAO-56 Chapter 7 (fao.org page downloaded and read as text: eqs. 71-79, Table 19,
  Examples 31 and 35; Example 35's rows after day 2 disagree with themselves as printed, so only days 1-2 and day 6's
  start depletion are tested); SSSA Glossary of Soil Science Terms (2022), p. 115 (the texture classes on p. 116 were
  not opened; the class key follows the NRCS texture calculator from memory: TODO-VERIFY in rules.yaml).
- **Rule committed before its first run:** `5dce176` (`rules.yaml bare_soil`, `apply: false`). Readings put to the owner:
  rain wets the layer after the day's evaporation; the same SCS runoff for the layer; De at a spell's start =
  TEW x Dr / TAW; Ze 0.10 m and the REW midpoint.
- **Result (VALIDATION 2.5 and 3.21, METHOD_NOTES 18, 65-68):** FAO-56's examples reproduced; on the demo field bare
  ground loses about twice as much water as with Kc 0.3 (showers on bare ground go back to the air), so the next crop
  starts drier: current plan 72.3 -> 68.6, the same three rotations chosen. Not tuned. For a person to review: the
  readings above, and that six other callers (diary, memory, SMAP check, future, twin_now, season test) pass
  `bare_soil.kc` themselves and will not follow the switch until changed.
- **2c (4c in the owner's queue), a proposal, not applied:** `season.paddy_transplant` and `paddy_outcome`,
  `--paddy-rainfed proposal` in both scripts, tests first; rule `rules.yaml paddy_rainfed` committed before the what-if
  (`abbe701`). A research sub-agent (Claude) opened the sources; quotes as it reported them: Bouman et al. 2007 (IWMI
  ch. 14, Box 14.2) "as low as 100-150 mm ... when the time lag between soaking and transplanting is only a few days";
  Balwinder-Singh et al. 2019 "at least 21 days old", "surface water ponding exceeded 50 mm", no crop "if these
  conditions were not met by 15 August"; Han et al. 2024 "threshold ponding water depth (30 mm) was reached by
  rainfall"; Chaulagain et al. 2022 (Khumaltar) "merely a few filled grains per panicle due to a lower temperature and
  less soil moisture in October"; FAO Training Manual 4 "the amount of water needed to saturate the root zone is 200
  mm". Bouman et al. 2007 in Advances in Agronomy and De Datta 1981 were not reached. `config/known_events.yaml` was
  read only after the commit. Owner's note: `notes/proposal_2c_rainfed_rice.md` (recommendation: not as a harvest rule).
- **4a (owner's queue, 2026-11-14), switched off:** `season.plan_from_seasons`, `--season-dates hls` in
  `run_replay.py`, tests first; rule `rules.yaml season_dates` committed before the run (`7538f10`). REVIEW_2's 53 %
  agreement had no kept script; SI rebuilt the measure from REVIEW_2's description (it reproduces 97 % for rice and
  47/42/11 % for potato days against REVIEW_2's 45/44/11 %, and 54.5 % against 53 % overall). VALIDATION 4.2c,
  METHOD_NOTES 69b (70 was taken by another agent).
- **Later the same night (coordinator's items 1, 4b, 4d):** `run_diary.py`, `run_memory.py`, `run_smap_check.py` and
  `run_season.py` now take the bare-soil method from `evaporation.bare_soil_setting` (unchanged while apply is false; a
  guard test in `tests/test_evaporation.py`). A third rain version, `with_rain(..., 'dhm')` in `pipeline/twin/inputs.py`
  with `tests/test_rain_dhm.py` first, rule `gpm_series.dhm_scaling` committed before the run (`cc369a4`); `--rain dhm` in
  `run_replay.py` and `run_plans.py` (`data/checks/demo/rain_dhm/`); side by side in `data/checks/demo/rain_versions.json`
  (VALIDATION 3.9d). Soil range with the neighbourhood median profile, rule committed first (`e8fce4f`), offline from the
  cached WCS maps (`data/checks/demo/soil_range/`, VALIDATION 4.4c). No new sources.
- **2026-11-14, 4a and 4c switched on (owner's decisions of 2026-11-14, on the coordinator's instruction):** SI wrote
  `pipeline/plans/twin_options.py` (the three switches applied the same way by every runner; tests first,
  `tests/test_twin_options.py`, including plan_run = evaluate with both on) and wired it into `run_replay.py`,
  `run_plans.py`, `run_diary.py` (soil words), `run_memory.py`, `run_smap_check.py`, `run_twin_now.py`,
  `run_validation_checks.py`, `pipeline/future/runs.py` and `run_future.py`. Clarifications (the farmer's plans, suggested
  plans on the calendar, the order of 4a and 4c) and both switches committed before any run (`e89d3e1`), after the
  integrator's 09:38 rerun, whose outputs were kept as the 'before'. Then the whole demo pipeline was rerun (not the
  export). Result: the rule catches neither the 2009 nor the 2015 monsoon drought (VALIDATION 4.1); the independent checks
  got weaker (SMAP, GLDAS ET, FAOSTAT rice and potato); twin-satellite agreement is no longer independent (VALIDATION 4.2c,
  4.2). Nothing tuned. For a person to review: the order of 4a and 4c, and that the cover-the-gap pick moved on a tie
  (METHOD_NOTES 69, 69b).
- **2026-11-14 afternoon, owner's items 3 and 4 (both behind switches that stay off):** SI read FAO Training Manuals 3
  and 4 (sec. 4.4: SAT 200 mm; PERC 2/4 heavy clay, 8 sandy, 5/6 average mm/day; WL 100 mm) and FAO Soils Bulletin 55
  (Chin and Lee 1961 by clay content) as text from fao.org, wrote rules.yaml `paddy_losses` (committed `84eefb9` before
  the what-if), the loss in `soil_water.step`/`run_bucket`, `season.simulate` and `twin_options`, tests first
  (`tests/test_paddy_losses.py`), and ran the what-if in memory (`data/checks/demo/paddy_losses/whatif.json`). A research
  sub-agent (Claude) opened the field-capacity sources (CREDITS); SI re-read the FAO-56 and Soils Bulletin 79 lines.
  SI wrote `notes/FIELD_CAPACITY_PROTOCOL.md`, `notes/field_capacity_template.csv`, rules.yaml `field_capacity_measured`
  (`e15dff6`), `pipeline/twin/field_capacity.py`, `pipeline/fetch/field_visit.py`, `twin_options.soil_versions`, tests
  first (`tests/test_field_capacity.py`, a fixture file in a temporary folder). For a person to review: reading 'this
  soil type' as FAO's average 5 mm/day, the 'wet day' reading, FAO's 200 mm replacing Bouman's 150 mm, and the
  protocol's plain words (a team member should try it once before the real test).
- **For a person to review:** every reading marked "put to the owner" in the five rule blocks; the 2c and 4b recommendations.

## 2026-11-13 (night): build step 10, the probe updates the twin (Claude Opus 5.5 via Claude Code, parallel agent)

Written between 00:20 and about 03:00 on 14 November (Nepal time), after a usage-limit pause in which nothing had been written.
At about 01:30 the owner's new probe brief replaced the cup and bridge parts; the Kalman update and the twin's state were kept.

- **What SI made:** `pipeline/twin/kalman.py` (predict, update, sure, the aged prior, P0, anomalies, the SMAP fit, the state
  on the as-of day), `pipeline/fetch/now.py` (near-real-time POWER and IMERG Late, built by weather.py's own pieces; the
  rebuilt 2001-2025 history equals `weather.parquet`), `scripts/run_twin_now.py` (`data/clean/demo/twin_state.json`; the
  bare-soil setting passed as `scripts/run_plans.py` passes it), and for the owner's probe brief `robot/settle.py` (settle 20
  lines, measure 10), `robot/fake_probe.py` scenarios (settling ramp, jumpy, stuck at 100, wiring lost), `robot/calibrate.py`
  (water %, band, drier / wetter, R in twin units), `robot/bench.py` and `scripts/run_probe_bench.py` (the four proofs,
  settling time, `config/probe_calibration.yaml` only from real cups), `robot/bridge.py` (walk the parts, `live.json` only at
  state changes, every raw line logged, the pulled cable: REVIEW_2 L7), `scripts/build_probe_log.py` and
  `pipeline/export/probe_log_schema.json` (a new contract file), `robot/CUPS_PROTOCOL.md` (the team's bench steps).
  Tests first, each with worked numbers: `tests/test_kalman.py`, `test_settle.py`, `test_calibrate.py`, `test_bench.py`,
  `test_probe_bridge.py` (extended), `test_probe_log.py`, `test_twin_now.py`. A bug found by the rehearsal (one part's ending
  closed the shared input stream) has a test that fails on the old code.
- **Rules before runs:** `rules.yaml probe.*`, committed `6ca9bd1` and `9e144ea` (Kalman, as-of day, aging) and `32890ca`
  (the owner's probe brief: settle and measure, off scale, temperature spread, bands, the bench rules; it replaced the cup rules
  of `6ca9bd1`, which had never run), each before its first run.
- **Downloads** (no new account or dependency; under the git-ignored `data/`): 316 IMERG Late V07 daily box subsets for
  2026 and one NASA POWER request; about 10 minutes, 9.9 MB.
- **Results:** the twin as of 3 Nov 2026 (POWER's sunshine is the last input): potato day 5, wetness 95.7 %; P0 181.5;
  SMAP r 0.622 over 3,929 days; prior_var 111.3, sure_prior 0.22; Q 4.70 a day. Rehearsals with the fake probe and made-up
  cups (scratch and `data/checks/probe/bench_fixture.json`, labelled REHEARSAL, never exported): settling median 18 s, at most
  26 s on the made-up ramp; the made-up ice cup reads 0.6 C after 40 s and fails the ice check.
- **Sources:** none opened tonight. From memory: the variance of an even rounding error (step^2 / 12), the first-day growth
  of a first-order autoregressive error, 1 - r^2 as the unexplained share of a straight-line fit, the particle density 2.65
  g/cm3 of mineral soil, and the DS18B20's +/-0.5 C accuracy (its datasheet was not opened). What the temperature sensor is
  comes from the sketch alone.
- **For a person to review:** every `probe.*` rule marked "Claude's choice" (P0 window, the 1 - r^2 prior, Q, the aging cap,
  the 1/12 floor, the top 10 cm for the band, no band on bare ground, 'about the same' within 3 points, the curve rule's 1.0
  point and 5 cups, the 4-cup minimum, the note words, staleness after 10 s); `robot/CUPS_PROTOCOL.md` (amounts: 300 g of soil,
  0-125 g of water in 250 ml cups); the new `live.json` fields and `probe_log_schema.json`. The owner confirms where the
  temperature sensor sits (soil or air).

## 2026-11-13 (night): a second monsoon-onset measure, the anomalous accumulation (Claude Opus 5.5 via Claude Code, parallel agent)

Ran from 2026-11-13 evening to 2026-11-14 about 01:30, paused by an account usage limit.
- **Rules before runs:** `rules.yaml onset_accumulation` was committed before the first run on real data (`636a5c8`, that file
  only). It holds the definition, the two variants and which one feeds `shift_days` (own-year mean, corrected rain), the
  four-part trust test, the sanity window and DHM's yearly dates. The kept rule `monsoon_onset` is untouched. No variant was
  chosen or changed after a trend was seen. One addition after the first run, for reporting only: the Spearman p-value
  beside the DHM correlation.
- **Code (tests first):** `pipeline/diary/onset_accumulation.py`, `tests/test_onset_accumulation.py` (34 tests with hand-worked
  series: one season, two variants on a wet and a dry year, scaling, two rainy seasons, flat bottom, no rain, rain all year,
  edges, missing days, the trust test, shift_days, agreement, word length), `scripts/run_onset_check.py` ->
  `data/checks/demo/onset_accumulation.json`.
- **Sources opened:** Noska & Misra 2016 (authors' PDF, pp. 4547-4554: eqs. 1-2, the onset definition). DHM's Monsoon
  Onset and Withdrawal date information (PDF: earliest 31 May 1996, latest 27 June 1982, Table 1 for 1968-2024).
  **Not opened:** Liebmann & Marengo 2001 and Liebmann et al. 2007 and 2012 (journals.ametsoc.org returned 403; Columbia and
  Reading copies refused or blocked). They are cited only as the method's origin.
- **Result:** the measure is not trusted, so `shift_days` stays null (VALIDATION 3.22, 4.1e; METHOD_NOTES 70-74).
  - The own-year variant fails sanity (median 27 May).
  - The paper's variant passes sanity (2 June) but its trend flips sign with the rain version (+12.0 against -17.0 days).
  - The paper's variant follows DHM's yearly dates (Spearman 0.57); the kept rule does not (-0.09).
- **For a person to review:** every `onset_accumulation` choice marked "put to the owner": the tie and flat-year
  readings, the own-year variant and its feeding `shift_days`, the 2-29 June window and the trust test. Also the proposed
  contract fields `diary.shift_days_low`, `diary.shift_days_high` and `diary.shift_note`, and the English words in
  `export_proposal`.
- **The owner's answer (2026-11-14): "fix the answer, not the method".** No further onset definition was tried.
  - **Rule before run:** `rules.yaml monsoon_onset_dhm` (`09c1327`). It covers the DHM record, `shift_days`, the start
    window, late after 20 June, the cross-check agreement test, the words rule and the approximate BS dates.
  - **The DHM table:** Table 1, 1968-2024, now in `config/dhm_onset_dates.csv` with a NOTICE. Both files went into the
    integrator's commit `345d4b1` from the index, before the run.
  - **Code (tests first):** `pipeline/diary/onset_dhm.py`, `tests/test_onset_dhm.py` (24 tests), `scripts/run_onset_dhm.py`
    -> `data/checks/demo/onset_dhm.json`.
  - **Result:** DHM shows no clear shift: -2.2 days (-11.5 to +7.7). The usual start is 10-16 June. Only 2009 came after
    20 June (1 of 24 years). Both cross-checks pass the declared test, but weakly: wide ranges that lean later. CHIRPS's
    onset by this method has median 17 May and does not follow DHM's years.
  - **SI wrote** the English and Nepali drafts (diary, "Next 3 months", "How we know"). Every Nepali line needs a
    native speaker's review, and its BS dates are approximate.

## 2026-11-13 (night): Local Impact, the area map and sample fields (Claude Opus 5.5 via Claude Code, parallel agent)

- **Rules first:** `config/rules.yaml` `area_map` and `sample_fields`, committed alone before any run (`cb85cc8`): the
  cropland rule on the 30 m grid, the years, the 60-day line, the range (bare threshold +/- 0.05; WorldCover's published
  accuracy as a worst-case bound), the field check, the classes and colours, and the quadrant spread rule.
- **SI did (tests first, `tests/test_area_map.py`, `tests/test_sample_fields.py`):** `pipeline/area/` (per-pixel versions of
  the diary's own steps, bit for bit the same as `greenness.daily_series`; stats; Web Mercator PNG layers; the spread
  rule), `scripts/run_area_map.py`, `scripts/pick_sample_fields.py`. Opened the WorldCover v200 Product Validation Report
  and read the cropland accuracies from its Tables 2 and A2.4. Checked that the generalised `placeholder.py` still gives
  the demo's recorded search (1,591 passing, the same top three).
- **Results:** VALIDATION 3.23 (PASS), METHOD_NOTES 80-84, DATA_AUDIT 1.20; `data/checks/demo/area_map.json`,
  `sample_fields.json`, `site/data/area/`, `config/fields/sample_1.yaml` to `sample_4.yaml`.
- **For a person to review:** the legend and number lines in `site/data/area/demo.json`. English is SI's draft (at most
  8 words a line). **The Nepali is SI's draft and needs a native speaker's review.** The four sample squares have not been
  looked at on imagery.

## 2026-11-13 (night): independent checks of the twin with unused data, ECOSTRESS, HLS, FAOSTAT and GLDAS (Claude Opus 5.5 via Claude Code, parallel agent)

- **Asked:** owner's group 3a-3c (ECOSTRESS ESI against the twin's crop stress by season; the twin against HLS peak
  greenness, VALIDATION 4.2; FAOSTAT ups and downs, 4.3) and, added by the owner on 2026-11-14 via the integrator, GLDAS
  as one more check of the twin's soil water and evapotranspiration. Checks only; nothing exported.
- **Rules before runs:** every design (statistic, seasons, years, bootstrap, minimums, the threshold for "holds up") was
  written into rules.yaml `validation_checks` and committed (`fe3223a`) before any check was run. Only data availability
  (ECOSTRESS overpass counts at the field pixel, FAOSTAT items, GLDAS variables) was looked at first.
- **SI did (tests first: `tests/test_gldas.py`, `test_corr_ci.py`, `test_ecostress.py`, `test_validation_checks.py`):**
  `pipeline/fetch/gldas.py` (GES DISC's own OPeNDAP is retired, "410"; Earthdata Cloud OPeNDAP subsets; a month guard was
  added after the server answered 3 of 300 parallel requests with another month's granule), `pipeline/fetch/ecostress.py`
  (the five traps of DATA_AUDIT 1.8), `pipeline/checks/corr_ci.py`, `ecostress_check.py`, `twin_vs_greenness.py`,
  `faostat_check.py`, `gldas_check.py`, `scripts/run_validation_checks.py` (reruns the twin with run_replay's and
  run_plans' own helpers and stops unless it reproduces the stored replay and plans). Two citations for the LST hard
  limit checked by web search (Scambos et al. 2018 confirmed with its DOI; Mildrexler et al. 2011's DOI could not be
  confirmed, so it is cited without one).
- **Results:** VALIDATION 4.2 (monsoon not testable; winter potato rho 0.47 [-0.19, 0.84], not shown; rice-then-wheat
  0.71 [0.24, 0.94], secondary), 4.2d (GLDAS: soil 0.34 and ET 0.33, below the 0.3 lower-bound bar; ET0 0.74 holds; GLDAS's
  rain agrees with the corrected rain, 0.70, not the published, 0.40), 4.2e (ECOSTRESS: not testable, 4 qualifying
  seasons per slot; no diary line), 4.3 (wheat holds up, 0.55 [0.15, 0.80]; potato does not; rice not testable).
  DATA_AUDIT 1.8 and 1.21, METHOD_NOTES 75-79.
- **For a person to review:** the pre-declared bars (minimum seasons and overpasses, the degenerate rule, Cohen's 0.3 for
  the monthly checks), the "best quality only" ECOSTRESS rule, and FAOSTAT's year convention (TODO-VERIFY).

## 2026-11-13 (night): the 2040 outlook from NEX-GDDP-CMIP6, build step 9 (Claude Opus 5.5 via Claude Code, parallel agent)

- **What SI wrote:** `pipeline/fetch/nexgddp.py` (THREDDS point fetch with the data guards, card, cache by cell),
  `pipeline/future/deltas.py` (monthly change, apply to the observed weather, ET0 rebuilt with relative humidity held),
  `pipeline/future/runs.py` (the core of `run_plans.evaluate`, including the bare-soil switch), `scripts/run_future.py`;
  tests first in `tests/test_nexgddp.py` and `tests/test_future.py` (worked numbers: the server's own grid point for
  the field, unit conversions, a 3-month rain window by hand, FAO-56 Table 2.3 vapour pressures, equality with
  `run_plans.evaluate` with the bare-soil switch off and on). The `rules.yaml` `future` block was written and committed
  before the first download (`578b8a6`); the plausibility check before the first change was computed (`90161de`).
- **Research sub-agent (web, 2026-11-14):** verified Thrasher et al. 2022 (doi:10.1038/s41597-022-01393-4), the
  dataset DOI 10.7917/OFSG3345, the CMIP6 Terms of Use 6.2, Held & Soden 2006 and Byrne & O'Gorman 2016 (quotes in
  CREDITS.md), and found the comparison range (World Bank CCKP CMIP6 0.25 deg, Nepal, 2020-2039 vs 1995-2014; DHM
  2024 for context). The humidity rule's source text was corrected after the paper was opened ("falls a little" ->
  "decrease substantially over land"); its value did not change.
- **Ran:** download started 00:24 Nepal time in the background (34 models, seeded order, about 6 minutes each); outlook
  on the first 5 complete models (01:00): plausibility PASS (VALIDATION 4.7); DATA_AUDIT 1.9, METHOD_NOTES 50-54,
  CREDITS rows.
- **For a person to review:** relative humidity held, the 3-month rain window, leaving out GFDL-CM4_gr2, MIROC-ES2L
  refused for tasmin files without units, the licence notes (CC-BY-SA 4.0 on some variables), and the proposed words
  for the 2040 screen. No farmer-facing text was exported.

## 2026-11-13 (night): the field on another continent, build step 11 first part (Claude Opus 5.5 via Claude Code, parallel agent)

- **Chose the field abroad** (Claude's choice, METHOD_NOTES 85): Ambohidratrimo, Madagascar highlands (FAO Crop Calendar MG
  aez 004: rainy-season rice, dry-season potato or wheat). Survey of 12 candidate points in Madagascar, Kenya and Ethiopia
  (and Guatemala's calendar, which has no sowing windows): FAO calendars read from the public JSON API, HLS granule counts and
  MGRS tiles from CMR, WorldCover class shares, GHCN-Daily coverage by year. Survey scripts in the session scratchpad only.
- **Picked the 60 m square** by the demo's rule with the zone's own seasons (METHOD_NOTES 86): candidate 1, the rule's first
  rank, picked without imagery. Its NDVI shows no bare dry-season trough, so it may not be a rice field: **for a person: check
  it on satellite imagery** (candidates 2 and 3 need no new download).
- **Wrote and committed a rule before any data of the field existed**: `gpm_series.break_test` (`6d2919c`), the thresholds
  Claude's choices with reasons (20-point gauge-weight fall, Pettitt p < 0.05, one-year window). Checked that it classifies
  the demo's evidence as a break (it does: 2017). Then ran it on the field abroad (VALIDATION 3.24).
- **Generalised the fetch modules, the rain check and the driver** (METHOD_NOTES 87-89; `tests/test_field_abroad.py`, worked
  numbers in every test): placeholder seasons from config, UTC-day labels from `utc_offset`, FAOSTAT country and crops,
  CHIRPS field cell at build time, GRACE and GPCC global files reused, correction A only with a `correction_label`, HLS
  `--since`, a GPM bug (Late search with from > to for a range ending before the last Final day), `scripts/fetch_field.py`.
  The demo's `rain_check_b.json` is byte-identical before and after.
- **A research sub-agent (Explore)** listed the Nepal-specific constants in the diary, plans, events, onset, words and export
  (input for REVIEW_2 H6); Claude spot-checked five of its line numbers (all right). Nothing was changed from it tonight.
- **For a person to review:** the field and square choice; the break-test thresholds; the config's `placeholder_seasons`
  months read from the FAO windows.

## 2026-11-13 (night): draft translations (Claude Opus 5.5 via Claude Code, parallel agent)

- **What SI did (tests first):** machine-translated every text in `pipeline/words/screens.json`, `glossary.json` and
  `crop_explainers.json` (269 texts) from the English into Hindi (hi), Bengali (bn), Spanish (es), French (fr) and Swahili
  (sw): `pipeline/words/drafts/<lang>.json`, one entry per English text node, recording the English it translates.
  `pipeline/export/build_words.py` adds each draft text beside "en" and "ne" in its node of `site/data/words.json` (English
  and Nepali unchanged) and a `languages` list (Nepali first; each draft with `draft: true`, status "machine-translated (SI),
  needs native-speaker review", and a label "Draft translation" in that language and in English). Tests in
  `tests/test_words_export.py`: same keys as the English and not stale, same placeholders and digits, eight-word screen
  sentences, one-sentence glossary meanings, Gregorian months, the flag and label, every published node carries every draft.
- **Kept in English on purpose:** the 21 verbatim source quotations of the crop explainers (18 from FAO) and the glossary's
  `basis` notes. A translation would be an adaptation of a licensed text (e.g. CC BY-NC-SA 3.0 IGO); each draft entry
  carries its quote verbatim, marked `lang: en, translated: false`, with its source.
- **Choices a reviewer should check:** ASCII digits in every draft (Bengali readers may prefer ০-৯); Bengali uses পানি
  (Bangladesh) not জল; Spanish uses usted and Latin American farm words (papa, computadora); French uses vous and no-break
  spaces before ? ! : ;; finger millet is रागी / মারুয়া / mijo africano / éleusine / ulezi; Swahili keeps "buckwheat" (no
  common word); the months note says "Nepali months don't line up exactly with these" in es, fr and sw, where "English
  months" means nothing; a few Hindi lines are verbless to stay within eight words.
- **Not translated (out of scope):** each plan's tabs and tips in `site/data/fields/demo.json` (English and Nepali only).
- **For a person to review:** every draft text, by a native speaker of each language. No draft has been reviewed.

## 2026-11-14: the data story, report card and inventories (Claude Opus 5.5 via Claude Code, parallel agent)

- **What SI did (tests first):** `tests/test_story.py` (33 tests), then `pipeline/export/story_schema.json` and
  `pipeline/export/build_story.py`, which writes `site/data/story.json` (17 charts, about 80 KB) for the site's "How we
  know" page from finished outputs only: the 2017 rain-gauge loss (IMERG gauge weight, GPCC station counts, GPM against
  CHIRPS, GPCC and DHM's Bhaktapur normal, the corrected rain), the field's seasons from HLS with the "less sure" months,
  the model against the written flood and drought records, DHM's 2025 gauges (ratios only), the other checks (SMAP, GLDAS,
  HLS, FAOSTAT, ECOSTRESS) as correlations with their ranges, the GRACE trend (labelled regional), the probe's bench test
  (written as "not ready yet": only the REHEARSAL fixture exists, and the builder refuses it), the area map (a pointer to
  `site/data/area/demo.json`), the 2040 outlook beside today's harvest, and how the computer helped (three season
  methods, field memory not kept, the review state of the SI-drafted words). A slot for the farmer's best and worst years
  says "coming" with no data. Every number in a caption is computed from the files, so the page follows the integrator's
  reruns; it was rebuilt twice this morning while `demo.json` and `words.json` changed under it.
- **Accuracy report card** (owner's item 5e): twelve lines (floods and dry years split), each with high, medium or low,
  plain reasons and the VALIDATION rows behind it; in `story.json` and as a new VALIDATION section. The rules for the
  three words are METHOD_NOTES 98, fixed before the first build. The Totals line of VALIDATION was recounted.
- **Satellite inventory and the challenge's resource list:** DATA_AUDIT sections 7 and 8, and `satellites` / `resources`
  in `story.json`. FAO GAEZ is "linked as a reference, data not used" (owner). ERA5 is marked not used, with the note that
  it reaches us only inside CHIRPS v3 `rnl`'s day split.
- **Sentinel-1 assessment** (DATA_AUDIT 8.1): ASF's search API (metadata, no login, nothing downloaded) lists 30 IW GRD
  scenes over the field in June-September 2025 and 826 in 2017-2025 (272 in the monsoons); HyP3's documentation gives 5
  credits and "an hour or two" per 30 m RTC job and a 267 MB VV GeoTIFF in its example. One season would be about 16 GB to
  download, eight times the 2 GB rule: a next step.
- **Nepali:** every Nepali caption, title and report-card line was drafted by SI and is marked "needs native-speaker review"
  (`ne_review` in `story.json`).
- **Please review (owner):** (1) the confidence words and their rules (METHOD_NOTES 98), above all "high" for the seasons
  and "medium" for rain, groundwater and the onset; (2) the event-matching rule of the timeline (METHOD_NOTES 97); (3) the
  Sentinel-1 verdict; (4) that the site's "How we know" page shows the report card with its weaknesses, not only the charts.

## 2026-11-14: the static site built from the teammate's design (Claude Opus 5.5 via Claude Code, parallel agent)

- **What SI did:** built `site/` (index.html, css/app.css, js/app.js, js/how.js, img/, vendor/leaflet/) as plain static
  files from our UI teammate's design in `design/` (the phone and web screens, their colours, fonts, images and motion).
  Every number and sentence on screen is read from `site/data/` (fields/demo.json, words.json, index.json, area/demo.json,
  story.json; probe_log.json and live.json only when they exist); nothing is simulated in the browser.
- **Words added (drafted by SI):** 107 screen texts in `pipeline/words/screens.json` (English, and Nepali marked "needs
  native-speaker review"), with machine translations into hi, bn, es, fr and sw in `pipeline/words/drafts/` (SI drafts,
  not reviewed); `site/data/words.json` and `pipeline/words/PREVIEW.md` regenerated. They replace the design's sample
  texts that the data cannot back: no drone photo (a map of the field's outline instead), no robot readings (a prototype
  soil stick carried by hand; Krishi Scout is the planned next step), no forecast ("what these months usually bring"),
  no market or income claims, the real 2001-2025 record instead of "20 years", the real three plans instead of lentil,
  mustard or leaving the field empty, and no "Listen" buttons.
- **Checked by SI:** `scripts/check_site.py --final` (0 problems), the word tests, screenshots at 360, 390 and 1440 px in
  headless Chrome (Nepali, English, French and Hindi), the soil screen with a rehearsal `live.json` from
  `robot.bridge --fake` and a test `probe_log.json`, both kept in the scratchpad, never in `site/data/`.
- **For a person to review:** every new Nepali text and every draft translation; the wording that replaces the design's
  claims; the designer's review of the look (see the hand-over report).

## 2026-11-14: the locked test set's reference data, DHM gauges and Bhaktapur yields (Claude Opus 5.5 via Claude Code, session 9f5addf3, sub-agent)

- **What SI did:** downloaded every DHM monthly "Preliminary Precipitation and Temperature Summary" online (38 issues, June
  2023 to July 2026; none exists before June 2023) and transcribed Annex 1 monthly rain for 10 valley gauges
  (`data/clean/demo/dhm_bulletin_months.csv`, 358 rows, 340 with a value; card `data/cards/demo/dhm_bulletin_months.json`);
  downloaded 7 editions of MoALD's "Statistical Information on Nepalese Agriculture" and transcribed Bhaktapur paddy,
  wheat and potato (`data/clean/demo/district_yields_bhaktapur.csv`, 21 rows, 2015/16 and 2018/19-2024/25; card
  `data/cards/demo/district_yields_bhaktapur.json`). Reference data only: no model output was opened or compared.
- **Checked by SI:** each DHM value's position in the Total column (pdftotext boxes); 44 DHM values and 12 SINA rows re-read
  on the page images. The checks found one parser error (Khumaltar July 2026: the Normal taken for an empty Total, now
  missing) and two DHM errors (December 2024's second annex page repeats October 2024's; Bhaktapur April 2026 printed 0.0).
- **For a person to review:** the station choice (valley and rim, 2.4-21.8 km), the notes "NOT USED" and "SUSPECT", and the
  missing SINA years (2001/02-2014/15, 2016/17, 2017/18, 2020/21).
- **Added the same day (second request):** each month's wettest day (`max_24h_mm`, `max_24h_date`, 340 values; each
  checked against the month's rainy-day counts and total, 35 re-read on the page images, no disagreement) in
  `dhm_bulletin_months.csv`; June-September totals from DHM's monsoon reports 2022-2025 for 10 valley gauges
  (`data/clean/demo/dhm_monsoon_years.csv`, 36 rows; card `data/cards/demo/dhm_monsoon_years.json`; 19 rows re-read on the
  images, 2023-2025 equal to the summed monthly bulletins); no station table was found for 2001-2021 (archived
  monitoring PDFs could not be downloaded: Internet Archive HTTP 429). The card of the 2025 check
  (`data/cards/demo/dhm_bulletins.json`, overwritten earlier the same day) was restored to its 2026-11-13 content.

## 2026-11-14: choosing the central rain version on gauges it never saw, and the year order (Claude Opus 5.5 via Claude Code, session 9f5addf3, sub-agent)

- **What SI did:** followed rules.yaml verification.rain_selection and year_order (committed eb3a57d before any score);
  wrote `pipeline/checks/rain_selection.py` with tests first (`tests/test_rain_selection.py`, worked numbers) and
  `scripts/run_rain_selection.py` (writes `data/checks/demo/rain_selection/`); fetched IMERG Late for January-July 2026
  into `data/rain2026/` with the existing fetcher (no code change, existing Earthdata login). The leave-one-gauge-out
  selection was run and saved before the 2026 file existed; the locked 2026 test was then run once. Nothing switched or
  exported.
- **SI's own reading of the rule:** the gauge-calibrated factors are fitted on every selection month with a gauge value,
  including months under 10 mm (not scored, but selection months). Fitted only on scored months, the corrected rain would
  have won instead (38 against 36 of 83); reported, not used.
- **For a person to review:** the winner (gauge-calibrated, 40 of 83 against corrected 38 of 83), the 2026 result, and
  January 2026 (IMERG Late 130 mm at the field's cell against 2-3 mm at the gauges).
