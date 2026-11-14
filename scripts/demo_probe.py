"""The live probe demo as one command (owner's launch brief, 2026-11-14; docs/DEMO_CHECKLIST.md).

    .venv/bin/python scripts/demo_probe.py                                   # the real probe (finds its USB port)
    .venv/bin/python scripts/demo_probe.py --port /dev/cu.usbserial-0001     # the real probe on this port (Windows: COM3)
    .venv/bin/python scripts/demo_probe.py --fake                            # the backup: the fake probe (rehearsal)

It starts a small web server for site/ on this laptop (port 8000) and robot/bridge.py, and prints the address a phone on
the same hotspot opens (the laptop's own address on that network). The bridge asks for Enter at each part, as always.
Ctrl-C stops both; the bridge marks live.json stale first.

- The real probe: the bridge writes site/data/live.json (git-ignored; it exists during the demo only) and logs every
  line to data/probe/<field>/readings_<date>.jsonl, the file the public replay is built from (scripts/build_probe_log.py).
- --fake: robot/fake_probe.py's made-up lines. They never enter site/data/ or data/probe/<field>/ (the bridge refuses):
  live.json and the log go to a rehearsal folder, and the server answers data/live.json from there. The phone shows them
  under a big "Practice: made-up numbers" banner, and only because it opens this laptop's own address on the hotspot
  (rules.yaml probe.live.practice_on_phone); the public site never shows them, and nothing made-up can be published.
Every answer carries Cache-Control: no-store, so the phone never shows an old reading.
"""
import argparse
import ipaddress
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
SITE_DATA = SITE / "data"
FAKE_SCENARIOS = ("settling", "wander", "jumpy", "stuck100", "wiring_lost")      # robot/fake_probe.py SCENARIOS


def pick_addresses(candidates):
    """The private IPv4 addresses a phone on the same network can reach, in order, without repeats."""
    out = []
    for a in candidates:
        try:
            ip = ipaddress.ip_address(a)
        except ValueError:
            continue
        if ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_link_local and a not in out:
            out.append(a)
    return out


def lan_addresses():
    """This laptop's addresses on its networks. A UDP connect only picks a route; no packet is sent."""
    found = []
    for target in ("10.255.255.255", "192.168.255.255", "172.31.255.255"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((target, 1))
                found.append(s.getsockname()[0])
        except OSError:
            pass
    try:
        found += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass
    return pick_addresses(found)


def find_ports():
    """USB serial ports that may be the probe (pyserial's list)."""
    from serial.tools import list_ports
    return [p.device for p in list_ports.comports()
            if any(k in f"{p.device} {p.description} {p.hwid}".lower() for k in ("usb", "cp210", "ch34", "slab", "wch"))]


def bridge_command(port, fake, field, sections, live, log_dir, fake_interval=0.5, no_wait=False, python=sys.executable):
    """The robot/bridge.py command line. A fake probe may never write into site/data/."""
    live = Path(live)
    if fake and (live.resolve() == SITE_DATA.resolve() or SITE_DATA.resolve() in live.resolve().parents):
        raise ValueError("the fake probe's live.json may not go into site/data/: made-up numbers never reach the site")
    cmd = [str(python), "-m", "robot.bridge", "--field", field, "--out", str(live)]
    cmd += ["--fake", fake, "--fake-interval", f"{fake_interval:g}"] if fake else ["--port", str(port)]
    if sections:
        cmd += ["--sections", sections]
    if log_dir is not None:
        cmd += ["--log-dir", str(log_dir)]
    if no_wait:
        cmd += ["--no-wait"]
    return cmd


def make_server(site_dir, live_path, host="0.0.0.0", port=8000):
    """A static server for site/ whose data/live.json is the bridge's file; nothing is cached on the phone."""
    live_path = Path(live_path)

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if urllib.parse.urlsplit(path).path == "/data/live.json":
                return str(live_path)
            return super().translate_path(path)

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *args):          # keep the terminal for the bridge's prompts
            pass

    return ThreadingHTTPServer((host, port), partial(Handler, directory=str(site_dir)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="the probe's serial port (default: the one USB serial port found)")
    ap.add_argument("--fake", nargs="?", const="settling", choices=FAKE_SCENARIOS,
                    help="the backup: the fake probe (default scenario: settling); nothing it says is published")
    ap.add_argument("--field", default="demo")
    ap.add_argument("--sections", default=None, help="parts to walk, e.g. s1,s2,s3,s4 (default: all of the field's)")
    ap.add_argument("--http-port", type=int, default=8000, help="the web server's port (default 8000)")
    ap.add_argument("--bind", default="0.0.0.0", help="the address the server listens on (default: every network)")
    ap.add_argument("--fake-interval", type=float, default=0.5, help="seconds between fake lines (the real probe: 2)")
    ap.add_argument("--no-wait", action="store_true", help="do not wait for Enter at each part (rehearsal)")
    ap.add_argument("--rehearsal-dir", default=None, help="with --fake: where live.json and the log go (default: a new temp folder)")
    a = ap.parse_args(argv)

    if a.fake:
        rdir = Path(a.rehearsal_dir or tempfile.mkdtemp(prefix="khet-rehearsal-"))
        live, log_dir, port = rdir / "live.json", rdir / "logs", None
    else:
        port = a.port
        if not port:
            ports = find_ports()
            if len(ports) != 1:
                print("Plug the probe in and give its port with --port. USB serial ports found: "
                      + (", ".join(ports) or "none") + ". (Or run the backup: --fake)", file=sys.stderr)
                return 2
            port = ports[0]
        live, log_dir = SITE_DATA / "live.json", None
    cmd = bridge_command(port, a.fake, a.field, a.sections, live, log_dir, a.fake_interval, a.no_wait)
    srv = make_server(SITE, live, host=a.bind, port=a.http_port)
    http_port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    addrs = lan_addresses()
    print("=" * 64)
    print("KHET SATHI LIVE PROBE DEMO" + ("   ** REHEARSAL with the FAKE probe: made-up numbers, never published **"
                                          if a.fake else f"   (the real probe on {port})"))
    for ip in addrs:
        print(f"  On the phone (same hotspot):  http://{ip}:{http_port}/#/soil")
    if not addrs:
        print("  No network address found: join the phone's hotspot, then run this again.")
    print(f"  On this laptop:               http://localhost:{http_port}/#/soil")
    print(f"  live.json: {live}" + ("" if a.fake else "   (log: data/probe/" + a.field + "/)"))
    print("  Stop: Ctrl-C (the site then says the probe is not connected).")
    print("=" * 64, flush=True)

    proc = subprocess.Popen(cmd, cwd=str(REPO))
    try:
        code = proc.wait()
    except KeyboardInterrupt:
        try:
            code = proc.wait(timeout=10)                # the bridge got Ctrl-C too: it marks live.json stale and stops
        except subprocess.TimeoutExpired:
            proc.terminate()
            code = proc.wait()
    finally:
        srv.shutdown()
        srv.server_close()
    print(f"Demo stopped (bridge exit {code}).")
    return code


if __name__ == "__main__":
    sys.exit(main())
