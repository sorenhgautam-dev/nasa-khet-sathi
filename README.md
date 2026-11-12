# Khet Sathi

**Khet Sathi** means "field friend" in Nepali. It is a phone website that helps small farmers choose
what to grow, and when, in each part of their field. It starts in Nepal and is built to work anywhere.

Made for NASA Space Apps 2026, challenge "Field Shift: Adapting Farms with NASA Data".

> **Work in progress.** The demo field is a labelled **placeholder** near Bhaktapur, Nepal, until we know
> the real field. Parts of `site/data/fields/demo.json` still hold **MOCK** numbers, and each one is marked as
> mock. We would rather say "not known yet" than show a made-up number.

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

| Data | What it gives the twin |
| --- | --- |
| NASA POWER (daily, model-based) | Temperature, humidity, wind, sunshine |
| GPM IMERG (daily, 0.1°) | Rain |
| HLS (Landsat and Sentinel-2, 30 m) and MODIS (250 m) | Greenness: when the field is green or bare |
| NASADEM (30 m) | Height and slope of the field |
| GRACE / GRACE-FO | Whether groundwater in the region is falling |
| SMAP (soil moisture) | A check on the twin's soil water |
| ECOSTRESS | Surface heat and plant stress (optional) |
| NEX-GDDP-CMIP6 | Climate change to 2040, from many models |

It also uses data from outside NASA: ISRIC SoilGrids (soil), ESA WorldCover (to find cropland for the
placeholder), NOAA GHCN-Daily (a weather station, used for checking), and FAOSTAT (national harvests, used
for checking). The full list, with versions and citations, is in [CREDITS.md](CREDITS.md).

## Why there is no backend

The judges open the site on their own phones, months after the event, while our laptops are off. So
everything heavy runs here, on our laptops, before we publish:

- the downloads, the twin and the scoring run once per field, ahead of time;
- the website (`site/`) is plain files: HTML, CSS, JavaScript and the JSON this pipeline writes;
- the site needs no server, no login and no key, and it never calls an AI service.

A few fields are prepared ahead of time, and `site/data/index.json` lists them. A field drawn outside every
prepared area gets a friendly message instead of an error.

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
   .venv/bin/python -m pipeline.fetch.soilgrids --field <id>
   .venv/bin/python -m pipeline.fetch.appeears submit --field <id>     # MODIS and SMAP, cut by NASA
   .venv/bin/python -m pipeline.fetch.appeears download --field <id>
   .venv/bin/python -m pipeline.fetch.cogwindows --field <id> --set hls_l30 hls_s30
   .venv/bin/python -m pipeline.fetch.ghcn --field <id>                # only if a station is named
   ```

3. **Build the daily weather** the twin reads, then **run the 25-year replay**:

   ```sh
   .venv/bin/python -m pipeline.fetch.weather --field <id>
   .venv/bin/python scripts/run_replay.py --field <id>
   .venv/bin/python scripts/run_checks.py --field <id>
   ```

4. **Export and check** the website file:

   ```sh
   .venv/bin/python -m pipeline.export.build_field_json --field <id>
   .venv/bin/python -m pipeline.export.validate
   ```

Every download writes a "data card" in `data/cards/<id>/`: the product, version, units, fill values removed
and pixels over the field. Every export must match `pipeline/export/schema.json`.

*Today the export fills in the replay only. The diary, plans and future come in build steps 6 to 9, and a
full file for a brand-new field comes in step 11.*

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
and terms, for example CC BY 4.0 for ESA WorldCover and SoilGrids. See [CREDITS.md](CREDITS.md) for each
source and how to cite it.
