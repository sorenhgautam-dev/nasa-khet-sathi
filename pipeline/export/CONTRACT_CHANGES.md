# Contract changes (for the UI teammate)

`schema.json` is the full truth. `site/data/fields/demo.json` is regenerated after every change and
still holds **MOCK numbers**; real numbers arrive from build step 5 on.

## 2026-11-11 (b): owner decisions A13 and D7

| What | Before | Now | What the UI must do |
| --- | --- | --- | --- |
| `future.nothing_changes`, `future.with_plan` | `{harvest: [...]}` | `{harvest, harvest_low, harvest_high}`: three arrays, one value per year in `future.years`, with low <= harvest <= high | Show a range (for example a band on each dial), not one number. Golden rule 11: projections are ranges |
| `diary.groundwater` | did not exist | `{trend_cm_per_year: number, direction: "falling" or "steady" or "rising", confidence: 0 to 1}`, required | A simple picture (well or water level going down, flat or up) plus fog when confidence is low. It is regional (from GRACE satellites), not this one field: say so in the glossary |
| `diary.months[].frost` | `none / risk / frost` | `none / risk / high` | Rename the third icon state |
| `diary.months[].cover` | free text (crop names) | `bare / partial / crop` | Three cover pictures; crop names are no longer here |
| `diary.months[].rain` | `low / medium / high` | unchanged | — |
| `diary.months[].soil` | `dry / medium / wet` | unchanged | — |
| `diary.months[].heat` | `none / some / high` | unchanged | — |

## 2026-11-11 (a): first version (build step 1)

- Section polygons are `[lon, lat]` pairs and the ring is not closed. **Leaflet wants `[lat, lon]`,
  so swap them.**
- `sources[].type` is one of `satellite`, `model`, `station`, `probe`. Show "model" sources as
  model-based (golden rule 8).
- At least 3 plans; one has id `current`. `replay` has a key per plan id, years 2001 to 2025.
- No extra keys are allowed anywhere. Ask before relying on a key that is not in the schema.
