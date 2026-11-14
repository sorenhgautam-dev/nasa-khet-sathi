# The farmer's locked answers: files the scorecard reads (2026-11-14)

The farmer's dates and best and worst years are locked test data (rules.yaml `verification.locked_test.farmer`; owner's
D3). Type them from `farmer.yaml` (notes/REAL_FIELD_RECORDING.md) into the two files below, convert Bikram Sambat to AD
by hand, then lock each file before any score reads it:

```
.venv/bin/python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" data/field_visit/demo/farmer_dates.csv
```

and add one line per file to `config/locked_test.yaml`: `data/field_visit/demo/farmer_dates.csv: <sha256>`.
`scripts/run_verification.py` refuses a file that is not locked, or that changed after it was locked.

## data/field_visit/<field>/farmer_dates.csv: Field Pulse season dates (scorecard row `season_dates`)

| column | meaning |
| --- | --- |
| crop | crops.json name: rice, wheat, potato, lentil, maize, mustard, buckwheat, finger_millet |
| year | the year (AD) the crop was harvested |
| planted | sown or transplanted, YYYY-MM-DD |
| harvested | YYYY-MM-DD |

One row per crop and year (three recent years asked). Each date passes within 10 days (one dekad) of the Pulse's HLS
season of the same slot and year: planted against green-up minus the crop's initial stage, harvested against the
season's end (rules.yaml `pulse.farmer_scoring`).

## data/field_visit/<field>/farmer_years.csv: worst and best years (scorecard row `harvest_years`)

| column | meaning |
| --- | --- |
| kind | worst or best |
| year | the year (AD) the crop was harvested |
| crop | crops.json name |
| why | the farmer's words (not scored) |

Scored twice: the field's replay (a worst year in our lowest third, a best year in our highest third, 2002-2025), and the
25-Year Replay (`harvest_years.replay_window`: the current plan's 6-month window from the default start, only the rows
whose crop grows in that window; rules.yaml `window_replay.farmer_scoring`). Until the files exist both say NOT YET
VERIFIABLE.
