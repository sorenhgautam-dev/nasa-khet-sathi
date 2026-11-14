# Tomorrow morning: testing the soil stick (Sunday 15 November)

This is for the team. Do the steps in order. The full details are in `docs/PROBE_RECORDING.md` (the walk) and
`robot/CUPS_PROTOCOL.md` (the cup test). If anything here and those pages disagree, tell the owner.

## The plan for the day

| Time | What happens | Who |
| --- | --- | --- |
| 7:30 | Water one patch or bowl. Make the six cups while it soaks. | the team |
| **8:00** | **The tests start:** the walk first (15 min), then the cup test (about 45 min). | the team |
| **9:30** | **Results to the owner:** the zip file and a short message. | the team |
| 10:30 | Nepali fixes and the final check. | the owner and Claude |
| 11:30 | The video. | the team |
| **14:00** | **Freeze.** Nothing changes after this. | everyone |

## Golden rules

- **Only the real soil stick, on its USB cable.** Never use `--fake`: practice numbers are refused and never published.
- **Never type, guess or change a number.** If something fails, write it down. A missing reading is fine.
- **Never edit or rename the files the tools write.**

## Tonight (10 minutes)

1. Check the laptop that has this project. Open a terminal in the project folder and run:

   ```
   .venv/bin/python -m robot.bench --help
   ```

   It should print help text. If it prints an error, tell the owner tonight.
2. Plug in the soil stick and find its port: `ls /dev/cu.*` (on a Mac). It looks like `/dev/cu.usbserial-0001`. Write it
   down.
3. **The cup test needs dusty-dry soil** (dried in the sun for two days). If you have none, skip the cup test tomorrow and
   do only the walk. The site then says "wetter than the others" instead of a water amount. That is fine.

## 7:30: get ready

**Choose one test: the garden or the bowls.**

- **Garden:** mark a 2 m by 2 m square of bare soil. Split it into four 1 m squares with string. Label them s1 (south-west),
  s2 (south-east), s3 (north-west), s4 (north-east). Pour **10 litres** of water evenly on **one** square only.
- **Bowls (indoors):** fill 4 bowls of the same size with the same well-mixed soil, at least 12 cm deep, pressed the same
  way. Label them s1, s2, s3, s4. Pour **200 ml** of water slowly into **one** bowl only.

Write down which one got water, and the time. **Wait 30 minutes** before testing.

While you wait, make the six cups for the cup test (`robot/CUPS_PROTOCOL.md`, steps 1 and 2). Write each cup into
`data/probe/bench/cups.csv` (make the folder first if it is missing: `mkdir -p data/probe/bench`), for example with
250 ml cups and 300 g of dry soil each:

```
cup_id,cup_volume_ml,dry_soil_g,water_added_g,notes
c1,250,300,0,
c2,250,300,25,
c3,250,300,50,
c4,250,300,75,
c5,250,300,100,
c6,250,300,125,
```

Weigh the real amounts and write those. Keep the cups covered.

## 8:00: the walk (about 15 minutes)

1. Run this, and write down the **start time**:

   ```
   .venv/bin/python scripts/demo_probe.py
   ```

2. At each one, in the order s1, s2, s3, s4, when the laptop asks:
   1. Push the stick in to its line, in the middle.
   2. Push the temperature sensor into the soil beside it.
   3. Press Enter.
   4. **Do not touch it for 60 seconds.**
   5. If it says "not steady, test again", press Enter and test the **same** spot again.
3. After s4, press Ctrl-C (hold Ctrl, press C).

## 8:20: the cup test (about 45 minutes)

Skip this if you have no dusty-dry soil.

1. For each cup, c1 to c6, run (use your port):

   ```
   .venv/bin/python -m robot.bench --port /dev/cu.usbserial-0001 --cup c1
   ```

   Do **3 push-ins** per cup. Each time: push the stick in to its line, press Enter, **keep it still for 60 seconds**, take
   it out and wipe it. Then the next cup: `--cup c2`, and so on to `--cup c6`.
2. **The ice cup:** half ice, half water, stirred for 5 minutes. Put the stick and the temperature sensor in, then run the
   same command with `--cup ice`.
3. Check the results (2 minutes):

   ```
   .venv/bin/python scripts/run_probe_bench.py
   ```

   It says whether the cups passed. If they fail, that is a result too. Send everything anyway.

## 9:10: write the notes

Make a file `data/probe/demo/notes_2026-11-15.txt` with these lines filled in:

```
date: 2026-11-15
who recorded:
test: garden (2 m by 2 m)  or  indoor (4 bowls of the same soil)
walk start time:
watered: s3, 10 litres at 07:30   (or: s3, 200 ml at 07:30)
last rain or watering before the test:
blade depth (cm):
temperature sensor: in the soil / in the air
cup test: done / skipped (why)
anything odd (a pulled cable, a part tested again, a cup with water on top):
```

## 9:30: send to the owner

1. Zip the whole `data/probe/` folder. Call it `khet_probe_2026-11-15.zip`.
2. Also send these two files if they exist: `config/probe_calibration.yaml` and `data/checks/probe/bench.json`.
3. In the message, write two things: **the walk's start time** and **which one got the water**.

Photos are welcome (one of each patch or bowl with the stick in). They are for us only and are never published.

## What happens next

Claude builds the public soil screen from your walk. It will say "Garden test of our soil stick, recorded on 15 November
2026" (or "Indoor test of our soil stick. 4 bowls of soil, recorded on …"). We check that the watered one reads "wetter
than the others". If it does not, we say so. We never change a reading.
