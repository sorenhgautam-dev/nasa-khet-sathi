# CREDITS.md

Every dataset, library and use of SI (AI) goes here the moment it is used (CLAUDE.md rule 10).
Citation texts in quotes are copied verbatim from the official pages named (opened 2026-11-11).

## Hosting

The site is served by **Vercel** (vercel.com) as static files from `site/` (owner, 2026-11-13): no build step, no
server functions, no environment variables. GitHub Pages is not used.

## Site design

- **Design:** our UI teammate. The look, the seven-step flow (phone and web screens), the wording the site starts from and
  the motion (clouds, birds, sun, the robot, the screen changes) come from our UI teammate's Claude Design artifact
  "Khet Sathi: App Screens", exported to `design/` on 2026-11-14. The static site in `site/` was built from it by SI
  (see SI_LOG.md, 2026-11-14).
- **Images:** `site/img/bg-phone.svg`, `bg-web.svg`, `bg-home.svg` and `farm.webp` are our UI teammate's images from
  `design/assets/` (the farm illustration re-encoded smaller with cwebp; no other change). `site/img/icon.svg` redraws the
  design's leaf logo.
- **Fonts:** Inter Tight, Inter and Mukta (SIL Open Font License 1.1), loaded from Google Fonts after the first screen,
  with `font-display: swap` and system fallbacks. Not self-hosted: the woff2 files the site uses (about 220 KB: Inter and Inter Tight
  variable, Mukta 400 and 700) would not fit the first screen's 300 KB.
- **Map:** Leaflet 1.9.4 (BSD 2-Clause; self-hosted in `site/vendor/leaflet/` with its LICENSE), with map tiles from
  OpenStreetMap (© OpenStreetMap contributors, ODbL; https://www.openstreetmap.org/copyright), credited on every map.
- **Charts:** drawn as inline SVG and HTML by `site/js/how.js`; no chart library and no outside chart service.

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
2 m via the REST API (beta), from the nearest cell with values, 750 m from the demo point (superseded 2026-11-12: the
twin's soil now comes from the WCS maps of the whole box, the nearest cell with a prediction in all 36 maps, 859 m
south-east of the placeholder field; of the six properties the twin reads only the two water contents).

### NEX-GDDP-CMIP6 (data, model-based; the 2040 outlook, build step 9)

- Dataset: NASA Earth Exchange Global Daily Downscaled Projections - CMIP6 (NEX-GDDP-CMIP6), NASA Center for Climate
  Simulation, 2021, doi:10.7917/OFSG3345 (resolves to the NCCS page; verified 2026-11-14). Files of version 2.0, read
  as point answers from NASA NCCS THREDDS (https://ds.nccs.nasa.gov/thredds, AMES/NEX/GDDP-CMIP6): pr, tasmax, tasmin
  at one 0.25 deg cell, historical 1995-2014 and ssp245 / ssp585 2026-2040; the models used are listed in
  `data/cards/<field>/nexgddp.json` and `data/checks/<field>/future.json`. Public bucket `nex-gddp-cmip6` (AWS Open
  Data) lists the same 35 model folders.
- Paper: Thrasher, B., Wang, W., Michaelis, A., Melton, F., Lee, T., Nemani, R. (2022). NASA Global Daily Downscaled
  Projections, CMIP6. Scientific Data 9, 262, doi:10.1038/s41597-022-01393-4 (verified via Crossref 2026-11-14; NCCS's
  v2 Tech Note misprints it as "9 (254)"). The files' own `references` attribute cites the BCSD method: Thrasher et al.
  2012, Hydrol. Earth Syst. Sci. 16, 3309-3314.
- Terms: each file's `cmip6_license` attribute, recorded per model and variable in the model's manifest
  (`data/raw/nexgddp/<cell>/<model>/manifest.json`) and in the card: CC-BY 4.0 or CC-BY-SA 4.0 (e.g. KACE-1-0-G: pr
  CC-BY 4.0, tasmax and tasmin CC-BY-SA 4.0). The NEX-GDDP-CMIP6 v2 Tech Note (31 May 2025, sec. 7, p. 33) says
  derivatives "are governed by the original Terms of use" and points to that attribute; the AWS registry page says that
  "as of September 2022, all NEX-GDDP-CMIP6 outputs are made available under a blanket Creative Commons Zero license
  (CC0)", and the CMIP6 Terms of Use (PCMDI, version 6.2, 12 October 2022) say the CC BY-SA and CC BY-NC-SA licences
  "were relaxed in October 2022" to CC BY 4.0. Raw files are never redistributed (`data/` is git-ignored); the site
  shows only derived harvest percentages, with this attribution. Acknowledgement asked by the CMIP6 Terms of Use: "We
  acknowledge the World Climate Research Programme, which, through its Working Group on Coupled Modelling, coordinated
  and promoted CMIP6. We thank the climate modeling groups for producing and making available their model output, the
  Earth System Grid Federation (ESGF) for archiving the data and providing access, and the multiple funding agencies
  who support CMIP6 and ESGF." The terms also ask for a table of the models and institutions (in the card's summary).
- Comparison only (VALIDATION 4.7): World Bank Climate Change Knowledge Portal, "Projected Climate Data, CMIP6
  0.25-degree" (CC BY 4.0), https://datacatalog.worldbank.org/search/dataset/0042297, Nepal annual anomalies 2020-2039
  vs 1995-2014 (read from its API by a research sub-agent, 2026-11-14); DHM (2024), "Update of Climate Change Study of
  Nepal", Department of Hydrology and Meteorology, Government of Nepal (context only).
- Method sources for the humidity rule (rules.yaml future.humidity): Held, I. M., Soden, B. J. (2006). Robust
  responses of the hydrological cycle to global warming. J. Climate 19(21), 5686-5699, doi:10.1175/JCLI3990.1 (p. 5687:
  "climate models tend to maintain a fixed tropospheric relative humidity as they warm"); Byrne, M. P., O'Gorman, P. A.
  (2016). Understanding decreases in land relative humidity with global warming. J. Climate 29(24), 9045-9061,
  doi:10.1175/JCLI-D-16-0351.1 (relative humidity "tends to ... decrease substantially over land"). Both verified by a
  research sub-agent, 2026-11-14.

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
- FAO-56 Chapter 7 (https://www.fao.org/4/x0490e/x0490e0c.htm, read 2026-11-14): eqs. 71-79, Table 19 and worked
  Examples 31 and 35: bare-soil evaporation from the surface layer (build step 2a, `pipeline/twin/evaporation.py`,
  tests/test_evaporation.py).
- Soil Science Society of America (2022). Glossary of Soil Science Terms, entry 'soil texture', p. 115
  (https://agronomy.org/files/publications/soils-glossary/table-5.pdf, read 2026-11-14): USDA texture classes for the
  REW of FAO-56 Table 19.
- Proposal 2c only (rules.yaml paddy_rainfed, not applied; opened 2026-11-14 by a research sub-agent): Bouman, B.A.M.,
  Barker, R., Humphreys, E., Tuong, T.P. et al. (2007). Rice: feeding the billions. Ch. 14 in Water for Food, Water for
  Life (IWMI/Earthscan), Box 14.2; Balwinder-Singh et al. (2019). Field Crops Research 239:92-103, sec. 2.3.2; Han, E.,
  Montes, C., Hussain, S.G., Krupnik, T.J. (2024). Climatic Change 177:77; Chaulagain et al. (2022). Agronomy Journal of
  Nepal 6(1):87-94; Adhikari, Mehera & Haefele (2013). American Journal of Plant Sciences 4(12C):146-155; Brouwer, Prins
  & Heibloem (1989). Irrigation Water Management Training Manual 4, Irrigation Scheduling, FAO, sec. 4.4; Sri Lanka
  Department of Agriculture (RRDI), land preparation page.
- A paddy's seepage and percolation and its puddling water (owner's item 3; rules.yaml paddy_losses, switch off; pages
  read as text by Claude on 2026-11-14): Brouwer, C., Heibloem, M. (1986). Irrigation Water Management Training Manual 3,
  Irrigation Water Needs, FAO, sec. 4.4 (https://www.fao.org/4/s2022e/s2022e08.htm); Brouwer, C., Prins, K., Heibloem,
  M. (1989). Training Manual 4, Irrigation Scheduling, FAO, ch. 4, sec. 4.2 and 4.4
  (https://www.fao.org/4/t7202e/t7202e07.htm); FAO (1985). Guidelines: land evaluation for irrigated agriculture, FAO
  Soils Bulletin 55, the section on seepage and percolation, citing Chin and Lee (1961) for Taiwan soils by clay content
  (https://www.fao.org/4/x5648e/x5648e0e.htm).
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
- FAO Crop Calendar, Madagascar, "Highlands Zone South" (aez 004; lastUpdated 26/02/2021), the field abroad
  (config/fields/ambohidratrimo.yaml): https://api-cropcalendar.apps.fao.org/api/v1/countries/MG/cropCalendar?language=en&aez=004
  (read 2026-11-14). Read the same night to choose the field (METHOD_NOTES 85): the zone lists of Kenya (KE aez 007, 008,
  012, 013, 019, 020), Ethiopia (ET 004-006), Madagascar (MG 004, 005, 008) and Guatemala (GT 002, 004, 005; no sowing
  windows), from https://api-cropcalendar.apps.fao.org/api/v1/countries/<CC>/aez and .../cropCalendar.
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
  SPL3SMP_E.006 and SPL4SMGP.008 to the box).
- **GPM IMERG V07, the twin's rain** (added 2026-11-13, REVIEW_2: this line had still said "not yet downloaded"):
  Huffman, G. J., Stocker, E. F., Bolvin, D. T., Nelkin, E. J., Tan, J. (2023). GPM IMERG Final Precipitation L3 1 day
  0.1 degree x 0.1 degree V07 (GPM_3IMERGDF), NASA GES DISC, doi:10.5067/GPM/IMERGDF/DAY/07; the same authors, GPM
  IMERG Late Precipitation L3 1 day V07 (GPM_3IMERGDL), doi:10.5067/GPM/IMERGDL/DAY/07 (October to December 2025, and
  the 2014-2019 check); GPM IMERG Final Precipitation L3 1 month V07 (GPM_3IMERGM), doi:10.5067/GPM/IMERG/3B-MONTH/07
  (gauge weight, a check). Daily box subsets, 2001-01-01 to 2025-12-31, 9,131 days, fetched 2026-11-12 by
  `pipeline/fetch/gpm.py` through GES DISC OPeNDAP. The Final days from 2017 are scaled in the twin (VALIDATION 3.9b).
- MOD13Q1: Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061. NASA EOSDIS LP DAAC,
  doi:10.5067/MODIS/MOD13Q1.061. Compared with HLS only; no number shown uses it.
- HLS-VI v2.0: HLS Landsat OLI Vegetation Indices Daily Global 30 m (HLSL30_VI), doi:10.5067/HLS/HLSL30_VI.002, and HLS
  Sentinel-2 MSI Vegetation Indices Daily Global 30 m (HLSS30_VI), doi:10.5067/HLS/HLSS30_VI.002, NASA LP DAAC; 1,471
  granules of tile T45RUL, read as box windows of the cloud-optimised GeoTIFFs. **Contains modified Copernicus
  Sentinel data (2015-2025)** (HLSS30).
- SMAP: Reichle, R. et al., SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Geophysical
  Data, Version 8 (SPL4SMGP), NASA NSIDC DAAC, doi:10.5067/T5RUATAQREF8 (model-assisted; a check on the twin, VALIDATION
  4.2b); O'Neill, P. E. et al., SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture,
  Version 6 (SPL3SMP_E), doi:10.5067/M20OXIZHY3RJ (downloaded; no recommended-quality retrieval over the field, not
  used). Author lists as on the NSIDC landing pages (TODO-VERIFY the exact citation text).
- ECOSTRESS tiled LST and emissivity (ECO_L2T_LSTE, doi:10.5067/ECOSTRESS/ECO_L2T_LSTE.002 and .003) and evaporative
  stress index (ECO_L4T_ESI, doi:10.5067/ECOSTRESS/ECO_L4T_ESI.002), NASA LP DAAC: raw box windows downloaded, **not used
  in any result yet** (build step 8).
- GPCC: Schneider, U., Hänsel, S., Finger, P., Rustemeier, E., Ziese, M. (2022). GPCC Full Data Monthly Product Version
  2022 at 1.0 degree, doi:10.5676/DWD_GPCC/FD_M_V2022_100 (station counts and totals; a check only).
- CHIRPS v3.0: Climate Hazards Center, UC Santa Barbara, doi:10.15780/G2JQ0P (a check only; the paper to cite is named
  on the CHC page and was not opened here).
- ESA WorldCover: **(c) ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA
  WorldCover consortium** (CC BY 4.0); Zanaga, D. et al. (2022), ESA WorldCover 10 m 2021 v200,
  doi:10.5281/zenodo.7254221 (TODO-VERIFY the DOI on the landing page).
- DHM (Department of Hydrology and Meteorology, Nepal): monthly "Preliminary Precipitation and Temperature Summary"
  bulletins of 2025 (six months; (c) DHM, preliminary data; validation only, kept under `data/`, not in this repository).
- DHM Climate Division, every monthly "Preliminary Precipitation and Temperature Summary" online on 2026-11-14 (38 issues,
  June 2023 to July 2026; the series starts June 2023), https://dhm.gov.np/climate-services/climate%20reports/monthly-reports,
  Annex 1 monthly totals and wettest days of 10 Kathmandu-valley gauges, and DHM's "Meteorological station list"
  (https://dhm.gov.np/uploads/dhm/downloads/Meteorological_station_list.pdf) for the station index numbers. (c) DHM, no open
  licence found; preliminary data; **validation only, not redistributed** (kept under `data/`; locked accuracy test set,
  `data/clean/demo/dhm_bulletin_months.csv`).
- DHM Climate Division, Monsoon Season (June-September) reports 2022 to 2025
  (https://dhm.gov.np/climate-services/climate%20reports/seasonal-reports), the archived 2019 and 2020 monsoon reports (Internet
  Archive copies of dhm.gov.np/uploads/climatic/, maps only, nothing read), and the "State of the Climate of Nepal 2024" and
  "State of the Nepal Climate 2025" (Annex 2, a cross-check). (c) DHM, no open licence found; preliminary data;
  **validation only, not redistributed** (`data/clean/demo/dhm_monsoon_years.csv`).
- MoALD (Ministry of Agriculture and Livestock Development, Nepal; earlier MoAD), "Statistical Information on Nepalese
  Agriculture", editions 2072/73, 2075/76, 2076/77, 2078/79, 2079/80, 2080/81 and 2081/82,
  https://moald.gov.np/category/statistics-related-to-agriculture (PDFs on giwmscdnone.gov.np), district tables for
  Bhaktapur paddy, wheat and potato. No licence stated; **validation only, not redistributed** (kept under `data/`; locked
  accuracy test set, `data/clean/demo/district_yields_bhaktapur.csv`).

- ISRIC SoilGrids 2.0 through its WCS (maps.isric.org), 2026-11-12, for the whole fetch box: Poggio, L., de Sousa,
  L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified
  spatial uncertainty. SOIL 7:217-240, doi:10.5194/soil-7-217-2021. CC BY 4.0.

### Event rule sources (2026-11-12, opened by a research sub-agent)

- Gibbs, W. J., Maher, J. V. (1967). Rainfall deciles as drought indicators. Bureau of Meteorology
  Bulletin No. 48; decile classes as given by Hayes, M. J., "Drought Indices", National Drought
  Mitigation Center (archived 2009-05-10).
- WMO and GWP (2016). Handbook of Drought Indicators and Indices, WMO-No. 1173, pp. 11-13.
- ETCCDI (Expert Team on Climate Change Detection and Indices), "Climate Change Indices: Definitions of the
  27 core indices", http://etccdi.pacificclimate.org/list_27_indices.shtml (read 2026-11-12 by a web-fetch
  sub-agent): Rx1day, "Monthly maximum 1-day precipitation", for the flood rule (owner, 2026-11-12); Karl, T. R.,
  Nicholls, N., Ghazi, A. (1999). CLIVAR/GCOS/WMO workshop on indices and indicators for climate extremes:
  workshop summary. Climatic Change 42, 3-7. The decile classes (deciles 9-10, "much above normal") are
  Hayes' table above.
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

### Methods and sources added on 2026-11-13 (listed by REVIEW_2; each is cited where it is used, in `config/rules.yaml` or the module)

- Pettitt, A. N. (1979). A non-parametric approach to the change-point problem. Applied Statistics 28, 126-135.
- Mann, H. B. (1945), Econometrica 13, 245-259, and Kendall, M. G. (1975), Rank Correlation Methods; Sen, P. K. (1968),
  JASA 63, 1379-1389; Hirsch, R. M., Slack, J. R., Smith, R. A. (1982), Water Resources Research 18, 107-121 (the
  seasonal test); through `pymannkendall` and `scipy.stats.theilslopes`.
- Savitzky, A., Golay, M. J. E. (1964), Analytical Chemistry 36, 1627-1639 (smoothing; `scipy.signal`); Killick, R.,
  Fearnhead, P., Eckley, I. A. (2012), JASA 107, 1590-1598 (PELT; `ruptures`).
- Doorenbos, J., Kassam, A. H. (1979). Yield response to water. FAO Irrigation and Drainage Paper 33.
- Erosion (relative index for `soil_kept`): Wischmeier, W. H., Smith, D. D. (1978), Agriculture Handbook 537; the daily
  erosivity model of Xie et al. as tabulated in Yin, S. et al. (2015), HESS 19, 4113-4126; crop C factors of Panagos et
  al. (2015) as reprinted in Benavidez, R. et al. (2018), HESS 22, 6059-6086, and Borrelli, P. et al. (2017), Nature
  Communications 8, 2013; Richardson et al. (1983) as reported by Sepaskhah and Panahi (2007) (sensitivity exponent).
- Probe sketch (`robot/firmware/original_probe/`, the robot teammate's own code): uses the Arduino libraries OneWire
  and DallasTemperature (their licences: TODO-VERIFY with the robot teammate).

### Sections sources (build step 8, 2026-11-14; cited in `config/rules.yaml` `sections` and `scripts/run_sections.py`)

- Ju, J., Neigh, C., Sridhar, M., Claverie, M., Skakun, S., Roger, J.-C., Vermote, E., Dungan, J., Ashokkumar, L.,
  Harmonized Landsat and Sentinel-2 (HLS) Product User Guide, product version 2.0, NASA GSFC / LP DAAC, last updated April
  2026 (https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf, downloaded and read 2026-11-14): geolocation and
  co-registration, sec. 2, 3.1, 4.3.
- Buckley, S. M., et al., NASADEM User Guide, NASA JPL, January 2020 (https://lpdaac.usgs.gov/documents/592/NASADEM_User_Guide_V1.pdf,
  read 2026-11-14): SRTM height errors, sec. 4.2.2.1 and 4.2.6.2.
- Weiss, A. (2001), Topographic Position and Landforms Analysis, poster, ESRI User Conference, San Diego (not opened: the
  poster link returned 404), as documented by Jenness, J. (2006), Topographic Position Index (tpi_jen.avx) extension for
  ArcView 3.x, v. 1.2, Jenness Enterprises (http://www.jennessent.com/downloads/TPI_Documentation_online.pdf, read 2026-11-14).
- Ju, J., Zhou, Q., Freitag, B., Roy, D. P., et al. (2025), The Harmonized Landsat and Sentinel-2 version 2.0 surface
  reflectance dataset, Remote Sensing of Environment 324, 114723, doi:10.1016/j.rse.2025.114723 (abstract read 2026-11-14
  through OpenAlex; CC BY-NC-ND): the same-day vegetation-index difference behind the parts' size floor.
- Conover, W. J. (1999), Practical Nonparametric Statistics, 3rd ed., Wiley (sign test, interval for the median), and
  Holm, S. (1979), A simple sequentially rejective multiple test procedure, Scandinavian Journal of Statistics 6, 65-70:
  standard results, cited from memory, not opened.

### Second onset measure (2026-11-14; cited in `config/rules.yaml` `onset_accumulation`, `pipeline/diary/onset_accumulation.py`)

- Noska, R., Misra, V. (2016). Characterizing the onset and demise of the Indian summer monsoon. Geophysical Research
  Letters 43, 4547-4554, doi:10.1002/2016GL068409 (authors' copy https://www.coaps.fsu.edu/~vmisra/ism.pdf, read
  2026-11-13): eqs. 1-2 and the onset definition, p. 4548. The definition used, exactly.
- Liebmann, B., Marengo, J. A. (2001), J. Climate 14, 4308-4318; Liebmann, B., et al. (2007), J. Climate 20, 2037-2050,
  doi:10.1175/JCLI4122.1; Liebmann, B., et al. (2012), J. Climate 25, 4304-4322: the anomalous accumulation that Noska &
  Misra build on. Cited for the method's origin; **not opened** (journals.ametsoc.org refused automated reads).
- DHM Climate Division (Government of Nepal), Monsoon Onset and Withdrawal date information, 1968-2024 (file created
  2024-10-20; https://www.dhm.gov.np/uploads/dhm/climateService/monsoon_onset_and_withdrawal_dates_english3.pdf, read
  2026-11-14): earliest and latest onset (p. 1) for the sanity window; Table 1 (p. 3), onset dates 2001-2024, for the
  year-by-year comparison (information only). Since the owner's decision of 2026-11-14, Table 1 is also the record of a
  monsoon shift, the usual start window and the late years (`diary.shift_days`, credited to DHM). The whole table
  (1968-2024) is copied into `config/dhm_onset_dates.csv` with `config/dhm_onset_dates.NOTICE.md`. DHM states no open
  licence: the table is not covered by the MIT licence. Cross-check rain: CHIRPS v3.0 (above) and GPM IMERG V07 Final.

### Area map and sample fields (Local Impact 4a and 4b, 2026-11-14; cited in `config/rules.yaml` `area_map`, `sample_fields`)

- Tsendbazar, N., Xu, P., Herold, M., Lesiv, M., Duerauer, M. (2022). ESA WorldCover Product Validation Report (D12-PVR),
  version 2.0, 2022-10-25, WorldCover 2021 v200: Table 2 p. 15 (global) and Table A2.4 p. 29 (Asia), cropland user's and
  producer's accuracy (opened 2026-11-14, esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PVR_V2.0.pdf).
- Brewer, C. A., Harrower, M., ColorBrewer 2.0 (colorbrewer2.org): the YlOrBr and Greens sequential palettes of the area
  map, marked colour-blind safe there.
- Data reused, nothing downloaded: HLS-VI v2.0 box windows and ESA WorldCover 10 m 2021 v200 (CC BY 4.0), as listed above.

### The data story, the inventories and the Sentinel-1 assessment (2026-11-14; metadata and documentation only)

- *metadata* ASF Search API, Alaska Satellite Facility DAAC (https://api.daac.asf.alaska.edu/services/search/param):
  Sentinel-1 IW GRD-HD scene counts and listings (sizes, tracks, platforms) over the demo field's point, June-September
  2025 and 2017-2025, queried 2026-11-14 without a login; nothing downloaded (DATA_AUDIT 8.1). Sentinel-1 data: Copernicus
  Sentinel data, ESA, distributed by ASF.
- ASF HyP3 documentation (hyp3-docs.asf.alaska.edu), read 2026-11-14: RTC Product Guide (file contents and the example
  GeoTIFF sizes), "Credits" (cost per job, monthly allowance), "On Demand Sentinel-1 Processing in Vertex" (typical time to
  download, 14-day retention).
- FAO GAEZ v4 (https://gaez.fao.org/): **linked as a reference, data not used** (owner, 2026-11-14: its licence is
  non-commercial and share-alike). Nothing from it is in the repository or the export.
- `site/data/story.json` reuses only the project's own outputs listed above (each chart names its sources); no new dataset.

### Licence notices (REVIEW_2, 2026-11-13; owner's answer 13: keep the DHM table with a notice, state the GSOD terms, say in LICENSE what MIT does not cover)

- **Kathmandu Airport station values.** Every value has GHCN source flag `S` (NOAA Global Summary of the Day). The GSOD
  readme says of non-US data, under WMO Resolution 40, that "the data or any derived product shall not be provided to
  other users or be used for the re-export of commercial services". GHCN-Daily's own readme has no such clause. The
  station fits the temperature correction, so it stands behind every exported temperature-dependent number.
- **DHM normals** (`config/dhm_normals_1991_2020.csv`, 156 values, not yet committed) and the 2025 bulletin values
  (kept under `data/`): (c) DHM; no open licence was found on dhm.gov.np.
- **FAO texts.** `pipeline/words/crop_explainers.json` and `glossary.json` quote FAO publications word for word (18 of
  21 quotes); FAO publications are commonly CC BY-NC-SA 3.0 IGO. Crop values in `config/crops.json` come from FAO-56,
  FAO-33/66 and the FAO Crop Calendar.
- **LICENSE** now ends with "What this licence does not cover" (2026-11-13), and `config/dhm_normals_1991_2020.NOTICE.md` sits beside the DHM table.
- No library is GPL or non-commercial: the 76 installed distributions are MIT, BSD, Apache, PSF or MIT-CMU (certifi and
  tqdm are MPL-2.0).

## Libraries (installed in `.venv`, Python 3.12.9)

Licences are read from each package's installed metadata.

| Library | Version | Licence | Used for |
| --- | --- | --- | --- |
| numpy | 2.5.4 | BSD-3-Clause (and bundled MIT, 0BSD, Zlib, CC0-1.0) | data guards, ET0 |
| pandas | 2.3.3 | BSD-3-Clause | tables, review pack (pyet 1.5.0 needs pandas<3) |
| xarray | 2026.9.0 | Apache-2.0 | pinned for gridded data; no module imports it today (h5py, rasterio and scipy read the files) |
| pyarrow | 26.0.1 | Apache-2.0 | parquet |
| PyYAML | 6.0.3 | MIT | config files |
| jsonschema | 4.26.0 | MIT | contract validation |
| requests | 2.34.2 | Apache-2.0 | HTTP fetches |
| matplotlib | 3.11.2 | Matplotlib licence (PSF-based) | review plots |
| pytest | 9.2.0 | MIT | tests |
| pyet | 1.5.0 | MIT | step 3: reference library for ET0 in the tests (the same FAO-56 algorithm, so not an independent check; FAO-56's printed examples are) |
| scipy | 1.18.1 | BSD-3-Clause | imported directly (Savitzky-Golay smoothing, Theil-Sen slopes, the netCDF-3 reader for GPCC) but installed only as a dependency of scikit-learn, pyet and others: not pinned in `requirements.txt` (REVIEW_2 L8, with the owner) |
| affine | 3.0.1 | BSD-3-Clause | grid transforms; installed with rasterio, not pinned itself (REVIEW_2 L8) |
| pillow | 13.0.0 | MIT-CMU (HPND) | the area map's palette PNGs (`pipeline/area/render.py`, 2026-11-14); installed with matplotlib (in requirements-lock.txt), not pinned itself |
| earthaccess | 0.19.0 | MIT | Earthdata search, login (~/.netrc) and downloads (owner's go 2026-11-12) |
| h5py | 3.16.0 | BSD-3-Clause | HDF5 / netCDF-4 files: GRACE, GPM subsets, AppEEARS output (owner's go 2026-11-12) |
| rasterio | 1.5.2 (bundles GDAL 3.12.2) | BSD-3-Clause | GeoTIFF / COG windows: WorldCover, NASADEM, HLS, ECOSTRESS (owner's go 2026-11-12) |
| python-dateutil | 2.9.0.post0 | BSD / Apache-2.0 (dual) | dependency; pinned after earthaccess downgraded it |
| affine, click | 3.0.1, 8.5.1 | BSD-3-Clause | rasterio dependencies |
| scikit-learn | 1.9.1 (with scipy 1.18.1, joblib 1.6.0, threadpoolctl 3.8.0) | BSD-3-Clause | step 6 season detective, step 7b field memory (owner's go 2026-11-12) |
| ruptures | 1.1.10 | BSD-2-Clause | step 6 change-point season detection (owner's go 2026-11-12) |
| pymannkendall | 1.4.3 | MIT | step 6 trends: Mann-Kendall with Sen's slope (owner's go 2026-11-12) |
| flask | 3.1.3 (with Werkzeug, Jinja2, itsdangerous, blinker, MarkupSafe) | BSD-3-Clause | step 10, local demo only; not used yet (owner's go 2026-11-12) |
| pyserial | 3.5 | BSD-3-Clause | step 10: the probe bridge reads the probe's USB serial lines (owner's go 2026-11-12) |

## SI (AI) use

| Tool | Date | What it produced | Reviewed by |
| --- | --- | --- | --- |
| Perplexity (Perplexity AI), used by the team | 2026-11 | Background research questions asked by the team (owner, 2026-11-14: "Perplexity for research"). Not logged per question; nothing from it enters the pipeline or the site unless a person or a research sub-agent opened the cited source, which is then cited directly in `config/rules.yaml` or here | The team |
| Claude Fable 5.2 (Anthropic), the independent review REVIEW_2.md | 2026-11-13 | An independent review of the 13 November version: it recomputed the checks from the primary sources; the model changes of 14 November came after it | The owner |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Step 1 code and tests, `schema.json`, `index_schema.json`, mock data, data guards, backup and review-pack scripts, DATA_AUDIT.md, VALIDATION.md. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Contract changes (A13, D7), guard change (D2), step 2 POWER fetch, GHCN fetch, layer-3 checks and cross-checks, CLAUDE.md edits (D1 to D7, SI components, build order), MASTER_PROMPT.md (owner's text, copied), VALIDATION.md and DATA_AUDIT.md rewrites. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with two research sub-agents | 2026-11-12 | Step-3 review items (quantile mapping, rain vote, SoilGrids fetch), build step 4 (crop library, bucket, runoff, yield, season test). Two sub-agents opened FAO-56/FAO-66, TR-55/NEH, FAO Crop Calendar, ASCE-EWRI and quantile-mapping sources. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with two research sub-agents | 2026-11-11 | Decisions A to H (station correction, spike check, day alignment, rain fill-in, sourced known events, FAOSTAT, citations, history scan), build step 3 (ET0), rules.yaml. Sub-agents opened official pages for the citations, FAO-56 worked examples and the known-events sources. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code, with one research sub-agent and one review sub-agent | 2026-11-12 (later) | Step-4 review answers (cold-night roles, assumed Ky, irrigation bug fix, approvals), step 5 without GPM (replay, events, export guard, METHOD_NOTES.md), placeholder field (WorldCover), fetchers for WorldCover, NASADEM, GRACE, AppEEARS, HLS/ECOSTRESS windows and GPM. The research sub-agent opened the event-rule and Ky sources above. The review sub-agent ran the **"silent-failure-hunter" agent prompt from the ECC selection in the team's claude-code-kit** (ECC, MIT licence) over the new code; its 10 findings were verified and the real ones fixed test-first. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code (parallel words session), with one research sub-agent | 2026-11-12 | Build-time drafting of plain-language texts and Nepali translations (`pipeline/words/`: glossary, crop explainers, five-tab templates, tips, screen texts), and a source search for the crop explainers (FAO, CGIAR centres, NARC; sources listed above). Nothing calls an AI service from the site. Details in SI_LOG.md | Owner: English and the listed choices (decided 2026-11-12); Nepali: native-speaker review pending |
| Claude Opus 5.5 (Anthropic), via Claude Code, with one audit, three fix and one research sub-agent | 2026-11-12 (late night) | REVIEW_NOTES fixes (H1-H4, M1-M13, L1-L7: code, tests, rules.yaml and docs), the owner's words decisions (Bikram Sambat months, soil temperature), the Nepali tabs/tips contract change, reruns of the dry run, season test, pixel check and cleaned tables from cache. The research sub-agent opened FAO/IIASA/ISRIC pages on HWSD v2 (licence and access; not used). Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 7a992fe8), with one web-fetch and two research sub-agents | 2026-11-12 (evening) | Owner review of d34fa93: pandas pin and fresh-install check, README.md, LICENSE (MIT), GitHub Pages workflow, FAO-56 Kc climate adjustment (eqs. 62, 63, 65) with tests from Example 27 and Box 15, REVIEW_NOTES status table, TODO-CONFIRM batch and TODO-VERIFY triage, rain sensitivity, event plan. The web-fetch sub-agent read FAO-56 Chapters 6 and 7 on fao.org; the research sub-agents read the repository and opened primary sources for the TODO-VERIFY items. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 2f8edafe), with one web-fetch sub-agent | 2026-11-12 (Thursday evening) | The owner's batch decisions: flood rule fixed in advance (ETCCDI Rx1day, deciles 9-10), approvals in rules.yaml and the docs, complete-years export, rotation stop, both water cases, nullable soil temperature, sowing position, ECOSTRESS QC mask, five libraries pinned, rule 2 and audio removal in CLAUDE.md, word changes (months, labels, rain caveat, flood entry), probe bridge and fake probe; tests first. Earlier the same day: Nepali frost spelling, review-mark check, PREVIEW status lines. Details in SI_LOG.md | Owner review pending; Nepali needs native-speaker review |
| Claude Code kit (team-prepared zip, 2026-11-07): superpowers plugin (MIT, already installed: its test-driven-development skill guided the work) and an ECC selection (MIT) | 2026-11-12 | Workflow guidance and one review prompt (above). The ECC skills and agents were **not installed** into `~/.claude` (blocked as a self-modification; the owner can copy them) | Owner |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 2f8edafe), with one research sub-agent | 2026-11-12 (late night) | Build step 6b: three season-detection methods (threshold; change-point with ruptures PELT; the SI season detective, a scikit-learn random forest trained on this field's own greenness, rain and temperature at build time, never on the site), the held-out comparison (VALIDATION 3.15), rules.yaml season_detection; the owner's decisions recorded (onset rule kept, flood years 2006 and 2020, Firebase keys). The research sub-agent opened the sources for the threshold batch (DHM onset dates, ETCCDI, Moron et al. 2009, HLS and MOD13 user guides, MSLSP30NA, MCD12Q2, TIMESAT 3.3, Killick et al. 2012); Claude checked the key quotes. Details in SI_LOG.md | Owner review pending |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 2f8edafe), with four research sub-agents | 2026-11-13 (Friday, early) | The owner's approvals applied (sourced thresholds), the method page's season comparison (contract key `method`), build step 6c (GRACE trend, Mann-Kendall trends, monthly calendar, rotation guess, real diary export), the GitHub Pages failure diagnosis; research sub-agents opened DHM normals, CHIRPS/APHRODITE access, IMERG calibration fields and rice-mapping papers for the owner's upgrade list. Details in SI_LOG.md | Owner review pending |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 2f8edafe) | 2026-11-13 (Friday, midday) | The owner's decisions 1-6: the GPM break correction and the uncorrected run beside it, IMERG Late and CHIRPS check downloads, build step 7 (three plans, their replays, tabs and tips from templates, Nepali drafts), the method page's rain note and stated choices. Details in SI_LOG.md | Owner review pending (English lines); native-speaker review pending (Nepali) |
| Claude Fable 5.2 (Anthropic), via Claude Code (session 9f5addf3), with ten read-only sub-reviewers | 2026-11-13 (Friday, afternoon) | Independent AI review of the whole project. Phase 1: every equation, correction, rule and exported number recomputed from the primary sources; data handling, the rain break, the export, licences, security and the probe checked (`REVIEW_2.md`). Phase 2: fixes with tests first (method-page approval labels, the leap-year count of pinned onset years, the hot-day trend caveat, `sources` rows, validator checks and `--final`, the mock-overwrite guard, GPM card flags) and the stale documents brought up to date. Phase 3: SMAP cleaned and compared with the twin (`pipeline/fetch/smap.py`, `scripts/run_smap_check.py`), DHM's 2025 gauge totals as an independent rain check (`scripts/run_dhm_bulletin_check.py`), the gauge evidence made reproducible (`pipeline/fetch/gauge_evidence.py`), sensitivity and switch-off runs. Phase 4: the plan in `REVIEW_2.md`. No scientific method, rule, threshold or exported result was changed; those questions are listed for the owner | Owner: not reviewed by a person yet |
| Claude Opus 5.5 (Anthropic), via Claude Code (parallel agent) | 2026-11-13 (night) | Draft machine translations of the site's words (screens, shared words, glossary, crop explainers; 269 texts each) into Hindi, Bengali, Spanish, French and Swahili, translated from the English (`pipeline/words/drafts/`), published beside English and Nepali in `site/data/words.json`, each language flagged as a draft with a 'Draft translation' label. Source quotations kept in their original English, untranslated. Nothing calls an AI service from the site. Details in SI_LOG.md | Not reviewed: every draft language needs native-speaker review |
| Claude Opus 5.5 (Anthropic), via Claude Code (parallel agent) | 2026-11-14 (Saturday morning) | The "How we know" data story (`pipeline/export/build_story.py` -> `site/data/story.json`: 17 charts from finished outputs), the accuracy report card (VALIDATION.md), the satellite inventory and the challenge's resource list (DATA_AUDIT.md 7-8), the Sentinel-1 assessment (DATA_AUDIT 8.1, ASF metadata only); English and Nepali captions drafted by SI. Details in SI_LOG.md | Not reviewed yet: the owner reviews the report card and the confidence rules (METHOD_NOTES 98); a native speaker reviews the Nepali |
| Claude Opus 5.5 (Anthropic), via Claude Code (session 9f5addf3, a sub-agent) | 2026-11-14 (Saturday) | Locked accuracy test set, reference data only: downloaded and transcribed DHM's 38 monthly bulletins (10 valley gauges, 358 station-months, with each month's wettest day), DHM's monsoon-season station totals (2022-2025, 36 rows) and MoALD's district yields for Bhaktapur (7 editions, 21 rows), with data cards and image spot-checks; not compared with any model output. Details in SI_LOG.md | Not reviewed by a person yet |

## Data fetched by the pipeline

- NASA POWER Daily API v2.10.3 (model-based), field `demo`, 2001-01-01 to 2025-12-31, fetched 2026-11-11
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `demo`, 2001-01-01 to 2025-08-24, fetched 2026-11-11
- FAOSTAT QCL bulk file (FAO), Nepal rice, wheat and maize yields, 2001 to 2024, fetched 2026-11-11 (validation only)
- ISRIC SoilGrids 2.0 REST API (model-based, CC-BY 4.0), field `demo`, cell 750 m from the field point, fetched 2026-11-12 (superseded the same day by the WCS maps of the whole box: the cell used is 859 m from the placeholder field)
- NASA POWER Daily API v2.10.3 (model-based), field `demo`, 2001-01-01 to 2025-12-31, fetched 2026-11-12
- ESA WorldCover 10 m 2021 v200 (CC BY 4.0), field `demo` fetch box, fetched 2026-11-12 (placeholder field only)
- NASADEM_HGT v001 (NASA JPL, LP DAAC), field `demo` fetch box, fetched 2026-11-12
- JPL GRACE/GRACE-FO mascon CRI RL06.3Mv04 (PO.DAAC), cell holding field `demo`, 2002-04 to 2026-09, fetched 2026-11-12
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), precipitation, gaugeRelativeWeighting and precipitationQualityIndex for the 3x3 block of 0.1 deg cells around field `demo`, 2001-01 to 2025-09, fetched 2026-11-13 by a research sub-agent (rain check B only; not a twin input)
- GPCC Full Data Monthly V2022, 1.0 deg (Deutscher Wetterdienst, opendata.dwd.de), 2011-2020 file: station counts and totals around field `demo`, fetched 2026-11-13 by a research sub-agent (rain check B only)
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain), the cell holding field `demo` and its neighbours, 2020 only, read 2026-11-13 by a research sub-agent (rain check B test read; doi:10.15780/G2JQ0P)
- DHM (Department of Hydrology and Meteorology, Nepal) 1991-2020 climate normals: the official 'Climate Normals' table (Kathmandu Airport; Internet Archive copy of 30 Jan 2022) and the 'Normal' columns of DHM's monthly bulletins, Jan 2025 to Jul 2026 (Bhaktapur, Changu Narayan, Nagarkot), transcribed 2026-11-13 by a research sub-agent into config/dhm_normals_1991_2020.csv with the document and page of every number (validation only)
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `demo`'s fetch box, 2001-2025, fetched 2026-11-13 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA GPM IMERG V07 Late daily (GPM_3IMERGDL, GES DISC OPeNDAP), the 0.1 deg cells of field `demo`'s fetch box, 2014-2019, fetched 2026-11-13 by pipeline/fetch/gpm_late.py (rain check B confirmation only; never the twin's rain)
- NASA SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture Geophysical Data (SPL4SMGP v008, model-assisted) and SMAP Enhanced L3 Radiometer Global Daily 9 km Soil Moisture (SPL3SMP_E v006), NSIDC DAAC via LP DAAC AppEEARS, the 9 km cell holding field `demo`, 2015-03-31 to 2025-12-31, cleaned 2026-11-13 by pipeline/fetch/smap.py (a check on the twin only; no number shown uses it)
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `demo`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-13 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- NOAA NCEI GHCN-Daily v3.35, station MA000067083 (validation only), field `ambohidratrimo`, 2001-01-01 to 2025-08-23, fetched 2026-11-14
- NASA POWER Daily API v2.10.3 (model-based), field `ambohidratrimo`, 2001-01-01 to 2025-12-31, fetched 2026-11-14
- NASA POWER daily API (near-real-time: GEOS-IT, FLASHFlux; model-based) and NASA GPM IMERG Late V07 daily (GPM_3IMERGDL, GES DISC OPeNDAP), field `demo`, 2026-01-01 to 2026-11-03, fetched 2026-11-14 by pipeline/fetch/now.py (the twin's state now, build step 10)
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `ambohidratrimo`'s fetch box, 2001-2025, fetched 2026-11-14 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA GLDAS-2.1 Noah monthly 0.25 deg (GLDAS_NOAH025_M v2.1, GES DISC, Earthdata Cloud OPeNDAP), soil moisture and evapotranspiration for the field's cell, 2001-2025, fetched 2026-11-14 (check on the twin only)
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `ambohidratrimo`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-14 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- FAOSTAT QCL bulk file (FAO), Madagascar rice, potato and wheat yields, 2001 to 2024, fetched 2026-11-14 (validation only)
- NEX-GDDP-CMIP6 (NASA Earth Exchange; Thrasher et al. 2022), pr, tasmax, tasmin at the 0.25 deg cell 27.625 N, 85.375 E (field `demo`), historical 1995-2014 and ssp245 / ssp585 2026-2040, fetched from 2026-11-14 via NASA NCCS THREDDS by pipeline/fetch/nexgddp.py (the 2040 outlook; the models used are listed in data/cards/demo/nexgddp.json)
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `sample-1`'s fetch box, 2001-2025, fetched 2026-11-14 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA POWER Daily API v2.10.3 (model-based), field `sample-1`, 2001-01-01 to 2025-12-31, fetched 2026-11-14
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `sample-1`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-14 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- FAOSTAT QCL bulk file (FAO), Nepal rice, wheat and maize yields, 2001 to 2024, fetched 2026-11-14 (validation only)
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `sample-1`, 2001-01-01 to 2025-08-24, fetched 2026-11-14
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `sample-2`'s fetch box, 2001-2025, fetched 2026-11-14 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA POWER Daily API v2.10.3 (model-based), field `sample-2`, 2001-01-01 to 2025-12-31, fetched 2026-11-14
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `sample-2`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-14 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `sample-2`, 2001-01-01 to 2025-08-24, fetched 2026-11-14
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `sample-3`'s fetch box, 2001-2025, fetched 2026-11-14 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA POWER Daily API v2.10.3 (model-based), field `sample-3`, 2001-01-01 to 2025-12-31, fetched 2026-11-14
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `sample-3`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-14 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `sample-3`, 2001-01-01 to 2025-08-24, fetched 2026-11-14
- CHIRPS v3.0 daily final `rnl` (Climate Hazards Center, UC Santa Barbara; public domain; doi:10.15780/G2JQ0P), the cells overlapping field `sample-4`'s fetch box, 2001-2025, fetched 2026-11-14 by pipeline/fetch/chirps.py (rain check B only; never the twin's rain)
- NASA POWER Daily API v2.10.3 (model-based), field `sample-4`, 2001-01-01 to 2025-12-31, fetched 2026-11-14
- NASA GPM IMERG V07 Final monthly (GPM_3IMERGM, GES DISC OPeNDAP), `gaugeRelativeWeighting` and `precipitation` for the 3 x 3 cells around field `sample-4`, and GPCC Full Data Monthly Product V2022 1.0 deg (Schneider et al. 2022, doi:10.5676/DWD_GPCC/FD_M_V2022_100; DWD open data), station counts and totals for the field's box, fetched 2026-11-14 by pipeline/fetch/gauge_evidence.py (rain check B evidence only; never the twin's rain)
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation; temperature correction A), field `sample-4`, 2001-01-01 to 2025-08-24, fetched 2026-11-14
- NASA GPM IMERG V07 daily (GPM_3IMERGDF Final for 2025-09-30, its last day in CMR; GPM_3IMERGDL Late for 2025-10-01 to 2026-07-31; GES DISC OPeNDAP, the field `demo`'s box), fetched 2026-11-14 by pipeline/fetch/gpm.py into `data/rain2026/` (never `data/clean/demo/gpm.parquet`): the locked 2026 test of the central rain version only (`scripts/run_rain_selection.py`; rules.yaml verification.rain_selection); never the twin's rain
