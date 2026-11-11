# DATA_AUDIT.md

Updated 2026-11-11, end of build step 2. Regenerate the data-level parts after each fetch step.

## Status

| Dataset | Downloaded into the pipeline? | Data card |
| --- | --- | --- |
| NASA POWER | **Yes**: 2001-01-01 to 2025-12-31, 9,131 days | `data/cards/demo/power.json` |
| NOAA GHCN-Daily, Kathmandu Airport (validation only) | **Yes**: 2001-01-01 to 2025-08-24 | `data/cards/demo/ghcn_NP000444540.json` |
| GPM IMERG, HLS, MODIS, SMAP, NASADEM, ECOSTRESS, GRACE | No: Earthdata login missing (`~/.netrc`) | — |
| SoilGrids, NEX-GDDP-CMIP6 | No: not their build step yet (no login needed) | — |

Metadata items (names, versions, documented units, fills, scale factors, valid ranges) were checked
on 2026-11-11 against NASA CMR (concept IDs given), the provider APIs and the GHCN-Daily readme.

Status words: **VERIFIED** (source given) · **FOUND** (measured in our downloaded data) · **NOT YET
POSSIBLE** · **TODO-VERIFY** · **DECIDED** (owner decision, with its date).

### Blockers still open

| # | Blocker | Blocks | Fix |
| --- | --- | --- | --- |
| B2 | No field outline: `config/fields/demo.yaml` has `polygon: null` | pixel counts and plots for gridded data, sections | Owner supplies four corners |
| B3 | No Earthdata login (`~/.netrc` absent) | GPM (and so step 5's twin rain under D6), HLS, MODIS, SMAP, NASADEM, ECOSTRESS, GRACE | Owner creates `~/.netrc` |

## Owner decisions applied (2026-11-11)

D1 IMERG Final through 2025-09-30, then Late (GPM_3IMERGDL) for Oct-Dec 2025, recorded in the card's
`segments` · D2 each guard uses the product's documented valid range; the rule-12 range only warns ·
D3 NASADEM_HGT · D4 ECOSTRESS V003, V002 only for dates V003 lacks · D5 GRACE CRI
(C3195527175-POCLOUD) · D6 IMERG drives the twin's rain; POWER gives temperature, humidity, wind,
sunshine; IMERG days are UTC, POWER days local solar time · D7 `diary.groundwater` from GRACE,
used in the water score.

---

## 1. Per-dataset audit

### 1.1 NASA POWER (model-based): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Product, version | POWER Daily API **v2.10.3**, point endpoint, community AG. Sources named in every response header: MERRA2, SYN1DEG, POWER | VERIFIED: API header |
| Role (D6) | Temperature, humidity, wind and sunshine for the twin. PRECTOTCORR is for cross-checks only | DECIDED |
| Files | `data/raw/power/demo/<start>_<end>.json` (25, one per year) → `data/clean/demo/power.parquet` | FOUND |
| Variables, units in → out | T2M_MAX C → `tmax_c`; T2M_MIN C → `tmin_c`; RH2M % → `rh_pct`; WS2M m/s → `ws2m_ms`; ALLSKY_SFC_SW_DWN MJ/m^2/day → `rs_mj_m2_day`; PRECTOTCORR mm/day → `rain_mm`. The fetch stops if the API ever reports another unit | VERIFIED: API `parameters` block, every response |
| Scale factor | none | VERIFIED |
| Fill values | documented -999.0; **found and removed: 0** in every column | FOUND |
| Quality flags | none in the response, so none applied; **records dropped: 0** | FOUND; whether POWER offers flags elsewhere is TODO-VERIFY |
| Range guards | all passed; **0 warnings**. Wind and sunshine checked as non-negative | FOUND |
| Date range | **2001-01-01 to 2025-12-31, 9,131 days, no gaps, no repeats** | FOUND |
| Time zone | **LST** (local solar time), from the header of every response | VERIFIED |
| Pixels over field | **1** (the point API returns one grid cell). Cell elevation 1269.39 m. Cell size per CLAUDE.md is 0.5 x 0.625 deg (about 55 x 62 km); the solar part is SYN1DEG | Count FOUND; resolutions TODO-VERIFY |
| Plot | A point product has no pixel grid to draw in our data; plotting the cell outline needs POWER's grid edges | TODO-VERIFY grid edges |
| Known problem 1 | PRECTOTCORR yearly totals for 2001 to 2003 (621, 525, 534 mm) are about half of every later year. The station has almost no records then, so it cannot settle this | TODO-VERIFY; one more reason for D6 |
| Known problem 2 | Implausible daily rain: **2025-03-01 233.7 mm** (station 3.8 mm, dry season); 2024-06-26 114.3 mm (station 4.3 mm). The real flood of 2024-09-27/28 (station 97.0 + 194.1 mm) appears as only 76.3 + 93.3 mm. All inside the 0 to 500 mm guard, so not caught by it. Not removed: PRECTOTCORR is not a model input (D6) | FOUND by cross-check; cause TODO-VERIFY |

### 1.2 GPM IMERG: NOT DOWNLOADED (login)

| Item | Value | Status |
| --- | --- | --- |
| Products (D1) | `GPM_3IMERGDF` V07 (`C2723754864-GES_DISC`) through **2025-09-30** (its last granule), then `GPM_3IMERGDL` V07 (Late) for 2025-10-01 to 2025-12-31, recorded in the card's `segments` | VERIFIED: CMR; DECIDED |
| Variable | `precipitation`, float32, mm/day, no scale factor, fill -9999.9 (float32; the guard matches both spellings) | VERIFIED: UMM-Var `V3156651215-GES_DISC` |
| Quality flags | candidates `precipitation_cnt`, `precipitation_cnt_cond` | TODO-VERIFY meaning in V07 docs |
| Time zone | daily files cover the **UTC day** (05:45 to 05:45 Nepal time) | TODO-VERIFY in the V07 documentation (owner's note) |
| Fills found, records dropped, pixels, plot | — | NOT YET POSSIBLE (B2, B3) |

### 1.3 HLS Vegetation Indices: NOT DOWNLOADED (login)

| Item | Value | Status |
| --- | --- | --- |
| Products | `HLSL30_VI` v2.0 (from 2013-04-11), `HLSS30_VI` v2.0 (from 2015-11-28) | VERIFIED: CMR |
| NDVI | int16, scale 0.0001, fill -9999, valid -1 to 1 (CMR lists it after scaling) | VERIFIED: UMM-Var |
| Cloud mask | **list one granule's layers to find it** (owner's note); bit meanings from the HLS VI user guide | TODO-VERIFY |
| Pixels | 30 m: a 10 m section is one-ninth of a pixel | count NOT YET POSSIBLE (B2) |

### 1.4 MODIS MOD13Q1 v061: NOT DOWNLOADED (login)

| Item | Value | Status |
| --- | --- | --- |
| NDVI | `250m 16 days NDVI`: int16, scale 0.0001, fill -3000, valid raw -2000 to 10000 (that is, -0.2 to 1.0) | VERIFIED: UMM-Var `V3143914093-LPCLOUD` |
| Quality and date layers | expected `250m 16 days pixel reliability`, `250m 16 days VI Quality`, `250m 16 days composite day of the year` (owner's note) | TODO-VERIFY by listing a file's layers |

### 1.5 SMAP: NOT DOWNLOADED (login)

| Item | Value | Status |
| --- | --- | --- |
| Products | `SPL3SMP_E` v006, `SPL4SMGP` v008, both from 2015-03-31 | VERIFIED: CMR |
| L3 soil moisture | cm3/cm3, fill -9999.0, valid 0.02 to 0.50 | VERIFIED: UMM-Var |
| L4 soil moisture | m3 m-3, fill -9999.0, **valid 0 to 0.9**. Under D2 this is the hard limit, and values above 0.6 are logged warnings | VERIFIED; DECIDED |
| L3 quality | `retrieval_qual_flag`: **which bit means "recommended quality"** (owner's note) | TODO-VERIFY |

### 1.6 SoilGrids 2.0 (model-based map): NOT YET (step 4)

`wv0033` and `wv1500` exist as layers (VERIFIED: `/properties/layers`). Every conversion factor and
unit is **TODO-VERIFY**.

### 1.7 NASADEM_HGT v001 (D3): NOT DOWNLOADED (login)

`DEM` int16, meters (`C2763264762-LPCLOUD`, UMM-Var `V3219987629-LPCLOUD`); no fill value listed.
Acquired February 2000. VERIFIED.

### 1.8 ECOSTRESS V003, V002 fallback (D4): NOT DOWNLOADED (login)

`ECO_L2T_LSTE` V003 `C3998139651-LPCLOUD` (V002 `C2076090826-LPCLOUD`); `ECO_L4T_ESI` v003
`C4057232495-LPCLOUD` (V002 `C2076104650-LPCLOUD`). Variables, units, scale, fill, flags and time
stamps: **TODO-VERIFY**.

### 1.9 NEX-GDDP-CMIP6: NOT YET (step 9)

Not in CMR; public bucket `nex-gddp-cmip6` lists 35 models (VERIFIED). Version, every unit,
calendars and wind height: **TODO-VERIFY**.

### 1.10 GRACE/GRACE-FO (D5, D7): NOT DOWNLOADED (login)

`TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`, version RL06.3Mv04, `C3195527175-POCLOUD`, from
2002-04 (VERIFIED). It now feeds `diary.groundwater` and the water score (D7). Variable, unit, grid
and the gap between missions: **TODO-VERIFY**.

### 1.11 NOAA GHCN-Daily, Kathmandu Airport (validation only): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Station | `NP000444540` KATHMANDU AIRPORT, 27.700 N 85.367 E, 1337 m, about 7 km from the demo point | VERIFIED: `ghcnd-stations.txt` |
| Product, version | GHCN-Daily **Version 3.35**, by_station CSV | VERIFIED: readme line 2 |
| Units in → out | PRCP **tenths of mm** → `rain_mm`; TMAX, TMIN **tenths of degrees C** → `tmax_c`, `tmin_c` (scale 0.1) | **VERIFIED**: readme lines 149 to 153 (owner's note confirmed) |
| Fill | -9999 = missing; **found: 0** (missing days are simply absent rows) | FOUND |
| Quality flags | any non-blank Q-FLAG dropped: **PRCP 0, TMAX 1, TMIN 0** | FOUND |
| Date range | **2001-01-01 to 2025-08-24** (the record stops there) | FOUND |
| Time zone | station observation day. **0 of 12,147 records give an observation time**, so the day boundary is unknown | FOUND; TODO-VERIFY |
| Rain records per year | 2001: 38, 2002: 2, 2003: 39, 2004: 290, 2005: 297, 2006: 165, 2007: 161, 2008: 222, 2009: 164, 2010: 77, 2011: 54, 2012: 155, 2013: 0, 2014: 0, 2015: 362, 2016: 356, 2017: 354, 2018: 265, 2019: 339, 2020: 217, 2021: 355, 2022: 354, 2023: 312, 2024: 233, 2025: 225 | FOUND |
| Comparison rule (owner) | monthly totals, only years with at least 330 records: 2015, 2016, 2017, 2019, 2021, 2022 | applied |

---

## 2. Field outline over pixels

**NOT YET POSSIBLE** for every gridded dataset: there is no field polygon (B2) and no gridded data
(B3). POWER and GHCN are points, so they have no pixels to count beyond the single cell and the
single station.

## 3. Cross-checks

| Check | Result | Status |
| --- | --- | --- |
| POWER vs GHCN rain | **49 complete months in 2015, 2016, 2017, 2019, 2021, 2022: POWER 21.3% drier, r = 0.93, mean absolute error 46.8 mm per month** | RUN (`data/checks/demo/crosscheck_power_ghcn_NP000444540.json`) |
| POWER vs GHCN January Tmin | 205 shared days: station 3.7 C, POWER 7.5 C, **POWER +3.8 C** | RUN |
| POWER vs GHCN May-June Tmax | 829 shared days: station 29.4 C, POWER 29.5 C, **POWER +0.08 C** | RUN |
| GPM vs POWER vs GHCN rain | — | NOT YET POSSIBLE (B3) |
| MODIS vs HLS NDVI, 2013 on | — | NOT YET POSSIBLE (B2, B3) |

## 4. Switch-off test

**Result if run today:** the only export is still MOCK, so switching off any dataset changes nothing,
and **every dataset is flagged**. POWER and GHCN are now real, but feed only checks, not exports.

What each dataset must change once the pipeline exists (the pass criteria):

| Dataset | Export keys that must change when it is switched off |
| --- | --- |
| NASA POWER | replay (via ET0 and temperature), plans.score, future, diary.months (heat, frost) |
| GPM IMERG (D6: the twin's rain) | replay (harvest, dry_days, event), diary.shift_days, diary.months.rain, plans.score |
| HLS + MODIS | diary.bare_days, diary.guess, diary.months.cover, plans.score.cover |
| SMAP | field.sections[].sure (via P0 and Q) |
| SoilGrids | replay.dry_days and harvest (via TAW), plans.score.soil_kept (K factor) |
| NASADEM | sections, plans.score.soil_kept (LS), frost flags |
| ECOSTRESS | section status (optional layer) |
| NEX-GDDP-CMIP6 | future (harvest, harvest_low, harvest_high) |
| GRACE/GRACE-FO (D7) | diary.groundwater, plans.score.water |
| GHCN | none by design (validation only) |

## 5. Data cards

Written: `data/cards/demo/power.json`, `data/cards/demo/ghcn_NP000444540.json`. Each has every
rule-12 field plus `range_warnings`; POWER's also notes the D6 role.

## 6. TODO-VERIFY (open)

1. POWER: per-value quality flags anywhere in its docs; MERRA-2 and SYN1DEG cell sizes and edges; the
   cause of the 2001 to 2003 low rain totals.
2. IMERG: daily files cover the UTC day (V07 documentation); meaning of the count fields.
3. HLS: list one granule's layers to find the cloud mask; its bits.
4. MODIS: confirm `250m 16 days pixel reliability`, `250m 16 days VI Quality`, `250m 16 days composite
   day of the year` by listing a file's layers.
5. SMAP L3: which bit of `retrieval_qual_flag` means "recommended quality"; L4 daily day boundary.
6. SoilGrids: every conversion factor and unit.
7. ECOSTRESS V003: variables, units, scale, fill, quality flags, time stamps.
8. NEX-GDDP-CMIP6: version, units, calendars, wind height.
9. GRACE: variable, unit, grid, gap between missions.
10. GHCN: the station's observation-day boundary (no OBS-TIME in the file).
11. My reading of the switch-off test (section 4).

Closed today: GHCN units (readme v3.35); GRACE product name; IMERG coverage gap (D1); soil-moisture
range conflict (D2).
