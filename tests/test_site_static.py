"""The site is hosted on GitHub Pages from this repository as plain files (owner, 2026-11-14 night; .github/workflows/
pages.yml publishes site/): no build step, no server functions, no environment variables, and every path relative, so it
works in the site's /data-test-game/ folder.
scripts/check_site.py is the guard; these tests build throwaway site folders in tmp_path."""
from pathlib import Path

import pytest

from scripts import check_site as cs

REPO = Path(__file__).resolve().parents[1]


def _site(tmp_path, files):
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


GOOD = {
    "index.html": '<!doctype html><link rel="stylesheet" href="css/app.css"><script type="module" src="js/app.js"></script>'
                  '<a href="https://www.nasa.gov/">NASA</a><img src="img/field.svg"><a href="#plans">plans</a>',
    "js/app.js": "import { draw } from './draw.js';\nconst r = await fetch('data/index.json');\n"
                 "const f = await fetch(`data/fields/${id}.json`);\nconst w = await fetch(\"./data/words.json\");\n"
                 "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png');\n",
    "js/draw.js": "export function draw() {}\n",
    "css/app.css": "body { background: url(../img/bg.svg); }\n",
    "img/field.svg": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
    "data/index.json": '{"fields": [{"note": "a /slash in data is not a path"}]}',
}


def test_a_plain_static_site_with_relative_paths_passes(tmp_path):
    assert cs.site_problems(_site(tmp_path, GOOD), final=True) == []


@pytest.mark.parametrize("name, text, kind", [
    ("js/app.js", "fetch('/data/index.json')", "absolute path"),
    ("js/app.js", 'const r = await fetch("/data/fields/demo.json");', "absolute path"),
    ("js/app.js", "fetch(`/data/fields/${id}.json`)", "absolute path"),
    ("js/app.js", "import x from '/js/draw.js';", "absolute path"),
    ("js/app.js", "xhr.open('GET', '/data/index.json');", "absolute path"),
    ("js/app.js", "new URL('/data/words.json', location.origin)", "absolute path"),
    ("index.html", '<script src="/js/app.js"></script>', "absolute path"),
    ("index.html", '<link rel="stylesheet" href="/css/app.css">', "absolute path"),
    ("css/app.css", "body { background: url(/img/bg.svg); }", "absolute path"),
    ("js/app.js", "const key = process.env.API_KEY;", "environment variable"),
    ("js/app.js", "const key = import.meta.env.VITE_KEY;", "environment variable"),
    ("js/app.js", "fetch('api/plans')", "server function"),
    ("js/app.js", "fetch('./api/plans?x=1')", "server function"),
])
def test_what_would_break_a_static_site_is_found(tmp_path, name, text, kind):
    problems = cs.site_problems(_site(tmp_path, {**GOOD, name: text}))
    assert any(p["kind"] == kind and p["file"] == name for p in problems), problems


@pytest.mark.parametrize("name, text", [
    ("api/hello.js", "export default (req, res) => res.end('hi');"),
    ("middleware.js", "export function middleware() {}"),
    ("package.json", '{"scripts": {"build": "vite build"}}'),
    (".env", "KEY=1"),
    ("js/app.ts", "const x: number = 1;"),
    ("vercel.json", '{"functions": {"api/*.js": {"memory": 128}}}'),
    ("vercel.json", '{"env": {"KEY": "1"}}'),
    ("vercel.json", '{"buildCommand": "npm run build"}'),
])
def test_files_that_mean_functions_a_build_step_or_environment_variables_are_refused(tmp_path, name, text):
    problems = cs.site_problems(_site(tmp_path, {**GOOD, name: text}))
    assert any(p["file"] == name for p in problems), problems


def test_a_vercel_json_that_only_sets_headers_is_fine(tmp_path):
    ok = '{"cleanUrls": false, "headers": [{"source": "/data/(.*)", "headers": [{"key": "Cache-Control", "value": "no-cache"}]}]}'
    assert cs.site_problems(_site(tmp_path, {**GOOD, "vercel.json": ok})) == []


def test_the_final_check_wants_index_html_at_the_root_of_site(tmp_path):
    files = {k: v for k, v in GOOD.items() if k != "index.html"}
    assert cs.site_problems(_site(tmp_path, files)) == []                       # before the UI lands: data only
    assert any(p["kind"] == "missing" for p in cs.site_problems(_site(tmp_path, files), final=True))


def test_the_real_site_folder_is_static_and_pages_publishes_only_site():
    assert cs.site_problems(REPO / "site") == []
    wf = (REPO / ".github" / "workflows" / "pages.yml").read_text()               # hosting: GitHub Pages (2026-11-14 night)
    assert "branches: [main]" in wf and "upload-pages-artifact" in wf and "path: site\n" in wf
    assert "run:" not in wf                                                          # no build step, nothing but site/
