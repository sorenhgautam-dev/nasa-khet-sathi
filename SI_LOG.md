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
- 2026-11-11 19:23: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-11_192320` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-11 19:53: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-11_195346` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-11 20:23: owner-approved commit `d4d3e49` (53 files) pushed to private `github.com/sorenhgautam-dev/data-test-game`, branch `main` (CLAUDE.md rule 2 exception). Jury .docx excluded via .gitignore.
- 2026-11-11 22:19: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-11_221921` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-12 00:28: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-12_002813` (data/, .env*, .netrc, .venv excluded; checked)
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
- 2026-11-12 13:41: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-12_134141` (6.0 MB; data/, .env*, .netrc, .venv excluded; checked). 654 tests passed just before.
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
