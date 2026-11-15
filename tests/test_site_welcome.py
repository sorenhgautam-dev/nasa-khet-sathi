"""The loading curtain (owner, 2026-11-15, twice): the teammate's colours (ink, lime, cream); in the centre the leaf logo,
breathing slowly (scale 1.0 to 1.04), "खेत साथी · Khet Sathi" below it in our fonts (Mukta for Nepali), no stray dot; the
7 welcome words one after another, Nepali first, with short crossfades and a slight upward drift; a thin progress line
that fills as the app loads; then the curtain slides up (500-600 ms, ease-out) onto Home. Only opacity and transform move,
with soft easing; nothing jumps; under 2 s in all; a tap skips it; once per visit; reduced motion: the logo and
"स्वागत छ · Welcome", still. Any failure opens the app. The browser's translate bar is told not to offer to translate an
app that has its own languages."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HTML = (REPO / "site" / "index.html").read_text()
APP = (REPO / "site" / "js" / "app.js").read_text()
CSS = (REPO / "site" / "css" / "app.css").read_text()
ORDER = ["ne", "en", "hi", "bn", "es", "fr", "sw"]
CURTAIN_HTML = re.search(r'<div id="curtain">(.*?)</div>\n<!--', HTML, re.S).group(1)
CURTAIN_CSS = CSS[CSS.index("/* ---------------- curtain (first paint)"):CSS.index("/* ---------------- frame, header")]


def _curtain_words():
    box = re.search(r'<p class="hello" aria-hidden="true" hidden>(.*?)</p>', HTML).group(1)
    return re.findall(r'<span lang="([a-z]+)">([^<]+)</span>', box)


def _ms(name):
    return int(re.search(rf"{name} = (\d+)", APP).group(1))


def test_the_curtain_holds_the_owners_seven_words_nepali_first():
    assert _curtain_words() == [("ne", "स्वागत छ"), ("en", "Welcome"), ("hi", "स्वागत है"), ("bn", "স্বাগতম"),
                                ("es", "Bienvenidos"), ("fr", "Bienvenue"), ("sw", "Karibu")]


def test_the_words_are_the_reviewed_words_lists_and_the_nepali_is_marked_for_review():
    words = json.loads((REPO / "site" / "data" / "words.json").read_text())
    node = words["shared"]["welcome"]
    assert node["ne_review"] == "needs native-speaker review"
    assert _curtain_words() == [(lang, node[lang]) for lang in ORDER]
    assert [x["code"] for x in words["languages"]] == ORDER                  # the site's own language order


def test_logo_and_name_in_the_centre_and_no_stray_dot():
    leaf = re.search(r"leaf: '([^']+)'", APP).group(1)                          # the header's own leaf icon
    assert 'class="clogo"' in CURTAIN_HTML and leaf in CURTAIN_HTML
    assert '<span lang="ne">खेत साथी</span>' in CURTAIN_HTML and '<span lang="en">Khet Sathi</span>' in CURTAIN_HTML
    assert "dot" not in CURTAIN_HTML and ".dot" not in CURTAIN_CSS
    assert re.search(r'#curtain \.cname \[lang="ne"\][^{]*\{[^}]*font-family: Mukta', CURTAIN_CSS)


def test_only_opacity_and_transform_move_with_soft_easing():
    for props in re.findall(r"transition(?:-property)?:\s*([^;]+);", CURTAIN_CSS):
        for part in re.split(r",(?![^(]*\))", props):                     # commas inside cubic-bezier() are not lists
            assert part.split()[0] in ("opacity", "transform", "none"), part
    assert "cubic-bezier(.22, 1, .36, 1)" in CURTAIN_CSS
    breathe = re.search(r"@keyframes ks-breathe \{([^}]*\}[^}]*)\}", CURTAIN_CSS).group(1)
    assert "scale(1)" in breathe and "scale(1.04)" in breathe and "opacity" not in breathe
    assert "#curtain .hello[hidden] { display: block; visibility: hidden; }" in CURTAIN_CSS   # its room is kept: no jump
    assert "body:has(#curtain) #sky .puff { opacity: 0; }" in CURTAIN_CSS                 # no stall as the slide starts


def test_under_two_seconds_slide_up_500_to_600_ms_and_a_tap_skips_it():
    first, step, hold, lift, still = (_ms(k) for k in ("HELLO_FIRST_MS", "HELLO_STEP_MS", "HELLO_HOLD_MS", "LIFT_MS", "HELLO_STILL_MS"))
    assert first + step * 6 + hold + lift < 2000 and still < 2000
    assert 500 <= lift <= 600 and f"{lift}ms" in CURTAIN_CSS.replace(" ", "")
    assert "cur.addEventListener('click', skip)" in APP and "D.addEventListener('keydown', skip, { once: true })" in APP


def test_a_progress_line_fills_as_the_app_loads():
    assert '<span class="cbar" aria-hidden="true"><span></span></span>' in CURTAIN_HTML
    body = APP[APP.index("function init() {"):APP.index("W.KS = {")]
    assert "scaleX(" in body and body.count("step(") >= 4                     # started, words, fields list, Home drawn


def test_once_per_visit_reduced_motion_still_and_any_failure_opens_the_app():
    body = APP[APP.index("function hello(cur) {"):APP.index("function init() {")]
    assert "ss.getItem('ks.hello')" in body and "ss.setItem('ks.hello', '1')" in body
    assert "if (RM) {" in body and "words[0].textContent + ' · ' + words[1].textContent" in body
    assert "} catch (e) { return 0; }" in body                               # 0: the curtain as before


def test_our_fonts_arrive_with_the_curtain_and_no_translate_bar():
    assert "<html lang=\"ne\" translate=\"no\">" in HTML and '<meta name="google" content="notranslate">' in HTML
    for f in ("mukta-devanagari-700.woff2", "inter-tight-latin-var.woff2"):
        assert f'<link rel="preload" href="fonts/{f}" as="font" type="font/woff2" crossorigin>' in HTML
    assert '<link rel="stylesheet" href="fonts/fonts.css">' in HTML
    assert "url(" not in CURTAIN_CSS and "@font-face" not in CURTAIN_CSS
