# What to record at the real field (for the owner's teammate)

Written 2026-11-14 (Saturday, 01:00) for owner's group 3. The real field replaces the placeholder square. It must be inside
the fetch box: longitude 85.379 to 85.481 E, latitude 27.625 to 27.715 N (about 5 km around Bhaktapur's old city). Inside
that box nothing needs downloading.

Send three small text files and one photo. Copy the templates below exactly. Write "unknown" for anything you don't know.
Never guess a number. Do not write the farmer's name anywhere.

## 0. Ask first

- Ask the farmer whether the field's location and their answers may be shown on a public website, without their name.
  Write the answer in `farmer.yaml` (`consent_public`). If the answer is no, don't send anything.

## 1. `corners.csv`: the four corners

- Stand on each corner. Take the coordinates from your phone's map: long-press on your blue dot in Google Maps, then copy
  the "27.xxxxxx, 85.xxxxxx" numbers.
- Give at least 6 decimals.
- Write down the accuracy the phone shows (for example "± 5 m"), if it shows one.
- Go round the field in order: south-west first, then south-east, north-east, north-west.
- Also pace each side (one pace is about 0.75 m). We use this to check the GPS.

```csv
corner,lat,lon,gps_accuracy_m,side_to_next_corner_paces
SW,27.xxxxxx,85.xxxxxx,5,80
SE,27.xxxxxx,85.xxxxxx,5,78
NE,27.xxxxxx,85.xxxxxx,4,81
NW,27.xxxxxx,85.xxxxxx,5,79
```

If the field is not a four-sided shape, add a row for every corner in order round the field (name them C1, C2, ...).

## 2. The photo from above

- One JPG of the whole field from above (a roof, a hill or a drone), with all four corners visible.
- Send the original file. We crop and shrink it for the website.
- In `farmer.yaml` write:
  - the date and time it was taken;
  - where it was taken from;
  - which way is north in the photo;
  - which corner is which.

## 3. `farmer.yaml`: the farmer's answers

```yaml
consent_public: yes            # yes / no: location and answers may be shown on a public website, without a name
date_of_visit: 2026-11-14
photo:
  taken: 2026-11-14 10:30
  from: "roof of the house to the west, about 6 m up"   # or "drone, about 40 m up"
  north_in_photo: up           # up / down / left / right
  corners_in_photo: "SW bottom-left, SE bottom-right, NE top-right, NW top-left"
crops:                         # every crop through one normal year, in order. Nepali month names are fine
  - crop: rice
    sown_or_transplanted: "Asar 15 (about 30 June)"   # say "seedbed" and "transplanted" separately if both are known
    harvested: "Kartik 10 (about 27 October)"
  - crop: potato
    sown_or_transplanted: "Mangsir 1"
    harvested: "Magh 20"
  - crop: "nothing (empty)"
    from: "Falgun"
    to: "Asar"
same_every_year: yes           # yes / no. If no, write the other years' crops below, with the years
other_years: ""
watering:
  source: rain only            # rain only / canal / well or pump / river / other
  which_crops: ""              # e.g. "potato only"
  how_often: ""                # e.g. "every 10 days in winter"
  enough_water: ""             # yes / sometimes / no
# ASK THE NEXT TWO QUESTIONS FIRST, BEFORE THE FARMER SEES THE APP (owner, 2026-11-14), so the app cannot shape the answer.
# Ask for the three worst and the three best years since about 2001 (2058 BS), with the crop and why.
bad_years:                     # the three worst years, in Bikram Sambat or AD (say which), and why
  - year: "2079 BS"
    crop: rice
    what_happened: "rain came late, transplanted late"   # drought / flood / hail / frost / pests / late rain / other
    how_bad: "about half"      # their own words: "half", "a little less", "nothing"
good_years:                    # the three best years, and why
  - year: "2080 BS"
    crop: potato
    why: "good rain in winter"
normal_harvest: ""             # optional, in their own unit (muri, kg). Not shown on the site; only for comparing years
soil:
  feels: ""                    # sandy / loamy / sticky clay
  water_stands_after_rain: ""  # never / sometimes / often
  jar_test: ""                 # optional: see section 5
notes: ""
```

The three worst and three best years matter most: they are our first real ground truth for the twin. Ask them before showing the app.

## 4. `probe_spots.csv`: probe readings in four spots

The field is split into four parts:
- s1 is the south-west quarter;
- s2 is the south-east quarter;
- s3 is the north-west quarter;
- s4 is the north-east quarter.

Read one spot near the middle of each quarter.

**With the laptop:**
```
.venv/bin/python robot/bridge.py --port <port> --sections s1,s2,s3,s4
```
Press Enter when the probe is in the next part. The bridge waits for the probe to settle, measures, and logs everything by
itself. Then send the file `data/probe/demo/readings_<date>.jsonl`.

**Without the laptop:** use the Arduino Serial Monitor.
- Push the probe in fully.
- Wait 1 minute, then copy the next 20 seconds of lines (about 10 lines).
- Fill in one row per spot, pasting the lines into one text file per spot (s1.txt ... s4.txt).

```csv
section,time,depth_cm,raw_lines_file,last_rain,watered_in_last_3_days,notes
s1,2026-11-14 10:40,10,s1.txt,"2 days ago, light",no,""
s2,2026-11-14 10:43,10,s2.txt,"2 days ago, light",no,""
s3,2026-11-14 10:46,10,s3.txt,"2 days ago, light",no,""
s4,2026-11-14 10:49,10,s4.txt,"2 days ago, light",no,""
```

## 5. Optional, if there is time: a jar test for texture (owner's 4d)

This helps the soil numbers.
- Fill a straight glass jar one third with soil from the field (no stones or roots).
- Add water to two thirds, plus a pinch of washing powder, and shake for 3 minutes.
- Put it down. Mark the height of the settled layer after 1 minute (sand), after 2 hours (silt), and after 2 days (clay
  on top).
- Write the three heights in cm in `farmer.yaml` `soil.jar_test`, and send a photo of the jar.

## What we do with it

- **The field:** the corners replace the placeholder square (config/fields/demo.yaml). The four parts are rebuilt from
  the real outline, and the whole pipeline reruns.
- **The farmer's answers:** they set the current crops and dates, and the water source.
- **Comparison:** the satellite's seasons and the twin's good and bad years are compared with the farmer's answers.
  Agreements and disagreements alike go in VALIDATION.md.
- **Probe readings:** they go into `site/data/probe_log.json`.
- **Labels:** PLACEHOLDER labels that no longer apply come off. Ones that still apply stay, for example the soil from
  the nearest SoilGrids cell.
