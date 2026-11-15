"""One command before the final push (owner's launch brief, 2026-11-14), and one after the deploy.

    .venv/bin/python scripts/final_check.py                                  # before the push: stamp, then every check
    .venv/bin/python scripts/final_check.py --live https://<live address>    # after the deploy: every check, no new
                                                                             # stamp, and the live files byte for byte
    .venv/bin/python scripts/final_check.py --live https://<address> --live-only    # only the live comparison

Steps, each PASS or FAIL, then one RESULT line (exit 0 only if every step passed):
  1. version stamp   site/data/version.json: the commit the files are checked at, its date, today, and whether other
                     files had changes not yet committed (pipeline/export/version_schema.json; for the How-we-know page).
                     Written first, so the checks below cover it; rewritten only when its content changes. Not with --live:
                     the live copy must be the one that was pushed. The stamp names the commit it was made at; commit the
                     stamp after it (the published commit is then the next one).
     offline list    scripts/build_offline.py, right after the stamp: site/sw.js's version is named from it (commit
                     site/sw.js with the stamp).
  2. tests          the full suite (python -m pytest -q), judged by its exit code; FAILED / ERROR lines are shown
  3. validate        python -m pipeline.export.validate --final
  4. static site     scripts/check_site.py --final
  5. no outside      no file in site/ makes the browser fetch anything from another address at runtime (fonts, map
     requests       tiles, scripts, styles, images, fetch, WebSocket, ...); links a person taps are not requests
  6. secrets         scripts/scan_history.py (every commit and the working tree)
  7. live site       with --live: every file the site publishes (everything under site/ except live.json and hidden
                     files) is downloaded from the live address and compared byte for byte with the checked local file
Git is only read (rev-parse, log, status). Nothing is committed or pushed.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[1]
STAMP = Path("site") / "data" / "version.json"
INNER = "KHET_FINAL_CHECK"                     # set for the test run, so final_check never runs inside its own tests
SKIP_NAMES = {"live.json", ".DS_Store"}        # live.json is git-ignored: it exists during the in-person demo only
ALLOWED_OUTSIDE = ()                           # owner's launch brief: none (a Firebase live probe, step 10b, would be the owner's call)

_U = r"""[`'"]?(?:https?:)?//"""               # an address on another site (http, https or protocol-relative)
_Q = r"""[`'"](?:https?:)?//"""
OUTSIDE = [
    ("tag", re.compile(r"<(?:script|img|iframe|source|audio|video|embed|link|image|use|track|object)\b[^>]*?"
                       r"\b(?:src|href|xlink:href|data|srcset|poster)\s*=\s*" + _U, re.I)),
    ("stylesheet or font link (js)", re.compile(r"""['"]link['"][^)]*?\bhref\s*:\s*""" + _Q)),
    ("src", re.compile(r"\bsrc(?:set)?\s*[:=]\s*" + _Q)),
    ("fetch", re.compile(r"\bfetch\(\s*" + _Q)),
    ("map layer", re.compile(r"\b(?:tileLayer|imageOverlay|videoOverlay|wms)\(\s*" + _Q)),
    ("connection", re.compile(r"\bnew\s+(?:WebSocket|EventSource|Worker|SharedWorker)\(\s*[`'\"](?:wss?:|https?:)?//")),
    ("request", re.compile(r"\.open\(\s*[`'\"][A-Za-z]+[`'\"]\s*,\s*" + _Q)),
    ("request", re.compile(r"\b(?:importScripts|sendBeacon)\(\s*" + _Q)),
    ("module", re.compile(r"(?:\bimport\s*\(\s*|\bfrom\s+)" + _Q)),
    ("css import", re.compile(r"@import\s+(?:url\(\s*)?" + _U, re.I)),
    ("css url", re.compile(r"\burl\(\s*" + _U, re.I)),
]
CODE = {".html", ".htm", ".js", ".mjs", ".css", ".svg"}


# ---------- the checks ----------

def run(cmd, cwd, env=None):
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env, capture_output=True, text=True, errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def git_stamp(runner, repo, today):
    """The version stamp: HEAD, its committer date, today, and whether files other than the stamp are not committed."""
    code, head = runner(["git", "rev-parse", "HEAD"], repo)
    if code != 0:
        raise RuntimeError(f"git rev-parse HEAD failed: {head.strip()}")
    _, cdate = runner(["git", "log", "-1", "--format=%cs", "HEAD"], repo)
    _, status = runner(["git", "status", "--porcelain"], repo)
    others = [ln for ln in status.splitlines() if ln.strip() and ln[3:].strip() != STAMP.as_posix()]
    head = head.strip()
    return {"commit": head, "commit_short": head[:7], "commit_date": cdate.strip(), "checked_on": today,
            "uncommitted_changes": bool(others), "made_by": "scripts/final_check.py"}


def write_stamp(path, doc):
    """Write the stamp; False (and nothing written) when the file already says exactly this."""
    path = Path(path)
    text = json.dumps(doc, indent=1) + "\n"
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
    return True


def outside_requests(site_dir):
    """[{file, line, kind, text}]: code in site/ that makes the browser fetch from another address at runtime."""
    site_dir, hits = Path(site_dir), []
    for f in sorted(p for p in site_dir.rglob("*") if p.is_file() and p.suffix in CODE):
        name = f.relative_to(site_dir).as_posix()
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            for kind, rx in OUTSIDE:
                m = rx.search(line)
                if m and not any(a in line[m.start():] for a in ALLOWED_OUTSIDE):
                    hits.append({"file": name, "line": i, "kind": kind, "text": line.strip()[:140]})
                    break
    return hits


def site_files(site_dir):
    """Every file the site publishes: all of site/, without hidden files and live.json."""
    site_dir = Path(site_dir)
    return sorted(p.relative_to(site_dir).as_posix() for p in site_dir.rglob("*")
                  if p.is_file() and p.name not in SKIP_NAMES and not any(part.startswith(".") for part in p.relative_to(site_dir).parts))


def _get(url):
    import requests
    r = requests.get(url, timeout=60, headers={"User-Agent": "khet-sathi-final-check", "Cache-Control": "no-cache",
                                                "Accept-Encoding": "gzip"})
    return r.status_code, r.content


def compare_live(base_url, site_dir, get=_get):
    """{same, differs, missing, errors}: each published file fetched from base_url and compared byte for byte."""
    base = base_url.rstrip("/") + "/"
    out = {"same": [], "differs": [], "missing": [], "errors": []}
    for rel in site_files(site_dir):
        try:
            status, body = get(base + quote(rel))
        except Exception as e:                          # a network error is a failure of this file, named
            out["errors"].append(f"{rel}: {e}")
            continue
        if status == 404:
            out["missing"].append(rel)
        elif status != 200:
            out["errors"].append(f"{rel}: HTTP {status}")
        elif body == (Path(site_dir) / rel).read_bytes():
            out["same"].append(rel)
        else:
            out["differs"].append(rel)
    return out


def _tail(text, pattern=r"^(FAILED|ERROR|FAIL)\b", n=15):
    lines = [ln for ln in text.splitlines() if re.match(pattern, ln)]
    return (lines or text.strip().splitlines()[-n:])[:n]


# ---------- the command ----------

def main(argv=None, runner=run, repo=REPO, today=None, get=_get):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", metavar="URL", help="the live address: compare every published file with the local one")
    ap.add_argument("--live-only", action="store_true", help="with --live: only the live comparison")
    a = ap.parse_args(argv)
    if a.live_only and not a.live:
        ap.error("--live-only needs --live <address>")
    repo, today = Path(repo), today or date.today().isoformat()
    py = sys.executable
    steps = []                                          # (name, ok or None for skipped, detail lines)

    def cmd_step(name, cmd, env=None):
        code, out = runner(cmd, repo, env) if env is not None else runner(cmd, repo)
        steps.append((name, code == 0, [] if code == 0 else _tail(out)))

    if not a.live_only:
        if a.live:
            steps.append(("version stamp", None, ["not written with --live: the live copy must be the one pushed"]))
        else:
            try:
                doc = git_stamp(runner, repo, today)
                changed = write_stamp(repo / STAMP, doc)
                steps.append(("version stamp", True, [f"{STAMP} = {doc['commit_short']} ({doc['commit_date']}), checked "
                                                      f"{today}{', other files not committed yet' if doc['uncommitted_changes'] else ''}"
                                                      f"{'' if changed else ' (unchanged)'}"]))
            except (RuntimeError, OSError) as e:
                steps.append(("version stamp", False, [str(e)]))
            # the offline copy's version is named from the stamp (site/sw.js; 2026-11-15): rebuilt after it, before the checks
            cmd_step("offline list (build_offline)", [py, "scripts/build_offline.py"])
        if os.environ.get(INNER):
            steps.append(("tests", False, ["not run: already inside final_check's own test run"]))
        else:
            cmd_step("tests (full suite)", [py, "-m", "pytest", "-q"], env={**os.environ, INNER: "1"})
        cmd_step("validate --final", [py, "-m", "pipeline.export.validate", "--final"])
        cmd_step("static site (check_site --final)", [py, "scripts/check_site.py", "--final"])
        hits = outside_requests(repo / "site")
        steps.append(("no outside requests at runtime", not hits,
                      [f"{h['file']}:{h['line']} [{h['kind']}] {h['text']}" for h in hits]))
        cmd_step("secrets (scan_history)", [py, "scripts/scan_history.py"])
    if a.live:
        res = compare_live(a.live, repo / "site", get)
        bad = [f"differs: {x}" for x in res["differs"]] + [f"missing on the live site: {x}" for x in res["missing"]] \
            + [f"error: {x}" for x in res["errors"]]
        steps.append((f"live site = local files ({len(res['same'])} same)", not bad, bad[:40]))
    else:
        steps.append(("live site", None, ["after the deploy: final_check.py --live <address>"]))

    print("FINAL CHECK")
    for name, ok, detail in steps:
        print(f"  {'SKIP' if ok is None else 'PASS' if ok else 'FAIL'}  {name}")
        for d in detail if ok is not True or name == "version stamp" else []:
            print(f"        {d}")
    failed = [n for n, ok, _ in steps if ok is False]
    ran = [n for n, ok, _ in steps if ok is not None]
    if failed:
        print(f"RESULT: FAIL ({len(failed)} of {len(ran)} checks failed: {', '.join(failed)}). Do not push.")
        return 1
    print(f"RESULT: PASS ({len(ran)} checks).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
