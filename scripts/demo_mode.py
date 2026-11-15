"""Phone as drone (owner, 2026-11-15): switch the in-person demo mode on or off on this laptop.

    .venv/bin/python scripts/demo_mode.py on     # writes site/data/demo.json (git-ignored), prints how to serve the hotspot
    .venv/bin/python scripts/demo_mode.py off    # removes it

Demo mode shows only when BOTH hold: the page comes from this laptop or its hotspot (a private address, never github.io;
site/js/app.js demoHost) and this switch file exists. The file is git-ignored, so no push can publish it, and
scripts/check_site.py --final refuses it, so the final check reminds you to switch it off."""
import json
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FLAG = REPO / "site" / "data" / "demo.json"


def lan_ip():
    """This laptop's address on the hotspot (no packet is sent: a UDP socket only picks the outgoing interface)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main(argv):
    if argv[:1] not in (["on"], ["off"]):
        print(__doc__)
        return 2
    ignored = subprocess.run(["git", "check-ignore", "-q", str(FLAG.relative_to(REPO))], cwd=REPO).returncode == 0
    if not ignored:
        print("refused: site/data/demo.json is not git-ignored, so it could be published (add it to .gitignore)")
        return 1
    if argv[0] == "off":
        FLAG.unlink(missing_ok=True)
        print("demo mode off (site/data/demo.json removed)")
        return 0
    FLAG.write_text(json.dumps({"demo": True, "what": "phone as drone: the in-person demo on the laptop's hotspot only; "
                                "git-ignored, never published (scripts/demo_mode.py off removes it)"}, indent=1) + "\n")
    ip = lan_ip()
    print("demo mode on (site/data/demo.json, git-ignored)\n"
          "serve with the probe:  .venv/bin/python scripts/demo_probe.py --sections s1,s2,s3,s4   (site/ on port 8000)\n"
          "or without the probe:  .venv/bin/python -m http.server 8000 --bind 0.0.0.0 --directory site\n"
          f"phones: http://{ip}:8000/#/photo  (on the laptop's hotspot; plain http, never the public address)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
