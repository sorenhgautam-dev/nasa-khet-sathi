"""The site must stay fully static and work from any address (owner, 2026-11-14 night: hosted on GitHub Pages from this
repository, `.github/workflows/pages.yml` publishing `site/`; no build step, no server functions, no environment variables;
every fetch relative). The api/, middleware, package.json and vercel.json checks keep it plain on any static host.

    .venv/bin/python scripts/check_site.py            # exit 1 on any problem
    .venv/bin/python scripts/check_site.py --final    # the freeze check: also wants site/index.html

What it refuses in site/:
- a path that starts at the domain root (`fetch('/data/...')`, `src="/js/app.js"`, `url(/img/x.svg)`): write
  `data/...`, `js/app.js`, `../img/x.svg`. Relative paths work at the site's root and in any folder; full addresses
  of other sites (`https://...`) are not touched by this rule;
- reading an environment variable (`process.env`, `import.meta.env`): there is none on a static site;
- with --final, the demo switch site/data/demo.json (phone as drone: the laptop's hotspot only; git-ignored);
- calling a server function (`fetch('api/...')`), or files that would make Vercel run code or a build: an `api/`
  folder, `middleware.*`, `package.json`, `.env*`, files that need compiling (.ts, .tsx, .jsx, .vue, .svelte, .scss),
  or a `vercel.json` that sets functions, env, crons, builds or a build or install command.
The JSON under site/data/ is data and is not searched for code paths; the four feature folders (replay, pulse, checkup,
labels; 2026-11-14) are searched for links: any text that starts at the domain root ('/...') or names another site
('https://...') is refused, so their files point only at other files of the site, relatively.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE_EXT = {".html", ".htm", ".js", ".mjs", ".css", ".svg"}
NEEDS_BUILD = {".ts", ".tsx", ".jsx", ".vue", ".svelte", ".scss", ".sass", ".less"}
Q = r"""["'`]"""
RULES = [
    ("absolute path", re.compile(r"fetch\(\s*" + Q + r"/(?!/)")),
    ("absolute path", re.compile(r"\.open\(\s*" + Q + r"[A-Za-z]+" + Q + r"\s*,\s*" + Q + r"/(?!/)")),
    ("absolute path", re.compile(r"new\s+URL\(\s*" + Q + r"/(?!/)")),
    ("absolute path", re.compile(r"(?:\bfrom|\bimport)\s*\(?\s*" + Q + r"/(?!/)")),
    ("absolute path", re.compile(r"""\b(?:src|href|action|poster|srcset|data-src)\s*=\s*["']/(?!/)""")),
    ("absolute path", re.compile(r"""url\(\s*["']?/(?!/)""")),
    ("absolute path", re.compile(r"serviceWorker\.register\(\s*" + Q + r"/(?!/)")),
    ("environment variable", re.compile(r"process\.env\b|import\.meta\.env\b")),
    ("server function", re.compile(Q + r"(?:\./|/)?api/")),
]
VERCEL_JSON_OK = {"$schema", "cleanUrls", "trailingSlash", "headers", "framework", "buildCommand", "installCommand",
                  "outputDirectory", "public", "github"}


def text_problems(name, text):
    """[{file, line, kind, text}] for one HTML, JS, CSS or SVG file."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for kind, rx in RULES:
            if rx.search(line):
                out.append({"file": name, "line": i, "kind": kind, "text": line.strip()[:120]})
                break
    return out


def _vercel_json_problems(name, text):
    try:
        doc = json.loads(text)
    except ValueError:
        return [{"file": name, "line": 1, "kind": "vercel.json", "text": "not valid JSON"}]
    bad = sorted(k for k in doc if k not in VERCEL_JSON_OK)
    bad += [k for k in ("buildCommand", "installCommand", "framework") if doc.get(k)]
    return [{"file": name, "line": 1, "kind": "vercel.json",
             "text": f"sets {bad}: the site has no functions, no environment variables and no build step"}] if bad else []


FEATURE_DIRS = ("replay", "pulse", "checkup", "labels", "simple", "rainrisk", "fertiliser", "heatclock")   # last three: build_risks.py


def data_link_problems(name, doc):
    """[{file, line, kind, text}] for every string in a feature file that is an absolute path or another site's address."""
    out, stack = [], [doc]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            stack += list(x.values())
        elif isinstance(x, list):
            stack += x
        elif isinstance(x, str) and (x.startswith("/") or "://" in x):
            out.append({"file": name, "line": 0, "kind": "data link", "text": f"{x[:100]!r}: only relative links to the site's own files"})
    return out


def site_problems(site_dir=REPO / "site", final=False):
    site_dir = Path(site_dir)
    out = []
    for f in sorted(p for p in site_dir.rglob("*") if p.is_file()):
        name = f.relative_to(site_dir).as_posix()
        parts = name.split("/")
        if parts[0] == "api":
            out.append({"file": name, "line": 0, "kind": "server function", "text": "Vercel runs files under api/ as functions"})
        elif len(parts) == 1 and f.stem == "middleware":
            out.append({"file": name, "line": 0, "kind": "server function", "text": "Vercel runs middleware as a function"})
        elif f.name == "package.json":
            out.append({"file": name, "line": 0, "kind": "build step", "text": "package.json makes Vercel install and build; the site is plain files"})
        elif f.name.startswith(".env"):
            out.append({"file": name, "line": 0, "kind": "environment variable", "text": "no environment file belongs in the site"})
        elif f.suffix in NEEDS_BUILD:
            out.append({"file": name, "line": 0, "kind": "build step", "text": f"{f.suffix} files need compiling; the site has no build step"})
        elif name == "vercel.json":
            out += _vercel_json_problems(name, f.read_text(errors="replace"))
        elif f.suffix in CODE_EXT:
            out += text_problems(name, f.read_text(errors="replace"))
        elif f.suffix == ".json" and len(parts) == 3 and parts[0] == "data" and parts[1] in FEATURE_DIRS:
            out += data_link_problems(name, json.loads(f.read_text()))
    if final and (site_dir / "data" / "demo.json").is_file():   # phone as drone: the hotspot-only demo switch (scripts/demo_mode.py)
        out.append({"file": "data/demo.json", "line": 0, "kind": "demo switch",
                    "text": "demo mode is for the laptop's hotspot only: run scripts/demo_mode.py off before the final commit"})
    if final and not (site_dir / "index.html").is_file():
        out.append({"file": "index.html", "line": 0, "kind": "missing", "text": "site/index.html is the page the live address opens"})
    return out


def main(argv=None):
    argv = list(argv or [])
    final = "--final" in argv
    dirs = [a for a in argv if not a.startswith("--")]
    site = Path(dirs[0]) if dirs else REPO / "site"
    problems = site_problems(site, final=final)
    for p in problems:
        print(f"FAIL {p['file']}:{p['line']} [{p['kind']}] {p['text']}")
    files = sum(1 for p in site.rglob("*") if p.is_file())
    print(f"{files} file(s) in {site} checked, {len(problems)} problem(s)")
    if not final and (site / "data" / "demo.json").is_file():
        print("NOTE: demo mode is on (site/data/demo.json, git-ignored; hotspot only). scripts/demo_mode.py off turns it off")
    if not final and not (site / "index.html").is_file():
        print("NOTE: no index.html at the root of site/ yet (--final makes this a failure)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
