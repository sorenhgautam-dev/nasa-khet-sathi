# CLAUDE.md: Khet Sathi data and model

## What this repo is

Khet Sathi ("field friend") is a phone website that helps smallholder farmers (Nepal first, anywhere
later) choose crop rotations for each section of their field, using NASA data. This repository holds
the **pipeline**: it downloads public data for a field, runs a small physics "twin" of the field's soil
water and crops through every season from 2001 to 2025 and through projected futures, scores crop
rotations, and exports **static JSON** that the website in `site/` reads.

There is **no backend**. Everything heavy is precomputed here; the site only reads small files.
Several fields are prepared in advance (the demo field in Nepal plus a few abroad). Each gets its own
JSON file and an index file lists them, so a judge anywhere can open the live site and explore a
prepared field while our laptop is switched off.

Context: NASA Space Apps 2026, challenge "Field Shift: Adapting Farms with NASA Data". The tool must
compare at least three rotations including the farmer's current one, explain each (why, evidence,
benefits, gaps, risks needing local review), and support, never replace, the farmer's judgment.

## Golden rules

1. **The output contract is sacred.** Every `site/data/fields/<id>.json` must validate against
   `pipeline/export/schema.json`. Never rename or remove a field without updating the schema and
   noting it in your step summary, because the UI is built against it.
2. **No git commits or pushes.** Never run `git commit` or `git push`; the owner commits everything
   once, just before the deadline. Keep `.gitignore` correct from step 1 so that final commit is safe.
   Earthdata credentials live in `~/.netrc`; any key lives in `.env` (gitignored).
   **Exception (owner, 2026-11-11):** commits and pushes to the private repository
   `github.com/sorenhgautam-dev/data-test-game` (branch `main`) are allowed when the owner asks for
   them, after the full test suite passes. Never push anywhere else, and never make that repository
   public; going public stays part of the owner's final-commit steps.
3. **Back up instead of committing.** Step 1 creates `scripts/backup.sh` (or `backup.ps1` on
   Windows), which copies the project, excluding `data/` and `.env`, to a folder outside the repository
   named with the date and time. Run it at the end of every step.
4. **`data/` is gitignored.** Raw downloads are large. Only small exports go in `site/data/`.
5. **Tests first for every equation.** Each physics function gets a pytest with a worked number,
   checked against a reference library or a published example, before anything uses it.
6. **Units in names:** `rain_mm`, `tmax_c`, `et0_mm`, `theta_m3m3`, `zr_m`, `soil_loss_t_ha`.
7. **Physics functions are pure.** File and network I/O only in `fetch/`, `export/` and `robot/`.
8. **Every number shown to farmers carries its source, resolution and years.** Label model-based data
   (NASA POWER, SMAP L4, the twin itself) as model-based.
9. **Keep it simple:** plain Python, pandas, numpy, xarray. Ask before adding a heavy dependency.
10. **Log as you go:** every dataset, library and use of SI (AI) goes into `CREDITS.md` the moment it is
   used. The submission requires it.
11. **Honest outputs only:** yield is a percentage of the field's potential, never tonnes; projections
    are ranges; every rotation is flagged for local review.
12. **Data guards.** Every fetch and clean step must: (a) print the raw variable's attributes (units,
    scale_factor, add_offset, _FillValue, valid_range) before converting; (b) assert sensible ranges
    after converting (rain 0 to 500 mm per day, temperature -30 to 50 C, NDVI -1 to 1, soil moisture
    0 to 0.6 m3/m3, relative humidity 0 to 100 percent); (c) fail loudly, never silently clip, when a
    value is out of range; (d) write data/cards/<field>/<dataset>.json recording product, version,
    variable, units in and out, scale factor, fill values removed, quality flags used, records dropped,
    date range, time zone and pixel count over the field; (e) carry the source and resolution into
    every exported number. **Decision D2 (2026-11-11):** where a product documents its own valid
    range, that range is the hard limit (for example SMAP L4 soil moisture 0 to 0.9 m3/m3), and values
    outside the ranges in (b) but inside the product's range are logged as warnings and counted in
    the card (`range_warnings`), not failures. Implemented in `pipeline/fetch/guards.py` (tested in
    `tests/test_guards.py`).
13. **No AI service is ever called from the public site.** All SI runs at build time on our laptops,
    or on the phone itself (see "SI components"). Any service key lives in `.env`.

## Repository layout

```
khet-sathi/
  CLAUDE.md
  MASTER_PROMPT.md      # the owner's brief and session prompts
  CREDITS.md            # every dataset, library and SI use
  SI_LOG.md             # what SI generated and what a person reviewed
  DATA_AUDIT.md         # per-dataset audit (products, units, fills, flags, coverage, switch-off)
  VALIDATION.md         # every check, by validation layer, with pass / fail / not yet possible
  requirements.txt
  config/
    fields/             # one YAML per prepared field (demo.yaml first): id, name, lat, lon, polygon,
                        # elevation_m, water_source, current_rotation
    crops.json          # crop library (see "Crop library")
    rules.yaml          # thresholds: bare NDVI, onset rule, frost, event definitions
  pipeline/
    fetch/              # guards.py, fields.py, credits.py, one module per source; each caches raw files in
                        # data/raw/<source>/<field>/ and writes data/clean/<field>/<source>.parquet
    twin/               # et0.py, crops.py, soil_water.py, runoff.py, yield_.py, erosion.py, frost.py, kalman.py
    diary/              # ndvi.py, bare_days.py, seasons.py, onset.py, trends.py, groundwater.py
    plans/              # generate.py, simulate.py, score.py, explain.py
    future/             # nexgddp.py, scenarios.py
    sections/           # grid.py: split the field polygon into sections, attach per-section attributes
    ml/                 # seasons.py (season detective classifier), memory.py (field memory)
    words/              # SI drafts of tabs, tips, glossary, Nepali text; text-to-speech at build time
    checks/             # validation-layer statistics (layer 3 "data sensible" and on)
    export/             # schema.json, index_schema.json, validate.py, mock.py, build_field_json.py,
                        # CONTRACT_CHANGES.md (what changed for the UI, and when)
  scripts/              # backup.sh, make_review_pack.py, run_checks.py
  robot/
    bridge.py           # tiny Flask server for the live probe demo
    firmware/           # ESP32 code
  tests/
  data/                 # gitignored: raw/, clean/, cards/, checks/ (all per field)
  site/                 # the UI (owned by the UI teammate); we only write site/data/
    data/index.json     # list of prepared fields
    data/fields/<id>.json
    data/probe_log.json # recorded probe readings, replayed on the public site
    data/live.json      # live probe reading during the in-person demo only
```

## The output contract

`site/data/fields/<id>.json`, one per prepared field (abbreviated; `schema.json` is the full truth):

```json
{
  "field": {
    "name": "Demo field", "lat": 27.67, "lon": 85.43,
    "sections": [
      {"id": "s1", "polygon": [[85.4301, 27.6701], [85.4302, 27.6701], [85.4302, 27.6702], [85.4301, 27.6702]],
       "status": "green", "wetness": 62, "temp": 18.4, "sure": 0.4}
    ]
  },
  "diary": {
    "shift_days": 12, "bare_days": 110, "guess": ["rice", "bare"],
    "groundwater": {"trend_cm_per_year": -1.2, "direction": "falling", "confidence": 0.7},
    "months": [{"m": "Jan", "rain": "low", "soil": "dry", "heat": "none", "frost": "risk", "cover": "bare"}]
  },
  "plans": [
    {"id": "current", "name": "What you do now",
     "crops": [{"crop": "rice", "start": "06-15", "end": "10-30"}],
     "score": {"harvest": 72, "water": 40, "cover": 35, "soil_kept": 60},
     "tabs": {"why": "...", "evidence": "...", "benefits": "...", "unknown": "...", "check": "..."},
     "tips": ["..."]}
  ],
  "replay": {"current": [{"year": 2001, "harvest": 80, "dry_days": 12, "event": "none"}]},
  "future": {"years": [2026, 2040],
             "nothing_changes": {"harvest": [70, 55], "harvest_low": [62, 41], "harvest_high": [76, 66]},
             "with_plan": {"harvest": [78, 74], "harvest_low": [72, 63], "harvest_high": [83, 81]}},
  "sources": [{"name": "NASA POWER", "product": "Daily API", "resolution": "0.5 x 0.625 deg", "years": "2001-2025", "type": "model"}]
}
```

Value rules: `status` is green, yellow, red or grey (grey = unknown). `event` is none, drought, flood or
frost. `sure` runs 0 to 1. Scores run 0 to 100, higher is better for the farmer. Month words:
`rain` low, medium, high; `soil` dry, medium, wet; `heat` none, some, high; `frost` none, risk, high;
`cover` bare, partial, crop. `groundwater.direction` is falling, steady or rising (falling needs a
negative trend, rising a positive one); `groundwater.confidence` runs 0 to 1. In `future`, each
`harvest` array has `harvest_low` and `harvest_high` beside it (the spread across models and
scenarios), one value per year, with low <= harvest <= high. Every change to the contract is listed
in `pipeline/export/CONTRACT_CHANGES.md`.

`site/data/index.json` lists the prepared fields so the site can offer them and can tell when a
drawn field is outside every prepared area:
`{"fields": [{"id": "demo", "name": "Bhaktapur demo field", "country": "Nepal", "lat": 27.67, "lon": 85.43, "bbox": [85.42, 27.66, 85.44, 27.68]}]}`

Live probe file for the demo, `site/data/live.json`, written by `robot/bridge.py`:
`{"section": "s1", "wetness": 41, "temp": 17.9, "sure": 0.8, "time": "2026-11-14T10:32:00"}`

## Data sources (fetch/)

| Source | Product | Variables | Access |
| --- | --- | --- | --- |
| NASA POWER | Daily point API, community AG | T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR | HTTP, no login |
| GPM IMERG | GPM_3IMERGDF V07 (Final, daily, 0.1 deg) through 2025-09-30, then GPM_3IMERGDL V07 (Late) for Oct-Dec 2025 (D1; the switch is recorded in the card's `segments`) | precipitation | earthaccess |
| HLS | HLSL30_VI and HLSS30_VI v2.0 (30 m) | NDVI, plus the cloud-mask layer (name TODO-VERIFY by listing a granule) | earthaccess; read only the field's window |
| MODIS | MOD13Q1.061 (250 m, 16-day) | NDVI before 2013 | earthaccess |
| SMAP | SPL3SMP_E v006 (surface), SPL4SMGP v008 (root zone, model-assisted) | soil moisture | earthaccess |
| SoilGrids 2.0 | 250 m | sand, clay, soc, bdod; water content at 33 kPa (wv0033) and 1500 kPa (wv1500) if present, else a pedotransfer function | public WCS/REST |
| NASADEM | NASADEM_HGT v001 (30 m) (D3) | elevation, then slope and topographic position | earthaccess |
| ECOSTRESS | ECO_L2T_LSTE and ECO_L4T_ESI V003 (70 m); V002 only for dates V003 lacks (D4) | surface temperature, stress | earthaccess (optional layer) |
| NEX-GDDP-CMIP6 | daily, 0.25 deg, to 2100 (not in CMR; public bucket `nex-gddp-cmip6`, 35 models) | pr, tasmax, tasmin, hurs, rsds, sfcWind | public cloud storage; extract one grid point |
| GRACE/GRACE-FO | TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 (CMR C3195527175-POCLOUD) (D5) | water storage anomaly, trend for `diary.groundwater` (D7) | earthaccess |

**Who supplies what to the twin (D6, 2026-11-11):** GPM IMERG supplies the twin's rain. NASA POWER
supplies temperature, humidity, wind and sunshine; POWER's PRECTOTCORR is kept for cross-checks only.
IMERG days are UTC days (05:45 to 05:45 Nepal time; TODO-VERIFY in the V07 documentation); POWER days
are local solar time (API header `time_standard: LST`). Say so wherever the two are compared, and
compare monthly totals as well as daily values.

Each fetch module: (1) downloads only the field's area or point, (2) caches raw files in
`data/raw/<source>/<field>/`, (3) writes a tidy daily or per-image table to
`data/clean/<field>/<source>.parquet` (per field, so step 11 needs no code change), (4) writes its
data card and appends to `CREDITS.md`. Verify every unit against the product documentation and write
the unit into the column name.

## The twin: equations (twin/)

All daily time steps. Sources: FAO Irrigation and Drainage Paper 56 (FAO-56) and Paper 33 (FAO-33).

**Reference evaporation, ET0 (FAO-56 Penman-Monteith, daily, G = 0):**

```
ET0 = [0.408 * D * Rn + g * (900 / (T + 273)) * u2 * (es - ea)] / [D + g * (1 + 0.34 * u2)]
T  = (Tmax + Tmin) / 2
e0(T) = 0.6108 * exp(17.27 * T / (T + 237.3))            # kPa
es = (e0(Tmax) + e0(Tmin)) / 2;   ea = RHmean / 100 * es   # FAO-56 eq. 19 when only mean RH exists
D  = 4098 * e0(T) / (T + 237.3)^2
P  = 101.3 * ((293 - 0.0065 * z) / 293)^5.26;   g = 0.000665 * P
Rn = (1 - 0.23) * Rs - Rnl   # Rnl from FAO-56 eq. 39 using Rso = (0.75 + 2e-5 * z) * Ra
```

Test: compare against the `pyet` (or `refet`) library on 30 days of real POWER data; daily values
must agree within 3 percent.

**Crop water use:** `ETc = Kc * ET0`, with Kc following the FAO-56 four-stage curve (Kc_ini flat,
linear rise through development, Kc_mid flat, linear fall to Kc_end). Bare soil days use a soil
evaporation coefficient (start with 0.3, tune, document).

**Soil-water bucket (root-zone depletion Dr, mm):**

```
TAW = 1000 * (theta_fc - theta_wp) * Zr        # mm
p   = p_table + 0.04 * (5 - ETc)                # clamp to 0.1..0.8
RAW = p * TAW
Ks  = 1 if Dr <= RAW else (TAW - Dr) / ((1 - p) * TAW)
ETa = Ks * ETc
Dr_today = Dr_yesterday - (rain - runoff) - irrigation + ETa
if Dr_today < 0: deep_percolation = -Dr_today; Dr_today = 0
Dr_today = min(Dr_today, TAW)
```

A "dry day" is a day with Ks < 1 during a crop season. Irrigation is applied only if the field's
water source allows it, using a simple rule (refill when Dr > RAW), and its total is reported.

**Rice:** paddy rice is not a free-draining bucket. In the monsoon season, treat rice as ponded: no
water stress while rain plus irrigation keep the field wet; switch to the bucket when the water source
is rain-only and rain stops. State this simplification in the "unknown" tab.

**Runoff (SCS curve number, mm):**

```
S  = 25400 / CN - 254;   Ia = 0.2 * S
runoff = (P - Ia)^2 / (P - Ia + S) if P > Ia else 0
```

CN depends on cover and soil group: bare fallow high (about 86 to 91), growing crop lower, cover crop
or residue lower still. Values from a published curve-number table, cited in `rules.yaml`.

**Yield as a percentage of potential (FAO-33):**

```
harvest_pct = 100 * (1 - Ky * (1 - sum(ETa) / sum(ETc)))     # over the crop season, clamp 0..100
```

Ky per crop from FAO-33 or FAO-66 tables, recorded with its source in `crops.json`. Add frost and
heat penalties only if a published rule supports them.

**Erosion (RUSLE, t/ha/yr):** `A = R * K * LS * C * P`. R from daily rainfall with a published
erosivity equation; K from SoilGrids texture and organic carbon (EPIC/Williams formula); LS from
SRTM slope; C from each month's cover in the rotation (bare high, crop medium, cover crop or residue
low); P = terracing factor. Report as a comparison between plans ("soil kept"), not as a precise
tonnage.

**Frost:** a frost night is Tmin below 0 C (risk band 0 to 2 C). Sections in low ground (negative
topographic position index from SRTM) get a cold-air pooling flag. Clear, calm nights (low cloud,
low wind) raise the risk.

**Probe fusion (scalar Kalman update, per section):**

```
predict:  x = twin soil wetness for today;   Pk = Pk + Q          # model variance grows daily
update:   K = Pk / (Pk + R);   x = x + K * (z - x);   Pk = (1 - K) * Pk
sure = clamp(1 - sqrt(Pk) / sqrt(P0), 0, 1)
```

z is the probe reading converted to volumetric water through the day's calibration (air = dry,
water = saturated). R is the probe's error variance from repeated readings. The initial P0 and Q come
from comparing SMAP with the twin; document the values.

## Field diary (diary/)

- **Greenness series:** NDVI per image for the field polygon from HLS (2013 on) and MODIS (2000 on),
  cloud-masked; require a minimum clear-pixel fraction per image.
- **Bare days:** a day is bare when interpolated NDVI is below the threshold in `rules.yaml` (start
  at 0.25, tune with known bare dates); report per year and per month. Widen uncertainty in cloudy
  months (days since last clear image).
- **Seasons and rotation guess:** detect green-up, peak and harvest per season from the smoothed NDVI
  curve; map season timing to likely crops using the crop calendar; the farmer confirms on screen.
  Compare **three** detection methods (thresholds; change-point, e.g. `ruptures`; and the SI season
  detective in "SI components") on held-out years, use the best, and report the comparison in
  VALIDATION.md and on the site's method page.
- **Groundwater (D7):** from GRACE/GRACE-FO (JPL mascon CRI RL06.3), the regional water-storage trend
  over the record: `diary.groundwater = {trend_cm_per_year, direction: falling|steady|rising,
  confidence}`. It is regional context (a mascon is far larger than a field), and it feeds the plans'
  water score. The rule for "steady" and for confidence is set and cited in `rules.yaml` at step 6.
- **Monsoon onset (per year, GPM):** search from 15 May; onset is the first run of at least 2 wet days
  totalling 10 mm within 5 days, not followed by a 10-day dry spell (under 1 mm per day) in the next
  20 days. Re-run with 15- and 20-day dry spells to show robustness. Sanity check: Nepal's
  climatological onset is about 10 June.
- **Trends:** Mann-Kendall test with Sen's slope (`pymannkendall`) on onset dates, hot days (above
  the local 90th percentile of Tmax), longest dry spell (consecutive days under 1 mm), and heavy-rain
  days (20 mm or more). `shift_days` is the onset trend over the record, with its confidence range.
- **Monthly calendar:** classify each month as low, medium or high (terciles of the 2001 to 2025
  climatology) for rain, soil, heat and frost, and record typical cover.

## Plans (plans/)

1. **Generate:** every feasible sequence from `crops.json` that fits the calendar (season windows,
   durations, no overlap), the water source and the zone. Expect a few hundred.
2. **Simulate:** run each sequence through every season 2001 to 2025 on one representative section.
3. **Score (0 to 100):** harvest (mean harvest_pct), stability (10th percentile year), water (water
   need versus availability, made stricter when `diary.groundwater.direction` is falling; D7, method
   and source recorded in `rules.yaml`), cover (fewer bare days), soil_kept (erosion versus the
   current plan), plus pest-cycle breaks (no same crop family back to back) and nitrogen (legumes
   included).
4. **Select:** keep the Pareto-best set; the three shown are the current plan, the best "cover the
   gap" plan and the best "follow the shift" plan, re-ranked by the farmer's priority weights.
5. **Explain:** fill the five tabs from the numbers using templates (why, evidence with dataset names
   and years, benefits, unknowns, what to check locally). SI may polish wording at build time; a person
   reviews every text before export.
6. **Tips:** derived from the twin, per section: when the bucket runs low (watering), which months
   stress the crop (timing), where runoff and erosion are high (cover, mulch, contour planting).

## Future (future/)

- **Delta-change method:** for several NEX-GDDP-CMIP6 models and two scenarios (SSP2-4.5 and
  SSP5-8.5), compute monthly changes between 1995-2014 and 2026-2040 (temperature as a difference,
  rainfall as a ratio) and apply them to the observed 2001-2025 weather. Run the twin; report the
  spread across models as a range.
- **Slider scenarios:** precompute a grid (rain x 1.0, 0.9, 0.8, 0.7; warming +0, +0.5, +1, +1.5,
  +2 C) for the three plans, so the UI sliders only switch between saved results. No simulation runs
  in the browser.

## Sections (sections/)

Split the field polygon into roughly 10 m by 10 m sections (coarser for big fields, aiming for 10 to
40 sections). Treat terrace steps (sharp elevation changes) as boundaries. Attach slope, topographic
position, SoilGrids soil, and ECOSTRESS stress to each section. Most sections in a small field share
the same 250 m soil cell; the probe readings are what tell them apart. Say so in the "unknown" tab.

## Field memory (ml/memory.py, required: build step 7b)

Learn this field's quirks: predict each season's observed peak-NDVI anomaly from the twin's simulated
stress, onset date and dry spells, using ridge regression or a small random forest with
leave-one-year-out validation. Apply the correction to future runs only if it beats the physics-only
baseline on held-out years; otherwise report the result honestly and keep physics only. Report the
result either way. NDVI is a stand-in for harvest; state that.

## SI components (required unless marked optional)

SI (AI) is a required part of the project. **Rule: never call an AI service from the public site; all
SI runs at build time or on the phone** (golden rule 13). Log every use in `CREDITS.md` and
`SI_LOG.md`.

1. **Season detective** (required, build step 6; `ml/seasons.py`): a third season-detection method. A
   small machine-learning classifier (random forest or gradient boosting) on smoothed-NDVI features
   (level, slope, time since green-up) plus rain and temperature labels each date growing, harvested
   or bare. Train on high-confidence dates from the threshold method plus the farmer-confirmed
   calendar; test on held-out years; compare all three methods and use the best. Report the
   comparison in VALIDATION.md and on the site's method page. *(The method page needs a contract
   field; propose it at step 6 and wait for the owner's go.)*
2. **Field memory** (required, build step 7b): see "Field memory" above.
3. **Plain words and voice** (required, build step 7; `words/`): SI drafts the five tabs, the tips,
   the glossary and the Nepali translations from the numbers at build time. A person reviews every
   text before export, and everything is logged in `SI_LOG.md`. Nepali audio files are generated with
   a text-to-speech service at build time, with any key kept in `.env`. *(The service is a new
   dependency: ask first.)*
4. **Photo check** (optional, after step 11): a small on-device image model (TensorFlow.js or ONNX
   Runtime Web) that labels a farmer's photo as bare, residue or green cover. Cover only, never
   disease. It runs on the phone; no photo leaves it.

## Probe bridge (robot/bridge.py)

Flask app on the laptop for the live demo only: `POST /reading` with `{"section", "raw", "temp_c"}`;
convert raw to wetness via today's calibration; run the Kalman update against the twin state stored
in `data/clean/twin_state.json`; write `site/data/live.json`. After the demo, save all readings to
`site/data/probe_log.json` so the public site can replay them.

## How judges will see it (requirements this creates)

Global judges only ever see the project page, the 30-second video, the public repository and the
**live site**, opened on their own device between submission and January, with nothing running on
our side and nothing changeable after submission. Local judges also see the live probe demo.

1. The site must work fully from static files, on a phone, on mobile data, with no keys.
2. **Prepared fields:** export at least the Nepal demo field plus two or three abroad (for example
   Guatemala, Kenya, USA) through the same pipeline with no code changes. That is the proof the
   method is global.
3. **Guided entry:** `index.json` powers a "Try our demo field" button and a short list of prepared
   fields. A field drawn outside every `bbox` gets a friendly message, not an error.
4. **Probe replay:** `probe_log.json` holds the readings recorded at the event, with the before and
   after `sure` values, so the site can replay the live demo for judges who were not in the room.
5. **Readable repository:** `README.md` explains, in plain words, what the pipeline does, how to run
   it for a new field, and why there is no backend.

## Site rules (only when asked to work in site/)

- Ten screens, one action each: Home (zoom into the field); Where is your field (tap four corners,
  two picture questions); We looked at your field from space (rotation guess, two cards); Your field
  in small parts (sections with numbers and dots); How is each part (colours and faces); Let's check
  the soil (probe, fog clears as `sure` rises); Watch your field's last 20 years (replay, baskets);
  What should I grow (three plans, five tabs, tips); Your field in 2040 (nothing changes versus the
  plan, two dials); Your plan (takeaway, with "you know your land best"). No games.
- Words a five-year-old and a ninety-year-old both understand: sentences of eight words or fewer; no
  science words ("harvest", not "yield"; "what to grow, and when", not "rotation"). Science terms live
  only in the glossary.
- Pictures before words: baskets for harvest, drops for water, faces plus tick, warning and cross for
  status, fog for "not sure yet". Never colour alone.
- Nepali first, English one tap away; a speaker button on every text, playing prebuilt MP3s.
- Plain HTML, CSS and JavaScript; Leaflet for the map; SVG tiles for the little field (no heavy 3D
  engine); first screen under 300 KB; designed at 360 px wide; buttons at least 48 px.

## Build order (one Claude Code session per step; tests first)

1. **Skeleton:** layout, `requirements.txt`, `.gitignore` (data/, .env), `scripts/backup.sh`, pytest, `schema.json` from the
   contract, `mock.py` writing a valid mock `site/data/fields/demo.json` and `site/data/index.json`. *Done when* the mock validates and
   the UI teammate has it.
2. **Fetch POWER** for `config/fields/demo.yaml`, 2001-2025. *Done when* `data/clean/demo/power.parquet`
   has 9,000+ daily rows with unit-named columns and `data/cards/demo/power.json` exists.
3. **ET0** with tests against pyet. *Done when* within 3 percent.
4. **Crop library and bucket:** `crops.json` for rice, wheat, maize, potato, lentil, mustard,
   buckwheat, finger millet (Kc, stage lengths, Zr, p, Ky, family, legume flag, calendar window,
   sources); soil-water bucket with runoff; yield. *Done when* one rice-wheat season runs and a plot
   of Dr looks sensible.
5. **First real export:** replay 2001-2025 for the current rotation; write `replay.current` into
   the field file. *Done when* the UI's replay screen shows real years. *(D6: the twin's rain is
   IMERG, so this step needs the GPM fetch and an Earthdata login in `~/.netrc`.)*
6. **Diary:** GPM fetch (Final, then Late, D1) and onset; HLS/MODIS greenness; bare days; three-way
   season detection including the SI season detective; GRACE groundwater (D7); trends; monthly
   calendar; rotation guess. *Done when* `diary` in the field file is real and the three-method
   comparison is in VALIDATION.md.
7. **Plans:** generate, simulate, score, select three, explain, tips; SI plain words and voice (drafts,
   Nepali, audio, all reviewed by a person). *Done when* `plans` is real and every tab has reviewed
   text.
7b. **Field memory:** train and test (leave one year out); keep it only if it beats physics alone.
    *Done when* the result, either way, is in VALIDATION.md.
8. **Sections, erosion, frost, ECOSTRESS:** per-section status and zones.
9. **Future:** NEX-GDDP deltas, scenario grid, `harvest_low` / `harvest_high` from the spread.
10. **Probe bridge and Kalman.**
11. **More fields and the judge path:** run the whole pipeline for two or three fields abroad; write
    `index.json`; record `probe_log.json`; write `README.md`. *Done when* each prepared field opens on
    the live site from a phone on mobile data.
11b. **Optional:** photo check (on-device cover classifier).
12. **Optional:** SMAP comparison; haze calendar.

After every step: run the tests, export the field file, validate it, run the backup script, and note anything the UI
teammate needs to know.

**Before submission (Sunday evening, before the final commit):** every file in `site/data/`
validates; the full test suite passes; `.gitignore` covers `data/`, `.env` and anything with a
credential; a search of the repository finds no key, token or password; `CREDITS.md` and `SI_LOG.md`
are complete.

**The final commit, done by the owner** (start at least 30 minutes before the local deadline):
1. Check `.gitignore` one last time.
2. Commit everything and push to GitHub.
3. Make the repository public and turn on GitHub Pages.
4. Open the live link on a phone that has never opened it, and check that a prepared field loads.
5. Paste the live link and repository link into the Space Apps project page and submit.

After submission, change nothing until the Global Winners are announced in January.

## Out of scope

A backend or database; user accounts; live API calls from the site; yield in tonnes; disease
diagnosis; any claim that the tool replaces an agronomi