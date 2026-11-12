# REVIEW_NOTES.md

Reviewer pass, 2026-11-12, run alongside the build session. Read: CLAUDE.md, DATA_AUDIT.md, VALIDATION.md,
METHOD_NOTES.md (for context), config/rules.yaml, config/crops.json, config/fields/demo.yaml, pipeline/twin/*,
pipeline/fetch/*. Spot checks were read-only, on the cached files in `data/`. Line numbers are as of the
review. The other session was editing at the same time (rules.yaml gained a potato frost rule,
`soilgrids_wcs.py` appeared, the test count moved from 466 to 493), so some items may already be fixed.

Only problems are listed: things that are wrong, unproven, inconsistent or overclaimed. Most severe first.

---

## Owner response, 2026-11-12

The owner accepted these notes. **The fixes go to the other build session, not to this reviewer.** This session
changes only REVIEW_NOTES.md. Decisions given with the acceptance:

- **H3 field: candidate 1** in `data/clean/demo/placeholder_candidates.json`.
  - Centre **27.690542 N, 85.441792 E**, 60 m square.
  - Polygon (SW, SE, NE, NW, as [lon, lat]): `[[85.441487, 27.690272], [85.442097, 27.690272],
    [85.442097, 27.690812], [85.441487, 27.690812]]`.
  - The owner asked for a check that the HLS pixels covering the square do not reach the Kasan River's tree
    line to the south, and for a nudge north if they do. Result of the check (read-only, below): **no nudge
    needed; the centre stays 27.690542 N, 85.441792 E.**
  - **Superseded (owner, 2026-11-12): moved 25 m north.** New centre **27.690767 N, 85.441792 E**, still a 60 m
    square. Polygon (SW, SE, NE, NW): `[[85.441487, 27.690497], [85.442097, 27.690497], [85.442097, 27.691037],
    [85.441487, 27.691037]]`.
    - Reason: on Google Maps the Kasan River and its riparian strip run about 30 m south of the old centre, at the
      square's southern edge. The strip is too narrow for WorldCover or HLS to show.
    - This is the field H3 applies; it is in `config/fields/demo.yaml`, and the earlier squares are under
      `earlier_placeholders`. The check is below.
- **Built-up margin (owner, 2026-11-12):** the moved field's 30 m margin is 77 m from the nearest built-up pixel,
  not the 100 m the search asks. Accepted by the owner, 2026-11-12.
- **M1:** take frost out of the per-year replay events; show it only as a risk band in the monthly calendar.
- **M4:** the unscaled GRACE trend is the main number. Say that a CRI scale factor exists but is not applied,
  because it is CLM-based and the mascon includes glaciers.
- **M5:** for cells SoilGrids leaves empty, try FAO HWSD v2. Check its licence and access first, and ask the
  owner before adding any dependency. Otherwise use the nearest SoilGrids cell within 3 km, with a caveat.
  Fix the WCS reader (nodata, units, bounds; never treat "no prediction" as 0%).
- **M6:** hold the actual vapour pressure `ea` from POWER, capped at es of the corrected Tmin. Report ET0
  under both choices.

### Fix status (build session, 2026-11-12, after VS Code closed; tests first throughout)

| Item | Status | Where |
| --- | --- | --- |
| H1 paddy water | **Fixed.** Ponded only when irrigated; the daily refill is irrigation (`pond_supply_mm` is its paddy part); rain-fed paddy is the plain bucket, no outside water. Owner to confirm (it changes METHOD_NOTES item 2) | `soil_water.run_bucket`, `season.simulate`; METHOD_NOTES 2; VALIDATION 2.2, 4.1, 4.4b; CLAUDE.md "Rice"; rules.yaml `paddy_rice` |
| H2 station S-flag | **Fixed.** S-flag kept per row and counted in the card; every record is `S`; "synoptic-derived, use with caution" wherever the station is used as truth | `ghcn.py`; DATA_AUDIT 1.11, section 3; VALIDATION header, 3.7, 3.9, 3.11, 3.14; rules.yaml `rain_vote` |
| H3 field | Done earlier (field move); built-up exception recorded | above |
| H4 stage lengths | **Fixed.** Maize 180→130 d, lentil 170→133 d, finger millet 105→117 d from transplanting (TODO-VERIFY); mustard `days` recomputed; mustard and buckwheat `simulate: false`; `simulatable_crops` helper | `crops.json`, `twin/crops.py`; METHOD_NOTES 9 |
| M1 frost | **Fixed.** No per-year frost event; contract enum is none/drought/flood; screen-7 frost label removed | `events.py`, `rules.yaml`, `schema.json`, mock, words; CONTRACT_CHANGES |
| M2 GPM card | **Fixed** (code). Fills, failed and missing days counted apart; raw attributes printed; `--from-cache`; exit non-zero on missing days; POWER fill capped at 5% a year (TODO-CONFIRM). Card rebuilt after the download | `gpm.py`, `inputs.py`, `weather.py` |
| M3 audit consistency | **Fixed** | DATA_AUDIT, VALIDATION |
| M4 GRACE | **Fixed.** Unscaled trend -2.56 cm/yr is the main number; factor 1.4945 recorded, not applied | `grace.py`; DATA_AUDIT 1.10; rules.yaml |
| M5 SoilGrids | **Fixed.** WCS reader masks by all 36 maps, bounds-checked; soil now from the cell 859 m SE (3 km rule). HWSD v2 checked: CC BY-NC-SA, needs the owner's go | `soilgrids_wcs.py`, `soilgrids.py`; DATA_AUDIT 1.6, B5; METHOD_NOTES 7 |
| M6 humidity | **Fixed.** ea held from POWER, capped at e0(corrected Tmin); ET0 1,325 vs 1,281 mm/yr with RH held; the cap binds on 55% of days (owner to confirm) | `inputs.py`, `weather.py`; METHOD_NOTES 20; DATA_AUDIT 1.13 |
| M7 Kc and bare soil | **Declared** (no code change) | METHOD_NOTES 16-18 |
| M8 cold-night evidence | **Fixed.** Small-sample wording and numbers; "independent in time only"; qmap docstring; months without an offset reported loudly (none on the demo) | CLAUDE.md, rules.yaml, METHOD_NOTES 6, VALIDATION; `qmap.py`, `bias.py`, `weather.py` |
| M9 weather checks | **Fixed.** Tmin > Tmax fails loudly (0 days); `tmin_frost_c` range-checked; per-column sources in the card | `weather.py`; DATA_AUDIT 1.13 |
| M10 day alignment | **Fixed** (wording) | DATA_AUDIT 1.11, VALIDATION 3.13 |
| M11 placeholder test | **Fixed.** Wording; limit from rules.yaml; None guarded; the chosen field is labelled with its 77 m exception; stale `placeholder_field.json` renamed | `placeholder.py`, `worldcover.py`; CLAUDE.md, METHOD_NOTES 13, VALIDATION 1.4 |
| M12 HLS water bit | **Checked, kept.** 0 of 2,916 June-August observations over the field are water-flagged | `ndvi.py` docstring; DATA_AUDIT 1.3 |
| M13 numbers | **Fixed.** Wheat 2016 gap explained (starting depletion); test count and totals updated; rice→potato everywhere | VALIDATION 1.1, 2.4, totals; CLAUDE.md; rules.yaml |
| L1-L3 | **Fixed** | `soil_water.py`, `season.py`, `yield_.py`; METHOD_NOTES 19 |
| L4 | **Fixed**, except EGM96 (still TODO-VERIFY in the NASADEM user guide) | DATA_AUDIT, `et0.py`, demo.yaml |
| L5 WorldCover tiles | **Fixed** (not run against the network) | `worldcover.py` |
| L6 boundless fill | **Fixed.** 0 cached windows reach outside their granule. New finding: ECOSTRESS V002 QC and cloud read 0 where data is missing, so mask by LST/ESI | `cogwindows.py`; DATA_AUDIT 1.8 |
| L7 cards | **Fixed.** Cards for HLS L30/S30, ECOSTRESS LSTE/ESI and MODIS from the cache | `cogwindows.py`, `appeears.py`; DATA_AUDIT 5 |

### Tree-line check for candidate 1 (2026-11-12)

The check used cached data only. The scripts are outside the repository, in this session's scratchpad.

- **Covering pixels.** 9 HLS pixels intersect the square: rows 92-94 × cols 207-209 of the box grid.
  - Their footprints reach 23.7 m south and 5.8 m north of the square.
  - The season test itself samples only the 4 pixels whose centres lie within 30 m of the square's centre.
- **WorldCover 2021.** None of the 9 footprints contains a tree-cover cell (class 10).
  - Nearest tree cell: **167 m north** of the centre (27.692042 N, 85.441875 E).
  - Nearest tree cell to the south: 293 m away, to the west-southwest (27.689542 N, 85.439042 E).
  - Due south, over the same longitudes: 1,054 m.
- **HLS greenness.** Evergreen trees keep a high NDVI all year, so the indicator used is each pixel's annual
  minimum (median of the 2016-2025 yearly minima).
  - The 9 covering pixels: 0.19-0.21. One exception is the south-east pixel at 0.27 (yearly 0.22-0.32):
    slightly greener, but nothing like a tree.
  - Due south, out to about 1 km: no pixel reaches 0.35.
  - The nearest pixels at or above 0.35 form a band **120-210 m north** of the centre. This matches
    WorldCover's tree cells there.
  - The 0.35 cut-off is this check's own indicator, not a sourced rule.
- **Conclusion.** The covering pixels do not reach any tree line. The nearest tree line in both sources is to
  the **north**, so nudging north would move the square *towards* trees.
  - The river cannot be identified from these data. The owner should confirm on imagery which side of the
    square the Kasan River lies.
  - Map: `candidate1_treeline.png` in this session's scratchpad (annual-minimum NDVI, the square and its
    covering pixels).

### Tree-line check for the moved field, 27.690767 N (2026-11-12)

Same method and cached data as above, rerun after `placeholder.py` rebuilt the HLS monthly composites (2013-04 to
2025-12, with the granules fetched at 12:41). Scripts: `treeline_nudged.py` and `plot_nudged.py`, in session
7a992fe8's scratchpad, outside the repository.

- **Covering pixels.** 9 HLS pixels intersect the square: rows 91-93 × cols 207-209 (one row north of before).
  - Their footprints reach 18.6 m south and 10.8 m north of the square.
  - The season test samples rows 91-92 × cols 208-209.
- **River line as described** (30 m south of the old centre, 27.690272 N).
  - It lies 24.5 m south of the new square's southern edge.
  - The covering footprints stop **5.9 m** north of it. A strip wider than about 6 m on the north bank would still
    reach the southern row (93), which the season test does not use.
  - The 4 sampled pixels stop **35.9 m** short of it. Before the move, the covering footprints reached 24 m past it.
- **WorldCover 2021.**
  - No tree cell in the 9 footprints (107 cells, all cropland).
  - Nearest tree cell: **142 m north** (27.692042 N, 85.441875 E). Nearest to the south: 303 m, west-southwest.
  - The square and its 30 m margin are all cropland (210 cells).
  - **Built-up:** the nearest cell is 107 m from the square, but **77 m from its 30 m margin**. Three cells fall
    within 100 m of the margin, so the moved square misses `placeholder.py`'s rule (no built-up pixel within 100 m
    of the margin) by about 23 m. The square itself is still at least 100 m clear, which is CLAUDE.md's wording.
- **HLS greenness** (median of the 2016-2025 yearly minima).
  - The 9 covering pixels: 0.19-0.21.
  - The nearest pixel at or above 0.35: **117 m north** (0.36), in the band 116-176 m north that matches WorldCover's
    tree cells.
  - South of the square, the nearest such pixel is 312 m away, to the west.
  - A faint diagonal line of slightly greener pixels (0.24-0.33) runs south-west to north-east, just south-east of
    the square:
    - east of the covering block it is 34 m south of the centre (row 93, cols 210-214);
    - to the west it is 64-124 m south (rows 94-96, cols 204-210).
    - It touches the covering block only at the south-east corner, where the covering pixel itself reads 0.21.
    - The values are far below 0.35. The line is consistent with the river strip the owner describes, but it does not
      prove it.
    - **For the owner:** if the river does run south-west to north-east, its strip comes closest at the square's
      south-east corner. That corner is worth a look on imagery.
- **Season test (`placeholder.py`, 4 pixels).** Passes 2023-2025: peaks 0.784-0.927 (candidate 1 as found:
  0.774-0.890); winter rise after the rice harvest 0.59-0.64.
- **Conclusion.** The moved square's pixels reach no tree line and stop short of the river line as described. The
  only rule it misses is the built-up margin (77 m against 100 m), which follows from the owner's move north.
  - Map: `field_nudged_treeline.png` in session 7a992fe8's scratchpad. It shows both squares, the covering pixels
    and the river line.

---

## High

### H1. Rain-fed paddy gets unlimited water, and irrigated paddy reports 0 mm of irrigation
- `pipeline/twin/soil_water.py:70-73`: on every ponded day `supply = max(0, dr - (rain - q) + etc)` is added
  with no source. It refills the whole root zone on transplanting day and covers any shortfall on up to 9
  dry days in a row. `pipeline/twin/season.py:24-35, 86` pond every rain-fed rice day until the first
  10-day dry run.
- Measured in `data/checks/demo/replay_station_dryrun.json`: rain-fed rice gets **120 to 203 mm of
  `pond_supply_mm` per season**. That is the same as the irrigated case in 5 of 6 seasons (same supply, 110
  ponded days). In the irrigated case `irrigation_mm` is 0 for rice.
- What follows from this:
  - Rain-fed and irrigated rice are the same by construction.
  - "Every rice season 100%" (`VALIDATION.md:68`) is not evidence.
  - The 4.4b "no change at Ky 0.8/1.2" result (`VALIDATION.md:73`) comes from this flaw, not from robustness.
  - CLAUDE.md:288-289 ("irrigation ... its total is reported") is not met for paddy.
  - `pond_supply_mm` is not used anywhere outside `pipeline/twin/` (grep), so the replay and export never show it.
- Overclaims and inconsistencies:
  - `VALIDATION.md:37` (2.2, "balance closes to 0.0000 mm") counts this unsourced water as a valid inflow.
  - `METHOD_NOTES.md:11` says the top-up is "booked" but not that it is external water in the rain-fed case.
  - CLAUDE.md:291-293 says "no water stress **while rain plus irrigation keep the field wet**". The code never
    checks that rain keeps the field wet.
- Fix direction: in the rain-fed case, limit the pond to rain (a pond-depth store with bund height), or at least
  report `pond_supply_mm` as irrigation-equivalent water and label rain-fed rice results as such.

### H2. Every Kathmandu Airport value is derived from GSOD synoptic reports; the S-flag is ignored
- `pipeline/fetch/ghcn.py:42` reads `sid, date, elem, value, _m, qflag = r[:6]` and never looks at the
  S-FLAG (`r[6]`).
- In the cached file for 2001-2025, **every** record has S-flag `S`: PRCP 5,036/5,036, TMAX 4,707/4,707,
  TMIN 2,404/2,404.
- The GHCN-Daily readme's note on S values reads: "derived from hourly synoptic reports exchanged on the
  GTS. Daily values derived in this fashion may differ significantly from 'true' daily data, particularly
  for precipitation (i.e., use with caution)."
- `DATA_AUDIT.md:172-176` marks the station "VERIFIED" and lists only the Q-FLAG handling. The source caveat
  appears nowhere.
- Everything that relies on the station inherits this:
  - Decision A's reference and the "independent" held-out results: `VALIDATION.md:59, 62`.
  - 3.7 "POWER 21.3% drier": `VALIDATION.md:55`.
  - The spike flags and the vote labels "station value suspect" / "real local storm": `rules.yaml:63-66`.
  - The 2015/16 wheat "match", which used station rain: `VALIDATION.md:68`.
- The station "0.0" readings on flagged POWER-high days (`DATA_AUDIT.md:246`: 2009-07-28, 2024-06-25) may be
  missing synoptic reports rather than dry days. This is unverified.
- The GHCN-vs-DHM gap at `DATA_AUDIT.md:177` (194.1 vs 239.7 mm) fits the same pattern.
- Fix direction: record the S-flag in the card and in DATA_AUDIT 1.11, and label station rain "synoptic-derived,
  use with caution" wherever it is used as truth.

### H3. The field the pipeline uses is the rejected construction plot; files disagree on which field is current
- CLAUDE.md:19-25 and `METHOD_NOTES.md:22` say the 100 m square at 27.6785 N, 85.427417 E was a construction
  plot, replaced by a 60 m square.
- `config/fields/demo.yaml` still holds the old field:
  - lines 6-9: the header describes the 100 m square;
  - lines 15-17: lat, lon and polygon are the rejected square;
  - line 20: `elevation_m` is NASADEM over the rejected square.
- Everything derived from demo.yaml is therefore for the rejected plot:
  - the ET0 elevation (`weather.py:106`);
  - the NASADEM card;
  - `gpm.py:111-112` (field cell fixed at fetch time). `weather.py:91-93` reads `gpm.parquet` without
    checking which cell it was built for.
- `VALIDATION.md:24` (1.4) still says **PASS: "the placeholder field is cropland"** for that square. It
  should be withdrawn or marked FAIL.
- `VALIDATION.md:4`, `DATA_AUDIT.md:8, 217` still name the 100 m square as the field.
- `pipeline/fetch/placeholder.py:188-197` labels whatever `demo.yaml` holds as "Rejected first placeholder
  (construction plot)". After demo.yaml is updated, a rerun will label the chosen field as rejected.

### H4. Crop stage lengths contradict the crop calendars, so standard rotations are infeasible
- **Maize** (`crops.json:145-150`): 30/50/60/40 = 180 days, but the default calendar window says 120-140 days
  (`crops.json:174-183`).
  - Sown about 31 March, the season ends about 27 September, overlapping every rice window (sow 1 June to
    15 July).
  - `pipeline/plans/simulate.py:66-68` will therefore reject maize→rice, a standard hill rotation, with
    "crops overlap".
- **Lentil** (`crops.json:271-274`): 170 days, against a calendar of 120-145 days with harvest by 15 March
  (`crops.json:288-296`). Sown about 31 October, it ends about 18 April.
- Only rice and wheat were scaled to the local season (`crops.json:2`). `METHOD_NOTES.md:18` says "stage
  lengths scaled to the local season" in general, which overclaims.
- **Mustard** (`crops.json:328-349`): the windows contradict themselves. Sowing 15 Sep-15 Oct with harvest
  15 Mar is 150-180 days, but `days` says 100-150. The second window is 120-150 days against a listed 100-120.
- **Finger millet** (`crops.json:436-441`): `days` 148-149 counts from nursery sowing, but `sow` is the
  transplant date. The two use different starting points.
- **Buckwheat** (`crops.json:368-371`): stages, kc, zr_m and p are all null, so it cannot be simulated. It is
  still listed as a library crop (CLAUDE.md:481-482) and step 7 must exclude it explicitly.

---

## Medium

### M1. Frost is used as a count after all, from a Tmin known to overcount cold nights
- CLAUDE.md:226-227 and `rules.yaml:56-61` say that both corrections overcount cold nights, so frost is shown
  "as risk bands ... never as a count".
- `rules.yaml` `events.frost` (about lines 148-151 at review time) still turns a **single** night below the
  threshold (wheat 0 C mid-season; potato -2 C over the whole season) into the year's `event: frost`, using
  `tmin_frost_c`.
- That is a count-based use of the same overcounting series. Held out, it gave 15 nights below 2 C against 9
  at the station (`VALIDATION.md:62`).
- The potato threshold comes from stage-specific critical temperatures (germination, flowering, fruiting) but
  is applied to the whole season.
- CLAUDE.md:324 defines a frost night as below 0 C, while potato now uses -2 C. That is a second, undefined
  convention.

### M2. GPM fetch carries on after partial failures, and its card misreports
- `pipeline/fetch/gpm.py:144-145` stops only when **every** request fails. Any smaller failure becomes NaN
  rain, which `weather.py:93` then fills from POWER with no limit on how much.
- The card is wrong in three places:
  - `gpm.py:161`: `fill_values_removed` counts every NaN (failed downloads and days without a granule) as
    "-9999.9" fills.
  - `gpm.py:162`: `records_dropped=0` even when days failed.
  - `gpm.py:163`: `date_range` is the requested range, not the coverage actually obtained.
- Rule 12a is not met: `read_subset` (`gpm.py:62-81`) reads the units and `_FillValue` but prints neither,
  and `raw_attrs` (`gpm.py:165`) holds only the grid.
- `gpm.py:10, 163` state "UTC days (05:45 to 05:45 Nepal time)" as fact, while CLAUDE.md:205 and
  `DATA_AUDIT.md:89` mark it TODO-VERIFY.

### M3. DATA_AUDIT contradicts itself on GPM and on gridded data
- GPM status disagrees with itself:
  - line 23: "No: blocked ... EULA not accepted";
  - line 42: B4 still open;
  - line 229: "BLOCKED (B4)";
  - line 82: "DOWNLOADING (EULA accepted 2026-11-12)".
  - At review time `data/raw/gpm/demo/final/` already held 931 daily files.
- `VALIDATION.md:51, 57` still give the EULA as the blocker.
- Several lines cite B3, which line 41 closed:
  - line 90 ("NOT YET POSSIBLE (B2, B3)");
  - lines 235-237 (section 2: "no gridded data (B3)", although WorldCover, NASADEM and GRACE are gridded and
    downloaded, and line 21 already counts 16 NASADEM pixels over the field);
  - lines 248-249.

### M4. GRACE scale factor: contradictory records, and the method is unproven
- `DATA_AUDIT.md:160` says the factor is "recorded, **not applied**"; `DATA_AUDIT.md:163` says "**applied**".
- `pipeline/fetch/grace.py:8-9` says "recorded, not applied", but `grace.py:82` applies it.
- The factor's own description is "based on CLM data" (land hydrology). The mascon covers glaciers and snow
  (`rules.yaml:165`). No source was checked for applying a CLM-derived gain to a glacier-influenced mascon.

### M5. SoilGrids: the cell in use breaks the 1 km rule, and the new WCS reader has silent paths
- `DATA_AUDIT.md:27`: the cell in use is 1.07 km from the field, above the limit at `rules.yaml:77-79`
  (1000 m). The TAW values (`DATA_AUDIT.md:128`) and soil group C (`rules.yaml:84`) come from that cell.
- `DATA_AUDIT.md:121-123` still describe the REST cell as "750 m W of the demo point" (the old-city point),
  with "rule TODO-CONFIRM", while `rules.yaml:79` says the rule is owner-approved.
- `METHOD_NOTES.md:16` cites "DATA_AUDIT B5", which does not exist.
- Problems in `pipeline/fetch/soilgrids_wcs.py`:
  - line 8: "cells without a prediction come back as 0" is assumed. The nodata value is printed (line 94) but
    never checked.
  - line 29: `D_FACTOR` is hard-coded, whereas `soilgrids.py:61` checked units on every response.
  - lines 40-42: there is no bounds check. A field north of or west of the box gives a negative index, which
    numpy wraps silently to the wrong cell.
  - line 101: sand, clay, soc and bdod are read from a cell chosen only because the water-content maps have
    values there. A 0 ("no prediction") becomes a real 0% and passes `check()`.

### M6. ET0 humidity: the temperature correction silently changes vapour pressure
- `weather.py:88-89, 109-110` combine POWER's RH2M, which was computed against POWER's own (in winter, up to
  4 C warmer) temperatures, with corrected temperatures through eq. 19 (`ea = RH × es(T_corr)`). The actual
  vapour pressure `ea` therefore falls with the correction.
- `DATA_AUDIT.md:203` says "Humidity: not corrected", which understates this: `ea` is changed.
- Whether to hold RH or `ea` fixed has not been tested. Neither choice appears in METHOD_NOTES.

### M7. Kc and bare-soil evaporation depart from FAO-56 without saying so
- `pipeline/twin/crops.py:8-17` uses FAO-56 Table 12 Kc_mid and Kc_end unadjusted. FAO-56 eqs. 62 and 65
  adjust them when RHmin ≠ 45% or u2 ≠ 2 m/s, which matters in the humid, low-wind monsoon (maize and millet
  as well as rice).
- Kc_ini uses the group values rather than the FAO-56 wetting-interval method (Figs. 29-30).
- Neither choice appears in METHOD_NOTES.
- Bare soil:
  - The constant `bare_kc` 0.3 is "not yet tuned" (`rules.yaml:100-103`; CLAUDE.md:273 says "tune, document").
  - It draws from the next crop's full root zone (`season.py:77-79`, up to 1.5 m) through Ks.
  - FAO-56 bare-soil evaporation dries only the surface layer (TEW/REW, eqs. 71-74).
  - So a long fallow hands the next crop a profile that is too dry. This is undeclared.

### M8. The cold-night and correction evidence is weaker than the docs state
- CLAUDE.md:223-226, `rules.yaml:58` and `METHOD_NOTES.md:15` say quantile mapping has the "better
  coldest-night error and nights below 2 C". The evidence:
  - The coldest-night error comes from **3 Januaries** (`VALIDATION.md:69`: QM errors 1.0, 1.2 and 4.7 C,
    offset errors 1.8, 1.6 and 5.1 C; one year dominates).
  - The nights-below-2 C result rests on **9 station nights**.
  - No uncertainty is given for either.
- `pipeline/twin/qmap.py:8-9` says quantile mapping is "used only if it is better on all three". The code
  (lines 78-80) and the owner's decision use it regardless, and it is worse on MAE.
- Calling held-out years "independent" (`VALIDATION.md:13, 59, 62`) overstates them. They are independent in
  time only. They do not test:
  - whether the airport (GSOD-derived, see H2; urban; about 6-7 km away) represents the field. DHM Bhaktapur
    sits almost on the field (`DATA_AUDIT.md:181`).
  - whether offsets fitted in 2015-2023 hold for 2001-2014, given POWER's warning about source changes
    (`DATA_AUDIT.md:75`).
- `bias.py:43` and `weather.py:58-59`: a month with no fitted offset passes through uncorrected. It is
  marked only in a per-day boolean, not reported loudly.

### M9. Claimed weather checks do not exist; rain is misattributed in the card
- `DATA_AUDIT.md:208` claims "no day with Tmin > Tmax after correction". No such check exists in
  `pipeline/`, `scripts/` or `tests/` (grep).
- `weather.py:111` range-checks `tmax_c` and `tmin_c` but not `tmin_frost_c`.
- `weather.py:123-124`: the card's `source` and `resolution` name only POWER (and the station), even when
  the rain column is GPM at 0.1 deg. This breaks rule 12e.

### M10. Day-alignment overclaim
- `DATA_AUDIT.md:176` says "the station's days line up with POWER's local solar days". The lag-0 maximum
  (r 0.634) shows only that no whole-day shift does better. It does not establish a common day boundary.
- `ghcn.py:101` itself still says "day boundary TODO-VERIFY".

### M11. The placeholder "green in both seasons" test cannot show a crop
- CLAUDE.md:22-23 and `METHOD_NOTES.md:22` describe the chosen square as "green in both the monsoon and
  winter".
- The test (`placeholder.py:55-70`) is only a monthly-median NDVI peak above 0.25. Grass, weeds and trees
  all pass it, and `placeholder.py:9-11` admits it "does not separate a fallow or cleared plot".
- With `half_m=30` (line 178), the test samples the roughly 2 × 2 HLS pixels whose centres lie within 30 m of
  the square's centre. Their footprints reach up to 15 m beyond the 60 m square. (Corrected 2026-11-12: this
  line first said 15-30 m.)
- `placeholder.py:185` hard-codes `limit = 1000` instead of reading rules.yaml.
- `placeholder.py:186` compares `None > limit`, which raises TypeError whenever the WCS map is absent
  (`soil_distances` returns None).

### M12. HLS "clear" excludes water, which may remove flooded-paddy observations
- `DATA_AUDIT.md:98` defines clear as Fmask bits 0-5 all zero, and bit 5 is water.
- Paddies at transplanting may be flagged as water and dropped as not clear. Those are exactly the dates that
  identify rice.
- The effect is unverified and should be tested on the June-July months before the season detection uses it.

### M13. VALIDATION numbers that disagree or are stale
- Wheat 2016 rain-fed appears as **59.6%** (`VALIDATION.md:39`, 2.4) and "60%" (line 68), but also as
  **55%** in the dry run (line 68). Same season, same rain source; the difference (probably the starting
  depletion) is not explained.
- `VALIDATION.md:22` says 466 tests. Collection gives **493** now.
- Totals at lines 104-110 do not add up:
  - "PASS 15" lists 14 items, and leaves out 1.4 and 1.5;
  - "NOT YET POSSIBLE 16" lists 15 items plus 2 more.
- Every replay and dry-run number (4.1, 4.4b) is for wheat→rice on the rejected square. The configured
  rotation is now rice→potato (`demo.yaml:22`).
- Other places still give the placeholder rotation as wheat then rice:
  - CLAUDE.md:495 ("placeholder wheat then rice");
  - `rules.yaml:130-132` (`rotation_unknown: [wheat, rice]`).

---

## Low

- **L1** `pipeline/twin/soil_water.py:72-73`: on the first ponded day after a dry spell, Ks is taken from
  the depletion before the pond supply. ETa is then below ETc while the row reports `ks = 1.0` and
  `dry_day = False`, and the shortfall is booked as deep percolation.
- **L2** `pipeline/twin/season.py:57-63`: `simulate` does not check for overlapping crops (`s < cursor`).
  `season.py:62, 102-110`: a season cut short by the end of the record still gets a `harvest_pct`. Today
  `rotation_plan` protects against both, but step 7's plan generator will call `simulate` directly.
- **L3** `pipeline/twin/yield_.py:3-4, 9`: the docstring and error message say an unpublished Ky gives "no
  harvest number", which contradicts the owner-assumed Ky 1.0. The clamp at 0..100 also lets the FAO-33
  linear Ky relation run past the deficit range it was published for. This is undeclared.
- **L4** Stale TODO-VERIFYs and status words:
  - `et0.py:10` and CLAUDE.md:266-267 still say "page TODO-VERIFY" for the Rs/Rso floor;
    `rules.yaml:71` and `DATA_AUDIT.md:298` give eq. 18, p. 20.
  - `DATA_AUDIT.md:139` says EGM96 is TODO-VERIFY, while `nasadem.py:82` states it as fact.
  - `DATA_AUDIT.md:282-283, 288` list the HLS cloud mask, MODIS layers and GRACE as open; lines 224, 227 and
    159 closed them.
  - `DATA_AUDIT.md:274` lists 4 cards; 8 exist.
  - `demo.yaml:24` gives the station distance as TODO-VERIFY, while `DATA_AUDIT.md:170` has it VERIFIED.
  - `ghcn.py:102` says "about 7 km from the demo field". That is the distance from the old-city point; the
    100 m square is about 6.4 km away.
- **L5** `pipeline/fetch/worldcover.py:87` picks one 3-degree tile from the box centre. A box that crosses a
  tile edge is not handled, which matters for the "fields abroad, no code changes" requirement
  (CLAUDE.md:446-448).
- **L6** `pipeline/fetch/cogwindows.py:82`: a boundless read fills with 0 when a file has no nodata value.
  For HLS that would be NDVI 0 with Fmask 0 ("clear"), i.e. fake bare-soil observations. Unverified whether
  the HLS COGs set nodata; worth one check on a cached file.
- **L7** `pipeline/fetch/appeears.py` and `cogwindows.py` write no data cards and print no raw attributes
  (rule 12a/d). The cards are due "after download", but nothing enforces that before the diary reads the
  files.
