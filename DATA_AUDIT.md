# DATA_AUDIT.md

Updated 2026-11-12 (later): placeholder field, fetch box and the first Earthdata fetches (build step 5,
parts without GPM). Regenerate the data-level parts after each fetch step.

**Field (owner, 2026-11-12):** 27.67 N, 85.43 E is Bhaktapur's old city, so it is only the centre of the
fetch box `[85.379227, 27.625034, 85.480773, 27.714966]` (5 km N, S, E, W). The field is a PLACEHOLDER
60 m square at **27.690767 N, 85.441792 E**: the owner's candidate 1 (`pipeline/fetch/placeholder.py`), moved 25 m north away from the Kasan River strip (section 1.14). It replaced a 100 m square at 27.6785 N, 85.427417 E, which was a construction plot. Datasets fetched before
this (GHCN, FAOSTAT) are not location-bound; POWER was re-fetched at the placeholder (same grid cell,
identical values).

## Status

| Dataset | Downloaded into the pipeline? | Data card |
| --- | --- | --- |
| NASA POWER | **Yes**, re-fetched at the placeholder 2026-11-12: 2001-01-01 to 2025-12-31, 9,131 days. The whole box lies in one 0.5 x 0.625 deg cell | `data/cards/demo/power.json` |
| NOAA GHCN-Daily, Kathmandu Airport (validation; reference for correction A) | **Yes**: 2001-01-01 to 2025-08-24 | `data/cards/demo/ghcn_NP000444540.json` |
| FAOSTAT QCL, Nepal yields (validation 4.3 only) | **Yes**: 2001 to 2024, 72 rows | `data/cards/demo/faostat_yields.json` |
| Twin weather (derived: corrected POWER + rain merge + ET0) | **Built**: 2001-01-01 to 2025-12-31 | `data/cards/demo/weather.json` |
| ESA WorldCover 2021 (placeholder field only) | **Yes**: box window, 1,080 x 1,224 pixels at 10 m | `data/cards/demo/worldcover.json` |
| NASADEM | **Yes**: box, elevation and slope; field 1,325.0 m, slope 1.6 deg (4 pixels) | `data/cards/demo/nasadem.json` |
| GRACE/GRACE-FO mascon CRI | **Yes**: 261 months, 2002-04 to 2026-09, the 0.5 deg cell holding the field (one 3 deg mascon) | `data/cards/demo/grace.json` |
| GPM IMERG | **Downloading** (EULA accepted by the owner, 2026-11-12): daily box subsets; the run was cut off at 2009-03-03 when VS Code closed, resumed from the cache at 13:02, and ended with **7,558 of 9,131 days**: every day from 2021-09-11 to 2025-12-31 (1,573) failed while the laptop's internet was down (about 14:10-14:31; both GES DISC hosts unreachable, and AppEEARS failed to resolve at the same time). The retry (15:59, 2 workers) fetched them all: **9,131 of 9,131 days** (Final 9,039 to 2025-09-30, Late 92), 0 failed, 0 fills in the field's cell; `gpm.parquet`, the card and the weather table rebuilt from the cache at 16:31. Field-cell rain averages 2,162 mm/yr (2009 lowest 1,436; 2020 highest 3,120). **Well above the station from 2017:** in the station's well-recorded years GPM is 1,505 / 1,736 / 2,635 / 2,399 / 2,969 / 2,644 mm (2015, 2016, 2017, 2019, 2021, 2022) against the station's 1,495 / 1,460 / 1,146 / 1,559 / 1,737 / 1,756 and POWER's 1,205 / 1,155 / 1,077 / 1,182 / 1,562 / 1,242; spike flags rise from 9 to 170, mostly 'gpm disagrees with the other two'. Cause not yet known (IMERG over the valley, or the synoptic-derived station undercounting): VALIDATION 3.9 | after download (`data/cards/demo/gpm.json`) |
| MODIS MOD13Q1, SMAP L3 and L4 | **MODIS downloaded** (one netCDF-4 for the box, 2001-2025). **SMAP requested**: 13 AppEEARS tasks (2 L3, 11 L4 by year) still processing on NASA's side at 13:05; a poller downloads each when it is ready | `data/cards/demo/modis.json` (576 composites, 2000-12-18 to 2025-12-19; the field touches 2 MODIS cells but holds no cell centre); SMAP after download |
| HLS-VI (L30, S30) | **Yes**: all 1,471 granules (L30 336, S30 1,135), box windows of NDVI + Fmask, tile T45RUL; the retry finished with 0 failures (2026-11-12, 12:39). Monthly clear-sky composites built (`hls_monthly_ndvi.npz`) | `data/cards/demo/hls_l30.json`, `hls_s30.json` (from the cache, REVIEW_NOTES L7: 4 pixel centres in the field, 9 touching; no NDVI outside -1..1; 0 windows outside their granule, L6) |
| ECOSTRESS LSTE, ESI | **Yes (raw windows)**: LSTE 769 (V003 27, V002 742), ESI 310 (V003 3, V002 307); the retry finished with 0 failures (2026-11-12, 12:41). Cleaning is step 8 | `data/cards/demo/eco_lste.json`, `eco_esi.json` (raw, from the cache, L7); cleaned cards at step 8 |
| ISRIC SoilGrids 2.0 | **Box downloaded through the WCS** (36 maps: 6 properties x 6 depths, 45 x 38 cells of about 250 m; the REST point service was down). **Only 947 of 1,710 box cells have a prediction** (763 are 0 in all 36 maps, none in only some): SoilGrids leaves most of the Kathmandu valley floor empty; values sit in the surrounding hills. **The twin's soil table is now the nearest cell where all 36 maps are valid: 859 m south-east of the field** (27.6854 N, 85.4481 E), within the owner's 3 km (REVIEW_NOTES M5); rebuilt offline 2026-11-12. The REST module now writes `soilgrids_rest.*` only | `data/cards/demo/soilgrids.json` |
| NEX-GDDP-CMIP6 | No: not its build step yet (no login needed) | — |

Metadata items (names, versions, documented units, fills, scale factors, valid ranges) were checked
on 2026-11-11 against NASA CMR (concept IDs given), the provider APIs and the GHCN-Daily readme.

Status words: **VERIFIED** (source given) · **FOUND** (measured in our downloaded data) · **NOT YET
POSSIBLE** · **TODO-VERIFY** · **DECIDED** (owner decision, with its date).

### Blockers still open

| # | Blocker | Blocks | Fix |
| --- | --- | --- | --- |
| B2 | Real field unknown: a **placeholder** polygon stands in (WorldCover cropland) | everything field-specific is labelled placeholder | Owner supplies four corners |
| ~~B3~~ | ~~No Earthdata login~~ | **Closed 2026-11-12**: `~/.netrc` present (mode 600); LP DAAC, PO.DAAC and AppEEARS work | — |
| B5 | **SoilGrids has no prediction over most of the valley floor** (947 of 1,710 box cells have values) | the soil table for any valley field | Owner (2026-11-12, REVIEW_NOTES M5): try FAO HWSD v2, else the nearest SoilGrids cell within 3 km with a caveat. **HWSD v2 checked 2026-11-12 (web, nothing downloaded):** licence **CC BY-NC-SA 3.0 IGO** ("may be copied, redistributed and adapted for non-commercial purposes ... If the work is adapted, then it must be licensed under the same or equivalent Creative Commons license"; FAO & IIASA 2023, doi:10.4060/cc3823en); raster `HWSD2_RASTER.zip` (22 MB, 1 km, readable with rasterio); attributes only as MS Access .mdb (needs mdbtools or a new package) or ISRIC's third-party SQLite conversion (67 MB, standard-library sqlite3); per-layer sand, silt, clay, bulk density, organic carbon, but no 33/1500 kPa water contents (AWC is one texture-class lookup per soil unit); FAO says it is least reliable in parts of South Asia and advises national databases for national studies. **Not used (owner, 2026-11-12, batch item 21)**: ShareAlike/non-commercial licence, 1 km cells, no water contents at 33 or 1500 kPa. The nearest SoilGrids cell with a prediction is used, with its distance and the caveat in the card (`rules.yaml` soilgrids.nearest_cell_max_m) |
| ~~B4~~ | ~~GES DISC EULA not accepted on the Earthdata account~~ | **Closed 2026-11-12**: the owner accepted it; GPM is downloading | — |

## Owner decisions applied (2026-11-11)

D1 IMERG Final through 2025-09-30, then Late (GPM_3IMERGDL) for Oct-Dec 2025, recorded in the card's
`segments` · D2 each guard uses the product's documented valid range; the rule-12 range only warns ·
D3 NASADEM_HGT · D4 ECOSTRESS V003, V002 only for dates V003 lacks · D5 GRACE CRI
(C3195527175-POCLOUD) · D6 IMERG drives the twin's rain; POWER gives temperature, humidity, wind,
sunshine; IMERG days are UTC, POWER days local solar time · D7 `diary.groundwater` from GRACE,
used in the water score · A station correction of POWER Tmin/Tmax (held-out tested) before ET0 and
frost · B cross-source rain spike flags in the cards · C day-alignment test · D POWER rain is fill-in
only, never 2001-2003 · E sourced known-events list (`config/known_events.yaml`) · F FAOSTAT yields ·
G official citations (CREDITS.md) · H full-history secret scan before going public.

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
| Pixels over field | **1** (the point API returns one grid cell). Cell elevation 1269.39 m (recorded in the card's `location`) | FOUND |
| Resolution | Meteorology "½° latitude by ⅝° longitude grid from GMAO MERRA-2" (about 55 x 62 km), with GEOS-IT for the latest 1 to 3 months until MERRA-2 overwrites it; solar "1° latitude by 1° longitude" from CERES SYN1deg Ed. 4.2 (2001 on), FLASHFlux 4A for the latest 3 to 4 months. POWER warns that series spanning a source change are not recommended for climate trends | **VERIFIED**: power.larc.nasa.gov/docs/methodology (sources_meteorology, sources_fluxes) |
| PRECTOTCORR | "The average MERRA-2 bias corrected total precipitation at the surface of the earth" (POWER parameter manager); GEOS-IT for recent months lacks the gauge normalization | VERIFIED; the correction's gauge source is in Reichle et al. 2017 (not opened, TODO-VERIFY) |
| Plot | A point product has no pixel grid to draw in our data; plotting the cell outline needs POWER's grid edges | TODO-VERIFY grid edges |
| Known problem 1 | PRECTOTCORR yearly totals for 2001 to 2003 (621, 525, 534 mm) are about half of every later year. The station has almost no records then, and POWER documents no source change in those years | Cause TODO-VERIFY. **Decision D: never used to fill GPM gaps** |
| Known problem 2 | Implausible daily rain, e.g. **2025-03-01 233.7 mm** (station 3.8 mm, dry season) | **Decision B: flagged** (section 3); not removed |
| Temperature bias | Against the station on shared days: Tmin too warm (January +3.8 C; monthly offsets +0.3 to +4.2 C), Tmax too cool from July to December (offsets down to -4.2 C in September) | FOUND; **decision A correction** applied in the twin's weather (1.13) |

### 1.2 GPM IMERG: DOWNLOADING (GES DISC EULA accepted 2026-11-12; daily box subsets, 9,131 days)

| Item | Value | Status |
| --- | --- | --- |
| Products (D1) | `GPM_3IMERGDF` V07 (`C2723754864-GES_DISC`) through **2025-09-30** (its last granule), then `GPM_3IMERGDL` V07 (Late) for 2025-10-01 to 2025-12-31, recorded in the card's `segments` | VERIFIED: CMR; DECIDED |
| Variable | `precipitation`, float32, mm/day, no scale factor, fill -9999.9 (float32; the guard matches both spellings) | VERIFIED: UMM-Var `V3156651215-GES_DISC` |
| Quality flags | `precipitation_cnt` = number of valid half-hourly values in the day, 'only given to gauge the significance of the daily rates'; count-0 cells are fill (GPM_3IMERGDF V07 abstract). Not a quality flag, so none applied. `precipitation_cnt_cond`: meaning not found | PARTLY VERIFIED (verified 2026-11-12); `precipitation_cnt_cond` TODO-VERIFY |
| Time zone | UTC days (00:00-24:00 UTC = 05:45-05:45 Nepal time); each file's BeginTime 00:00:00.000Z and EndTime 23:59:59.999Z support it | **VERIFIED**: IMERG V07 Technical Documentation (13 July 2023) p. 40, 'The time zone for these data sets is Universal Coordinated Time'; the daily file is the mean of the 48 UTC half-hours of the data day (GPM_3IMERGDF V07 abstract) |
| Fills found, records dropped, pixels, plot | — | NOT YET POSSIBLE: waiting for the download to finish, then `python -m pipeline.fetch.gpm --field demo --from-cache`. The card now counts real fills in the field's cell, failed days, days without a granule and days not cached separately per segment, records the dropped days and the date range actually covered, prints the raw attributes (units mm/day; scale_factor, add_offset, valid_range ABSENT; _FillValue -9999.9), and the run exits non-zero if any day is missing (REVIEW_NOTES M2) |

### 1.3 HLS Vegetation Indices: DOWNLOADED (box windows; 1,404 of 1,471 granules, tile T45RUL)

| Item | Value | Status |
| --- | --- | --- |
| Products | `HLSL30_VI` v2.0 (from 2013-04-11), `HLSS30_VI` v2.0 (from 2015-11-28) | VERIFIED: CMR |
| NDVI | int16, scale 0.0001, **fill -19999** in the files (UMM-Var said -9999), valid -1 to 1 after scaling | **VERIFIED**: file tags (`_FillValue -19999`, `scale_factor 0.0001`) |
| Cloud mask | **`Fmask`** (uint8, fill 255). Bits from each file's own `Fmask description` tag: 7-6 aerosol, 5 water, 4 snow/ice, 3 cloud shadow, 2 adjacent to cloud, 1 cloud, 0 cirrus. Clear = bits 0-5 all zero (`pipeline/diary/ndvi.py`); water (bit 5) is kept as not clear after a check (REVIEW_NOTES M12): no water-flagged observation over the field in June-August 2013-2025 (0 of 2,916), and only 0.001-0.004% of clear observations over the box's cropland in those months | **VERIFIED**: file tag |
| Pixels | 30 m: a 10 m section is one-ninth of a pixel | count NOT YET POSSIBLE (B2) |

### 1.4 MODIS MOD13Q1 v061: REQUESTED (AppEEARS task for the box, 2001-2025)

| Item | Value | Status |
| --- | --- | --- |
| NDVI | `250m 16 days NDVI`: int16, scale 0.0001, fill -3000, valid raw -2000 to 10000 (that is, -0.2 to 1.0) | VERIFIED: UMM-Var `V3143914093-LPCLOUD` |
| Quality and date layers | `_250m_16_days_pixel_reliability` (0 to 3, fill -1), `_250m_16_days_VI_Quality` (fill 65535), `_250m_16_days_composite_day_of_the_year` (1 to 366, fill -1) | **VERIFIED**: AppEEARS product API |

### 1.5 SMAP: REQUESTED (AppEEARS: L3 AM and PM, L4 one task per year)

| Item | Value | Status |
| --- | --- | --- |
| Products | `SPL3SMP_E` v006, `SPL4SMGP` v008, both from 2015-03-31 | VERIFIED: CMR |
| L3 soil moisture | cm3/cm3, fill -9999.0, valid 0.02 to 0.50 | VERIFIED: UMM-Var |
| L4 soil moisture | m3 m-3, fill -9999.0, **valid 0 to 0.9**. Under D2 this is the hard limit, and values above 0.6 are logged warnings | VERIFIED; DECIDED |
| L3 quality | `retrieval_qual_flag` bit 0 = Recommended Quality (0 = recommended, 1 = not); keep values 0 or 8 ("A retrieval_qual_flag value of either 0 or 8 indicates high-quality retrievals"; 8 = only the freeze/thaw retrieval failed) | **VERIFIED**: NSIDC SPL3SMP_E v006 User Guide, Table 6 (p. 10) and p. 13 |

### 1.6 ISRIC SoilGrids 2.0 (model-based map, CC-BY 4.0): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Access | WCS box maps (maps.isric.org; the REST service was down for the box). `soilgrids_wcs.py` writes the twin's table; the REST module (`soilgrids.py`) writes `soilgrids_rest.*` only, and a partly null REST answer no longer counts as a prediction (REVIEW_NOTES M5) | FOUND |
| The field's own cell | **no prediction** (row 10, col 27: 0 in all 36 maps). The maps declare no nodata, so a cell counts only where all 36 maps are valid; 0 is never read as a real 0% (M5). A point outside the maps raises. Reason for the valley gap (e.g. a land-cover mask) TODO-VERIFY | FOUND |
| Cell used | nearest cell where all 36 maps are valid: **859 m south-east** of the field (27.6854 N, 85.4481 E), within 3,000 m (owner, 2026-11-12, M5; was 1 km). Distance and the caveat "soil from the nearest SoilGrids cell with a prediction, not the field's own" in the card | FOUND; DECIDED |
| Units and factors | the maps carry no unit tags or nodata; the conversion table (wv0033, wv1500 /1000 → m3/m3 via 10^-3 cm3/cm3; sand, clay g/kg /10 → %; soc dg/kg /10 → g/kg; bdod cg/cm3 /100 → kg/dm3) is checked on real data: the REST answers' `unit_measure` blocks match it, and the WCS values equal the cached REST values in 36 of 36 cases at the same point. ISRIC's 'SoilGrids layers' table (docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html, updated 2026-09-02) gives the same factors | **VERIFIED** (REST unit blocks, 36/36 match, and the ISRIC table, verified 2026-11-12) |
| Values used | 0-5 / 5-15 / 15-30 / 30-60 / 60-100 / 100-200 cm. Sand 33.6 / 33.0 / 31.0 / 28.8 / 26.6 / 26.2%; clay 20.6 / 21.4 / 25.2 / 29.8 / 33.0 / 35.5%; SOC 25.0 / 14.8 / 12.7 / 6.8 / 5.3 / 5.0 g/kg; bulk density 1.23 / 1.25 / 1.29 / 1.31 / 1.33 / 1.33 kg/dm3; field capacity 0.333 / 0.331 / 0.326 / 0.322 / 0.322 / 0.331; wilting point 0.148 / 0.152 / 0.159 / 0.173 / 0.191 / 0.202 m3/m3 | FOUND |
| Guards | field capacity above wilting point at every depth; sand and clay 0 to 100%, their sum under 100%; soil moisture within rule 12; 0 warnings | FOUND |
| Hydrologic soil group | **C**, from NEH 630 Ch. 7 texture guidance (20 to 40% clay, under 50% sand): clay 20.6-35.5%, sand 26.2-33.6% at the new cell; the top layer's 20.6% clay is close to the 20% edge; Ksat unknown | sourced (rules.yaml) |
| TAW | 96.9 mm (Zr 0.6 m), 149.3 mm (1.0 m), 213.8 mm (1.5 m) at the new cell; the old REST cell near the old-city point gave 91.3, 140.9 and 194.4 mm (the step-4 and dry-run numbers before 2026-11-12 used those) | FOUND |

### 1.7 NASADEM_HGT v001 (D3): DOWNLOADED (box)

| Item | Value | Status |
| --- | --- | --- |
| Granule | one tile `n27e085` (zip 16.2 MB, `.hgt` read inside the zip) | FOUND |
| Raw attributes | SRTMHGT, EPSG:4326, 1/3600 deg, int16, nodata -32768; AREA_OR_POINT Point | VERIFIED: file |
| Voids | 0 in the box (the product is void-filled; the reader stops on any void) | FOUND |
| Field | elevation **1,325.0 m** (1,324 to 1,326) and slope **1.6 deg** mean (1.0 to 2.5; Horn 1981) over 4 pixels (27.4 x 30.9 m), for the 60 m square at 27.690767 N (the first placeholder gave 1,313.2 m and 2.2 deg over 16 pixels) | FOUND |
| Use | field elevation now feeds ET0 (POWER's cell is 1,269.4 m; mean ET0 changed from 3.5045 to 3.5071 mm/day, then 3.5076 at the 60 m square's 1,325.0 m); slope is for revisiting the curve numbers (owner): 1.6 deg is about 2.8 % (the first placeholder's 2.2 deg was about 4 %), gentle, but terraces are likely in the hills | FOUND; curve numbers kept for this 1.6 deg valley-floor placeholder, revisit closed (owner, 2026-11-12, batch item 20); revisit for a terraced hill field |
| Heights | above the EGM96 geoid | **VERIFIED**: NASADEM User Guide (Jan 2020) Section 3 ('the integer heights in the merged void-free DEM files are relative to the EGM96 geoid') and Table 1 |

### 1.8 ECOSTRESS V003, V002 fallback (D4): DOWNLOADED (raw box windows; LSTE 741, ESI 307)

`ECO_L2T_LSTE` V003 `C3998139651-LPCLOUD` (V002 `C2076090826-LPCLOUD`); `ECO_L4T_ESI` V003
`C4057232495-LPCLOUD` (V002 `C2076104650-LPCLOUD`). Tile 45RUL. Over the box V003 has only **27 LSTE and
3 ESI** granules, so V002 fills the other overpasses (D4; ESI V002: 307). Assets read: `LST`, `QC`, `cloud`
(LSTE) and `ESI`, `cloud` (ESI); units and fills from the AppEEARS product API: LST Kelvin, NaN fill;
cloud 1 = cloud, fill 255 (V003 only: V002 QC and cloud declare no nodata and read 0 where LST or ESI is missing, on
5.6 million QC pixels and 6.1 / 2.8 million LSTE / ESI cloud pixels, so **the diary must mask by LST or ESI, never by QC or
cloud == 0**; owner-approved 2026-11-12, batch item 25: `cogwindows.layers_where_valid` keeps QC and cloud only beside a valid LST or ESI, `rules.yaml` ecostress.qc_needs_valid_value, tested on a cached V002 window). Cards `eco_lste.json` (742 V002 + 27 V003 granules) and `eco_esi.json` (310) from the cache (L7): 16 LSTE
granules (31,066 pixels) hold LST outside -30..50 C before QC is applied. Boundless fill (L6): 0 windows outside their
granule by geometry (the windows sit 33-50 km inside tile T45RUL's north and west edges; tile size 1568 px TODO-VERIFY).
QC bits **VERIFIED** (ECOL2 User Guide V3, Table 6): bits 1&0 00 = produced, 01 = produced but degraded, 11 = not produced; 65,535 (25 V002 granules) sets every bit, i.e. "Pixel not produced" and "Missing/bad L1B data". LST is float32 Kelvin, cloud 1 = cloud, ESI a 0-1 ratio (Tiled User Guide V2, Tables 5 and 11). Time stamps in UTC: **TODO-VERIFY** (none of the guides states it).

### 1.9 NEX-GDDP-CMIP6: NOT YET (step 9)

Not in CMR; public bucket `nex-gddp-cmip6` lists 35 models (VERIFIED). Units **VERIFIED** (Tech Note v2, 31 May 2025,
p. 3): pr kg m-2 s-1, tasmax/tasmin K, hurs %, rsds W m-2, sfcWind m s-1. sfcWind is nominally 10 m (CMIP6 day table:
height10m), so u2 needs FAO-56 eq. 47. The bucket holds v1.0 and `_v2.0` files side by side: step 9 chooses v2.0 and
records it. Calendars: per model, read from each file's `time:calendar` (**TODO-VERIFY** at fetch time).

### 1.10 GRACE/GRACE-FO (D5, D7): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| File | `GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc` (44.2 MB, one global file) | FOUND |
| Variables | `lwe_thickness` cm, fill -99999, valid -2305.0 to 1273.7 (the hard limit, D2); `uncertainty` cm, 1-sigma per 3-degree mascon | VERIFIED: file attributes |
| Cell | lat 27.5-28.0, lon 85.0-85.5, mascon 1213, land mask 1 | FOUND |
| Series | 261 monthly solutions, 2002-04 to 2026-09; lwe -73.3 to +37.4 cm; GRACE/GRACE-FO gap months are absent, not filled | FOUND |
| Resolution | 0.5 deg grid of 3-degree equal-area mascons: regional context only (file attribute) | VERIFIED |
| CRI scale factor (owner, 2026-11-12, REVIEW_NOTES M4) | 1.4945 at the cell, recorded in the card, **not applied**: it is CLM-based (land hydrology; file attribute 'based on CLM data from 2002-2009'), the mascon includes glaciers and snow, and no source was found for applying it here. **Unscaled OLS trend -2.56 cm/yr** (261 months, 2002-04 to 2026-09; 2002-2025 only: -2.561); scaled it would be -3.82 cm/yr. `grace.parquet` has no scaled column any more | DECIDED |
| Caveat (owner) | regional water storage over one 3-degree mascon (about 330 km), including glaciers and the plains, **not the field's own aquifer**; carried in the card and in `rules.yaml` `groundwater.caveat` for every explanation | DECIDED |

### 1.11 NOAA GHCN-Daily, Kathmandu Airport (validation; reference for correction A): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Station | `NP000444540` KATHMANDU AIRPORT, 27.700 N 85.367 E, 1337 m: about 6.3 km from the old demo point and **about 7.4 km west of the placeholder field** (great-circle, from these coordinates) | VERIFIED: `ghcnd-stations.txt`; distance computed |
| Product, version | GHCN-Daily **Version 3.35**, by_station CSV | VERIFIED: readme line 2 |
| Units in → out | PRCP **tenths of mm** → `rain_mm`; TMAX, TMIN **tenths of degrees C** → `tmax_c`, `tmin_c` (scale 0.1) | **VERIFIED**: readme lines 149 to 153 (owner's note confirmed) |
| Fill | -9999 = missing; **found: 0** (missing days are simply absent rows) | FOUND |
| Quality flags | any non-blank Q-FLAG dropped: **PRCP 0, TMAX 1, TMIN 0** | FOUND |
| **Source flag (S-FLAG)** | **Every record 2001-2025 has S-flag `S`** (PRCP 5,036 of 5,036, TMAX 4,707 of 4,707, TMIN 2,404 of 2,404; REVIEW_NOTES H2; now kept per row in `sflag_*` columns and counted in the card's `quality_flags_used.source_flags`). The readme on `S`: "derived from hourly synoptic reports exchanged on the GTS. Daily values derived in this fashion may differ significantly from 'true' daily data, particularly for precipitation (i.e., use with caution)." So the station is **synoptic-derived: use with caution**, above all for rain. Everything that treats it as the reference inherits this: decision A's fit and held-out results, the POWER-vs-station rain checks (VALIDATION 3.7), the spike flags and the rain-vote labels, and the 2016 wheat check | VERIFIED: raw file column 7; readme |
| Date range | **2001-01-01 to 2025-08-24** (the record stops there) | FOUND |
| Time zone | station observation day. **0 of 12,147 records give an observation time.** Day-alignment test (C): daily rain vs POWER correlates best at **lag 0** (Pearson 0.634, Spearman 0.746, n 5,036; lag -1: 0.387 / 0.658; lag +1: 0.264 / 0.586), so no whole-day shift between the station and POWER's local solar days does better than none. This does **not** establish a common day boundary (REVIEW_NOTES M10): the station's observation time is unknown, but its S-flag values are GSOD summaries on the GMT day 0000Z-2359Z (05:45-05:45 Nepal time, the same day as IMERG), and GSOD rain "may include latter part of previous day" (GSOD readme, NCEI 10/28/2020). | FOUND (test C); day boundary **VERIFIED** (verified 2026-11-12; rain window approximate) |
| Disagreement with DHM | 2024-09-28: GHCN 194.1 mm (and 97.0 mm on 09-27), but DHM's situational report gives Kathmandu Airport **239.7 mm** in 24 h. Different 24-h windows or record versions; the airport's GHCN values are synoptic-derived (S-flag `S`, above), which the readme says may differ significantly from true daily rain | TODO-VERIFY |
| Rain records per year | 2001: 38, 2002: 2, 2003: 39, 2004: 290, 2005: 297, 2006: 165, 2007: 161, 2008: 222, 2009: 164, 2010: 77, 2011: 54, 2012: 155, 2013: 0, 2014: 0, 2015: 362, 2016: 356, 2017: 354, 2018: 265, 2019: 339, 2020: 217, 2021: 355, 2022: 354, 2023: 312, 2024: 233, 2025: 225 | FOUND |
| Comparison rule (owner) | monthly totals, only years with at least 330 records: 2015, 2016, 2017, 2019, 2021, 2022 | applied |
| Humidity | none: the station records only TMAX, TMIN, TAVG, PRCP, SNWD, so decision A's RH check is not possible | FOUND |
| Better stations nearby | DHM "Bhaktapur" (27.68 N, 85.42 E, 1315 m) is about 2.5 km from the placeholder field (coordinates given to 0.01 deg), and "Changu Narayan" is nearby (distance TODO-VERIFY); both are much closer than the airport. DHM seasonal PDFs list them | not fetched (DHM station series are not open downloads; TODO-VERIFY access) |

### 1.12 FAOSTAT, Nepal national yields (validation layer 4.3 only): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Product | QCL "Production: Crops and livestock products", public bulk file (normalized), dated 2025-12-31; the FAOSTAT API now needs a token (HTTP 401) | VERIFIED: FAOSTAT catalogue `datasets_E.json` |
| Rows used | Area Code 149 (Nepal); Item 27 Rice, 15 Wheat, 56 Maize (corn); Element "Yield"; 2001 on | FOUND |
| Units in → out | kg/ha → `yield_kg_ha` (hg/ha would be converted x0.1; none seen) | FOUND |
| Flags | kept, not filtered: A (official) 71, E (estimated) 1 | FOUND |
| Date range | 2001 to 2024 (72 rows) | FOUND |
| Use | year-to-year ups and downs only; never shown as mass per area (rule 11) | DECIDED (F) |

### 1.13 Twin weather (derived): BUILT

`data/clean/demo/weather.parquet`, card `data/cards/demo/weather.json`. POWER temperature with the
**Kathmandu-valley correction** (decision A, station NP000444540), rain merge (D), ET0 (step 3).

| Item | Value |
| --- | --- |
| Tmin correction | applied: held-out MAE **2.31 → 1.22 C**, bias **+2.15 → -0.32 C** (n 714; fit 2015, 2017, 2021, 2023; test 2016, 2019, 2022). Monthly offsets POWER - station: +4.10 Jan, +3.29, +3.27, +3.46, +2.84, +1.49, +0.38, +0.28, +0.41, +1.82, +3.42, +4.22 Dec |
| Tmax correction | applied: held-out MAE **2.25 → 1.16 C**, bias **-1.67 → -0.10 C** (n 1,303; fit 2001, 2015, 2017, 2019, 2022; test 2005, 2016, 2018, 2021, 2023). Offsets from +0.79 (May) to -4.22 (Sep) |
| Humidity | RH2M not corrected (no station humidity). For ET0 the actual vapour pressure is held from POWER (RH2M with POWER's own temperatures, FAO-56 eq. 19), capped at e0 of the corrected Tmin, and used with the corrected temperatures (owner, 2026-11-12, REVIEW_NOTES M6; columns `ea_kpa`, `ea_capped`). Cap binds on 5,056 of 9,131 days (3,028 even without the correction). Mean annual ET0 1,325 mm (used) vs 1,281 mm with RH held (`et0_rh_held_mm`); by month -0.06 to +0.37 mm/day; largest +0.97 mm on 2023-08-27. Card `corrections.ea_kpa` |
| **Known limit** | one offset per month over-corrects extreme nights: Jan 2013 coldest corrected night **-4.2 C** vs the reported Kathmandu low of **-1.1 C** (raw POWER -0.1 C). Jan 2018: corrected 0.7 C vs station 0.0 C. Frost (step 8) needs a better method or a stated caveat |
| Cold nights (owner, 2026-11-12) | held-out 2016, 2019, 2022: MAE offset **1.22** vs QM 1.34 C; January-coldest-night error offset 2.83 vs **QM 2.31** C; nights below 2 C (station 9) offset 22 vs **QM 15**. **Both used, each for its job**: offset in `tmin_c` (twin, ET0), QM in `tmin_frost_c` (frost only, risk bands, never a count) |
| Rain | GPM downloading (D6); POWER fills only GPM gaps (D). The three-source vote is built and waits for GPM |
| ET0 | FAO-56 PM from corrected temperatures; mean 3.63 mm/day, about 1,325 mm/yr (ea held from POWER, capped; 3.51 mm/day, 1,281 mm/yr with RH held); elevation = the field's NASADEM height (1,325.0 m over the 60 m square; 1,313.2 m over the first placeholder) |
| Checks | weather.py now fails loudly if any day has `tmin_c` or `tmin_frost_c` above `tmax_c` (0 days each; smallest gaps 3.96 and 3.98 C; the earlier claim had no check behind it, REVIEW_NOTES M9); `tmin_frost_c` range-checked -30 to 50 C; `months_uncorrected` empty for Tmin, Tmax and frost Tmin (M8); both ET0 columns non-negative; POWER rain fill at most 5% of any year inside the GPM record (M2); the card names each column's source and resolution (M9) |

### 1.14 ESA WorldCover 10 m 2021 v200 (placeholder field only): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| Access | public COG tile `ESA_WorldCover_10m_2021_v200_N27E084_Map.tif` (S3, no login); box window only | FOUND |
| Raw attributes | EPSG:4326, 1/12000 deg, uint8, nodata 0; legend in the file tags (10 tree cover ... 40 cropland, 50 built-up ...); licence CC-BY 4.0 | VERIFIED: file tags |
| Box classes | cropland 556,066; tree cover 362,535; built-up 233,606; grassland 155,267; bare 7,409; water 418 pixels (0 no-data) | FOUND |
| Placeholder | first: the nearest 100 m square that is cropland with a 30 m cropland margin (18 x 20 pixels all class 40); 26,388 candidates; centre 27.6785 N, 85.427417 E, 0.979 km from the old point: **a construction plot** (owner). Now: a 60 m square from `pipeline/fetch/placeholder.py` (cropland with a 30 m margin, no built-up within 100 m of the margin, both seasons green in HLS 2023-2025; 1,591 pass). The owner chose candidate 1 and moved it 25 m north to **27.690767 N, 85.441792 E**, 2.59 km from the old point, away from the Kasan River strip. Its margin is then 77 m from the nearest built-up pixel (rule: 100 m) | FOUND; `placeholder_candidates.json`, plots `placeholder_candidates.png`, `placeholder_field.png` |
| Caveat | a 2021 map at 10 m: one year, and its accuracy varies by class (TODO-VERIFY the product's cropland accuracy for Nepal). The HLS greenness record will be checked for crop seasons over the square once fetched | TODO-VERIFY |

### 1.15 How each box dataset is fetched (2026-11-12)

| Dataset | What is fetched | Status |
| --- | --- | --- |
| MODIS MOD13Q1.061 | NDVI, pixel reliability, VI quality, composite day, 2001-2025, box, native sinusoidal, netCDF-4 (AppEEARS) | DOWNLOADED; layer names VERIFIED via the AppEEARS product API (closes the TODO in 1.4) |
| SMAP SPL3SMP_E.006 | AM soil moisture + retrieval quality flag, PM the same, 2015-03-31 to 2025-12-31 | REQUESTED, processing on NASA's side at 13:05 (split: one task was 57.2 % over AppEEARS's file limit) |
| SMAP SPL4SMGP.008 | root-zone and surface soil moisture, 3-hourly, one task per year | REQUESTED, processing or pending on NASA's side at 13:05 |
| HLS-VI | `NDVI` (int16, scale 0.0001, fill -19999) and `Fmask` (uint8, fill 255; bit meanings in the file's `Fmask description` tag) per granule, box window in UTM 45N, tile T45RUL | DONE (all 1,471 granules, 0 failures). **Cloud-mask layer name VERIFIED: `Fmask`** (closes the TODO in 1.3). NDVI files are strip-organised, so each window read takes about 10-20 s |
| ECOSTRESS | LSTE: `LST`, `QC`, `cloud`; ESI: `ESI`, `cloud`; V003 first, V002 for overpasses V003 lacks (D4) | DONE (769 LSTE, 310 ESI, 0 failures) |
| GPM IMERG | daily box subsets; Final ends 2025-09-30 in CMR (D1 confirmed) | DOWNLOADING (EULA accepted 2026-11-12). Cloud OPeNDAP fails for this collection (no DMR++); GES DISC Hyrax works |

---

## 2. Field outline over pixels

Rerun 2026-11-12 for the current placeholder field (60 m square at 27.690767 N, 85.441792 E;
`scripts/plot_pixels.py`, `data/checks/demo/field_pixels.json`, plots in `data/plots/pixels/demo/`). A pixel
counts when its centre lies inside the polygon: **WorldCover 42, NASADEM 4, HLS 4**; GRACE: the field lies in one
0.5 deg cell of one 3 deg mascon. GPM and SMAP: not downloaded yet. MODIS (250 m) and ECOSTRESS (70 m) are
downloaded but the script does not draw them yet. POWER and GHCN are points. (The file held the rejected first
square until this rerun.)

## 3. Cross-checks

| Check | Result | Status |
| --- | --- | --- |
| POWER vs GHCN rain | **49 complete months in 2015, 2016, 2017, 2019, 2021, 2022: POWER 21.3% drier, r = 0.93, mean absolute error 46.8 mm per month** | RUN (`data/checks/demo/crosscheck_power_ghcn_NP000444540.json`) |
| POWER vs GHCN January Tmin | 205 shared days: station 3.7 C, POWER 7.5 C, **POWER +3.8 C** | RUN |
| POWER vs GHCN May-June Tmax | 829 shared days: station 29.4 C, POWER 29.5 C, **POWER +0.08 C** | RUN |
| Spike check B (rain > 50 mm and > 5x another source) | **9 days flagged**, written to the power, station and weather cards. POWER high: 2009-07-28 (59.2 vs 0.0), 2024-06-25 (74.2 vs 0.0), 2024-06-26 (114.3 vs 4.3), 2024-09-25 (55.9 vs 0.8), **2025-03-01 (233.7 vs 3.8)**. Station high: 2012-09-13 (134.6 vs 16.0), 2018-04-03 (51.1 vs 0.2), 2021-07-11 (90.9 vs 2.7), 2022-08-10 (76.2 vs 14.2). The 2024-09-27/28 flood is not flagged (ratios under 5). Nothing deleted. The station's 0.0 on the POWER-high days (2009-07-28, 2024-06-25) may be a missing synoptic report rather than a dry day (the station is synoptic-derived, 1.11): unverified, so the GPM vote decides | RUN |
| Day alignment C (POWER vs station daily rain) | best lag **0** (see 1.11) | RUN |
| GPM vs POWER vs GHCN rain | — | NOT YET POSSIBLE: GPM download running |
| MODIS vs HLS NDVI, 2013 on | — | NOT YET POSSIBLE: both are downloaded; the comparison belongs to diary step 6 |

## 4. Switch-off test

**Result if run today:** the only export is still MOCK, so switching off any dataset changes nothing,
and **every dataset is flagged**. POWER and GHCN now feed the twin's weather table, but no export yet.

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
| GHCN | twin temperatures (via correction A; weather card) |
| FAOSTAT | none by design (validation only) |

## 5. Data cards

Written (all in `data/cards/demo/`): `power.json`, `ghcn_NP000444540.json`, `faostat_yields.json`, `weather.json`,
`worldcover.json`, `nasadem.json`, `grace.json`, `soilgrids.json` (WCS) and `soilgrids_rest.json`, and from the cache
(REVIEW_NOTES L7, 2026-11-12) `hls_l30.json`, `hls_s30.json`, `eco_lste.json`, `eco_esi.json`, `modis.json`; `gpm.json`
after the download (`--from-cache`), SMAP cards after their bundles arrive. Each has every rule-12 field plus `range_warnings`; power and station cards carry
`cross_source_flags` (B); the weather card carries `corrections` (A) and the ET0 elevation used.

## 6. TODO-VERIFY (open)

1. POWER: per-value quality flags; grid edges for a cell plot; cause of the 2001-2003 low rain totals.
2. IMERG: ~~daily files cover the UTC day~~ (closed verified 2026-11-12); meaning of `precipitation_cnt_cond`.
3. ~~HLS: list one granule's layers to find the cloud mask; its bits.~~ Closed: `Fmask`, bits from the file tag (1.3, 1.15).
4. ~~MODIS: confirm the three expected layer names by listing a file.~~ Closed: AppEEARS product API (1.4, 1.15).
5. SMAP L3: ~~which bit of `retrieval_qual_flag` means "recommended quality"~~ (closed verified 2026-11-12); L4 day boundary.
6. SoilGrids: why the demo point's own cell has no prediction.
7. ECOSTRESS V003: ~~units, fill, flags~~ (closed verified 2026-11-12); time stamps.
8. NEX-GDDP-CMIP6: ~~units, wind height~~ (closed verified 2026-11-12); version choice (v2.0) and calendars at fetch time; citation.
9. ~~GRACE: variable, unit, grid, gap between missions.~~ Closed: file attributes (1.10).
10. GHCN vs DHM: 194.1 vs 239.7 mm at Kathmandu Airport on 2024-09-28; access to DHM Bhaktapur and
    Changu Narayan series.
11. FAOSTAT formal citation text.
12. Crops (crops.json): no published seasonal Ky for rice, lentil, mustard, buckwheat or finger millet;
    no FAO-56 stage lengths for mustard or buckwheat and no Kc, Zr or p for buckwheat.
13. Quantile mapping below the fitted range: Gudmundsson et al. 2012 state the constant-correction
    rule only above it.
14. My reading of the switch-off test (section 4).

Closed this round: ASCE-EWRI page for the Rs/Rso floor (eq. 18, p. 20); quantile-mapping citations;
SoilGrids conversion factors (from the API itself); hydrologic soil group (NEH 630 Ch. 7 texture
guidance); curve numbers (TR-55 Table 2-2b = NEH Table 9-1); Nepal crop calendar (FAO Crop Calendar,
Hill zone). Earlier: POWER resolutions; station observation day; CMR, SoilGrids, POWER citations; FAO-56
example values; GHCN units; GRACE product name; IMERG gap (D1); soil-moisture range (D2).
