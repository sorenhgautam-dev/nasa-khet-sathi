"""A fake soil probe for testing the bridge without the hardware. It prints the real probe's lines, in exactly
the same format, every 2 seconds (owner, 2026-11-12):

    Temperature: 23.1 °C  |  Moisture: 45%
    Temperature: Check wiring  |  Moisture: 45%

    .venv/bin/python -m robot.fake_probe --pty          # prints a port path; give it to the bridge's --port
    .venv/bin/python -m robot.fake_probe | .venv/bin/python -m robot.bridge --port - --section s1
    .venv/bin/python -m robot.fake_probe --wiring-every 5 --interval 0.5

Scenarios (owner's probe brief, 2026-11-14, fix 5), each a test case for the settle logic (robot/settle.py):
    wander       moisture wanders slowly, temperature around 22 C (the default)
    settling     a settling ramp: from air (0 %) towards --target, and from --start-temp to the soil's --soil-temp
    jumpy        readings jump about --target by up to 5 points each line (never steady)
    stuck100     moisture stuck at 100 % (off the scale)
    wiring_lost  like settling, but the temperature sensor is lost after 5 lines ("Check wiring")

    .venv/bin/python -m robot.fake_probe --pty --scenario settling --target 38

The numbers are made up: never record them into site/data/ (the bridge and scripts/build_probe_log.py refuse them).
"""
import math
import argparse
import os
import random
import sys
import time

LINE = "Temperature: {temp} °C  |  Moisture: {moist}%"
WIRING = "Temperature: Check wiring  |  Moisture: {moist}%"
_KEEP_OPEN = {}                     # master fd -> slave fd, so the pseudo-terminal stays usable


SCENARIOS = ("wander", "settling", "jumpy", "stuck100", "wiring_lost")
SETTLE_TAU_LINES, TEMP_TAU_LINES, WIRING_AFTER = 4.0, 6.0, 5


def lines(n=None, seed=0, wiring_every=0, start_moist=45.0, start_temp=22.0, scenario="wander", target=45.0,
          soil_temp=18.0):
    """Probe lines without line endings. Every `wiring_every`-th line says 'Check wiring' (0 = never)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    rng = random.Random(seed)
    moist, temp, i = start_moist, start_temp, 0
    while n is None or i < n:
        i += 1
        if scenario == "wander":
            moist = moist + rng.uniform(-1.5, 1.5)
            temp = min(35.0, max(5.0, temp + rng.uniform(-0.1, 0.1)))
        elif scenario in ("settling", "wiring_lost"):
            moist = target * (1 - math.exp(-i / SETTLE_TAU_LINES)) + rng.uniform(-0.4, 0.4)
            temp = soil_temp + (start_temp - soil_temp) * math.exp(-i / TEMP_TAU_LINES) + rng.uniform(-0.03, 0.03)
        elif scenario == "jumpy":
            moist, temp = target + rng.uniform(-5.0, 5.0), soil_temp + rng.uniform(-0.05, 0.05)
        else:                                                   # stuck100
            moist, temp = 100.0, soil_temp
        moist = min(100.0, max(0.0, moist))
        lost = scenario == "wiring_lost" and i > WIRING_AFTER
        if lost or (wiring_every and i % wiring_every == 0):
            yield WIRING.format(moist=int(round(moist)))
        else:
            yield LINE.format(temp=f"{temp:.1f}", moist=int(round(moist)))


def open_pty():
    """(master fd, slave path): a pseudo-terminal the bridge can open like a USB serial port."""
    import tty
    master, slave = os.openpty()
    tty.setraw(slave)               # no echo or line editing, like a real serial link
    _KEEP_OPEN[master] = slave
    return master, os.ttyname(slave)


def serve(fd=None, interval_s=2.0, n=None, seed=0, wiring_every=0, **kw):
    """Write lines ending in CR LF (as Arduino's Serial.println does) to `fd`, or to stdout."""
    for line in lines(n=n, seed=seed, wiring_every=wiring_every, **kw):
        data = (line + "\r\n").encode("utf-8")
        try:
            if fd is None:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            else:
                os.write(fd, data)
        except (OSError, BrokenPipeError):
            return                  # the reader went away
        time.sleep(interval_s)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between lines (the probe: 2)")
    ap.add_argument("--n", type=int, default=None, help="stop after this many lines (default: run until Ctrl-C)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--wiring-every", type=int, default=0, help="every N-th line says 'Check wiring' (0 = never)")
    ap.add_argument("--pty", action="store_true", help="serve on a pseudo-terminal and print its path")
    ap.add_argument("--scenario", default="wander", choices=SCENARIOS)
    ap.add_argument("--target", type=float, default=45.0, help="the moisture a settling or jumpy probe heads for")
    ap.add_argument("--start-temp", type=float, default=22.0)
    ap.add_argument("--soil-temp", type=float, default=18.0)
    a = ap.parse_args(argv)
    fd = None
    if a.pty:
        fd, path = open_pty()
        print(f"fake probe on {path}\nrun: .venv/bin/python -m robot.bridge --port {path} --section s1", file=sys.stderr)
    try:
        serve(fd=fd, interval_s=a.interval, n=a.n, seed=a.seed, wiring_every=a.wiring_every, scenario=a.scenario,
              target=a.target, start_temp=a.start_temp, soil_temp=a.soil_temp)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
