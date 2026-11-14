# How much water does our field hold? A field test for the team

**Why we do this.** The website's field model uses a soil map to guess how much water the soil holds after rain.
The map is a guess for a big square of land. Your field may hold more or less. This test measures it in your own
field. When your numbers arrive, the model will use them and show both answers: the map's and yours.

The number we want is called **field capacity**: the water the soil still holds two days after a soaking, when the
extra water has drained away. (FAO-56, chapter 8; FAO Soils Bulletin 79: "FC is best determined in the field by
saturating the soil and measuring its water content after 48 hours of drainage have elapsed".)

## When

- In a **dry spell**: no rain expected for 3 days. Do not do it on a day after heavy rain.
- Day 1: soak and cover. Day 3 (48 hours later): take the tins. Same day: weigh them wet.

## What you need

- 24 empty tin cans, all the same size, about 7 to 10 cm across and 5 to 10 cm tall, with the bottom still on.
  Make one small nail hole in each bottom (to let air out). Write a name on each tin with a marker, as in the sheet:
  S1-0-1 is part s1, top layer, tin 1; S1-15-1 is part s1, lower layer, tin 1.
- 24 lids or squares of plastic with rubber bands, and 24 plastic bags.
- A kitchen scale that shows grams (1 g steps or finer).
- A spade or trowel, a flat knife, a short flat board, a hammer or stone.
- 4 plastic sheets, each about 2 m x 2 m, and some soil or stones to hold the edges down.
- Water: about 150 litres for each soaked square (600 litres for the four parts). Buckets.
- A ruler, a pen and this sheet. A watch.
- For drying: an oven (best), or a microwave, or a sunny place (see "Dry the soil").

## Before you go: weigh and measure each tin

1. Weigh each empty, dry tin. Write it down as **tin_empty_g**.
2. Put tape over the nail hole. Put the tin on the scale. Fill it with water **to the very top**.
3. The water's weight in grams is the tin's volume in millilitres (1 g of water = 1 ml).
   Volume = (tin full of water) - (empty tin). Write it down as **tin_volume_ml**.
4. Pour the water out, take the tape off, and dry the tin.

## Where

- Your field has **four parts** (s1, s2, s3, s4, as on the website). Do one test spot in each part.
- Pick a spot in the middle of the part, away from the bunds and away from footpaths.
- In each spot, take tins at **two depths**: 0 to 15 cm (the top) and 15 to 30 cm (below it).
- Take **3 tins at each depth**. So each spot gives 6 tins, and the field gives 24.

## Day 1: soak and cover

1. Mark a square of 1 m x 1 m. Pull out weeds. Do not dig it.
2. Build a small soil wall around it, about 10 cm high, so water stays inside.
3. Pour in about **100 litres** of water, slowly, a bucket at a time, over about an hour. Let it soak in.
4. Check: dig a small hole **just outside** the square, at its edge, 40 cm deep. Is the soil wet below 30 cm?
   If not, pour another 50 litres and check again. Fill the small hole back in.
5. When all the water has soaked in, **cover the square** with a plastic sheet. Let it hang over the wall on all sides.
   Hold the edges down with soil. This stops the sun and wind drying it.
6. Write down the time. Come back after **48 hours**.

## Day 3: take the tins (48 hours later)

For each depth, do this 3 times, a hand's width apart, inside the square (not at its edges).

**Top (0 to 15 cm):**
1. Lift the plastic. Scrape off only loose leaves on the top.
2. Hold a tin upside down (open side down) on the soil. Put the board on top. Tap the board until the tin is fully in.
   Push straight down. Do not twist.
3. Dig around the tin. Slide the knife under it. Lift it out with the knife held underneath.
4. Cut the soil flat with the tin's edge. Wipe the outside clean.
5. Put the lid on at once. Put it in a bag. Write the tin's name, the part and the depth on your sheet.

**Below (15 to 30 cm):**
1. Next to where you took the top tins, dig away the top 15 cm to make a flat shelf.
2. Take 3 tins from the shelf, the same way as above. Keep them in the 15 to 30 cm layer.

Put the plastic back if you have to stop. Work in the shade if you can.

## Weigh wet (the same day)

1. Take each tin out of its bag, lid off. Weigh tin + wet soil. Write it down as **wet_with_tin_g**.
2. Do not let soil fall out. If some falls out, write it in **notes**.

## Dry the soil

- **Best: oven at 105 C for 24 hours.** Put the open tins in. (FAO GLOSOLAN-SOP-22: "dry at 105 °C ±5 °C for 24 hours
  or until the constant weight is achieved".) Write **oven** in **dried_how**.
- **Microwave**: never put the metal tin in a microwave. Tip all the soil onto a microwave-safe plate. Heat 4 minutes
  at full power, rest 1 minute, weigh. Repeat until the weight stops changing. (USDA Soil Quality Test Kit Guide.)
  Then put **all** the soil back in its own tin. Write **microwave**.
- **Only if there is nothing else: the sun.** Spread the soil thin on a tray in the sun. Cover it at night. Weigh it
  every day. It is dry when two weighings one day apart are the same. Put all of it back in its own tin. Write **sun**.
  Sun-dried soil still holds a little water, so the result will read a little low. That is fine; we will say so.

## Weigh dry

1. Let the tins cool. Weigh tin + dry soil. Write it down as **dry_with_tin_g**.

## Write it in the sheet

Use the file `notes/field_capacity_template.csv`, one line per tin:

`part,depth_cm,tin,tin_empty_g,tin_volume_ml,wet_with_tin_g,dry_with_tin_g,dried_how,notes`

- part: s1, s2, s3 or s4. depth_cm: 0-15 or 15-30. tin: the name on the tin.
- All weights in grams; the volume in millilitres. dried_how: oven, microwave or sun.
- notes: anything odd (soil fell out, a stone in the tin, rain came, ...).

Send the file to the data team. They put it in `data/field_visit/demo/field_capacity.csv`.

## What the computer does with it

For each tin:

- **water held** = (wet_with_tin_g - dry_with_tin_g) / tin_volume_ml. This is in m3 of water per m3 of soil.
- **soil density** = (dry_with_tin_g - tin_empty_g) / tin_volume_ml, in g per cm3.

Example: empty tin 50 g, volume 250 ml, wet 450 g, dry 370 g. Water held = 80 / 250 = **0.32**. Soil density =
320 / 250 = **1.28 g/cm3**.

Then it takes the middle value (the median) of all tins at each depth. The model uses your value instead of the map's
for the top 30 cm. Below 30 cm it keeps the map. It always keeps the map's "dry limit" (wilting point). The website
then shows two results side by side: the map's and your field's.

The computer stops and asks for a check if a tin looks impossible: lighter wet than dry, or more water than the soil
has room for.

## Sources

- FAO-56 (Allen et al. 1998), chapter 8: field capacity is "the amount of water remaining when downward drainage has
  markedly decreased".
- FAO Soils Bulletin 79 (Shaxson & Barber 2003), glossary of soil moisture terms: measure "after 48 hours of drainage".
- Ottoni Filho et al. (2014), Revista Brasileira de Ciência do Solo 38(6):1750-1764, describing the field method of
  Cassel & Nielsen (1986): flood a plot, cover it with plastic, sample after 48 hours, in the dry season if possible.
- FAO (2023), GLOSOLAN-SOP-22, soil bulk density by the cylinder method: a core of known volume, dried at 105 °C.
- USDA ARS/NRCS (2001), Soil Quality Test Kit Guide, chapter 4 (bulk density; the microwave method).
- USDA-NRCS (2014), Soil Survey Field and Laboratory Methods Manual (SSIR 51), sec. 2.3.1: air-dry soil still holds
  about 1 to 2 percent water.
- The rule the computer follows: `config/rules.yaml` `field_capacity_measured`.
