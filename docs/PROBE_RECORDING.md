# What to record with the soil probe

This is the team's list, step by step. It covers four things:

1. The bench test with six cups. This is the proof.
2. The calibration that comes out of it.
3. The bands ("needs water", "good", "too wet").
4. The walk over the four parts, which becomes the replay on the public site.

The bench-test method itself is in `robot/CUPS_PROTOCOL.md`. Follow it exactly; this page only puts it in order and
adds what to send back.

**Rules for every step**

- Never change the probe's code (`robot/firmware/original_probe/`).
- Record only with the real probe on its USB cable. Readings from the fake probe, from a pipe or typed in are refused
  by the tools and never published.
- Never edit or rename the files the tools write. Write down anything odd in the notes file instead (step 5).
- No made-up numbers. If something fails, say so in the notes. A missing reading is fine; a guessed one is not.

## 0. Before you start (5 minutes)

- Use the laptop with this repository, and the probe with its USB cable.
- Plug the probe in. Find its port:
  - macOS: `ls /dev/cu.*`. It looks like `/dev/cu.usbserial-0001`.
  - Windows: Device Manager, then Ports, then a `COM` number.
- Check the probe in the Serial Monitor, or just run step 1. Every 2 seconds it should print a line like
  `Temperature: 23.1 °C  |  Moisture: 45%`.
- Measure the probe's moisture blade with a ruler. Write down, in cm, how deep it goes into the soil (step 5). The tools
  assume 10 cm until you tell us.

## 1. The bench test: six cups (about 90 minutes)

Do this **before** the demo. Without it the site can only say "drier" or "wetter" than the other parts. It cannot give
a water percentage, a band or a "sure" value.

Follow `robot/CUPS_PROTOCOL.md`. In short:

1. **Dry the soil.** Take about 2 kg of field soil from the top 10 cm, with no stones or roots. Dry it in the sun for two
   days until it is dusty-dry, and break the lumps.
2. **Make six cups** of the same size, each with a line about 1 cm below the rim.
   - Weigh one cup filled with water to the line, minus the empty cup: that is the cup volume (1 g = 1 ml).
   - Put **the same dry soil weight in every cup**, about 300 g for a 250 ml cup.
   - Add **weighed water** for 0, 10, 20, 30, 40 and 50 % of the cup volume. For a 250 ml cup that is c1 0 g, c2 25 g,
     c3 50 g, c4 75 g, c5 100 g and c6 125 g.
   - Mix each cup in the bowl. Pack it back to the line in three light layers, the same way every time.
3. **Wait 10 minutes**, with the cups covered.
   - If water pools on top of a cup, write that in its notes.
   - If a cup cannot be packed to the line, write that in its notes.
4. **Fill in `data/probe/bench/cups.csv`**, one row per cup, exactly as shown in `CUPS_PROTOCOL.md`:

   ```
   cup_id,cup_volume_ml,dry_soil_g,water_added_g,notes
   c1,250,300,0,
   ...
   ```

5. **Record each cup: 3 push-ins.** Start with cup c1:

   ```
   .venv/bin/python -m robot.bench --port /dev/cu.usbserial-0001 --cup c1
   ```

   For each push-in:
   - Push the probe in to its line, then press Enter.
   - **Keep it still for 60 seconds.** The first 40 s let it settle and are not used. The next 20 s are measured.
   - Take it out and wipe it.

   Then do `--cup c2`, and so on up to `--cup c6`.
6. **The ice cup.** Fill a seventh cup with half ice and half water, and stir it 5 minutes before use. Put the probe and
   its temperature sensor in, then run `--cup ice`.

The tool writes every line to `data/probe/bench/readings_<date>.jsonl`. You do not need to copy any number by hand.

## 2. The calibration (2 minutes, on the same laptop)

```
.venv/bin/python scripts/run_probe_bench.py
```

This tool reads your cups and push-ins and checks four things (the table in `CUPS_PROTOCOL.md`):

- **Steady:** the readings of one push-in agree within 3 points.
- **In order:** drier cups always read drier.
- **Accurate:** how far off the probe is against the weighed water. This is scored by leaving one cup out each time.
- **Ice:** the ice cup reads 0 °C, give or take 0.5 °C.

If the cups pass, it writes `config/probe_calibration.yaml`. That file is the calibration. If the checks fail, it
writes no calibration. That is a result, not a mistake: send us the files anyway (step 5).

## 3. The bands (nothing extra to measure)

The bands are worked out by the tools, not measured. They come from three things:

- the calibration (step 2);
- the field's own soil (SoilGrids);
- the crop growing now.

What we need from you, in the notes (step 5):

- **the crop in the ground** at the field today (for example potato, wheat, or nothing);
- **the blade's depth in cm** (step 0);
- **where the temperature sensor was**: pushed into the soil next to the blade, or in the air. The site only calls it
  "soil temperature" if it was in the soil.

## 4. The walk: settle, then measure at each of the four parts (about 10 minutes)

The demo field has four parts:

| Part | Where |
| --- | --- |
| s1 | south-west quarter |
| s2 | south-east quarter |
| s3 | north-west quarter |
| s4 | north-east quarter |

At the event the four "parts" may be four pots or trays of soil instead of the field. That is fine. Say so in the
notes; the public replay will say where it was recorded.

1. Join the phone's hotspot with the laptop. Plug in the probe and run:

   ```
   .venv/bin/python scripts/demo_probe.py
   ```

   It prints the address to open on the phone (see `docs/DEMO_CHECKLIST.md`). Write down the **time you start**.
2. At each part, in the order s1, s2, s3, s4, when the laptop asks for it:
   1. Push the probe in to its line, at the centre of that part.
   2. Push the temperature sensor into the soil beside it.
   3. **Then** press Enter.
   4. **Do not touch it for 60 seconds.** The phone shows "settling", then "measuring", then "done".
   5. If it says **"not steady, test again"**, press Enter to measure that part again. Do not move to a new spot.
3. Walk all four parts. Stop with Ctrl-C at the end.

Every line goes to `data/probe/demo/readings_<date>.jsonl` automatically.

If you do a practice walk with the real probe, that is fine. Write down its start time too and say it was practice.
We publish only the walk you name.

## 4b. The garden test (about 45 minutes, before the freeze)

The owner's test of the probe in a garden mini-field (2026-11-14 night). The public site then replays it, labelled "A
garden test of our probe, recorded on <date>". It is not the demo field, so the twin is never updated with it.

1. **Mark the mini-field.** On bare garden soil, mark a square 2 m by 2 m with four sticks and string. Split it with
   string into four patches of 1 m by 1 m. Name them like the field and put a label on a stick in each:
   s1 south-west, s2 south-east, s3 north-west, s4 north-east.
2. **Water one patch only.** Choose one patch. Pour **10 litres** from a watering can evenly over that patch, and none on
   the others. Write down which patch and the time. **Wait 30 minutes** so the water soaks in.
3. **Start the recording.** Plug the probe into the laptop with this repository and run
   `.venv/bin/python scripts/demo_probe.py` (the real probe; never `--fake`). Write down the **time you start**.
4. **Walk the four patches** in the order s1, s2, s3, s4, exactly as in step 4 above: probe in at the patch's centre,
   temperature sensor beside it, then Enter, then **60 seconds without touching**. If it says "not steady, test again",
   press Enter and measure the same spot again.
5. **Stop** with Ctrl-C after s4.
6. **Notes.** Make the notes file of step 5 and add three lines:

   ```
   place: garden mini-field, 2 m by 2 m
   watered patch: s3, 10 litres at 15:20
   last rain before the test:
   ```

7. Send the zip as in step 5, or, on the main laptop, just tell the owner the start time and the watered patch.

What we check: the watered patch should read "wetter than the other parts". If it does not, we say so; we never change a
reading.

## 5. What to send back, and how to name it

Make a notes file in `data/probe/demo/`, called **`notes_<YYYY-MM-DD>.txt`** (for example `notes_2026-11-16.txt`).
Put this in it:

```
date: 2026-11-16
who recorded:
place: the demo field / four pots of field soil at the event / ...
walk to publish: started 10:30 (and any practice walks: started 10:05, practice)
crop in the ground:
last rain or watering:
blade depth (cm):
temperature sensor: in the soil / in the air
bench test date: 2026-11-15
anything odd (a pulled cable, a cup that pooled, a part tested again):
```

Then zip the whole **`data/probe/`** folder. Call the zip **`khet_probe_<YYYY-MM-DD>.zip`** and send it to the owner.
It holds:

| File | Made by | What it is |
| --- | --- | --- |
| `data/probe/bench/cups.csv` | you (step 1.4) | the cups' weights and notes |
| `data/probe/bench/readings_<date>.jsonl` | `robot/bench.py` | every line of every push-in |
| `data/probe/demo/readings_<date>.jsonl` | the bridge (step 4) | every line of the walk |
| `data/probe/demo/notes_<date>.txt` | you (step 5) | the notes above |

Also send `config/probe_calibration.yaml` if step 2 wrote it, and `data/checks/probe/bench.json`.

Photos are optional: one of each part with the probe in, named `photo_s1_<date>.jpg` and so on. They are for us only and
are never published.

## 6. What happens next (the owner, on the main laptop)

```
.venv/bin/python scripts/run_probe_bench.py                      # if the bench files came from another laptop
.venv/bin/python scripts/build_probe_log.py --field demo --session <the walk's session id> --place "<place from the notes>"
.venv/bin/python scripts/build_probe_log.py --field demo --session <the garden walk's session id> --garden   # the garden test (4b)
.venv/bin/python -m pipeline.export.validate
.venv/bin/python scripts/final_check.py
```

- The session id is in the first line of `data/probe/demo/readings_<date>.jsonl` (`"kind": "session"`). It starts with
  the date and the start time, for example `2026-11-16T103012_serial`.
- `build_probe_log.py` writes `site/data/probe_log.json`, the public replay.
  - Every reading keeps its date and time.
  - The file says "Recorded on <date>" and where it was recorded.
  - It keeps the twin's "sure" before and after each reading, but only after the bench test.
- Until real readings exist there is no `probe_log.json`, and the site says "not ready yet".
