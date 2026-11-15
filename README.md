# Khet Sathi

**Khet Sathi** means "field friend" in Nepali. It is a phone website that helps small farmers choose
what to grow, and when, in each part of their field. It starts in Nepal and is built to work anywhere.

Made for NASA Space Apps 2026, challenge "Field Shift: Adapting Farms with NASA Data".

> **Work in progress (15 November 2026).** The app shows one field: **Kharipati**, a real farm in Kharipati,
> Bhaktapur, Nepal. Its outline and 9 parts come from an open drone map (OpenAerialMap, 5 May 2026). Its crops
> (rice, then potato; our guess from space: rice, then wheat), dates and water source are placeholders until its
> farmer answers; no farmer has checked any number yet. In `site/data/fields/kharipati.json` the replay, the three
> plans, the diary, the parts, the 2040 outlook and the method page are real (its `mock` list is empty). The earlier
> Bhaktapur demo square and four sample fields are hidden from the app; their files are kept. Its numbers are in
> [docs/PITCH_FACTS.md](docs/PITCH_FACTS.md). An independent review of the whole project is in [REVIEW_2.md](REVIEW_2.md).

## Our promise (हाम्रो वाचा)

Nepali first; the Nepali awaits a native speaker's review.

- **हरेक किसानका लागि सधैं निःशुल्क।** Free for every farmer, always.
- **कुनै विज्ञापन छैन, कुनै खाता छैन।** No ads and no accounts.
- **खेतको जानकारी र फोटो फोनमै रहन्छन्।** The field's data and photos stay on the phone: the site never sends them
  anywhere.
- **खुला कोड र खुला डाटा।** Open code and open data, so anyone can check our work or bring it to their own valley.

## What it does

1. It reads more than 20 years of free satellite and weather data for one field.
2. It runs a small model of the field (a "twin"). The twin tracks water in the soil and the crops, day by
   day, from 2001 to 2025. It uses the methods of FAO papers 56 and 33.
3. It tries many crop plans in the twin. It scores each plan on harvest, water, ground cover and soil.
4. It keeps three plans to show: what the farmer grows now, and two others. Each plan says why it was chosen,
   what the evidence is, what we don't know, and what to check locally.
5. It writes small JSON files. The website reads only these files.

Harvest is a percentage of what the field could grow, never tonnes. Every number says where it comes from.
Every plan is marked for local review: the farmer knows their land best.

## The NASA data it uses

| Data | What it is used for today |
| --- | --- |
| NASA POWER (daily, model-based) | Temperature, humidity, wind, sunshine for the twin |
| GPM IMERG (daily, 0.1°) | The twin's rain. NASA's rain combines satellites with ground gauges. From 2017 far fewer gauges near our valley fed into it, so the record stepped up; we corrected for it and show both versions |
| HLS (Landsat and Sentinel-2, 30 m) | Greenness: when the field is green or bare, its seasons, a guess at the crops |
| MODIS (250 m) | Compared with HLS only. No number shown uses it: the field is a small part of one MODIS pixel |
| NASADEM (30 m) | The field's height (for evaporation) |
| GRACE / GRACE-FO | Whether stored water in the wider region is falling (not the field's own well) |
| SMAP L4 (soil moisture, model-assisted) | A check on the twin's soil water. SMAP's direct readings (L3) are not good enough over this valley |
| ECOSTRESS | Downloaded, not used yet (build step 8) |
| NEX-GDDP-CMIP6 | Climate change to 2040: 23 climate models, two futures, at the field's 0.25° cell (shared with the valley) |

It also uses data from outside NASA: ISRIC SoilGrids (how much water the soil holds; Kharipati's 250 m cell holds
156 mm for plants in the top metre), ESA WorldCover (cropland for the area map), NOAA GHCN-Daily
(the Kathmandu Airport weather station: it corrects the temperatures and checks the rain), and, for checking
only, CHIRPS rain, GPCC rain-gauge counts, Nepal's DHM climate normals and monthly bulletins, and FAOSTAT
national harvests. The full list, with versions and citations, is in [CREDITS.md](CREDITS.md).

## Which checks are about Kharipati itself, and which are for the valley

Kharipati sits in the same NASA rain square as the earlier Bhaktapur demo square: one IMERG 0.1° cell (27.6-27.7 N,
85.4-85.5 E) and one NASA POWER cell. We checked: NASA's rain as published and POWER's temperatures are the same for
both, day for day, 2001-2025.

- **For the valley, so they apply to Kharipati:** the rain-record check and its 2017 correction; the checks against
  DHM's rain gauges; the monsoon onset (DHM's record); the month words for rain, heat and frost; Weather ahead; the
  flood and dry years; the 2040 outlook's climate cell; groundwater (GRACE, regional, about 300 km). The area map's
  numbers come from the same 5 km box.
- **About Kharipati itself:** its outline and 9 parts from the drone photo; the drone photo's ripe crop on 5 May 2026
  (a check on our crop guess and bare months); its HLS greenness and seasons (about one 30 m square); its soil cell;
  the replay and the plans, run on its own seasons and soil; and the soil stick's parts.
- **One difference:** the demo square's rain was also tuned to four of Nepal's gauges; Kharipati's is not
  (`config/rules.yaml` `gpm_series.gauge_calibration.fields`).

## Why there is no backend

The judges open the site on their own phones, months after the event, while our laptops are off. So
everything heavy runs here, on our laptops, before we publish:

- the downloads, the twin and the scoring run once per field, ahead of time;
- the website (`site/`) is plain files: HTML, CSS, JavaScript (the screens, built from our teammate's design) and the
  JSON this pipeline writes;
- the site needs no server, no login and no key, and it never calls an AI service;
- it is hosted on GitHub Pages from this repository as plain files: on every push to `main`,
  `.github/workflows/pages.yml` publishes the `site/` folder as it is, with no build step, no server functions and no
  environment variables. Every path in the site is relative, so it works in the site's folder. `scripts/check_site.py`
  checks this.

Live site: **https://sorenhgautam-dev.github.io/data-test-game/**

Fields are prepared ahead of time, and `site/data/index.json` lists them: Kharipati for farmers, and the field in
Madagascar on the world page. The earlier demo square and four sample fields are hidden (`config/rules.yaml`
`site_hidden_fields`); their files are kept. A field drawn outside every
prepared area gets a friendly message instead of an error.

### Works offline after one visit

- **The first opening needs internet.** On that visit the phone saves the whole web app: every field, How we know,
  Behind the scenes and the world page (about 110 files, 7 MB; `site/sw.js`, a service worker; its list and version are
  written by `scripts/build_offline.py` from the final files, and `scripts/check_site.py` checks they are current).
- **After that it opens with no internet**, on that phone and browser, and says "Offline: showing your saved field."
  When the phone is online again and we have published new data, it fetches the new files once and uses them.
- **Live probe readings always need the laptop** (and its hotspot) nearby: `data/live.json` and the probe log are never
  saved for offline use, and on the laptop or its hotspot the service worker is not used at all.
- It works at any address: the worker covers only the folder it is served from (GitHub Pages' `/data-test-game/`, or the
  root of another host), and every path is relative.

Test on a real phone (about 5 minutes): (1) on mobile data, open the live address and wait until the home screen
shows; (2) open "From the sky", "Your field in small parts" and "What should I grow"; (3) turn on aeroplane mode and
close the browser; (4) open the address again: the home screen and those screens show, with the offline line; (5) turn
aeroplane mode off and reload: the offline line goes. Do it once on an iPhone (Safari) and once on Android (Chrome). On an
iPhone, "Add to Home Screen" keeps its own saved copy, so do the test from the home-screen icon too.

## How to run it for a new field

You need Python 3.12 and a free NASA Earthdata login (saved in `~/.netrc`; never in this repository).
For GPM rain, accept the GES DISC data licence on your Earthdata account once.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest                      # everything should pass
```

1. **Describe the field.** Copy `config/fields/demo.yaml` to `config/fields/<id>.yaml`. Set `id`, `name`,
   `lat`, `lon`, the four corners (`polygon`), the download box (`fetch_box`, `bbox`), and the current crops.
   Leave anything you don't know as `null`; the pipeline never guesses it.
2. **Download the data** (each command saves raw files under `data/`, which is never committed):

   ```sh
   .venv/bin/python -m pipeline.fetch.power --field <id>
   .venv/bin/python -m pipeline.fetch.gpm --field <id>
   .venv/bin/python -m pipeline.fetch.nasadem --field <id>
   .venv/bin/python -m pipeline.fetch.grace --field <id>
   .venv/bin/python -m pipeline.fetch.soilgrids_wcs --field <id>   # the soil maps for the whole box
   .venv/bin/python -m pipeline.fetch.appeears submit --field <id>     # MODIS and SMAP, cut by NASA
   .venv/bin/python -m pipeline.fetch.appeears download --field <id>
   .venv/bin/python -m pipeline.fetch.cogwindows --field <id> --set hls_l30 hls_s30
   .venv/bin/python -m pipeline.fetch.ghcn --field <id>                # only if a station is named
   ```

   `scripts/fetch_field.py --field <id>` runs the downloads a field abroad needs in one go, resumably (no MODIS, SMAP
   or ECOSTRESS: nothing shown abroad uses them).

3. **Build everything else with one command**, from the downloaded files only: the daily weather, the rain check,
   the diary, the replay, the plans (on each rain version), the 2040 outlook, the checks, then the website's files
   and their checks (`validate --final`, `check_site.py --final`):

   ```sh
   .venv/bin/python scripts/run_field.py --field <id>                  # about 20 minutes for the demo
   .venv/bin/python scripts/run_field.py --field <id> --list           # the steps; --from <step> resumes, --only <step> picks
   ```

   It stops at the first step that fails. Each step is one script in `scripts/` (or module), which can also run alone.

Every download writes a "data card" in `data/cards/<id>/`: the product, version, units, fill values removed
and pixels over the field. Every export must match `pipeline/export/schema.json`.

*Today the export fills in everything for Kharipati: the replay, the diary, the plans, its 9 parts, the 2040 outlook,
the sources and the method page. A brand-new field now builds from its config
alone (REVIEW_2 H6), and `scripts/make_site.py` runs every step for it (see "Global, usable everywhere" below).*

Optional checks, each with its own data card: `pipeline.fetch.chirps` and `pipeline.fetch.gpm_late` (a second and
third look at the rain), `pipeline.fetch.gauge_evidence` (how many rain gauges stand behind GPM's rain),
`pipeline.fetch.smap` (soil moisture, compared by the runner's `smap_check` step), `scripts/run_dhm_bulletin_check.py`
(Nepal's own gauges, if you have their monthly bulletins; run alone), and the runner's `memory` step,
`scripts/run_memory.py` (does a small learned correction beat the physics twin on years it has not seen? On Kharipati
it does not, and we say so).

## Global, usable everywhere

**Built and verified in Nepal; any organisation can set it up for any field on Earth with one command; better wherever
a country adds its profile. Next step: a hosted service for instant check-ups.**

**Works today: the same pipeline already runs a field in Madagascar**, and it is on the site. **Next steps:** the hosted
service; the Nepal-only parts for other countries (below); and a NASA season outlook, once its skill here is shown: NASA's GEOS-S2S gives only raw monthly numbers, with no ready probabilities, and the published skill of seasonal forecasts at the field (IRI's NMME-based ones) is about zero for December-May (`docs/NEXT_STEPS.md` 9).

- **Global core, local plug-ins.** The twin, the plans and the site are the same everywhere. What is country-specific
  (rain classes, dry day and dry spell, drought seasons, rain gauges, crop-calendar zone, calendar, language, area units,
  fertiliser notes) lives in one profile file per country, each setting with its value and its source:
  `config/countries/NP.yaml` for Nepal. A field in a country with no profile takes the sourced global defaults,
  `config/countries/default.yaml`: ETCCDI's dry day (under 1 mm) and rain indices, NOAA GHCN-Daily and GPCC rain gauges,
  the FAO Crop Calendar for the field's country and zone, Gregorian months and hectares.
- **One command** (`scripts/make_site.py`; how to, logins and hosting in [docs/DEPLOY_ANYWHERE.md](docs/DEPLOY_ANYWHERE.md)):

  ```sh
  .venv/bin/python scripts/make_site.py --lat -18.834 --lon 47.437 --size-m 60 --name "A field" \
      --country Madagascar --country-code MG --aez 004 --rotation rice,potato --out ../my-site --dry-run
  ```

  It writes the field's settings (anything unknown is left as a TODO, never guessed), downloads the public data, runs
  every step, and writes a folder of plain files to host free on GitHub Pages, Vercel or Netlify. It needs a free NASA
  Earthdata login and the GES DISC data agreement. A new field takes about 3 to 4 hours, nearly all of it downloads.
  **Status: built, and used for the Madagascar field.** Partly done: on the global defaults it leaves out the Nepal-only
  steps (the DHM-scaled and gauge-tuned rain, rain at harvest, the fertiliser saver, the heat clock, the Replay window
  and the farmer answers for the coming months), so those say "not ready yet"; and `--short-record` is not ready.
- **A field on another continent.** `config/fields/ambohidratrimo.yaml`, a PLACEHOLDER square in Madagascar's central
  highlands, was built with the kit on the global defaults: its own rain check (no step in its rain record, so NASA's rain is used as
  published), its own FAO crop calendar, and labels that say NOT YET VERIFIABLE where no local check exists. **It is on
  the site:** open it from "Fields we have looked at" on Home (its farmer steps) or on How we know (its own evidence and
  labels), where it reads "A field on another continent, run by the same pipeline." Not made for it yet: the answers
  for the coming months (Next 3 and 6 months, Weather ahead) and the Nepal-only checks; those screens say "Not ready yet".
- **"Could Khet Sathi work here?"** On the site's "Fields around the world" page (`#/world`, from Home's field list and
  How we know), a tap anywhere on the map answers from fixed rules (`config/rules.yaml` `global_use`, each NASA
  dataset's coverage taken from its own documentation, page cited): which NASA records cover the spot, the crops in our
  library (which of them fit needs the field's own data), what we cannot do yet (snowy winters, orchards and vineyards,
  crops outside our library such as soybean), the nearest prepared field and its distance, and "Not prepared yet: one
  command on a laptop prepares a field here". It never shows a number from a field file for a spot that is not prepared.
  The map is Natural Earth's 1:110m land outline (public domain), fetched once at build time
  (`pipeline/fetch/world_outline.py`, `pipeline/export/build_world.py` -> `site/data/world.json`): the site makes no
  outside request. Outside Nepal the app uses Gregorian months and English first; Nepal keeps Bikram Sambat and Nepali.

**What works anywhere, what is Nepal-only**

| Works anywhere | Nepal-only |
| --- | --- |
| The NASA datasets (GPM IMERG rain, NASA POWER weather, HLS greenness, NASADEM height, NEX-GDDP-CMIP6 outlook; coverage limits in `rules.yaml` `global_use.coverage`) | DHM's records and checks (Nepal's Department of Hydrology and Meteorology: normals, onset dates, bulletins) |
| The Field Twin (soil water, crops, harvest as a share of the field's best) | Bikram Sambat months |
| The rain-record check (each field's own test for a step in NASA's rain record when fewer gauges feed it) | The reviewed Nepali texts (every Nepali line still needs a native speaker's review) |
| The 24-year replay (the years differ per field: its complete years) | Ropani, Nepal's land unit |
| The labels (VERIFIED, ESTIMATE, NOT YET VERIFIABLE on every answer) | |

## Next steps (after the deadline)

**Our roadmap, plans and not results, in order** (details, and our plan to test the advice with 10 to 20 farmers through
a cooperative for one season, in [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)): (1) a field's own local rain readings,
a measured soil value and the farmer's real crop calendar; (2) a whole valley prepared in advance, so a tap gives the
nearest prepared plan at once; (3) a one-page printable view for agriculture advisers that works offline; (4) fewer but
stronger outputs; (5) a "what really happened" checker for the season's results; (6) the 2040 outlook rebuilt after
the rain correction; (7) reaching farmers through cooperatives and women's groups, since many farms are run by women.

The full list, with what each would need, is in [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md). Among them: a NASA season outlook, once its skill here is shown: NASA's GEOS-S2S gives only raw monthly numbers, with no ready probabilities, and the published skill of seasonal forecasts at the field (IRI's NMME-based ones) is about zero for December-May (`docs/NEXT_STEPS.md` 9).
First on it: **the rice pond**. Today rain-fed rice runs as a free-draining soil bucket, so water a bunded paddy holds above field capacity is not kept (METHOD_NOTES 103).

## Credits

- **Data and methods:** NASA (POWER, GPM, HLS, MODIS, SMAP, NASADEM, ECOSTRESS, GRACE-FO, NEX-GDDP-CMIP6),
  ISRIC, ESA, NOAA NCEI and FAO. Exact products, versions and citations are in [CREDITS.md](CREDITS.md).
- **Libraries:** listed in [CREDITS.md](CREDITS.md) and pinned in `requirements.txt`.
- **AI (SI) use:** every use is logged in [CREDITS.md](CREDITS.md) and, with what a person reviewed, in
  [SI_LOG.md](SI_LOG.md). AI runs only at build time, never from the public site.
- **How we checked our work:** [VALIDATION.md](VALIDATION.md), [DATA_AUDIT.md](DATA_AUDIT.md) and
  [METHOD_NOTES.md](METHOD_NOTES.md).

## Licence

The code is under the MIT licence ([LICENSE](LICENSE)). The data and texts we use keep their own licences
and terms, for example CC BY 4.0 for ESA WorldCover and SoilGrids. Some are for non-commercial use or have no
open licence (the airport station's values, quotes from FAO publications, DHM's tables): they are not covered
by the MIT licence. See [CREDITS.md](CREDITS.md) for each
source and how to cite it.
