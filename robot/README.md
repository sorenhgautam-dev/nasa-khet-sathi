# The Khet Sathi soil probe: an open design

This folder holds a hand-held prototype probe that reads soil moisture and temperature at one spot. It is built from
common parts and one short Arduino sketch. Today a person carries it to each part of the field. A robot that carries it
(our mascot, Krishi Scout) is the planned next step, not something we have built.

Everything here is open: the sketch, the laptop code that reads it, and the bench test that checks it. It is cheap
enough for a cooperative to share.

## What it measures, and what it does not

- **Moisture:** a capacitive soil sensor reads the top few centimetres of soil, as far as its blade reaches. That is not
  the whole root zone; crop roots go 0.3 to 1 m deep. Topsoil dries first, so a dry reading can sit above wetter soil.
- **The probe's own scale:** the sketch maps the sensor's raw value to a 0-100 scale, with air = 0 and water = 100.
  That is not "percent water in the soil". Turning it into real soil water needs the bench test below.
- **Temperature:** a waterproof DS18B20 sensor. The sketch cannot tell whether it sits in the soil or in the air, so
  push it into the soil next to the moisture blade.

## Parts

| Part | Job | Pin on the ESP32 |
| --- | --- | --- |
| ESP32 development board | reads both sensors and prints one line every 2 seconds over USB | |
| Capacitive soil moisture sensor (analogue output) | moisture | AOUT to GPIO34 (an ADC1 pin), VCC to 3V3, GND to GND |
| DS18B20 waterproof temperature sensor | temperature | data to GPIO4, VCC to 3V3, GND to GND |
| 4.7 kΩ resistor | pull-up for the DS18B20's data line | between GPIO4 and 3V3 |
| Jumper wires, breadboard | connections | |
| USB cable | power and data to the laptop | |

## Build it

1. Wire it as in the table above. The 4.7 kΩ resistor goes between the DS18B20's data wire and 3.3 V.
2. In the Arduino IDE, install ESP32 board support and the libraries `OneWire` and `DallasTemperature`.
3. Open `firmware/original_probe/original_probe.ino`, our teammate's sketch, kept unchanged byte for byte. Upload it at
   115200 baud.
4. Open the Serial Monitor. Every 2 seconds you should see a line like `Temperature: 23.1 °C  |  Moisture: 45%`.
   - `Check wiring` means the temperature sensor is not found.
   - Moisture stays at 0 in air and near 100 in water.
5. The two numbers `DRY_VALUE` (2467) and `WET_VALUE` (660) in the sketch are its own air and water readings. Another
   board may need its own values. That is the only thing to change in the sketch, and we did not change it.

## Read it on a laptop: settle, then measure

The laptop code in this folder never changes the sketch. It reads the USB lines and decides when a reading can be
trusted (owner's probe brief; rules in `config/rules.yaml` `probe`):

- **Settle, then measure.** Per part, the first 5 good lines (10 s; 20 lines, 40 s, until 15 November) are thrown away while the sensor settles. The next
  5 lines (10 s) are measured. The reading is their median (`robot/settle.py`): 20 s a part.
- **Steady or test again.** If the 10 moisture values spread more than 3 points, the state is `test_again` and no
  number is shown. Temperature has its own steadiness rule (spread at most 0.5 °C).
- **Off the scale.** The sketch clips moisture to 0-100. A median of exactly 0 or 100 is shown as "off the scale",
  never as a value.
- **Walking the field.** Run `.venv/bin/python robot/bridge.py --port <port> --sections s1,s2,s3,s4`, then press Enter
  when the probe is in the next part.
  - The bridge writes `site/data/live.json` once per part, with the final median only.
  - It logs every raw line to `data/probe/<field>/readings_<date>.jsonl`.
  - A pulled cable is reported plainly and marks the live view as stale.
- **Rehearse without the hardware.** `robot/fake_probe.py` prints the same lines: a settling ramp, jumpy readings,
  stuck at 100, wiring lost. Nothing from the fake probe is ever published.

## The bench test: the proof

The bench test turns the probe's 0-100 scale into real soil water and gives its error. The exact steps are in
`CUPS_PROTOCOL.md`. In short:

- six same-size cups;
- the same weight of sun-dried field soil in each;
- weighed water for 0 to 50 % of the cup's volume;
- three push-ins per cup;
- one cup of ice water for the temperature check.

Run `robot/bench.py` per cup, then `scripts/run_probe_bench.py`. It reports four things in
`data/checks/probe/bench.json` (VALIDATION 5.1-5.3):

1. **Steady:** how far repeat readings of one cup spread. Their variance is the probe's error, which sets how much a
   reading moves the field twin (the Kalman update).
2. **In order:** drier cups must read drier, strictly.
3. **Accurate:** a straight line from the probe's scale to the weighed water. Its error is tested leaving one cup out
   each time, so the score never comes from the cups it was fitted on.
4. **Temperature:** ice water should read 0 °C within about 0.5 °C.

**Result: waiting for the team's bench test.** When it is done, this section will state the results in one sentence:
- readings agree within X points;
- drier soil always reads drier;
- against weighed water the probe is off by about Y.

Until then the site shows only "drier / wetter than the other parts", never a water percentage.

## Files

| File | What it does |
| --- | --- |
| `firmware/original_probe/` | the sketch, unchanged |
| `probe.py` | parses the sketch's exact lines; anything else is refused |
| `settle.py` | settle, then measure: median, spread, steady, off the scale (pure functions, tested) |
| `bridge.py` | walks the parts, writes `site/data/live.json`, logs every line |
| `bench.py`, `calibrate.py` | the bench test and the fit from probe scale to soil water |
| `fake_probe.py` | the same lines without hardware, for tests and rehearsal |
| `CUPS_PROTOCOL.md` | the bench-test steps for the team |

What the team records, step by step, and what to send back: `docs/PROBE_RECORDING.md`. The live demo as one command
(web server, bridge and the phone's address): `scripts/demo_probe.py`, with `docs/DEMO_CHECKLIST.md`.
