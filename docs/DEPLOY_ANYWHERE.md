# Deploy anywhere: a Khet Sathi site for any field

Written 14 November 2026 (owner's item 3: "global, usable everywhere"). One command makes a Khet Sathi site for one field,
anywhere on Earth: it writes the field's settings, downloads the public data, runs every step, and gives you a folder of
plain files to host for free. Built and checked in Nepal; a field in Madagascar was made with it on the global settings
(below).

## What you need

1. **A computer with Python 3.12, git and about 2 GB of free disk.** Then, once:

   ```sh
   git clone https://github.com/sorenhgautam-dev/data-test-game.git khet-sathi && cd khet-sathi
   python3.12 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python -m pytest -q          # every test should pass
   ```

2. **A NASA Earthdata login** (for GPM rain, HLS greenness, MODIS, NASADEM and GRACE). Register at
   https://urs.earthdata.nasa.gov/ ("EOSDIS data are openly available to all and free of charge except where governed by
   international agreements"). Keep the login in `~/.netrc` in your home folder, never in the repository. The easiest
   way: run `.venv/bin/python -c 'import earthaccess; earthaccess.login(strategy="interactive", persist=True)'`, type
   your user name and password once, and earthaccess writes the file for you (its `persist` option: "persist credentials
   to a `.netrc` file", earthaccess 0.19.0). Or write the file yourself: one line with three pairs, `machine` followed by
   urs.earthdata.nasa.gov, then your Earthdata user name, then your password, each pair as Earthdata's own instructions
   show (https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget). Then `chmod 0600 ~/.netrc`.

3. **The GES DISC data agreement, accepted once.** GPM's rain comes from NASA's GES DISC servers: "Access to GES DISC
   data requires all users to be registered with the Earthdata Login system", and you must authorise the application
   **"NASA GESDISC DATA ARCHIVE"**: in your Earthdata profile, open *Applications*, then *Authorized Apps*, then *Approve
   more applications*, search for it and press *Authorize*.
   **Warning:** the GES DISC page says "Access to this server (and all other GES DISC data servers) will end no earlier
   than September 30th 2026. Users will need to transition to Earthdata Cloud." On 14 November 2026 the servers still
   answered. If they stop, `pipeline/fetch/gpm.py` needs moving to Earthdata Cloud (docs/NEXT_STEPS.md).

No other account is needed. NASA POWER, CHIRPS, SoilGrids, ESA WorldCover, NOAA GHCN-Daily, GPCC and the FAO Crop
Calendar need no login.

## One command

```sh
.venv/bin/python scripts/make_site.py --lat -18.834 --lon 47.437 --size-m 60 --name "Rakoto's field" \
    --country Madagascar --country-code MG --aez 004 --rotation rice,potato --out ../rakoto-site
```

- `--dry-run` prints the plan first: the settings it will write, what it will download (and what is already held), how
  many megabytes and minutes, and the build steps. Nothing runs.
- `--short-record` keeps only the last 10 years (2016-2025), for faster downloads. **Not ready yet** (see "Not ready
  yet" below): the downloads take it, the build does not.
- `--field <id>` uses a field whose `config/fields/<id>.yaml` already exists.
- Run the same command again after any failure: every download resumes where it stopped.

What it does, in order:

1. **Writes `config/fields/<id>.yaml`** from the point, the size (a 60 m square around the point) and the name. Anything
   it does not know is `null` with a `TODO`, never guessed:
   - `current_rotation`: the crops grown now, in order (`--rotation rice,potato`). The build stops without it.
   - `fao_crop_calendar.aez`: the FAO crop-calendar zone. List a country's zones, with their districts, with
     `.venv/bin/python -m pipeline.fetch.cropcalendar --zones MG`, and pick the one holding the field.
   - `water_source`: unknown is allowed. Then the site shows both cases, "if you can water" and "if you can't".
   - `validation_station`: optional, a nearby NOAA GHCN-Daily station, for checks only.
2. **Picks the country's profile**, `config/countries/<ISO2>.yaml`, or the global defaults, `config/countries/default.yaml`
   (below).
3. **Downloads** with `scripts/fetch_field.py` (logs in `data/raw/_logs/<id>_<step>.log`).
4. **Builds** with `scripts/run_field.py`: every step for a field with a country profile. On the global defaults it runs
   the steps that need only global data: the weather, the rain check, the diary, the replay, the plans and the site's
   files. Left out there, so the site says "not ready yet" for them: the Nepal-only rain versions (DHM-scaled,
   gauge-tuned), rain at harvest and the fertiliser saver (written with DHM's rain classes and Nepal's urea prices), the
   heat clock (needs the 2040 climate runs), and the 25-year replay window and its simple page (need the twin's state
   today, a Nepal step). `scripts/make_site.py --dry-run` lists each with its reason.
5. **Copies a static site folder** (`--out`). It holds the app and only this field's data, with an `index.json` listing
   it.

## How long it takes

Times as measured for the field in Madagascar (14 November 2026). NASA's servers set the pace.

| Step | Full record (2001-2025) | Size |
| --- | --- | --- |
| GPM IMERG rain (daily, 6 at a time) | about 75 min | 285 MB kept |
| CHIRPS rain (a check) | about 30 min | about 1.5 GB read, 0.6 MB kept |
| HLS greenness (2013-2025) | about 30 min | 40 MB |
| MODIS greenness (AppEEARS: NASA cuts the box, then you wait in its queue) | 77 min here | 1 MB |
| Rain-gauge counts (IMERG and GPCC) | about 30 min | 10 MB |
| POWER, NASADEM, SoilGrids, GRACE, FAOSTAT, GHCN, FAO Crop Calendar | 1 to 2 min each | under 60 MB |
| Build: weather, rain check, diary, replay | under 1 min | |
| Build: the plans (67 crop plans here, 25 years, two water cases; Nepal's 165 take about 3 min) | about 1.5 min | |
| Build: the site's files and the folder | seconds | 1.6 MB |

So a new field takes about **3 to 4 hours**, nearly all of it downloads. The kit prints its estimate before it starts
and the time each step took.

## Country profiles: global core, local plug-ins

The twin, the plans and the site are the same everywhere. What is country-specific lives in one file per country, each
setting with its value and its source (as `config/rules.yaml`). A field in a country with no profile takes the global
defaults:

| Setting | Nepal (`NP.yaml`) | Global default (`default.yaml`) |
| --- | --- | --- |
| Rain classes | DHM's five, light to extremely heavy (heavy = 50 mm or more in 24 h) | ETCCDI thresholds: under 1 mm, 1 mm (wet day), 10 mm (R10mm), 20 mm (R20mm) |
| Dry day, dry spell | under 1 mm; the longest run (CDD), as DHM's 2024 report defines it | ETCCDI: under 1 mm; CDD |
| Drought years | DHM's seasons (monsoon June-September, winter December-February) | the calendar year's wet-day total (ETCCDI PRCPTOT), lowest fifth |
| Monsoon start | CLAUDE.md's rule, checked against DHM's dates | none (no global rule): "can't tell" |
| Rain gauges | NOAA GHCN-Daily (Kathmandu Airport), DHM normals, bulletins and onset dates | NOAA GHCN-Daily (nearest station) and GPCC gauge counts |
| Crop calendar | FAO Crop Calendar, Hill zone, hand-checked in `config/crops.json` | FAO Crop Calendar for the field's country and zone (58 countries), read by `pipeline/fetch/cropcalendar.py` |
| Calendar, language | Bikram Sambat first; Nepali first, English one tap away | Gregorian months; English |
| Area | hectares (no sourced ropani conversion found) | hectares |
| Fertiliser notes | shortages at paddy planting; urea in 50 kg bags | none |
| Scorecard | checked against DHM's gauges and records | none: every label says NOT YET VERIFIABLE |

A country adds its profile by writing `config/countries/<ISO2>.yaml` with the settings it knows (the rest come from
the default) and committing it before its first run. Better local data then replaces the global defaults: its own rain
classes, gauges and seasons, its language, and its checks.

## Host it free

The folder is plain files (HTML, CSS, JavaScript and JSON): no server, no login, no key, no build step. Every path in it
is relative, so it works at a site's root or in any folder. Open it through a web server, not by double-clicking
`index.html` (browsers block the data files then): `python3 -m http.server -d ../rakoto-site 8000`.

- **Netlify:** drag the folder onto Netlify Drop (https://app.netlify.com/drop). "If you drop a project without being
  logged in, Netlify publishes the files as-is." Netlify's free plan is "$0 forever".
- **GitHub Pages:** put the folder's files in a public repository (or its `/docs` folder) and choose *Settings, Pages,
  Deploy from a branch*. "Published GitHub Pages sites may be no larger than 1 GB"; on GitHub Free the repository must be
  public.
- **Vercel:** import the repository, Framework Preset "Other", Build Command empty, Root Directory the folder. "The
  Hobby plan is free".

## What the labels say on the global defaults

A field built on the global defaults is honest about what was not checked:

- its rain check is its own (each field tests its own rain record for a gauge break; Madagascar found none, so its rain
  is used as published);
- every number's label says **NOT YET VERIFIABLE**: there is no country scorecard, and it never borrows another field's;
- what needs Nepal's records (DHM's normals, bulletins and monsoon dates) is simply absent: no monsoon-start words, no
  "checked against gauges" claims;
- the crop calendar, the drought rule and the dry spell are the global ones, and the sources list says so.

## The field on another continent

`config/fields/ambohidratrimo.yaml`: a 60 m PLACEHOLDER square in Madagascar's central highlands (FAO zone "Highlands Zone
South"), rainy-season rice then dry-season potato, built with
`scripts/make_site.py --field ambohidratrimo --skip-fetch --out <folder>` on the global defaults (no Madagascar profile).
Its results are in VALIDATION.md (3.26).

Its zone's FAO calendar lists four of the library's crops (rice, wheat, potato, maize: no lentil), so it has three rice
rotations: rice then potato (today), rice then wheat ("Fill the empty months") and rice alone. The third plan is rice
alone, the only rotation left (rules.yaml `plans.third_plan_fallback`), with less cover than today, and it is named
"Safest in bad years" (`plans.third_plan_name_no_legume`), not "Feed your soil": nothing in it feeds the soil.

**Built, not on the live site yet.** The pieces of the app written for Nepal now follow the field's profile: its labels
name its own station and FAO zone (no DHM), Field Pulse shows no typical seasons (Nepal's "monsoon" and "winter" slots
do not fit a rainy season that crosses the new year), the method page says its list of choices is the whole project's,
and `validate --final` accepts the files only a country profile makes (VALIDATION 3.26). Still to do: the third plan's
words ("This plan is here to feed your soil" and NARC's dhaincha lines) and its name on screen, which the site takes from
the plan's id. Then `scripts/run_field.py --field ambohidratrimo --only export pulse checkup labels` and
`python -m pipeline.export.build_index` put it on the site.

## Not ready yet

- **The shorter record (`--short-record`).** The downloads take the years (`record_years` in the config), but the
  build assumes 2001-2025 in several places (the rain check's 2001-2016 reference, the diary's years before HLS, the
  replay's labels). Dropped under the owner's stop rule; listed in docs/NEXT_STEPS.md.
- **A map picture for a new field.** `pipeline/fetch/basemap.py` rebuilds every field's picture at once, so the kit
  leaves it out; the map then shows the world picture.
- **A hosted service** that does all of this for a farmer in minutes (docs/NEXT_STEPS.md).
