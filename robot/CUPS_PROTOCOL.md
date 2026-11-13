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

It asks for **3 push-ins**: push the probe in to its line, press Enter, keep still for about **60 s** (the first 20
lines, 40 s, settle and are not used; the next 10, 20 s, are measured), then take it out and wipe it. It prints each
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
