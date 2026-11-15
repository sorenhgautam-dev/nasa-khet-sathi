"""The offline copy (owner, 2026-11-15, Part 2): the list of files site/sw.js saves on a first visit, and its version.

    .venv/bin/python scripts/build_offline.py           # rewrite the list in site/sw.js; print what a first visit saves
    .venv/bin/python scripts/build_offline.py --check   # the problems, exit 1 if any (scripts/check_site.py runs it)

A first visit saves the app's own files (everything in site/ outside data/, except sw.js and the world page) and the main
field's files (index.json's first field: every data/<kind>/<id>.* and <id>_*, the pictures its map and drone files name),
plus the shared data files, so every farmer screen works with no signal. Other fields and the world page are saved when
first opened (sw.js). NEVER is never saved: the live reading, the demo-mode switch and the recorded test readings (the
owner: live readings, practice readings and demo-mode data always come fresh). The version is the version stamp
(data/version.json) plus a hash of the listed files, so any change gives a new worker, which replaces the old copy.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "site"
NEVER = ("data/live.json", "data/demo.json", "data/probe_log.json")
LATER = ("js/world.js", "data/basemap/world.json", "data/basemap/world.jpg")
BEGIN, END = "// BEGIN LIST (scripts/build_offline.py writes this block)\n", "// END LIST\n"


def first_visit(site=SITE):
    """(main field id, sorted relative paths a first visit saves). Pure apart from reading site/."""
    site = Path(site)
    main = json.loads((site / "data" / "index.json").read_text())["fields"][0]["id"]
    rel = [p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file() and not p.name.startswith(".")]
    app = [f for f in rel if not f.startswith("data/") and f != "sw.js"]
    shared = [f for f in rel if f.startswith("data/") and f.count("/") == 1 and f.endswith(".json")]
    field = [f for f in rel if f.count("/") == 2 and re.fullmatch(re.escape(main) + r"(_[^/]*)?\.[a-z]+", f.split("/")[2])]
    for j in (f"data/basemap/{main}.json", f"data/drone/{main}.json"):
        img = json.loads((site / j).read_text()).get("image") if (site / j).exists() else None
        field += [img] if img else []
    return main, sorted(set(app + shared + field) - set(NEVER) - set(LATER))


def block(site=SITE):
    site = Path(site)
    _, files = first_visit(site)
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0" + (site / f).read_bytes())
    stamp = json.loads((site / "data" / "version.json").read_text())["commit_short"]
    return (BEGIN + f"const VERSION = 'ks-{stamp}-{h.hexdigest()[:10]}';\n"
            + f"const FIRST_VISIT = {json.dumps(files, indent=1)};\nconst NEVER = {json.dumps(list(NEVER))};\n" + END)


def listed(sw_text):
    m = re.search(r"const FIRST_VISIT = (\[.*?\]);", sw_text, re.S)
    return json.loads(m.group(1)) if m else []


def check(site=SITE):
    """Problems: the list in sw.js is not the site's (stale), names a file the site lacks (missing), or leaves out a file a
    screen loads (not listed: every static path the page, its CSS and scripts name, and every file of the main field)."""
    site = Path(site)
    sw = (site / "sw.js").read_text() if (site / "sw.js").exists() else ""
    have = listed(sw)
    out = [f"missing: sw.js lists {f}, which is not in the site" for f in have if not (site / f).is_file()]
    try:
        if not sw or block(site) not in sw:
            out.append("stale: sw.js's list is not the site's (run scripts/build_offline.py)")
    except (OSError, KeyError, ValueError) as e:
        out.append(f"stale: {e}")
    text = "\n".join((site / f).read_text(errors="ignore") for f in ["index.html", *[p.relative_to(site).as_posix()
                     for p in site.glob("*/*") if p.suffix in (".js", ".css")]] if (site / f).exists())
    named = set(re.findall(r"""['"(]((?:img|fonts|vendor|css|js|data|icons)/[\w./-]+\.\w+)['")]""", text))
    main = first_visit(site)[0] if (site / "data" / "index.json").exists() else None
    named |= {p.relative_to(site).as_posix() for p in (site / "data").glob(f"*/{main}.*")} if main else set()
    for f in sorted(named):
        if (site / f).is_file() and f not in NEVER and f not in LATER and f not in have:
            out.append(f"not listed: {f} is loaded by a screen but not saved for offline use")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        probs = check()
        print("\n".join(probs) or "offline list: OK")
        return 1 if probs else 0
    sw = (SITE / "sw.js").read_text()
    i, j = sw.index(BEGIN), sw.index(END) + len(END)
    (SITE / "sw.js").write_text(sw[:i] + block() + sw[j:])
    main_id, files = first_visit()
    sizes = sorted(((SITE / f).stat().st_size, f) for f in files)
    total = sum(s for s, _ in sizes)
    print(f"a first visit saves {len(files)} files, {total / 1e6:.2f} MB (main field: {main_id}); biggest: "
          + ", ".join(f"{f} {s / 1e3:.0f} KB" for s, f in sizes[::-1][:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
