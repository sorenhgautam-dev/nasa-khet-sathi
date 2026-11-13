# Khet Sathi

**Khet Sathi** means "field friend" in Nepali. It is a phone website that helps small farmers choose
what to grow, and when, in each part of their field. It starts in Nepal and is built to work anywhere.

Made for NASA Space Apps 2026, challenge "Field Shift: Adapting Farms with NASA Data".

> **Work in progress (13 November 2026).** The demo field is a labelled **placeholder** near Bhaktapur, Nepal,
> until we know the real field and what is grown on it. In `site/data/fields/demo.json` the replay, the three
> plans, the diary and the method page are real. Two parts are **not ready yet**: the field's small parts
> (`field.sections`) and the 2040 outlook (`future`). They hold no numbers and are named in the file's `mock`
> list, so the site says "not ready yet". We would rather say that than show a made-up number. The website screens are not
> in this repository yet. An independent review of the whole project is in [REVIEW_2.md](REVIEW_2.md).

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
| GPM IMERG (daily, 0.1°) | The twin's rain. Its rain here jumps in 2017, when the rain gauges behind it stop reporting, so we scale the later years back and show both versions |
| HLS (Landsat and Sentinel-2, 30 m) | Greenness: when the field is green or bare, its seasons, a guess at the crops |
| MODIS (250 m) | Compared with HLS only. No number shown uses it: the field is a small part of one MODIS pixel |
| NASADEM (30 m) | The field's height (for evaporation) |
| GRACE / GRACE-FO | Whether stored water in the wider region is falling (not the field's own well) |
| SMAP L4 (soil moisture, model-assisted) | A check on the twin's soil water. SMAP's direct readings (L3) are not good enough over this valley |
| ECOSTRESS | Downloaded, not used yet (build step 8) |
| NEX-GDDP-CMIP6 | Not downloaded yet (build step 9: climate change to 2040) |

It also uses data from outside NASA: ISRIC SoilGrids (how much water the soil holds; the nearest mapped cell
is 859 m from the placeholder field), ESA WorldCover (to find cropland for the placeholder), NOAA GHCN-Daily
(the Kathmandu Airport weather station: it corrects the temperatures and checks the rain), and, for checking
only, CHIRPS rain, GPCC rain-gauge counts, Nepal's DHM climate normals and monthly bulletins, and FAOSTAT
national harvests. The full list, with versions and citations, is in [CREDITS.md](CREDITS.md).

## Why there is no backend

The judges open the site on their own phones, months after the event, while our laptops are off. So
everything heavy runs here, on our laptops, before we publish:

- the downloads, the twin and the scoring run once per field, ahead of time;
- the website (`site/`) is plain files: HTML, CSS, JavaScript and the JSON this pipeline writes (today `site/`
  holds only the JSON; the screens are a teammate's work and are not in this repository yet);
- the site needs no server, no login and no key, and it never calls an AI service.

Fields are prepared ahead of time, and `site/data/index.json` lists them (today one: the demo field; fields
abroad are build step 11). A field drawn outside every
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
   .venv/bin/python -m pipeline.fetch.soilgrids_wcs --field <id>   # the soil maps for the whole box
   .venv/bin/python -m pipeline.fetch.appeears submit --field <id>     # MODIS and SMAP, cut by NASA
   .venv/bin/python -m pipeline.fetch.appeears download --field <id>
   .venv/bin/python -m pipeline.fetch.cogwindows --field <id> --set hls_l30 hls_s30
   .venv/bin/python -m pipeline.fetch.ghcn --field <id>                # only if a station is named
   ```

3. **Build the daily weather** the twin reads, check the rain, then run the **replay**, the **diary** and the
   **plans**. Where the rain was corrected, the rain-based steps run a second time on the rain as published:

   ```sh
   .venv/bin/python -m pipeline.fetch.weather --field <id>
   .venv/bin/python scripts/run_checks.py --field <id>
   .venv/bin/python scripts/run_rain_check.py --field <id>             # is there a break in the rain record?
   .venv/bin/python scripts/run_replay.py --field <id>
   .venv/bin/python scripts/run_diary.py --field <id>                  # onset, greenness, seasons, calendar
   .venv/bin/python scripts/run_plans.py --field <id>                  # about two minutes
   .venv/bin/python scripts/run_replay.py --field <id> --rain uncorrected
   .venv/bin/python scripts/run_diary.py --field <id> --steps onset,diary --rain uncorrected
   .venv/bin/python scripts/run_plans.py --field <id> --rain uncorrected
   ```

4. **Export and check** the website file:

   ```sh
   .venv/bin/python -m pipeline.export.build_field_json --field <id>
   .venv/bin/python -m pipeline.export.validate
   .venv/bin/python -m pipeline.export.build_words         # the site's words: site/data/words.json
   .venv/bin/python -m pipeline.export.validate --final    # before freezing: fails on any made-up number
   ```

Every download writes a "data card" in `data/cards/<id>/`: the product, version, units, fill values removed
and pixels over the field. Every export must match `pipeline/export/schema.json`.

*Today the export fills in the replay, the diary, the plans, the sources and the method page for the demo field.
The field's small parts and the 2040 outlook come in build steps 8 and 9. For a brand-new field the last step
does not work yet without changes to the code (it starts from an existing site file and writes the demo field's
sources list): that is build step 11, see [REVIEW_2.md](REVIEW_2.md), H6.*

Optional checks, each with its own data card: `pipeline.fetch.chirps` and `pipeline.fetch.gpm_late` (a second and
third look at the rain), `pipeline.fetch.gauge_evidence` (how many rain gauges stand behind GPM's rain),
`pipeline.fetch.smap` with `scripts/run_smap_check.py` (soil moisture), `scripts/run_dhm_bulletin_check.py`
(Nepal's own gauges, if you have their monthly bulletins), and `scripts/run_memory.py` (does a small learned
correction beat the physics twin on years it has not seen? On the demo field it does not, and we say so).

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
