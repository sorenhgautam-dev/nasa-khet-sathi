# CREDITS.md

Every dataset, library and use of SI (AI) goes here the moment it is used (CLAUDE.md rule 10).

## Data and metadata services

Rows marked *metadata* were used only to check names, versions and units. Data that entered the
pipeline is listed under "Data fetched by the pipeline" below (written by the fetch modules).

| Source | What we used | When | Citation |
| --- | --- | --- | --- |
| NASA Common Metadata Repository (CMR) search API | Product short names, versions, coverage dates, variable units, fill values, scale factors (DATA_AUDIT.md) | 2026-11-11 | TODO-VERIFY preferred citation |
| NASA POWER Daily API v2.10.3 | **Data** (step 2): daily T2M_MAX, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR at 27.67 N, 85.43 E, 2001 to 2025 | 2026-11-11 | TODO-VERIFY official POWER acknowledgement text |
| ISRIC SoilGrids 2.0 REST API | List of available properties | 2026-11-11 | TODO-VERIFY (Poggio et al. 2021, SOIL; confirm) |
| NEX-GDDP-CMIP6 public bucket (AWS Open Data) | Listing of model folders | 2026-11-11 | TODO-VERIFY |
| NOAA NCEI GHCN-Daily, Version 3.35 | **Data** (validation only): station NP000444540 Kathmandu Airport, PRCP, TMAX, TMIN, 2001 to 2025 | 2026-11-11 | Menne, M.J., I. Durre, R.S. Vose, B.E. Gleason, and T.G. Houston, 2012: An overview of the Global Historical Climatology Network-Daily Database. J. Atmos. Oceanic Technol., 29, 897-910, doi:10.1175/JTECH-D-11-00103.1. Dataset: Menne et al. 2012, GHCN-Daily, Version 3.35, NOAA National Climatic Data Center, doi:10.7289/V5D21VHZ, accessed 2026-11-11 (text from the GHCN-Daily readme) |

## Libraries (installed in `.venv`, Python 3.12.9)

Licences are read from each package's installed metadata.

| Library | Version | Licence | Used for |
| --- | --- | --- | --- |
| numpy | 2.5.4 | BSD-3-Clause (and bundled MIT, 0BSD, Zlib, CC0-1.0) | data guards |
| pandas | 3.1.1 | BSD-3-Clause | tables, review pack |
| xarray | 2026.9.0 | Apache-2.0 | (from step 6) gridded data |
| pyarrow | 26.0.1 | Apache-2.0 | parquet |
| PyYAML | 6.0.3 | MIT | config files |
| jsonschema | 4.26.0 | MIT | contract validation |
| requests | 2.34.2 | Apache-2.0 | (from step 2) HTTP fetches |
| matplotlib | 3.11.2 | Matplotlib licence (PSF-based) | review plots |
| pytest | 9.2.0 | MIT | tests |

## SI (AI) use

| Tool | Date | What it produced | Reviewed by |
| --- | --- | --- | --- |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Step 1 code and tests, `schema.json`, `index_schema.json`, mock data, data guards, backup and review-pack scripts, DATA_AUDIT.md, VALIDATION.md. Details in SI_LOG.md | Owner: to fill in after review |
| Claude Opus 5.5 (Anthropic), via Claude Code | 2026-11-11 | Contract changes (A13, D7), guard change (D2), step 2 POWER fetch, GHCN fetch, layer-3 checks and cross-checks, CLAUDE.md edits (D1 to D7, SI components, build order), MASTER_PROMPT.md (owner's text, copied), VALIDATION.md and DATA_AUDIT.md rewrites. Details in SI_LOG.md | Owner: to fill in after review |

## Data fetched by the pipeline

- NASA POWER Daily API v2.10.3 (model-based), field `demo`, 2001-01-01 to 2025-12-31, fetched 2026-11-11
- NOAA NCEI GHCN-Daily v3.35, station NP000444540 (validation only), field `demo`, 2001-01-01 to 2025-08-24, fetched 2026-11-11

