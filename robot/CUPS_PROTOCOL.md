# The probe's bench test (the proof)

The probe says moisture on its own scale: 0 % in air, 100 % in water. That is not the soil's water. Six cups of soil
with weighed water turn one into the other and show how steady, how ordered and how accurate the probe is. Until the
bench test is done the site shows only "drier / wetter than the other parts" and no "sure". Never change the probe's
code. About 90 minutes. (Owner's probe brief, 2026-11-14, fix 3; rules in `config/rules.yaml` `probe.bench`.)

## You need

- The probe, its USB cable, the laptop with this repository.
- **6 cups of the same size** (plastic, about 250 ml), a marker, a kitchen scale (1 g steps), a bowl, a spoon, a cloth.
- **About 2 kg of soil from the field** (top 10 cm, no stones or roots), spread thin and dried in the sun for two days
  until dusty-dry. Break the lumps.
- A seventh cup of **ice water** (half ice, half water, stirred, 5 minutes before use).

## Make the cups

1. Draw a line on each cup about 1 cm below the rim. **Cup volume:** fill one cup with water to the line and weigh it,
   minus the empty cup: grams = ml (1 g = 1 ml). Write it down; all cups are the same size.
2. Use **the same dry soil weight in every cup** (about 300 g for a 250 ml cup).
3. Add **weighed water so the cups hold 0, 10, 20, 30, 40 and 50 % of the cup volume as water**. For a 250 ml cup:
   c1 0 g, c2 25 g, c3 50 g, c4 75 g, c5 100 g, c6 125 g. Mix each in the bowl until even, put it back in its cup and
   pack it to the line (press lightly with the back of the spoon, in three layers, the same way every time).
4. **Wait 10 minutes.** If water pools on top of a wet cup, or its soil cannot be packed to the line, write that in the
   cup's notes: the analysis leaves such a cup out by a rule written down before any fit (soil cannot hold more water
   than its pore space). Cover the cups so they do not dry.
5. Fill in **`data/probe/bench/cups.csv`** (one row per cup; the ice cup is not in it):

   ```csv
   cup_id,cup_volume_ml,dry_soil_g,water_added_g,notes
   c1,250,300,0,
   c2,250,300,25,
   c3,250,300,50,
   c4,250,300,75,
   c5,250,300,100,
   c6,250,300,125,water pooled on top
   ```

## Record (3 push-ins per cup)

Plug the probe in and find its port (macOS `ls /dev/cu.*`, Windows: Device Manager, COM port). For each cup:

```
.venv/bin/python -m robot.bench --port /dev/cu.usbserial-0001 --cup c1
```

It asks for **3 push-ins**: push the probe in to its line, press Enter, keep still for about **20 s** (the first 5
lines, 10 s, settle and are not used; the next 5, 10 s, are measured), then take it out and wipe it. It prints each
push-in's median, spread and temperature, and logs every line to `data/probe/bench/readings_<date>.jsonl`. Then
`--cup c2` ... `--cup c6`, and last `--cup ice` with the probe and its temperature sensor in the ice water.

## Results

```
.venv/bin/python scripts/run_probe_bench.py
```

writes `data/checks/probe/bench.json` with four proofs, and **only if the cups are real and in order**,
`config/probe_calibration.yaml` (the fit, its error, the date, the number of cups, "made from the bench test of <date>,
not field-tested"). Send us `cups.csv` and the `readings_*.jsonl` files if you run it elsewhere.

| Proof | VALIDATION | Passes when |
| --- | --- | --- |
| (a) steady | 5.2 | every push-in's 10 measured lines lie within 3 points (max - min); the spread between a cup's 3 push-ins is reported. The pooled variance of the repeats is the probe's error R for the Kalman `sure` |
| (b) in order | 5.3 | the cups' values rise strictly with the water added (Spearman reported) |
| (c) accurate | 5.1 | true water % = water_added_g / cup_volume_ml x 100, fitted to the probe's % with a straight line (a curve only if, with 5+ cups, it lowers the leave-one-cup-out error by 1 point); the score is the leave-one-cup-out mean absolute error in water-% points ("give or take"), never on the cups it was fitted on; residuals reported |
| (d) temperature | - | the ice-water cup reads 0 C within 0.5 C |

It also reports how long settling really takes (from each push-in's first line until its lines stay within 3 points of
its median).

## No scale: the spoon method (a rough calibration)

Owner, 2026-11-15; rules in `config/rules.yaml` `probe.bench.spoon` (committed before any cup was measured). **4 cups,
one spoon, level spoonfuls only.** A small spoon (a teaspoon) is better: more spoonfuls, less rounding.

1. Mark a line on each cup about 1 cm below the rim. **N:** count level spoonfuls of water to the line in one cup (do
   it twice; if the counts differ, use the mean). If the cup has a printed volume (ml), note it. Empty and dry the cup.
2. **Water per cup:** c1 0, c2 10 %, c3 20 %, c4 30 % of N, to the nearest spoonful (N = 50: 0, 5, 10, 15).
3. For each cup: fill it with the air-dried soil to the line (press lightly, three layers), tip it into the bowl, add
   its spoonfuls of water, mix until even, pack it all back to the line the same way. If it will not all go back, or
   will not reach the line, write `pack` in its notes (it is left out) and make it again if you can. Cover the cups.
4. Write `data/probe/bench/cups.csv`:

   ```csv
   cup_id,cup_spoons,water_spoons,printed_volume_ml,notes
   c1,50,0,250,
   c2,50,5,,
   c3,50,10,,
   c4,50,15,,
   ```

5. Record **driest cup first** (c1, c2, c3, c4), 3 push-ins each, and **let go of the probe** while it measures:
   `.venv/bin/python -m robot.bench --port <port> --cup c1` ... `--cup c4`. Then `scripts/run_probe_bench.py`.

The reference is the water added, w / N (m3/m3); the soil's own starting water is unknown, so the dry point may be a
few percent above zero. The result is labelled "rough calibration (spoon measures, air-dried soil)". It is used for the
fog only if the cups rise in order and the leave-one-cup-out RMSE is at most 0.04 m3/m3 (NASA SMAP's yardstick); its
own error is then added to the probe's in the Kalman update. If it does not pass, there is no calibration file and the
site keeps "drier / wetter than the other parts".
