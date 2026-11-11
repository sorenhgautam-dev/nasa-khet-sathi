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

### Backup runs

(appended by each step)
- 2026-11-11 19:23: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-11_192320` (data/, .env*, .netrc, .venv excluded; checked)
- 2026-11-11 19:53: `scripts/backup.sh` -> `/Users/paritoshbhattarai/khet-sathi-backups/khet-sathi_2026-11-11_195346` (data/, .env*, .netrc, .venv excluded; checked)
