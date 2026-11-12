# Parallel session log: plain words (SI component 3, text only)

Second Claude Code session, 2026-11-12. Scope given by the owner: create or edit only `pipeline/words/`,
`tests/test_words.py` and this file. Read-only use of `config/crops.json`, `config/rules.yaml`,
`config/fields/demo.yaml` and `pipeline/export/schema.json`. No dependency added, no commit, no push.
Backup: `~/khet-sathi-backups/khet-sathi_2026-11-12_123400`.

## What was generated

| File | What it holds |
| --- | --- |
| `pipeline/words/glossary.json` | 32 science terms, one plain sentence each (English and Nepali), with aliases, banned Nepali words, and the basis of each meaning. Includes all nine terms the brief named, plus the ones the screens point to (satellite, ground measurement, data fusion, model-based, field twin, relative yield, water stress, irrigation, drought year, flood year, soil probe, uncertainty, regional water storage, erosion, runoff, the four crop kinds, pest cycle, organic matter, heat stress, resolution, climate projection). `never_on_screens` lists jargon with no entry (data, AI, SI, index...) |
| `pipeline/words/crop_explainers.json` | Nitrogen-fixing, cover, deep-rooting and drought-tolerant crops: a plain title, examples from `crops.json`, and 5 or 6 short claims each, every claim with publisher, title, year, page or section, verbatim quote, URL and date |
| `pipeline/words/tabs.json` | Templates for the five tabs (why, evidence, benefits, unknown, check) and three tips. Each line has `when` conditions, `{placeholders}`, and a `basis` where it makes a claim. Every tab has an "always" or "fallback" line, so it is never empty |
| `pipeline/words/screens.json` | Texts for the ten screens (CLAUDE.md "Site rules"), answer and label sets (with `maps_to` for the UI), glossary links per screen, and shared words (buttons, crop names, months, source kinds, joining words) |
| `pipeline/words/fill_registry.json` | Where the pipeline gets each of the 30 placeholders and 25 conditions: a schema path, a `crops.json` key, a field-YAML key, a word list, or (for twin-only values) a function in the code |
| `pipeline/words/texts.py` | Load, check and fill: `sentences`, `word_count`, `placeholders`, `science_hits`, `fill` (Devanagari digits in Nepali), `render_tab`, `resolve_ref` |
| `pipeline/words/preview.py`, `PREVIEW.md` | Every text as an English and Nepali table, grouped by screen (tabs and tips under screen 8), then shared words, glossary, and crop explainers with their sources. Regenerate with `.venv/bin/python -m pipeline.words.preview` |
| `tests/test_words.py` | 34 tests (below) |

Counts: 304 text nodes (screens 169, glossary 64, tabs 46, crop explainers 25). Every Nepali text
carries `"ne_review": "needs native-speaker review"`. A reviewer replaces that value with their name and
date; the test will then need its check relaxed to "reviewed or needs review" (owner's call).

## Tests (`tests/test_words.py`, 34 tests, all pass; full suite 527 passed)

- Every text has English and Nepali in Devanagari, marked for review. Nepali static text uses Devanagari digits and the danda, never ASCII digits or a full stop.
- No sentence over eight words, in either language, on the screens, tabs, tips and crop explainers. The longest are exactly 8 (29 English, 12 Nepali). Glossary: one sentence of at most 15 words.
- Every placeholder is in `fill_registry.json`, English and Nepali use the same ones, none is unused, and every `from` reference resolves against the real schema, `crops.json`, `demo.yaml`, word files or code. Negative cases are tested.
- Every `when` condition is in the registry and has plain words for the reviewer.
- No glossary term, alias, banned Nepali word or `never_on_screens` word appears in any farmer text (157 English, 40 Nepali entries). Placeholders are skipped, so `{dataset}`-style names are fine.
- Crop explainers: the four kinds are present, examples exist in `crops.json`, lentil is the legume, deep-rooting examples are deeper than the shallowest crop, and every claim has an FAO, CGIAR-centre or NARC source with an https URL, a quote and no TODO.
- Five tabs in order; each plan kind has its own "why"; a rendered tab is never empty for any plan kind, in either language.
- `PREVIEW.md` is up to date, lists every text, and holds no code blocks.

## SI use (paste into SI_LOG.md and CREDITS.md; this session may not edit them)

**SI_LOG.md entry**
- 2026-11-12, Claude (Opus 5.5), parallel session. Drafted all English and Nepali texts in `pipeline/words/*.json`: glossary, crop explainers, five-tab templates, tips, and screen texts.
- A research sub-agent (Claude) opened FAO, CGIAR (CIMMYT, ICRISAT) and NARC pages and PDFs and copied quotes verbatim. Its scratch downloads are in the session scratchpad, not the repo.
- Person to review: a native Nepali speaker reviews every Nepali text; the owner reviews the English and the choices listed below. Not reviewed yet.

**CREDITS.md entry**
- SI: Claude (Anthropic), build-time drafting of plain-language texts and Nepali translations (`pipeline/words/`), and a source search for the crop explainers. Nothing calls an AI service from the site.
- Sources cited in `crop_explainers.json` and `glossary.json`:
  - FAO 2016, *Soils and pulses: symbiosis for life*
  - FAO Newsroom 2024, World Pulses Day
  - FAO Conservation Agriculture pages "Benefits of CA", "Soil organic cover" and "Species diversification" (no date; accessed 2026-11-12)
  - FAO-56 Chapters 1 and 8
  - FAO Crop Calendar, Nepal Hill zone (already credited)
  - FAO International Year of Millets 2023
  - FAO and ICRISAT 1996, *The World Sorghum and Millet Economies*, Annex I
  - FAO 1998, *Emergency Activities Technical Handbook: Prevention*
  - FAO AGROVOC c_6662 and c_1936
  - Paudel et al. 2020, PLoS ONE 15(4): e0231377 (CIMMYT)
  - ICRISAT, finger millet overview page
  - NARC NSSTRC Annual Report 2076/77 (2020)
  - NASA Earth Observatory, *Measuring Vegetation* (2000)

## Choices that need the owner's OK

**Owner's decisions, 2026-11-12** (applied by the build session the same night; tests in `tests/test_words.py`):
- **1 to 5, 8 and 10: approved.** Plan ids `cover_gap` and `follow_shift` are now the ids build step 7 uses
  (`fill_registry.json`).
- **6: approved, pending the owner's own Nepali review.** The Nepali stays "needs native-speaker review".
- **7: Bikram Sambat months first in Nepali,** with the approximate Gregorian months beside them, e.g. बैशाख (Apr–May).
  Each Gregorian month key is named by the BS month that begins in it (about mid-month). Every screen that names a
  month says "Nepali and English months don't line up exactly." English stays Gregorian.
- **9: `temp` is soil temperature from the probe.** Screen 5 now says "How warm the soil is: {temp} degrees." The
  contract's description says so too (CONTRACT_CHANGES.md).
- **Nepali tabs and tips:** the contract now has `plans[].tabs_ne` and `plans[].tips_ne` (owner's go), so the
  "Nepali in the field file is not provided yet" note below is resolved.
- **SI_LOG.md and CREDITS.md:** the entries below were copied into both files.

1. **Screen 7 title.** CLAUDE.md says "last 20 years", but the replay has 25 (2001-2025). The text uses `{year_count}`.
2. **Screen 2's two picture questions.** I chose water source (rain only, canal, well or pump, pipe or other, I don't know) and field shape (flat, steps, slope). Shape is not stored anywhere yet; it would feed the curve numbers once terraces are handled. The alternative is "What do you grow now?", but screen 3 already confirms the guess.
3. **Model-based label (golden rule 8).** Screens say "worked out by computer" and link to the glossary entry "model-based"; the word "model" itself is banned from farmer text. Please confirm this satisfies rule 8.
4. **Plan ids `cover_gap` and `follow_shift`.** These are proposed (the contract only fixes `current`). Build step 7 sets them.
5. **Glossary sentences: up to 15 words** (screens: 8). The glossary is where science lives; 8 was too short to stay accurate.
6. **Probe = "soil stick"** (Nepali: माटो जाँच्ने यन्त्र). **Farm advisor** = कृषि प्राविधिक. **Mustard** = तोरी, because crops.json uses FAO's rapeseed/colza row. **Finger millet** = कोदो, **buckwheat** = फापर, **basket** = डोको.
7. **Months.** Gregorian month names in Nepali script (जनवरी ...). Bikram Sambat months do not line up with them one to one; the native reviewer may want them added.
8. **Nepali numbers.** Written with Devanagari digits (`texts.fill` converts them). Temperature is rounded to a whole degree, so no decimal point appears in Nepali.
9. **Section temperature.** It is shown as "How warm: {temp} degrees". The contract does not say whether it is soil or air temperature; please confirm.
10. **"Sowing dates are typical ones"** and **"Prices and markets are not included"** are always in the "unknown" tab. The groundwater caveat is in every plan's "unknown" tab, as the owner asked ("say it in every explanation").

## Honesty notes on the sources

- **Lentil after rice in Nepal:** rests on a CIMMYT study of the Terai (Paudel et al. 2020). No source opened describes rice then lentil in the Kathmandu valley itself. NARC pages for this were down (500 or 404) or in Nepali only, without the statement.
- **Finger millet:** FAO, ICRISAT and CIMMYT call it hardy and resilient, not drought-tolerant without qualification. FAO and ICRISAT (1996) say it needs slightly more water than most other millets, so that caveat is a claim of its own.
- **"Roots leave channels that let rain in":** partly supported. FAO ties the channels to diverse roots, not to deep roots alone. The claim's note says so.
- **Two claims rest on data rows, not prose.** "Lentil is sown mid-October to mid-November" and "Lentil and mustard grow here in winter" come from the FAO Crop Calendar rows as recorded in `crops.json`; the `quote` field says this.
- **FAO Conservation Agriculture pages have no publication date.** They are cited as "n.d., accessed 2026-11-12".
- **Two glossary meanings rest on AGROVOC.** For crop rotation and cover crop, AGROVOC credits other FAO documents, which were not opened, so AGROVOC itself is cited.
- **Tip "plant across the slope" (contour planting)** has no cited source yet. CLAUDE.md lists it, and its condition needs a sourced slope threshold in build step 8 (TODO-VERIFY).
- **Drought year and flood year** follow the `rules.yaml` event rules, which are still TODO-CONFIRM.

## For the UI teammate

- **Where texts are.** Each screen's texts are in `screens.json` by screen `id` and text `id`. Answer and label sets are keyed by the contract's own values (for example `labels.event.items.drought`), and `maps_to` names the contract field. The five tab names are in `what_to_grow.labels.tab`.
- **Glossary links.** Each screen lists the glossary ids its "what does this word mean?" button should offer.
- **Tabs and tips.** These are filled by the pipeline at build time (step 7) into `plans[].tabs` and `plans[].tips`. The site reads finished strings and never fills tab templates itself. Screen texts with `{placeholders}` need filling from the field file; the registry says from where.
- **Nepali in the field file is not provided yet.** The contract has one string per tab, so a Nepali copy of tabs and tips needs a contract change. It is not proposed here because `pipeline/export/` belongs to the other session. Flagged for the owner.

## Not done (out of scope or blocked)

- Audio and text-to-speech (the brief said text only; the service is a new dependency that needs the owner's go).
- Native-speaker review of the Nepali.
- Wiring `render_tab` into `build_field_json.py` (build step 7, other session's files).
- A contract field for Nepali text and for the method page.
