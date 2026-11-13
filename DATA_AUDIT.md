# DATA_AUDIT.md

Updated 2026-11-13 (REVIEW_2, an independent AI review: stale lines corrected, the switch-off test run on the real export,
SMAP cleaned, DHM's 2025 gauges and the gauge evidence added). Before that, 2026-11-12 (later): placeholder field, fetch box and the first Earthdata fetches (build step 5,
parts without GPM). Regenerate the data-level parts after each fetch step.

**Field (owner, 2026-11-12):** 27.67 N, 85.43 E is Bhaktapur's old city, so it is only the centre of the
fetch box `[85.379227, 27.625034, 85.480773, 27.714966]` (5 km N, S, E, W). The field is a PLACEHOLDER
60 m square at **27.690767 N, 85.441792 E**: the owner's candidate 1 (`pipeline/fetch/placeholder.py`), moved 25 m north away from the Kasan River strip (section 1.14). It replaced a 100 m square at 27.6785 N, 85.427417 E, which was a construction plot. Datasets fetched before
this (GHCN, FAOSTAT) are not location-bound; POWER was fetched at the first, since rejected, placeholder (27.6785 N, 85.427417 E): the same POWER grid cell as the field (0 of 9,131 days differ between cached points; a 2016 request at the field's own point matches on all 366 days; REVIEW_2 L1; the card still names the old point;
identical values).

## Status

| Dataset | Downloaded into the pipeline? | Data card |
| --- | --- | --- |
| NASA POWER | **Yes**, re-fetched at the placeholder 2026-11-12: 2001-01-01 to 2025-12-31, 9,131 days. The whole box lies in one 0.5 x 0.625 deg cell | `data/cards/demo/power.json` |
| NOAA GHCN-Daily, Kathmandu Airport (validation; reference for correction A) | **Yes**: 2001-01-01 to 2025-08-24 | `data/cards/demo/ghcn_NP000444540.json` |
| FAOSTAT QCL, Nepal yields (validation 4.3 only) | **Yes**: 2001 to 2024, 72 rows | `data/cards/demo/faostat_yields.json` |
| Twin weather (derived: corrected POWER + rain merge + ET0) | **Built**: 2001-01-01 to 2025-12-31 | `data/cards/demo/weather.json` |
| ESA WorldCover 2021 (placeholder field only) | **Yes**: box window, 1,079 x 1,219 pixels at 10 m | `data/cards/demo/worldcover.json` |
| NASADEM | **Yes**: box, elevation and slope; field 1,325.0 m, slope 1.6 deg (4 pixels) | `data/cards/demo/nasadem.json` |
| GRACE/GRACE-FO mascon CRI | **Yes**: 261 months, 2002-04 to 2026-09, the 0.5 deg cell holding the field (one 3 deg mascon) | `data/cards/demo/grace.json` |
| GPM IMERG | **Yes: complete, 9,131 of 9,131 days** (Final 9,039 to 2025-09-30, Late 92; 0 days filled from POWER; the 3,287 days from 2017 are scaled in the twin's rain, the 92 Late days with the Final factors since 2026-11-13, see 1.2). Download history (EULA accepted by the owner, 2026-11-12): daily box subsets; the run was cut off at 2009-03-03 when VS Code closed, resumed from the cache at 13:02, and ended with **7,558 of 9,131 days**: every day from 2021-09-11 to 2025-12-31 (1,573) failed while the laptop's internet was down (about 14:10-14:31; both GES DISC hosts unreachable, and AppEEARS failed to resolve at the same time). The retry (15:59, 2 workers) fetched them all: **9,131 of 9,131 days** (Final 9,039 to 2025-09-30, Late 92), 0 failed, 0 fills in the field's cell; `gpm.parquet`, the card and the weather table rebuilt from the cache at 16:31. Field-cell rain averages 2,162 mm/yr (2009 lowest 1,436; 2020 highest 3,120). **Well above the station from 2017:** in the station's well-recorded years GPM is 1,505 / 1,736 / 2,635 / 2,399 / 2,969 / 2,644 mm (2015, 2016, 2017, 2019, 2021, 2022) against the station's 1,495 / 1,460 / 1,146 / 1,559 / 1,737 / 1,756 and POWER's 1,205 / 1,155 / 1,077 / 1,182 / 1,562 / 1,242; spike flags rise from 9 to 170, mostly 'gpm disagrees with the other two'. Cause not yet known (IMERG over the valley, or the synoptic-derived station undercounting): VALIDATION 3.9 | after download (`data/cards/demo/gpm.json`) |
| MODIS MOD13Q1, SMAP L3 and L4 | **MODIS downloaded** (one netCDF-4 for the box, 2001-2025). **SMAP downloaded and cleaned (2026-11-13, REVIEW_2)**: 13 AppEEARS bundles (L3 AM and PM; L4 one per year, 2015-2025), `pipeline/fetch/smap.py` -> `data/clean/demo/smap.parquet`, card `smap.json`; a check only (1.5) | `data/cards/demo/modis.json` (576 composites, 2000-12-18 to 2025-12-19; the field touches 2 MODIS cells but holds no cell centre); SMAP after download |
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
| Known problem 1 | **Not only rain (REVIEW_2 H8, 2026-11-13):** in 2001-2003 POWER's daytime temperature and humidity are off too: yearly mean Tmax 27.2-27.6 C against 24.6-26.8 C in every later year (POWER minus station Tmax about 1.7 C higher than in 2004-2012, in every month; the station shows no warm spell), RH 51.8% against 56-71%, so ET0 is 1,429 mm a year against 1,311 (+9%) and the diary's hot days number 96, 139, 113 against at most 66 later. The hot-day trend is therefore also given without these years; replay years 2002-2003 carry the excess ET0 (lowering it to the later level changes 3 of 24 years' harvest integers and no plan pick). PRECTOTCORR yearly totals for 2001 to 2003 (621, 525, 534 mm) are about half of every later year. The station has almost no records then, and POWER documents no source change in those years | Cause TODO-VERIFY. **Decision D: never used to fill GPM gaps** |
| Known problem 2 | Implausible daily rain, e.g. **2025-03-01 233.7 mm** (station 3.8 mm, dry season) | **Decision B: flagged** (section 3); not removed |
| Temperature bias | Against the station on shared days: Tmin too warm (January +3.8 C; monthly offsets +0.3 to +4.2 C), Tmax too cool from July to December (offsets down to -4.2 C in September) | FOUND; **decision A correction** applied in the twin's weather (1.13) |

### 1.2 GPM IMERG: DOWNLOADED (GES DISC EULA accepted 2026-11-12; daily box subsets, 9,131 of 9,131 days); 2017+ CORRECTED (owner's decision 1, 2026-11-13)

| Item | Value | Status |
| --- | --- | --- |
| Products (D1) | `GPM_3IMERGDF` V07 (`C2723754864-GES_DISC`) through **2025-09-30** (its last granule), then `GPM_3IMERGDL` V07 (Late) for 2025-10-01 to 2025-12-31, recorded in the card's `segments` | VERIFIED: CMR; DECIDED |
| Variable | `precipitation`, float32, mm/day, no scale factor, fill -9999.9 (float32; the guard matches both spellings) | VERIFIED: UMM-Var `V3156651215-GES_DISC` |
| Quality flags | `precipitation_cnt` = number of valid half-hourly values in the day, 'only given to gauge the significance of the daily rates'; count-0 cells are fill (GPM_3IMERGDF V07 abstract). Not a quality flag, so none applied. `precipitation_cnt_cond`: meaning not found | PARTLY VERIFIED (verified 2026-11-12); `precipitation_cnt_cond` TODO-VERIFY |
| Time zone | UTC days (00:00-24:00 UTC = 05:45-05:45 Nepal time); each file's BeginTime 00:00:00.000Z and EndTime 23:59:59.999Z support it | **VERIFIED**: IMERG V07 Technical Documentation (13 July 2023) p. 40, 'The time zone for these data sets is Universal Coordinated Time'; the daily file is the mean of the 48 UTC half-hours of the data day (GPM_3IMERGDF V07 abstract) |
| Fills found, records dropped, pixels, plot | 0 fills in the field's cell, 0 days dropped, 4 box cells (2 x 2, card `data/cards/demo/gpm.json`) | DONE (9,131 of 9,131 days: Final 9,039 to 2025-09-30, Late 92). Earlier note: The card now counts real fills in the field's cell, failed days, days without a granule and days not cached separately per segment, records the dropped days and the date range actually covered, prints the raw attributes (units mm/day; scale_factor, add_offset, valid_range ABSENT; _FillValue -9999.9), and the run exits non-zero if any day is missing (REVIEW_NOTES M2) |

**Rain check B (2026-11-13; VALIDATION 3.9b).** IMERG Final's gauge input collapses in January 2017 (monthly gauge
weight 96-98% to 56-72%; GPCC Full Data V2022 stations in the field's 1-degree box about 50 to about 1 a month), and
Pettitt finds a change in the yearly GPM totals after 2016 (p 0.0014). Against DHM's 1991-2020 normals GPM is
1.34 x Bhaktapur's annual normal in 2001-2016 and 1.99 x in 2017-2025 (POWER 0.79 x; the airport station 1.00 x its
own normal). The correction of 2017-2025 is applied (owner's decision 1, below). REVIEW_2 (2026-11-13) fetched the gauge
evidence again and made it reproducible (1.17), and added DHM's own 2025 gauge totals as an independent check (1.16).

**DHM's 1991-2020 normals (config/dhm_normals_1991_2020.csv).** Kathmandu Airport from DHM's official 'Climate
Normals' table (20 stations; the DHM link is now 404, read from the Internet Archive copy of 30 Jan 2022); Bhaktapur
(index 1052, 2.3 km from the field), Changu Narayan and Nagarkot are not in it and come from the 'Normal' columns of
Annex 1 of DHM's monthly bulletins (Jan 2025 to Jul 2026), where an asterisk marks temperature normals averaged over
the available years (all of Bhaktapur's and Changu Narayan's). **DHM counts a rainy day as 1 mm or more** (Monsoon
2025 summary p. 3: 'the number of rainy days (precipitation >= 1 mm)'; bulletin Annex 1 columns '>=1.0mm'), the same
as our ETCCDI wet day (rules.yaml monsoon_onset.wet_day_mm, trends.dry_day_mm). The owner's '1,200.4 mm' is the
airport's measured June-September 2025 rain (DHM monsoon 2025 summary, Annex 1), not its annual normal (1,502 mm).

**Break correction (owner's decision 1, 2026-11-13; rules.yaml gpm_series.correction).** The twin's rain
(`weather.parquet` rain_mm) scales every IMERG Final day from 2017-01-01 by its calendar month's factor = mean
complete-month total 2001-2016 / mean 2017-01 to 2025-09 (Jan 0.83, Feb 0.79, Mar 0.54, Apr 0.47, May 0.55, Jun 0.63,
Jul 0.73, Aug 0.71, Sep 0.77, Oct 0.80, Nov 2.40, Dec 0.46; 3,195 Final days). Since 2026-11-13, 17:00 (owner's answer 7) the 92 Late days are scaled with the same factors (3,287 days
in all; the factors are still fitted on Final months only); a POWER-filled day would not be. Mean yearly rain 2017-2025:
2,731 mm as published, 1,874 corrected (1,882 before the Late days were scaled; 2001-2016: 1,842). The rain as
published stays in `rain_uncorrected_mm` (flag `rain_break_corrected`); every rain-based result is also run on it.
Held out against the airport station (fit on odd years from 2017, test on even, and the reverse; 48 months): mean
monthly error 93.7 -> 31.4 mm, total over the station 1.62 -> 1.06.

**Check datasets (rain check B; never the twin's rain).** IMERG Late V07 daily 2014-2019 (`pipeline/fetch/gpm_late.py`,
own cache `data/raw/gpm_late_check/`, `data/clean/demo/gpm_late_check.parquet`, card `gpm_late_check.json`) and CHIRPS
v3.0 daily final `rnl` 2001-2025 (`pipeline/fetch/chirps.py`: HTTP range reads of the yearly global netCDF-4 files,
only the chunks holding the box; precip mm/day, _FillValue -9999, no scale or offset, every day of the year checked;
UTC calendar-day labels; 9 cells of 0.05 deg overlapping the box; `data/clean/demo/chirps.parquet`, card `chirps.json`). Results (VALIDATION 3.9b): CHIRPS has no step at 2017 (1,454 then 1,437 mm a year); IMERG Late steps 1.13 against Final's 1.62 and is wetter than gauge-adjusted Final in 2014-2016, equal to it from 2017.

### 1.3 HLS Vegetation Indices: DOWNLOADED (box windows; all 1,471 granules: L30 336, S30 1,135, tile T45RUL)

| Item | Value | Status |
| --- | --- | --- |
| Products | `HLSL30_VI` v2.0 (from 2013-04-11), `HLSS30_VI` v2.0 (from 2015-11-28) | VERIFIED: CMR |
| NDVI | int16, scale 0.0001, **fill -19999** in the files (UMM-Var said -9999), valid -1 to 1 after scaling | **VERIFIED**: file tags (`_FillValue -19999`, `scale_factor 0.0001`) |
| Cloud mask | **`Fmask`** (uint8, fill 255). Bits from each file's own `Fmask description` tag: 7-6 aerosol, 5 water, 4 snow/ice, 3 cloud shadow, 2 adjacent to cloud, 1 cloud, 0 cirrus. Clear = bits 0-5 all zero (`pipeline/diary/ndvi.py`); water (bit 5) is kept as not clear after a check (REVIEW_NOTES M12): no water-flagged observation over the field in June-August 2013-2025 (0 of 2,916), and only 0.001-0.004% of clear observations over the box's cropland in those months | **VERIFIED**: file tag |
| Pixels | 30 m: a 10 m section is one-ninth of a pixel | 4 pixel centres inside the field, 9 pixels touching it; the 4 cover 77.6% of the field and 22.4% of their footprint lies outside it (REVIEW_2) |

### 1.4 MODIS MOD13Q1 v061: DOWNLOADED (AppEEARS, the box, 2001-2025: 576 composites, 447 kept at reliability 0). No number shown uses it (REVIEW_2 M6): the field is 5.9% of its 250 m pixel; it is compared with HLS only (section 3)

| Item | Value | Status |
| --- | --- | --- |
| NDVI | `250m 16 days NDVI`: int16, scale 0.0001, fill -3000, valid raw -2000 to 10000 (that is, -0.2 to 1.0) | VERIFIED: UMM-Var `V3143914093-LPCLOUD` |
| Quality and date layers | `_250m_16_days_pixel_reliability` (0 to 3, fill -1), `_250m_16_days_VI_Quality` (fill 65535), `_250m_16_days_composite_day_of_the_year` (1 to 366, fill -1) | **VERIFIED**: AppEEARS product API |

### 1.5 SMAP: DOWNLOADED AND CLEANED 2026-11-13 (AppEEARS: L3 AM and PM, L4 one bundle per year). A check on the twin only

**Result (REVIEW_2 Phase 3, `pipeline/fetch/smap.py`, card `data/cards/demo/smap.json`).** The 9 km EASE-Grid 2.0 cell holding the field (row 0, col 1 of the 2 x 2 box; the field lies 0.6 km and 2.9 km from its centre). **L4 (`SPL4SMGP` v008, model-assisted):** 31,432 three-hourly values, 2015-03-31 to 2025-12-31, no fills, root zone 0.155-0.422 m3/m3 (inside both the product's 0-0.9 and rule 12's 0-0.6); daily means of the eight values of each UTC day: 3,929 days, none incomplete. **L3 (`SPL3SMP_E` v006): not usable here.** Of 1,404 morning and 1,859 evening retrievals at the cell, **none is of recommended quality** (flag values 9 and 13 only; AppEEARS's own lookup table reads "doesn't have recommended quality" for both), and 237 and 263 of them exceed the product's valid maximum of 0.5 cm3/cm3 (up to 0.561). They are dropped and counted; the L3 columns are empty. A valley of city, paddy and steep hills is poor ground for a 9 km radiometer retrieval. **Use:** `scripts/run_smap_check.py` compares monthly anomalies of the L4 root zone with the twin's root-zone wetness (VALIDATION 4.2b). No number shown to farmers uses SMAP.

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

### 1.8 ECOSTRESS V003, V002 fallback (D4): DOWNLOADED (raw box windows; LSTE 769, ESI 310); CLEANED 2026-11-14 (a check only, VALIDATION 4.2e)

**Cleaned 2026-11-14 (`pipeline/fetch/ecostress.py`, rules fixed and committed before the first run, `fe3223a`, rules.yaml `validation_checks.ecostress`; card `eco_clean.json`, table `data/clean/demo/ecostress.parquet`, one row per overpass). The five traps:** (4) one granule per overpass, the latest build then iteration: 126 LSTE and 39 ESI granules replaced, 659 overpasses left (643 with LSTE, 16 with ESI only); (1-2) cloud = 1 dropped in both versions, QC and cloud read only beside a valid value; (3) LST kept only where QC bits 1-0 = 00 (best quality): every LST outside -98 to 70.7 C in the box was degraded (V002, bits 01) or under cloud (V003), so after masking none is left anywhere in the box and the hard limit (the coldest and hottest land surface measured from space; Scambos et al. 2018, Mildrexler et al. 2011) never fires; 11,940 kept box pixels lie outside rule 12's -30 to 50 C (counted as warnings, D2); (5) the field's value is the pixel at row 39, col 90 of the box grid: **37% of it is field and it holds 50% of the field**; the touching pixels hold 31%, 7% and 11% of the field (shares on a 1 m sub-grid) and their field-area-weighted mean is kept beside it. ESI is kept only where the same overpass has a kept LST at the pixel. **At the field pixel: 178 overpasses with a kept LST, 72 with a kept ESI (2018-2025)**, too few per season for the seasonal check (VALIDATION 4.2e). Before: **Not used in any result (REVIEW_2 L11, 2026-11-13); five things to settle before step 8 uses it.** (1) 742 of 769 LST and 307 of 310 ESI granules are V002, the rest V003 (D4 is implemented correctly: no overpass has both). (2) The versions differ: in V002 no valid LST pixel has cloud = 1 (0 of 5.06 million), in V003 10.6% do, so a mixed series must apply the cloud layer to V003; no code does yet. (3) "Valid" LST runs from 14.6 K to 1,305.8 K (31,066 pixels in 16 granules): mask by QC first, then fail loudly (rule 12c). (4) 119 overpass times have two or three product iterations (`_01`, `_02`, `_03`) and 111 of the first pairs differ: pick one before averaging. (5) Overpasses fall at every hour of the day, and one 70 m pixel centre lies in the field (38% of that pixel is field): 10 m sections cannot differ by ECOSTRESS. The earlier finding stands: QC and cloud read 0 where there is no data (5,631,223 QC and 6,139,061 cloud pixels in LSTE), so both are used only where LST is valid.

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

### 1.9 NEX-GDDP-CMIP6: DOWNLOADING (step 9; 5 models complete at 01:00 on 2026-11-14, the run continues)

Not in CMR; public bucket `nex-gddp-cmip6` lists 35 models (VERIFIED). Units **VERIFIED** (Tech Note v2, 31 May 2025,
p. 3): pr kg m-2 s-1, tasmax/tasmin K, hurs %, rsds W m-2, sfcWind m s-1. sfcWind is nominally 10 m (CMIP6 day table:
height10m), so u2 needs FAO-56 eq. 47 (not used: only pr, tasmax, tasmin). Rules: `rules.yaml` `future`, committed
before the first download (`578b8a6`).

| Item | Value | Status |
| --- | --- | --- |
| Access | NASA NCCS THREDDS (`ds.nccs.nasa.gov/thredds`, AMES/NEX/GDDP-CMIP6): catalogues for the file names, one NetcdfSubset point CSV per model, experiment, variable and year (`temporal=all`), and each file's OPeNDAP `.das` for its attributes. About 10 s a request; 4 connections; about 6 minutes per model (150 requests); retries with back-off (31 retries, 0 lost requests in the first 7 models) | DONE for the code; `pipeline/fetch/nexgddp.py`, log `data/raw/nexgddp/fetch.log` |
| Cell | **27.625 N, 85.375 E**, the 0.25 deg cell holding the field; its centre is 9.8 km from the field. Requested at the centre; every answer must return that grid point (it did). Raw answers cached by cell (`data/raw/nexgddp/cell_27.625_85.375/`), so fields in the same cell reuse them | VERIFIED: every answer |
| Units, fill | Every answer's header and every file's attributes: pr `kg m-2 s-1` -> `pr_mm` (x 86400), tasmax/tasmin `K` -> `tasmax_c`/`tasmin_c` (- 273.15). `_FillValue` = `missing_value` = 1e20; no scale_factor, add_offset or valid_range, so golden rule 12's ranges are the hard limits | VERIFIED |
| Versions | Every file used is `_v2.0` (the NCCS catalogue holds v2.0 files; `version "2.0"` in the files); recorded per file in each model's `manifest.json` | VERIFIED |
| Calendars | From each file's `time:calendar`: 360_day (KACE-1-0-G), 365_day (CanESM5), standard (MIROC-ES2L), others per model in the card; each answer must have that calendar's number of days. Only monthly means are used | VERIFIED (closes the TODO above) |
| Licences | Each file's `cmip6_license`: CC-BY 4.0 or CC-BY-SA 4.0, by model and variable (KACE-1-0-G: pr CC-BY 4.0, tasmax/tasmin CC-BY-SA 4.0); CREDITS.md has the terms | VERIFIED per file |
| Models | 35 folders; GFDL-CM4_gr2 left out by the rule (GFDL-CM4 again); the other 34 fetched in the order fixed by seed 2026 (`fetch_order.json`). **Left out by the guards:** CESM2 (no historical tasmax in its r4i1p1f1 folder); MIROC-ES2L (its tasmin files have **no units attribute**: refused, never assumed to be K; 50 files). Complete at 01:00: KACE-1-0-G, CanESM5, MPI-ESM1-2-LR, MIROC6, INM-CM5-0 | RUNNING |
| Clean table, card | `data/clean/<field>/nexgddp_daily.parquet` (model days, never real dates); `data/cards/<field>/nexgddp.json` (models used, order, calendars, licences, variants) | DONE |
| Switch-off | Without 5 complete models `scripts/run_future.py` writes the outlook as NOT YET and the field file's `future` stays null and in the mock list | BY DESIGN |

### 1.10 GRACE/GRACE-FO (D5, D7): DOWNLOADED

| Item | Value | Status |
| --- | --- | --- |
| File | `GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc` (44.2 MB, one global file) | FOUND |
| Variables | `lwe_thickness` cm, fill -99999, valid -2305.0 to 1273.7 (the hard limit, D2); `uncertainty` cm, 1-sigma per 3-degree mascon | VERIFIED: file attributes |
| Cell | lat 27.5-28.0, lon 85.0-85.5, mascon 1213, land mask 1 | FOUND |
| Series | 261 monthly solutions, 2002-04 to 2026-09; lwe -73.3 to +37.4 cm; GRACE/GRACE-FO gap months are absent, not filled | FOUND |
| Resolution | 0.5 deg grid of 3-degree equal-area mascons: regional context only (file attribute) | VERIFIED |
| CRI scale factor (owner, 2026-11-12, REVIEW_NOTES M4) | 1.4945 at the cell, recorded in the card, **not applied**: it is CLM-based (land hydrology; file attribute 'based on CLM data from 2002-2009'), the mascon includes glaciers and snow, and no source was found for applying it here. **Unscaled OLS trend -2.56 cm/yr; the exported value is the seasonal Sen slope, -2.57 cm/yr** (REVIEW_2: the cell belongs to JPL mascon 1213, 25.5-28.5 N, 85.0-88.5 E, 42 identical half-degree cells from the Bihar plain to Everest, Kathmandu on its western edge) (261 months, 2002-04 to 2026-09; 2002-2025 only: -2.561); scaled it would be -3.82 cm/yr. `grace.parquet` has no scaled column any more | DECIDED |
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
| Rain | GPM IMERG complete (D6): 9,131 days, 0 filled from POWER (D); 3,287 days from 2017-01-01 scaled (owner's decision 1: 3,195 Final days; owner's answer 7 of 2026-11-13: the 92 Late days too, with the Final factors), `rain_uncorrected_mm` kept beside it. The three-source vote ran: 170 flags on 120 days (section 3) |
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
| SMAP SPL3SMP_E.006 | AM soil moisture + retrieval quality flag, PM the same, 2015-03-31 to 2025-12-31 | DOWNLOADED (2026-11-12); cleaned 2026-11-13: no recommended-quality retrieval at the field's cell, not used (1.5) (split: one task was 57.2 % over AppEEARS's file limit) |
| SMAP SPL4SMGP.008 | root-zone and surface soil moisture, 3-hourly, one task per year | DOWNLOADED (2015-2017 on 2026-11-12; 2018-2025 on 2026-11-13 from the same tasks); cleaned 2026-11-13 (1.5) |
| HLS-VI | `NDVI` (int16, scale 0.0001, fill -19999) and `Fmask` (uint8, fill 255; bit meanings in the file's `Fmask description` tag) per granule, box window in UTM 45N, tile T45RUL | DONE (all 1,471 granules, 0 failures). **Cloud-mask layer name VERIFIED: `Fmask`** (closes the TODO in 1.3). NDVI files are strip-organised, so each window read takes about 10-20 s |
| ECOSTRESS | LSTE: `LST`, `QC`, `cloud`; ESI: `ESI`, `cloud`; V003 first, V002 for overpasses V003 lacks (D4) | DONE (769 LSTE, 310 ESI, 0 failures) |
| GPM IMERG | daily box subsets; Final ends 2025-09-30 in CMR (D1 confirmed) | DONE: 9,131 of 9,131 days (EULA accepted 2026-11-12). Cloud OPeNDAP fails for this collection (no DMR++); GES DISC Hyrax works |

---

### 1.16 DHM monthly bulletins, 2025 (validation only; added 2026-11-13, REVIEW_2 Phase 3)

| Item | Value | Status |
| --- | --- | --- |
| Product | DHM Climate Division, monthly "Preliminary Precipitation and Temperature Summary", Annex 1 "Monthly precipitation and temperature data"; six bulletins (April, August, September, October, November, December 2025) | PRELIMINARY data; (c) DHM; **validation only, kept under `data/` (git-ignored), never redistributed** |
| Stations | Bhaktapur (27.68 N, 85.42 E, 1,315 m; about 2.3 km from the field), Changu Narayan (27.72 N, 85.43 E, 1,502 m), Kathmandu Airport (27.70 N, 85.36 E, 1,337 m) | read from the bulletins |
| Variables, units | monthly total, mm; the month's wettest day, mm, where read | transcribed by hand by a review sub-agent; **every value re-read in the bulletin text by the main review session** |
| Fills, flags, records dropped | none: a hand-made table of 18 values (an empty cell is a value not read); range guard 0 to 3,000 mm a month | `data/raw/dhm_bulletins/demo/monthly_2025.csv`, the six PDFs beside it |
| Time zone | Nepal time; DHM's rain day ends at 08:45 local (03:00 UTC), so single days differ from GPM's UTC days by up to a day | stated in the card |
| Card, check | `data/cards/demo/dhm_bulletins.json`; `scripts/run_dhm_bulletin_check.py` -> `data/checks/demo/rain_vs_dhm_2025.json` | VALIDATION 3.9c |
| Use | A check of the 2017 rain correction against gauges that are not the GHCN synoptic series and do not reach IMERG. No number shown uses it | |

### 1.17 Gauge evidence for the 2017 break: IMERG monthly gauge weight and GPCC station counts (checks only; added 2026-11-13)

Until 2026-11-13 the numbers in `rules.yaml gpm_series.break_evidence` (shown on the site's method page) had been read by
hand by a research sub-agent, with no raw file, fetch code or card in the project (REVIEW_2 M6). `pipeline/fetch/gauge_evidence.py`
now fetches both sources, caches them in `data/raw/gauge_evidence/demo/`, writes `data/clean/demo/gauge_evidence.parquet`
(one row per month) and the card `data/cards/demo/gauge_evidence.json`, whose `summary` holds the quoted ranges.

| Item | Value | Status |
| --- | --- | --- |
| Product 1 | `GPM_3IMERGM` V07 (monthly IMERG Final), GES DISC OPeNDAP subsets of the 3 x 3 cells of 0.1 deg around the field's cell | Earthdata login; raw attributes printed and stored in the card |
| Variables, units | `gaugeRelativeWeighting`, percent (the weight of the gauge analysis in the final estimate); `precipitation`, mm/hr x hours in the month = mm per month | guard: weight 0 to 100 |
| Product 2 | GPCC Full Data Monthly Product V2022, 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100), DWD open data, no login; two decade files, 2001-2020 (the product ends in 2020) | classic netCDF, read with scipy |
| Variables, units | `numgauge`, stations in the box that month; `precip`, mm per month; the box centred 27.5 N, 85.5 E | guard: counts not negative, rain 0 to 3,000 mm a month |
| Fills, flags | masked by each file's own fill value (none at these cells); no quality flags: these *are* the quality information | card |
| Result | 297 months, 2001-01 to 2025-09, none missing. **Gauge weight at the field's cell: 96-98% in every one of the 192 months of 2001-2016** (96% in 109, 97% in 66, 98% in 17; the same range in all nine cells); **from January 2017 it drops** (2017 by month: 62, 68, 64, 61, 63, 60, 60, 55, 60, 61, 71, 70%); yearly means 2017-2025: 62.9, 56.3, 62.2, 56.0, 68.4, 71.8, 70.7, 65.8, 68.9% (single months 31-80%). **GPCC stations in the box: 44.9 to 53.2 a month by year in 2001-2016 (50.3 in 2011-2016); 1.0, 0.7, 1.0, 0.7 in 2017-2020.** GPCC's own box totals do not jump (2016 1,664 mm; 2017 1,658; 2018 1,642; then 1,887 and 2,172). IMERG's monthly rain sums to the daily files' totals (2018: 3,003 mm). The number on the method page was corrected from 96-97% to 96-98% | VALIDATION 3.9b |

### 1.18 The field abroad: Ambohidratrimo, Madagascar (`config/fields/ambohidratrimo.yaml`; build step 11, added 2026-11-14)

Same modules, same guards and cards as the demo, for a fetch box 2 km each way around -18.83, 47.42 (METHOD_NOTES 85-89).
Driver: `scripts/fetch_field.py --field ambohidratrimo` (resumable; each step's log in `data/raw/_logs/ambohidratrimo_<step>.log`,
its exit code in `data/raw/_logs/ambohidratrimo_steps.json`). Cards in `data/cards/ambohidratrimo/`. Field: a 60 m PLACEHOLDER
square (candidate 1 of the demo's rule with the zone's seasons; METHOD_NOTES 86).

| Dataset | Product, access | State (2026-11-14 night) | Notes |
| --- | --- | --- | --- |
| ESA WorldCover | v200 2021, tile S21E045, box window (no login) | done | 60.5% cropland, 26.7% grassland, 8.2% built-up of 196,992 pixels |
| HLS-VI L30 + S30 | v2.0 windows of tile T38KQE (`cogwindows.py`); 2023-2025 first (`--since`), then 2013-2025 | done: 368 of 368 L30, 638 of 638 S30 (2013-04 to 2025-12; 2023-2025 first; 21 failed reads all succeeded on a retry); cards written | one tile, no overlap; the windows share one grid (two spellings of the same UTM 38 CRS, as on the demo) |
| GPM IMERG daily | V07 Final through 2025-09-30, Late for Oct-Dec 2025 (as on the demo), OPeNDAP box subsets | running | the field's 0.1 deg cell is the origin's; UTC days = 03:00-03:00 local time (UTC+03:00) |
| CHIRPS v3.0 `rnl` | yearly global files, range reads of the box's cells | done: 2001-2025 (25 years) | checks only. Mean 1,446 mm a year at the field's cell; wet November-March (January 340 mm), dry May-September (5-15 mm a month) |
| NASA POWER | point at the field, 2001-2025 | done (9,131 days, no fills, no range warnings) | cell elevation 1,425 m |
| NASADEM | NASADEM_HGT v001, one tile | done | field 1,249 m (4 pixels, 1,248-1,250 m), slope 2.4 deg |
| SoilGrids 2.0 | WCS maps of the box (36) | done | the field's own cell has a prediction (22 of 255 box cells have none); water held for plants (0-1 m) 146 mm at the field, 85-156 mm within 2 km |
| Gauge evidence | GPM_3IMERGM V07 gauge weight (3 x 3 cells) and GPCC V2022 station counts; the two global GPCC files are read from the demo's folder, not downloaded again | done: 297 of 297 months (2001-01 to 2025-09) | checks only. **Never gauge-dominated here:** the field cell's gauge weight is 22-62% a month in 2001-2016 and 37-65% from 2017 (yearly 40.5-54.7%); GPCC stations in the 1-degree box: 1.7 a month in 2011-2016, 1.2 in 2017-2020 |
| GRACE/GRACE-FO | the one global file held in `data/raw/grace/demo/`, reused (not downloaded again) | done: 261 months, 2002-04 to 2026-09 | regional context; cell 19.0-18.5 S, 47.0-47.5 E; unscaled trend -0.43 cm a year (OLS, for the record) |
| FAOSTAT | the bulk file held; Madagascar (area 129): rice, potato, wheat yields | done: 72 rows, 2001-2024 (flags A 22, E 49, X 1) | validation only; national means rice 2,894, potato 5,914, wheat 2,387 kg/ha (never shown to farmers) |
| GHCN-Daily | MA000067083 Antananarivo/Ivato, 7.4 km | done (2001-01-01 to 2025-08-23) | **validation only** (no `correction_label`, so no decision-A correction). Patchy: rain records per year 84-328 (over 300 only in 2003-2004); source flags S (2,697 rain records) and I (647) |
| Not fetched | MODIS, SMAP, ECOSTRESS (no number shown abroad uses them); NEX-GDDP (its own fetcher, another piece); DHM normals (Nepal only) | | |

### 1.19 Near-real-time weather for the twin's state now: NASA POWER and IMERG Late, 2026 (added 2026-11-14, build step 10)

`pipeline/fetch/now.py` -> `data/clean/demo/weather_now.parquet`, card `data/cards/demo/weather_now.json`; raw files in
`data/raw/power_now/demo/` and `data/raw/gpm_now/demo/late/`. `weather.parquet`, `power.parquet` and `gpm.parquet` are not
touched. Read by `scripts/run_twin_now.py` (the twin's state, METHOD_NOTES 60).

| Item | Value | Status |
| --- | --- | --- |
| Products | NASA POWER daily point API, community AG, one request for 2026-01-01 to 2026-11-13 (header sources GEOSIT, FLASHFLUX, POWER; days in local solar time); GPM IMERG Late V07 daily (`GPM_3IMERGDL`), 316 granules in CMR for 2026-01-01 to 2026-11-12, file versions **V07B, then V07C**, the box's 0.1 deg cells by GES DISC OPeNDAP (UTC days) | model-based (POWER); satellite, no monthly gauges (IMERG Late) |
| Raw attributes | printed before converting and kept in the card: POWER units per parameter, fill -999; IMERG `precipitation` in mm/day with its `_FillValue` | rule 12a |
| Last day of each input | POWER meteorology and PRECTOTCORR 10 Nov, **sunshine (ALLSKY_SFC_SW_DWN) 3 Nov**; IMERG Late 12 Nov (13 Nov not yet in CMR) | the state is **as of 3 Nov 2026**, set by POWER's sunshine |
| Fills, records dropped | POWER -999 -> missing; the 10 days after 3 Nov dropped, never filled or guessed; no fill in the field's IMERG cell; no POWER rain fill needed (307 of 307 days are IMERG) | rule 12c |
| Built how | exactly as `weather.parquet` (DATA_AUDIT 1.13): the Kathmandu-valley offsets and the frost quantile mapping fitted on the same 2001-2025 history, ET0 with the vapour pressure held from POWER at the field's 1,325 m, and the GPM break factors fitted on IMERG Final months applied to the 307 Late days (owner's answer 7). 2026 rain to 3 Nov: 1,171 mm (1,701 mm as published). **Check: the 2001-2025 history rebuilt by the same code equals `weather.parquet` in every column** (card `corrections.reproduction_of_weather_parquet`; `tests/test_twin_now.py`); the build stops if it does not | done |
| Spike flags | POWER against IMERG Late only (no station days in 2026): 1 day flagged, in the card | decision B |
| Caveats | IMERG Late changes file version within the year (V07B to V07C); Late sits at the un-gauged, too-wet level before scaling (VALIDATION 3.9b, 3.9c); 67 mm of scaled rain on 29-31 October (83 mm as published) sets the wet state of 3 Nov | |

### 1.20 Area map of the demo box (derived product; Local Impact 4a, added 2026-11-14)

| Item | Value | Status |
| --- | --- | --- |
| Inputs | the cached HLS-VI v2.0 box windows (1,471 granules, L30 and S30, tile T45RUL, 2013-04-24 to 2025-12) and ESA WorldCover 10 m 2021 v200 (1.14); nothing downloaded | read-only |
| Method | per 30 m pixel, the field diary's series and rules (rules.yaml `area_map`, committed before the first run, `cb85cc8`); NDVI guard -1 to 1 on every window (`scale_ndvi`), Fmask bits 0-5 zero | `scripts/run_area_map.py` |
| Cropland | WorldCover class 40 on a majority of the 10 m centres in a 30 m pixel: 47,866 pixels (4,308 ha, 43% of the box's 111,013 judged pixels); 31,150 wholly cropland. Every cropland pixel had at least 6 counted years | `data/checks/demo/area_map.json` |
| Accuracy | WorldCover 2021 v200 cropland, Asia: user's 80.6% +/- 2.8, producer's 82.7% +/- 2.5 (PVR v2.0, 2022-10-25, Table A2.4 p. 29; global 80.6 +/- 1.5 and 79.3 +/- 1.5, Table 2 p. 15). This answers the product-wide part of the TODO-VERIFY in 1.14; Nepal's own accuracy is not published | VERIFIED (report opened 2026-11-14) |
| Outputs | `site/data/area/demo_bare_days.png` (28.8 KB), `demo_seasons.png` (26.8 KB): 667 x 667 palette PNGs in EPSG:3857, exactly the fetch box, nearest neighbour from UTM 45N, about 15 m on the ground, non-cropland transparent; `site/data/area/demo.json` (bounds, classes, legend, numbers, sources) | written |
| Check | the map reproduces the field's own diary numbers | VALIDATION 3.23: PASS |
| Caveats | NDVI shows green cover, not which crop; mixed pixels (houses, trees) at field edges; WorldCover 2021 out of date in places; the bare threshold is untuned and moves the bare-day numbers a lot (METHOD_NOTES 83) | stated in the site file |

### 1.21 GLDAS-2.1 Noah, monthly (a check on the twin only; added 2026-11-14, owner's request): DOWNLOADED AND CLEANED

`pipeline/fetch/gldas.py`; table `data/clean/demo/gldas.parquet` (300 months), card `data/cards/demo/gldas.json`. **Use:** VALIDATION 4.2d only; never the twin's input, never shown to farmers.

| Item | Value | Status |
| --- | --- | --- |
| Product | `GLDAS_NOAH025_M` v2.1 (CMR `C1342986036-GES_DISC`), Noah 3.6 land-surface model, monthly means of 3-hourly steps, 0.25 degree; **model-based**. File attribute `source`: 'Noah_v3.6 forced with GDAS-AGRMET-GPCPv13rA1' | VERIFIED: CMR, file attributes |
| Access | GES DISC's own OPeNDAP (hydro1) answered **410 Service Retired** on 2026-11-14; NASA Earthdata Cloud OPeNDAP (DMR++ present) serves 3 x 3-cell DAP4 subsets, about 60 KB a month. Under 4 parallel requests the server answered 3 of 300 months with March 2001's granule: caught by the month guard, the module now checks every file's own `time_bnds` against the month asked for, and the three were fetched again | FOUND |
| Cell | row 350, col 1061: centre 27.625 N, 85.375 E, 27.5-27.75 N, 85.25-85.5 E (about 25 x 28 km); the whole fetch box lies in it | FOUND |
| Variables, units in | SoilMoi0_10cm, 10_40cm, 40_100cm, 100_200cm and RootMoist (kg m-2); Evap_tavg and Rainf_f_tavg (kg m-2 s-1); PotEvap, ESoil, Tveg, ECanop (W m-2); _FillValue -9999; no scale, offset or valid range (`vmin`/`vmax` are each file's global extremes) | VERIFIED: file attributes, checked on every read |
| Units out | kg m-2 = mm; m3/m3 = mm / layer thickness (100, 300, 600, 1,000 mm); fluxes x 86,400 = mm/day; W m-2 x 86,400 / 2.45 MJ/kg = mm/day (FAO-56 latent heat; Noah's own constant differs by about 2%, which no correlation sees) | FOUND |
| Guards | rule 12: soil moisture 0-0.6 m3/m3, rain 0-500 mm/day; every other water flux within +-500 mm/day (a unit check); a fill in the field's cell fails; 0 warnings. Values: 0-100 cm 0.106-0.329 m3/m3; ET 0.64-3.99 mm/day | FOUND |
| Levels | ET 779 mm a year (twin ETa 692); potential evaporation 2,108 mm a year (twin ET0 1,325: Noah's PotEvap is not grass-reference ET0); rain 1,027 mm a year (twin 1,853): GPCP-forced, **no 2017 step** | FOUND |
| Independence | GPCP v1.3 is gauge-adjusted (GPCC), so GLDAS may share some gauges with IMERG Final; its rain shows no 2017 jump | caveat |

## 2. Field outline over pixels

Rerun 2026-11-12 for the current placeholder field (60 m square at 27.690767 N, 85.441792 E;
`scripts/plot_pixels.py`, `data/checks/demo/field_pixels.json`, plots in `data/plots/pixels/demo/`). A pixel
counts when its centre lies inside the polygon: **WorldCover 42, NASADEM 4, HLS 4**; GRACE: the field lies in one
0.5 deg cell of one 3 deg mascon. GPM: the field lies in one 0.1 deg cell (centre 27.65 N, 85.45 E) of the 2 x 2 box. SMAP: one 9 km cell (1.5). MODIS (250 m) and ECOSTRESS (70 m) are
downloaded but the script does not draw them yet. POWER and GHCN are points. (The file held the rejected first
square until this rerun.)

## 3. Cross-checks

| Check | Result | Status |
| --- | --- | --- |
| POWER vs GHCN rain | **49 complete months in 2015, 2016, 2017, 2019, 2021, 2022: POWER 21.3% drier, r = 0.93, mean absolute error 46.8 mm per month** | RUN (`data/checks/demo/crosscheck_power_ghcn_NP000444540.json`) |
| POWER vs GHCN January Tmin | 205 shared days: station 3.7 C, POWER 7.5 C, **POWER +3.8 C** | RUN |
| POWER vs GHCN May-June Tmax | 829 shared days: station 29.4 C, POWER 29.5 C, **POWER +0.08 C** | RUN |
| Spike check B (rain > 50 mm and > 5x another source) | **170 flags on 120 days with GPM** (high source GPM 130, station 27, POWER 13; votes: gpm disagrees with the other two 82, undecided 37, no third source that day 33, POWER spike 10, station value suspect 8, real local storm 0), written to the power, station, weather and (from 2026-11-13) GPM cards. Before GPM existed: 9 days flagged. POWER high: 2009-07-28 (59.2 vs 0.0), 2024-06-25 (74.2 vs 0.0), 2024-06-26 (114.3 vs 4.3), 2024-09-25 (55.9 vs 0.8), **2025-03-01 (233.7 vs 3.8)**. Station high: 2012-09-13 (134.6 vs 16.0), 2018-04-03 (51.1 vs 0.2), 2021-07-11 (90.9 vs 2.7), 2022-08-10 (76.2 vs 14.2). The 2024-09-27/28 flood is not flagged (ratios under 5). Nothing deleted. The station's 0.0 on the POWER-high days (2009-07-28, 2024-06-25) may be a missing synoptic report rather than a dry day (the station is synoptic-derived, 1.11): unverified, so the GPM vote decides | RUN |
| Day alignment C | POWER vs station daily rain: best lag **0** (see 1.11). **GPM vs station: best lag -1** (Pearson 0.509 / 0.405 / 0.221 at -1 / 0 / +1; `crosscheck_gpm_ghcn_NP000444540.json`): station day d pairs best with GPM's UTC day d - 1, because the station's GSOD rain "may include latter part of previous day". Monthly comparisons are barely affected; the spike vote compares the same calendar day and is (REVIEW_2 M9) | RUN |
| GPM vs POWER vs GHCN rain | Over 49 complete station months GPM as published is +41.2% (r 0.915, MAE 77.6 mm); the twin's corrected rain +8.3% (MAE 38.7 mm); over all 65 shared months MAE 34.7 mm, r 0.950 (CHIRPS 36.6, 0.938). The cause of the gap is the 2017 break (1.2; VALIDATION 3.9, 3.9b) | RUN |
| MODIS vs HLS NDVI, 2013 on | 671 pairs within 8 days: r 0.83, MODIS minus HLS -0.085; where HLS shows bare ground MODIS is below 0.25 only 45% of the time (VALIDATION 3.10) | RUN |

## 4. Switch-off test

**Run on the real export, 2026-11-13 (REVIEW_2 Phase 3).** Each input was perturbed in memory or in a private copy
of the repository (the project's own functions, nothing written here) and the whole plan step was rerun: generate,
replay rain-fed and watered, score, Pareto, pick three. "Changes" counts the current plan's 24 exported years
(harvest integer / dry days / event). Base case: the export itself, reproduced exactly.

| Input | Switched off or perturbed how | What changes in the export | Verdict |
| --- | --- | --- | --- |
| GPM IMERG (the twin's rain) | GPM as published instead of the corrected rain | harvest in 8 years, dry days in 6, event in 5; water and soil-kept scores of all three plans; (exported as the `uncorrected_rain` ranges) | **used** |
| NASA POWER (ET0: temperature, humidity, wind, sunshine) | ET0 -10% / +10% | every year's harvest and dry days; plan harvest 72.3 -> 75.5 / 69.5 (current), 89.6 -> 93.2 / 86.0, 80.8 -> 84.0 / 78.1 | **used** |
| GHCN station (temperature correction A, frost quantile mapping) | no station: uncorrected POWER | ET0 1,325 -> 1,285 mm/yr; plan harvest +1.5 to +1.7 points (72.3 -> 73.9, 89.6 -> 91.1, 80.8 -> 82.3); frost Tmin nights below 0 C 28 -> 1 and the median coldest January night 0.6 -> 3.9 C, so January's frost band would fall from "risk" to "none" | **used** |
| SoilGrids (theta_fc, theta_wp only) | plant-available water -20% / +20% | all 24 years; plan harvest 72.3 -> 68.6 / 75.8, 89.6 -> 83.6 / 94.0, 80.8 -> 76.8 / 84.6. Not `soil_kept` (K cancels between plans) and not the events | **used** |
| `config/crops.json` (root depth) | FAO-56 Table 22's smaller depths | all 24 years; 72.3 -> 66.1, 89.6 -> 79.7, 80.8 -> 76.2 | **used** |
| GRACE/GRACE-FO | direction "steady" instead of "falling" | `diary.groundwater`; water scores 38.2 -> 58.8, 50.8 -> 67.2, 44.5 -> 63.0 (the 1.5x on irrigation); no harvest number | **used** |
| HLS-VI | (traced and recomputed from the raw images) | `diary.bare_days`, `diary.guess`, `diary.months[].cover`, `method.season_detection`. Not `plans.score.cover`: that score is the share of the year inside crop seasons from the crop calendar (`pipeline/plans/score.py`) | **used** |
| NASADEM (elevation, by hand into `demo.yaml`) | POWER's 1,269 m instead of 1,325 m | ET0 +0.08%: 0 of 24 harvest integers, 2 of 24 dry-day counts. Slope is read by no code | **barely used** |
| DHM normals (`config/dhm_normals_1991_2020.csv`) | (traced) | `method.rain_correction.rain_mm_per_year.station_normal` and its sentence only | **used for one number** |
| MODIS MOD13Q1 | (traced) | **nothing**: bare days, cover months, the guess and the method page use HLS years only. Its `sources` row now says so | **not used** |
| SMAP, ECOSTRESS, WorldCover, FAOSTAT, CHIRPS, IMERG Late, GPCC, known events | (traced) | nothing, by design: checks, or the placement of the placeholder square (WorldCover); none is in `sources` | **checks only** |
| NEX-GDDP-CMIP6 | not fetched | `future` is still MOCK (step 9) | **not yet** |

The expectations written here before the pipeline existed were wrong in three places, now corrected: HLS and MODIS do
not change `plans.score.cover`; SoilGrids and NASADEM do not change `soil_kept` (K and LS cancel between plans on one
field); SMAP does not feed `sure` and ECOSTRESS does not feed section status (neither is built).

**Does the plan ranking hold?** In every case above the two suggested rotations stay **rice then wheat** and **rice
then lentil**. The sowing position of the rice moves in three cases (ET0 -10%, the smaller root depths, a single
yearly rain factor), and with wheat's roots at 1.0 m the two suggested plans are level (80.5 against 80.8). Scaling
the 92 IMERG Late days as well changes no harvest, dry-day count or event in any of the three plans; only `soil_kept`
of the two suggested plans rises from 74 to 75 (VALIDATION 4.4).

## 5. Data cards

Written (all in `data/cards/demo/`, 20 on 2026-11-13): `power.json`, `ghcn_NP000444540.json`, `faostat_yields.json`,
`weather.json`, `worldcover.json`, `nasadem.json`, `grace.json`, `soilgrids.json` (WCS; there is no `soilgrids_rest.json`:
the REST point service was never used for the twin), `gpm.json`, `gpm_late_check.json`, `chirps.json`,
`greenness_field.json`, and from the cache (REVIEW_NOTES L7) `hls_l30.json`, `hls_s30.json`, `eco_lste.json`,
`eco_esi.json`, `modis.json`; new on 2026-11-13 (REVIEW_2): `smap.json`, `dhm_bulletins.json`, `gauge_evidence.json`.
Each has every rule-12 field plus `range_warnings`; the power, station, weather and (from 2026-11-13) GPM cards carry
`cross_source_flags` (B); the weather card carries `corrections` (A) and the ET0 elevation used. **Stale text inside
cards (REVIEW_2 L1, not rebuilt because that needs the network or would re-run a fetch):** `gpm.json` time zone and
`ghcn_NP000444540.json` distance and day boundary still read TODO-VERIFY although both are verified above (1.2, 1.11);
`power.json` names the first placeholder's point (same POWER cell). `soilgrids.json` was rebuilt offline on 2026-11-13
(its `units_source` is current, and its `summary` holds the neighbourhood range: owner's answer 10).

## 6. TODO-VERIFY (open)

1. POWER: per-value quality flags; grid edges for a cell plot; cause of the 2001-2003 low rain totals and of the high daytime temperature and low humidity of the same years (REVIEW_2 H8; a likely cause, not verified: MERRA-2's land surface is driven by its own gauge-corrected rain, about half of normal here in those years).
2. IMERG: ~~daily files cover the UTC day~~ (closed verified 2026-11-12); meaning of `precipitation_cnt_cond`.
3. ~~HLS: list one granule's layers to find the cloud mask; its bits.~~ Closed: `Fmask`, bits from the file tag (1.3, 1.15).
4. ~~MODIS: confirm the three expected layer names by listing a file.~~ Closed: AppEEARS product API (1.4, 1.15).
5. SMAP L3: ~~which bit of `retrieval_qual_flag` means "recommended quality"~~ (closed verified 2026-11-12); ~~L4 day boundary~~ (closed 2026-11-13: the eight 3-hourly values stamped 01:30 to 22:30 UTC are averaged per UTC day, 1.5). Open: which rain forcing SMAP L4 v008 uses over Nepal (if it shares gauges with IMERG the SMAP check is less independent; VALIDATION 4.2b).
6. ~~SoilGrids: why the demo point's own cell has no prediction.~~ Closed 2026-11-13 (REVIEW_2): ISRIC's FAQ "Which soil mask was used?" says the mask comes from the ESA land-cover map with urban (class 190), inland water, glaciers and bare areas masked out (docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html). That the field's own cell is class 190 there is inferred from the mask's shape, not read from the map.
7. ECOSTRESS V003: ~~units, fill, flags~~ (closed verified 2026-11-12); time stamps.
8. NEX-GDDP-CMIP6: ~~units, wind height~~ (closed verified 2026-11-12); version choice (v2.0) and calendars at fetch time; citation.
9. ~~GRACE: variable, unit, grid, gap between missions.~~ Closed: file attributes (1.10).
10. GHCN vs DHM: 194.1 vs 239.7 mm at Kathmandu Airport on 2024-09-28; access to DHM Bhaktapur and
    Changu Narayan series (partly closed 2026-11-13: six months of 2025 transcribed from DHM's bulletins, 1.16; a longer series needs DHM).
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
