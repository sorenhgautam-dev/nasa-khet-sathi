# Next steps after the deadline

Written 14 November 2026. Seven steps, the rice pond first (owner's decision 7). One paragraph each: why it matters,
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

## 3. Market prices and labour

**Why.** Our harvest score is "out of 100 of what the field could grow", never money [H1]. But a farmer chooses a
winter crop by what it sells for, what seed costs, and how many days of work it takes. Every plan's "unknown" tab says
so today: "Prices and markets are not included." **What it needs.** A public Nepali market-price series with a licence
that allows reuse; labour days per crop from extension sources; and a careful way to show them as a range beside the
harvest, never as a promise of income. Until then the site makes no money claim at all.

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
