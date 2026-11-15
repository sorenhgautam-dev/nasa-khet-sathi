# Next steps after the deadline

Written 14 November 2026. Ten steps, the rice pond first (owner's decision 7); the hosted service (8) and the season outlook (9) added the same evening (owner's item 3 and answer 3); more winter crops (10) on 15 November. One paragraph each: why it matters,
and what it would need. Numbers in square brackets are in `docs/PITCH_FACTS.md`.

## 1. The rice pond

**Why.** Today rain-fed rice runs as a soil-water bucket. Water the bunds would hold above field capacity is drained
away each day, so the model's paddy has no standing water. The result: rice never fails in the model. Its lowest year
is 91.2 out of 100, and the sourced monsoon droughts of 2009 and 2015 give 92.9 and 96.4 [H10]. So the winter crop alone
ranks the plans, and a farmer's main worry, a bad rice year, cannot show (METHOD_NOTES 36, 103). **What it needs.** A
pond water balance for paddy days: standing water topped up by rain, lost to evaporation, seepage and percolation, and
spilling over the bund (the FAO and IWMI paddy sources of METHOD_NOTES 100-101). A bund height and the field's
percolation rate, ideally measured: the falling water level in a bunded field (FAO Soils Bulletin 55, VALIDATION 4.8).
Tests against published examples, and a keep rule fixed before the first run, as for the water losses [H9].

## 2. AquaCrop

**Why.** Our harvest number uses FAO-33's straight line: harvest falls in step with the water a crop missed. That line
is pushed far past its range here: in the dry winter of 2024/25, today's potato got about a third of its water [M5].
FAO's AquaCrop model follows the crop's canopy and growth through the season, so it responds to when water is short,
not only how much. **What it needs.** AquaCrop crop files for rice, wheat, potato and lentil, set for Nepal's hills;
farmers' own harvests to check them against (none yet); an open implementation in Python, which is a new dependency and
needs the owner's approval (CLAUDE.md rule 9); and a side-by-side run with the current twin, with a rule fixed in advance
for which one the site shows.

## 3. Through cooperatives and women's groups

**Why.** Many farms are run by women, and advice travels best through people a farmer already trusts. Khet Sathi is
best used with a helper beside the farmer (`docs/PROJECT_PAGE.md`, "How Khet Sathi reaches farmers"). **What it
needs.** A cooperative or women's group willing to try it for one season; a group member who learns to be the helper
(the field from the sky, the crop question, the soil stick, the four answers); the screens tested with that group
first (`docs/FARMER_TEST.md`); and one soil stick, cheap enough for a cooperative to share. It stays free for every
farmer, and the farmer's answers stay on the phone.

## 4. Nepal Bhasa and voice

**Why.** Bhaktapur's own language is Nepal Bhasa, and not every farmer reads easily. Today the site is Nepali first,
English one tap away, and text only (owner, 2026-11-12: no audio). Even the Nepali is mostly unreviewed: 32 of 385 texts
checked by a person so far [I5]. **What it needs.** Native speakers of Nepali and Nepal Bhasa to write and review every
screen word; recorded voices of real people, or speech made on the phone itself (never a cloud service: golden rule
13); and the owner's decision to lift the text-only rule. The farmer test (`docs/FARMER_TEST.md`) would show whether
voice is the bigger need.

## 5. Radar and NISAR

**Why.** HLS sees greenness, not water, and only through clear skies. June, when the monsoon arrives and rice is
transplanted, is the month our two season methods agree least (78% of days) [D5]. A rise in greenness may also be weeds
or the rice nursery, not the crop (VALIDATION 4.2c). Radar sees through cloud and can see a flooded paddy. NASA and
ISRO's NISAR (L-band radar) and ESA's Sentinel-1 (C-band) could date transplanting directly. **What it needs.** Access
to the radar products for the fetch box, a published method for detecting flooded paddies, a check against farmers'
own transplanting dates, and data guards and cards like every other source (CLAUDE.md rule 12).

## 6. A valley-wide atlas

**Why.** Our area map already covers the box around one field: about 4,300 hectares of cropland [A1], built in under
two minutes on a laptop [A9]. It shows how much land sits bare and how little grows two crops [A2, A4]. The same map for
the whole Kathmandu valley would let co-operatives and extension offices see where the empty months are, without a
single field visit. **What it needs.** HLS downloads for the whole valley; a newer cropland map (WorldCover 2021 is out
of date in places: our first placeholder field turned out to be a construction plot, VALIDATION 1.4); a tuned bare line,
checked against farmers' calendars (bare days are graded "low" today); and map tiles, so a phone loads only the part it
shows.

## 7. A co-operative pilot

**Why.** No farmer has checked any number yet [B4]. The scorecard names the data that would: farmers' best and worst
years, their real dates, their real water, and at least 10 fields for the crop guess [G4]. Safe Trial results only come
after a season [E4]. **What it needs.** A co-operative willing to take part, with consent from each farmer
(`notes/REAL_FIELD_RECORDING.md`); at least 10 real fields, each prepared with the same two commands [I3]; the probe's
bench test first [E3]; the farmer test (`docs/FARMER_TEST.md`); and one full season, with the comparison rule written
before it starts. Every plan would still say "try it on one small part first. You know your land best." [E2]

## 8. A hosted service for instant check-ups

**Why.** Today any organisation can make a Khet Sathi site for any field with one command (`scripts/make_site.py`,
`docs/DEPLOY_ANYWHERE.md`), but it takes a computer, a NASA Earthdata login and about 3 to 4 hours, nearly all of it
downloads. A farmer or an extension worker should get a check-up in minutes. **What it needs.** A server that keeps the
global datasets on hand (GPM, POWER, HLS, SoilGrids, GRACE, NEX-GDDP) for whole regions, so a new field only reads its own
cells; the same pipeline, unchanged, as a job queue; country profiles (`config/countries/`) written with each country's
weather office and extension service; the shorter record finished first (the downloads take `record_years`, the build
still assumes 2001-2025); Field Pulse's typical seasons for a field abroad, with season slots taken from each field's own
wet and dry months (left out on the global defaults today, VALIDATION 3.26); and a privacy rule written before launch, since a farmer's field location is personal. The
public site stays static and keeps working without it. GPM's GES DISC servers are moving to Earthdata Cloud ("will end
no earlier than September 30th 2026"), so `pipeline/fetch/gpm.py` would move with them.

## 9. A season outlook, once its skill for Nepal is verified

**Why.** Weather ahead (the app's third choice) says only what usually happened in each month of the field's own 24 years;
it is never a forecast. A real outlook for the coming months would help more. **What it needs.** A seasonal forecast whose
skill at this field is shown first. NASA's GEOS-S2S is open but gives raw monthly means, with no probabilities
(`notes/SOURCES_CHECK.md` 8); IRI's NMME-based forecasts need no account for downloads, but their published skill (RPSS) at
the field's 1-degree cell is about zero for December-May (SOURCES_CHECK 9b), so "NASA's guess" would be the wrong label
today. Dropped from the app by the owner (answer 3, 2026-11-14 evening) until its skill for Nepal is verified.

## 10. More winter crops after rice: pea and cabbage (owner's yes, 2026-11-15 evening)

**Why.** Farmers in the valley grow vegetables after rice, and the app compares only potato, wheat and lentil. The owner
asked for up to three winter crops for which FAO publishes every number the twin needs, grown in Bhaktapur, each
compared with the current plan by the same rule as the others ("usually better than"), labelled "estimate", with How we
know saying that vegetables are usually watered, so the rain-fed result is a low guess. **Step 1 (done, nothing to add).**
The crop library holds eight crops (rice, wheat, maize, potato, lentil, mustard, buckwheat, finger millet); the replay ran
165 plans in 23 crop orders. Every rice plan (rice then potato, wheat or lentil) is already on the farmer screens; the
others put maize or finger millet, upland crops in the FAO calendar, in rice's place, or potato straight after potato.
Mustard and buckwheat are in the library but cannot run (`simulate: false`). **Step 2 (owner said yes; it did not fit
the hour, so it stops here).** Numbers checked by opening each source on 2026-11-15 (a research sub-agent; FAO-56 at
fao.org/4/x0490e, chapters 6 and 8; FAO-66 Table 1; FAO Crop Calendar, Nepal hill zone 002, which lists Bhaktapur;
MoALD Statistical Information on Nepalese Agriculture 2079/80 Table 7.3 p. 135 and 2081/82 Table 7.3 pp. 120-121):

| Crop | Kc ini / mid / end (FAO-56 Table 12) | Zr m, p (Table 22) | Ky (FAO-56 Table 24, from FAO-33) | FAO calendar, Nepal hills | Bhaktapur |
|---|---|---|---|---|---|
| Pea (dry; the calendar's only pea) | 0.4 (legume group) / 1.15 / 0.30 | 0.6-1.0, 0.40 | 1.15 | sow 15 Sep-15 Oct, harvest 15 Jan-15 Feb | 24 ha (2081/82); none listed (2079/80) |
| Cabbage | 0.7 (vegetable group) / 1.05 / 0.95 | 0.5-0.8, 0.45 | 0.95 | transplant 15 Sep-15 Oct, harvest 15 Dec-15 Jan | 75 ha (2081/82); 218 ha (2079/80) |

**What it needs.** No Table 11 stage row is for Asia: take the nearest (pea: Mediterranean 20/30/35/15 days; cabbage:
crucifers or California 40/60/50/15) and scale it to the calendar window, as lentil already is; written into
`config/crops.json` and `rules.yaml`, committed before the first run. Then the replay and 25-Year Replay for "rice, then
pea" and "rice, then cabbage" as extra plans only (the three shown plans and their picks must stay byte-identical), their
symbols and 24-year sheets in the folded "other choices" row, crop names in every language, "Ask your agriculture office"
where no official fertiliser rate or confirmed heat and cold limit exists, and the crop count updated in How we know,
Behind the scenes, README and the project page. **Left out.** Onion: FAO has every number, but Bhaktapur's district
tables list none in either year. Mustard (rapeseed in FAO-56): no Table 11 stage lengths and no seasonal Ky in FAO-56
Table 24 or FAO-66, so it cannot be compared (Bhaktapur: sarsoon 223 ha in 2079/80, 6 ha in 2081/82).


## 11. "Food and sprays" card (owner's request, 2026-11-15 evening): the amounts. A small card without numbers is built (owner, 2026-11-15 night; rules.yaml food_and_sprays)

**Why it was left out.** The owner asked for rice's fertiliser rate and timing exactly as printed in NARC's 2022 paper
(narc.gov.np/wp-content/uploads/2022/05/Article-03.pdf), with each source opened by us. On 2026-11-15 at 21:00 that link
returned 404, the Wayback Machine could not be reached from our tools, and journal.narc.gov.np refused the connection,
so the numbers (said to be 100:30:30 kg N:P2O5:K2O per hectare irrigated, 60:20:20 rain-fed) could not be confirmed.
CIMMYT's news page of 9 August 2022 (cgiar.org, "Nepal government endorses new site-specific fertilizer recommendations
for rice") says MoALD endorsed new rice recommendations in July 2022 and that "the new regime replaces the existing
blanket approach" (the old rates date from 1976); the 2023 page says they entered the DoA's extension guidelines in 2023.
So a blanket rate may no longer be the government's rate. The spray link (npponepal.gov.np/en/pages/78/84661316) opens
the centre's Introduction page, not the registered list; the site lists "List of registered pesticides and their
consumption record 2024" and a 2081 BS registered list (not opened).

**What it needs.** The official 2022/2023 rice recommendation (MoALD/NARC NSSRC, or the DoA extension guideline), opened
and quoted with page; then the card as the owner specified (rule first, tests first): nutrients as printed, urea, DAP and
potash as our arithmetic, sized per hectare, per field and per part; wheat, lentil, potato "Ask your agriculture office";
the fertiliser-saver note; the three spray lines with the registered-list link; How we know: source, what the card is not,
and next steps (NARC's soil map, a soil-test entry per part, a nutrient sensor on the soil stick).
