# Live probe demo: checklist

One command runs the demo: `scripts/demo_probe.py`. It starts the web server and the probe bridge together. How to
record is in `docs/PROBE_RECORDING.md`.

## The day before

- [ ] The bench test is done and `config/probe_calibration.yaml` exists (`docs/PROBE_RECORDING.md`, steps 1-2).
      Without it the phone shows only "drier / wetter", with no water % and no "sure".
- [ ] Rehearse once with the fake probe: `.venv/bin/python scripts/demo_probe.py --fake`. Its numbers are made up and
      never published.
- [ ] Charge the laptop and the phone. Pack the probe, its USB cable, a spare cable and the four pots or trays of soil
      if you will not be in the field.
- [ ] iPhone hotspot: Settings, Personal Hotspot, turn on "Maximize Compatibility".
- [ ] We do not use the phone-as-drone demo mode. Leave it off (`site/data/demo.json` must not exist). "From the
      sky" shows Kharipati's open drone map, standing in for our future drone. The probe in the four pots stays
      the live soil test.

## At the venue (5 minutes)

1. [ ] Turn on the phone's hotspot and join it with the laptop.
2. [ ] Plug the probe into the laptop.
3. [ ] Run `.venv/bin/python scripts/demo_probe.py`.
   - It finds the probe's port itself. If it finds none or several, add `--port /dev/cu.usbserial-0001` (Windows:
     `--port COM3`).
   - On macOS, if a box asks "accept incoming connections" for Python, click **Allow**.
4. [ ] On the phone, open the address it prints, `http://<laptop address>:8000/#/soil`. You should see "Let's check the
       soil".
5. [ ] Walk s1, s2, s3, s4.
   - At each part, push the probe in, then press Enter.
   - Hands off for 60 seconds.
   - "Not steady" means press Enter and test that part again.
6. [ ] When you are done, press Ctrl-C. The phone then says the probe is not connected.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| "cable was pulled" | Plug it back in. The bridge tries again every 2 s and starts that part again. |
| The phone cannot open the address | Check both are on the same hotspot. Open `http://localhost:8000/#/soil` on the laptop and show that screen instead. |
| The probe does not work at all | Run the backup, `scripts/demo_probe.py --fake`. The phone shows a big "Practice: made-up numbers" banner (only on the hotspot, never on the public site). **Say it out loud too.** |
| A part keeps saying "not steady" | Push the probe in firmly, wait, and test again. Or type `n` to go on and say so. |

## After

- [ ] Send the files: zip `data/probe/` as `khet_probe_<date>.zip`, with `notes_<date>.txt` (`docs/PROBE_RECORDING.md`,
      step 5).
- [ ] The owner builds the public replay with `scripts/build_probe_log.py`. `site/data/live.json` is git-ignored and is
      never published.
