# CLAUDE.md: Khet Sathi data and model

## What this repo is

Khet Sathi ("field friend") is a phone website that helps smallholder farmers (Nepal first, anywhere
later) choose crop rotations for each section of their field, using NASA data. This repository holds
the **pipeline**: it downloads public data for a field, runs a small physics "twin" of the field's soil
water and crops through every season from 2001 to 2025 and through projected futures, scores crop
rotations, and exports **static JSON** that the website in `site/` reads.

There is **no backend**. Everything heavy is precomputed here; the site only reads small files. The one
exception (owner, 2026-11-12) is the live probe: one Firebase Realtime Database carries live probe
readings and nothing else (see "Out of scope" and build step 10b).
Several fields are prepared in advance (the demo field in Nepal plus a few abroad). Each gets its own
JSON file and an index file lists them, so a judge anywhere can open the live site and explore a
prepared field while our laptop is switched off.

**Demo field (owner, 2026-11-12):** 27.67 N, 85.43 E is Bhaktapur's old city, not farmland, so it is
only the centre of a **fetch box** of about 5 km each way (`fetch_box` in `config/fields/demo.yaml`;
every dataset is fetched for the box, so a nearby real field needs no re-download). The field itself
is a labelled **PLACEHOLDER**. The first one (a 100 m WorldCover-cropland square at 27.6785 N,
85.427417 E) turned out, on satellite imagery, to be a construction plot (owner, 2026-11-12): WorldCover
2021 is out of date there. The replacement is a **60 m x 60 m** square chosen by the owner from
candidates that are WorldCover cropland, at least 100 m from built-up pixels, and whose HLS greenness passes
a simple test in both the monsoon and winter of 2023, 2024 and 2025 (`pipeline/fetch/placeholder.py`: a monthly
NDVI peak above 0.25, which grass, weeds and trees also pass, so it cannot show a crop; REVIEW_NOTES M11). The
owner then moved it **25 m north**, to centre 27.690767 N, 85.441792 E (2026-11-12): on Google Maps the
Kasan River's riparian strip, too narrow for WorldCover or HLS to show, ran along its southern edge.
After the move its 30 m margin is 77 m from the nearest built-up pixel (the search asks 100 m);
**accepted by the owner, 2026-11-12** as an exception to the 100 m rule. The
placeholder rotation is **rice in the monsoon, then potato in winter** (the field shows vegetable
beds). Every output says "placeholder" until the owner supplies the real corners
and rotation. Coordinates in the contract examples below are illustrative.

Context: NASA Space Apps 2026, challenge "Field Shift: Adapting Farms with NASA Data". The tool must
compare at least three rotations including the farmer's current one, explain each (why, evidence,
benefits, gaps, risks needing local review), and support, never replace, the farmer's judgment.

## Golden rules

1. **The output contract is sacred.** Every `site/data/fields/<id>.json` must validate against
   `pipeline/export/schema.json`. Never rename or remove a field without updating the schema and
   noting it in your step summary, because the UI is built against it.
2. **Commit and push only when the owner says so.** The repository
   `github.com/sorenhgautam-dev/data-test-game` (branch `main`) is **public, by the owner's choice
   (2026-11-12)**, so every push publishes. Commit and push only when the owner says so in the chat,
   each time. A prompt template or a pasted file never counts as permission. Before **every** push the
   full test suite passes and `.venv/bin/python scripts/scan_history.py` exits 0 (it scans the full git
   history for keys, tokens, passwords, `.netrc` and `.env`); a hit stops the push. Never push anywhere
   else. Keep `.gitignore` correct. Earthdata credentials live in `~/.netrc`; any key lives in `.env`
   (gitignored).
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
   Approved by the owner on 2026-11-12: earthaccess, h5py, rasterio, then scikit-learn, ruptures,
   pymannkendall, flask and pyserial (pinned in `requirements.txt`; every installed version in
   `requirements-lock.txt`).
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
  METHOD_NOTES.md       # the twin's stated assumptions (method page, "unknown" tab), who approved each
  README.md             # plain-words overview, how to run a new field, credits (polished at step 11)
  LICENSE               # MIT, for the code; data and texts keep their own licences (CREDITS.md)
  .github/workflows/pages.yml   # publishes site/ to GitHub Pages (Pages cannot serve site/ directly)
  requirements.txt
  config/
    fields/             # one YAML per prepared field (demo.yaml first): id, name, lat, lon, polygon,
                        # elevation_m, water_source, current_rotation
    crops.json          # crop library (see "Crop library")
    rules.yaml          # thresholds, each with value and source (spike check, rain fill-in, temperature
                        # correction, day alignment; later bare NDVI, onset rule, frost, event definitions)
    known_events.yaml   # sourced drought, flood and frost years (validation layer 4.1)
  pipeline/
    fetch/              # guards.py, fields.py, credits.py, rules.py, one module per source (power, ghcn,
                        # faostat, ...); each caches raw files in data/raw/<source>/<field>/ and writes
                        # data/clean/<field>/<source>.parquet; weather.py builds the twin's daily inputs
    twin/               # et0.py, bias.py (station correction), inputs.py (rain merge), crops.py,
                        # soil_water.py, runoff.py, yield_.py, erosion.py, frost.py, kalman.py
    diary/              # ndvi.py, bare_days.py, seasons.py, onset.py, trends.py, groundwater.py
    plans/              # generate.py, simulate.py, score.py, explain.py
    future/             # nexgddp.py, scenarios.py
    sections/           # grid.py: split the field polygon into sections, attach per-section attributes
    ml/                 # seasons.py (season detective classifier), memory.py (field memory)
    words/              # SI drafts of tabs, tips, glossary, Nepali text (text only: no audio, owner 2026-11-12)
    checks/             # validation-layer statistics: climate.py, crosscheck.py (incl. day alignment), spikes.py
    export/             # schema.json, index_schema.json, validate.py, mock.py, build_field_json.py, build_words.py,
                        # CONTRACT_CHANGES.md (what changed for the UI, and when)
  scripts/              # backup.sh, make_review_pack.py, scan_history.py; the runners run_checks.py, run_replay.py,
                        # run_diary.py, run_plans.py, run_rain_check.py; checks run_smap_check.py, run_dhm_bulletin_check.py
  robot/
    probe.py            # parse the probe's USB serial lines (pure)
    bridge.py           # read the probe over USB serial, write site/data/live.json (live demo only)
    fake_probe.py       # prints the probe's exact lines, for tests and rehearsal without the hardware
    firmware/           # original_probe/: the robot teammate's sketch, kept unchanged (owner, 2026-11-12); khet_probe/ comes with 10b
  tests/
  data/                 # gitignored: raw/, clean/, cards/, checks/ (all per field)
  site/                 # the UI (owned by the UI teammate); we only write site/data/
    data/index.json     # list of prepared fields
    data/fields/<id>.json
    data/words.json     # every screen word, the glossary and the crop explainers (pipeline/export/build_words.py)
    data/probe_log.json # recorded probe readings, replayed on the public site
    data/live.json      # live probe reading during the in-person demo only
```

Not written yet (2026-11-13): `twin/erosion.py`, `twin/frost.py`, `twin/kalman.py`, `diary/bare_days.py`, `future/nexgddp.py`,
`future/scenarios.py`, `sections/grid.py`, `ml/memory.py`. What exists instead: the relative erosion index in
`plans/score.py`, the frost band in `diary/months.py`, bare days in `diary/greenness.py`. Added since this layout was
written: `fetch/chirps.py`, `gpm_late.py`, `gauge_evidence.py`, `smap.py` (checks only), `checks/rain_check.py`,
`diary/groundwater.py`, `guess.py`, `months.py`, `seasons.py`, `trends.py`.

## The output contract

`site/data/fields/<id>.json`, one per prepared field (abbreviated; `schema.json` is the full truth):

```json
{
  "field": {
    "name": "Demo field", "lat": 27.67, "lon": 85.43, "water_source": "unknown",
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
  "replay": {"current": [{"year": 2001, "harvest": 80, "dry_days": 12, "event": "none",
                          "irrigated": {"harvest": 97, "dry_days": 0}}]},
  "future": {"years": [2026, 2040],
             "nothing_changes": {"harvest": [70, 55], "harvest_low": [62, 41], "harvest_high": [76, 66]},
             "with_plan": {"harvest": [78, 74], "harvest_low": [72, 63], "harvest_high": [83, 81]}},
  "sources": [{"name": "NASA POWER", "product": "Daily API", "resolution": "0.5 x 0.625 deg", "years": "2001-2025", "type": "model"}]
}
```

Value rules: `status` is green, yellow, red or grey (grey = unknown). `event` is none, drought or
flood (frost is only a monthly risk band, owner, 2026-11-12). `sure` runs 0 to 1. Scores run 0 to 100, higher is better for the farmer. Month words:
`rain` low, medium, high; `soil` dry, medium, wet; `heat` none, some, high; `frost` none, risk, high;
`cover` bare, partial, crop. `groundwater.direction` is falling, steady or rising (falling needs a
negative trend, rising a positive one); `groundwater.confidence` runs 0 to 1. In `future`, each
`harvest` array has `harvest_low` and `harvest_high` beside it (the spread across models and
scenarios), one value per year, with low <= harvest <= high. Each replay year's `irrigated`
(owner's go, 2026-11-12) is the same year with water whenever needed; `harvest`, `dry_days` and
`event` are the field's own water case. `field.water_source` is unknown, rain-only, canal, well or
irrigated; **while it is unknown the site shows both cases side by side**, "if you can't water" (the
rain-fed `harvest`, `dry_days`) and "if you can water" (`irrigated`) (owner, 2026-11-12). Only complete
years are exported, each holding every crop of the rotation (2002-2025 for rice then potato; owner,
2026-11-12). Each plan also carries `tabs_ne` and
`tips_ne` (owner, 2026-11-12): the same five tabs and one Nepali tip per English tip, in the same order.
A section's `temp` is soil temperature from the probe (owner, 2026-11-12), and `null` until the probe has
read that section ("not sure yet"). **No made-up number is ever exported (owner, 2026-11-13):** a block that is not
computed yet is named in the top-level `mock` list (`field.sections`, `future`) and holds no numbers (sections grey with
null `wetness` and `temp` and `sure` 0; `future` null), and the site says "not ready yet". Each replay year's `irrigated`
is required. The file also has a required `method` block (the method page: `season_detection`, `rain_correction`,
`choices`). `site/data/words.json` holds every screen word, the glossary and the crop explainers. Every change to the
contract is listed in `pipeline/export/CONTRACT_CHANGES.md`.

`site/data/index.json` lists the prepared fields so the site can offer them and can tell when a
drawn field is outside every prepared area:
`{"fields": [{"id": "demo", "name": "Bhaktapur demo field", "country": "Nepal", "lat": 27.67, "lon": 85.43, "bbox": [85.42, 27.66, 85.44, 27.68]}]}`

Live probe file for the demo, `site/data/live.json`, written by `robot/bridge.py`:
`{"section": "s1", "wetness": 41, "temp": 17.9, "sure": 0.8, "time": "2026-11-14T10:32:00"}`
(`temp` is null when the probe says "Check wiring"; `sure` is null until the step-10 Kalman update.)

## Data sources (fetch/)

| Source | Product | Variables | Access |
| --- | --- | --- | --- |
| NASA POWER | Daily point API, community AG; 0.5 x 0.625 deg meteorology (MERRA-2, GEOS-IT for the latest 1-3 months), 1 x 1 deg solar (CERES SYN1deg) | T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR | HTTP, no login |
| GPM IMERG | GPM_3IMERGDF V07 (Final, daily, 0.1 deg) through 2025-09-30, then GPM_3IMERGDL V07 (Late) for Oct-Dec 2025 (D1; the switch is recorded in the card's `segments`) | precipitation | earthaccess |
| HLS | HLSL30_VI and HLSS30_VI v2.0 (30 m) | NDVI, plus the cloud-mask layer `Fmask` (verified 2026-11-12, DATA_AUDIT 1.3) | earthaccess; read only the field's window |
| MODIS | MOD13Q1.061 (250 m, 16-day) | NDVI before 2013 | earthaccess |
| SMAP | SPL3SMP_E v006 (surface), SPL4SMGP v008 (root zone, model-assisted) | soil moisture | earthaccess |
| SoilGrids 2.0 | 250 m | sand, clay, soc, bdod; water content at 33 kPa (wv0033) and 1500 kPa (wv1500) if present, else a pedotransfer function | REST API; if it is down, ISRIC's downloadable GeoTIFF files, recorded in the card. If the field's cell has no prediction, the nearest cell with values (250 m steps, up to 1 km), distance in the card |
| NASADEM | NASADEM_HGT v001 (30 m) (D3) | elevation, then slope and topographic position | earthaccess |
| ECOSTRESS | ECO_L2T_LSTE and ECO_L4T_ESI V003 (70 m); V002 only for dates V003 lacks (D4) | surface temperature, stress | earthaccess (optional layer) |
| NEX-GDDP-CMIP6 | daily, 0.25 deg, to 2100 (not in CMR; public bucket `nex-gddp-cmip6`, 35 models) | pr, tasmax, tasmin, hurs, rsds, sfcWind | public cloud storage; extract one grid point |
| GRACE/GRACE-FO | TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 (CMR C3195527175-POCLOUD) (D5) | water storage anomaly, trend for `diary.groundwater` (D7) | earthaccess |
| ESA WorldCover 10 m 2021 v200 (placeholder field only) | cropland class 40 | land-cover class | public COG, no login (CC BY 4.0) |
| GHCN-Daily (validation, and the station for correction A) | NOAA NCEI v3.35, by_station CSV; station in the field's `validation_station` | PRCP, TMAX, TMIN (tenths) | HTTP, no login |
| FAOSTAT (validation layer 4.3 only) | QCL bulk file (the API needs a token) | Nepal rice, wheat, maize yield, kg/ha | HTTP, no login |

**How each source is actually fetched for the box (2026-11-12):** GPM by daily OPeNDAP subsets from
GES DISC's Hyrax servers (`pipeline/fetch/gpm.py`; needs the GES DISC EULA accepted on the Earthdata
account); MODIS MOD13Q1 and SMAP L3/L4 through NASA LP DAAC **AppEEARS** area tasks, cut to the box on
NASA's side, netCDF-4, native projection (`pipeline/fetch/appeears.py`; MOD13Q1 is HDF4, which no
installed reader opens); HLS-VI NDVI + Fmask and ECOSTRESS tiled LST/QC/cloud and ESI by windowed
reads of the cloud-optimised GeoTIFFs (`pipeline/fetch/cogwindows.py`; ECOSTRESS V003 first, V002 for
overpasses V003 lacks, per D4; AppEEARS offers only V002); NASADEM and GRACE as whole files via
earthaccess (one tile, one 44 MB file). The cloud OPeNDAP endpoint failed for GPM (no DMR++ files).

**Who supplies what to the twin (D6, 2026-11-11):** GPM IMERG supplies the twin's rain. GPM reads about
40% above the Kathmandu Airport station (49 complete months), so the station records about a third less;
the station is synoptic-derived and may under-record, so it is not the truth either. Owner, 2026-11-12:
(A) keep GPM and say so in the "unknown" tab; (B) Friday: compare the 4 GPM cells around the field and
monthly totals with DHM's published Bhaktapur averages, **and test for a break in the GPM series**: from
2017 GPM's yearly totals jump well above both the station and POWER (GPM/station about 1.0-1.2 in
2015-2016, then 1.5-2.3), so run a change-point test on yearly GPM totals and on the yearly GPM/POWER
ratio over 2001-2025, check the 4 neighbouring cells (hills nearby?), and say whether the jump is real or a
data break. **Until that is settled, no rain trend or monsoon-shift trend is reported without saying the
break may explain it** (`rules.yaml` gpm_series.trend_caveat; owner, 2026-11-12); (C) only if B shows GPM reads high, show a
station-scaled run as the lower edge of a range, labelled, never as a replacement. **Owner, 2026-11-13
(decision 1):** rain check B found a data break (IMERG Final's monthly gauge input around the field is lost from
January 2017; VALIDATION 3.9b), so the twin's rain from 2017 is scaled month by month back to GPM's own 2001-2016
level (`rules.yaml` gpm_series.correction; IMERG Final days only, demo field only until a field's own rain check
finds the break). The uncorrected GPM run is kept beside it (`weather.parquet` rain_uncorrected_mm; runners'
`--rain uncorrected` into `data/checks/<field>/rain_uncorrected/`), and every result it changes is exported as a
range (`replay` years' `uncorrected_rain`, plans' `score_uncorrected_rain`) and explained in plain words in the
"unknown" tab and on the method page (`method.rain_correction`). Checks only, never the twin's rain: IMERG Late
2014-2019 (`pipeline/fetch/gpm_late.py`) and CHIRPS v3.0 `rnl` 2001-2025 (`pipeline/fetch/chirps.py`). NASA POWER
supplies temperature, humidity, wind and sunshine; POWER's PRECTOTCORR is kept for cross-checks only.
IMERG days are UTC days (05:45 to 05:45 Nepal time; IMERG V07 Technical Documentation, 13 July 2023, p. 40); POWER days
are local solar time (API header `time_standard: LST`). Say so wherever the two are compared, and
compare monthly totals as well as daily values.

**The twin's daily inputs (`fetch/weather.py` → `data/clean/<field>/weather.parquet`), owner decisions
of 2026-11-11, thresholds in `rules.yaml`:**

- **A. Station correction of POWER temperature.** If the field config names a nearby station
  (`validation_station`, with `correction_label`), fit a monthly additive POWER-minus-station offset
  for Tmin and Tmax from shared days; fit on alternate qualifying years, test on the others, report
  the error before and after, and apply the offsets (refitted on all qualifying years) only if they
  lowered the held-out error. Applied **before ET0 and frost**. For the demo it is labelled
  "Kathmandu-valley correction" (valley cold-air pooling that a 55 km cell cannot resolve). Prepared
  fields without a nearby station use uncorrected POWER, labelled "uncorrected POWER". Humidity is
  checked the same way when the station records it (Kathmandu Airport does not). **Cold nights
  (owner, 2026-11-12):** Tmin is also fitted by empirical quantile mapping (per month, per season
  Dec-Feb / Mar-May / Jun-Sep / Oct-Nov when a month has under 20 shared days) on the same split, and
  judged against the offset on held-out years by mean absolute error, each January's coldest night and
  the count of nights below 2 C. **Owner, 2026-11-12 (step-4 review): use both, each for its
  purpose.** The offset feeds the twin's temperatures and ET0 (`tmin_c`, better MAE); quantile mapping
  feeds frost only (`tmin_frost_c`, better coldest-night error and nights below 2 C, on small samples: 3
  Januaries and 9 station nights, with no uncertainty given; REVIEW_NOTES M8). Both overcount
  cold nights against the station (held-out: offset 22, QM 15, station 9), so frost is shown as risk
  bands with the caveat, never as a count. Temperature checks against the same station are "fitted reference";
  the held-out results (independent in time only) and the known-events comparison are the independent evidence.
- **B. Cross-source spike check.** Flag any day where one rain source exceeds 50 mm and is more than
  five times another source; write the flags into each source's data card (`cross_source_flags`).
  Never delete or change a flagged value silently. Once GPM exists the three sources vote on each
  flagged day: a high station that GPM agrees with is a "real local storm", a high POWER outvoted is a
  "POWER spike", an outvoted station is "station value suspect" (`spikes.vote`).
- **C. Day alignment.** Daily rain correlation between sources at lags -1, 0, +1 days (lag k pairs
  reference day d with the other source's day d + k); report the best lag, for POWER vs station now
  and GPM later.
- **D. POWER rain is fill-in only.** Rain comes from GPM IMERG; POWER fills only days GPM lacks, never
  with 2001-2003 values, and every filled day is flagged (`rain_filled`, `rain_source`). Without a GPM
  record there is no rain: POWER never stands in for the whole series.

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
must agree within 3 percent. Implemented in `twin/et0.py` (step 3, 2026-11-11): FAO-56 Examples 2, 8
and 18 reproduced as printed (Example 18: 3.88 mm/day); identical to pyet on the 30 days. In eq. 39,
Rs/Rso is limited to 0.3..1.0 (FAO-56 states only the upper limit; the 0.3 floor is from ASCE-EWRI
2005, Task Committee final report, eq. 18, p. 20, and matches pyet). The twin computes ET0 from the station-corrected
temperatures (decision A). Elevation: the field's own once NASADEM is fetched; until then POWER's cell
elevation, labelled as such in the weather card.

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
water source allows it, using a simple rule (refill when Dr > RAW), and its total is reported (for
paddy too: the pond top-up is irrigation water; REVIEW_NOTES H1).

**Rice:** paddy rice is not a free-draining bucket. In the monsoon season, treat rice as ponded: no
water stress while rain plus irrigation keep the field wet; switch to the bucket when the water source
is rain-only and rain stops. State this simplification in the "unknown" tab. **As implemented
(REVIEW_NOTES H1; owner-approved 2026-11-12):** the pond is kept only when the field is irrigated, and
its top-up is booked as irrigation. Rain-fed rice gets no water beyond rain: it runs as the bucket with
rice's depletion fraction, so it is stressed once rain no longer keeps the root zone wet (no free top-up;
water the bunds would hold above field capacity is not modelled, so rain-fed rice is on the dry side).

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

Ky per crop from FAO-33 or FAO-66 tables, recorded with its source in `crops.json`. **Where no
seasonal Ky is published (owner, 2026-11-12):** a neutral Ky of 1.0, `ky_assumed: true` in
`crops.json` and labelled "assumed" in every output and explanation; the plan ranking is rerun with
Ky 0.8 and 1.2 for those crops (`rules.yaml` `ky_assumed`) and any change is reported. A
peer-reviewed rice Ky, if found, replaces 1.0 with its citation. Add frost and heat penalties only if
a published rule supports them.

**Erosion (RUSLE, t/ha/yr):** `A = R * K * LS * C * P`. R from daily rainfall with a published
erosivity equation; K from SoilGrids texture and organic carbon (EPIC/Williams formula); LS from
NASADEM slope (D3); C from each month's cover in the rotation (bare high, crop medium, cover crop or residue
low); P = terracing factor. Report as a comparison between plans ("soil kept"), not as a precise
tonnage. (As built, step 7: on one field K, LS and P cancel between plans, so `soil_kept` is 100 x (1 - the plan's
erosion index / the index of bare fallow all year), from daily erosivity and each crop's C; `pipeline/plans/score.py`.)

**Frost:** a frost night is Tmin below 0 C (risk band 0 to 2 C). Frost is never a per-year replay event
(owner, 2026-11-12, REVIEW_NOTES M1): it is shown only as the monthly risk band. Sections in low ground (negative
topographic position index from NASADEM, D3) get a cold-air pooling flag. Clear, calm nights (low cloud,
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
  20 days (counted from the onset date, as Moron, Robertson & Boer 2009 do; owner-approved 2026-11-13).
  Re-run with 15- and 20-day dry spells to show robustness. Sanity check: DHM's normal onset is 13 June
  in eastern Nepal, about two days later in Kathmandu (DHM Climate Division; replaces "about 10 June",
  owner-approved 2026-11-13). **Owner, 2026-11-12: keep this rule as set, with no tuning to
  the results**, although it fails the sanity check (median 16 May: in the valley late-May showers already
  pass it, VALIDATION 4.1d). So the dates it finds are the first lasting rain spell, not the monsoon's
  arrival, and every output says so.
- **Trends:** Mann-Kendall test with Sen's slope (`pymannkendall`) on onset dates, hot days (above
  the local 90th percentile of Tmax), longest dry spell (consecutive days under 1 mm), and heavy-rain
  days (20 mm or more). `shift_days` is the onset trend over the record, with its confidence range, and
  `null` ("can't tell") while the onset is pinned at its search start in most years (2026-11-13).
  Every rain-based trend (onset, `shift_days`, dry spells, heavy-rain days) carries the GPM-break caveat
  until rain check B settles it (owner, 2026-11-12).
- **Monthly calendar:** classify each month as low, medium or high (terciles of the 2001 to 2025
  climatology) for rain, soil, heat and frost, and record typical cover.

## Plans (plans/)

1. **Generate:** every feasible sequence from `crops.json` that fits the calendar (season windows,
   durations, no overlap), the water source and the zone. Expect a few hundred.
2. **Simulate:** run each sequence through every season 2001 to 2025 on one representative section.
3. **Score (0 to 100):** harvest (mean harvest_pct), stability (10th percentile year), water (water
   need versus availability, made stricter when `diary.groundwater.direction` is falling; D7, method
   and source recorded in `rules.yaml`), cover (fewer bare days; as built: the share of the year inside crop seasons, from the crop calendar, not from the
   satellite), soil_kept (erosion versus the current plan; as built: versus bare fallow all year, see "Erosion"), plus pest-cycle breaks (no same crop family back to back) and nitrogen (legumes
   included).
4. **Select:** keep the Pareto-best set; the three shown are the current plan, the best "cover the
   gap" plan and the best "follow the shift" plan, re-ranked by the farmer's priority weights. (Owner, 2026-11-13,
   decision 5: while `shift_days` cannot be measured the third plan is `safest`, "Safest in bad years"; see build
   step 7 and REVIEW_2 H2 on that name.)
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
   field; propose it at step 6 and wait for the owner's go. Done 2026-11-13: the required `method` block.)*
2. **Field memory** (required, build step 7b): see "Field memory" above.
3. **Plain words** (required, build step 7; `words/`): SI drafts the five tabs, the tips, the
   glossary and the Nepali translations from the numbers at build time. A person reviews every text
   before export, and everything is logged in `SI_LOG.md`. **No audio** (owner, 2026-11-12): the site is
   text only, Nepali first, English one tap away.
4. **Photo check** (optional, after step 11): a small on-device image model (TensorFlow.js or ONNX
   Runtime Web) that labels a farmer's photo as bare, residue or green cover. Cover only, never
   disease. It runs on the phone; no photo leaves it.

## Probe bridge (robot/bridge.py)

For the live demo only, on the laptop. The probe is the robot teammate's own build; its code is not
changed (owner, 2026-11-12); the sketch is kept as it is in `robot/firmware/original_probe/`. Over USB serial it prints one line every 2
seconds, exactly `Temperature: 23.1 °C  |  Moisture: 45%`, or `Temperature: Check wiring  |  Moisture: 45%`
when the temperature sensor is disconnected. Moisture is already 0-100 %, calibrated on the probe, so it
is the reading z as it is. `robot/probe.py` parses that format (anything else, or a value out of range, is
refused and logged); `robot/bridge.py --port <serial port> --section s1` reads the port and writes
`site/data/live.json` atomically for every good line, and logs every line to `data/probe/<field>/`;
`robot/fake_probe.py` prints the same lines (to stdout, or a pseudo-terminal the bridge opens like a USB
port) for tests and rehearsal. Step 10 adds the Kalman update against the twin state
(`data/clean/twin_state.json`) for `sure`. After the demo, the logged readings become
`site/data/probe_log.json` so the public site can replay them. The probe's own sketch is kept unchanged in
`robot/firmware/original_probe/` (115200 baud; moisture on GPIO34, an ADC1 pin; DS18B20 on GPIO4).

## How judges will see it (requirements this creates)

Global judges only ever see the project page, the 30-second video, the public repository and the
**live site**, opened on their own device between submission and January, with nothing running on
our side and nothing changeable after submission. Local judges also see the live probe demo.

1. The site must work fully from static files, on a phone, on mobile data, with no keys. The live
   probe (step 10b) is an extra: if Firebase is unreachable, every screen still works.
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
  the soil (probe, fog clears as `sure` rises); Watch your field's last {year_count} years (replay, baskets; {year_count} comes from the data: 24 for the demo's complete years 2002-2025; owner, 2026-11-12);
  What should I grow (three plans, five tabs, tips); Your field in 2040 (nothing changes versus the
  plan, two dials); Your plan (takeaway, with "you know your land best"). No games.
- Words a five-year-old and a ninety-year-old both understand: sentences of eight words or fewer; no
  science words ("harvest", not "yield"; "what to grow, and when", not "rotation"). Science terms live
  only in the glossary.
- Pictures before words: baskets for harvest, drops for water, faces plus tick, warning and cross for
  status, fog for "not sure yet". Never colour alone.
- Nepali first, English one tap away. Text only: no speaker buttons and no audio (owner, 2026-11-12). Months
  in Nepali are Bikram Sambat first, with the approximate Gregorian months beside them in Devanagari, e.g.
  बैशाख (अप्रिल–मे), and a note
  that they don't line up exactly (owner, 2026-11-12).
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
   of Dr looks sensible. Until GPM exists, the one-season test uses station rain (Kathmandu Airport,
   2016), clearly labelled as a temporary input; step 5 switches to GPM. Ky not published in
   FAO-56/FAO-66 (rice, lentil, mustard, buckwheat, millet) is the owner-assumed 1.0 (see "Yield").
5. **First real export:** replay 2001-2025 for the current rotation; write `replay.current` into
   the field file. *Done when* the UI's replay screen shows real years. *(D6: the twin's rain is
   IMERG, so this step needs the GPM fetch and an Earthdata login in `~/.netrc`.)* Every replay runs
   both rain-fed and irrigated and keeps both (owner, 2026-11-12); the export uses the field's water
   source. Built without GPM (2026-11-12): `pipeline/plans/simulate.py`, `scripts/run_replay.py`
   (stops with NOT YET POSSIBLE while rain is missing; `--temporary-station-rain` is a dry run that is
   never exported), `pipeline/export/build_field_json.py` (refuses non-GPM rain, missing years or
   missing events). GPM is complete (9,131 of 9,131 days); the event rules are owner-approved (flood fixed
   in advance from ETCCDI Rx1day and the decile classes, 2026-11-12); only complete years are exported
   (2002-2025). Still needed: the owner's `current_rotation` (placeholder rice then potato) and water source
   (unknown: both cases shown side by side).
6. **Diary:** GPM fetch (Final, then Late, D1) and onset; HLS/MODIS greenness; bare days; three-way
   season detection including the SI season detective; GRACE groundwater (D7); trends; monthly
   calendar; rotation guess. *Done when* `diary` in the field file is real and the three-method
   comparison is in VALIDATION.md. **6a** (onset, greenness, bare days) and **6b** (three season methods,
   held-out comparison fixed in advance in `rules.yaml` season_detection: the threshold method is used,
   VALIDATION 3.15) are built; **6c** (groundwater, trends, monthly calendar, rotation guess, diary export) is
   built (2026-11-13; VALIDATION 3.16-3.18, 4.1c): the diary in `demo.json` is real, with `shift_days` null while
   the onset is pinned at its search start.
7. **Plans:** generate, simulate, score, select three, explain, tips; SI plain words (drafts and
   Nepali, all reviewed by a person; no audio). *Done when* `plans` is real and every tab has reviewed
   text. **Built and exported 2026-11-13** (owner's decisions 1, 4, 5): every suggested plan keeps rice in the
   monsoon; the three plans are `current`, `cover_gap` ("Fill the empty months") and `safest` ("Safest in bad
   years"), three different rotations (VALIDATION 3.19); tabs and tips come from the templates in
   `pipeline/words` (`pipeline/plans/explain.py`). Still open: the owner's review of the English lines added
   on 2026-11-13 and a native speaker's review of all Nepali.
7b. **Field memory:** train and test (leave one year out); keep it only if it beats physics alone.
    *Done when* the result, either way, is in VALIDATION.md.
8. **Sections, erosion, frost, ECOSTRESS:** per-section status and zones.
9. **Future:** NEX-GDDP deltas, scenario grid, `harvest_low` / `harvest_high` from the spread.
10. **Probe bridge and Kalman.**
10b. **Online probe (option B; owner, 2026-11-12), only after the must-have steps:** the probe joins the
    farmer's phone hotspot (setup page on the probe; iPhone "Maximize Compatibility" for 2.4 GHz) and
    writes its readings to Firebase Realtime Database (Spark plan, no card); the website shows them
    live in iPhone Safari and Android Chrome. Security rules: each probe has its own ID, only that probe
    writes its readings, nobody can read another probe's data, and every value in the website is safe to
    be public. If Firebase is unreachable the site works fully. Firmware: Wi-Fi and Firebase added
    around the owner's reading code (its reading and calibration unchanged, USB output kept), in
    `robot/firmware/khet_probe/`, with no secrets. Each online reading also carries the raw moisture
    reading (`analogRead`, before mapping and limiting), so a limited 0 or 100 % can be told apart; the
    USB line stays exactly as the sketch prints it (owner, 2026-11-12). The live view is one small piece
    for the UI teammate.
    *Firebase project ready (owner, 2026-11-12):* `khet-sathi-probe`, Spark plan, Realtime Database in
    Singapore (asia-southeast1), anonymous sign-in on, anonymous clean-up off. The web config is in `.env`
    (gitignored) until 10b is built; the database is still locked (an unsigned read and write were both
    refused, 2026-11-12). The web config is public by Firebase's design, but `scan_history.py` flags
    `apiKey`. **Keys (owner, approved in advance, 2026-11-12):** two API keys, both restricted to the
    Identity Toolkit API and the Token Service API only: the website's key, also restricted to the GitHub
    Pages address; and a separate key for the probe, with no website restriction (the probe is not a
    browser). `scan_history.py` lets through the website's key **by its exact value only**, nothing else (built 2026-11-13, owner's answer 14: the
    script holds the key's SHA-256, never the key, and scans the working tree as well as the history; REVIEW_2 H7).
    The probe's key is therefore never in the repository (it is entered on the probe, or kept in a
    gitignored file). Claude gives the owner the exact console steps when 10b is built. The probe code
    is in `robot/firmware/original_probe/`.
11. **More fields and the judge path:** run the whole pipeline for two or three fields abroad; write
    `index.json`; record `probe_log.json`; write `README.md`. *Done when* each prepared field opens on
    the live site from a phone on mobile data.
11b. **Optional:** photo check (on-device cover classifier).
12. **Optional:** SMAP comparison (run 2026-11-13: `pipeline/fetch/smap.py`, `scripts/run_smap_check.py`, VALIDATION 4.2b;
    SMAP L3 has no recommended-quality retrieval over the demo field, so the check uses the model-assisted L4); haze calendar.

After every step: run the tests, export the field file, validate it, run the backup script, and note anything the UI
teammate needs to know.

**Before submission (Sunday evening, before the final commit):** every file in `site/data/`
validates; the full test suite passes; `.gitignore` covers `data/`, `.env` and anything with a
credential; a search of the repository finds no key, token or password; `CREDITS.md` and `SI_LOG.md`
are complete.

**Before ANY change of the repository to public (owner decision H):** run
`.venv/bin/python scripts/scan_history.py` over the **full git history** (every commit on every
branch, not just the current files) for keys, tokens, passwords, `.netrc` and `.env`. It must exit 0;
report the result. A hit in an old commit means the history must be cleaned (or a fresh repository
used) before going public: deleting the file in a new commit is not enough.

**The final commit, done by the owner** (start at least 30 minutes before the local deadline):
1. Check `.gitignore` one last time.
2. Commit everything and push to GitHub.
3. Run `scripts/scan_history.py` (above) and read its report. Only if it is clean: make the repository
   public and turn on GitHub Pages (Settings > Pages > Source: **GitHub Actions**; the workflow
   `.github/workflows/pages.yml` publishes `site/` on every push to `main`, owner review of d34fa93).
4. Open the live link on a phone that has never opened it, and check that a prepared field loads.
5. Paste the live link and repository link into the Space Apps project page and submit.

After submission, change nothing until the Global Winners are announced in January.

## Out of scope

A backend or database, **except one Firebase Realtime Database (free Spark plan) for live probe readings
only** (owner, 2026-11-12; build step 10b): nothing else is stored there, and nothing else on the site
depends on it. User accounts; any other live API call from the site; yield in tonnes; disease
diagnosis; any claim that the tool replaces an agronomist.
