# Sources check (2026-11-14)

The owner's rule: "Open each source before using its number, and check the number is really there."
Every source below was opened on **2026-11-14** (access date for all entries). PDFs were downloaded to the session
scratchpad and read with `pdftotext -layout`. Page numbers are printed page numbers unless marked "PDF p.".
Quotes are copied from the source; `[...]` marks a cut.

## Summary

| # | Claim | Verdict | One-line finding |
| --- | --- | --- | --- |
| 1 | DHM: heavy rain is 50 mm/day or more | CONFIRMED | Heavy = "50 mm or more but less than 100 mm" in 24 h. Five classes, every lower bound inclusive. The page does not define a dry day. |
| 2a | DHM: a dry day is below 1 mm | CONFIRMED WITH CONDITIONS | Not defined by name. It is implied by CDD ("RR < 1mm") and wet day ("RR ≥ 1.0mm"), in Table 6 on p.16. |
| 2b | DHM: a dry spell is 8 or more dry days | NOT FOUND | No 8-day rule. The report only uses CDD, the yearly **maximum** run of days under 1 mm (national baseline: 51 days). |
| 3 | Dhaincha before rice = 50-100 kg fertiliser N/ha | CONFIRMED WITH CONDITIONS | The exact words are "equivalent to 50-100 kg of fertilizer N (Lacsina et al., 1987)". There is no "/ha" and no growth period in that sentence. The booklet is NARC 2014, and its URL has moved. |
| 4 | Lentil leaves 23-45 kg N/ha | CONFIRMED WITH CONDITIONS | Both ends are in **one** sentence of an Indian MSc thesis citing Quinn (2009): "carry-over of N [...] 23–45 kg N ha-1". The Saskatchewan paper gives neither number; its recovered residue N is only 2.3 kg/ha. |
| 5 | Fertiliser shortage at planting | CONFIRMED | Kathmandu Post, Post National Bureau, 26 May 2026. |
| 6 | Urea in 50 kg bags | CONFIRMED | "Rs. 847 per 50 kg bag of urea" (BankingNews, 16 Jul 2026). The Kathmandu Post gives "Rs894.50 per 50-kg sack". |
| 7a | Wheat pollen damaged outside 8-35 °C | DIFFERENT | FAO-66 says this about **rice** (p.106), not wheat. For wheat, FAO's *Bread Wheat* gives ">30°C during floret formation cause complete sterility". |
| 7b | Wheat grain filling above 34 °C cuts grain size | CONFIRMED WITH CONDITIONS | FAO-66 p.98. It describes temperatures that are "possible", not a tested threshold, and does not say which daily temperature. |
| 7c | Potato cold stress at 1 °C or below | CONFIRMED WITH CONDITIONS | FAO-66 p.187, not the Y4011e page (a wheat chapter). No crop stage, and no daily min/max is given. |
| 7d | Potato heat stress at 35 °C or above | CONFIRMED WITH CONDITIONS | Same sentence on FAO-66 p.187. |
| 8 | GEOS-S2S open on a 0.5° grid, feeds NMME | CONFIRMED WITH CONDITIONS | Public NCCS folder with **no login**: netCDF-4, 720 x 361 (0.5°), about 1 MiB per variable, member and lead. Values are **raw monthly means**: no anomalies, no probabilities. NASA is in NMME as of June 2025 (version 2); version 3 has run since March 2026. |
| 9a | IRI: monthly, 6 months ahead, 1°, NMME-recalibrated, no account | CONFIRMED WITH CONDITIONS | All true, but the Data Library **web pages now need a free sign-in**. Data downloads (tsv/netCDF/OPeNDAP) still work without one: a one-cell read succeeded. A licence applies (non-commercial use is free) and Kirtman et al. 2014 must be cited. |
| 9b | Skill (RPSS) for Nepal, Dec-May | CONFIRMED WITH CONDITIONS | Global hindcast RPSS is published (1991-2020). At the field's 1° cell, Dec-May skill is about **zero** for both rain and temperature. |
| 10a | 1 ropani = 508.72 m² | NOT FOUND (no government or academic source opened) | The national statistics site was unreachable (2 tries). 74 ft x 74 ft gives 508.74 m², not 508.72. |
| 10b | Urea N share | COMPUTED | 28.014 / 60.056 = **46.6 %**, so a 50 kg bag holds 23.3 kg N. |
| 11 | WRSI: < 50 failure, 80-95 average (Smith 1992) | < 50: CONFIRMED. Table: SITE REFUSED | The WRSI readme on the IRI Data Library needs sign-in (2 tries). FEWS NET gives only "< 50 is regarded as a crop failure condition (Smith, 1992)". "80-95 average" was **not** found in any source opened. |
| 12 | ENSO: ONI ≥ +0.5 / ≤ -0.5; 5 overlapping seasons | CONFIRMED WITH CONDITIONS | The 5-season rule is "for historical purposes". Since **1 Feb 2026** NOAA's official index is the **Relative ONI (RONI)**, not the ONI. The ONI_v5.php address has moved. |
| 13 | HLS DOIs in CREDITS.md | CONFIRMED | Both DOIs resolve and name HLSL30 v2.0 and HLSS30 v2.0. Only L30 was used for the pictures. |
| 14 | Blue Marble citation and reuse | CONFIRMED WITH CONDITIONS | The authors, year and "August 2004" are right. Add the title, and credit "NASA Earth Observatory" on the site (NASA asks for it). |

---

## 1. DHM rain classes

- **Source:** DHM, Meteorological Forecasting Division, "नेपालको मौसम पूर्वानुमानमा प्रयोग हुने शब्दावली / Terms used in Weather Forecasting
  in Nepal", http://dhm.gov.np/mfd/api/image/forecast-terminology/. It is a one-page PDF, not a web page. The PDF metadata gives
  2026-09-17 as its date.
- **Verdict: CONFIRMED.**
- **Quote** (table "Rain intensity based on total accumulated rainfall during 24 hrs"; English as printed. The Nepali names are given
  as they read on the page. The text extraction garbles some conjuncts, so they were checked by eye):

  | Class | Boundaries as printed | Lower bound | Upper bound |
  | --- | --- | --- | --- |
  | Light rain (हल्का वर्षा) | "less than 10 mm" | 0 | < 10 (exclusive) |
  | Moderate rain (मध्यम वर्षा) | "10 mm or more but less than 50 mm" | ≥ 10 (inclusive) | < 50 |
  | Heavy rain (भारी वर्षा) | "50 mm or more but less than 100 mm" | ≥ 50 (inclusive) | < 100 |
  | Very heavy rain (धेरै भारी वर्षा) | "100 mm or more but less than 200 mm" | ≥ 100 (inclusive) | < 200 |
  | Extremely heavy rain (अति भारी वर्षा) | "200 mm or more" | ≥ 200 (inclusive) | none |

- **Conditions:** the classes are 24-hour totals. The page does not say which 24 hours (no clock time); its "Today" is "6 AM to
  6 PM". So "50 mm/day or more" means *heavy or above*. Heavy on its own ends below 100 mm.
- **Dry day:** **not defined on this page.** The page also defines cloud cover (eighths), rain probability and coverage bands
  (<10 %, 10-30 %, 30-50 %, 50-80 %, >80 %), and time periods.

## 2. DHM dry days and dry spells

- **Source:** DHM, *Update of Climate Change Study of Nepal*, Final Report (RFP No. DHM/CD/C/RFP/04-2080/81), August 2024,
  © Government of Nepal, MoEWRI, DHM. Prepared by the consultant RITI (page footers). 183 pages.
  http://dhm.gov.np/uploads/dhm/climateService/Update_of_Climate_Change_Study_of_Nepal_compressed.pdf
- **Definitions table:** Table 6, "Overview of selected twelve climate extreme indices", p.16 (PDF p.21), continued on p.17 (PDF
  p.22). The indices were "calculated using the RClimDex package" (ETCCDI definitions).
  - "Consecutive dry days (CDD, days) | Maximum length of dry spell | Maximum number of consecutive days with RR < 1mm: Let RRij
    be the daily precipitation amount on day i in period j. Count the largest number of consecutive days where: RRij < 1mm"
  - "Consecutive wet days (CWD, days) | Maximum length of wet spell | Maximum number of consecutive days with RR ≥ 1mm"
  - "Number of rainy days (R1mm, days) | Annual count of days when PRCP≥ nn mm | nn is a user defined threshold"
  - p.17 (R95ptot row): "a wet day w (RR ≥ 1.0mm)"
- **2a. Dry day below 1 mm: CONFIRMED WITH CONDITIONS.** The phrase "dry day" is never defined on its own. The < 1 mm rule comes from
  the CDD definition and its opposite, the wet day (≥ 1.0 mm).
- **2b. Dry spell of 8 or more days: NOT FOUND.** The report has no fixed-length dry-spell definition (searched for "8 consecutive",
  "eight", "dry spell" and "dry day"). The only dry-spell measure is CDD, the **longest** run per period. Table 14, p.39 (PDF p.44):
  national CDD baseline (1981-2010) **51 days**; SSP2-4.5 56/58/58 and SSP5-8.5 59/57/57 days (2030s/2050s/2080s).
- **What this changes:** an "8+ day dry spell" cannot be credited to DHM. Either cite another source for 8 days, label it as our own
  threshold, or use DHM's CDD (the longest run under 1 mm).

## 3. Dhaincha as green manure before rice

- **Source:** the URL given (`.../sites/default/files/publication/Green%20Manuring%20booklet.pdf`) returns **404** (2 tries). The same
  booklet is listed on the same site's publications page ("हरियो मल बनाउने सम्बन्धी पुस्तिका", /publications/22) at
  https://doad.lumbini.gov.np/media/publications/Green_Manuring_booklet.pdf (11 pages, opened).
- **Attribution correction:** the booklet is **NARC**, not the Department of Agriculture. Its title page reads: *Green-Manuring for
  Increased Crop Production* (Nepali title in Preeti font, which reads "बढी उत्पादनको लागि हरियो मलको प्रयोग"), Bishnu H. Adhikary,
  Senior Scientist; Nepal Agricultural Research Council, Communication, Publication and Documentation Division, Khumaltar; NARC
  Publication Serial No. 0042-2013/14; January 2014 (2070 BS). It is hosted by the Directorate of Agriculture Development, Lumbini.
- **Language:** the body text is **English**. Only the headings are Nepali, so there is no Nepali sentence carrying the number. The
  section heading is "3. Dhaincha (ढैंचा)" (PDF p.5).
- **Verdict: CONFIRMED WITH CONDITIONS.**
- **Quote** (PDF p.5, section "3. Dhaincha"): "Dhaincha is a popular green-manuring crop for rice and it is reported that nitrogen
  gain by green manured Dhaincha is equivalent to 50-100 kg of fertilizer N (Lacsina et al., 1987)."
- **Conditions and units:**
  - The sentence says "50-100 kg of fertilizer N" **with no "/ha"** (per hectare is implied, not printed). It gives no growth days,
    no species and no place. It is a secondary citation; Lacsina et al. 1987 was not opened.
  - Same booklet, PDF p.6, the in-situ method: "Dhaincha seeds are seeded in the plowed land. Dhaincha plants are then incorporated
    in 6-7 weeks of planting and light irrigation it given for well decomposition [...] After incorporation, rice seedlings can be
    transplanted after 2-3 days." Seed rate: "@ 40 kg seeds/ha for green manuring purpose".
  - Same page, a different timing: "In 3-4 months, Dhaincha crop is ready for incorporation into the soil." (This conflicts with the
    6-7 weeks above.)
  - Other numbers on PDF p.6: "Reports also prove that 50 kg of Dhaincha-N is added after a single crop of Dhaincha in a ha of
    land." "By the use of Dhaincha, total amount of urea-N can be cutdown at least by 50% to the rice crop." "21-25% yield increment
    observed in rice by the application of Dhaincha alone."
  - Species (PDF p.5): *Sesbania rostrata* "can fix 267 kg atmospheric N/ha which is utilized by 1/3rd by the follwing rice crops";
    *S. cannabina* is "available for cultivation in [...] Nepal". It names hills and valleys among the suitable areas: "Terai,
    Inner-terai, River valleys and basins, foot hills and middle mountains of Nepal".

## 4. Lentil nitrogen for the next crop

**4a. Krishikosh:** Mamindla Nagaraju, *Drought management through foliar application and balance supply of nutrients in lentil
(Lens culinaris Medic.)*, M.Sc. (Ag) Agronomy thesis, Banaras Hindu University, Varanasi, India, 2017.
https://krishikosh.egranth.ac.in/server/api/core/bitstreams/ca484984-ae09-41d1-9a85-d3df51acb455/content

- **Quote** (Introduction, p.2, PDF p.13): "The reported amount of N fixed varies from 0 to 192 kg total N ha-1 around a mean of 80 kg
  total N ha-1. [...] Most of the fixed N is removed as grain, leaving only a small percentage in the soil. The carry-over of N from
  lentil is low at 23–45 kg N ha-1 but, in comparison to other legumes like common bean and chickpea, is generally positive." The
  paragraph ends "Quinn (2009)" (reference: Quinn, M. A. 2009, "Biological nitrogen fixation and soil health improvement", in
  Erskine et al. (eds), *The Lentil: Botany, Production and Uses*, pp. 229-247).
- **Both ends of the range (23 and 45) come from this one sentence.** What it measures is "carry-over of N", which is not defined (it
  is not stated whether this is residue N, soil N or an N credit). No country or conditions are given, and it is a secondary
  citation.
- Elsewhere in the thesis (Discussion 5.7, PDF p.80): "lentil is a pulse crop which fixes atmospheric nitrogen about 25 kg ha -1".

**4b. Saskatchewan:** S.P. Mooleki, A.E. Slinkard and C. van Kessel, "Nitrogen and non-nitrogen benefits of lentil in the
succeeding wheat crop", University of Saskatchewan, pp. 292-300 (the PDF metadata title starts "1996").
https://harvest.usask.ca/server/api/core/bitstreams/7d7103d7-1356-45d4-80e4-45e0323cc8d4/content

- **Neither 23 nor 45 appears as an N amount.** Place: Dinsmore, southern Saskatchewan, **Canada**, Dark Brown soil zone, on a
  long-term fallow-wheat site. Lentil was grown in 1994 and wheat in 1995, with 49 kg N/ha of urea banded on the wheat.
- What it does measure:
  - **N fixed by the lentil:** "the lentil in the lentil-wheat rotation fixed 34.7 kg N ha-1 on the average across the landscape"
    (p.300).
  - **N in the lentil residue, and how much the next crop took up:** "Only 2.3 kg N ha-1 was recovered in the subsequent wheat crop.
    [...] it represented 14.6% of the 15.8 kg N ha-1 supplied by the lentil residue." (p.297)
  - **Soil N after lentil:** spring available mineral N, 0-60 cm, **37.9** (lentil-wheat) vs **26.8** (wheat-wheat) kg/ha (Table 2,
    p.297). The difference is 11.1 kg/ha, which the text calls "41% higher" (p.299).
  - Table 4 (p.298), wheat N derived from soil (Ndfs): 41.1 vs 18.4 kg/ha. The difference (22.7) is our arithmetic; the paper does
    not present it as a lentil N credit.
- **What this changes:** "23-45 kg N/ha" should be cited as Quinn 2009 (via the thesis), worded as "carry-over" and labelled a
  literature range. The one field measurement here (Canada, not Nepal) shows a direct residue-N uptake by the next crop of only
  2.3 kg/ha, plus about 11 kg/ha more mineral N in spring.

## 5. Fertiliser shortages at planting

- **Source:** "Farmers scramble for fertiliser as paddy planting season begins amid shortages", *The Kathmandu Post*, byline **Post
  National Bureau**, "Published at : May 26, 2026", "Updated at : May 26, 2026 20:57".
  https://kathmandupost.com/money/2026/05/26/farmers-scramble-for-fertiliser-as-paddy-planting-season-begins-amid-shortages
- **Verdict: CONFIRMED.**
- **Quotes:** "Nepal requires around 250,000 tonnes of fertiliser during the paddy plantation season alone, raising fears of a
  potential supply gap that could hit crop yields and farm incomes." "Farmers say they have suffered for years from shortages of
  fertiliser, seeds and irrigation facilities during the paddy planting season."
- **Conditions:** the districts quoted are Terai and inner-Terai ones (Nepalgunj, Bardiya, Rautahat, Rampur, West Nawalparasi,
  Kailali), not Bhaktapur. The shortage is described for the monsoon paddy season.

## 6. Urea bag size

- **Source:** "Government Policy Guides Fertilizer Distribution, Says Salt Trading Corporation", BankingNews (bankingnews.com.np),
  published 2026-07-16 (page metadata), in English. https://bankingnews.com.np/2026/07/4524/
- **Verdict: CONFIRMED.**
- **Quote:** "The subsidized prices fixed by the government are Rs. 847 per 50 kg bag of urea, Rs. 2,297 per bag of DAP, and Rs. 1,697
  per bag of potash."
- **Second source (same claim):** the Kathmandu Post article in claim 5: "subsidised fertiliser is distributed through cooperatives at
  fixed prices: Rs894.50 per 50-kg sack of urea, Rs2,344.50 for DAP and Rs1,744.50 for potash."
- **Condition:** the price differs between the two (Rs 847 from Salt Trading, July 2026; Rs 894.50 through cooperatives, May 2026).
  The bag size (50 kg) is the same in both.

## 7. FAO crop temperatures

**Sources opened:**
- FAO Irrigation and Drainage Paper 66, *Crop yield response to water* (2012), section "3.4 Herbaceous crops" (editor T.C. Hsiao),
  https://www.fao.org/4/i2800e/i2800e07.pdf. Printed page = PDF page + 88.
- https://www.fao.org/4/Y4011e/y4011e06.htm is **not about potato**. It is E. Acevedo, P. Silva and H. Silva, "Wheat growth and
  physiology", in Curtis, Rajaram and Gómez Macpherson (eds), *Bread Wheat: Improvement and Production*, FAO Plant Production and
  Protection Series No. 30, Rome, 2002. It has no potato content. The potato numbers are in FAO-66.

**7a. Wheat pollen damage outside 8-35 °C at flowering: DIFFERENT.**
- FAO-66 has this sentence in the **RICE** chapter (p.106, PDF p.18): "Generally, damage to the pollen occurs when the temperature at
  ﬂowering is outside the range of 8 to 35 °C." It does not say whether this is the daily maximum, minimum or mean (just "the
  temperature at flowering"). The same paragraph: "Most tropical cultivars die when, in the early vegetative growth phase, the
  average daytime temperature drops below 12 °C for more than three consecutive days."
- The FAO-66 wheat chapter has no pollen or 8-35 °C statement.
- For wheat, the *Bread Wheat* chapter says: "Temperatures above 30°C during floret formation cause complete sterility (Owen, 1971;
  Saini and Aspinal, 1982)." This is during floret formation (before anthesis); the type of temperature is not stated. On frost:
  "Frost can be particularly damaging between flag leaf emergence and ten days after anthesis [...] The damage during this period
  occurs at minimum screen temperatures below 0°C and tissue temperatures of around -4°C (Harding et al., 1990) and is associated with
  radiative cooling in calm clear nights." Here "minimum screen temperature" means daily minimum air temperature.

**7b. Wheat grain filling above 34 °C cuts grain size: CONFIRMED WITH CONDITIONS.**
- FAO-66 wheat, TEMPERATURE, p.98 (PDF p.10): "Temperatures above 34 oC are possible in most wheat-growing regions during grain
  ﬁlling. Such temperatures accelerate senescence and can cause signiﬁcant reduction in grain yield through reduced grain size and
  increase the proportions of shrivelled and undersized grain."
- **Conditions:** it is worded as what is "possible", not as a damage threshold. It does not say which daily temperature (max, min
  or mean); daily maximum air temperature is the natural reading but is not stated. Stage: grain filling.
- Also from *Bread Wheat* (mean temperature): "Over the range of 12° to 26°C increase in mean temperature during grainfilling, grain
  weight is reduced at a rate of 4 to 8 percent/°C".

**7c. Potato cold at 1 °C or below** and **7d. potato heat at 35 °C or above: CONFIRMED WITH CONDITIONS.**
- FAO-66 potato, p.187 (PDF p.99): "Soil and air temperatures affect growth and tuber yield. The temperature for frost or cold stress
  for potato is considered 1 oC and less, whereas that of heat stress is 35 oC or higher. However, potato cultivars vary in their
  tolerance to frost, cold and heat stress, and the extent of damage depends on stress intensity and duration."
- **Conditions:** no crop stage, and no daily max/min/mean. The sentence before it says "soil and air temperatures"; the thresholds
  read as air temperature. The paragraph continues: "Optimum soil temperature for tuber growth is 15 to 18 oC whereas air temperature
  requirements for growing potatoes are a diurnal temperature of 25 to 32 oC and night temperature of 12 to 18 oC." Base temperature
  for GDD: "2 oC" (Stol et al., 1991).

**Stage timing:**
- Wheat, FAO-66 p.93: "ﬂowering of individual heads can last between one and 10 days. Grain ﬁlling usually occurs into the warming
  part of the year when average maximum temperatures are between 20-30 ºC." Spring wheat life cycle "ranges from 100 to 170 days".
- Wheat, FAO-66 Table 1, p.95, "Duration of the main phenological phases of wheat in days from sowing (S)", row **India**:
  S-Emergence "4-", S-Heading "ca. 77", S-Anthesis "70-103", S-Maturity "85-145", spring. So grain filling (anthesis to maturity) is
  roughly 15-40+ days by subtraction (our arithmetic). FAO-66 gives no separate grain-filling length.
- Wheat, *Bread Wheat* Table 3.1 (Chile, 34°S, sown in May), days from emergence: spring type anthesis 100, physiological maturity 140;
  winter type 130 and 170. GS3 "includes the grainfilling period, from anthesis to maturity".
- Potato, FAO-66 p.186: "The plant emerges about 7 days after planting under good conditions. [...] At the early vegetative stage,
  between emergence and tuber initiation, stolon formation begins, followed by tuberization and tuber enlargement. The duration of the
  growth cycle [...] depends on cultivar, temperature and day length." p.185 gives season lengths by region, e.g. "short season crop
  (90-110 days)" in northern China.

## 8. NASA GMAO seasonal forecasts (GEOS-S2S)

- **Pages:** https://gmao.gsfc.nasa.gov/seasonal-forecasts/seasonal-decadal-analysis-prediction/ (this is the **Ver 2** page; a v3
  page also exists) and https://gmao.gsfc.nasa.gov/gmao-products/geos-s2s-2/.
- **0.5° grid: CONFIRMED.** v2 page: "Data collections from GMAO's GEOS-S2S-2 are provided on a regular 0.5°×0.5°
  longitude-by-latitude grid with 720 points in the longitudinal direction and 361 points in the latitudinal direction." The v3 page
  says the same for GEOS-S2S-3. The GEOS-S2S-3 product page: "Version 3 of NASA's GEOS-S2S was released in March, 2026."
- **Feeds NMME: CONFIRMED WITH CONDITIONS.**
  - v2 page: "Seasonal forecasts are submitted to the National MultiModel Ensemble (NMME) project, and are part of the US/Canada
    multi-model seasonal forecasts and used to produce NOAA's seasonal outlook for the nation."
  - CPC NMME page (https://www.cpc.ncep.noaa.gov/products/NMME/about.html): "As of June 8, 2025, the NMME consists of the NCEP-CFSv2,
    ECCC-CanESM5, ECCC-GEM5.2-NEMO, NCAR-CESM1, NCAR-CCSM4, and NASA-GEOS-S2S-2".
  - The current v3 page does not name NMME: "submitted to many national and international multimodel comparisons (IRI, APCN, SubC, AR
    forecast project, for example)". IRI's methodology page lists its current models as CanSIPSv2, NCEP-CFSv2, COLA-RSMAS-CCSM4 and
    GFDL-SPEAR, without NASA. The NASA version-3 files are still delivered to a folder named `NMME` (below).
- **Data access:**
  - GEOS-S2S-2 "Data Access" page: "Data Access information will be provided here at a future date."
  - GEOS-S2S-3 "Data Access" page: "Subsets of the near-real time forecast output created for individual users upon request are
    available from: https://portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/NRT/". Users listed: APCN, AtmRiver, IRI, SubC, PM25.
  - That folder is a **public directory listing: no login, no account.** One listing and two small file headers were read.
  - **URL pattern (latest monthly forecast):**
    `https://portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/NRT/NMME/monthly/<mon><yyyy>/<YYYYMMDD>.<var>.ens<N>.lead<L>.nc4`,
    for example `.../NMME/monthly/nov2026/20261028.precip.ens1.lead1.nc4`. The November 2026 folder (dated 2 Nov 2026) holds 3,150
    files. Start dates: 20261003, 08, 13, 18, 23, 28. Leads 1 to 9. 21 variables, including `precip`, `at` (2 m temperature),
    `t2mmax` and `t2mmin`.
  - **Format and size:** netCDF-4 (HDF5), **1.0 MiB per file** (one variable, one member, one lead, global). The precip file holds
    `PRECTOTCORR` "total_precipitation", units "kg m-2 s-1", shape (1, 361, 720), lat -90..90 and lon -180..179.5 in 0.5° steps.
    The `at` file holds `T2M` "2-meter_air_temperature", units "K". Monthly means, made with `cdo -selname`.
  - **No anomalies and no probabilities are provided** in this folder. Turning them into anomalies needs GEOS-S2S hindcast
    climatologies, which were not found here. GMAO's "Atmospheric Anomalies" page offers T2M and Precip anomaly **plots** only (regions
    include SEASIA).
  - Another route (checked only by its metadata): the IRI Data Library NMME archive,
    `https://iridl.ldeo.columbia.edu/SOURCES/.Models/.NMME/.NASA-GEOSS2S/.FORECAST/.MONTHLY/.prec/`. It is on a 1° grid, with 10
    members and 9 leads; its latest start is S = 801 (October 2026).
- **What this changes:** no login is needed. But the NASA files are raw model totals for one model. A per-farmer "wetter or drier than
  normal" message needs a climatology we do not have. IRI's calibrated probabilities (claim 9), which include NASA's model through
  NMME, are the practical route.

## 9. IRI seasonal forecasts

- **Page:** https://iri.columbia.edu/our-expertise/climate/forecasts/
- **9a. Verdict: CONFIRMED WITH CONDITIONS.**
  - Quotes: "IRI's Seasonal Climate Forecasts are updated every month for the next 6 months into the future. They give
    probabilistic outlooks for temperature and precipitation to be in the above-normal, near-normal, or below-normal tercile
    categories". "The IRI probabilistic seasonal climate forecast product is based on a re-calibration of model output from [...]
    (NMME)." "The output from each NMME model is re-calibrated prior to multi-model ensembling to form reliable probability
    forecasts." "The forecasts are now presented on a 1-degree latitude-longitude grid."
  - Methodology page: the ELR is "trained using hindcast ensemble-means and observed precipitation (or temperature) data over the
    1991-2020 period". Also: "In the case of precipitation, the final probability maps are smoothed spatially with a 9×9 point
    Gaussian smoother." So a single cell is a smoothed value.
  - **Account:** the IRI Data Library **web pages now require sign-in**. The notice reads: "The Data Library now requires all users to
    sign in" (create an account "for free"). It also says: "Only the web interface is affected. Download requests (e.g. netcdf,
    tiff, tsv, OPeNDAP/DODS) do not require authentication". Tested: the downloads below worked without login. The dataset page
    itself redirects to the login page.
  - **Licence** (https://iri.columbia.edu/our-expertise/climate/forecasts/seasonal-climate-forecasts/licensing/): "All IRI forecasts
    are free to use with a license [...] Current seasonal and sub seasonal forecasts may be downloaded without a license.
    Non-commercial licenses are free to use and commercial licenses are also available". It asks that seasonal-forecast use cite
    Kirtman et al. 2014, BAMS 95, 585-601, doi:10.1175/BAMS-D-12-00050.1. The maproom index adds: "Please refer to our licensing
    agreement [...] for permission to use any IRI forecast material. This licensing requirement does not apply to the NMME
    Forecasts." The Columbia licensing page (innovation.columbia.edu/technologies/cu17015) returned **403** (SITE REFUSED).
- **Single-cell read (public, tested):** the field (27.69 N, 85.44 E) lies in the 1° cell centred on X = 85, Y = 28
  (27.5-28.5 N, 84.5-85.5 E). That cell covers the asked box 27.5-28 N, 85-85.5 E.
  - Precipitation: `https://iridl.ldeo.columbia.edu/SOURCES/.IRI/.FD/.NMME_Seasonal_Forecast/.Precipitation_ELR/.prob/X/85/VALUE/Y/28/VALUE/F/last/VALUE/data.tsv`
  - Temperature: the same address with `.Temperature_ELR`.
  - Dimensions (from `dods.dds`): `prob[F=117][L=4][C=3][Y=181][X=360]`, units "percent". F is in "months since 1960-01-01" (360-day
    calendar). L is lead 1-4 months (four overlapping 3-month seasons). C is Below_Normal, Normal, Above_Normal; the order was checked
    by selecting `C/(Below_Normal)` and `C/(Above_Normal)`.
  - Result: latest F = 801.5, which is the **October 2026** issue. The F axis "expires" at 2026-11-14 00:00 UTC, so the November
    issue was not in the Data Library yet.
    - Rain, below/normal/above (%): NDJ 31.8/33.8/34.4; DJF 29.6/34.3/36.1; JFM 30.7/34.0/35.2; FMA 29.6/33.9/36.5.
    - Temperature: NDJ 32.9/31.8/35.4; DJF 31.0/29.8/39.2; JFM 24.1/26.3/49.6; FMA 22.1/26.9/51.0.
- **9b. Skill: CONFIRMED WITH CONDITIONS.**
  - IRI publishes global hindcast **RPSS** maps (no GROC found for the current system). From the maproom "Precipitation Seasonal
    Hindcast Skill" (https://iridl.ldeo.columbia.edu/maproom/Global/Forecasts/skill_precip_seasonal.html): "Seasonal skill score
    based on the historical performance of each calibrated NMME model and their multimodel ensemble (1991-2020). Skill is mapped by
    calendar month for seasonal lead times. Lead 1 = months 2-4 [...] after the forecast is issued." "RPSS values tend to be small,
    even for skillful forecasts. [...] a RPSS value of 0.1 corresponds to a correlation of about 0.44 (Tippett et al. 2010)."
    Reliability diagrams exist only pooled over the tropics and the extratropics.
  - Single-cell skill (public tsv, tested):
    `https://iridl.ldeo.columbia.edu/SOURCES/.IRI/.FD/.NMME_Seasonal_Forecast/.Hindcast/.verification/.monthly_precip_ELR/.lead1/.NMME/.RPSS/X/85/VALUE/Y/28/VALUE/data.tsv`
    (temperature: `.monthly_temp_ELR`). T is the issue month, January to December; the order was checked with `T/(Nov)/VALUE`.
  - Lead-1 RPSS at the field's cell, by target season:

    | Issued | Target season | Rain RPSS | Temperature RPSS |
    | --- | --- | --- | --- |
    | Oct | NDJ | 0.079 | -0.025 |
    | Nov | DJF | 0.039 | 0.003 |
    | Dec | JFM | 0.005 | -0.017 |
    | Jan | FMA | 0.001 | -0.011 |
    | Feb | MAM | -0.031 | -0.029 |

    The highest values at this cell are temperature in the monsoon months: issue May 0.12, June 0.27, July 0.15, August 0.15.
- **What this changes:** for December to May at Bhaktapur, IRI's own hindcasts show **almost no skill** for rain or temperature
  (RPSS about 0; 0.1 would be modest). A "next 6 months" outlook for the winter crop would have to say this plainly, or show only
  "no clear signal".

## 10. Not on the owner's list

**10a. Ropani to square metres: NOT FOUND** (no government or academic source opened).
- The search found only converter websites, blogs and Wikipedia. These say 508.72 m², sometimes 508.74 m².
- A search snippet points to the National Statistics Office's *National Sample Census of Agriculture* national report
  (data.nsonepal.gov.np), which reportedly says "1 Hectare = 19.657178 ropanis". 10,000 / 19.657178 = **508.720 m²**. The site
  **timed out or refused the connection twice** (SITE REFUSED), so this was not checked.
- Arithmetic: the common definition 1 ropani = 74 ft x 74 ft = 5,476 sq ft gives 5,476 x 0.09290304 = **508.737 m²**. So 508.72 and
  508.74 rest on different definitions.
- Suggestion: say "about 509 m²" until the NSO report (or the Standard Measurement and Weight Act, not opened) can be checked.

**10b. Urea's nitrogen share: COMPUTED.**
- Standard atomic weights: IUPAC CIAAW *Abridged Standard Atomic Weights 2024* (https://www.ciaaw.org/abridged-atomic-weights.htm):
  H 1.0080, C 12.011, N 14.007, O 15.999.
- CO(NH2)2 = CH4N2O. Molar mass = 12.011 + 15.999 + 2 x 14.007 + 4 x 1.0080 = 12.011 + 15.999 + 28.014 + 4.032 = **60.056 g/mol**.
- N share = 28.014 / 60.056 = **0.4665, so 46.6 %** (commercial urea is sold as 46 % N).
- A 50 kg bag holds 50 x 0.4665 = **23.3 kg N**.

## 11. WRSI classes (added by the coordinator)

- **USGS WRSI readme:** https://iridl.ldeo.columbia.edu/documentation/usgs/adds/wrsi/WRSI_readme.pdf redirects to the IRI Data
  Library **sign-in page** (2 tries). **SITE REFUSED.** The class table and the readme's citation could not be read.
- **FEWS NET product page** (https://earlywarning.usgs.gov/fews/product/890/, "CHIRPS - Croplands WRSI", updated July 2025), opened:
  - "A case of 'no deficit' will result in a WRSI value of 100, which corresponds to the absence of yield reduction related to water
    deficit. A seasonal WRSI value less than 50 is regarded as a crop failure condition (Smith, 1992)."
  - Reference as given: "Smith, M., 1992. Expert consultation on revision of FAO methodologies for crop water requirements. FAO,
    Rome, Publication 73."
  - Definition: "WRSI = AET / WR * 100", with "WR = PET * KC". Footnote: "Originally developed by FAO, the WRSI has been adapted and
    extended by USGS".
  - **No class table** (no 50-60, 60-80, 80-95 and so on) appears on the page text.
- **Verdict:** "< 50 = crop failure (Smith 1992)": **CONFIRMED** (FEWS NET page). "80-95 = average" and the full band table: **NOT
  FOUND** in any source opened.
- **What this changes:** the Replay's "failed" mark (WRSI < 50) can be cited to FEWS NET / Smith 1992. The "worked" and "struggled"
  boundaries need the readme (a free IRI sign-in, done by a person) or another opened source before they are cited.

## 12. NOAA CPC ENSO threshold (added by the coordinator)

- **The page given** (https://origin.cpc.ncep.noaa.gov/.../ONI_v5.php): the host **does not resolve** (DNS failure). The same page
  on www.cpc.ncep.noaa.gov now says: "This page has moved. The Oceanic Niño Index (ONI) table based on ERSST version 6 is available
  at: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/"
- **ONI v6 page:**
  - "This page will continue to be updated by the 5th of each month, but per NWS Public Information Statement 26-05, the Relative
    Oceanic Niño index (RONI) is used for official monitoring and prediction of the El Niño-Southern Oscillation (ENSO)
    phenomenon."
  - "Warm (red) and cold (blue) periods based on a threshold of +/- 0.5 oC for the Oceanic Niño Index (ONI) [3 month running mean of
    ERSST.v6 SST anomalies in the Niño 3.4 region (5oN-5oS, 120o-170oW)], based on centered 30-year base periods updated every 5
    years."
  - "For historical purposes, periods of below and above normal SSTs are colored in blue and red when the threshold is met for a
    minimum of 5 consecutive overlapping seasons."
- **NWS Public Information Statement 26-05** (13 Jan 2026,
  https://www.weather.gov/media/notification/pdf_2026/pns26-05_Relative_ONI.pdf):
  - "the shift to a Relative Oceanic Niño Index for the official monitoring and prediction of the El Niño-Southern Oscillation (ENSO)
    phenomenon, effective February 1, 2026."
  - "NCEP CPC will define El Niño (La Niña) as a relative, positive (negative) mean SST anomaly of 0.5 degrees C or greater over 3
    consecutive months in the Niño 3.4 region".
  - "Historical El Niño and La Niña events will be categorized based on this index, specifically when there are five or more
    consecutive, overlapping three-month seasons where the RONI is greater than 0.5C (El Niño) or less than -0.5C (La Niña)."
  - "the legacy Niño 3.4 and Oceanic Niño Index files will continue to be updated".
  - RONI file: https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt
- **Verdict: CONFIRMED WITH CONDITIONS.**
  - The ±0.5 °C threshold is right.
  - The **5 consecutive overlapping seasons** rule applies to classifying **historical episodes** ("for historical purposes"). Current
    *conditions* use the 0.5 °C threshold, and the ENSO Alert System also requires an expected 3-month index and an atmospheric
    response.
  - The wording mixes "0.5 or greater" (PNS) with "greater than 0.5" (episode tables), so whether exactly 0.5 counts is ambiguous.
  - Since **1 Feb 2026** the official index is **RONI**, not ONI.
- **Current state:** the ENSO Diagnostic Discussion of 12 November 2026 reports "El Niño Advisory" and "a strong-to-very strong El Niño
  likely through January-March 2027".
- **What this changes:** `pipeline/fetch/oni.py` downloads the legacy `oni.ascii.txt`. It is still updated (now ERSSTv6), but it is no
  longer NOAA's official ENSO index. Either switch to `RONI.ascii.txt` or label the series "legacy ONI".

## 13. HLS DOIs (added by the coordinator)

- **Checked against** CREDITS.md lines 28-30 ("HLSL30 v2.0, doi:10.5067/HLS/HLSL30.002, or HLSS30 v2.0, doi:10.5067/HLS/HLSS30.002;
  NASA LP DAAC").
- `https://doi.org/10.5067/HLS/HLSL30.002` redirects (302) to https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-2.0.
  DataCite gives the title "HLS Operational Land Imager Surface Reflectance and TOA Brightness Daily Global 30m v2.0", publisher NASA
  Land Processes Distributed Active Archive Center, 2021.
- `https://doi.org/10.5067/HLS/HLSS30.002` redirects (302) to https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-2.0.
  DataCite gives the title "HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance Daily Global 30m v2.0", same publisher, 2021.
- DataCite's creator list for both: Neigh, Ju, Roger, Skakun, Vermote, Claverie, Dungan, Yin, Freitag, Justice.
- The GIBS layer metadata for `HLS_L30_Nadir_BRDF_Adjusted_Reflectance`
  (https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/HLS_L30_Nadir_BRDF_Adjusted_Reflectance.json) names the source collection
  "HLSL30", "HLS Landsat Operational Land Imager Surface Reflectance and TOA Brightness Daily Global 30m v2.0", version "2.0",
  C2021957657-LPCLOUD.
- **Verdict: CONFIRMED.** Both DOIs resolve and name the right product.
- **Suggested corrections (minor):**
  - All five basemap cards (`data/cards/{demo,sample-1..4}/basemap.json`) used only `HLS_L30_Nadir_BRDF_Adjusted_Reflectance` on
    2025-11-11. CREDITS could say "HLSL30 v2.0 (doi:10.5067/HLS/HLSL30.002)" and drop the "or HLSS30" part.
  - The basemap cards carry no DOI; adding `doi:10.5067/HLS/HLSL30.002` would make them complete.
  - Aside: CREDITS lines 526-529 say the `sample-1` to `sample-4` pictures are "site/data/basemap/demo.jpg". Check whether that is
    intended.

## 14. NASA Blue Marble citation and reuse terms (added by the coordinator)

- **Checked against:**
  - CREDITS.md line 30: "Blue Marble: Next Generation, August 2004 (Stöckli, R., Vermote, E., Saleous, N., Simmon, R. and Herring, D.,
    2005, NASA Earth Observatory)".
  - CREDITS.md line 530 and `site/data/basemap/world.json`: "(MODIS; NASA Earth Observatory, Stockli et al. 2005)", attribution "NASA
    Blue Marble (Aug 2004), via NASA GIBS".
- **NASA page** (visibleearth and earthobservatory URLs now redirect to
  https://science.nasa.gov/earth/earth-observatory/blue-marble-next-generation):
  - "Blue Marble: Next Generation was produced by Reto Stöckli, NASA Earth Observatory (NASA Goddard Space Flight Center). See The
    Blue Marble Next Generation—A true color Earth dataset including seasonal dynamics from MODIS (880 kB PDF) for acknowledgments.
    Anyone using or republishing Blue Marble: Next Generation please credit 'NASA Earth Observatory.'"
  - "a year's worth of monthly composites at a spatial resolution of 500 meters".
- **The technical PDF** (https://assets.science.nasa.gov/content/dam/science/esd/eo/content-feature/bluemarble/bmng.pdf, dated 17
  October 2005), section 5.5 "Citation of the BMNG", p.11: "R. Stöckli, E. Vermote, N. Saleous, R. Simmon and D. Herring (2005). The
  Blue Marble Next Generation - A true color earth dataset including seasonal dynamics from MODIS. Published by the NASA Earth
  Observatory."
- **GIBS layer metadata** (https://gibs.earthdata.nasa.gov/layer-metadata/v1.0/BlueMarble_NextGeneration.json): title "Blue Marble
  (August 2004)", subtitle "MODIS / NASA Earth Observatory". So "August 2004" is correct for the GIBS layer used.
- **Reuse terms:**
  - The old Earth Observatory "ImageUse" page now redirects to the Earth Observatory home page; no standalone policy page was found.
  - NASA's general guidelines (https://www.nasa.gov/nasa-brand-center/images-and-media/): "NASA content [...] generally are not
    subject to copyright in the United States. You may use this material for educational or informational purposes, including [...]
    Internet Web pages." "NASA content used in a factual manner that does not imply endorsement may be used without needing explicit
    permission. NASA should be acknowledged as the source of the material."
- **Verdict: CONFIRMED WITH CONDITIONS.** The authors, their order, the year and "August 2004" are all correct.
- **Corrections:**
  1. Add the title: "The Blue Marble Next Generation - A true color earth dataset including seasonal dynamics from MODIS. Published
     by the NASA Earth Observatory."
  2. Change the on-site attribution in `site/data/basemap/world.json` from "NASA Blue Marble (Aug 2004), via NASA GIBS" to include the
     requested credit, for example "NASA Earth Observatory (Blue Marble: Next Generation, Aug 2004), via NASA GIBS".
  3. Optional: write "Stöckli" with the umlaut in `world.json` and the card, to match the source.
  4. Do not imply NASA endorses the site.
