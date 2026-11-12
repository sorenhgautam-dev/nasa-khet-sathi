"""A fake soil probe for testing the bridge without the hardware. It prints the real probe's lines, in exactly
the same format, every 2 seconds (owner, 2026-11-12):

    Temperature: 23.1 °C  |  Moisture: 45%
    Temperature: Check wiring  |  Moisture: 45%

    .venv/bin/python -m robot.fake_probe --pty          # prints a port path; give it to the bridge's --port
    .venv/bin/python -m robot.fake_probe | .venv/bin/python -m robot.bridge --port - --section s1
    .venv/bin/python -m robot.fake_probe --wiring-every 5 --interval 0.5

Moisture wanders slowly between 0 and 100 %, temperature around 22 C. The numbers are made up: never record
them into site/data/probe_log.json.
"""
import argparse
import os
import random
import sys
import time

LINE = "Temperature: {temp} °C  |  Moisture: {moist}%"
WIRING = "Temperature: Check wiring  |  Moisture: {moist}%"
_KEEP_OPEN = {}                     # master fd -> slave fd, so the pseudo-terminal stays usable


def lines(n=None, seed=0, wiring_every=0, start_moist=45.0, start_temp=22.0):
    """Probe lines without line endings. Every `wiring_every`-th line says 'Check wiring' (0 = never)."""
    rng = random.Random(seed)
    moist, temp, i = start_moist, start_temp, 0
    while n is None or i < n:
        i += 1
        moist = min(100.0, max(0.0, moist + rng.uniform(-1.5, 1.5)))
        temp = min(35.0, max(5.0, temp + rng.uniform(-0.1, 0.1)))
        if wiring_every and i % wiring_every == 0:
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


def serve(fd=None, interval_s=2.0, n=None, seed=0, wiring_every=0):
    """Write lines ending in CR LF (as Arduino's Serial.println does) to `fd`, or to stdout."""
    for line in lines(n=n, seed=seed, wiring_every=wiring_every):
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
    a = ap.parse_args(argv)
    fd = None
    if a.pty:
        fd, path = open_pty()
        print(f"fake probe on {path}\nrun: .venv/bin/python -m robot.bridge --port {path} --section s1", file=sys.stderr)
    try:
        serve(fd=fd, interval_s=a.interval, n=a.n, seed=a.seed, wiring_every=a.wiring_every)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
