# CREDITS.md

Every dataset, library and use of SI (AI) goes here the moment it is used (CLAUDE.md rule 10).
Citation texts in quotes are copied verbatim from the official pages named (opened 2026-11-11).

## Data and metadata services

Rows marked *metadata* were used only to check names, versions and units. Data that entered the
pipeline is also listed under "Data fetched by the pipeline" below (written by the fetch modules).

### NASA POWER (data, model-based)

Daily API v2.10.3: T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR at 27.67 N, 85.43 E,
2001 to 2025 (step 2). Referencing guide: https://power.larc.nasa.gov/docs/referencing/

- POWER's Reference: "The data was obtained from National Aeronautics and Space Administration (NASA)
  Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the
  NASA Earth Science Division."
- POWER's Data Reference (their template is "The data was obtained from the POWER Project's Hourly
  2.x.x version on YYYY/MM/DD."; filled in for our use): "The data was obtained from the POWER Project's
  Daily 2.10.3 version on 2026/11/11."
- POWER asks users to send a reference, web link or description of the use to
  larc-power-project@mail.nasa.gov (TODO: owner to send after submission).

### NASA Common Metadata Repository (CMR) and Earthdata (metadata)

Product names, versions, coverage dates, variable units, fill values and scale factors (DATA_AUDIT.md).
**No official citation for CMR or its search API exists** (none on the CMR page, the API docs or its
GitHub repository). We follow NASA's general guidance instead,
https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance :
"NASA data are freely accessible; however, when you publish these data or works based on the data, we
request that you cite the datasets within the text of the publication and include a reference to them
in your reference list." Each NASA dataset gets its own DOI citation when its data enter the pipeline.
Guidance document: Wilson, Bruce E. (2025). Data Use and Citation Guidance. NASA Earth Science Data and
Information System Standards Coordination Office. doi:10.5067/DOC/ESCO/ESDS-RFC-055

### ISRIC SoilGrids 2.0 (data, step 4; model-based map)

"Poggio, L., de Sousa, L. M., Batjes, N. H., Heuvelink, G. B. M., Kempen, B., Ribeiro, E., and
Rossiter, D.: SoilGrids 2.0: producing soil information for the globe with quantified spatial
uncertainty, SOIL, 7, 217–240, https://doi.org/10.5194/soil-7-217-2021, 2021." Licence: "The SoilGrids
maps are publicly available on the SoilGrids website under the CC-BY 4.0 License."
(https://www.isric.org/explore/soilgrids). Used: wv0033, wv1500, sand, clay, soc, bdod at six depths to
2 m via the REST API (beta), from the nearest cell with values, 750 m from the demo point.

### NEX-GDDP-CMIP6 (metadata so far)

Public bucket `nex-gddp-cmip6` (AWS Open Data), listing of 35 model folders. Citation: TODO-VERIFY
(step 9).

### NOAA NCEI GHCN-Daily, Version 3.35 (data, validation and station correction)

Station NP000444540 Kathmandu Airport, PRCP, TMAX, TMIN, 2001 to 2025. From the GHCN-Daily readme:
Menne, M.J., I. Durre, R.S. Vose, B.E. Gleason, and T.G. Houston, 2012: An overview of the Global
Historical Climatology Network-Daily Database. J. Atmos. Oceanic Technol., 29, 897-910,
doi:10.1175/JTECH-D-11-00103.1. Dataset: Menne et al. 2012, Global Historical Climatology Network -
Daily (GHCN-Daily), Version 3.35, NOAA National Climatic Data Center, doi:10.7289/V5D21VHZ, accessed
2026-11-11.

### FAOSTAT (data, validation layer 4.3 only)

Domain QCL "Production: Crops and livestock products" (FAO Statistics Division, faostat@fao.org), bulk
file dated 2025-12-31, Nepal rice, wheat and maize yields 2001 to 2024. Formal citation text:
TODO-VERIFY on the FAOSTAT site.

### Methods

- FAO-56: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration: guidelines
  for computing crop water requirements. FAO Irrigation and Drainage Paper 56. FAO, Rome.
  https://www.fao.org/4/x0490e/x0490e00.htm (Examples 2, 8, 18 reproduced in tests/test_et0.py).
- FAO-56 Tables 11, 12, 14, 22 and 24 (Chapter 6: https://www.fao.org/4/x0490e/x0490e0b.htm; Chapter 8:
  https://www.fao.org/4/x0490e/x0490e0e.htm) and worked Examples 28, 30, 36, 37, 39: crop library and
  bucket tests.
- FAO-66: Steduto, P., Hsiao, T.C., Fereres, E., Raes, D. (2012). Crop yield response to water. FAO
  Irrigation and Drainage Paper 66, Table 1 (Ky from FAO-33). https://www.fao.org/4/i2800e/i2800e02.pdf
- ASCE-EWRI: Allen, R.G., Walter, I.A., Elliott, R.L., Howell, T.A., Itenfisu, D., Jensen, M.E., Snyder,
  R.L. (eds.) (2005). The ASCE Standardized Reference Evapotranspiration Equation. ASCE, Reston, VA.
  doi:10.1061/9780784408056. Task Committee final report (Jan 2005), eq. 18, p. 20: "Rs/Rso = relative
  solar radiation (limited to 0.3 ≤ Rs/Rso ≤ 1.0)" (copy: https://www.mesonet.org/images/site/ASCE_Evapotranspiration_Formula.pdf).
- USDA NRCS (1986). Urban Hydrology for Small Watersheds, TR-55, 2nd ed., Table 2-1 and Table 2-2b
  (copy: https://ponce.sdsu.edu/tr55.pdf); USDA NRCS National Engineering Handbook Part 630, Chapter 7
  Hydrologic Soil Groups (2009, https://directives.nrcs.usda.gov/sites/default/files2/1712930597/11905.pdf),
  Chapter 9 Table 9-1 (2004, https://directives.nrcs.usda.gov/sites/default/files2/1712930607/7306.pdf),
  Chapter 10 Example 10-1 (https://directives.nrcs.usda.gov/sites/default/files2/1712930608/7300.pdf).
- Gudmundsson, L., Bremnes, J. B., Haugen, J. E., and Engen-Skaugen, T. (2012). Technical Note:
  Downscaling RCM precipitation to the station scale using statistical transformations – a comparison of
  methods. Hydrol. Earth Syst. Sci., 16, 3383–3390, doi:10.5194/hess-16-3383-2012.
- Themeßl, M. J., Gobiet, A., Leuprecht, A. (2011). Empirical-statistical downscaling and error correction
  of daily precipitation from regional climate models. Int. J. Climatol. 31(10), 1530–1544,
  doi:10.1002/joc.2168.

### Crop calendars (step 4)

- FAO Crop Calendar, Nepal, "B. Hill Agro-ecological Zone" (lastUpdated 26/02/2021),
  https://api-cropcalendar.apps.fao.org/api/v1/countries/NP/cropCalendar?language=en&aez=002 (read 2026-11-12).
- Chaulagain, B., Bhattarai, R. K., Timalsina, H. P., Neupane, R., Kaduwal, S. (2025). Productivity and Land
  Use Efficiency of Maize Varieties under Different Row Spacings in a Maize–Finger Millet Relay Cropping
  System of the Mid-Hills of Nepal. Agronomy Journal of Nepal 9, 172–179, doi:10.3126/ajn.v9i1.91446.
- FAO GIEWS Country Brief, Nepal (18 Aug 2026), https://www.fao.org/giews/countrybrief/country.jsp?code=NPL&lang=en

### Placeholder field and box fetches (2026-11-12)

- ESA WorldCover 10 m 2021 v200: Zanaga, D., Van De Kerchove, R., Daems, D., et al. (2022). ESA WorldCover
  10 m 2021 v200, doi:10.5281/zenodo.7254221. CC BY 4.0. Tile N27E084, box window (placeholder field only).
- NASADEM: NASA JPL (2020). NASADEM Merged DEM Global 1 arc second V001. NASA EOSDIS LP DAAC,
  doi:10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001. Tile n27e085.
- GRACE/GRACE-FO: Wiese, D. N., Yuan, D.-N., Boening, C., Landerer, F. W., Watkins, M. M. JPL GRACE and
  GRACE-FO Mascon Ocean, Ice, and Hydrology Equivalent Water Height CRI Filtered RL06.3Mv04. PO.DAAC,
  CMR C3195527175-POCLOUD (citation text TODO-VERIFY on the PO.DAAC landing page).
- AppEEARS Team (2026). Application for Extracting and Exploring Analysis Ready Samples (AppEEARS). NASA
  EOSDIS LP DAAC, USGS EROS, https://appeears.earthdatacloud.nasa.gov (service used to cut MOD13Q1.061,
  SPL3SMP_E.006 and SPL4SMGP.008 to the box; product citations added when the downloads are cleaned).
- HLS-VI v2.0 (HLSL30_VI, HLSS30_VI) and ECOSTRESS tiled LSTE and ESI (V003, V002 where V003 lacks an
  overpass): NASA LP DAAC; read as box windows of the cloud-optimised GeoTIFFs. Product citations are
  added when the downloads are cleaned (TODO-VERIFY each DOI on its landing page).
- GPM IMERG Final/Late daily V07 (Huffman et al., NASA GES DISC): fetcher built; not yet downloaded (the
  account must accept the GES DISC EULA).

- ISRIC SoilGrids 2.0 through its WCS (maps.isric.org), 2026-11-12, for the whole fetch box: Poggio, L., de Sousa,
  L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified
  spatial uncertainty. SOIL 7:217-240, doi:10.5194/soil-7-217-2021. CC BY 4.0.

### Event rule sources (2026-11-12, opened by a research sub-agent)

- Gibbs, W. J., Maher, J. V. (1967). Rainfall deciles as drought indicators. Bureau of Meteorology
  Bulletin No. 48; decile classes as given by Hayes, M. J., "Drought Indices", National Drought
  Mitigation Center (archived 2009-05-10).
- WMO and GWP (2016). Handbook of Drought Indicators and Indices, WMO-No. 1173, pp. 11-13.
- WMO (2012). Standardized Precipitation Index User Guide, WMO-No. 1090; McKee, T. B., Doesken, N. J.,
  Kleist, J. (1993). 8th Conference on Applied Climatology (not used: SPI needs a gamma fit; kept as
  the alternative).
- Government of Nepal, Department of Hydrology and Meteorology, Meteorological Forecasting Division.
  Terms used in Weather Forecasting in Nepal, https://dhm.gov.np/mfd/api/image/forecast-terminology/
- Zheng, B., Chapman, S. C., Christopher, J. T., Frederiks, T. M., Chenu, K. (2015). Frost trends and their
  estimated impact on yield in the Australian wheatbelt. J. Exp. Bot. 66(12):3611-3623, doi:10.1093/jxb/erv163.
- Frederiks, T. M., Christopher, J. T., Sutherland, M. W., Borrell, A. K. (2015). Post-head-emergence
  frost in wheat and barley. J. Exp. Bot. 66(12):3487-3498, doi:10.1093/jxb/erv088.
- Snyder, R. L., de Melo-Abreu, J. P. (2005). Frost Protection: fundamentals, practice and economics, Vol. 1.
  FAO Environment and Natural Resources Series 10, Ch. 4, Table 4.5 (potato critical temperatures),
  https://www.fao.org/4/y7223e/y7223e0a.htm
- Seppanen, M. M., Nissinen, O., Perala, S. (2001). Freezing and low temperature photoinhibition tolerance in
  cultivated potato and potato hybrids. Agric. Food Sci. Finland 10:153-163, doi:10.23986/afsci.5690.
- Sepaskhah, A. R., Yousofi-Falakdehi, A. (2010). Pakistan J. Biol. Sci. 13(22):1099-1105,
  doi:10.3923/pjbs.2010.1099.1105: "where Ky is unknown it is suggested to use Ky = 1" (supports the
  owner's assumed Ky; no seasonal rice Ky found in any source opened).
- Horn, B. K. P. (1981). Hill shading and the reflectance map. Proc. IEEE 69(1):14-47 (slope method).
- Moritz, H. (2000). Geodetic Reference System 1980. J. Geodesy 74:128-133 (mean Earth radius 6371.0088 km).

### Plain-word and crop-explainer sources (2026-11-12, opened by a research sub-agent)

Cited in `pipeline/words/crop_explainers.json` and `glossary.json`, with page or section and a verbatim quote
for each claim (copied from notes/parallel_session.md).

- FAO (2016). Soils and pulses: symbiosis for life. https://www.fao.org/4/i6437e/i6437e.pdf
- FAO Newsroom (2024). World Pulses Day 2024: Shining the spotlight on the vital role of pulses in promoting soil
  health and nourishing people.
- FAO Conservation Agriculture pages "Benefits of CA", "Soil organic cover" and "Species diversification" (no
  date; accessed 2026-11-12).
- FAO-56, Chapters 1 and 8 (already credited under Methods).
- FAO Crop Calendar, Nepal Hill zone (already credited under Crop calendars).
- FAO (2023). International Year of Millets 2023: About. https://www.fao.org/millets-2023/about/en
- FAO and ICRISAT (1996). The World Sorghum and Millet Economies: Facts, Trends and Outlook, Annex I.
- FAO (1998). FAO's Emergency Activities: Technical Handbook Series, Phase One: Prevention.
- FAO AGROVOC concepts c_6662 and c_1936.
- Paudel, G. P., Devkota, M., Keil, A., McDonald, A. J. (2020). Climate and landscape mediate patterns of low
  lentil productivity in Nepal. PLoS ONE 15(4): e0231377 (CIMMYT).
- ICRISAT (n.d.). Finger millet: overview. https://icrisat.org/crops/finger-millet/overview
- NARC NSSTRC (2020). Annual Report 2076/77 (2019/2020), National Seed Science Technology Research Centre, Khumaltar.
- NASA Earth Observatory (2000). Measuring Vegetation.

## Libraries (installed in `.venv`, Python 3.12.9)

Licences are read from each package's installed metadata.

| Library | Version | Licence | Used for |
| --- | --- | --- | --- |
| numpy | 2.5.4 | BSD-3-Clause (and bundled MIT, 0BSD, Zlib, CC0-1.0) | data guards, ET0 |
| pandas | 3.1.1 | BSD-3-Clause | tables, review pack |
| xarray | 2026.9.0 | Apache-2.0 | (from step 6) gridded data |
| pyarrow | 26.0.1 | Apache-2.0 | parquet |
| PyYAML | 6.0.3 | MIT | config files |
| jsonschema | 4.26.0 | MIT | contract validation |
| requests | 2.34.2 | Apache-2.0 | HTTP fetches |
| matplotlib | 3.11.2 | Matplotlib licence (PSF-based) | review plots |
| pytest | 9.2.0 | MIT | tests |
| pyet | 1.5.0 | MIT | step 3: independent reference for ET0 in the tests |
| earthaccess | 0.19.0 | MIT | Earthdata search, login (~/.netrc) and downloads (owner's go 2026-11-12) |
| h5py | 3.16.0 | BSD-3-Clause | HDF5 / netCDF-4 files: GRACE, GPM subsets, AppEEARS output (owner's go 2026-11-12) |
| rasterio | 1.5.2 (bundles GDAL 3.12.2) | BSD-3-Clause | GeoTIFF / COG windows: WorldCover, NASADEM, HLS, ECOSTRESS (owner's go 2026-11-12) |
| python-dateutil | 2.9.0.post0 | BSD / Apache-2.0 (dual) | dependency; pinned after earthaccess downgraded it |
| affine, click | 3.0.1, 8.5.1 | BSD-3-Clause | rasterio dependencies |

## SI (AI) use

| Tool | Date | What it produced | Reviewed by |
| --- | --- | --- | --- |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Step 1 code and tests, `schema.json`, `index_schema.json`, mock data, data guards, backup and review-pack scripts, DATA_AUDIT.md, VALIDATION.md. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Contract changes (A13, D7), guard change (D2), step 2 POWER fetch, GHCN fetch, layer-3 checks and cross-checks, CLAUDE.md edits (D1 to D7, SI components, build order), MASTER_PROMPT.md (owner's text, copied), VALIDATION.md and DATA_AUDIT.md rewrites. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with two research sub-agents | 2026-11-12 | Step-3 review items (quantile mapping, rain vote, SoilGrids fetch), build step 4 (crop library, bucket, runoff, yield, season test). Two sub-agents opened FAO-56/FAO-66, TR-55/NEH, FAO Crop Calendar, ASCE-EWRI and quantile-mapping sources. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with two research sub-agents | 2026-11-11 | Decisions A to H (station correction, spike check, day alignment, rain fill-in, sourced known events, FAOSTAT, citations, history scan), build step 3 (ET0), rules.yaml. Sub-agents opened official pages for the citations, FAO-56 worked examples and the known-events sources. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with one research sub-agent and one review sub-agent | 2026-11-12 (later) | Step-4 review answers (cold-night roles, assumed Ky, irrigation bug fix, approvals), step 5 without GPM (replay, events, export guard, METHOD_NOTES.md), placeholder field (WorldCover), fetchers for WorldCover, NASADEM, GRACE, AppEEARS, HLS/ECOSTRESS windows and GPM. The research sub-agent opened the event-rule and Ky sources above. The review sub-agent ran the **"silent-failure-hunter" agent prompt from the ECC selection in the team's claude-code-kit** (ECC, MIT licence) over the new code; its 10 findings were verified and the real ones fixed test-first. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code (parallel words session), with one research sub-agent | 2026-11-12 | Build-time drafting of plain-language texts and Nepali translations (`pipeline/words/`: glossary, crop explainers, five-tab templates, tips, screen texts), and a source search for the crop explainers (FAO, CGIAR centres, NARC; sources listed above). Nothing calls an AI service from the site. Details in SI_LOG.md | Owner: English and the listed choices (decided 2026-11-12); Nepali: native-speaker review pending |
| Claude Opus 5.5 (Anthropic), via Claude Code, with one audit, three fix and one research sub-agent | 2026-11-12 (late night) | REVIEW_NOTES fixes (H1-H4, M1-M13, L1-L7: code, tests, rules.yaml and docs), the owner's words decisions (Bikram Sambat months, soil temperature), the Nepali tabs/tips contract change, reruns of the dry run, season test, pixel check and cleaned tables from cache. The research sub-agent opened FAO/IIASA/ISRIC pages on HWSD v2 (licence and access; not used). Details in SI_LOG.md | Owner: to fill in after review |
| Claude Code kit (team-prepared zip, 2026-11-07): superpowers plugin (MIT, already installed: its test-driven-development skill guided the work) and an ECC selection (MIT) | 2026-11-12 | Workflow guidance and one review prompt (above). The ECC skills and agents were **not installed** into `~/.claude` (blocked as a self-modification; the owner can copy them) | Owner |

## Data fetched by the pipeline

- NASA POWER Daily API v2.10.3 (model-based), field `demo`, 2001-01-01 to 2025-12-31, fetched 2026-11-11
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `demo`, 2001-01-01 to 2025-08-24, fetched 2026-11-11
- FAOSTAT QCL bulk file (FAO), Nepal rice, wheat and maize yields, 2001 to 2024, fetched 2026-11-11 (validation only)
- ISRIC SoilGrids 2.0 REST API (model-based, CC-BY 4.0), field `demo`, cell 750 m from the field point, fetched 2026-11-12
- NASA POWER Daily API v2.10.3 (model-based), field `demo`, 2001-01-01 to 2025-12-31, fetched 2026-11-12
- ESA WorldCover 10 m 2021 v200 (CC BY 4.0), field `demo` fetch box, fetched 2026-11-12 (placeholder field only)
- NASADEM_HGT v001 (NASA JPL, LP DAAC), field `demo` fetch box, fetched 2026-11-12
- JPL GRACE/GRACE-FO mascon CRI RL06.3Mv04 (PO.DAAC), cell holding field `demo`, 2002-04 to 2026-09, fetched 2026-11-12
